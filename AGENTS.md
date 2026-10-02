# Agents guide — claude-cli-config

> Loaded into every session via `@AGENTS.md` in CLAUDE.md. Keep it under ~200
> lines and keep it true — anything stale here is stale in every session's
> context, including unattended ones.

## Project in one sentence

A Claude Code configuration template: a constitution-governed agentic build
system — four descending design levels, five blind critics, seven enforcement
hooks, and a supervisor that runs the whole thing unattended — meant to be
copied into a real project.

## What is unusual about this repo

It is the template, not a consumer of the template. There is no application
source: no `src/`, no `tests/`, no `pyproject.toml`. The "code" is the skills,
hooks, and supervisor under `.claude/`. Two consequences that surprise people:

- `.claude/project.env` here describes the engine itself: `SOURCE_DIRS` names the
  hook, harness, evals and suite directories, `CODE_EXTENSIONS="py sh"`, and
  `TEST_CMD` runs the whole suite — so the Stop gate verifies the engine's own code
  (about 100 s per gated turn end). The seed a target project receives
  (`templates/project/.claude/project.env`) still says `src` and `py`.
- Work here is config and infrastructure. The backlog lives in
  `.engine/architecture/feature-dag.json`, not in a issue tracker.

## Active agents

| Agent | Layer | Entry point |
|---|---|---|
| `master-architect` | Design (project) | `/master-architect` |
| `feature-architect` | Design (feature) | `/feature-architect` |
| `mvp-architect` | Design (cheapest thing that answers one question) | `/mvp-architect` |
| `plan-slice` | Design (slice contract) | `/plan-slice` |
| `slice-builder` | Build | invoked with a slice contract |
| `overseer` | Audit | auto-triggered by the Stop hook |
| `self-learning-orchestrator` | Memory | session start/end, `/lesson`, `/wrap-up` |
| `documentation` | Docs | any README/ADR/AGENTS.md work |

Critics (fresh-context, blind, in `.claude/agents/`): `master-critic`,
`feature-critic`, `slice-planner-critic`, `mvp-critic`, all inheriting
`critic-core`.

## Pipeline

`/master-architect` → `/feature-architect` → `/plan-slice` → `slice-builder` →
`overseer` (auto). Agents communicate through **files, never chat**.

Unattended, `.claude/unattended/supervisor.sh` drives the loop: it spawns a
session per DAG node, restarts one that dies, and stops on a terminal state.

## Key paths

| Path | What it is |
|---|---|
| `.claude/constitution.md` | 8 articles. Human-only. Overrides everything. |
| `CLAUDE.md` | Standing policy: permissions, verdict routing, session contract |
| `.claude/skills/`, `.claude/commands/` | Agent definitions |
| `.claude/agents/` | The five critics |
| `.claude/hooks/` | 9 enforcement hooks, wired in the project's `settings.json` only — nothing the engine ships puts a hook under `~/.claude/` |
| `.engine/` | What the agent produces while working: records, slice contracts, architecture, premises, spikes, PROGRESS. Not protected by Claude Code — that is the point (`docs/engine-limits.md`) |
| `.claude/state/` | Machine state, written by hooks and scripts only; one line in `.gitignore` |
| `user/` | The owner's own: personal skills (`install.sh`) and `user/settings.json`, the personal settings layer (`engine.py install --personal`). Never ships. |
| `docs/tasks/` | Proposals the engine may not apply itself (`.claude/settings.json`), each with its test and one apply command |
| `docs/engine-limits.md` | What the guarantees assume: one session, one repository; hooks guard tool calls, not scripts |
| `.claude/unattended/` | Supervisor, state machine, rotation, park re-check |
| `.engine/overseer/` | `ledger.md`, `parked.md`, `audit.md`, `escalations.md`, `MEMORY.md` |
| `.engine/architecture/feature-dag.json` | The work queue |
| `.engine/premises/premise-log.md` | Load-bearing assumptions and what depends on them |
| `.claude/references/` | System-design and software-architecture playbooks |

## Rules that bite

- **Never `git commit`.** Denied in `settings.json` and blocked by
  `block-dangerous.sh`. Stage, summarise, suggest a message, stop.
- **Never edit `.claude/constitution.md`.** Propose in `audit.md` instead.
- **Hooks need `jq` or `python3`.** The bash hooks parse stdin with `jq`, falling back
  to `python3`; with neither, the two deny hooks refuse every call rather than allow it.
- **`*.env` is unwritable** — `protect-paths.sh` cannot tell a config file from a
  secrets file by name. One narrow exception: `.claude/project.env`, the
  template's own committed config, which Step 2 of setup tells you to edit.
  Everything else matching `*.env` is denied, so name new config files `.sh`.
- **Hooks guard tool calls, not scripts.** `block-dangerous.sh`, `protect-paths.sh`
  and the `permissions.deny` list all evaluate the Bash call the agent issues.
  A command run from INSIDE a shell script is seen by none of them — verified
  2026-08-27: `git commit --dry-run` is refused at top level and executes
  untouched from a two-line script. So a script the agent writes is a hole
  through every hook in this repo. Put the check inside the script too, and
  treat "a hook enforces this" as true only of what is typed directly.
- **Three legitimate stops only**: a human-only input, a falsified premise
  invalidating committed work, or an empty unblocked queue. Everything else is
  decided, logged, and continued.

## Verifying a change to this repo

There is no application test suite. Exercise the thing you changed and show the
negative case:

```bash
command -v jq || command -v python3                  # one of them must exist
python3 .claude/hooks/overseer_stop.py --dry-run     # always emits a block
python3 tests/test_format_on_edit.py           # 22 cases, exits 1 on any fail
python3 tests/test_deny_gaps.py               # 10 blocked / 9 allowed
python3 tests/test_overseer_continue.py       # the loop cannot silently stop
python3 tests/test_decision_logged.py         # no unlogged autonomous deviation
python3 tests/test_engine_lint.py             # ruff --isolated + mypy --strict on the engine's own Python
python3 .claude/unattended/test_selfref.py          # no self-spawning DAG node
bash tests/run_all.sh                                # the whole set, one summary line per suite
bash .claude/unattended/supervisor.sh --status       # state, restarts, spend
```

A hook change is not verified until you have seen it **block** something it
should block — a passing allow-case proves nothing, because a dead hook also
allows. Where the hook's tool is absent from the machine, put a **shim on PATH
that records its argv**: that shows the hook issuing the right command without
pretending the tool is installed. See `.engine/overseer/MEMORY.md`.

`tests/` holds every check of this repository — hooks, harness, installer, evals
instruments — and `bash tests/run_all.sh` runs the whole set, by hand after a slice and
from the Stop gate whenever a `.py` or `.sh` file changed (`TEST_CMD` in this repository's
`.claude/project.env`). Left empty, `verify-on-stop.sh` would run `pytest -x` here because
a `tests/` directory exists, and pytest is not installed.