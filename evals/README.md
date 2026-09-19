# evals — the measuring instrument

Everything here exists to answer one question before and after any change to the engine:
**did behaviour change, and if so, was that intended?** Nothing in this directory is loaded
by Claude Code, wired into `settings.json`, or copied into a target project.

## What is here

| Path | What it is |
|---|---|
| `reference-project/` | A tiny, fully typed Python project (uv, ruff, mypy, pytest). Real code for the hooks to act on. |
| `make_sandbox.sh` | Builds a disposable git repository: the reference project + the engine from ONE git ref, installed the way `docs/TEMPLATE-SETUP.md` installs it today. |
| `run_hook_scenarios.py` | Feeds each hook the JSON envelope Claude Code would send and records what the hook decided. Deterministic, no model involved. |
| `compare.py` | Diffs two result files. The differences are what changed between two engine versions, two machines, or two hook directories. |
| `scenarios/hooks/*.json` | 65 scenarios as data. `expect` describes the current engine; `why` says what each one protects. |
| `scenarios/audit/*.md` | 10 scripted turns for the overseer's 12-check audit. Run by hand in a real Claude Code session. |
| `baseline/` | Recorded results. `clean-ubuntu-24.04/` was recorded on a machine with none of the author's tooling. |

## Quick start

```bash
# 1. A sandbox per engine version. Always OUTSIDE this repository, always fresh.
evals/make_sandbox.sh v0.9.0 ~/engine-sandboxes/v0.9.0
evals/make_sandbox.sh v0.8.0 ~/engine-sandboxes/v0.8.0

# 2. Current engine: expectations are enforced (exit code 1 on any mismatch).
python3 evals/run_hook_scenarios.py --sandbox ~/engine-sandboxes/v0.9.0 --out results-v0.9.0.json

# 3. Older engine: record only, then look at what differs.
python3 evals/run_hook_scenarios.py --sandbox ~/engine-sandboxes/v0.8.0 --record-only --out results-v0.8.0.json
python3 evals/compare.py results-v0.8.0.json results-v0.9.0.json --details

# 4. This machine against the clean reference machine — should be identical.
python3 evals/compare.py evals/baseline/clean-ubuntu-24.04/results-v0.9.0.json results-v0.9.0.json
```

Any directory of hooks can be measured, not only a sandbox's own — for example the user-level
copies in the home folder, or the `.claude/hooks/` of an existing project (read-only: the hooks
run against the sandbox, never against that project):

```bash
python3 evals/run_hook_scenarios.py --sandbox ~/engine-sandboxes/v0.9.0 \
  --hooks-dir ~/.claude/hooks --record-only --out results-home-hooks.json
```

## Reading an outcome

`block`, `ask`, `allow-explicit`, `allow`, `absent`, `error:<n>`, `timeout` mean what they say.
`malformed-json` deserves attention: the hook tried to deny, wrote JSON the harness cannot
parse, and the deny was silently lost. A scenario that blocks must block **for the reason it
planted** (`expect_detail_contains`); a gate that objects to something unrelated has not passed.

Two scenarios record known defects on purpose, so that fixing them shows up as a diff:
`vs-engine-files-in-lint-scope` and `vs-untracked-file-with-type-error`.

## The audit scenarios (manual)

The hook scenarios cover the deterministic half of the enforcement loop. The overseer's
judgement is a model's, so it is measured in real sessions, three runs per scenario:

```bash
evals/make_sandbox.sh v0.9.0 ~/engine-sandboxes/audit-v0.9.0 --audit-fixtures
cd ~/engine-sandboxes/audit-v0.9.0
claude --setting-sources project,local     # the engine alone, without the user-level layer
#   paste prompt A, then prompt B, from evals/scenarios/audit/NN-*.md; note the verdict
python3 <engine>/evals/run_hook_scenarios.py --sandbox . --reset-only   # before the next run
```

Record the verdicts in a copy of `baseline/AUDIT-RECORD-TEMPLATE.md`. Check `claude --help`
for the exact spelling of the settings-source flag on your version.

## Adding a scenario

Add an object to the matching file in `scenarios/hooks/`. Setup is declarative on purpose
(`write`, `remove`, `git`) — a scenario file cannot run arbitrary shell or touch anything
outside the sandbox. Placeholders: `{{SANDBOX}}`, `{{TRANSCRIPT}}`. State the `why`: a
scenario nobody can explain gets deleted the first time it is inconvenient.

## Limits

- The runner calls hooks directly. It does not prove that `settings.json` wires them; a real
  session does.
- `uv sync` needs the network once per machine; later sandboxes reuse the uv cache.
- Requirements: bash, git, Python 3.12+, uv. `jq` is what the bash hooks themselves need —
  run once without it to see what a machine lacking it loses.
