#!/usr/bin/env python3
"""The engine's lint is red on a form only a newer Python parses on a machine WITHOUT the oldest Python too (board 769).

Board 748: testing.py:202 carried a backslash inside an f-string's expression, a 3.12 form, and nothing under 3.11
started. The check that came with the fix compiled every file with python3.11 — when it was on PATH; without it
tests/test_engine_lint.py printed a note and «PASS: engine lint clean», exit 0, so the regression passed every
machine that lacks 3.11, against that file's own rule: a lint gate that cannot run has not run. Board 751 gave
ruff `--target-version`; this suite holds the verdict of the whole lint in place, whatever way it is reached:

  - a throwaway copy of the repository's Python (the .py files under .claude/ with ownership.txt, engine.py,
    evals/*.py, tests/*.py), judged by the copy's own tests/test_engine_lint.py;
  - a PATH of links to everything on this machine's PATH except python<MIN_PYTHON>, so the scene is the same on a
    machine that has the oldest Python and on one that has not;
  - as the code stands the lint is green there; with board 748's line back in the copy's .claude/hooks/testing.py
    it exits non-zero and a FAIL line names testing.py.

Run:   python3 tests/test_engine_lint_oldest.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import hook_env
from tool_pins import tool_versions

ROOT = Path(__file__).resolve().parent.parent
MIN_PYTHON: str = tool_versions.MIN_PYTHON
OLDEST = f"python{MIN_PYTHON}"
# The two lines board 748 left in testing.py, and the one line as it stood before — a form only 3.12 parses.
FIXED = ('        escaped = compact.replace("--", "-\\\\u002d")   # outside the f-string: a backslash in its expression needs Python 3.12\n'
         '        carried = f"<!-- row: {escaped} -->\\n"\n')
BROKEN = "        carried = f\"<!-- row: {compact.replace('--', '-\\\\u002d')} -->\\n\"\n"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:1200]}")


def copy_of_repository(target: Path) -> None:
    """The Python test_engine_lint judges, and what it needs to tell the engine's files from a project's."""
    files = [p for p in (ROOT / ".claude").rglob("*.py") if not {"__pycache__", "state"} & set(p.relative_to(ROOT).parts)]
    files += [ROOT / ".claude/ownership.txt", ROOT / "engine.py", *(ROOT / "evals").glob("*.py"), *(ROOT / "tests").glob("*.py")]
    for source in files:
        place = target / source.relative_to(ROOT)
        place.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, place)


def path_without_oldest(folder: Path) -> str:
    """This machine's PATH, directory by directory, as links to everything in it but the oldest Python."""
    mirrors = []
    for number, place in enumerate(p for p in os.environ.get("PATH", "").split(os.pathsep) if p and Path(p).is_dir()):
        mirror = folder / str(number)
        mirror.mkdir(parents=True)
        for entry in Path(place).iterdir():
            if entry.name != OLDEST:
                (mirror / entry.name).symlink_to(entry)
        mirrors.append(str(mirror))
    return os.pathsep.join(mirrors)


def lint(copy: Path, path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "tests/test_engine_lint.py"], cwd=copy, env=hook_env(str(copy), PATH=path),
                          capture_output=True, text=True, check=False)


with tempfile.TemporaryDirectory() as tmp:
    copy = Path(tmp) / "repo"
    copy_of_repository(copy)
    path = path_without_oldest(Path(tmp) / "bin")
    print(f"— a machine without {OLDEST}")
    check(f"the PATH of the scene has no {OLDEST}", shutil.which(OLDEST, path=path) is None, shutil.which(OLDEST, path=path))

    r = lint(copy, path)
    check("the code as it stands: the lint is green there", r.returncode == 0 and "PASS: engine lint clean" in r.stdout,
          f"exit {r.returncode}\n{r.stdout}{r.stderr}")

    testing = copy / ".claude/hooks/testing.py"
    text = testing.read_text(encoding="utf-8")
    check("the lines board 748 left are in testing.py once, to put the old one in their place", text.count(FIXED) == 1, text.count(FIXED))
    testing.write_text(text.replace(FIXED, BROKEN), encoding="utf-8")
    try:
        compile(testing.read_text(encoding="utf-8"), str(testing), "exec")
        parses_here = True
    except SyntaxError:
        parses_here = False
    newer = sys.version_info >= (3, 12)
    check("the old line is the form this scene is about: python3.12+ parses it, an older one does not", parses_here == newer,
          f"parses under {sys.version.split()[0]}: {parses_here}")

    r = lint(copy, path)
    failures = [line for line in r.stdout.splitlines() if "testing.py" in line and ("FAIL" in line or "invalid-syntax" in line)]
    check(f"board 748's line back in testing.py: the lint exits non-zero without {OLDEST}", r.returncode != 0,
          f"exit {r.returncode}\n{r.stdout}{r.stderr}")
    check("…its verdict line is FAIL, not «PASS: engine lint clean»",
          "FAIL: engine lint has findings" in r.stdout and "PASS: engine lint clean" not in r.stdout, r.stdout[-600:])
    check("…and what it reports names testing.py", bool(failures), r.stdout)

print(f"\n{'FAIL' if FAIL else 'PASS'}: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
