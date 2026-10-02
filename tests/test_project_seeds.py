#!/usr/bin/env python3
"""A new project starts from the short clean seeds in templates/project/, not from this
repository's own CLAUDE.md and AGENTS.md — and the seed imports the engine's rules.

WHY. Until package 2b the seed for CLAUDE.md WAS this repository's CLAUDE.md: a new project
received 202 lines that mixed the engine's rules with text about the engine repository
("Agents guide — claude-cli-config", its evals, its test runner). The rules now ship as the
engine-owned `.claude/engine-rules.md`; a project's CLAUDE.md only imports it.

engine.py reads the engine from a git ref, never from the working tree, so the test commits
the working tree's `.claude/`, `templates/` and `engine.py` into a temporary engine
repository and installs from it — the same device tests/test_engine_install.py uses.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def engine_repo_from_working_tree(where: Path) -> Path:
    """A git repository holding this working tree's engine files (tracked or not), committed once."""
    eng = where / "engine"
    eng.mkdir()
    for rel in (".claude", "templates"):
        shutil.copytree(ROOT / rel, eng / rel, ignore=shutil.ignore_patterns("__pycache__", "state", "settings.local.json"))
    shutil.copy2(ROOT / "engine.py", eng / "engine.py")
    git(eng, "init", "-q", "-b", "main")
    git(eng, "add", "-A")
    git(eng, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "engine from the working tree")
    git(eng, "tag", "v99.0.0")
    return eng


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="project-seeds-") as tmp:
        where = Path(tmp)
        eng = engine_repo_from_working_tree(where)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(where / "projects.txt")}
        proj = where / "fresh"
        proj.mkdir()
        git(proj, "init", "-q", "-b", "main")

        r = subprocess.run([sys.executable, str(eng / "engine.py"), "install", str(proj), "--ref", "v99.0.0", "--no-register"],
                           capture_output=True, text=True, env=env, check=False)
        check("install exits 0", r.returncode == 0, r.stdout + r.stderr)

        seed_claude = (ROOT / "templates/project/CLAUDE.md").read_text(encoding="utf-8")
        seed_agents = (ROOT / "templates/project/AGENTS.md").read_text(encoding="utf-8")
        got_claude = (proj / "CLAUDE.md").read_text(encoding="utf-8") if (proj / "CLAUDE.md").is_file() else ""
        got_agents = (proj / "AGENTS.md").read_text(encoding="utf-8") if (proj / "AGENTS.md").is_file() else ""
        check("the project's CLAUDE.md is the seed, byte for byte", got_claude == seed_claude)
        check("the project's AGENTS.md is the seed, byte for byte", got_agents == seed_agents)
        check("it is NOT this repository's CLAUDE.md", got_claude != (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
        check("it is NOT this repository's AGENTS.md", got_agents != (ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        check("nothing about the engine repository leaks into the seeds",
              "claude-cli-config" not in got_claude + got_agents and "evals/" not in got_claude + got_agents)
        check("the seed CLAUDE.md imports the engine's rules from the marked block",
              "<!-- >>> engine:" in got_claude and "@.claude/engine-rules.md" in got_claude and "<!-- <<< engine -->" in got_claude)
        rules = proj / ".claude" / "engine-rules.md"
        check("the engine's rules file ships with the engine", rules.is_file() and rules.read_text(encoding="utf-8") == (ROOT / ".claude/engine-rules.md").read_text(encoding="utf-8"))
        check("the references ship too", (proj / ".claude/references/hooks.md").is_file() and (proj / ".claude/references/unattended.md").is_file())
        check("no .claude/CLAUDE.md and no .claude/rules/ in the project (nothing is loaded twice)",
              not (proj / ".claude/CLAUDE.md").exists() and not (proj / ".claude/rules").exists())

        # The persistent context of the seeded project, counted the way tests/test_context_budget.py counts.
        total = sum(len((proj / f).read_text(encoding="utf-8").splitlines()) for f in ("CLAUDE.md", "AGENTS.md", ".claude/engine-rules.md"))
        check(f"a seeded project's persistent context is {total} lines (budget 200)", total <= 200)

        # A second install changes nothing; an edited CLAUDE.md is never overwritten.
        (proj / "CLAUDE.md").write_text(got_claude + "\n## Ours\n- a convention\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(eng / "engine.py"), "update", str(proj), "--ref", "v99.0.0"],
                           capture_output=True, text=True, env=env, check=False)
        check("update after an edit: exit 0, the project's CLAUDE.md untouched",
              r.returncode == 0 and (proj / "CLAUDE.md").read_text(encoding="utf-8").endswith("## Ours\n- a convention\n"), r.stdout + r.stderr)
        verbs = [line.split()[0] for line in r.stdout.splitlines() if line.startswith("  ") and line.split()]
        check("update does not seed or reseed", not {"seed", "reseed"} & set(verbs), r.stdout)

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
