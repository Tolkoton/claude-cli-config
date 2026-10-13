#!/usr/bin/env python3
"""A suite removes only the temporary directories it made itself (board 735).

Three suites used to end with `rmtree` over every directory in the shared temporary directory whose name has their
prefix — `simplifier-*`, `budget-*`, `signals-*` — and so deleted the directories of another run of the same suite
going on at the same time (the Stop gate's, a second clone's): that run then failed with FileNotFoundError. Now each
makes its directories inside one of its own and removes that one. Pinned two ways:

- in the source: no suite under tests/ lists the shared temporary directory, however it writes that (board 767: the
  check is itself checked on suites planted for it, one per way of listing, beside suites that list their own);
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
# The shared temporary directory as a suite can write it, and the calls that list a directory. A line with both lists the
# shared directory; so does a listing of a name the line above bound to that directory or to a pattern inside it.
SHARED = r"""gettempdir\(\)|\btempfile\.tempdir\b|["'](?:/var)?/tmp/?["']"""
SHARED_DIR = re.compile(rf"""{SHARED}|["'](?:/var)?/tmp/[^"']*[*?]""")
LISTING = re.compile(r"\b(?:i?glob|rglob|iterdir|listdir|scandir|walk)\(")
NAMED_DIR = re.compile(rf"^\s*(\w+)\s*=\s*(?:(?:\w+\.)*Path\()?\s*(?:\w+\.)?(?:{SHARED})\s*\)?\s*$")
NAMED_PATTERN = re.compile(rf"""^\s*(\w+)\s*=.*(?:{SHARED}).*["'][^"']*[*?]""")
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def shared_listings(tests: Path, skip: str = "") -> list[str]:
    """Every line of a suite in `tests` that lists the shared temporary directory, as `file:line`."""
    found = []
    for path in sorted(tests.glob("*.py")):
        names: set[str] = set()
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines() if path.name != skip else [], 1):
            named = NAMED_DIR.match(line) or NAMED_PATTERN.match(line)
            if LISTING.search(line) and (SHARED_DIR.search(line) or any(re.search(rf"\b{name}\b", line) for name in names)):
                found.append(f"{path.name}:{n}")
            elif named:
                names.add(named[1])
    return found


found = shared_listings(ROOT / "tests", skip=Path(__file__).name)
check("no suite lists the shared temporary directory", found == [], found)

# The source check itself, on suites written for it: each way of listing the shared directory, one per file (board 767).
LISTS_SHARED = {
    "path_glob": "for p in Path(tempfile.gettempdir()).glob('x-*'):\n    shutil.rmtree(p)\n",
    "glob_join": "for p in glob.glob(os.path.join(tempfile.gettempdir(), 'simplifier-*')):\n    shutil.rmtree(p)\n",
    "literal_path_glob": "for p in Path('/tmp').glob('budget-*'):\n    shutil.rmtree(p)\n",
    "literal_glob": 'for p in glob.glob("/tmp/signals-*"):\n    shutil.rmtree(p)\n',
    "iglob_fstring": 'for p in glob.iglob(f"{tempfile.gettempdir()}/x-*"):\n    shutil.rmtree(p)\n',
    "rglob": "left = list(pathlib.Path(tempfile.gettempdir()).rglob('x-*'))\n",
    "iterdir": "left = [p for p in Path(tempfile.gettempdir()).iterdir() if p.name.startswith('x-')]\n",
    "listdir": "left = [n for n in os.listdir(tempfile.gettempdir()) if n.startswith('x-')]\n",
    "scandir": "left = [e.path for e in os.scandir('/tmp') if e.name.startswith('x-')]\n",
    "walk": "for top, dirs, files in os.walk(tempfile.gettempdir()):\n    break\n",
    "tempdir_attribute": "left = glob.glob(tempfile.tempdir + '/x-*')\n",
    "var_tmp": "left = list(Path('/var/tmp').glob('x-*'))\n",
    "named_directory": "TMP = Path(tempfile.gettempdir())\nleft = list(TMP.glob('x-*'))\n",
    "named_pattern": "pattern = os.path.join(tempfile.gettempdir(), 'x-*')\nfor p in glob.glob(pattern):\n    shutil.rmtree(p)\n",
}
LISTS_ITS_OWN = {
    "own_directory": "OWN = Path(tempfile.mkdtemp(prefix='x-'))\nleft = list(OWN.glob('x-*'))\nshutil.rmtree(OWN)\n",
    "own_under_shared": "OWN = Path(tempfile.gettempdir()) / f'x-{os.getpid()}'\nOWN.mkdir()\nleft = list(OWN.iterdir())\n",
    "tmpdir_handed_on": "env = dict(os.environ, TMPDIR=str(work / 'tmp'))\nleft = list((work / 'tmp').glob('x-*'))\n",
    "paths_as_text": "sandbox = Path('/tmp/sandbox-x')\nok = d.startswith(('~/', '/tmp/'))\nseeds = sorted(root.rglob('*.md'))\n",
}
planted = Path(tempfile.mkdtemp(prefix="tmp-cleanup-"))
for name, body in (LISTS_SHARED | LISTS_ITS_OWN).items():
    (planted / f"test_{name}.py").write_text(body, encoding="utf-8")
flagged = {entry.split(":")[0] for entry in shared_listings(planted)}
for name in LISTS_SHARED:
    check(f"the source check flags a suite that lists the shared temporary directory: {name}", f"test_{name}.py" in flagged,
          LISTS_SHARED[name])
check("... and no suite that lists a directory of its own", flagged <= {f"test_{name}.py" for name in LISTS_SHARED}, sorted(flagged))
check("... and it names the line: the listing, not the line that named the directory",
      [e for e in shared_listings(planted) if e.startswith("test_named_")] == ["test_named_directory.py:2", "test_named_pattern.py:2"],
      shared_listings(planted))
check("... and it leaves out the one file it is told to", "test_path_glob.py" not in
      {e.split(":")[0] for e in shared_listings(planted, skip="test_path_glob.py")})
shutil.rmtree(planted)

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
