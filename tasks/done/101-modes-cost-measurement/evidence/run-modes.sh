#!/usr/bin/env bash
# Board 101: one small task on the reference project, once in each mode, through the real runner.
#
#   bash tasks/done/101-modes-cost-measurement/evidence/run-modes.sh <engine-ref> <work-dir> [mode…]
#
#   <engine-ref>  commit of this repository the sandboxes are built from
#   <work-dir>    directory outside this repository; one sandbox per mode is made in it
#   mode          sketch | solo | pipeline (default: all three, in parallel) | sketch-question
#                 (the same subject worded as the one question a sketch answers:
#                 sandbox-task-question.md, mode ескіз)
#
# Each sandbox is `evals/make_sandbox.sh` + the branch unattended/work (no remote) + the same
# task file (sandbox-task.md beside this script) with one line `Режим:` — nothing else differs.
# The session is started by the sandbox's own `board-runner.sh --once --no-push`, with none of the
# calling session's CLAUDE_* / BOARD_* variables, so no budget cap and no foreign project root
# reach it. What it cost is in <work-dir>/<mode>/.claude/state/board/ (costs.json, logs/).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$(git -C "$HERE" rev-parse --show-toplevel)"
[ $# -ge 2 ] || { echo "usage: run-modes.sh <engine-ref> <work-dir> [sketch|solo|pipeline …]" >&2; exit 2; }
REF="$1"; WORK="$2"; shift 2
[ $# -gt 0 ] || set -- sketch solo pipeline
mkdir -p "$WORK"; WORK="$(cd "$WORK" && pwd)"

mode_word() { case "$1" in sketch|sketch-question) echo ескіз ;; solo) echo соло ;; pipeline) echo конвеєр ;; *) return 1 ;; esac; }

run_one() {
  local mode="$1" word box="$WORK/$1" task="$HERE/sandbox-task.md"
  [ "$mode" != sketch-question ] || task="$HERE/sandbox-task-question.md"
  word="$(mode_word "$mode")" || { echo "unknown mode '$mode'" >&2; return 2; }
  bash "$ENGINE/evals/make_sandbox.sh" "$REF" "$box" > "$WORK/$mode.setup.log" 2>&1
  mkdir -p "$WORK/$mode-inbox"
  (
    cd "$box"
    git config user.name "engine-sandbox"; git config user.email "sandbox@example.invalid"
    git switch -q -c unattended/work
    # The runner would otherwise place its own weekly-care and cleanup tasks beside the measured one.
    sed -i -e 's/^MAINTAIN_EVERY_DAYS=.*/MAINTAIN_EVERY_DAYS="0"/' \
           -e 's/^CLEANUP_EVERY_DAYS=.*/CLEANUP_EVERY_DAYS="0"/' .claude/project.env
    sed "s/^Режим: .*/Режим: $word/" "$task" > tasks/todo/010-split-evenly.md
    git add -A
    git commit -q -m "sandbox: the measured task, mode $word"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$WORK/$mode.started"
    env -i HOME="$HOME" PATH="$PATH" USER="${USER:-}" LOGNAME="${LOGNAME:-}" LANG="${LANG:-C.UTF-8}" \
      SHELL="${SHELL:-/bin/bash}" TERM="${TERM:-dumb}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-}" \
      BOARD_INBOX="$WORK/$mode-inbox" \
      bash .claude/unattended/board-runner.sh --once --no-push > "$WORK/$mode.runner.log" 2>&1 || true
    date -u +%Y-%m-%dT%H:%M:%SZ > "$WORK/$mode.ended"
  )
  echo "$mode: $(cat "$box/.claude/state/board/status" 2>/dev/null)"
}

pids=()
for mode in "$@"; do run_one "$mode" & pids+=($!); done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
