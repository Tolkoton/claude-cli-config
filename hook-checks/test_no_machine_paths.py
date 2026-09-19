#!/usr/bin/env python3
"""No executable file may name a path on somebody's machine.

`test_overseer_continue.py` once hard-coded its author's home directory. Everywhere
else the hook was never found, so six of its eight cases passed vacuously and nobody
noticed for weeks. This check makes that class of mistake loud.

Scope is CODE that gets executed or shipped: hooks, harness scripts, tests, evals
scripts and the installer. Prose (docs, ledgers, spike notes) and scenario DATA may
mention paths — a scenario that feeds a hook `/home/someone/.ssh/id_ed25519` is
describing an input, not depending on a machine.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_GLOBS = (
    ".claude/hooks/*.sh", ".claude/hooks/*.py",
    ".claude/unattended/*.sh", ".claude/unattended/*.py",
    ".claude/skills/*/scripts/*",
    "hook-checks/*.py", "evals/*.py", "evals/*.sh", "install.sh",
)
# /Users/<name>/ (macOS) or /home/<name>/ (Linux). `$HOME`, `~` and relative paths are fine.
# The name must start with a letter or digit, so an elided example such as /home/.../src
# in a comment is not mistaken for a real directory.
MACHINE_PATH = re.compile(r"/(?:Users|home)/[A-Za-z0-9][A-Za-z0-9._-]*/")
# This file has to spell the patterns out to describe them.
SELF = Path(__file__).resolve()

tracked = subprocess.run(
    ["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard", "--", *CODE_GLOBS],
    capture_output=True, text=True, check=True,
).stdout.split("\n")

failures = []
checked = 0
for rel in filter(None, tracked):
    path = ROOT / rel
    if path.resolve() == SELF or not path.is_file():
        continue
    checked += 1
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        continue
    for number, line in enumerate(lines, 1):
        if MACHINE_PATH.search(line):
            failures.append(f"{rel}:{number}: {line.strip()[:120]}")

if failures:
    print("FAIL: machine-specific absolute paths in executable files:")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)
print(f"PASS: no machine-specific paths in {checked} executable files")
