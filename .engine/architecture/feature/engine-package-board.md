# Feature engine-package-board — a task board in files and a runner that works from it

Frame source: `docs/plan/package-board.md` (the owner's text, verbatim, commit `bea944c`). Every
numbered item there is an owner requirement; the critic checks how each is met, not whether, and
gets at most two rounds. Branch `unattended/work` (new, from `origin/unattended/2026-10-03-package-costs`,
`fa02ace`). Standing rules from the program: `bash tests/run_all.sh --fast` after every slice, one
full `bash tests/run_all.sh` and the golden set at the end, ruff and `mypy --strict`, UTC only, the
owner is not asked — whatever needs the owner is parked with its exact command. One paid action in
the whole package: the live check at the end, at most 3 USD. No paid audit.

## Goal

The owner stops writing programs for an operator-run queue and starts dropping task files. A
directory `tasks/` in the repository root is the board: `todo/`, `doing/`, `blocked/`, `done/`. A
task is one file; its number is its priority; its header says what it depends on and whether a
paid audit is wanted; its last section holds questions for the owner, each with an `Відповідь:`
line. A runner owned by the engine, `.claude/unattended/board-runner.sh`, takes the tasks one at a
time, each in a fresh headless conversation, carries answers and new tasks in, pushes finished work
out, and stops with a summary when nothing can move. Paid runs become deterministic: the audit
runner refuses to start a session unless the task in `doing/` says so, or the owner passes a flag
by hand.

## Acceptance criteria (the owner's, from the program's "ГОТОВО, КОЛИ")

- Every suite green (`bash tests/run_all.sh`); the golden set identical to the newest reference
  (`evals/baseline/Laos-MacBook-Pro/results-package-costs.json`) except what this package means to
  change (nothing is meant to change: no hook is touched).
- The live check passed: a task `000-перевірка` goes `todo → doing → done` with a report through
  the real `claude`, driven by the runner, for at most 3 USD.
- ruff and `mypy --strict` clean on the changed and new Python; the ownership map knows the new files.
- `docs/plan/package-board-report.md` (opening with «Що змінилось для власника»: five plain lines
  and a one-minute demonstration; separately an exact instruction for the operator on starting the
  runner) and `docs/plan/package-board-summary.md` written.

## Build parameters

- Budgets (owner's numbers): live check ≤ 3 USD; usage-limit wait 15 minutes; a task is abandoned
  after 12 hours; the runner stops after three consecutive attempts without a new commit.
- Policies: standard library only, no new dependency. Shell for the loop (the owner named a `.sh`),
  Python for everything that parses or decides (so it is typed and unit-tested). Every time the
  runner prints or stores is UTC. Every wait and limit is an environment variable with the owner's
  number as default, so the tests run in seconds.
- Risk tolerance: spikes run without asking unless they cost money — a paid probe is not allowed
  (program rule 5), so a premise that only a paid call could settle is settled by the live check.
- Autonomy: all slices built in order; interrupts only on the critical set. Unattended in fact (the
  program: «Мене не питай»).

## Premises (see `.engine/premises/premise-log.md`, PR-board-01…07)

1. `claude -p … --output-format json` prints one JSON object carrying `session_id` and
   `total_cost_usd`, and `claude -p … --resume <session_id>` continues that conversation headless.
   Evidence: `evals/run_audit_scenarios.py` (`call_claude`, `parse_json_output`, the `--resume`
   step) does exactly this on this machine; `claude --help` of 2.1.288 lists both flags.
2. On a continued conversation `total_cost_usd` is the conversation's running total, not the cost of
   the last call. Evidence, indirect: `~/engine-ops/events.log` 2026-10-03 12:05Z → 11.43, 12:07Z →
   11.90, 12:53Z → 13.31 for one continued conversation (a two-minute call cannot cost 11.90).
   Not provable without a paid call → the runner stores the raw figure of every attempt with its
   session id, so either reading can be recomputed; the task's cost is the sum over sessions of the
   highest figure each session reported. Re-read in the live check if a continuation happens.
3. `--permission-mode auto` with `--settings .claude/settings.json` is accepted by a headless
   session and lets it work in this repository. Evidence: `~/engine-ops/run-queue.sh` starts every
   program this way, this session included.
4. `engine.py` creates a project file from `seed=` once, also in a directory that does not exist
   yet and also for an empty file (`.gitkeep`). To verify in B1 by a test on a synthetic project.
5. A headless session may commit on `unattended/work` through `commit_checkpoint.sh` (the branch
   matches `unattended/*`). Evidence: this session, `bea944c`.
6. **Integration:** the runner can tell from the working tree and `HEAD` alone that the agent
   finished — the file left `doing/` and `done/NNN-name/` or `blocked/NNN-name.md` exists — with no
   channel between them except files and git. The tracer (B1 + B2 with a fake `claude`) proves it.
7. Headless sessions on this machine are logged in. External state: checked right before the live check.

## Out of scope (deliberately)

- `.claude/settings.json` and the constitution: untouched. No new hook; no change to a hook.
- The tasks in the inbox: carried into `tasks/todo/` verbatim and **not** executed here (except
  nothing — the live check is its own task 000).
- A daemon, a systemd unit, a web view. The runner is one foreground command the operator starts;
  it exits when nothing can move.
- Parallel tasks. One task in `doing/` at a time, by the owner's rule.
- Retiring `supervisor.sh` and the feature DAG: both stay; the board is another way in.
- A deterministic gate for paid runs other than `run_audit_scenarios.py` (it is the only script
  here that starts paid sessions); for the rest the rule is text.

## Decisions (agent; two-way unless stated; to be logged AUTONOMOUS in escalations.md)

- **K1 one Python module, `.claude/unattended/board.py`, is the only reader of the board.** It
  parses a task (number, dependencies, audit flag, questions and answers) and makes every move that
  needs a decision: `next`, `start`, `import-inbox`, `unblock`, `where`, `audit-allowed`, `summary`.
  The shell runner and the audit runner both call it, so "what counts as answered" and "what counts
  as audit wanted" exist once.
- **K2 the task header is two plain lines, as the owner already writes them** in the seventeen
  inbox files: `Залежить від: 001, 010` and `Аудит потрібен: ні`, directly under the title. The
  template uses the same form. A dependency is every three-digit-or-longer number on that line;
  words without a number («дошка задач», «—») name no task and block nothing. A missing audit line
  means «ні».
- **K3 a dependency is met when `tasks/done/NNN-*/` exists.** `blocked/` and `doing/` do not count.
- **K4 "answered" means: the questions section has at least one `Відповідь:` line and none is
  empty.** A blocked task with no question at all stays blocked (nothing to answer means nobody
  answered).
- **K5 the inbox moves, it does not copy:** a file taken into `todo/` is removed from the inbox in
  the same step, otherwise the next pass would resurrect a task that has since gone to `done/`.
  Same number already in `todo/` → replaced (owner's rule). Same number in `doing/` or `done/` →
  left in the inbox untouched, with an event (owner's rule: nothing there is touched). Same number
  in `blocked/` → the inbox file replaces the blocked one (this is how an answer arrives when the
  owner does not use git); the normal unblock check then decides. This last case is the agent's
  addition; cost to reverse: one branch of one function.
- **K6 the agent moves a task to `done/` or `blocked/`; the runner moves it to `doing/`.** The
  runner never writes a report and never judges the work. If the task is in `done/` or `blocked/`
  on disk but `tasks/` has uncommitted changes, the runner commits `tasks/` only and logs it.
- **K7 the runner commits through `commit_checkpoint.sh --staged`,** which carries the branch check
  (`unattended/*` only). The runner itself refuses to start on any branch but `BOARD_BRANCH`
  (default `unattended/work`) — it switches to it when it exists and stops otherwise.
- **K8 continuing is `--resume <session_id>`** taken from the previous attempt's JSON, not `-c`:
  `-c` continues "the most recent conversation in the directory", which is somebody else's when an
  operator session ran in between. No session id in the output → a fresh conversation with a
  "continue the task" prompt.
- **K9 a usage-limit reply is not an attempt:** it waits 15 minutes and repeats, and does not count
  toward the three-without-a-commit stop. Detected as in the operator's `run-queue.sh` (same pattern).
- **K10 `git pull --rebase --autostash`; a conflict aborts the rebase and stops the runner** with
  `state=error reason=pull-conflict`. A remote branch that does not exist yet is not an error.
  Flags `--no-push` and `--once` (one task, then stop): the live check uses both, so the agent
  starts no push (ask-gated for the agent; the operator's queue pushes `unattended/*` afterwards)
  and the runner does not walk into task 001.
- **K11 the runner marks its sessions `CLAUDE_UNATTENDED_SESSION=1` and sets
  `.claude/state/overseer/mode` to `unattended` for its own lifetime** (restored on exit), so a
  planning gate parks instead of asking nobody.
- **K12 `--owner-approved` is refused inside a Claude Code session** (`CLAUDECODE` set), like
  `gate.py --close-escalation`: it is the owner's flag. The tests of the audit runner that use a
  fake `claude` point `--tasks-dir` at a fixture board that says «Аудит потрібен: так». The gate is
  a seat belt, not a lock — an agent that rewrites the task defeats it and the diff shows it;
  `docs/engine-limits.md` says so.
- **K13 `tasks/README.md` and `tasks/TEMPLATE.md` are in Ukrainian**, the language of the owner's
  tasks and of the section names the owner fixed; the short rule in `.claude/engine-rules.md` is in
  English like the rest of that file and quotes the two markers literally.
- **K14 state the operator reads, in `.claude/state/board/`:** `status` (one `key=value` line, like
  the operator's own status file), `events.log` (one UTC line per event), `costs.json` (per task:
  attempts, sessions, raw figures, total), `summary.md` (written at every stop), `logs/` (each
  attempt's raw output), `lock` (one runner at a time).

## Revisions after the critic (round 1: REVISE — one blocking, nine notes; all folded in)

- **R1 (blocking) the 3 USD limit gets a mechanism.** `BOARD_MAX_USD` (default: no cap) is the
  cap for one task. Every `claude -p` the runner starts carries `--max-budget-usd <what is left>`
  (cap minus the task's recorded total, K14); when nothing is left the runner stops with
  `state=stalled reason=budget` and exit 1. B3 tests on the fake `claude`: the flag is in argv, the
  remainder shrinks on a continuation, a task over the cap stops the runner. The live check runs
  with `BOARD_MAX_USD=3`.
- **R2 K5, the blocked case, tightened.** An inbox file replaces a blocked task only when it has at
  least one `Відповідь:` line and none is empty; otherwise it is `skipped` with an event and stays
  in the inbox. An inbox copy can no longer wipe the agent's questions.
- **R3 `next` and `doing/`.** The contract stays (a task in `doing/` is printed, exit 0); the
  runner decides by the parent directory of the printed path and calls `start` only for `todo/`.
  In the B2 test: a runner started with a task already in `doing/` makes no "to doing" commit.
- **R4 the stop counters survive a restart.** `costs.json` keeps, per task, `started_utc` (set once,
  at the move to `doing/`), `attempts_without_commit` and the session id. A restarted runner resumes
  the `doing/` task with the original start time and counter, so the twelve hours and the three
  attempts are properties of the task, not of the process. "A new commit" is a change of `HEAD`
  between the start and the end of an attempt (never `rev-list --all`).
- **R5 context budget counted first.** The closure is 191 of 200 lines here (CLAUDE.md 11,
  engine-rules 94, AGENTS 81, rules 5); the seeded project's is 149. B5 gets at most 7 lines in
  `engine-rules.md` and one row in `AGENTS.md`; the detail goes to `tasks/README.md`.
- **R6 the README covers both ways into `doing/`:** started by the runner — the file is already
  there, continue; started by hand — take the first eligible task and move it in a commit of its
  own. The B5 test accepts exactly that for the owner's first bullet of item 3.
- **R7 the mode file heals itself.** The runner saves the previous content of
  `.claude/state/overseer/mode` in `.claude/state/board/mode.before`, restores it in an EXIT trap,
  and at start restores a leftover `mode.before` first (a `kill -9` leaves one behind).
- **R8 the live check is one shot.** B5 freezes the README before B7; the text of `000-перевірка`
  is written in B7's plan before the run. Agent compliance with the README is the one premise only
  the paid run can test (premise 8 below); if the run fails, the cap bounds the loss, there is no
  second paid attempt, and the item is parked with the exact command.
- **R9 the gate and the fast suite.** `test_board.py` and `test_paid_run_gate.py` join
  `tests/fast-suites.txt` if they measure under about 2 s; `test_board_runner.py` stays out unless
  under about 5 s, with its measured time recorded there. All five suites that call
  `run_audit_scenarios.py` (`test_audit_tiers`, `test_audit_runner_resume`,
  `test_audit_turn_fixture`, `test_audit_verdict_parsing`, `test_audit_scene_gate_allow`) get the
  `--tasks-dir` fixture in B4.
- **Premise 8 (new):** a real headless session that is given only the task path and
  `tasks/README.md` performs the task, writes `report.md`, moves the task to `done/` and commits
  through `commit_checkpoint.sh`. Unverified until B7 — the live check is its test.

## After the critic's round 2: FEATURE_CRITIC_PASS — six notes, folded in at build time

- **N1 (must-fix, B1)** the questions section is the text under the heading `## Питання до власника`
  only; the body sentence «Питання до власника — у розділ нижче…» of tasks 012, 015, 060, 080 is not
  a section. The real inbox files are B1's fixtures, with question count and answered state asserted.
- **N2** whether `--max-budget-usd` on `--resume` counts the call or the conversation is unknown and
  may not be probed (it costs money). "Cap minus recorded total" errs toward stopping early, never
  toward overspending. The report says the resume semantics are unverified.
- **N3** `next` exits 3 when `todo/` is empty (`idle`) and 4 when `todo/` has tasks but none is
  eligible (`waiting-owner`); `summary` names a dependency that exists nowhere on the board.
- **N4** task 000 appends its line to this repository's `tasks/README.md` (the owner's example);
  the rule-text test reads for presence, so an appended line cannot turn it red, and the seed under
  `templates/project/tasks/` is not touched by the task.
- **N5** the no-commit counter is per task and is reset when a task leaves `doing/` (a B3 test).
- **N6** the tracer proves the runner's file and git mechanics; agent compliance with the README is
  proved by B7 alone, and the report says so.

## Slices (the DAG)

- **B1 board files and `board.py`** — delivers: `tasks/` with the four directories (`.gitkeep`),
  `README.md` (first version: how to use the board), `TEMPLATE.md`; their seeds under
  `templates/project/tasks/` and the `seed=` lines in `.claude/ownership.txt`; `board.py` with
  `parse`, `next`, `start`, `where`, `status`; `tests/test_board.py` (parsing the seventeen real
  inbox files included, as fixtures copied into the test, and a synthetic `engine.py install` that
  seeds the board once and never again). · contract out: the CLI below · depends on: — ·
  **TRACER BULLET, first half**
- **B2 runner, the thin loop** — delivers: `board-runner.sh`: lock, branch check, `next` → `start`
  → commit → fresh `claude -p` with the three flags → the task left `doing/`? → next; stop with a
  summary when `next` has nothing. `tests/test_board_runner.py` on a synthetic repository with a
  fake `claude` that performs the task (moves it to `done/` with a report and commits) and records
  its argv. · contract out: the state files · depends on: B1 · **TRACER BULLET, second half**
- **B3 runner, everything else** — delivers: fetch and `pull --rebase` before each task; inbox
  import; unblock; continue with `--resume`; the limit wait; cost per task; push after each task;
  the three-attempts and twelve-hour stops; `--once`, `--no-push`; the mode file; the leftover
  commit of `tasks/`. Each with a test on the fake `claude` (a bare repository as `origin`). ·
  depends on: B2
- **B4 the paid-run gate** — delivers: `run_audit_scenarios.py` refuses before the first session
  unless the task in `tasks/doing/` says «Аудит потрібен: так» or `--owner-approved` is given
  outside a Claude Code session; `tests/test_paid_run_gate.py` (both owner cases, the in-session
  refusal, no task in `doing/`, two tasks in `doing/`); the existing audit-runner suites pass
  `--tasks-dir` to a fixture. · depends on: B1
- **B5 the rules** — delivers: the short board rule and the paid-run rule in
  `.claude/engine-rules.md` (within the 200-line budget, `tests/test_context_budget.py`); the full
  agent rules and the paid-run rule in `tasks/README.md` and its seed; `AGENTS.md` key path;
  `evals/README.md`, `.claude/unattended/README.md`, `docs/engine-limits.md`; a test that the
  rule text names every owner bullet of item 3 and item 4. · depends on: B3, B4 (it describes them)
- **B6 the board starts full** — every file of `~/engine-ops/tasks-inbox/` moved into
  `tasks/todo/` through `board.py import-inbox`, byte-identical (checked with `cmp` before the
  inbox copy is removed), one commit. · depends on: B3
- **B7 live check, report, operator instruction, summary** — task `000-перевірка` through the real
  `claude` with `board-runner.sh --once --no-push`, cost read from `costs.json`; the full suite,
  the golden set, ruff, mypy; the three documents. · depends on: all

## Inter-slice contracts

- **B1 → B2, B3, B4 (the CLI of `board.py`; `--root` defaults to the repository the script is in):**
  - `next` → prints the path of the first file in `todo/` (ascending number) whose dependencies are
    all in `done/`; exit 0. Nothing eligible → prints nothing, exit 3. A task already in `doing/` →
    prints it, exit 0 (one at a time: finish what is started).
  - `start <todo-path>` → moves the file to `doing/`; refuses (exit 2) when `doing/` holds a task.
  - `where <NNN-name>` → prints `todo|doing|blocked|done|missing`.
  - `import-inbox <dir>` → applies K5; prints one line per file (`imported|replaced|answered|skipped`).
  - `unblock` → moves every answered task (K4) from `blocked/` to `todo/`; prints their names.
  - `audit-allowed [--tasks-dir D]` → exit 0 when exactly one task is in `doing/` and it says
    «Аудит потрібен: так»; exit 1 with the reason otherwise.
  - `summary` → the board in a dozen lines: counts, what is blocked and on which question, what
    waits on which dependency.
  - No command of `board.py` runs git; staging and committing are the runner's (and the agent's).
- **B2/B3 → the operator (state files, K14):** `status` is exactly one line,
  `state=<running|waiting-limit|idle|waiting-owner|stalled|deadline|error> task=<name|-> since=<UTC> [reason=…]`;
  the runner's exit code is 0 for `idle` and `waiting-owner`, 1 otherwise.
- **B3 → the agent (the prompt):** the first prompt names the task file in `doing/` and
  `tasks/README.md`; the continue prompt names the same file. Nothing else passes between them.
- **B4 → B5:** the refusal text of the audit runner names the two ways through; the rules quote it.

## Integration exit criterion

The tracer (B1 + B2): in a synthetic repository, one task in `todo/`, a fake `claude` that does
what the README tells an agent to do; `board-runner.sh` ends with the task in `done/NNN-name/`
(task.md and report.md), two commits (to `doing/`, to `done/`), `status` saying `idle`, and the
fake's recorded argv carrying `-p`, `--settings .claude/settings.json`, `--permission-mode auto`,
`--output-format json`. Then the same with the real `claude` (B7).

## Deferred to later features

- Escalations and lesson promotions arriving as blocked tasks — the owner's own tasks 005 and 040.
- Push without asking — the owner's task 006.
- A paid-run line with a dollar limit read by a machine (`Платні прогони: … не більше 30 доларів`
  in task 010): the rule text honours it; only the audit flag is enforced by a script.

## Open items requiring human decision

- none at planning time.
