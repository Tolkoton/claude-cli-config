#!/usr/bin/env python3
"""The engine's own Python is lint-clean and strictly typed.

The hooks and the unattended harness are shipped into every project and run there without
a review step; a finding ruff or mypy would have raised is a defect every project inherits.
Package 3b found sixteen such findings that had accumulated in four hooks because nothing
ran the tools over .claude/. This runs them:

    ruff check --isolated .claude          (the engine's rule set, not a project's — .claude/ruff.toml
                                            excludes everything so a PROJECT'S ruff never judges the
                                            engine; --isolated is how the engine judges itself)
    mypy --strict <every .py under .claude>

Through `uvx` when available, else `ruff` / `mypy` on PATH. Without either the check FAILS
with the reason rather than passing vacuously: a lint gate that cannot run has not run.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / ".claude"


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


def runner(tool: str) -> list[str] | None:
    if shutil.which("uvx"):
        return ["uvx", tool]
    if shutil.which(tool):
        return [tool]
    return None


def main() -> int:
    failed = 0
    py_files = engine_python()
    print(f"  {len(py_files)} engine-owned Python files under .claude/")

    ruff = runner("ruff")
    if ruff is None:
        print("  FAIL ruff: neither `uvx` nor `ruff` is on PATH — the engine cannot be linted here")
        failed += 1
    else:
        r = subprocess.run([*ruff, "check", "--isolated", "--output-format", "concise", *py_files], cwd=ROOT, capture_output=True, text=True, check=False)
        ok = r.returncode == 0
        print(f"  {'ok  ' if ok else 'FAIL'} ruff check --isolated <engine Python>  {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''}")
        if not ok:
            print(r.stdout[:3000])
            failed += 1

    mypy = runner("mypy")
    if mypy is None:
        print("  FAIL mypy: neither `uvx` nor `mypy` is on PATH — the engine cannot be type-checked here")
        failed += 1
    elif py_files:
        r = subprocess.run([*mypy, "--strict", *py_files], cwd=ROOT, capture_output=True, text=True, check=False)
        ok = r.returncode == 0
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[:200]
        print(f"  {'ok  ' if ok else 'FAIL'} mypy --strict (engine Python)  {last}")
        if not ok:
            print(r.stdout[:3000])
            failed += 1

    print(f"\n{'FAIL' if failed else 'PASS'}: engine lint {'has findings' if failed else 'clean'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
