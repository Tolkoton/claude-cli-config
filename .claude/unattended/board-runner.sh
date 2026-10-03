#!/usr/bin/env bash
# The board runner: works through tasks/ one task at a time, each in a fresh conversation.
#
#   bash .claude/unattended/board-runner.sh            run until nothing can move, then stop
#   bash .claude/unattended/board-runner.sh --once     one task, then stop
#   bash .claude/unattended/board-runner.sh --no-push  never push (somebody else sends the branch)
#   bash .claude/unattended/board-runner.sh --retry    give the task in doing/ a fresh clock and count
#   bash .claude/unattended/board-runner.sh --status   print the status line and the summary, run nothing
#
# WHAT IT DOES, in the order it does it (tasks/README.md is the board's manual):
#   before every task   fetch and `pull --rebase` the work branch — new tasks and the owner's
#                       answers arrive this way; take new files from the inbox into tasks/todo/
#                       (one commit); close the gate escalations the owner answered «закрити»
#                       and take the actions the owner answered «так» (see below); move answered tasks from tasks/blocked/ back to todo/ (one commit)
#   the task            the first in todo/ whose dependencies are in done/ goes to doing/ in a
#                       commit of its own, then `claude -p` in a FRESH conversation
#   while it is open    a session that ended with the task still in doing/ is continued
#                       (--resume); a usage-limit notice waits 15 minutes and is not an attempt
#   the task is closed  when the agent moved it to done/ or blocked/. Then: push, next task
#   it stops            three attempts in a row without a new commit; a task older than twelve
#                       hours; the task's budget spent; todo/ empty or everything left waiting
#                       for the owner — always with a summary
#
# WHAT THE OPERATOR READS, in .claude/state/board/:
#   status      one line: state=<running|waiting-limit|idle|waiting-owner|stopped|stalled|deadline|error>
#               task=<name|-> since=<UTC> [reason=<word>]
#   events.log  one UTC line per event      costs.json  per task: attempts, sessions, cost
#   summary.md  written at every stop       logs/       the raw output of every attempt
# Exit 0: idle, waiting-owner, stopped (--once). Exit 1: stalled, deadline, error.
#
# A GATE QUESTION (tasks/blocked/9NN-gate-escalation-*.md, written by gate.py when the Stop gate
# gives up) is the one task the runner finishes itself. It commits and pushes the question as
# soon as it appears; when the owner's answer «закрити» ARRIVES — by the pull or through the
# inbox — it runs `gate.py --close-escalation <stamp>` and moves the task to done/ with a
# two-line report. An answer that was already in the checkout before the pull was written on
# this machine, where the writer is the agent the gate judged: it is wiped and asked again.
# gate.py refuses the command inside a Claude Code session, so a runner an agent starts closes
# nothing.
#
# AN OWNER ACTION (board 008) is what the owner approved with «так» under a question that offers
# it (`Дія виконавця: <action> <sha256>`, see board.py). The runner takes it, never the agent,
# and only from the short list: `apply-settings` (owner_action.py: the settings proposal is
# copied over .claude/settings.json and its test run) and the gate's `close-escalation` above.
# The same rule for where the answer came from applies. The offer is then replaced by the
# outcome and the task returns to todo/ for the agent to check and report.
#
# THE RUNNER MOVES A TASK INTO doing/; ONLY THE AGENT MOVES IT OUT. Gate questions apart, the
# runner writes no report and judges no work. It commits nothing but tasks/ and, after
# apply-settings, .claude/settings.json — and only on the work branch, which must
# be an unattended/* branch: hooks do not see a commit made from a script, so the check is here.
#
# Every number is an environment variable, so the tests run in seconds:
#   BOARD_BRANCH (unattended/work)  BOARD_REMOTE (origin)  BOARD_INBOX (~/engine-ops/tasks-inbox)
#   BOARD_CLAUDE (claude)  BOARD_LIMIT_WAIT_SEC (900)  BOARD_TASK_MAX_SEC (43200)
#   BOARD_STALL_ATTEMPTS (3)  BOARD_PAUSE_SEC (30, between attempts)
#   BOARD_MAX_USD (empty = no cap): the most one task may cost; passed on as --max-budget-usd

set -uo pipefail

ONCE=0; PUSH=1; RETRY=0; STATUS_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --once) ONCE=1 ;;
    --no-push) PUSH=0 ;;
    --retry) RETRY=1 ;;
    --status) STATUS_ONLY=1 ;;
    *) echo "board-runner: unknown option '$arg' (see the head of this file)" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HERE/../.." && pwd)}"
cd "$PROJECT_ROOT" || exit 1

BRANCH="${BOARD_BRANCH:-unattended/work}"
REMOTE="${BOARD_REMOTE:-origin}"
INBOX="${BOARD_INBOX:-$HOME/engine-ops/tasks-inbox}"
CLAUDE_BIN="${BOARD_CLAUDE:-claude}"
LIMIT_WAIT="${BOARD_LIMIT_WAIT_SEC:-900}"
TASK_MAX="${BOARD_TASK_MAX_SEC:-43200}"
STALL_ATTEMPTS="${BOARD_STALL_ATTEMPTS:-3}"
PAUSE="${BOARD_PAUSE_SEC:-30}"
MAX_USD="${BOARD_MAX_USD:-}"

STATE="$PROJECT_ROOT/.claude/state/board"
MODE_FILE="$PROJECT_ROOT/.claude/state/overseer/mode"
MODE_BEFORE="$STATE/mode.before"
LOCK="$STATE/lock"
GATE_PY="$HERE/../hooks/gate.py"
ACCEPTED="$STATE/gate-accepted"   # answers that arrived from the owner: name, stamp, sha256
board() { python3 "$HERE/board.py" --root "$PROJECT_ROOT" "$@"; }
memo() { python3 "$HERE/board_state.py" "$STATE" "$@"; }

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
event() { echo "$(now) $*" >> "$STATE/events.log"; }
say() { echo "[board] $*"; }
status() {  # status <state> <task|-> [reason]
  echo "state=$1 task=$2 since=$(now)${3:+ reason=$3}" > "$STATE/status"
}

if [ "$STATUS_ONLY" -eq 1 ]; then
  cat "$STATE/status" 2>/dev/null || echo "state=never-ran"
  board summary
  exit 0
fi

mkdir -p "$STATE/logs" "$(dirname "$MODE_FILE")"

# --- one runner at a time. The lock holds the PID; a lock whose PID is gone is reclaimed. -------
if [ -f "$LOCK" ]; then
  HOLDER=$(cat "$LOCK" 2>/dev/null || echo "")
  if [ -n "$HOLDER" ] && kill -0 "$HOLDER" 2>/dev/null; then
    echo "board-runner: another runner is working here (pid $HOLDER); see $STATE/status" >&2
    exit 1
  fi
  event "lock-reclaimed pid=${HOLDER:-unknown}"
fi
echo $$ > "$LOCK"

# --- nobody is watching: say so for the lifetime of the runner, and put it back afterwards. -----
# A planning gate then parks instead of asking, and an ask-gated command is parked, not hung on.
# A leftover mode.before means a runner died without its trap (kill -9): heal first.
restore_mode() {
  [ -f "$MODE_BEFORE" ] || return 0
  if [ "$(cat "$MODE_BEFORE")" = "(absent)" ]; then rm -f "$MODE_FILE"; else cp "$MODE_BEFORE" "$MODE_FILE"; fi
  rm -f "$MODE_BEFORE"
}
restore_mode
if [ -f "$MODE_FILE" ]; then cp "$MODE_FILE" "$MODE_BEFORE"; else echo "(absent)" > "$MODE_BEFORE"; fi
echo unattended > "$MODE_FILE"
export CLAUDE_UNATTENDED_SESSION=1

CLAUDE_PID=""
cleanup() {
  if [ -n "$CLAUDE_PID" ]; then
    kill -TERM "$CLAUDE_PID" 2>/dev/null
    for _ in 1 2 3 4 5; do kill -0 "$CLAUDE_PID" 2>/dev/null || break; sleep 1; done
    kill -KILL "$CLAUDE_PID" 2>/dev/null
  fi
  restore_mode
  [ "$(cat "$LOCK" 2>/dev/null)" = "$$" ] && rm -f "$LOCK"
}
trap cleanup EXIT
trap 'event "killed"; status error "${TASK_NAME:--}" killed; exit 143' TERM INT

# finish <state> <task|-> <reason-word> <one sentence>: the summary, the status line, the exit code.
finish() {
  local state="$1" task="$2" reason="$3" sentence="$4" code=1
  case "$state" in idle|waiting-owner|stopped) code=0 ;; esac
  {
    echo "# Дошка: підсумок запуску"
    echo
    echo "- Час (UTC): $(now)"
    echo "- Стан: \`$state\` — $sentence"
    [ "$task" = "-" ] || echo "- Задача: \`$task\`"
    echo "- Гілка: \`$BRANCH\` на \`$(git rev-parse --short HEAD 2>/dev/null)\`"
    echo
    echo "## Дошка"
    echo
    board summary 2>&1 | sed 's/^/- /'
    echo
    echo "## Витрати"
    echo
    memo report 2>&1 | sed 's/^/- /'
  } > "$STATE/summary.md"
  status "$state" "$task" "$reason"
  event "stop $state $reason $task"
  say "$state ($reason): $sentence"
  say "summary: $STATE/summary.md"
  exit "$code"
}

# --- the branch. Commits are legal on unattended/* only; this runner works on one such branch. ---
case "$BRANCH" in
  unattended/*) ;;
  *) finish error - branch "BOARD_BRANCH is '$BRANCH'; the runner commits on an unattended/* branch only" ;;
esac
CURRENT=$(git branch --show-current 2>/dev/null || echo "")
if [ "$CURRENT" != "$BRANCH" ]; then
  git fetch -q "$REMOTE" 2>/dev/null
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git switch -q "$BRANCH" || finish error - branch "cannot switch from '${CURRENT:-detached}' to $BRANCH (uncommitted changes?)"
  elif git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
    git switch -q -c "$BRANCH" --track "$REMOTE/$BRANCH" || finish error - branch "cannot create $BRANCH from $REMOTE/$BRANCH"
  else
    finish error - branch "the work branch $BRANCH exists neither here nor on $REMOTE; create it first"
  fi
  event "switched ${CURRENT:-detached} -> $BRANCH"
fi

# board_commit <message>: commit tasks/ and nothing else, on the work branch and nowhere else.
board_commit() {
  [ "$(git branch --show-current 2>/dev/null)" = "$BRANCH" ] \
    || finish error "${TASK_NAME:--}" branch "the checkout left $BRANCH; nothing was committed"
  git add -A -- tasks/ || return 1
  if git diff --cached --quiet -- tasks/; then return 0; fi
  git commit -q -m "$1" -- tasks/ || return 1
  event "commit $(git rev-parse --short HEAD) $1"
}

push_branch() {
  [ "$PUSH" -eq 1 ] || return 0
  if git push -q "$REMOTE" "$BRANCH" >> "$STATE/logs/git.log" 2>&1; then
    event "pushed $(git rev-parse --short HEAD)"
  else
    event "push-failed $(git rev-parse --short HEAD)"; say "push failed (see $STATE/logs/git.log); it is tried again after the next task"
  fi
}

# Fetch and rebase onto the remote branch. A remote without the branch yet is not an error.
sync_branch() {
  git fetch -q "$REMOTE" >> "$STATE/logs/git.log" 2>&1 || { event "fetch-failed"; return 0; }
  git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH" || return 0
  if ! git pull -q --rebase --autostash "$REMOTE" "$BRANCH" >> "$STATE/logs/git.log" 2>&1; then
    git rebase --abort >> "$STATE/logs/git.log" 2>&1
    finish error "${TASK_NAME:--}" pull-conflict "pull --rebase of $BRANCH from $REMOTE did not apply cleanly; the rebase was aborted, nothing is lost. Resolve it by hand, then start the runner again"
  fi
}

# A question the gate put on the board is committed and pushed at once, by itself: the owner
# reads the branch, not this machine, and the task the agent was on may never close.
publish_gate_questions() {
  local -a fresh=()
  local path
  while IFS= read -r path; do
    case "$path" in tasks/blocked/[0-9]*-gate-escalation-*.md) fresh+=("$path") ;; esac
  done < <(git ls-files --others --exclude-standard -- tasks/blocked)
  [ "${#fresh[@]}" -gt 0 ] || return 0
  [ "$(git branch --show-current 2>/dev/null)" = "$BRANCH" ] \
    || finish error "${TASK_NAME:--}" branch "the checkout left $BRANCH; nothing was committed"
  git add -- "${fresh[@]}" && git commit -q -m "board: the gate asks the owner — ${#fresh[@]} question(s) in blocked/" -- "${fresh[@]}" \
    || finish error "${TASK_NAME:--}" commit "cannot commit the gate's question"
  event "gate-question $(git rev-parse --short HEAD) ${fresh[*]}"
  push_branch
}

# The «закрити» answers that are in the checkout NOW and did not arrive from the owner earlier.
# Called before the pull: whatever it lists was written here, not by the owner.
local_gate_answers() {
  local line
  { board gate-answers; board owner-actions; } | while IFS= read -r line; do
    grep -qxF -- "$line" "$ACCEPTED" 2>/dev/null || echo "$line"
  done
}

# Act on the owner's «так» under an offered action. Run here, by the runner — never by an agent;
# owner_action.py holds the list of what may be run and refuses inside a Claude Code session.
owner_actions() {
  local name action arg sum line rc outcome
  while IFS=$'\t' read -r name action arg sum; do
    [ -n "$name" ] || continue
    line="$name"$'\t'"$action"$'\t'"$arg"$'\t'"$sum"
    if grep -qxF -- "$line" <<< "$LOCAL_ANSWERS"; then
      board action-reject "$name" || finish error - action "board.py action-reject $name failed"
      event "action-answer-rejected $action $name written-here"
      say "$name: an answer written on this machine is not the owner's; wiped and asked again"
      board_commit "board: ${name%.md} — an answer written on this machine is not the owner's; asked again" \
        || finish error - commit "cannot commit the rejected answer"
      continue
    fi
    echo "$line" >> "$ACCEPTED"
    python3 "$HERE/owner_action.py" --root "$PROJECT_ROOT" "$action" "$arg" >> "$STATE/logs/owner-action.log" 2>&1; rc=$?
    case "$rc" in
      0) outcome=applied ;;
      1) outcome=failed ;;
      3) outcome=stale ;;
      *) event "action-refused $action $name rc=$rc"
         say "$name: owner_action.py refused $action (see $STATE/logs/owner-action.log); the question stays in blocked/"
         continue ;;
    esac
    board action-done "$name" "$outcome" || finish error - action "board.py action-done $name failed"
    event "action-$outcome $action $name"
    say "${name%.md}: $action on the owner's answer — $outcome"
    if [ "$outcome" = applied ] && ! git diff --quiet -- .claude/settings.json; then
      [ "$(git branch --show-current 2>/dev/null)" = "$BRANCH" ] \
        || finish error - branch "the checkout left $BRANCH; nothing was committed"
      git commit -q -m "settings: the proposal docs/tasks/settings.json applied on the owner's answer (${name%.md})" -- .claude/settings.json \
        || finish error - commit "cannot commit the applied settings"
      event "commit $(git rev-parse --short HEAD) settings applied"
    fi
    board_commit "board: ${name%.md} — $action on the owner's answer: $outcome" \
      || finish error - commit "cannot commit the outcome of the action"
  done <<< "$(board owner-actions)"
}

# Act on the owner's «закрити». The command is run here, by the runner — never by an agent.
close_escalations() {
  local name stamp sum line rc
  while IFS=$'\t' read -r name stamp sum; do
    [ -n "$name" ] || continue
    line="$name"$'\t'"$stamp"$'\t'"$sum"
    if grep -qxF -- "$line" <<< "$LOCAL_ANSWERS"; then
      board gate-reject "$name" || finish error - gate "board.py gate-reject $name failed"
      event "escalation-answer-rejected $stamp $name written-here"
      say "$name: an answer written on this machine is not the owner's; wiped and asked again"
      board_commit "board: ${name%.md} — an answer written on this machine is not the owner's; asked again" \
        || finish error - commit "cannot commit the rejected answer"
      continue
    fi
    echo "$line" >> "$ACCEPTED"
    CLAUDE_PROJECT_DIR="$PROJECT_ROOT" python3 "$GATE_PY" --close-escalation "$stamp" >> "$STATE/logs/gate.log" 2>&1; rc=$?
    case "$rc" in
      0) board gate-done "$name" closed > /dev/null || finish error - gate "board.py gate-done $name failed" ;;
      1) board gate-done "$name" absent > /dev/null || finish error - gate "board.py gate-done $name failed" ;;
      *) event "escalation-close-refused $stamp $name rc=$rc"
         say "$name: gate.py refused to close $stamp (see $STATE/logs/gate.log); the question stays in blocked/"
         continue ;;
    esac
    event "escalation-closed $stamp $name$([ "$rc" -eq 1 ] && echo ' was-not-open')"
    say "${name%.md}: gate escalation $stamp closed on the owner's answer"
    board_commit "board: ${name%.md} → done — gate escalation $stamp closed on the owner's answer" \
      || finish error - commit "cannot commit the closed gate question"
  done <<< "$(board gate-answers)"
}

# New task files and the owner's answers, each in a commit of its own.
intake() {
  local taken answered
  publish_gate_questions
  taken=$(board import-inbox "$INBOX") || finish error - inbox "board.py import-inbox failed"
  if [ -n "$taken" ]; then
    while IFS= read -r line; do event "inbox $line"; done <<< "$taken"
    board_commit "board: from the inbox — $(echo "$taken" | grep -vc ' skipped: ') file(s) taken" \
      || finish error - commit "cannot commit the inbox files"
  fi
  close_escalations
  owner_actions
  answered=$(board unblock) || finish error - unblock "board.py unblock failed"
  if [ -n "$answered" ]; then
    board_commit "board: answered, back to todo — $(echo "$answered" | tr '\n' ' ')" \
      || finish error - commit "cannot commit the answered tasks"
  fi
}

# run_task <tasks/doing/NAME.md>: attempts until the agent moved the task out of doing/.
# Sets OUTCOME to done or blocked; every other ending is a `finish`.
run_task() {
  local file="$1" stem place session before after n out note
  local -a flags
  stem=$(basename "$file" .md)
  local first="You are working from the task board, unattended: nobody will answer a question in this conversation. Your task is the file $file. Read tasks/README.md (the section «Правила для агента») and follow it. If work on this task has already begun (see git log and the working tree), continue it instead of starting over. The task is finished only when you have moved it to tasks/done/$stem/ (task.md and report.md) or, if it cannot proceed without the owner, to tasks/blocked/ with your questions, and committed that. Do not push. If the usage limit runs out, just end the turn; you will be continued."
  local again="Continue the task $file from where you stopped. It is finished only when it is in tasks/done/$stem/ (task.md and report.md) or in tasks/blocked/ with your questions, and that is committed."
  while :; do
    place=$(board where "$stem")
    case "$place" in
      done|blocked) OUTCOME="$place"; return 0 ;;
      doing) ;;
      *) finish error "$stem" task-vanished "the task is neither in doing/, done/ nor blocked/ (found: $place)" ;;
    esac
    if [ "$(memo get "$stem" age_sec)" -ge "$TASK_MAX" ]; then
      finish deadline "$stem" deadline "the task has been open for more than $((TASK_MAX / 3600)) hour(s). To give it a fresh clock: board-runner.sh --retry"
    fi
    if [ "$(memo get "$stem" idle)" -ge "$STALL_ATTEMPTS" ]; then
      finish stalled "$stem" no-commit "$STALL_ATTEMPTS attempts in a row made no new commit. Look at $STATE/logs/, then: board-runner.sh --retry"
    fi
    flags=(--settings .claude/settings.json --permission-mode auto --output-format json)
    if [ -n "$MAX_USD" ]; then
      note=$(memo get "$stem" left "$MAX_USD")
      if [ "$note" = "0.00" ]; then
        finish stalled "$stem" budget "the task has spent its budget of $MAX_USD USD ($(memo get "$stem" cost) recorded). Raise BOARD_MAX_USD to continue"
      fi
      flags+=(--max-budget-usd "$note")
    fi
    session=$(memo get "$stem" session)
    n=$(( $(memo get "$stem" attempts) + 1 ))
    out="$STATE/logs/$stem-$n.json"
    before=$(git rev-parse HEAD)
    status running "$stem"
    event "attempt $stem $n ${session:+resume=$session}"
    if [ -z "$session" ]; then
      "$CLAUDE_BIN" -p "$first" "${flags[@]}" < /dev/null > "$out" 2> "$out.err" &
    else
      "$CLAUDE_BIN" -p "$again" --resume "$session" "${flags[@]}" < /dev/null > "$out" 2> "$out.err" &
    fi
    CLAUDE_PID=$!
    wait "$CLAUDE_PID"
    CLAUDE_PID=""
    after=$(git rev-parse HEAD)
    note=$(memo record "$stem" "$out" "$([ "$before" != "$after" ] && echo 1 || echo 0)")
    event "attempt-end $stem $n cost=$(memo get "$stem" cost) commit=$([ "$before" != "$after" ] && echo yes || echo no)${note:+ $note}"
    publish_gate_questions
    if [ "$note" = "limit" ] && [ "$(board where "$stem")" = "doing" ]; then
      status waiting-limit "$stem"
      say "usage limit; waiting $LIMIT_WAIT s"
      sleep "$LIMIT_WAIT"
      continue
    fi
    [ "$(board where "$stem")" = "doing" ] && sleep "$PAUSE"
  done
}

event "start pid=$$ branch=$BRANCH once=$ONCE push=$PUSH${MAX_USD:+ max_usd=$MAX_USD}"
TASK_NAME="-"
FINISHED=0
while :; do
  LOCAL_ANSWERS=$(local_gate_answers)
  sync_branch
  intake
  TASK=$(board next); RC=$?
  case "$RC" in
    0) ;;
    3|4)
      push_branch
      if [ "$RC" -eq 4 ] || [ -n "$(find tasks/blocked -maxdepth 1 -name '[0-9]*.md' 2>/dev/null | head -1)" ]; then
        finish waiting-owner - owner "nothing can move: what is left waits for the owner's answers or for tasks that are not done ($FINISHED task(s) closed in this run)"
      fi
      finish idle - todo-empty "tasks/todo/ is empty ($FINISHED task(s) closed in this run)"
      ;;
    *) finish error - board "board.py next refused (two tasks in tasks/doing/?); see its message above" ;;
  esac
  TASK_NAME=$(basename "$TASK" .md)
  case "$TASK" in
    tasks/todo/*)
      TASK=$(board start "$TASK") || finish error "$TASK_NAME" start "board.py start refused"
      board_commit "board: $TASK_NAME → doing" || finish error "$TASK_NAME" commit "cannot commit the move to doing/"
      memo retry "$TASK_NAME"
      ;;
    *)
      memo begin "$TASK_NAME"
      if [ "$RETRY" -eq 1 ]; then memo retry "$TASK_NAME"; event "retry $TASK_NAME"; fi
      ;;
  esac
  RETRY=0
  OUTCOME=""
  run_task "$TASK"
  # The agent moved the task but left the move uncommitted: commit tasks/, nothing else.
  board_commit "board: $TASK_NAME → $OUTCOME (the move was left uncommitted)" \
    || finish error "$TASK_NAME" commit "cannot commit the leftover changes under tasks/"
  memo finish "$TASK_NAME" "$OUTCOME"
  event "task-$OUTCOME $TASK_NAME cost=$(memo get "$TASK_NAME" cost)"
  say "$TASK_NAME: $OUTCOME ($(memo get "$TASK_NAME" cost) USD)"
  FINISHED=$((FINISHED + 1))
  push_branch
  if [ "$ONCE" -eq 1 ]; then
    finish stopped "$TASK_NAME" once "one task was asked for (--once); it ended in $OUTCOME/"
  fi
  TASK_NAME="-"
done
