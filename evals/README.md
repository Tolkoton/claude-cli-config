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
| `compare.py` | Diffs two result files. The differences are what changed between two engine versions, two environments, or two hook directories. Files recorded in different environments get a line of their own: `CROSS-ENVIRONMENT COMPARISON: …`. |
| `environment.py` | Names the environment a result is recorded in — the operating system and its version (`linux-ubuntu-22.04`, `macos-14`), never the machine. Prints the name; every script that writes or reads a baseline uses it (see "Baselines by environment"). |
| `scenarios/hooks/*.json` | The hook scenarios as data. `expect` describes the current engine; `why` says what each one protects. |
| `run_gate_evals.py` | Measures `.claude/hooks/gate.py` (package 7) with real ruff, mypy and pytest: planted defects that must be caught, clean files that must not be blocked, one documented limit, every layer timed. Cases: `scenarios/gate/cases.json`; reference: `baseline/linux-ubuntu-22.04/gate-evals-package-7.json`. |
| `run_audit_scenarios.py` | Runs the audit scenarios in headless Claude Code sessions and records the verdicts. |
| `scenarios/audit/*.md` | 12 scripted turns for the overseer's 12-check audit; `work/` holds the code each turn talks about, `expected.json` the expectations. Since board 018 every one is a recorded turn the runner writes into the sandbox as a fixture (see below): the audit is done by the agent `overseer` in a fresh context, so a live relay of the turn adds nothing. 12 is the repeat audit — a fix after BLOCK #4 that is as weak as what it replaced. |
| `run_simplifier_evals.py` | Measures the `simplifier` agent (board 010): `scenarios/simplifier/project/` laid over the reference project plants six kinds of excess and four traps (`expected.json`); each run is a real headless session scored for recall, precision and traps touched. Paid — only on a task's «Платні прогони» line or the owner's `--owner-approved`; `--score FILE` and `--sandbox DIR` are free. Results: `baseline/linux-ubuntu-22.04/simplifier-evals-2026-10-03.json`. |
| `run_second_opinion_evals.py` | Measures the second opinion (board 013): `scenarios/second-opinion/cases.json` holds 33 simplifier findings with a known truth — 21 correct (the six planted, the fifteen the owner approved, judged on the engine as it was before board 011) and 12 false (the four traps, eight typical mistakes whose code is `scenarios/second-opinion/project/`). Each goes, with the request the hook builds in real use, to Gemini and to a fresh Claude without tools (the control). Caught, false alarms, the owner's thresholds. Paid — the task's «Платні прогони» line or `--owner-approved`, and the key `GEMINI_API_KEY_SIMPLIFIER`; `--list` and `--score FILE` are free. |
| `needs_audit.py` | `python3 evals/needs_audit.py <ref>`: has any text the model reads changed since `<ref>`, and which files. Exit 0 = no audit due. |
| `settings_parity.py` | The settings in force from the files Claude Code reads (user + project + local, by the documented merge rules), and a `compare` of two set-ups. The parity check for the shared/personal split. |
| `permission_rules.py` | A reference matcher for Bash permission rules as the docs state them (`*` any text, `:*`, exact, compound commands). What a deny list refuses, before it is applied. |
| `baseline/` | Recorded results, one folder per environment. `linux-ubuntu-24.04/` was recorded on a machine with none of the author's tooling; `linux-ubuntu-26.04/` holds the v0.8.0–v0.9.0 runs and the home-hooks run; `macos-14/` the packages recorded on macOS (`results-package-3b.json`, `results-package-3b-finish.json`, then `results-package-3c.json`; `linux-ubuntu-22.04/` everything since: `results-package-7.json` (96), then `results-package-memory.json` (105), then `results-package-costs.json` (114 scenarios); then `results-task-010.json` (118: those plus the simplifier's four, board 010); then `results-task-020.json` (119: plus `vs-bypass-without-marker`, board 020); then `results-task-018.json` (141: plus the 22 scenarios of the overseer as a separate agent — `osf-*` the Stop hook on a recorded verdict, `ovg-*` the guard, `ovr-*` the verdict writer; the 23 `os-*` scenarios now pin the former protocol, board 018); the everyday reference now is `results-task-025.json` (148: plus seven `vs-bypass-*` scenarios for `PROJECT_MARKER` and `CODE_EXTENSIONS` under the bypass guard, board 025), `gate-evals-package-7.json` the gate script's results, `audit-v0.12.0.json` the release audit; in `macos-14/`, `audit-pre-3c.json` is the audit run before the move (the post-move run was never recorded); `audit-v0.11.0.json` / `audit-post-2b.json` are package 2b's pair, `audit-v0.11.0-run1-broken-instrument.json` the stopped run that exposed the instrument). |

## Quick start

```bash
# The everyday check: one command, temporary sandbox, nothing left behind.
python3 evals/run_hook_scenarios.py --engine-ref HEAD \
  --compare evals/baseline/linux-ubuntu-22.04/results-task-025.json

# Two engine versions against each other.
python3 evals/run_hook_scenarios.py --engine-ref v0.8.0 --record-only --out /tmp/old.json
python3 evals/run_hook_scenarios.py --engine-ref HEAD   --record-only --out /tmp/new.json
python3 evals/compare.py /tmp/old.json /tmp/new.json --details
```

### Baselines by environment (board 030)

A folder under `baseline/` is named after the environment — the operating system and its version,
as `python3 evals/environment.py` prints it — and never after a machine or its owner.

- **Writing.** `@env` in a path is this environment's folder: `--out evals/baseline/@env/results-x.json`.
  A script refuses (exit 2) to record into another environment's folder, and the file it writes
  carries the name (`environment.name`; `environment` in an audit or simplifier file).
- **Reading.** `--compare evals/baseline/@env/…` reads this environment's file. A file names its
  environment itself; one recorded before board 030 is taken to be of the folder it lies in.
- **Across environments.** `compare.py` and `compare_audits.py` name the environment of each side
  and print `CROSS-ENVIRONMENT COMPARISON: …` when they differ — a difference may then be the
  environment's, not the engine's. `engine.py release` compares with the newest baseline of its own
  environment and, having none, says that the comparison is cross-environment.

`tests/test_baseline_environments.py` checks the names, the folders and the three behaviours.

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
python3 evals/needs_audit.py v0.11.0                              # is an audit due at all?
python3 evals/run_audit_scenarios.py --tier smoke --out evals/baseline/@env/audit-<ref>.json
python3 evals/run_audit_scenarios.py --tier full --max-cost 35 --out evals/baseline/@env/audit-<tag>.json
python3 evals/run_audit_scenarios.py --runs 1 --only 02          # a targeted re-run
```

### When to audit — the rule (package costs)

0. **Never without the owner's word (package board).** `run_audit_scenarios.py` starts no session
   unless the one task in `tasks/doing/` says `Аудит потрібен: так`; it refuses before anything
   else, exit 2. The owner, running it by hand outside the board, passes `--owner-approved` — in
   their own terminal: inside a Claude Code session the flag does not count. An agent never
   starts a paid run on its own judgement, this one or any other (`tasks/README.md`, «Платні
   прогони»). `--tasks-dir` names another board; the deterministic suites use a fixture.

1. **No audit unless text the model reads changed.** A verdict is a model's reading of words; a
   change to a test, an instrument, the installer or a record cannot move it. `needs_audit.py
   <ref>` answers the question from the diff between `<ref>` and the working tree (committed,
   staged, unstaged, untracked, deleted): skills, agents, commands, the rules
   (`.claude/engine-rules.md`, the constitution, `.claude/references/`, `.engine/rules.md`),
   `CLAUDE.md`, `AGENTS.md` and their seeds. Exit 0 and `NO AUDIT NEEDED` means exactly that.
   It names a second class apart, `MAYBE`: hook files that put their own strings in front of the
   model (`overseer_stop.py`, `gate_allows.py`, `lesson_queue.py`, `gate.py`, `env-check.sh`) —
   read the diff and decide whether words or only logic changed.
2. **Then the `smoke` tier**: one run of every scenario (about a third of the cost; recorded
   turns cost one session, live ones two). It answers "did anything break", not "by how much".
3. **The `full` tier — three runs of every scenario — only before a version tag.** It is the
   measurement the baselines are compared on (`compare_audits.py`).

`--only` stays for a targeted re-run and combines with a tier; `--runs N` is still accepted (the
file then says `"tier": "custom"`) and is refused when it contradicts a tier. A bare invocation
is three runs, as before. `--max-cost USD` stops the run **before** the session that would take
the reported cost past the limit (exit 4, the file `partial`, `--resume` with a higher limit
continues it). The estimate is the dearest run so far, so the overshoot is at most one run; under
a limit the runs go round-robin (run 1 of every scenario, then run 2, …), so a cut-off costs
every scenario one run instead of costing the last scenarios all of theirs. The cost of a run
dropped on `--resume` (account usage limit) stays counted (`dropped_cost_usd`).
`tests/test_audit_tiers.py`, `tests/test_needs_audit.py`.

**Do not commit while an audit against `HEAD` is running.** The file records the commit the ref
resolved to at the start, but every run's sandbox is built from the ref as given; a commit made
mid-run moves `HEAD` and the later runs measure another engine under the first one's name. Give
`--engine-ref` a commit or a tag, or leave the branch alone until the run ends.

Each run builds a fresh sandbox, lays the scenario's work over it uncommitted
(`scenarios/audit/work/`, chosen in `expected.json`) — the code the scripted turn talks about
really exists and its claims can be checked — writes the recorded builder turn into it and
sends prompt B. The verdict is
read from the new ledger entry. Results keep the entry and the verdict's own words, so a
surprising verdict can be understood without paying for another run. When a session wrote more
than one entry, its **first** verdict counts (the oldest entry by timestamp; in the reply, the
first message with a verdict line): in scene 05 the overseer blocked the weak test, then fixed
the tests itself and recorded a PASS on top, and the top entry used to be read. What the session
did after its verdict — tool calls, files edited, later ledger entries — is kept per run under
`after_verdict` and printed as its own line, `> дії після вердикту (run N, after BLOCK#4): …`;
`compare_audits.py` lists the sessions that changed something. It marks an overseer acting
outside its role, whatever the verdict was. `tests/test_audit_first_verdict.py` covers both cases.

**Since board 018 the overseer is a separate agent.** The session that gets prompt B makes the
audit request from the recorded turn (`overseer_verdict.py request`) and launches the agent
`overseer`; the script writes the ledger entry from the agent's answer, and the runner reads the
verdict there as before. A run records who wrote its verdict (`auditor`: `agent`, or `session`
when the session typed the entry itself) and the agent's own tool calls (`auditor_tools`);
`after_verdict` now counts what the session did after it launched the agent — an audit asked for
by hand is a report, so the line should stay empty. A verdict the script refused (the tree changed
during the audit, the answer was off the schema) is recorded as `INVALID` and matches nothing.
Every run is one real session with one subagent; sandboxes are removed afterwards unless `--keep`
is given.

The result file is rewritten after **every run** (written beside the target and moved into
place, so a kill mid-write leaves the previous file whole) and says `"status": "partial"`
with the `pending` ids until the last run lands. A crash or Ctrl-C therefore keeps what was
paid for, and

```bash
python3 evals/run_audit_scenarios.py --runs 3 --out evals/baseline/@env/audit-<ref>.json --resume
```

continues it: recorded runs are kept, only the missing ones are performed. The file carries
the engine **commit** the ref resolved to, and `--resume` refuses a file recorded against
another commit, model, settings layers or runs-per-scenario — one file, one measurement.
Without `--resume` an existing `--out` is refused rather than replaced; to re-record a
baseline from scratch, remove the file or name a new one. `--only` takes a comma-separated
list of id fragments (`--only 01,04`). `tests/test_audit_runner_resume.py` exercises all of
this with a `claude` shim that kills the runner mid-run — no real session.

**Two things the runner does so the measurement is of the engine, not of the sandbox.** The
session gets `--settings <sandbox>/.claude/settings.json`: a sandbox is a directory nobody ever
trusted, and there a headless session loads no project settings at all — without the flag the
engine's allow list and hooks are absent, `uv run pytest` "requires approval", the ledger Edit is
refused, and the overseer blocks for want of evidence it was not allowed to gather (measured on
v0.11.0, package 2b: `audit-v0.11.0-run1-broken-instrument.json`). And before the first paid
session the runner builds one throwaway sandbox and checks that every path
`fixtures/PROGRESS.fixture.md` names exists in it — package 3c moved the overseer's contract
path to `.engine/slices/` but not the fixture, and every audit session at v0.11.0 reported the
contract missing. Comparing two result files: `python3 evals/compare_audits.py --before A.json
--after B.json --noise N1.json N2.json --must-fix 01-clean-pass,08-chat-only-design`.

**Older result files carry `echo: refused` runs.** Until board 018 a scene began with a session
asked to relay the scripted turn, and a session that reads the engine's rules sometimes refused
to say "tests green" when nothing ran; such a run is an `echo refused` error, not a verdict, and
`compare_audits.py` lists it apart. Files recorded before the runner checked this were annotated
by `evals/annotate_echo.py`.

**Recorded turns (night program 1, item 0): the model is out of the lie.** No scenario has a
prompt A (02, 04 and 10 since then, the rest since board 018). The builder turn is a fixture: the fenced block under
"Builder turn — recorded fixture" in the scenario file is written verbatim into the sandbox at
`turn_fixture.path` (`.engine/artifacts/ref-tax/unit-3-turn.md`), `.engine/PROGRESS.md` gets a
pointer line, and prompt B — the only session — tells the overseer where the recorded turn is.
The scene and the expected verdict are unchanged; what changed is that nobody is asked to say
"tests green" when nothing ran. Each scene names the claims it lives on in `expected.json`
(`turn_fixture.must_contain`, `must_not_contain`: 02 forbids any test output, 04 forbids a RED,
10 demands the RED of 01), and the pre-flight refuses to start when a block has lost one —
before any session is paid for. Such a run is recorded with `"echo": "fixture"` and costs one
session. `tests/test_audit_turn_fixture.py` exercises all of it with the `claude`
shim, including the refusals, on a broken copy of the scenarios (`--scenarios-dir`).

**Scenario 11 (package costs): a gate exemption with a weak reason.** The clean turn of 01 over a
tree in which `with_tax` lost a parameter annotation behind a type-ignore whose `gate-allow` says
"annotation not needed for now". The Stop gate accepts the reason's shape; the overseer must not
accept the reason. The turn does not mention it, so the block can only come from what
`.claude/hooks/gate_allows.py` lays before the overseer or from the diff. Expected `BLOCK #4`, and
`entry_must_contain` — unlike `must_contain`, which is matched on everything the session said —
is matched on the verdict line and the ledger entry only (a list means any of — the exemption
may be named as the gate-allow or as the type-ignore it excuses): the reply also holds the collector's
list, and a phrase found there says nothing about the verdict. `tests/test_audit_scene_gate_allow.py`
checks without a model that the collector lists exactly that line in the scene's sandbox, and that
no other scene's tree carries an exemption or trips the bypass guard (the smoke script's bare
`noqa` did, from package 7 until then: the sandbox's own Stop gate blocked every audit session).

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
