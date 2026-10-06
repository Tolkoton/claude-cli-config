# Agents guide — claude-cli-config

> Loaded into every session via `@AGENTS.md`. Keep it short and true: anything stale here is
> stale in every session's context. Budget: CLAUDE.md + this file + every import ≤ 200 lines
> (`tests/test_context_budget.py` counts).

## Project in one sentence

A Claude Code configuration template: a constitution-governed agentic build system — four
descending design levels, five blind critics, enforcement hooks, and a task board whose runner works
through it unattended — meant to be installed into a real project by `engine.py`.

## What is unusual about this repo

It is the template, not a consumer of it: no `src/`, no application tests, no `pyproject.toml`.
The "code" is the skills, hooks, installer and harness under `.claude/`, `engine.py`, `evals/`
and `tests/`, and `.claude/project.env` here describes the engine itself, so the Stop gate
verifies the engine's own code (how: `docs/working-on-the-engine.md`). The backlog is
the task board (`tasks/`), not an issue tracker; `.engine/architecture/feature-dag.json` is the
slice graph `/feature-architect` plans a feature into.

## Active agents and pipeline

`/business-analyst` (level 0: the owner's goals → `.engine/goals.md`, sealed; architects cite its lines) →
`/master-architect` (project design) → `/feature-architect` (feature → slice DAG) →
`/plan-slice` (slice contract) → `slice-builder` (TDD build) → `overseer` (audit by a fresh agent, requested
by the Stop hook). A slice with a sealed contract passes the `test-manager` twice (read-only: who writes the contract tests before the code — the `slice-tester`, blind to the code, or the builder; what is checked or deferred after it); `testing.py` holds the cases it cannot cancel.
Also `/mvp-architect` (the cheapest thing that answers one question),
`/onboard` (first meeting with an existing project, with its owner → `.engine/onboard/profile.md`), `/bugfix` (one bug in full → `.engine/bugs/`, proved by `bugfix.py prove`), `/hotfix` (the owner's urgent fix: a hard limit, a debt in `.engine/debt.md`), `/maintain` (weekly care: a report in `.engine/maintain/`; dependency updates are the runner's, on the owner's «так»),
`self-learning-orchestrator` (memory), `documentation` (docs), `simplifier` (what can go; on a signal only). Critics in
`.claude/agents/` (`master-`, `feature-`, `slice-planner-`, `mvp-critic`, all inheriting
`critic-core`) are fresh-context and blind. Agents communicate through files, never chat.
Unattended work goes through the task board only: `.claude/unattended/board-runner.sh` takes one
task at a time, each in a fresh session.

## Key paths

| Path | What it is |
|---|---|
| `.claude/constitution.md` | 8 articles. Human-only. Overrides everything. |
| `.claude/engine-rules.md` | The standing rules every project imports (installed by engine.py) |
| `.claude/references/` | Read on demand: `hooks.md`, `unattended.md`, the design playbooks |
| `.claude/skills/`, `.claude/commands/`, `.claude/agents/` | Agent definitions and the critics |
| `.claude/hooks/` | The hooks, wired only in the project's `settings.json` |
| `.claude/state/` | Machine state, written by hooks and scripts only; one `.gitignore` line |
| `.engine/` | What the agent produces: records, slices, architecture, premises, PROGRESS |
| `.engine/goals.md` | The project's goals; changed only by the owner's answer (`goals.py`). This repository has none yet |
| `tasks/` | The task board: `todo/ doing/ blocked/ done/`; `board-runner.sh` works from it (`tasks/README.md`) |
| `docs/working-on-the-engine.md` | Read on demand: the verification commands, the rarer paths (ownership, seeds, `user/`, limits) |
| `docs/release.md` | The release order: `engine.py release <version>`, the owner's command only |
| `evals/`, `tests/` | The measuring instruments and every check of this repository |

## Rules that bite

- **Never edit `.claude/constitution.md` or `.claude/settings.json`**; propose in `audit.md`
  or `docs/tasks/`.

## Verifying a change

Exercise the thing you changed and show the negative case: a hook change is not verified until
you have seen it **block** something. Where a tool is absent, a PATH shim that records its argv
shows the hook issuing the right command.

`bash tests/run_all.sh` runs every suite (the pre-tag check), `--fast` the Stop-gate subset; the
other commands and what the Stop gate runs here: `docs/working-on-the-engine.md`.
