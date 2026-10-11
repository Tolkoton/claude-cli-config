#!/usr/bin/env python3
"""After engine.py moves a project's records to .engine/, it says what the project still says
about the old places (board 094) — and changes nothing in the project's own files.

WHY. The full trial of /onboard (board 057) installed the current engine over an older one: 19
records moved, the project's scripts and its file for agents went on naming the old paths, two
of its checks then exited 0 having checked nothing, and its formatter began to fail on three
moved files because the old directory was in its exclusions and the new one was not. The
installer said none of it.

The fixture, a real git repository: records at the old paths, a script that reads one, a file
for agents that names another, a formatter exclusion on the old directory, a second
configuration that names both the old and the new place, and — the negative cases — a line that
names only the new path, an engine file and a moved record that name the old ones, and a
configuration line about `.claude/tools`, which is not a place a record left.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
PASS = FAIL = 0

FILES = {
    ".claude/overseer/ledger.md": "# ledger\n\nthe records live in .claude/overseer/ — an entry of this project\n",
    ".claude/overseer/slice/checkout.md": "# checkout\n",
    ".claude/premises/premise-log.md": "# premises of this project\n",
    "PROGRESS.md": "# progress of this project\n",
    "scripts/check-ledger.sh": "#!/bin/sh\n# exits 0 when the ledger is absent\n[ -f .claude/overseer/ledger.md ] || exit 0\ngrep -c PASS .claude/overseer/ledger.md\n",
    "scripts/new-layout.sh": "#!/bin/sh\ncat .engine/PROGRESS.md .engine/overseer/ledger.md\n",
    "AGENTS.md": "# Agents\n\nRead PROGRESS.md first; premises are in `.claude/premises/premise-log.md`.\n",
    "pyproject.toml": '[tool.ruff]\nextend-exclude = [".claude", "build"]\n',
    ".prettierignore": "node_modules\n.claude/overseer/\n.engine/\n",
    ".pre-commit-config.yaml": "repos:\n  - repo: local\n    hooks:\n      - id: x\n        entry: python3 .claude/tools/x.py\n",
    ".claude/skills/old/SKILL.md": "# an engine file of the old copy: reads .claude/overseer/ledger.md\n",
    "big.txt": ".claude/overseer/ledger.md\n" * 60,
}


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900]}")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def engine(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ENGINE_PY), *args], capture_output=True, text=True, env=env, check=False)


def tree(project: Path) -> dict[str, bytes]:
    return {p.relative_to(project).as_posix(): p.read_bytes() for p in sorted(project.rglob("*")) if p.is_file() and ".git" not in p.relative_to(project).parts}


def notes(out: str) -> list[str]:
    return [line[len("  note    "):] for line in out.splitlines() if line.startswith("  note    ")]


def fixture(project: Path, files: dict[str, str], as_git: bool = True) -> None:
    project.mkdir()
    for rel, body in files.items():
        (project / rel).parent.mkdir(parents=True, exist_ok=True)
        (project / rel).write_text(body, encoding="utf-8")
    if as_git:
        git(project, "init", "-q", "-b", "main")
        git(project, "add", "-A")
        git(project, "commit", "-qm", "a project with an older engine's layout")


with tempfile.TemporaryDirectory(prefix="move-notes-") as tmp:
    env = {**os.environ, "ENGINE_PROJECTS_FILE": str(Path(tmp) / "projects.txt")}

    print("install --dry-run on a project with records at the old paths")
    p = Path(tmp) / "old"
    fixture(p, {k: v for k, v in FILES.items() if k != "big.txt"})
    before = tree(p)
    r = engine(env, "install", str(p), "--ref", "HEAD", "--dry-run", "--no-register")
    said = notes(r.stdout)
    check("the dry run runs and plans the moves", r.returncode in (0, 1) and "move    PROGRESS.md  — -> .engine/PROGRESS.md" in r.stdout, r.stdout[-900:] + r.stderr)
    check("the dry run writes nothing", tree(p) == before)
    check("note 1: the script that reads the old path, by file:line — both lines",
          "scripts/check-ledger.sh:3 still names .claude/overseer, which the move empties" in said
          and "scripts/check-ledger.sh:4 still names .claude/overseer, which the move empties" in said, said)
    check("note 1: the file for agents names two old paths on one line — one note, both paths",
          [n for n in said if n.startswith("AGENTS.md:")] == ["AGENTS.md:3 still names PROGRESS.md, .claude/premises, which the move empties"], said)
    check("note 1: a line that names only the new paths is not reported", not any(n.startswith("scripts/new-layout.sh") for n in said), said)
    check("note 1: an engine file and a moved record that name the old path are not the project's files",
          not any(n.startswith((".claude/skills/", ".claude/overseer/")) for n in said), said)
    check("note 2: the formatter exclusion on the old directory, and the file does not name the new one",
          any(n.startswith('pyproject.toml:2 names .claude and the file nowhere names .engine') and "no longer kept out" in n for n in said), said)
    check("note 2: a configuration that names the new place too says so, with both lines",
          any(n.startswith(".prettierignore:2 names .claude/overseer; the file names .engine too (.prettierignore:3)") for n in said), said)
    check("note 2: a configuration line about .claude/tools is not an exclusion of a moved place",
          not any(n.startswith(".pre-commit-config.yaml") for n in said), said)

    print("the real install changes nothing in the project's own files")
    r = engine(env, "install", str(p), "--ref", "HEAD", "--no-register")
    after = tree(p)
    own = ("scripts/check-ledger.sh", "scripts/new-layout.sh", "pyproject.toml", ".prettierignore", ".pre-commit-config.yaml")
    check("the install prints the same two notes", [n for n in notes(r.stdout) if "names" in n] == [n for n in said if "names" in n], r.stdout[-900:])
    check("the records moved", ".engine/overseer/ledger.md" in after and ".claude/overseer/ledger.md" not in after)
    check("the project's scripts and configuration are byte for byte as they were", all(after[f] == before[f] for f in own))
    r = engine(env, "update", str(p), "--ref", "HEAD", "--dry-run")
    check("a second run moves nothing and says nothing about old paths", "move    " not in r.stdout and not any("old path" in n or "which the move empties" in n for n in notes(r.stdout)), r.stdout[-900:])

    print("nothing names the old paths; many lines do; no git")
    q = Path(tmp) / "quiet"
    fixture(q, {"PROGRESS.md": "# progress\n", "src/app.py": "print('hello')\n"})
    said = notes(engine(env, "install", str(q), "--ref", "HEAD", "--dry-run", "--no-register").stdout)
    check("no mention and no configuration: each is said in one line",
          "no file of the project names the old paths (PROGRESS.md)" in said
          and "no lint or format configuration of the project names an old path of the moved records" in said, said)
    fresh = Path(tmp) / "fresh"
    fixture(fresh, {"src/app.py": "# reads .claude/overseer/ledger.md\n"})
    said = notes(engine(env, "install", str(fresh), "--ref", "HEAD", "--dry-run", "--no-register").stdout)
    check("no record moves — no search, no note", not any("old path" in n or "names" in n for n in said), said)
    m = Path(tmp) / "many"
    fixture(m, {".claude/overseer/ledger.md": "# ledger of this project\n", "big.txt": FILES["big.txt"]}, as_git=False)
    said = notes(engine(env, "install", str(m), "--ref", "HEAD", "--dry-run", "--no-register").stdout)
    check("sixty lines outside git: forty by file:line, the rest as a count",
          len([n for n in said if n.startswith("big.txt:")]) == 40 and "… and 20 more line(s) that name an old path" in said, said[-3:])

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
