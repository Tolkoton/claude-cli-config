#!/usr/bin/env bash
# Run every suite under tests/ and print one line per suite; exit 1 if any failed.
#
#   bash tests/run_all.sh            # everything
#   bash tests/run_all.sh deny       # only suites whose name contains "deny"
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.." || exit 2
FILTER="${1:-}"
fails=0; n=0
for t in tests/test_*.py; do
  case "$t" in *"$FILTER"*) ;; *) continue ;; esac
  n=$((n+1))
  out=$(python3 "$t" 2>&1); rc=$?
  last=$(printf '%s\n' "$out" | tail -1)
  if [ $rc -eq 0 ]; then printf '  ok    %-45s %s\n' "$t" "$last"; else printf '  FAIL  %-45s %s\n' "$t" "$last"; fails=$((fails+1)); fi
done
echo
[ $fails -eq 0 ] && echo "PASS: $n suites green" || echo "FAIL: $fails of $n suites red"
exit $(( fails > 0 ))
