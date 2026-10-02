# Feature engine-package-3c — decomposition

Frame source: `docs/plan/package-3c.md` (the owner's text, verbatim). Every numbered item
there is an **owner requirement** (not reviewed by architect or critic); what the critic
checks is how each is met. Choices a requirement leaves open are **agent decisions**, marked
below and logged as AUTONOMOUS in the escalations record.

## Goal and principle

Separate what defines and constrains the agent from what the agent produces. `.claude/` is
protected by Claude Code (every agent-tool write there is shown to a human or a classifier)
and keeps everything that defines, configures or feeds the gates — settings, hooks, skills,
agents, commands, the constitution, the ownership map, the unattended harness,
`project.env`, and ALL machine state (written by hooks and scripts, never by agent tools, so
it raises no prompt). `.engine/` is unprotected and receives what the agent produces while
working: the overseer's records, slice contracts, architecture, premises, spikes, PROGRESS.

## Acceptance (the plan's "ГОТОВО, КОЛИ")

1. Every test suite green.
2. Scenario set identical to `results-package-3b-finish.json` except intended, listed
   differences; new reference `evals/baseline/Laos-MacBook-Pro/results-package-3c.json`.
3. The audit behaves the same after the move as before (`audit-pre-3c.json` vs
   `audit-post-3c.json`); every difference explained. Budget for both runs: $60.
4. `engine.py update --dry-run` on the real `~/Documents/GitHub/decana` (read-only) shows
   adoption and migration with no loss.
5. ruff and mypy --strict clean; the ownership map knows the new paths.

## The new layout (agent decisions on names, marked)

| was | becomes | owner |
|---|---|---|
| `.claude/overseer/{ledger,audit,escalations,parked,MEMORY}.md` | `.engine/overseer/<same>` | project (seeded) |
| `.claude/overseer/slice/` | `.engine/slices/` | project |
| `.claude/architecture/` | `.engine/architecture/` | project |
| `.claude/premises/` | `.engine/premises/` | project (premise-log seeded) |
| `.claude/artifacts/` | `.engine/artifacts/` | project |
| `PROGRESS.md` | `.engine/PROGRESS.md` | project |
| `.claude/overseer/_template.md` | `.claude/templates/slice-contract.md` | engine |
| `.claude/overseer/{.last_audit_sha,.last_continue_sha,.continue_count,mode,state,.budget-*.json,complexity-report.md}` | `.claude/state/overseer/<same>` | machine |
| `.claude/unattended/{state.json,cost.json,heartbeat,restarts.log,sim-plan.txt,supervisor.lock,logs/,archive/}` | `.claude/state/unattended/<same>` | machine |
| (new) contract fingerprints | `.claude/state/contracts/<slug>.sha256` | machine |

Agent decisions: `.engine/slices/` is the plan's word; `.claude/state/<component>/<file>`
keeps each file's old name under its component so every reader changes one prefix;
`.claude/state/` is ONE line in `.gitignore` and ONE `machine` rule in the map;
`settings.local.json` and `worktrees/` stay where Claude Code itself puts them. The old
record paths get explicit `project` rules in the map ("legacy, migrated by engine.py") so
a project's un-migrated record can never be swept up by the engine-retirement step.

## Slices (the DAG)

- **C1 audit-pre** (item 1) — `evals/run_audit_scenarios.py --runs 3` on the plan commit
  (`2788357`, pinned so later commits cannot leak into its sandboxes) →
  `audit-pre-3c.json`. Started before any skill text changed. · depends on: —.
- **C2 the-move** (item 2) — the layout above applied to this repository: `git mv` of the
  engine's own records and template; every hook, script, skill, agent, command, scenario,
  test, doc and the ownership map and `.gitignore` updated; seeds mirror the new paths
  (`templates/project/.engine/...`); `make_sandbox.sh` lays the audit fixture at
  `.engine/PROGRESS.md`; `run_audit_scenarios.py` reads `.engine/overseer/ledger.md`.
  Closed records are moved, never rewritten. **Tracer bullet**: the hook scenarios and the
  hook-checks must stay green with only the path changes — that is the one chain crossing
  hooks, harness, evals and tests. · depends on: —.
- **C3 migration** (item 3) — `engine.py` carries an explicit old→new table; `update`, and
  `install` on a copy without a lock, move each old path that exists to its new place
  (file by file for directories), report and touch nothing when the file exists in both
  places, show it all under `--dry-run`, and do nothing on a second run. Tests: a project
  installed from v0.10.1, a hand copy of v0.8.0, a conflict, idempotence; plus the real
  decana dry run. · depends on: C2.
- **C4 contract-fingerprint** (item 4) — `.claude/hooks/contract_fingerprint.py seal
  <contract>` writes `sha256` to `.claude/state/contracts/<slug>.sha256` and refuses to
  overwrite; `check <contract>` compares. `plan-slice` seals after the critic's PASS and
  the write. `overseer_stop.py`, before injecting the audit request, finds the active
  contract (the IN PROGRESS slice in `.engine/PROGRESS.md`, as complexity_budget does)
  and compares: changed → no audit; the hook blocks with an escalation instruction
  instead. No fingerprint (a contract approved before 3c) → audit as before. Tests for
  both cases and for the refused overwrite. · depends on: C2.
- **C5 retire-approval-hook, settings-for-headless** (items 5, 6) — `approve-project-data.py`
  and its test removed; `docs/tasks/settings.json` drops its handler (proposal + command;
  the live file carries it since F8 and is the owner's); `session-claude.sh` adds
  `--settings "$PROJECT_ROOT/.claude/settings.json"`; a real session in this (trusted)
  repository with `--debug` counts hook executions with and without `--settings` to show
  the identical handlers run once. · depends on: C2.
- **C6 retire-claude-autonomy** (item 7) — the skill directory removed; of its three
  references, the still-true ones move to `.claude/references/` (reviewed one by one),
  stale ones are deleted; `test_hook_copies_in_sync.py` removed; every mention updated
  (the hook messages still say "claude-autonomy safety hook" only if a scenario's
  `expect_detail_contains` needs it — checked). · depends on: C2.
- **C7 tidy** (item 8) — `hook-checks/` → `tests/` (git mv; `verify-on-stop.sh` would then
  run `pytest -x` here on every Python change, so this repository's `project.env` sets
  `TEST_CMD` explicitly — agent decision, logged); `.claude/unattended/test_selfref.py` →
  `tests/`; seeds verified against the new paths. · depends on: C2–C6.
- **C8 records** (item 9 + acceptance) — `docs/engine-limits.md` (project.env never
  auto-approved; the `.claude/`/`.engine/` boundary), docs, ownership completeness,
  `results-package-3c.json`, the post-move audit run and its comparison, the report. ·
  depends on: C1–C7.
- **C9 apply-settings (PARKED, owner)** — the proposal in `docs/tasks/`.

## Inter-slice contracts

- C2 → C3: the old→new table in `engine.py` IS the table above; the test for C3 builds its
  "v0.10.1 project" from the real tag, so the table and the move cannot disagree silently.
- C2 → C4: the contract path the overseer reads is `.engine/slices/<slug>.md`; the
  fingerprint lives under `.claude/state/contracts/`.
- C1 → C8: the post run uses the same model/setting sources and `--runs 3`; the comparison
  is per scenario (matched runs out of 3) and every difference is explained.

## Premises

- P1 Claude Code protects writes under `.claude/` in auto mode (the classifier) — the
  frame's premise, observed in this run when the classifier refused a read-only git check.
- P2 Headless sessions in a never-trusted directory ignore the project's settings; in a
  trusted one `--settings <same file>` defines identical handlers, which run once
  (code.claude.com/docs/en/hooks). C5 measures it.
- P3 `verify-on-stop.sh` auto-runs `pytest -x` when a `tests/` directory exists and a `.py`
  changed (AGENTS.md) — the reason C7 sets TEST_CMD.

## Open items requiring human decision

None that block. C9 parked. If the classifier refuses the audit sessions, C1/C8 park with
the exact command (it has not refused so far: C1 is running).
