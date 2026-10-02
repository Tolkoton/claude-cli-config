# evals — the measuring instrument

Everything here exists to answer one question before and after any change to the engine:
**did behaviour change, and if so, was that intended?** Nothing in this directory is loaded
by Claude Code, wired into `settings.json`, or copied into a target project.

## What is here

| Path | What it is |
|---|---|
| `reference-project/` | A tiny, fully typed Python project (uv, ruff, mypy, pytest). Real code for the hooks to act on. |
| `make_sandbox.sh` | Builds a disposable git repository: the reference project + the engine from ONE git ref, installed by `engine.py install` — the path a real project takes. A ref older than `engine.py` is installed the way its own `docs/TEMPLATE-SETUP.md` said, so both sides of the change stay comparable. |
| `run_hook_scenarios.py` | Feeds each hook the JSON envelope Claude Code would send and records what the hook decided. Deterministic, no model involved. |
| `compare.py` | Diffs two result files. The differences are what changed between two engine versions, two machines, or two hook directories. |
| `scenarios/hooks/*.json` | The hook scenarios as data. `expect` describes the current engine; `why` says what each one protects. |
| `run_audit_scenarios.py` | Runs the audit scenarios in headless Claude Code sessions and records the verdicts. |
| `scenarios/audit/*.md` | 10 scripted turns for the overseer's 12-check audit; `work/` holds the code each turn talks about, `expected.json` the expectations. |
| `settings_parity.py` | The settings in force from the files Claude Code reads (user + project + local, by the documented merge rules), and a `compare` of two set-ups. The parity check for the shared/personal split. |
| `permission_rules.py` | A reference matcher for Bash permission rules as the docs state them (`*` any text, `:*`, exact, compound commands). What a deny list refuses, before it is applied. |
| `baseline/` | Recorded results. `clean-ubuntu-24.04/` was recorded on a machine with none of the author's tooling; `Laos-MacBook-Pro/` on the author's macOS machine (`results-package-3b.json`, `results-package-3b-finish.json`, then `results-package-3c.json` — the everyday reference now; `audit-pre-3c.json` is the audit run before the move (the post-move run was never recorded); `audit-v0.11.0.json` / `audit-post-2b.json` are package 2b's pair, `audit-v0.11.0-run1-broken-instrument.json` the stopped run that exposed the instrument). |

## Quick start

```bash
# The everyday check: one command, temporary sandbox, nothing left behind.
python3 evals/run_hook_scenarios.py --engine-ref HEAD \
  --compare evals/baseline/Laos-MacBook-Pro/results-package-3c.json

# Two engine versions against each other.
python3 evals/run_hook_scenarios.py --engine-ref v0.8.0 --record-only --out /tmp/old.json
python3 evals/run_hook_scenarios.py --engine-ref HEAD   --record-only --out /tmp/new.json
python3 evals/compare.py /tmp/old.json /tmp/new.json --details
```

`expect` values describe the current engine, so an older ref is recorded with `--record-only`.
Any directory of hooks can be measured, not only a sandbox's own — for example the user-level
copies in the home folder, or the `.claude/hooks/` of an existing project (read-only: the hooks
run against the sandbox, never against that project):

```bash
python3 evals/run_hook_scenarios.py --engine-ref HEAD --hooks-dir ~/.claude/hooks --record-only --out /tmp/home.json
```

Without `--hooks-dir`, a scenario that starts the session in a subdirectory (`project_dir`, the
worktree cases) runs THAT checkout's copy of the hook, as Claude Code would.

A sandbox you want to look into afterwards: `evals/make_sandbox.sh <ref> <dir outside this repo>`,
then `--sandbox <dir>` instead of `--engine-ref`. Delete it yourself when done.

## Reading an outcome

`block`, `ask`, `allow-explicit`, `allow`, `absent`, `error:<n>`, `timeout` mean what they say.
`malformed-json` deserves attention: the hook tried to deny, wrote JSON the harness cannot
parse, and the deny was silently lost. A scenario that blocks must block **for the reason it
planted** (`expect_detail_contains`); a gate that objects to something unrelated has not passed.

Some scenarios record a known defect on purpose, so that fixing it shows up as a diff
against the older baselines. None is open at the moment: `vs-engine-files-in-lint-scope`,
the two `*-in-worktree` scenarios and `vs-untracked-file-with-type-error` were all closed in
package 2a and show up as differences against `results-v0.9.0.json`.

## The audit scenarios

The hook scenarios cover the deterministic half of the enforcement loop. The overseer's
judgement is a model's, so it is measured in real headless sessions, several runs per scenario:

```bash
python3 evals/run_audit_scenarios.py --runs 1 --only 02          # a cheap first look
python3 evals/run_audit_scenarios.py --runs 3 --out evals/baseline/<machine>/audit-<ref>.json
```

Each run builds a fresh sandbox, lays the scenario's work over it uncommitted
(`scenarios/audit/work/`, chosen in `expected.json`) — the code the scripted turn talks about
really exists and its claims can be checked — then sends prompt A and prompt B. The verdict is
read from the new ledger entry. Results keep the entry and the verdict's own words, so a
surprising verdict can be understood without paying for another run. Every run is two real
sessions on your account (about a dollar on Opus-class models); sandboxes are removed afterwards
unless `--keep` is given.

The result file is rewritten after **every run** (written beside the target and moved into
place, so a kill mid-write leaves the previous file whole) and says `"status": "partial"`
with the `pending` ids until the last run lands. A crash or Ctrl-C therefore keeps what was
paid for, and

```bash
python3 evals/run_audit_scenarios.py --runs 3 --out evals/baseline/<machine>/audit-<ref>.json --resume
```

continues it: recorded runs are kept, only the missing ones are performed. The file carries
the engine **commit** the ref resolved to, and `--resume` refuses a file recorded against
another commit, model, settings layers or runs-per-scenario — one file, one measurement.
Without `--resume` an existing `--out` is refused rather than replaced; to re-record a
baseline from scratch, remove the file or name a new one. `--only` takes a comma-separated
list of id fragments (`--only 01,04`). `tests/test_audit_runner_resume.py` exercises all of
this with a `claude` shim that kills the runner mid-run — no real session.

**Two things the runner does so the measurement is of the engine, not of the sandbox.** Both
sessions get `--settings <sandbox>/.claude/settings.json`: a sandbox is a directory nobody ever
trusted, and there a headless session loads no project settings at all — without the flag the
engine's allow list and hooks are absent, `uv run pytest` "requires approval", the ledger Edit is
refused, and the overseer blocks for want of evidence it was not allowed to gather (measured on
v0.11.0, package 2b: `audit-v0.11.0-run1-broken-instrument.json`). And before the first paid
session the runner builds one throwaway sandbox and checks that every path
`fixtures/PROGRESS.fixture.md` names exists in it — package 3c moved the overseer's contract
path to `.engine/slices/` but not the fixture, and every audit session at v0.11.0 reported the
contract missing. Comparing two result files: `python3 evals/compare_audits.py --before A.json
--after B.json --noise N1.json N2.json --must-fix 01-clean-pass,08-chat-only-design`.

## Adding a scenario

Add an object to the matching file in `scenarios/hooks/`. Setup is declarative on purpose
(`write`, `remove`, `git`) — a scenario file cannot run arbitrary shell or touch anything
outside the sandbox. Placeholders: `{{SANDBOX}}`, `{{TRANSCRIPT}}`, `{{HEAD}}` (the sandbox's
initial commit). A group may give its hook command-line arguments with `"args"`. State the `why`: a
scenario nobody can explain gets deleted the first time it is inconvenient.

## Limits

- The runner calls hooks directly. It does not prove that `settings.json` wires them; a real
  session does.
- `uv sync` needs the network once per machine; later sandboxes reuse the uv cache.
- Requirements: bash, git, Python 3.12+, uv. the bash hooks parse their input with `jq`, or with
  `python3` when jq is absent — run once without both to see what a machine lacking them loses.
