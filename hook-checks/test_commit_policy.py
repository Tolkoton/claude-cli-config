#!/usr/bin/env python3
"""Commits are legal on unattended/<date> and nowhere else — plus the cloud switch.

Owner-ratified 2026-08-27. The checkpoint is kept where it does work -- nothing
reaches main without a human -- while a long run gets a committed base to build
on, instead of each session working on top of an unreviewed index inherited from
the one before it.

Package 3b adds the environment table (docs/plan/package-3b.md): a CLOUD session
(CLAUDE_CODE_REMOTE=true) may commit on its own non-protected branch, but ONLY when
CLOUD_COMMIT_POLICY in .claude/project.env says session-branch. The switch ships off.

Every case runs against a REAL throwaway git repo with a real branch checked
out, because the hook reads the branch with `git branch --show-current`; faking
it would test the test.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / ".claude/hooks/block-dangerous.sh"


def repo_on(branch: str) -> str:
    root = Path(tempfile.mkdtemp())

    def run(*a: str) -> None:
        subprocess.run(a, cwd=root, capture_output=True, text=True, check=False)

    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    (root / "f.txt").write_text("x")
    run("git", "add", "f.txt")
    run("git", "commit", "-qm", "init")
    if branch != "main":
        run("git", "switch", "-qc", branch)
    else:
        run("git", "branch", "-M", "main")
    return str(root)


def with_cloud_policy(root: str, value: str) -> str:
    """The same repo with CLOUD_COMMIT_POLICY set in .claude/project.env (the switch)."""
    env_file = Path(root) / ".claude" / "project.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f'SOURCE_DIRS="src"\nCLOUD_COMMIT_POLICY="{value}"\n')
    return root


def blocked(cmd: str, project_dir: str, cloud: bool = False) -> bool:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "CLAUDE_PROJECT_DIR": project_dir}
    if cloud:
        env["CLAUDE_CODE_REMOTE"] = "true"  # what a cloud session sets (code.claude.com/docs/en/env-vars)
    r = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return r.returncode == 2


UNATT = repo_on("unattended/2026-08-27")
MAIN = repo_on("main")
FEAT = repo_on("feat/something")
SUFFIXED = repo_on("unattended/2026-10-02-package-3b")
CLOUD_OFF = repo_on("claude/session-abc")  # no project.env at all
CLOUD_OFF_EXPLICIT = with_cloud_policy(repo_on("claude/session-abc"), "off")
CLOUD_ON = with_cloud_policy(repo_on("claude/session-abc"), "session-branch")
CLOUD_ON_MAIN = with_cloud_policy(repo_on("main"), "session-branch")
FORCE_PUSH = "git push " + "--force"  # split so the hook under test does not block THIS file being written

CASES = [
    # (name, command, project_dir, cloud?, must_block)
    ("commit on unattended/<date>", "git commit -m x", UNATT, False, False),
    ("compound commit on unattended", "cd . && git commit -m x", UNATT, False, False),
    ("commit -C form on unattended", "git -C . commit -m x", UNATT, False, False),
    ("commit on main", "git commit -m x", MAIN, False, True),
    ("compound commit on main", "cd . && git commit -m x", MAIN, False, True),
    ("commit -C form on main", "git -C . commit -m x", MAIN, False, True),
    ("commit on an ordinary feature branch", "git commit -m x", FEAT, False, True),
    ("push still blocked on main", "git push origin main", MAIN, False, True),
    ("force-push blocked on unattended too", FORCE_PUSH, UNATT, False, True),
    ("ordinary staging on main", "git add .", MAIN, False, False),
    ("status on unattended", "git status", UNATT, False, False),
    ("commit on a suffixed unattended branch", "git commit -m x", SUFFIXED, False, False),
    # --- by environment: the cloud switch ---------------------------------------------------
    ("local, session branch, switch on: refused (not a cloud session)", "git commit -m x", CLOUD_ON, False, True),
    ("cloud, no project.env: refused (switch defaults to off)", "git commit -m x", CLOUD_OFF, True, True),
    ("cloud, switch explicitly off: refused", "git commit -m x", CLOUD_OFF_EXPLICIT, True, True),
    ("cloud, switch on, session branch: allowed", "git commit -m x", CLOUD_ON, True, False),
    ("cloud, switch on, compound form: allowed", "cd . && git commit -m x", CLOUD_ON, True, False),
    ("cloud, switch on, on main: still refused (protected)", "git commit -m x", CLOUD_ON_MAIN, True, True),
    ("cloud, switch on: force push still blocked", FORCE_PUSH, CLOUD_ON, True, True),
    ("cloud, unattended branch: allowed regardless of the switch", "git commit -m x", UNATT, True, False),
]

fails = []
for name, cmd, root, cloud, must_block in CASES:
    got = blocked(cmd, root, cloud=cloud)
    ok = got == must_block
    verdict = "BLOCK" if got else "allow"
    print(f"  {'ok  ' if ok else 'FAIL'} {name:64} -> {verdict}")
    if not ok:
        fails.append(f"{name}: expected {'BLOCK' if must_block else 'allow'}, got {verdict}")

print()
if fails:
    print(f"FAIL ({len(fails)}):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print(f"PASS {len(CASES)}/{len(CASES)} commit-policy cases")
