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
