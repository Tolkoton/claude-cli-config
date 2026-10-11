#!/usr/bin/env python3
"""Board 104: every file that conflicts in the replay of board 083, not only the six most frequent.

    python3 .engine/artifacts/104-registry/conflicts.py [--union]

The same replay as .engine/artifacts/083-parallel/measure.py (task B merged as if it had started
1, 2 or 3 tasks earlier), with one line per conflicting file. With --union every merge gives
tests/fast-suites.txt `merge=union` (through core.attributesFile, a file beside the scratch clone:
the historical commits do not carry the line), and the registry each merge leaves is read the way
tests/run_all.sh reads it: a suite named twice, a line for a suite the merged tree does not have.
Writes nothing in this repository.
"""
import collections
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
UNION = "--union" in sys.argv
if UNION:   # measure.py reads its branch from the first argument
    sys.argv.remove("--union")
spec = importlib.util.spec_from_file_location("measure", HERE.parent / "083-parallel" / "measure.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
git = measure.git
REGISTRY = "tests/fast-suites.txt"


def main():
    start, end, order, _ = measure.ranges()
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="board104-"))
    hot = collections.Counter()
    merges = twice = missing = 0
    attributes = pathlib.Path(tempfile.mkdtemp(prefix="board104-attr-")) / "attributes"
    attributes.write_text(f"{REGISTRY} merge=union\n" if UNION else "")
    try:
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(measure.ROOT), str(scratch)], check=True)
        for back in (1, 2, 3):
            for i in range(back, len(order)):
                a, b = order[i - back], order[i]
                if git("checkout", "-q", "-f", "--detach", start[a], cwd=scratch).returncode:
                    continue
                git("clean", "-qfd", cwd=scratch)
                merged = git("-c", f"core.attributesFile={attributes}", "merge-recursive", start[b], "--", start[a], end[b], cwd=scratch)
                if merged.returncode not in (0, 1):
                    continue
                hot.update(f for f in git("diff", "--name-only", "--diff-filter=U", cwd=scratch).stdout.split()
                           if not measure.BOARD_MOVE.match(f) and not measure.JOURNAL.match(f))
                if UNION and (scratch / REGISTRY).is_file() and git("diff", "--quiet", start[b], end[b], "--", REGISTRY).returncode:
                    merges += 1
                    names = [line.split("#")[0].strip() for line in (scratch / REGISTRY).read_text(encoding="utf-8").splitlines()]
                    names = [n for n in names if n]
                    gone = sorted({n for n in names if not (scratch / "tests" / n).is_file()})
                    again = sorted({n for n in names if names.count(n) > 1})
                    twice += bool(again)
                    missing += bool(gone)
                    if gone or again:
                        print(f"   {a} + {b}: twice {again}, missing {gone}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(attributes.parent, ignore_errors=True)
    total = sum(hot.values())
    print(f"conflicts outside journals and board moves, N=1..3 together: {total} in {len(hot)} files")
    for name, n in hot.most_common():
        print(f"{n:4}  {name}")
    if UNION:
        print(f"merges in which task B changed {REGISTRY}: {merges}; the merged list names a suite twice in {twice}, "
              f"a suite the merged tree does not have in {missing}")


if __name__ == "__main__":
    main()
