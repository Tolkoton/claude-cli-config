# Unattended operation

Runs the agent 24/7 with nobody watching. A supervisor outside the agent
restarts a session that dies, leaves alone one that finishes, and caps both
restarts and spend so a bad night cannot run to morning.

Every design call is in [`unattended-decisions.md`](unattended-decisions.md)
with its reasoning and cost-to-reverse.

## Start it

**Prerequisite — grant the launch permission on this machine.** The agent cannot
grant it to itself: launching a self-restarting loop of agent processes is
refused, correctly, by the permission layer. Add to
`.claude/settings.local.json` (machine-local and gitignored, *not*
`settings.json`, which ships with the template):

```json
{ "permissions": { "allow": [
    "Bash(bash .claude/unattended/supervisor.sh:*)",
    "Bash(.claude/unattended/supervisor.sh:*)"
] } }
```

**Then restart Claude Code.** Settings are read at session start, so a rule
added mid-session does not apply until the next one.

```bash
command -v jq || command -v python3          # the hooks parse their input with one of
                                             # them; with neither, the deny hooks refuse
                                             # every call (.claude/references/hooks.md)
echo unattended > .claude/state/overseer/mode      # only when the guardrails verify green
nohup .claude/unattended/supervisor.sh >> .claude/state/unattended/logs/nohup.log 2>&1 &
```

On the Linux server, prefer the unit: `sudo cp claude-unattended.service
/etc/systemd/system/ && sudo systemctl enable --now claude-unattended`.

```bash
.claude/unattended/supervisor.sh --status    # state, restarts this hour, spend
.claude/unattended/supervisor.sh --reset     # clear state for a fresh run (keeps cost)
```

## The board runner — work from task files instead of a DAG

`board-runner.sh` is the second way to run unattended: it takes its work from `tasks/` (manual:
`tasks/README.md`) instead of the feature DAG, one task at a time, each in a fresh conversation.

```bash
bash .claude/unattended/board-runner.sh            # until nothing can move, then stop with a summary
bash .claude/unattended/board-runner.sh --once     # one task
bash .claude/unattended/board-runner.sh --status   # the status line and the board; runs nothing
bash .claude/unattended/board-runner.sh --retry    # after `stalled` or `deadline`: a fresh clock and count
bash .claude/unattended/board-runner.sh --stop-after-task   # the only way to stop a working runner
```

To stop a runner, never kill it — the agent loses the uncommitted work of its task. `--stop-after-task`
puts the flag `.claude/state/board/stop-after-task`; the runner looks at it between tasks, so the
current task is finished and pushed, then the runner stops with `state=stopped
reason=stop-after-task` and removes the flag. With no runner working the command sets nothing
and says so; a flag left by a runner that died is removed when the next one starts.

Before every task it fetches and rebases the work branch (`unattended/work`), takes new files
from the inbox (`~/engine-ops/tasks-inbox/`, if it exists) into `tasks/todo/`, and returns
answered tasks from `tasks/blocked/`. A question the Stop gate put there after giving up
(`9NN-gate-escalation-*.md`) it commits and pushes at once; when the owner's answer `закрити`
arrives by the pull or the inbox, the runner itself runs `gate.py --close-escalation` and moves
that task to `done/` — no agent is started for it (`.claude/references/gate.md`). An action the
owner approved with `так` under a question that offers it (`Дія виконавця: apply-settings <sha256>`)
the runner takes itself, through `owner_action.py`, whose list is short: the settings
proposal is copied over `.claude/settings.json`, its test run, the file committed, and the task
returned to `todo/` with the outcome in place of the offer (`docs/tasks/README.md`). A lesson
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
the branch and takes the next one. It stops — always with `.claude/state/board/summary.md` —
when `todo/` is empty or everything left waits for the owner (exit 0), after three attempts in a
row without a commit, after twelve hours on one task, or when the task's budget
(`BOARD_MAX_USD`) is spent (exit 1).

What to read, in `.claude/state/board/`: `status` (one line: `state=… task=… since=<UTC>
[reason=…]`), `events.log`, `costs.json`, `summary.md`, `logs/`. The numbers and paths are
environment variables listed at the head of the script. `board.py` is the board's one reader
(`next`, `summary`, …); `board_state.py` keeps what the runner remembers about each task.

The owner's review — `python3 .claude/unattended/board.py review [--since <commit|date>]` — is
one markdown document about the work branch as origin has it (`board_review.py`). It writes
nothing, so it may run next to a runner in the middle of a task and from any clone; the
runner's state files are read when they are there. `/review` walks it with the owner.

## The decision the supervisor makes

On every session exit, read `state.json`:

| status | meaning | supervisor |
|---|---|---|
| `working` | a session is in flight | process gone + this status = **it died** → restart |
| `unit-done` | unit finished, work remains | restart, self-feeding the next DAG node |
| `finished` | DAG exhausted | **stop.** Legitimate interrupt 3 |
| `parked` | work remains, all of it blocked | **stop.** Legitimate interrupt 1 or 2 |
| `halted` | a cap fired | **stop.** A human must look |
| *(no file)* | died before writing anything | restart |

The exit code is corroborating only. A crashed CLI, an OOM kill, and a clean
finish all return 0, so the file decides (D-3). The bias is deliberate:
restarting a finished run costs one no-op session; failing to restart a died run
costs the night.

## Session contract

Anything used as `SESSION_CMD` must:

1. **Tick the heartbeat** while working —
   `python3 .claude/unattended/runstate.py heartbeat`. Combined with
   `.engine/PROGRESS.md` mtime this is the liveness signal; a session that updates
   neither for `STALL_TIMEOUT_SEC` is killed as wedged (D-4, D-5).
2. **Write a terminal status before exiting** —
   `runstate.py set finished|parked|halted "<reason>" "<what unblocks it>"`, or
   `set unit-done` when work remains.
3. **Record its cost** — `runstate.py add-cost <usd>`.
4. **Never invent `finished`.** If the agent stops without a status, leave
   `working`: the supervisor reads that as a death and retries, which is
   recoverable. A false `finished` is a silent overnight halt, which is not.

## Files

| File | Role | Tracked |
|---|---|---|
| `supervisor.sh` | the loop: spawn, watch, classify, cap, restart | yes |
| `runstate.py` | state / cost / DAG operations, shared by shell and agent | yes |
| `session-claude.sh` | real runner: one headless `claude -p` per node | yes |
| `session-sim.sh` | scripted runner for the proof harness (D-15) | yes |
| `recheck_parked.py` | re-opens parked items whose condition is now met (D-12) | yes |
| `rotate.sh` | size-triggered log/ledger rotation (D-13) | yes |
| `config.sh` | all tunables. Named `.sh` because `protect-paths.sh` denies `*.env` | yes |
| `state.json` | the authoritative status | no |
| `cost.json` | cumulative spend, survives restarts (D-9) | no |
| `restarts.log` | timestamps for the rolling-hour cap (D-6) | no |
| `logs/`, `archive/` | session logs and rotated generations | no |

## Making a parked item auto-resume

`recheck_parked.py` runs before every spawn and re-opens an item only when a
machine-checkable condition in its `Unblocks when:` line is satisfied. Write one
of these tokens into the line and the queue heals itself:

| Token | True when |
|---|---|
| `env:VAR` | that variable is set |
| `file:PATH` | that path exists |
| `node:ID` | that DAG node is `done` |
| `mode:attended` | `.claude/state/overseer/mode` no longer says unattended |
| `premise:ID` | that premise row is `verified` in the premise log |

An item with no token stays parked until a human moves it. That is deliberate —
re-opening on a guess is how a run starts thrashing.

## The feature DAG

```json
{"feature": "slug",
 "nodes": [{"id": "S1", "deps": [], "status": "pending"},
           {"id": "S2", "deps": ["S1"], "status": "pending"}]}
```

`status` is `pending`, `done`, or `parked`. The next node is the first whose
deps are all `done` (D-10). A parked node blocks its dependents but not the rest
of the graph — the run routes around it.

`.engine/architecture/feature-dag.json` currently holds a **tracer-bullet DAG**
built to prove the harness. Replace it with a real one from
`/feature-architect`.

## What was proven, and what was not

Proven end to end, repeatedly, on this machine: a session killed with SIGKILL
mid-unit is detected and restarted; the run self-feeds across a slice boundary
with no human turn; a clean finish is not restarted; a crash loop halts at the
restart cap; the cost cap parks; a wedged session is killed and recovered;
rotation triggers, prunes, and no-ops correctly.

Not proven: multi-day operation, and the quality of the agent's work inside a
session. The proof used the simulated runner (D-15) — the supervisor code path
is identical either way, but what happens *inside* a session is out of its
scope by construction.
