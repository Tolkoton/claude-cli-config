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

*(Add a new row whenever a plan states a new load-bearing assumption. Ensure the statement is a single falsifiable sentence. If an assumption is falsified, immediately flag all items in the 'depended-on-by' column for review.)*
