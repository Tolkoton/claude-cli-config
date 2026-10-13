#!/usr/bin/env python3
"""The engine's own Python is lint-clean and strictly typed.

The hooks and the unattended harness are shipped into every project and run there without
a review step; a finding ruff or mypy would have raised is a defect every project inherits.
Package 3b found sixteen such findings that had accumulated in four hooks because nothing
ran the tools over .claude/. This runs them:

    ruff check --isolated .claude          (the engine's rule set, not a project's — .claude/ruff.toml
                                            excludes everything so a PROJECT'S ruff never judges the
                                            engine; --isolated is how the engine judges itself)
        --target-version py<MIN_PYTHON>    (board 751: the oldest Python the engine supports, from
                                            tool_versions.MIN_PYTHON — ruff then names every form only a
                                            newer Python parses, on a machine without that interpreter too)
    mypy --strict <every .py under .claude>

At the versions tool_versions.py pins (board 107; read through tests/tool_pins.py): a tool on PATH of exactly that
version, else `uvx <tool>@<version>`. Without either — or with only another version on PATH — the
check FAILS with the reason rather than passing vacuously or judging with another release: a lint
gate that cannot run has not run, and one whose verdict moves with a release is no gate.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tool_pins import tool_versions as VERSIONS

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / ".claude"
MIN_PYTHON: str = VERSIONS.MIN_PYTHON
RUFF_TARGET = "py" + MIN_PYTHON.replace(".", "")   # "3.11" -> "py311", ruff's name for it
# Board 748's line, as it stood in testing.py:202: a backslash inside an f-string's expression, which only 3.12 parses.
# Newer than MIN_PYTHON while that is 3.11: whoever raises MIN_PYTHON puts here a form the new minimum cannot parse.
NEWER_SYNTAX = 'compact = "a--b"\ncarried = f"<!-- row: {compact.replace("--", "-\\\\u002d")} -->\\n"\n'


def ruff_check(ruff: list[str], files: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """ruff over `files` as the engine judges itself: its own rule set, for the oldest supported Python."""
    return subprocess.run([*ruff, "check", "--isolated", "--target-version", RUFF_TARGET, "--output-format", "concise", *files],
                          cwd=cwd, capture_output=True, text=True, check=False)


def engine_python() -> list[str]:
    """The .py files under .claude/ that the ownership map calls `engine` — what ships.
    Project data under .claude/ (spikes in artifacts/, a project's own scripts) is not the
    engine's code and is not judged here."""
    spec = importlib.util.spec_from_file_location("engine", ROOT / "engine.py")
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    sys.modules["engine"] = module
    spec.loader.exec_module(module)
    rules = module.parse_ownership((ENGINE / "ownership.txt").read_text(encoding="utf-8"))
    files = []
    for p in sorted(ENGINE.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if module.owner_of(rules, rel) == "engine":
            files.append(rel)
    return files




def main() -> int:
    failed = 0
    py_files = engine_python()
    print(f"  {len(py_files)} engine-owned Python files under .claude/")

    ruff, why = VERSIONS.command("ruff")
    if ruff is None:
        print(f"  FAIL ruff: {why} — the engine cannot be linted here")
        failed += 1
    else:
        r = ruff_check(ruff, py_files, ROOT)
        ok = r.returncode == 0
        print(f"  {'ok  ' if ok else 'FAIL'} ruff {VERSIONS.VERSIONS['ruff']} check --isolated --target-version {RUFF_TARGET} <engine Python>  {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''}")
        if not ok:
            print(r.stdout[:3000])
            failed += 1
        # The negative case of the line above: the same call must be red on a form newer than MIN_PYTHON, or the
        # flag has stopped meaning anything (a ruff that no longer reports it, a target version it does not know).
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "newer.py").write_text(NEWER_SYNTAX, encoding="utf-8")
            r = ruff_check(ruff, ["newer.py"], Path(tmp))
        ok = r.returncode == 1 and "invalid-syntax" in r.stdout and f"Python {MIN_PYTHON}" in r.stdout
        print(f"  {'ok  ' if ok else 'FAIL'} ...and the same call is red on a form only a newer Python parses (a backslash inside an f-string's expression)")
        if not ok:
            print(f"  exit {r.returncode}: {(r.stdout + r.stderr).strip()[:600]}")
            failed += 1

    mypy, why = VERSIONS.command("mypy")
    if mypy is None:
        print(f"  FAIL mypy: {why} — the engine cannot be type-checked here")
        failed += 1
    elif py_files:
        r = subprocess.run([*mypy, "--strict", *py_files], cwd=ROOT, capture_output=True, text=True, check=False)
        ok = r.returncode == 0
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[:200]
        print(f"  {'ok  ' if ok else 'FAIL'} mypy {VERSIONS.VERSIONS['mypy']} --strict (engine Python)  {last}")
        if not ok:
            print(r.stdout[:3000])
            failed += 1

    # Board 748: the hooks say «Python 3.11+» (tool_versions.MIN_PYTHON), and a form that only 3.12 parses (a backslash inside an f-string's
    # expression) once kept testing.py from starting under 3.11 unseen — the suites run under the newest python3.
    # Every Python file of the repository is compiled by the oldest supported interpreter when it is on PATH (nothing
    # is written: compile() in memory). Board 771: every one is what git lists — the tracked files and the new ones it
    # does not ignore, at any depth (the scenes under evals/scenarios/ too) — not a glob of the top-level directories.
    oldest = shutil.which(f"python{MIN_PYTHON}")
    listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.py"],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    every = sorted({f for f in listed.stdout.split("\0") if f and (ROOT / f).is_file()})
    if oldest is None:
        print(f"  note python{MIN_PYTHON} is not on PATH: the oldest supported Python does not compile the files here (ruff judged the engine's for it above)")
    elif listed.returncode != 0 or not every:
        print(f"  FAIL python{MIN_PYTHON} compiles every Python file of the repository: git listed none (exit {listed.returncode}) "
              f"{listed.stderr.strip()[:200]} — nothing was compiled")
        failed += 1
    else:
        probe = ("import sys\nbad = []\nfor f in sys.argv[1:]:\n    try:\n        compile(open(f, encoding='utf-8').read(), f, 'exec')\n"
                 "    except SyntaxError as exc:\n        bad.append(f'{f}:{exc.lineno}: {exc.msg}')\nprint('\\n'.join(bad))\nsys.exit(1 if bad else 0)")
        r = subprocess.run([oldest, "-c", probe, *every], cwd=ROOT, capture_output=True, text=True, check=False)
        ok = r.returncode == 0
        print(f"  {'ok  ' if ok else 'FAIL'} python{MIN_PYTHON} compiles every Python file of the repository — tracked, or new and not ignored ({len(every)})  {r.stdout.strip()[:3000]}")
        failed += 0 if ok else 1

    print(f"\n{'FAIL' if failed else 'PASS'}: engine lint {'has findings' if failed else 'clean'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
