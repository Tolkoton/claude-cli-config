# Premise log — what we assume is true, and what depends on it

Governed by **Constitution Article 1** (verify before you commit) and **Article 8**
(a falsified premise re-opens whatever depended on it). Every level records its
load-bearing assumptions here — not only inside its own plan — so that when one turns
out false, the system can trace *everything it affects* instead of hoping someone
remembers.

(Markdown for now because every agent reads it natively and a human can scan it. If a
tool ever needs to query it programmatically, graduate it to JSON with the same
fields.)

## How to use — four operations

1. **RECORD.** When a plan states a load-bearing assumption about an external system
   or a chosen technology, add a row with status `unverified` and list what depends
   on it.
2. **VERIFY.** Attach evidence (a spike, a PoC, or docs + a captured runtime check)
   and set the status and the date checked. External-system checks go **stale after
   ~7 days**.
3. **FALSIFY & PROPAGATE.** If a check refutes the assumption, set status
   `falsified`, then mark every item in *depended-on-by* for review and route each to
   its level's human gate (Article 8).
4. **QUERY.** Before committing a plan: does it rely on any `unverified` or stale
   premise? Before deleting or changing something: what depends on it?

**Status:** `unverified` · `verified` · `accepted-as-risk` · `falsified`
**Level:** `slice` · `feature` · `architecture`

## Premises

| id | statement (one falsifiable sentence) | level | status | evidence | checked | depended-on-by |
|----|----|----|----|----|----|----|
| PR-example-01 | External API supports pagination via ?offset=N | feature | `unverified` | none | | `feature:data-sync` |
| PR-2b-01 | Claude Code loads `@.claude/engine-rules.md` from a project's CLAUDE.md in a headless `-p` session with `--setting-sources project,local` (the path the audit runner uses) | feature | `verified` | tracer probe 2026-10-02T16:01Z: a throwaway repo whose CLAUDE.md held only the marked block + import answered with the passphrase that exists only in the imported file ($0.004); negative control without the import line answered NONE ($0.05). Docs: code.claude.com/docs/en/memory (imports relative to the importing file, depth 4, code blocks skipped) | 2026-10-02 | `feature:engine-package-2b` P1, P2, P5, P7 |
| PR-2b-02 | `evals/make_sandbox.sh` installs the engine through `engine.py install --ref`, so an audit sandbox's CLAUDE.md is the seed of the ref, not this repository's working file | feature | `verified` | make_sandbox.sh step 2 (`engine.py install "$TARGET" --ref "$COMMIT"`); the before-run was started at 15:45Z and kept going through this session's edits | 2026-10-02 | `feature:engine-package-2b` P0, P7 |
| PR-2b-03 | The noise between the two package-3c "before" audit runs is 0.00 on every scenario where both have valid sessions (01, 07, 08) and undefined elsewhere | feature | `verified` | docs/plan/package-3c-report.md § 2.1 noise table; recomputed by evals/compare_audits.py in P7 | 2026-10-02 | `feature:engine-package-2b` P7 |
| PR-2b-04 | A headless `claude -p` session in a never-trusted directory loads no project settings unless `--settings <file>` names them; with it the engine's allow list and hooks apply | feature | `verified` | permission probe 2026-10-02T16:10Z on a v0.11.0 sandbox: plain → `uv run pytest` "requires approval" and the ledger Edit refused (2 denials); `--settings .claude/settings.json` → 0 denials, 4 passed, ledger appended; package 3c C5 found the same for session-claude.sh | 2026-10-02 | `feature:engine-package-2b` P0a, P0, P7 |
| PR-costs-01 | A subagent definition's `model` frontmatter field accepts a model alias (`sonnet`, `opus`, `haiku`, `fable`), a full model ID or `inherit`, and outranks the main conversation's model (order: per-invocation parameter, frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, main conversation) | feature | `verified` | code.claude.com/docs/en/sub-agents, fetched 2026-10-03T11:20Z ("Model alias: use one of the available aliases…", the four-step resolution order); runtime side: this session's Agent tool states "Each agent type's model… come from its definition (frontmatter)" | 2026-10-03 | `feature:engine-package-costs` C5 |
| PR-costs-02 | On the Nth consecutive Stop block `gate.py` appends an entry headed `## <utc> — gate stop layer — PARKED` to `.engine/overseer/parked.md` and lets the turn end | feature | `verified` | .claude/hooks/gate.py `park_escalation` / `finish_stop`; tests/test_gate.py (the Stop counter cases) | 2026-10-03 | `feature:engine-package-costs` C2 |
| PR-costs-03 | The list `gate_allows.py` produces can be computed and rendered inside the overseer Stop hook's single call (same repository root, git available, well under the hook timeout) | feature | `verified` | tracer C1+C2: tests/test_gate_allows.py "the tracer's first half / second half" (the real gate lets a weak well-formed reason through; overseer_stop.py's OVERSEER_REQUEST carries file, line and reason), 57/57 | 2026-10-03 | `feature:engine-package-costs` C2, C3, C6 |
| PR-costs-04 | Headless Claude Code sessions on this machine (`claw`) are logged in, so the release audit can run | feature | `verified` | `claude auth status` → `"loggedIn": true`, 2026-10-03T11:15Z (external state: re-check right before C7) | 2026-10-03 | `feature:engine-package-costs` C7 |

| PR-board-01 | `claude -p … --output-format json` prints one JSON object with `session_id` and `total_cost_usd`, and `--resume <session_id>` continues that conversation headless | feature | `verified` | evals/run_audit_scenarios.py `call_claude` / `parse_json_output` and its `--resume` step (run on this machine in the v0.12.0 audit, 5a3538c); `claude --help` of 2.1.288 lists `-p`, `--resume`, `--output-format` | 2026-10-03 | `feature:engine-package-board` B2, B3 |
| PR-board-02 | On a continued conversation `total_cost_usd` is the conversation's running total, not the last call's cost | feature | `accepted-as-risk` | indirect: ~/engine-ops/events.log 2026-10-03 12:05Z 11.43 → 12:07Z 11.90 → 12:53Z 13.31 for one continued conversation; a paid probe is forbidden by the program (rule 5). The runner stores every attempt's raw figure, so either reading can be recomputed | 2026-10-03 | `feature:engine-package-board` B3 (cost per task, R1 budget) |
| PR-board-03 | A headless session started with `--permission-mode auto --settings .claude/settings.json` can work in this repository | feature | `verified` | ~/engine-ops/run-queue.sh starts every program this way; this very session (commit bea944c made from it) | 2026-10-03 | `feature:engine-package-board` B2, B7 |
| PR-board-04 | `engine.py install` creates a seeded project file once, also in a directory that does not exist yet and also for an empty file | feature | `unverified` | to be verified by tests/test_board.py on a synthetic project (B1) | | `feature:engine-package-board` B1 |
| PR-board-05 | A headless session may commit on `unattended/work` through `commit_checkpoint.sh` | feature | `verified` | commit bea944c (this session, `commit_checkpoint.sh --staged`); the script's `unattended/*` case | 2026-10-03 | `feature:engine-package-board` B2, B3, B7 |
| PR-board-06 | The runner can tell from the working tree and `HEAD` alone that the agent finished a task (the file left `doing/`; `done/NNN-name/` or `blocked/NNN-name.md` exists) | feature | `unverified` | the tracer: tests/test_board_runner.py (B1 + B2, fake `claude`) | | `feature:engine-package-board` B2, B3, B7 |
| PR-board-07 | Headless Claude Code sessions on this machine are logged in | feature | `unverified` | external state: `claude auth status` right before B7 | | `feature:engine-package-board` B7 |
| PR-board-08 | A real headless session given only the task path and `tasks/README.md` performs the task, writes report.md, moves the task to `done/` and commits through `commit_checkpoint.sh` | feature | `unverified` | only the live check (B7) can test it; a fake `claude` follows the README by construction | | `feature:engine-package-board` B7 |

*(Add a new row whenever a plan states a new load-bearing assumption. Ensure the statement is a single falsifiable sentence. If an assumption is falsified, immediately flag all items in the 'depended-on-by' column for review.)*
