# Feature engine-package-3c-fix — decomposition

Frame source: `docs/plan/package-3c-fix.md` (the owner's text, verbatim; it ends mid-sentence
at item 6 "Тест:" — the test for item 6 is therefore an **agent decision**, marked below).
Every numbered item is an owner requirement; the critic checks how it is met.

## The defect

`engine.py` (package 3c) migrates a project's data but not its machine state. On a v0.10.1
project the state sits at the old paths (`.claude/overseer/{mode,.last_audit_sha,…}`,
`.claude/unattended/{state.json,…,logs/,archive/}`); the new map's `engine .claude/**`
catch-all owns them, so an update removes those whose blob matches engine history ("retired"
— `mode=unattended` vanished), holds back the rest as "edited" forever (exit 1 every time),
and the new .gitignore block no longer ignores the old paths.

## Slices

- **X1 state-migration** (items 1, 2) — `STATE_MIGRATIONS` in engine.py: every old state path
  → its `.claude/state/<component>/<same name>`; a pattern entry (`.claude/overseer/.budget-*.json`)
  moves each match; `logs/` and `archive/` move as directories. **Guard**: if the old
  `supervisor.lock` exists or the old `heartbeat` is fresh (younger than the harness's stall
  timeout, 900 s — agent decision on the threshold, read from config.sh's default) the state
  is NOT moved: every state path is reported as `keep … stop the unattended supervisor
  first`, the run exits 1, and the project's data still moves. · depends on: —.
- **X2 ownership-and-ignore** (item 3) — legacy `machine` rules for every old state path,
  placed before `engine .claude/**` (so retire and keep can never touch them; the
  machine-state note still reports them if tracked); the .gitignore block (built from the
  `machine` rules) therefore lists the old paths too, and this repository's own .gitignore
  lists them for the transition. · depends on: —.
- **X3 tests** (item 4) — `tests/test_state_migration.py`: a v0.10.1 install and a hand copy
  of v0.8.0, each with live state at the old paths (incl. `.budget-x.json`, `logs/`,
  `archive/`); after `update --ref HEAD`: all state at the new paths byte for byte, no
  `remove`, no `keep`, exit 0, second run changes nothing; the supervisor.lock case: state
  stays, data moves, exit 1, message names the supervisor; the owner's reproduction
  (mode=unattended + .last_audit_sha) verbatim. · depends on: X1, X2.
- **X4 decana** (item 5) — read-only `update --dry-run` on the real project: state moves
  listed, no keep/remove for state files, exit 0. · depends on: X1, X2.
- **X5 write-rules** (item 6) — `docs/tasks/settings.json` drops the twelve `Write(...)` deny
  rules; **test (agent decision, the frame is cut off here)**: `tests/test_settings_proposal.py`
  asserts the proposal has no `Write(` deny rule, that every rule removed relative to the live
  file is a `Write(...)` whose `Edit(...)` twin is present in the proposal, and lists the deny
  difference with that reason. · depends on: —.
- **X6 records** — report, DAG, ledger, parked (C8b, C9 unchanged). · depends on: X1–X5.

### Addendum (items 7–9, received after X6 shipped)

- **X7 own-project-env** (item 7) — this repository's `.claude/project.env`: `SOURCE_DIRS`
  names the engine's code directories (`.claude/hooks .claude/unattended evals tests`),
  `CODE_EXTENSIONS="py sh"` (the hooks are shell — agent decision), `TEST_CMD="bash
  tests/run_all.sh"`. **Prerequisite found while probing**: `overseer_stop._is_code_path`
  matches a multi-segment `SOURCE_DIRS` entry (`.claude/hooks`, or the documented
  `backend/src`) only against a RELATIVE path; Claude Code hands the hook absolute paths, so
  the setting would be inert. Fix the matcher (a directory entry matches when `/<entry>/`
  occurs in the path) with its own suite. AGENTS.md's two paragraphs on this file and the
  `3c-C7-test-cmd` decision are superseded. Measure `bash tests/run_all.sh` wall time for
  the report, and run the live Stop hook once against a dirty tree to see it call the suite.
  · depends on: —.
- **X8 audit-runner-resume** (item 8) — `evals/run_audit_scenarios.py` writes `--out` after
  every RUN (finer than the owner's "every scenario": a crash on run 3 of 3 keeps runs 1–2)
  with `"status": "partial"` and the pending ids; `--resume` reloads an existing `--out`,
  keeps every recorded run and performs only the missing ones; the file's `engine_ref`,
  `model`, `setting_sources` and `runs_per_scenario` must equal the invocation's or the
  runner refuses (exit 2) — mixing engines in one file is worse than a crash. Without
  `--resume` an existing `--out` is refused too (agent decision: forgetting the flag must
  not destroy paid results). Ctrl-C leaves a partial file and says how to resume.
  **Test** `tests/test_audit_runner_resume.py`: a `claude` shim on `--claude` that answers
  `--version`, prompt A (json with a session_id) and prompt B (stream-json with an
  OVERSEER_PASS text block and a cost), records every call in a log, and on the Nth call
  kills the runner (SIGKILL on its parent); asserts the partial file holds exactly the runs
  paid for; a `--resume` run completes the file, re-runs none of them (call log), and the
  final file is `complete` with the summed cost; the two refusals. Real sandboxes
  (`make_sandbox.sh`, ~1.4 s each), `--only` to keep it to three scenarios.
  · depends on: —.
- **X9 deny-hooks-typing** (item 9) — `tests/test_deny_hooks.py` clean under
  `mypy --strict`, 66 cases unchanged. The owner's "45" is the LINE count of mypy's output
  (9 errors + 36 overload-variant notes); the report's figure was wrong and is corrected.
  · depends on: —.
- **X10 records** — report, DAG, ledger, escalations. · depends on: X7–X9.

## Contracts

- X1 → X3: the state table is the single source for both the moves and the test's list of
  old paths (the test imports `STATE_MIGRATIONS`).
- X2 → X1: `plan_sync` must evaluate the legacy machine rules BEFORE the retire step, which
  it does by rule order alone; the test asserts "no remove, no keep" against the plan text.

## Premises

- The harness's heartbeat is written every 30 s while a session runs (session-claude.sh);
  `STALL_TIMEOUT_SEC` defaults to 900 (config.sh) — the freshness threshold.
- Claude Code 2.1.287 warns at session start that `Write(<path>)` permission rules are not
  matched by file permission checks (observed in C5; recorded as a FINDING).

## Critic

Round 1: REVISE — X1 must depend on X2 (the guard-skip branch leaves old-path state in place, which only the legacy machine rules protect). Applied: dependency added, the lock case asserts no `remove` for state and that the only `keep` lines are the guard's own.

Round 2 (addendum X7–X10): REVISE — (blocking) X8 must compare a RESOLVED commit, not the
`--engine-ref` string: a partial file saying `HEAD`, new commits, then `--resume` would mix
two engines. Also: write-to-temp + `os.replace` and "valid JSON after the kill" in the test;
the shim's kill pinned to a run boundary (the prompt-A call of run N); the authoritative
run_all.sh timing moves to X10 (X8 adds a suite); the matcher suite gains suffix look-alikes
(`other-src/`, `x.claude/hooks/`) and the final-segment case; the matcher fix and the
project.env edit ship as separate commits; README notes the refusal of an unflagged `--out`.
All applied. Found while applying, outside the critic's view: run from the Stop hook the suite
inherits `CLAUDE_PROJECT_DIR`, and `tests/test_deny_gaps.py` let the hook read this
repository's branch from it — green by hand, red under the gate (X7 pins it like
test_deny_hooks does); and `tests/test_no_machine_paths.py` rejects `/home/<name>/` even in
a docstring example.
