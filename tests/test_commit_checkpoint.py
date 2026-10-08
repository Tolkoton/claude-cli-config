#!/usr/bin/env python3
"""commit_checkpoint.sh commits where the policy allows and nowhere else — from INSIDE a
script, where no hook and no deny list can see the `git commit` it runs.

Pinned, each against a real throwaway repository with a real branch checked out:

- a run's own suffixed branch (`unattended/<date>-<package>`) is kept, never forked onto
  today's date;
- on `main` the script moves to today's `unattended/<date>` branch first;
- `--staged` commits exactly the index: an untracked file that was `git add`ed goes in, a
  tracked modification that was not staged stays out; without the flag tracked
  modifications are swept in (`git add -u`) and untracked files never are;
- a cloud session commits on its own branch only when CLOUD_COMMIT_POLICY says
  session-branch; with the switch off it still moves to the unattended branch, and on
  `main` it never commits in place.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import trace_env

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/unattended/commit_checkpoint.sh"


class Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ok   {name}")
        else:
            self.failed += 1
            print(f"  FAIL {name}  {detail[:500]}")


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, capture_output=True, text=True, check=False
    ).stdout.strip()


def repo_on(branch: str, cloud_policy: str | None = None) -> Path:
    root = Path(tempfile.mkdtemp(prefix="checkpoint-"))
    git(root, "init", "-q", "-b", "main")
    (root / "tracked.txt").write_text("v1\n", encoding="utf-8")
    (root / ".claude").mkdir()
    (root / ".claude/project.env").write_text(
        'SOURCE_DIRS="src"\n' + (f'CLOUD_COMMIT_POLICY="{cloud_policy}"\n' if cloud_policy else ""), encoding="utf-8"
    )
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")
    if branch != "main":
        git(root, "switch", "-qc", branch)
    return root


def checkpoint(root: Path, *args: str, cloud: bool = False) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/"), "CLAUDE_PROJECT_DIR": str(root), **trace_env()}
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "t"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "t@t"
    if cloud:
        env["CLAUDE_CODE_REMOTE"] = "true"
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, check=False)


def main() -> int:
    t = Checks()

    # --- a suffixed run branch is kept ----------------------------------------------------
    r = repo_on("unattended/2026-10-02-package-3b")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S1")
    t.check("suffixed branch: exit 0", out.returncode == 0, out.stdout + out.stderr)
    t.check("suffixed branch: committed on the SAME branch", git(r, "branch", "--show-current") == "unattended/2026-10-02-package-3b")
    t.check("suffixed branch: one new commit", git(r, "rev-list", "--count", "HEAD") == "2")
    t.check("suffixed branch: no second unattended branch was created", git(r, "branch", "--list", "unattended/*").count("unattended/") == 1)

    # --- main moves to today's branch -----------------------------------------------------
    r = repo_on("main")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S1")
    now = git(r, "branch", "--show-current")
    t.check("main: moved to today's unattended branch", out.returncode == 0 and now.startswith("unattended/20"), now + out.stderr)
    t.check("main: main itself gained no commit", git(r, "rev-list", "--count", "main") == "1")

    # --- --staged commits exactly the index -----------------------------------------------
    r = repo_on("unattended/2026-10-02-x")
    (r / "new.txt").write_text("new\n", encoding="utf-8")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    git(r, "add", "new.txt")
    out = checkpoint(r, "--staged", "S2", "staged only")
    t.check("--staged: exit 0", out.returncode == 0, out.stdout + out.stderr)
    shown = git(r, "show", "--stat", "--format=", "HEAD")
    t.check("--staged: the added untracked file is in", "new.txt" in shown, shown)
    t.check("--staged: the unstaged tracked change is NOT in", "tracked.txt" not in shown and "tracked.txt" in git(r, "status", "--porcelain"), shown)
    t.check("--staged: the message was used", git(r, "log", "-1", "--format=%s") == "staged only")

    # --- without the flag: tracked modifications swept in, untracked never ----------------
    out = checkpoint(r, "S3")
    shown = git(r, "show", "--stat", "--format=", "HEAD")
    (r / "scratch.log").write_text("x", encoding="utf-8")
    out2 = checkpoint(r, "S3")
    t.check("default: the tracked modification is swept in", out.returncode == 0 and "tracked.txt" in shown, shown)
    t.check("default: an untracked file is never swept in (nothing to commit)", out2.returncode == 0 and "nothing to commit" in out2.stdout, out2.stdout)

    # --- nothing staged is not an error ---------------------------------------------------
    out = checkpoint(r, "--staged", "S4")
    t.check("nothing staged: exit 0 with a note", out.returncode == 0 and "nothing to commit" in out.stdout, out.stdout)

    # --- cloud: the switch ----------------------------------------------------------------
    r = repo_on("claude/session-1", cloud_policy="session-branch")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S5", cloud=True)
    t.check("cloud, switch on: committed on the session's own branch", out.returncode == 0 and git(r, "branch", "--show-current") == "claude/session-1" and git(r, "rev-list", "--count", "HEAD") == "2", out.stdout + out.stderr)
    r = repo_on("claude/session-1", cloud_policy="off")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S5", cloud=True)
    t.check("cloud, switch off: moved to an unattended branch instead", out.returncode == 0 and git(r, "branch", "--show-current").startswith("unattended/"), out.stdout + out.stderr)
    t.check("cloud, switch off: the session branch gained no commit", git(r, "rev-list", "--count", "claude/session-1") == "1")
    r = repo_on("claude/session-1")  # no key at all
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S5", cloud=True)
    t.check("cloud, no key: treated as off", git(r, "branch", "--show-current").startswith("unattended/"), out.stdout + out.stderr)
    r = repo_on("main", cloud_policy="session-branch")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S6", cloud=True)
    t.check("cloud, switch on, on main: never commits on main", git(r, "rev-list", "--count", "main") == "1" and git(r, "branch", "--show-current").startswith("unattended/"), out.stdout + out.stderr)
    r = repo_on("claude/session-1", cloud_policy="session-branch")
    (r / "tracked.txt").write_text("v2\n", encoding="utf-8")
    out = checkpoint(r, "S7", cloud=False)
    t.check("local with the switch on: not a cloud session, so the unattended branch", git(r, "branch", "--show-current").startswith("unattended/"), out.stdout + out.stderr)

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
