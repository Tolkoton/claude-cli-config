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
fails=0; n=0
for t in "${SUITES[@]}"; do
  case "$t" in *"$FILTER"*) ;; *) continue ;; esac
  n=$((n+1))
  if [ "$LIST" -eq 1 ]; then echo "$t"; continue; fi
  out=$(python3 "$t" 2>&1); rc=$?
  last=$(printf '%s\n' "$out" | tail -1)
  if [ $rc -eq 0 ]; then printf '  ok    %-45s %s\n' "$t" "$last"; else printf '  FAIL  %-45s %s\n' "$t" "$last"; fails=$((fails+1)); fi
done
[ "$LIST" -eq 1 ] && exit 0
echo
[ $fails -eq 0 ] && echo "PASS: $n suites green${FAST:+}$([ "$FAST" -eq 1 ] && echo ' (fast subset)')" || echo "FAIL: $fails of $n suites red"
exit $(( fails > 0 ))
