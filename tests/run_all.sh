#!/usr/bin/env bash
# Run every suite under tests/ and print one line per suite; exit 1 if any failed.
#
#   bash tests/run_all.sh            # everything (the check before a tag; about 135 s)
#   bash tests/run_all.sh --fast     # only the suites in tests/fast-suites.txt (the Stop gate; under 20 s)
#   bash tests/run_all.sh --list     # print the suites the given mode would run, run nothing
#   bash tests/run_all.sh deny       # only suites whose name contains "deny"
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
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.." || exit 2
FILTER=""; FAST=0; LIST=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --list) LIST=1 ;;
    --*) echo "run_all.sh: unknown option '$arg'" >&2; exit 2 ;;
    *) FILTER="$arg" ;;
  esac
done
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
fails=0; n=0; RED=()
for t in "${SUITES[@]}"; do
  case "$t" in *"$FILTER"*) ;; *) continue ;; esac
  n=$((n+1))
  if [ "$LIST" -eq 1 ]; then echo "$t"; continue; fi
  out=$(python3 "$t" 2>&1); rc=$?
  last=$(printf '%s\n' "$out" | tail -1)
  if [ $rc -eq 0 ]; then printf '  ok    %-45s %s\n' "$t" "$last"; else printf '  FAIL  %-45s %s\n' "$t" "$last"; fails=$((fails+1)); RED+=("$t"); fi
done
[ "$LIST" -eq 1 ] && exit 0
if [ -z "$FILTER" ]; then
  MODE=full; [ "$FAST" -eq 1 ] && MODE=fast
  python3 - "${ENGINE_HEALTH_DIR:-.claude/state/health}" "$MODE" "$n" "$fails" ${RED[@]+"${RED[@]}"} <<'RECORD' || echo "run_all.sh: the machine record was not written" >&2
import json, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path

folder, mode, suites, red = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, check=False).stdout.strip()
record = {"what": "tests/run_all.sh", "mode": mode, "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
          "suites": suites, "green": suites - red, "red": sys.argv[5:]}
folder.mkdir(parents=True, exist_ok=True)
scratch = folder / f"tests-{mode}.json.tmp"
scratch.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
scratch.replace(folder / f"tests-{mode}.json")
RECORD
fi
echo
[ $fails -eq 0 ] && echo "PASS: $n suites green${FAST:+}$([ "$FAST" -eq 1 ] && echo ' (fast subset)')" || echo "FAIL: $fails of $n suites red"
exit $(( fails > 0 ))
