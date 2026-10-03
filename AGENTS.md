# Agents guide — claude-cli-config

> Loaded into every session via `@AGENTS.md`. Keep it short and true: anything stale here is
> stale in every session's context. Budget: CLAUDE.md + this file + every import ≤ 200 lines
> (`tests/test_context_budget.py` counts).

## Project in one sentence

A Claude Code configuration template: a constitution-governed agentic build system — four
descending design levels, five blind critics, enforcement hooks, and a supervisor that runs the
whole thing unattended — meant to be installed into a real project by `engine.py`.

## What is unusual about this repo

It is the template, not a consumer of it: no `src/`, no application tests, no `pyproject.toml`.
The "code" is the skills, hooks, installer and harness under `.claude/`, `engine.py`, `evals/`
and `tests/`. Consequences: `.claude/project.env` here describes the engine itself
(`SOURCE_DIRS` names the hook, harness, evals and test directories, `CODE_EXTENSIONS="py sh"`,
`TEST_CMD` runs the suites), so the Stop gate verifies the engine's own code; the seed a target
project receives (`templates/project/`) still says `src` and `py`. The backlog is
`.engine/architecture/feature-dag.json`, not an issue tracker.

## Active agents and pipeline

`/master-architect` (project design) → `/feature-architect` (feature → slice DAG) →
`/plan-slice` (slice contract) → `slice-builder` (TDD build) → `overseer` (audit, auto-triggered
by the Stop hook). Also `/mvp-architect` (the cheapest thing that answers one question),
`self-learning-orchestrator` (memory), `documentation` (README/ADR/AGENTS work). Critics in
`.claude/agents/` (`master-`, `feature-`, `slice-planner-`, `mvp-critic`, all inheriting
`critic-core`) are fresh-context and blind. Agents communicate through files, never chat.
Unattended, `.claude/unattended/supervisor.sh` spawns a session per DAG node and restarts one
that dies.

## Key paths

| Path | What it is |
|---|---|
| `.claude/constitution.md` | 8 articles. Human-only. Overrides everything. |
| `.claude/engine-rules.md` | The standing rules every project imports (installed by engine.py) |
| `.claude/references/` | Read on demand: `hooks.md`, `unattended.md`, the design playbooks |
| `.claude/skills/`, `.claude/commands/`, `.claude/agents/` | Agent definitions and the critics |
| `.claude/hooks/` | The hooks, wired only in the project's `settings.json` |
| `.claude/ownership.txt` | Who owns every path: engine, project, machine, user (read by engine.py) |
| `.claude/state/` | Machine state, written by hooks and scripts only; one `.gitignore` line |
| `.engine/` | What the agent produces: records, slices, architecture, premises, PROGRESS |
| `templates/project/` | The seeds a new project starts from (CLAUDE.md, AGENTS.md, records) |
| `user/` | The owner's own skills and settings layer. Never ships. |
| `docs/tasks/` | Proposals the engine may not apply itself, each with a test and one command |
| `docs/engine-limits.md` | What the guarantees assume |
| `evals/`, `tests/` | The measuring instruments and every check of this repository |

## Rules that bite

- **Never `git commit`** outside an `unattended/<date>` branch; `block-dangerous.sh` matches
  the whole command text, so a message that mentions a dangerous command goes through `-F`.
- **Never edit `.claude/constitution.md` or `.claude/settings.json`**; propose in `audit.md`
  or `docs/tasks/`.
- **`*.env` is unwritable** except `.claude/project.env`; name new config files `.sh`.
- **Hooks guard tool calls, not scripts** — a script you write must carry the check itself
  (`.claude/references/hooks.md`).
- **Hooks need `jq` or `python3`**; with neither the deny hooks refuse every call.
- **Three legitimate stops only**: a human-only input, a falsified premise behind committed
  work, an empty unblocked queue.

## Verifying a change

Exercise the thing you changed and show the negative case: a hook change is not verified until
you have seen it **block** something. Where a tool is absent, a PATH shim that records its argv
shows the hook issuing the right command.

```bash
bash tests/run_all.sh                 # every suite, one line each (the pre-tag check)
bash tests/run_all.sh --fast          # the Stop-gate subset
python3 evals/run_hook_scenarios.py --engine-ref HEAD --compare evals/baseline/Laos-MacBook-Pro/results-package-costs.json
python3 .claude/hooks/overseer_stop.py --dry-run     # always emits a block
bash .claude/unattended/supervisor.sh --status
```

`tests/` holds every check of this repository; the Stop gate runs `TEST_CMD` from
`.claude/project.env` whenever a `.py` or `.sh` file changed. Left empty it would run
`pytest -x`, which is not installed here.
