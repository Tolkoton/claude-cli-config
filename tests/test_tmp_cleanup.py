#!/usr/bin/env python3
"""A suite removes only the temporary directories it made itself (board 735).

Three suites used to end with `rmtree` over every directory in the shared temporary directory whose name has their
prefix — `simplifier-*`, `budget-*`, `signals-*` — and so deleted the directories of another run of the same suite
going on at the same time (the Stop gate's, a second clone's): that run then failed with FileNotFoundError. Now each
makes its directories inside one of its own and removes that one. Pinned two ways:

- in the source: no suite under tests/ deletes what a glob over the shared temporary directory found;
- for real: two instances of test_simplifier and the other two suites run at the same time beside directories that
  carry their prefixes and belong to nobody here; every run is green and every such directory is still there.

Run:   python3 tests/test_tmp_cleanup.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUITES = ("test_simplifier.py", "test_simplifier.py", "test_complexity_budget.py", "test_simplify_signals.py")
PREFIXES = ("simplifier-", "budget-", "signals-")
SHARED_GLOB = re.compile(r"gettempdir\(\)\)\s*\.glob\(")
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


me = Path(__file__).name
found = [f"{p.name}:{n}" for p in sorted((ROOT / "tests").glob("*.py")) if p.name != me
         for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if SHARED_GLOB.search(line)]
check("no suite deletes what a glob over the shared temporary directory found", found == [], found)

decoys = [Path(tempfile.mkdtemp(prefix=f"{prefix}someone-else-")) for prefix in PREFIXES]
for decoy in decoys:
    (decoy / "keep.txt").write_text("another run's file\n", encoding="utf-8")
runs = [subprocess.Popen([sys.executable, str(ROOT / "tests" / suite)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True) for suite in SUITES]
results = [(suite, run.communicate()[0], run.returncode) for suite, run in zip(SUITES, runs, strict=True)]
for suite, output, code in results:
    check(f"{suite}, run beside the others: green", code == 0, output.strip().splitlines()[-3:])
check("two instances of test_simplifier at once: neither removed the other's directories (both green above)",
      [code for suite, _, code in results if suite == "test_simplifier.py"] == [0, 0])
check("every directory with a suite's prefix that the suites did not make is still there, its file in it",
      all((d / "keep.txt").is_file() for d in decoys), [str(d) for d in decoys if not (d / "keep.txt").is_file()])
for decoy in decoys:
    shutil.rmtree(decoy, ignore_errors=True)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
