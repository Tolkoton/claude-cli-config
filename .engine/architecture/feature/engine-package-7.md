# Feature engine-package-7 — one gate script

Frame source: `docs/plan/package-7.md` (the owner's text, verbatim). Every numbered item is an
owner requirement; the critic checks how each is met, not whether. Branch
`unattended/2026-10-03-package-7` from the end of night-1 item 0 (`371e02c`; item 0.3, the paid
full audit, runs last by the program's order). Rules carried over from `docs/plan/night-1.md`:
after every slice `tests/run_all.sh`, the golden set against the newest reference, ruff and
`mypy --strict`; UTC only; new commits only; no paid sessions.

## Goal

Today three hooks each re-implement "find what changed, read project.env, run lint / types /
tests": `format-on-edit.sh`, `verify-on-stop.sh` and (differently) the pre-commit habit. One
script, `.claude/hooks/gate.py`, takes over, with four layers that share the project.env
switchboard, one finding format and one report. The Stop layer gains what the shell never had:
a retry counter that ends in an escalation, and a syntactic guard against the model passing the
gate by silencing it.

## Acceptance (owner's "done when")

- every suite green; golden set identical to `results-package-3c.json` except intended
  differences; ruff and `mypy --strict` clean on what this package touches; the ownership map
  knows every new file.

## Out of scope (deliberately)

- `.claude/settings.json` (owner-only; none is needed: the two wrappers keep their names).
- A `.github/workflows/` file, a git hook installed into `.git/` (documentation + the command).
- Model calls of any kind. The gate is deterministic.

## Decisions (agent; two-way unless stated; each logged AUTONOMOUS in escalations.md)

- **D1 stdlib-only Python ≥ 3.11.** Same constraint as complexity_budget.py: the gate must run
  in a cloud session and on a machine with no linter. Linters are external commands.
- **D2 the wrappers keep their names.** `settings.json` wires `format-on-edit.sh` and
  `verify-on-stop.sh`; renaming would need an owner edit. Each becomes ~15 lines: resolve the
  project, `exec python3 gate.py --hook --layer <x>`. With no python3 the wrapper exits 0
  silently (post_write) or refuses with exit 2 and a reason (stop) — never "verified" by silence.
- **D3 two exit vocabularies, one meaning.** CLI: exit 0 = no `block` finding, exit 2 = at least
  one. `--hook` additionally speaks Claude Code's protocol: a Stop block is
  `{"decision":"block","reason":…}` with exit 0 (what every baseline and test pins),
  post_write findings are `hookSpecificOutput.additionalContext`. The report's `exit_code` is
  always the CLI value.
- **D4 stop is incremental, configured commands are opaque.** Auto-detect runs `ruff check` and
  `mypy` on the changed `.py` files and pytest on the changed test files plus
  `tests/test_<module>.py` siblings. `LINT_CMD` / `TYPECHECK_CMD` / `TEST_CMD`, when set, run
  exactly as before: the project knows its own fast subset (this repository: `--fast`). The
  full set belongs to `pre_commit` and `ci` (`ruff check .`, `mypy .`, `TEST_CMD_FULL` else
  `TEST_CMD`).
- **D5 the counter.** `.claude/state/gate/stop-count.json`, written only by gate.py. The guard
  `stop_hook_active` is read before anything else and leaves the counter alone. A block
  increments, a pass resets. On the Nth consecutive block (`GATE_MAX_BLOCKS`, default 3 — the
  rules' "three different fixes") the gate lets the turn end, appends a PARKED entry (class
  `human-input`, the report path, the last findings) to `.engine/overseer/parked.md`, writes a
  `systemMessage`, and resets. N is a project.env key, not a new settings place.
- **D6 the bypass guard reads syntax, not text.** For `.py` it tokenizes the new version and
  takes COMMENT tokens at added line numbers (`# type: ignore`, `# noqa`) and decorator /
  call nodes `pytest.mark.skip|skipif|xfail`, `pytest.skip`, `pytest.xfail` at added lines —
  so a string literal or a docstring that merely mentions them is not a finding. For config:
  the parsed `tool.ruff` / `tool.mypy` tables of `pyproject.toml` before vs after, any change
  to `ruff.toml`, `.ruff.toml`, `.claude/ruff.toml`, `mypy.ini`, `.mypy.ini`, and any change of
  `LINT_CMD`, `TYPECHECK_CMD`, `TEST_CMD`, `FORMAT_CMD` values in project.env. The diff is the
  turn's: working tree + index against HEAD for `stop`, the index for `pre_commit`.
- **D7 the justification format.** On the same line or the line directly above an added
  suppression: `gate-allow: <reason>` (≥ 12 characters of reason, at least two words). For a
  config file, the same line anywhere in the added lines of that file. Or the slice contract
  (`.engine/slices/*.md`) carries a line `gate-allow: <kind-or-path> — <reason>` where kind ∈
  {type-ignore, noqa, skip, xfail} or a config path. A bare `gate-allow:` does not count.
- **D8 complexity_budget.py and contract_fingerprint.py stay separate** (item 4 allows it).
  Both are stateful in ways the gate is not: they read the slice contract and a sealed hash,
  have their own switch (`COMPLEXITY_GATE`) and their own state files and tests, and run on a
  different trigger (the fingerprint also gates `/plan-slice`; neither lints a file). Folding
  them in would put contract parsing into the hot path of every edit-time call and make one
  file the owner of four concerns. What they share instead is the format: gate.py exports
  `record_findings(root, source, findings)`; both call it, so `last-report.json` holds their
  findings under the same schema. Cost to reverse: low.
- **D9 timings.** Each step and the layer are timed (`timings_ms`) and written to the report;
  the evals instrument aggregates them per layer into the new baseline.
- **D10 pre_commit / ci are commands.** `python3 .claude/hooks/gate.py --layer pre_commit` is
  what a git `pre-commit` hook runs; `--layer ci [--diff <base>]` is what a pipeline runs. The
  documentation (`.claude/references/gate.md`) gives both, not a workflow file.
- **D11 post_write keeps the exact formatter behaviour** (FORMAT_CMD path, uv / poetry / bare
  ruff / black, jq for json, prettier for md/yml/toml, `--force-exclude`, jq-only JSON so a
  machine without jq degrades to doing nothing) and adds one quick lint of the file
  (`ruff check --force-exclude`, not `--fix`). It reports only when the formatter changed bytes
  or the lint found something; otherwise stdout stays empty. Never exit 2.

## Slice DAG

| id | slice | deps | verification |
|---|---|---|---|
| A1 | gate.py: report format, project.env reader, changed-file discovery, layers post_write / stop / pre_commit / ci, counter + escalation | — | tests/test_gate.py: every layer, the counter, the guards |
| A2 | bypass guard (D6, D7) inside A1's stop and pre_commit | A1 | test_gate_bypass.py: each trigger blocks, each exemption allows, the string-literal trap passes |
| A3 | the wrappers become thin; existing suites updated for the intended differences only | A1 | test_format_on_edit 22/22, test_verify_on_stop; deny-hooks untouched |
| A4 | complexity_budget / contract_fingerprint report in the shared format | A1 | their suites unchanged + a report-format check |
| A5 | evals/run_gate_evals.py + defect / clean corpus + timings baseline | A1, A2 | every defect caught, no false block on any clean file |
| A6 | golden set: new scenarios, new reference `results-package-7.json` | A3 | compare against 3c: only the declared differences |
| A7 | ownership map, project.env keys (+ seed), references/gate.md + hooks.md, report | A1–A6 | test_ownership, test_context_budget, test_project_seeds |

## Hardest seams

1. **The golden set's Stop scenarios** pin outcomes AND the `detail` text (`LINT FAILED`,
   `TYPECHECK FAILED`, `TESTS FAILED`) — the rewrite must keep those headings or the difference
   is declared. Declared differences expected: none for existing ids; additions only.
2. **Incremental mypy** over changed files only can miss an error in an unchanged dependant.
   Accepted for `stop` (speed is its contract); `pre_commit` / `ci` run the whole project.
3. **The guard vs. this repository's own tests**, which must mention `# noqa` in fixtures.
   They are built by concatenation and the guard is syntactic (D6), so the guard does not
   fire on them — and a test pins that.

## Revisions after the critic (FEATURE_CRITIC_REVISE, fresh context)

- **R1 (blocking, D5).** The critic is right: Claude Code sets `stop_hook_active` on the stop that
  follows a block, so a gate that exits on the flag can never count to N in one session. D5 is
  amended: the flag is read first, and ends the gate's work only while this session's counter is 0
  (a stop forced by another hook is not verified again — the golden scenario
  `vs-stop-hook-active-guard` stays `allow`); with counter > 0 the re-entry is checked, so
  block → re-entry → block → escalation is reachable. The counter is keyed by `session_id`.
  A1b tests the block / re-entry / re-block / escalate sequence.
- **R2 (blocking, D4).** Incremental scope is a declared difference, not "none": mypy and pytest
  see only the changed files (and their `tests/test_<stem>.py`); a type error in an unchanged
  dependant, or a test broken by a module with no sibling test, is caught by `pre_commit` / `ci`,
  not `stop`. Preserved and pinned by tests: the `[tool.ruff]` / `[tool.mypy]` gating, tests only
  after a clean lint + types, PROJECT_MARKER skip, non-Python CODE_EXTENSIONS notice, extension
  normalisation, the three headings. The existing golden Stop scenarios change in no outcome.
- **R3 (blocking).** Ownership entries and fast-suite registration land in the slice that adds the
  file (A1, A2, A5), not in A7. `ownership.txt` already covers `.claude/**` and `**`; what
  `tests/test_ownership.py` additionally pins per file is updated in the same slice.
- **R4 (blocking).** ruff / mypy are not installed here; `uvx --quiet ruff|mypy` is what this
  repository's own tests already use (an ephemeral tool run from uv's cache, nothing added to a
  project, no manifest or lockfile touched). Used for the acceptance checks and for the evals.
- **R5.** A1 is split in the build: A1a core + post_write, A1b stop + counter + guard, A1c
  pre_commit / ci. A6 depends on A2; A4 is verified by the full suite, not `--fast`.
- **R7 (D7).** A contract's `gate-allow:` line counts only from a contract whose fingerprint in
  `.claude/state/contracts/<slug>.sha256` matches (sealed and unchanged); an unsealed or edited
  slice file grants nothing. Tests: sealed allows, unsealed refuses, edited-after-seal refuses.
- **R8 (D8).** Settled as written in code: each separate gate writes its own
  `<source>-report.json` in the shared schema; `last-report.json` belongs to gate.py alone — two
  Stop hooks run side by side and a shared file would race.
- **R9.** Named test cases for A2: untracked new file (every line is added), project.env compared
  by parsed value (a reformat does not fire), the string-literal trap, the package's own
  project.env edit carries a `gate-allow:` line.
