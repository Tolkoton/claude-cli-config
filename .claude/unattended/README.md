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
owner approved with `так` under a question that offers it (`Дія виконавця: apply-settings <sha256>`)
the runner takes itself, through `owner_action.py`, whose list is short: the settings
proposal is checked by `settings_check.py` (it ships with the engine, so this works in every
project), copied over `.claude/settings.json`, the project's own `tests/test_settings_proposal.py`
run when it keeps one, the file committed, and the task returned to `todo/` with the outcome in
place of the offer. `engine.py` gives a project its `docs/tasks/settings.json` as a copy of its
own live settings. A lesson
becomes a rule the same way and no other: the question `8NN-rule-proposal-*.md` carries the offer
`Дія виконавця: promote-rule <sha256>`; on the owner's `так` the runner has `lesson_queue.py` add
that exact text to `.engine/rules.md`, on `ні` it closes the proposal, commits, and moves the
question to `done/` with a short report — no agent is started. A task that says `Потрібна присутність
власника: так` it never takes (`board.py next` does not offer one; left in `doing/` it stops the runner with
`reason=attended`): such a task is done in an interactive session with the owner (`tasks/README.md`).
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

It stops — always with `.claude/state/board/summary.md` — when `todo/` is empty or everything
left waits for the owner, or on a soft stop (exit 0); and with `state=error` (exit 1) only on what
it cannot work past: a pull that conflicts (`reason=pull-conflict`), claude logged out
(`reason=logged-out`; the task stays in `doing/` and the next start continues it), a git or
`board.py` failure after which nothing can be committed.

What to read, in `.claude/state/board/`: `status` (one line: `state=… task=… since=<UTC>
[reason=…]`), `events.log`, `costs.json`, `summary.md`, `logs/`. The numbers and paths are
environment variables listed at the head of the script. `board.py` is the board's one reader
(`next`, `summary`, …); `board_state.py` keeps what the runner remembers about each task.

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
