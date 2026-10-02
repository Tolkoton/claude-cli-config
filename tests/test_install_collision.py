#!/usr/bin/env python3
"""install.sh refuses to deploy a personal skill whose name an engine skill or command
already carries — before it links anything — and deploys cleanly otherwise.

A personal skill is /<name>, in the same namespace as the engine's .claude/skills/ and
.claude/commands/. Deployed into ~/.claude/skills it would shadow (or be shadowed by) the
engine's own in every project — so a collision is refused with the reason and the `my-`
prefix convention for new personal skills. Existing personal skills are never renamed; the
check is what protects their names.

Cases run against a copy of install.sh in a synthetic repository and a temporary CLAUDE_HOME;
the last one runs the REAL install.sh against this repository into a temporary home.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"


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


def synthetic_repo(root: Path, user_skills: list[str]) -> Path:
    root.mkdir()
    for name in ("overseer", "slice-builder"):
        (root / ".claude/skills" / name).mkdir(parents=True)
        (root / ".claude/skills" / name / "SKILL.md").write_text(f"# {name}\n")
    (root / ".claude/commands").mkdir(parents=True)
    (root / ".claude/commands/plan-slice.md").write_text("# plan-slice\n")
    for name in user_skills:
        (root / "user/skills" / name).mkdir(parents=True)
        (root / "user/skills" / name / "SKILL.md").write_text(f"# {name}\n")
    shutil.copy2(INSTALL, root / "install.sh")
    return root


def run(repo: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/"), "CLAUDE_HOME": str(home)}
    return subprocess.run(["bash", str(repo / "install.sh")], capture_output=True, text=True, env=env, check=False)


def links_in(home: Path) -> list[str]:
    skills = home / "skills"
    return sorted(p.name for p in skills.iterdir()) if skills.is_dir() else []


def main() -> int:
    t = Checks()
    with tempfile.TemporaryDirectory(prefix="install-collision-") as tmp:
        tmp_path = Path(tmp)

        # --- a collision with an engine skill: refused, nothing linked --------------------------
        repo = synthetic_repo(tmp_path / "repo-skill-clash", ["live-build", "overseer"])
        home = tmp_path / "home1"
        r = run(repo, home)
        t.check("skill-name collision: exit 1", r.returncode == 1, r.stdout + r.stderr)
        t.check("skill-name collision: names the colliding skill and says why", "COLLISION overseer" in r.stderr and "shadow" in r.stderr, r.stderr)
        t.check("skill-name collision: points to the my- prefix", "user/skills/my-overseer" in r.stderr, r.stderr)
        t.check("skill-name collision: NOTHING was linked (not even the clean skill)", links_in(home) == [], str(links_in(home)))

        # --- a collision with an engine command: refused too -----------------------------------
        repo = synthetic_repo(tmp_path / "repo-command-clash", ["plan-slice"])
        home = tmp_path / "home2"
        r = run(repo, home)
        t.check("command-name collision: refused", r.returncode == 1 and "COLLISION plan-slice" in r.stderr, r.stderr)

        # --- no collision: linked -----------------------------------------------------------------
        repo = synthetic_repo(tmp_path / "repo-clean", ["live-build", "my-notes"])
        home = tmp_path / "home3"
        r = run(repo, home)
        t.check("no collision: exit 0", r.returncode == 0, r.stdout + r.stderr)
        t.check("no collision: both skills linked", links_in(home) == ["live-build", "my-notes"], str(links_in(home)))
        t.check("no collision: links point into the repository", (home / "skills/live-build").is_symlink() and (home / "skills/live-build").resolve() == (repo / "user/skills/live-build").resolve())
        r = run(repo, home)
        t.check("re-run: idempotent (relinked, exit 0)", r.returncode == 0 and "relinked" in r.stdout, r.stdout)

        # --- a real directory in the way is never destroyed -------------------------------------
        home = tmp_path / "home4"
        (home / "skills/my-notes").mkdir(parents=True)
        (home / "skills/my-notes/keep.txt").write_text("mine")
        r = run(repo, home)
        t.check("existing real directory: skipped, exit 1, file intact", r.returncode == 1 and "SKIPPED" in r.stderr and (home / "skills/my-notes/keep.txt").read_text() == "mine", r.stderr)

        # --- THIS repository, for real, into a temporary home ----------------------------------
        home = tmp_path / "home-real"
        r = run(ROOT, home)
        t.check("this repository: no personal skill collides with an engine name", r.returncode == 0, r.stdout + r.stderr)
        t.check("this repository: live-build is deployed", "live-build" in links_in(home), str(links_in(home)))

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
