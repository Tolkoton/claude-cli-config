# gate.py — the one gate script

Read this when the Stop gate blocked you and its message was not enough, when you wire a git
pre-commit hook or a CI job, or when you change the gate. Hook table: `hooks.md`.

```
python3 .claude/hooks/gate.py --layer {post_write|stop|pre_commit|ci} [--files F...] [--diff REF] [--hook]
```

Exit 0 = no `block` finding, 2 = at least one. `--hook` speaks Claude Code's protocol (envelope on
stdin; a Stop block is `{"decision":"block","reason":…}` with exit 0). Report:
`.claude/state/gate/last-report.json` — per finding file, line, rule, severity (`block|warn|log`),
message, hint; `timings_ms` per step. The separate gates write `<source>-report.json` beside it in
the same schema. Settings live in `.claude/project.env` and nowhere else.

| Layer | Runs | Scope | Blocks |
|---|---|---|---|
| `post_write` | after every edit | one file: format, then a quick `ruff check` | never; says what changed through `additionalContext`, only when something did |
| `stop` | turn end | the files the turn changed (working tree + index vs HEAD + untracked): lint and types on them, the tests that map to them (`tests/test_<module>.py`, or the changed test file); or `LINT_CMD` / `TYPECHECK_CMD` / `TEST_CMD` as set | yes |
| `pre_commit` | `git commit` | the staged diff: bypass guard, then the full set | yes |
| `ci` | pipeline | the whole project: `ruff check .`, `mypy .`, `TEST_CMD_FULL` else `TEST_CMD` | yes |

Order inside a layer: bypass guard, lint, types, tests — tests only after a clean lint and types.
A declared limit of `stop`: it is incremental, so a defect in an untouched file or a test broken by
a module with no sibling test is for `pre_commit` and `ci`.

## The Stop counter

`stop_hook_active` is read first. Claude Code sets it on the stop that follows a block, so the gate
ends its work on it only while this session's counter is 0; with the counter above 0 the re-entry is
checked again. A block adds one (per `session_id`), a pass resets. On the `GATE_MAX_BLOCKS`th block
in a row (default 3) the gate lets the turn end, appends a PARKED entry (class `human-input`) to
`.engine/overseer/parked.md`, says so in a `systemMessage`, and starts counting again. That entry
is not the end of it: see "An open escalation refuses the PASS" below.

## The bypass guard (stop, pre_commit)

A block when the turn's diff **adds** a `# type: ignore`, a `# noqa`, `pytest.mark.skip` /
`skipif` / `xfail` (or `pytest.skip()` / `xfail()`), or **changes** the linter's or type checker's
configuration: the parsed `[tool.ruff]` / `[tool.mypy]` of `pyproject.toml`, any change of
`ruff.toml`, `.ruff.toml`, `mypy.ini`, `.mypy.ini`, or the values of `LINT_CMD`, `TYPECHECK_CMD`,
`TEST_CMD`, `TEST_CMD_FULL`, `FORMAT_CMD`, `GATE_MAX_BLOCKS` in `.claude/project.env`. Syntax only:
comments come from the tokenizer, marks from the AST, configuration from the parsed tables, so a
string, a docstring or a reformat is not a finding.

Allowed when the justification stands next to it:

- `# gate-allow: <reason>` on the same line, or on the comment-only line directly above; for a
  configuration file, any added line of that file. A reason is at least 12 characters and two words.
- or the slice contract says `gate-allow: <type-ignore|noqa|skip|xfail|path> — <reason>` — honoured
  only while the contract is **sealed and unchanged** (`.claude/state/contracts/<slug>.sha256`
  matches), so the work being judged cannot grant itself the exemption by editing a slice file.

## Who reads the reason (package costs)

The gate checks a reason's shape; the overseer judges whether it is true.
`python3 .claude/hooks/gate_allows.py [--json] [--base REF] [--all]` lists every exemption the work
adds that no accepted `OVERSEER_PASS` has seen: markers in `.py` comments (with the suppression
they stand beside), added marker lines of a config file, and a suppression that passes on a sealed
contract's grant, shown where it is used. "New" is measured from the commit of the last accepted
PASS (`.claude/state/overseer/gate-allows-judged.json`), else the active contract's `base_commit`,
else the merge-base with the main branch, else HEAD — so a checkpoint commit hides nothing.
`overseer_stop.py` appends the list to `OVERSEER_REQUEST` (nothing when it is empty; a notice when
the collector failed), and the overseer skill's check #4 blocks a weak or missing reason.

## An open escalation refuses the PASS

The `GATE_MAX_BLOCKS`th block also records the escalation in `.claude/state/gate/escalations.json`
(slice, the files it blocked on). While it is open, `overseer_stop.py` answers an `OVERSEER_PASS`
for that slice with `OVERSEER_PASS_REFUSED` — outside a slice, for any range that still holds
those files. The owner closes it, in their own terminal:

```bash
python3 .claude/hooks/gate.py --close-escalation <stamp|all>   # the stamp is in the parked entry
```

The command refuses inside a Claude Code session (`CLAUDECODE` set) and marks the parked entry
`RESUMED`. Editing `parked.md` by hand closes nothing.

## Wiring a git pre-commit hook and CI (nothing here installs them)

```bash
# .git/hooks/pre-commit  (chmod +x)
#!/usr/bin/env bash
exec python3 .claude/hooks/gate.py --layer pre_commit

# a CI job: one step
python3 .claude/hooks/gate.py --layer ci --diff origin/main
```

No file under `.github/workflows/` is shipped; add the step to your pipeline yourself.

## Measuring it

`python3 evals/run_gate_evals.py --engine-ref HEAD` — defective files that must be caught, clean
files that must not be blocked, every layer timed. `bash tests/run_all.sh` runs `tests/test_gate.py`
and `tests/test_gate_evals.py`. Reference results: `evals/baseline/Laos-MacBook-Pro/gate-evals-package-7.json`.
