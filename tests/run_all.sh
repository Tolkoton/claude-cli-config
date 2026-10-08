#!/usr/bin/env bash
# Run every suite under tests/ and print one line per suite; exit 1 if any failed.
#
#   bash tests/run_all.sh            # everything (the check before a tag)
#   bash tests/run_all.sh --fast     # only the suites in tests/fast-suites.txt (the Stop gate)
#   bash tests/run_all.sh --list     # print the suites the given mode would run, run nothing
#   bash tests/run_all.sh deny       # only suites whose name contains "deny"
#   bash tests/run_all.sh --jobs 1   # one suite at a time (the default: one per processor)
#
# WHY --fast: the Stop hook runs TEST_CMD at the end of every turn where a .py or .sh file
# changed. The full set takes over two minutes, which is a tax on every such turn; the fast
# subset keeps the deterministic, sub-second checks on the gate and leaves the slow ones
# (real sessions, real sandboxes, the installer) to the pre-tag run. The subset is a list
# file, so adding a suite to the gate is one line with a measured time next to it.
#
# THE MACHINE RECORD (board 035). A run of the whole set or of the whole fast subset — not a
# filtered one — leaves .claude/state/health/tests-full.json or tests-fast.json: the time (UTC),
# the commit, whether the tree had uncommitted changes, how many suites ran and how many were
# green, the red ones by name. The review's «Здоров'я» reads the fact from there, not from what
# an agent wrote about it. ENGINE_HEALTH_DIR names another directory (the suites use it).
#
# IN PARALLEL (board 087). The suites are independent — each builds its own throwaway
# repositories — so as many run at once as the machine has processors (--jobs N or
# ENGINE_TEST_JOBS says otherwise). What is printed and recorded does not depend on it: one line
# per suite in the order of the list, the same verdicts, the same exit code. A line appears when
# its suite and every suite before it have finished. The longest suites of the previous run start
# first, so that the last minutes are not one long suite running alone; on a terminal a count of
# the finished suites is kept on stderr meanwhile. The record carries the wall time of the run
# (`seconds`), the number of jobs and the time of every suite. The file is read as it runs: do
# not edit it during a run.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.." || exit 2
FILTER=""; FAST=0; LIST=0; JOBS="${ENGINE_TEST_JOBS:-}"; WANT_JOBS=0
for arg in "$@"; do
  if [ "$WANT_JOBS" -eq 1 ]; then JOBS="$arg"; WANT_JOBS=0; continue; fi
  case "$arg" in
    --jobs) WANT_JOBS=1 ;;
    --jobs=*) JOBS="${arg#--jobs=}" ;;
    --fast) FAST=1 ;;
    --list) LIST=1 ;;
    --*) echo "run_all.sh: unknown option '$arg'" >&2; exit 2 ;;
    *) FILTER="$arg" ;;
  esac
done
[ "$WANT_JOBS" -eq 0 ] || { echo "run_all.sh: --jobs needs a number" >&2; exit 2; }
case "$JOBS" in
  "") JOBS=0 ;;   # one per processor
  *[!0-9]*|0*) echo "run_all.sh: the number of jobs must be a whole number from 1, not '$JOBS'" >&2; exit 2 ;;
esac
if [ "$FAST" -eq 1 ]; then
  SUITES=()
  while IFS= read -r line; do
    line="${line%%#*}"; line="${line//[[:space:]]/}"
    [ -n "$line" ] || continue
    if [ ! -f "tests/$line" ]; then echo "run_all.sh: tests/fast-suites.txt names a missing suite: $line" >&2; exit 2; fi
    SUITES+=("tests/$line")
  done < tests/fast-suites.txt
  [ ${#SUITES[@]} -gt 0 ] || { echo "run_all.sh: tests/fast-suites.txt names no suite" >&2; exit 2; }
else
  SUITES=(tests/test_*.py)
fi
CHOSEN=()
for t in "${SUITES[@]}"; do
  case "$t" in *"$FILTER"*) ;; *) continue ;; esac
  if [ "$LIST" -eq 1 ]; then echo "$t"; else CHOSEN+=("$t"); fi
done
[ "$LIST" -eq 1 ] && exit 0
MODE=full; [ "$FAST" -eq 1 ] && MODE=fast
RECORD=1; [ -z "$FILTER" ] || RECORD=0
RUN=$(cat <<'RUN'
import json, os, subprocess, sys, threading, time
from datetime import UTC, datetime
from pathlib import Path

folder, mode, jobs, whole, suites = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]) or os.cpu_count() or 1, sys.argv[4] == "1", sys.argv[5:]
try:
    before = json.loads((folder / f"tests-{mode}.json").read_text(encoding="utf-8")).get("suite_seconds", {})
except (OSError, ValueError, AttributeError):
    before = {}
# The start order: a suite the previous run did not time first, then the longest. One job keeps the order of the list.
queue = list(range(len(suites))) if jobs == 1 or not isinstance(before, dict) else sorted(
    range(len(suites)), key=lambda i: (suites[i] in before, -float(before.get(suites[i]) or 0), i))
done: dict[int, tuple[int, str, float]] = {}
lock, finished = threading.Lock(), threading.Condition()


def work() -> None:
    while True:
        with lock:
            if not queue:
                return
            i = queue.pop(0)
        began = time.monotonic()
        try:
            proc = subprocess.run(["python3", suites[i]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            rc, last = proc.returncode, proc.stdout.decode("utf-8", "replace").rstrip("\n").split("\n")[-1]
        except OSError as error:   # no python3 to start: the suite is red, and the run goes on
            rc, last = 127, str(error)
        with finished:
            done[i] = (rc, last, time.monotonic() - began)
            if sys.stderr.isatty():   # a person is watching: the lines wait for their turn, the count does not
                print(f"\r  {len(done)} of {len(suites)} suites finished", end="\n" if len(done) == len(suites) else "", file=sys.stderr, flush=True)
            finished.notify()


began = time.monotonic()
for _ in range(min(jobs, len(suites))):
    threading.Thread(target=work, daemon=True).start()
red = []
for i, suite in enumerate(suites):
    with finished:
        finished.wait_for(lambda: i in done)
    rc, last, _ = done[i]
    print(f"  {'ok  ' if rc == 0 else 'FAIL'}  {suite:<45} {last}", flush=True)
    red += [suite] * (rc != 0)
seconds = round(time.monotonic() - began, 1)
if whole:
    try:
        git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, check=False).stdout.strip()
        record = {"what": "tests/run_all.sh", "mode": mode, "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
                  "suites": len(suites), "green": len(suites) - len(red), "red": red, "seconds": seconds, "jobs": jobs,
                  "suite_seconds": {suite: round(done[i][2], 1) for i, suite in enumerate(suites)}}
        folder.mkdir(parents=True, exist_ok=True)
        scratch = folder / f"tests-{mode}.json.tmp"
        scratch.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        scratch.replace(folder / f"tests-{mode}.json")
    except OSError:
        print("run_all.sh: the machine record was not written", file=sys.stderr)
print()
print(f"FAIL: {len(red)} of {len(suites)} suites red" if red else f"PASS: {len(suites)} suites green" + (" (fast subset)" if mode == "fast" else ""))
sys.exit(1 if red else 0)
RUN
)
python3 -c "$RUN" "${ENGINE_HEALTH_DIR:-.claude/state/health}" "$MODE" "$JOBS" "$RECORD" ${CHOSEN[@]+"${CHOSEN[@]}"}
