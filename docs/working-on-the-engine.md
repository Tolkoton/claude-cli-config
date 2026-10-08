# Working on the engine — the detail behind AGENTS.md

Read this when you change the engine itself and `AGENTS.md` was not enough: which command
verifies what, what the Stop gate runs in this repository, and the paths that are rarely
needed. `AGENTS.md` is loaded into every session and holds only what every session needs; the
rest moved here, and nothing in this file is loaded at launch.

## Verifying a change

The rule is in `AGENTS.md`: exercise the thing you changed and show the negative case.

```bash
bash tests/run_all.sh                 # every suite, one line each (the pre-tag check)
bash tests/run_all.sh --fast          # the Stop-gate subset
bash tests/run_all.sh --jobs 1        # one suite at a time; the default is one per processor
python3 evals/run_hook_scenarios.py --engine-ref HEAD --compare evals/baseline/linux-ubuntu-22.04/results-task-086.json
python3 .claude/hooks/overseer_stop.py --dry-run     # always emits a block
bash .claude/unattended/board-runner.sh --status
python3 evals/hook_coverage.py run --data /tmp/cov-tests -- bash tests/run_all.sh    # about an hour: every suite, traced
python3 evals/hook_coverage.py report /tmp/cov-tests --missing                       # what no suite ran, by function
```

## The suites run in parallel

`tests/run_all.sh` runs as many suites at once as the machine has processors (`--jobs N`,
`ENGINE_TEST_JOBS`), and prints and records what a run one at a time would: one line per suite in
the order of the list, the same exit code. A suite must therefore stand alone — its own throwaway
directories (`tempfile.mkdtemp`), no fixed path under `/tmp`, no fixed port, nothing written into
this repository — and must not measure a short time limit it could miss on a busy machine. The
record (`.claude/state/health/tests-full.json`) carries the run's `seconds` and every suite's
time; the next run starts the longest first. Do not edit `tests/run_all.sh` while it runs.

## A suite that runs a hook

The Stop gate runs `TEST_CMD` with `CLAUDE_PROJECT_DIR` naming this repository; by hand the
variable is unset. A hook that inherits it answers for this repository's branch and
`project.env`, so the suite is green by hand and red from the gate. Take the hook's
environment from `tests/hook_env.py` — `hook_env()` (a fresh empty directory),
`hook_env(main_repo())` (a repository on `main`), `hook_env(root, PATH=shims)` (the suite's
own project). `tests/test_hook_env.py` fails a new suite that runs a hook without it; the
suites written before the helper stand in `tests/hook-env-exempt.txt`, which may only shrink.

## What `.claude/project.env` says here

It describes the engine itself: `SOURCE_DIRS` names the hook, harness, evals and test
directories, `CODE_EXTENSIONS="py sh"`, `TEST_CMD` runs the suites — so the Stop gate verifies
the engine's own code whenever a `.py` or `.sh` file changed. Left empty, `TEST_CMD` would run
`pytest -x`, which is not installed here. The seed a target project receives
(`templates/project/`) still says `src` and `py`.

## Paths needed now and then

The paths every session needs are the table in `AGENTS.md`. These are the rest.

| Path | What it is |
|---|---|
| `.claude/ownership.txt` | Who owns every path: engine, project, machine, user (read by engine.py) |
| `templates/project/` | The seeds a new project starts from (CLAUDE.md, AGENTS.md, records) |
| `user/` | The owner's own skills and settings layer. Never ships. |
| `docs/tasks/` | Proposals the engine may not apply itself, each with a test and one command |
| `docs/engine-limits.md` | What the guarantees assume |
