#!/usr/bin/env bash
# worker.sh <clone> <session> [<session>...] — run the sessions in order, one mutant at a time, in the clone.
clone="$1"; shift
cd "$clone" || exit 2
for s in "$@"; do
  [ -f /tmp/mut085/STOP ] && { echo "stop flag: not starting $s"; break; }
  n="${s%%.*}"
  echo "$(date -u +%H:%M:%S) start $s"
  uvx cosmic-ray exec "/tmp/mut085/sessions/$n.toml" "/tmp/mut085/sessions/$s.sqlite" >>"/tmp/mut085/log/exec.$s.log" 2>&1
  echo "$(date -u +%H:%M:%S) done $s rc=$?"
  git checkout -q -- . 2>/dev/null
done
