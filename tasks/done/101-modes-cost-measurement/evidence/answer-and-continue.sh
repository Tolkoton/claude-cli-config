#!/usr/bin/env bash
# Board 101: a sandbox run of run-modes.sh ended in blocked/ with a question — answer it the way
# an owner would (a copy of the task with the answer, through the sandbox's own inbox) and let
# the sandbox's runner take the task once more.
#
#   bash tasks/done/101-modes-cost-measurement/evidence/answer-and-continue.sh <work-dir> <mode> <answer>
#
# The inbox is the sandbox's (<work-dir>/<mode>-inbox), never the real board's. The runner's
# costs.json goes on counting the same task, so the cost before the answer is the figure the
# first run left and the cost after it is the difference.
set -euo pipefail

[ $# -eq 3 ] || { echo "usage: answer-and-continue.sh <work-dir> <mode> <answer>" >&2; exit 2; }
WORK="$(cd "$1" && pwd)"; mode="$2"; answer="$3"
box="$WORK/$mode"; name=010-split-evenly.md
[ -f "$box/tasks/blocked/$name" ] || { echo "$box/tasks/blocked/$name is not there" >&2; exit 2; }

python3 - "$box/tasks/blocked/$name" "$WORK/$mode-inbox/$name" "$answer" <<'PY'
import re
import sys

src, dst, answer = sys.argv[1:]
text = open(src, encoding="utf-8").read()
text, n = re.subn(r"(?m)^(\s*Відповідь:)[ \t]*$", lambda m: f"{m.group(1)} {answer}", text)
if n != 1:
    sys.exit(f"expected one empty «Відповідь:» line, found {n}")
open(dst, "w", encoding="utf-8").write(text)
PY

cd "$box"
date -u +%Y-%m-%dT%H:%M:%SZ > "$WORK/$mode.continued"
env -i HOME="$HOME" PATH="$PATH" USER="${USER:-}" LOGNAME="${LOGNAME:-}" LANG="${LANG:-C.UTF-8}" \
  SHELL="${SHELL:-/bin/bash}" TERM="${TERM:-dumb}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-}" \
  BOARD_INBOX="$WORK/$mode-inbox" \
  bash .claude/unattended/board-runner.sh --once --no-push > "$WORK/$mode.runner-2.log" 2>&1 || true
date -u +%Y-%m-%dT%H:%M:%SZ > "$WORK/$mode.ended"
echo "$mode: $(cat "$box/.claude/state/board/status" 2>/dev/null)"
