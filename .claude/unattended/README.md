# Unattended operation

Unattended work has one way in: the task board. The owner puts tasks as files into `tasks/`
(manual: `tasks/README.md`); `board-runner.sh` takes them one at a time, each in a fresh
conversation, and stops with a summary when nothing can move. There is no other loop: the
supervisor that executed a feature DAG node by node was retired by board 039, and the feature
DAG (`.engine/architecture/feature-dag.json`) is only what `/feature-architect` plans a feature
into.

Why the commit policy, the deny hook and the patch screen are the way they are:
[`unattended-decisions.md`](unattended-decisions.md).

## The board runner

```bash
bash .claude/unattended/board-runner.sh            # until nothing can move, then stop with a summary
bash .claude/unattended/board-runner.sh --once     # one task
bash .claude/unattended/board-runner.sh --status   # the status line and the board; runs nothing
bash .claude/unattended/board-runner.sh --stop-after-task      # stop a working runner once its task is closed
bash .claude/unattended/board-runner.sh --stop-after-attempt   # …or once the attempt in hand has ended
```

To stop a runner, never kill it — the agent loses the uncommitted work of its task. `--stop-after-task`
puts the flag `.claude/state/board/stop-after-task`; the runner looks at it between tasks, so the
current task is finished and pushed, then the runner stops with `state=stopped
reason=stop-after-task` and removes the flag. `--stop-after-attempt` is the quicker one: the flag
`stop-after-attempt` is looked at before and after every attempt, so the session in hand ends by
itself, what it committed is pushed, and the runner stops with `reason=stop-after-attempt`; the
task stays in `doing/` with its uncommitted work, its conversation, its clock and its count, and
the next start continues it (`--resume`). With no runner working either command sets nothing
and says so; a flag left by a runner that died is removed when the next one starts.

Before every task it fetches and rebases the work branch (`unattended/work`), takes new files
from the inbox (`~/engine-ops/tasks-inbox/`, if it exists) into `tasks/todo/`, and returns
answered tasks from `tasks/blocked/`. A question the Stop gate put there after giving up
(`9NN-gate-escalation-*.md`) it commits and pushes at once; when the owner's answer `так`
arrives by the pull or the inbox, the runner itself runs `gate.py --close-escalation` and moves
that task to `done/` — no agent is started for it (`.claude/references/gate.md`). An action the
owner approved with `так` under a question that offers it (`Дія runner-а: apply-settings <sha256>`)
the runner takes itself, through `owner_action.py`, whose list is short: the settings
proposal is checked by `settings_check.py` (it ships with the engine, so this works in every
project), copied over `.claude/settings.json`, the project's own `tests/test_settings_proposal.py`
run when it keeps one, the file committed, and the task returned to `todo/` with the outcome in
place of the offer. `engine.py` gives a project its `docs/tasks/settings.json` as a copy of its
own live settings. An approved goals document is amended the same way (board 051): the offer
`Дія runner-а: amend-goals <sha256 of .engine/goals/proposed.md>`; on `так` the runner has `goals.py` check
that the proposal is a lawful amendment, put it in place of `.engine/goals.md`, seal it and list what cited a
changed line; the agent, when the task returns to it, commits the document. A lesson
becomes a rule the same way and no other: the question `8NN-rule-proposal-*.md` carries the offer
`Дія runner-а: promote-rule <sha256>`; on the owner's `так` the runner has `lesson_queue.py` add
that exact text to `.engine/rules.md`, on `ні` it closes the proposal, commits, and moves the
question to `done/` with a short report — no agent is started. Dependencies are updated the
same way and no other (board 076): the question that ends a `/maintain` task carries the offer
`Дія runner-а: update-deps <sha256 of .engine/maintain/updates.json>`; on `так` `owner_action.py` checks
that the list is the one the owner saw, that the tree is clean and the full gate green, then runs the
project's `DEPS_UPDATE_CMD` — the patches as one group, every minor version alone, never a major one
— each followed by `gate.py --layer ci` and a commit of its own, or rolled back and written with its
output to `.engine/maintain/update-result.md`; the task then returns to the agent, which reports.
Once a week the runner puts the maintenance task into `todo/` itself (`board.py maintain-task`:
`NNN-maintain-<date>.md`, a task to run `/maintain`) — never while one waits in `todo/`, `doing/` or
`blocked/`, `MAINTAIN_EVERY_DAYS` in `project.env` (empty: 7, `0`: never). When nothing can be taken — `todo/` is
empty, or all that is left waits for the owner — it puts a cleanup task there instead of stopping
(`board.py cleanup-task`: `NNN-cleanup-<date>.md`, a task to run `simplifier.py nightly` and act by the
simplifier's rules), with an entry in the anomaly journal, in one commit — not more than once a day, never
while one waits in `todo/`, `doing/` or `blocked/`, never while any task lies in `doing/` (the owner's attended
one too, board 723), `CLEANUP_EVERY_DAYS` in `project.env` (empty: 1, `0`:
never); the pass after that task finds nothing due and stops as before. A task that says `Потрібна присутність
власника: так` it never takes (`board.py next` does not offer one): such a task is done in an interactive
session with the owner (`tasks/README.md`). Left in `doing/` it stops no task: the runner leaves it as it is,
takes the next tasks beside it (only the cleanup task waits for it, board 723), and the review shows it as «у роботі з власником». A task the owner has just
answered is taken first after the one in hand, whatever its number (`tasks/.first`, written by `board.py unblock`).
It moves the task to `doing/` in its own commit and starts
`claude -p` with `--settings .claude/settings.json --permission-mode auto --output-format json`.
A session that ends with the task still open is continued (`--resume`); a usage-limit notice
waits 15 minutes. When the agent has moved the task to `done/` or `blocked/` the runner pushes
the branch and takes the next one.

One task never stops the board. After three attempts in a row without a commit, after twelve
hours on one task, when the task's budget (`BOARD_MAX_USD`) is spent, or when three overseers in a
row answered BLOCK on one of its units (the Stop hook then leaves a marker with the verdicts and
stops the session; the agent is asked nothing), the runner parks the
task itself (`board.py park`): it goes to `tasks/blocked/` with a section `## Чому зупинилась` and
a question to the owner, the agent's uncommitted work outside `tasks/` becomes one commit on a
branch of its own, `wip/<task>/<UTC>`, pushed to origin (and a git stash on this machine as well) —
that section names both and gives the command that brings the work back in any clone —, the event
is written into the anomaly journal `tasks/ANOMALIES.md`, and the next task is taken. Any answer returns the task to `todo/` with a fresh clock and count — after a
budget stop, with one more budget of the same size. Everything else that is odd (a push that
failed, a task that vanished from the board) is one more journal entry, not a stop; the review
shows the new entries in a section of their own. The journal is the one place for everything odd:
the Stop gate writes its escalation there, the stuck counter its third identical failure, the agent
what it met (`board.py anomaly … --source агент`), and every entry says who wrote it; the runner
commits what the others wrote before every pull and after every attempt. Every stop with
`state=error` leaves an entry too (not when the checkout is off the work branch). A gate question
nobody answered whose escalation the owner closed in a terminal goes to `done/` by itself, with an
entry.

A task closes with a clean tree. When the agent has moved its task to `done/` or `blocked/`, the
runner looks at `git status`; files that are uncommitted now and were not when the task began are
the task's. The agent gets the turn back once, in the same conversation, with one request: commit
what belongs to the task, remove the rest. A tree still dirty after that turn is one journal entry
with the list of files, and the next task is taken; the runner deletes, stashes and commits none
of them.

A task closes into `done/` with the minimum of its mode (board 098). Right after the clean-tree
check the runner asks `python3 .claude/hooks/mode.py check-close <task>`, which judges by files:
`report.md` in every mode; in соло, for every commit of the task that changed working code (what
the Stop hook asks an audit for: under `SOURCE_DIRS`, else an extension of `CODE_EXTENSIONS`, else
every file; never `tasks/` or `.engine/`), in every stay of the task in `doing/` and in the turn
back, a PASS of the overseer whose audit saw exactly that code; in конвеєр also the feature artifact and a matching seal on every slice contract the task
wrote; in ескіз `report.md` for now (board 099 adds the quarantine). Missing — the agent gets the turn
back once with the list; still missing — the task goes to `blocked/` with the reason `minimum`, its
report beside it as `blocked/report-<task>.md`, and a journal entry. A task closed into `blocked/`,
and one the runner closes itself (a gate's escalation, an owner action), is not checked; a check that
breaks (exit 3, or any code but 0 and 1) is a journal entry and the task stays in `done/` — never a
park, never a stop.

It stops — always with `.claude/state/board/summary.md` — when `todo/` is empty or everything
left waits for the owner, or on a soft stop (exit 0); and with `state=error` (exit 1) only on what
it cannot work past: a pull that conflicts (`reason=pull-conflict`), claude logged out
(`reason=logged-out`; the task stays in `doing/` and the next start continues it), a git or
`board.py` failure after which nothing can be committed.

What to read, in `.claude/state/board/`: `status` (one line: `state=… task=… since=<UTC>
[reason=…]`), `events.log`, `costs.json`, `summary.md`, `logs/`. The numbers and paths are
environment variables listed at the head of the script. `board.py` is the board's one reader
(`next`, `summary`, …); `board_state.py` keeps what the runner remembers about each task, and its
`report` — the summary's «Витрати» — also says what every UTC day cost: the day in progress and the
seven before it, a day with nothing spent at 0.00, an attempt recorded without a time on a line of its
own (board 106). No limit is set per day; `BOARD_MAX_USD` per task is as it was.

The owner's review — `python3 .claude/unattended/board.py review [--since <commit|date>]` — is
one markdown document about the work branch as origin has it (`board_review.py`). It writes
nothing, so it may run next to a runner in the middle of a task and from any clone; the
runner's state files are read when they are there. `/owner-review` walks it with the owner.

## Files

| File | Role |
|---|---|
| `board-runner.sh` | the loop: pull, inbox, unblock, one task per fresh session, park, push |
| `board.py` | the board's one reader and mover (`next`, `start`, `park`, `summary`, `review`, …) |
| `board_state.py` | what the runner remembers about each task (attempts, clock, cost) |
| `board_review.py` | the owner's review document |
| `owner_action.py` | the short list of actions the owner's `так` has the runner take |
| `settings_check.py` | judges a settings proposal before it is applied |
| `commit_checkpoint.sh` | the one sanctioned commit path, on `unattended/*` only |
| `env-probe.sh` | prints what kind of session this is (attended, unattended, cloud) |

Machine state is in `.claude/state/board/` and is never committed.
