# The hooks — what each one does, and how to work with them

Read this when a hook blocked you and the message was not enough, when you need to disable one
for a measurement, or when you change one. The standing rules are in `.claude/engine-rules.md`;
this file holds the detail they point at. Wiring: `.claude/settings.json`; configuration:
`.claude/project.env` (sourced by the hooks at run time, no restart needed).

| Hook | When | What it does |
|---|---|---|
| `block-dangerous.sh` | before any Bash | Hard-blocks destructive patterns and a `git commit` outside an `unattended/<date>` branch (or, in a cloud session, outside the session's own branch when `CLOUD_COMMIT_POLICY=session-branch`). Matches the whole command text, quoted strings included: a commit message that *mentions* a force push is refused too — write such text to a file and pass `-F`. |
| `protect-paths.sh` | before Edit/Write/MultiEdit | Hard-blocks edits to secrets (`*.env`, `secrets/`, credential files), `migrations/`, `alembic/versions/`, `.git/`, `.github/workflows/`, `.claude/settings.json`, the constitution. One exception: `.claude/project.env`, the template's own config. |
| `format-on-edit.sh` | after Edit/Write/MultiEdit | A thin call to `gate.py --layer post_write`: `FORMAT_CMD` from project.env, else `ruff format` + `ruff check --fix --select I` on `.py` files, then a quick lint; never blocks, reports through `additionalContext` only when something changed. |
| `park-ask-gated.py` | before any Bash | Unattended only: denies an ask-listed command with a park instruction instead of letting it hang on a prompt nobody answers. No-op when attended. Standard library only. |
| `verify-on-stop.sh` | turn end | A thin call to `gate.py --layer stop`: runs `LINT_CMD`, `TYPECHECK_CMD`, `TEST_CMD` (or ruff / mypy / pytest on the changed files) when a file matching `CODE_EXTENSIONS` changed; blocks the turn with the failure output; refuses to be passed by an added `# type: ignore` / `# noqa` / skip / xfail or a loosened lint or type config; escalates to a human after `GATE_MAX_BLOCKS` blocks in a row. |
| `gate.py` | called by the two hooks above, by a git pre-commit hook and by CI | The one gate script: layers `post_write`, `stop`, `pre_commit`, `ci`; report in `.claude/state/gate/last-report.json`. Everything about it: `.claude/references/gate.md`. |
| `overseer_stop.py` | turn end | On a unit-completion claim (sentinel + code edit + verification command) writes an audit request package and injects `OVERSEER_REQUEST <id>` — "launch the agent `overseer` with exactly this line"; then acts on the verdict `overseer_verdict.py` recorded: PASS re-injects "continue", BLOCK hands the finding back (the third in a row on one unit parks it by script: under the board runner the hook leaves `.claude/state/board/three-blocks-<task>.json` and stops the session with `continue: false`, and the runner moves the task to `tasks/blocked/`; elsewhere the hook writes the PARKED entry itself and tells the person at the terminal in a `systemMessage`), ADR / ESCALATE are routed, no valid verdict repeats the request twice and then parks. `OVERSEER_PASS` typed by the builder is refused. In a project whose settings lack the two `overseer_verdict.py` handlers a claim gets `OVERSEER NOT WIRED` instead of a request — there is no other way to audit; `engine.py update` adds the handlers. Compares the active slice contract with its sealed fingerprint first. Lists the gate exemptions no accepted PASS has seen in the request (`gate_allows.py`), and warns while the Stop gate's escalation for the work is open. Until `overseer_verdict.py` is wired in the settings it keeps the former protocol (the session audits itself, `OVERSEER_PASS` continues, `OVERSEER_PASS_REFUSED` under an open escalation). |
| `overseer_verdict.py` | `guard`: before Agent and the edit tools; `record`: when the agent `overseer` ends (SubagentStop); `request`, `status`: by hand | The overseer is a separate agent in a fresh context (`.claude/agents/overseer.md`: Read, Grep, Glob, Bash). `guard` starts it only for the pending request and only with the prompt `OVERSEER_REQUEST <id>`, fingerprints the tree at that moment, and refuses every editing tool and the Agent tool inside it. `record` is the one writer of verdicts: checks the agent's JSON answer against the schema (first failure back to the agent, second recorded `INVALID`), compares the tree (HEAD, `git status`, content of changed and untracked files; ignored files apart) and the contract's sha256 with the request — a difference is `INVALID`, nothing is rolled back — records a BLOCK instead of a PASS while the gate's escalation is open, then writes `.engine/overseer/ledger.md` and `.claude/state/overseer/verdicts.jsonl`. `request --turn-file F` makes a request by hand; an audit asked by hand is a report, the Stop hook adds nothing to it. |
| `gate_allows.py` | called by `overseer_stop.py` and by the overseer | Collects every new `gate-allow` (code comment, config line, contract grant in use) for the overseer to judge; reports, never blocks. `.claude/references/gate.md`. |
| `simplify_signals.py` | called by `gate.py` in every layer but `post_write`, when `COMPLEXITY_GATE` is not off | The simplifier's deterministic signals as `warn` findings, never a block: at stop the changed files (complexity, nesting, new dependencies, dead code), at pre_commit / ci the whole repository (plus unused dependencies, duplication, the history in `.claude/state/simplifier/metrics.jsonl`). vulture and pylint through `uvx`. |
| `simplifier.py` | called by the builder and the architects | Everything deterministic around the `simplifier` agent: the request, the validator of its findings, the routing to the owner's report, `accept` for a justified budget overrun, the reversal rate. `.claude/references/simplifier.md`. |
| `second_opinion.py` | called by the builder between `simplifier.py validate` and `route`, when `SECOND_OPINION="on"` | Gemini's view of each finding: `agree` / `disagree` / `unsure`, checked and recorded; it can only lower what a finding may do. Key from `GEMINI_API_KEY_SIMPLIFIER` only. Off by default. `.claude/references/simplifier.md`. |
| `complexity_budget.py` | turn end | `COMPLEXITY_GATE=warn|call`: measures the slice's changes against the contract's "Complexity budget" section; an overrun calls the simplifier (`call` holds the turn until its verdict is recorded). Off by default. Stays separate from `gate.py`; reports in its schema (`.claude/state/gate/complexity_budget-report.json`). |
| `overseer_phase.py` | called by `/plan-slice` and `/feature-architect` | `set plan` / `clear` / `show`: the sanctioned way to set the phase guard the Stop hook reads (`.claude/state/overseer/state`). |
| `goals.py` | called by `/business-analyst`, the architects, the owner's review and (for `amend`) the board runner | The goals document `.engine/goals.md` (level 0): `seal` / `status` (the fingerprint in `.claude/state/goals/`; a changed document is re-sealed only by the owner), `check` and `unreconciled` (a decision's «Звірка з цілями» cites lines that exist and stand), `quote` (the analyst's «the document already answers» is a verbatim line), `proposal` / `amend` (a lawful amendment, applied on the owner's «так» — the action `amend-goals`), `affected` (who cited a changed line). Not wired as a hook. `.claude/references/business-analysis.md`. |
| `baseline.py` | by hand; read by `gate.py` | The snapshot "as it was", `.engine/baseline.json`: `record` (the owner's, refused in a session when it would loosen) lists the failing tests and counts lint and type findings per (file, rule); `tighten` only removes. With the file the gate blocks only what got worse. `.claude/references/gate.md`. |
| `delete_guard.py` | called by `gate.py` at turn end and before a commit; `confirm` by hand | Blocks a change that deletes a function, a class or a file of working code no test touched, or more than `DELETE_GUARD_LINES` lines inside one function; a move is not a deletion. Exact with `COVERAGE_CMD`, coarser without. Through: a test, a simplifier finding the owner confirmed (`confirm`, refused in a session), a grant in the sealed contract. `.claude/references/gate.md`. |
| `contract_fingerprint.py` | called by `/plan-slice` and `overseer_stop.py` | `seal` writes `.claude/state/contracts/<slug>.sha256` and refuses to overwrite; `check` compares (and reports in the gate schema). |
| `env-check.sh` | session start | Names the tools this machine lacks for the hooks to enforce anything. Silent when nothing is missing. |

## Input parsing — jq or python3, on any operating system

The bash hooks read Claude Code's JSON envelope with `jq` when it is installed and fall back to
`python3` otherwise. With **neither** present, the two deny hooks (`block-dangerous.sh`,
`protect-paths.sh`) **refuse** the call (exit 2, reason on stderr) rather than let it through
unchecked, `format-on-edit.sh` does nothing and says so, and `verify-on-stop.sh` refuses (exit 2: a gate
that cannot run is not a verified turn). Both need `python3` for `gate.py`. Install one of them with your package manager (`apt install jq`,
`dnf install jq`, `brew install jq`, or any `python3`); `env-check.sh` tells you at session
start if both are missing. Pinned by `tests/test_deny_hooks.py` (the NOJQ cases).

## Inspecting, disabling, smoke-testing

- Inspect: `cat .claude/hooks/<name>`.
- Disable one temporarily: rename it to `<name>.disabled`, or start Claude Code with
  `--disable-hooks` (all of them). Settings are read at session start.
- Smoke-test the overseer wiring: `python3 .claude/hooks/overseer_stop.py --dry-run` always
  emits a block.
- A hook change is not verified until you have seen it **block** something it should block; a
  passing allow-case proves nothing, because a dead hook also allows.

## What a hook cannot see

`block-dangerous.sh`, `protect-paths.sh` and the `permissions` lists evaluate the tool call
the agent issues. A command run from **inside a shell script** is seen by none of them
(verified 2026-08-27: `git commit --dry-run` is refused at top level and executes untouched
from a two-line script). The guard inside `commit_checkpoint.sh` is the only guard on that
path. The guarantees also assume one session working in one repository: the branch is read
from the session's repository, not from wherever `cd` points (`docs/engine-limits.md`).

## Recursion guards of the overseer hook

`overseer_stop.py` keeps two per-branch SHA-256 idempotency files —
`.claude/state/overseer/.last_audit_sha` for the audit-request branch and
`.last_continue_sha` for the PASS→CONTINUE branch — honours every `OVERSEER_` halt marker as
"the audit already ran" (silent pass, no re-injection), and skips the audit while
`.claude/state/overseer/state` contains `plan`. A `stop_hook_active` guard used to exist and
was removed: it short-circuited before the per-branch SHAs on every hook-initiated turn, which
made both injection branches unreachable in the autonomous loop. Do not reintroduce it.
Kill switch: rename `.claude/hooks/overseer_stop.py` to `*.disabled`, or `--disable-hooks`.
