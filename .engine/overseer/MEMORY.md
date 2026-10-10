# Overseer cross-slice memory

Entries here are added only when a pattern recurs across 3+ slices, OR when
the user has manually ratified a pattern. Empty initially.

## Citation-or-prune rule (load-bearing)

Every entry in this file MUST cite at least two ledger.md entries by
date+slice. Uncited entries are deleted on next read. This prevents
memory pollution and confabulation amplification.

## Source-of-truth pointers

- Project conventions: `CLAUDE.md`
- Slice ledger: `.engine/PROGRESS.md`
- Architectural decisions: `docs/adr/`
- TDD discipline: slice-builder skill
- Overseer ledger: `.engine/overseer/ledger.md`
- Human escalations log: `.engine/overseer/escalations.md`
- Self-improvement proposals: `.engine/overseer/audit.md`

## Cross-slice patterns

## 2026-08-27 — A passing test proves nothing until it has failed for the right reason

On this machine, verify the negative case before trusting the positive one. A
check that silently degrades to "no output, exit 0" looks identical to a check
that passed.

**The specific trap: the `jq` idiom.** `VAL=$(echo "$INPUT" | jq -r '...' 2>/dev/null || echo "")`
followed by `[ -z "$VAL" ] && exit 0` reports success when `jq` is absent. Four
hooks used it; with `jq` missing, `git commit`, a recursive root delete, and a
write to `.env` all returned exit 0 from hooks that exist to block them.

**Second trap, same shape, found in the same pass:** encoding a hook decision
with a heredoc instead of `jq -n`. `protect-paths.sh` interpolated regex
patterns containing backslashes (`\.env$`) straight into a JSON string,
emitting 406 bytes of invalid JSON. The harness cannot parse it, so the deny is
lost — again indistinguishable from "allowed" unless you validate the output.

Both were found only because a *deny* case was asserted, not just an *allow*
case. Assert the block.

- Cited: `ledger.md` 2026-08-27T17:42:42Z (jq absent; three enforcement tests
  returned exit 0) and `ledger.md` 2026-08-27T18:07:44Z (post-install retest;
  `protect-paths.sh` malformed-JSON defect and its fix).
- Owner reports two earlier instances of the same harness-shaped class this
  slice — a mutation that did not apply, and a harness that died mid-mutation.
  Recorded as the owner's observation; not independently verified here, and
  carrying no citation of mine.

## 2026-10-07 — A scorer that matches findings by words must be tested with a finding that names two entri

A scorer that matches findings by words must be tested with a finding that names two entries of opposite kinds (a planted item AND its trap), in both directions — aimed at the trap's line and aimed at the planted item's line. When an audit finds a gap in one direction, check the mirror case before claiming the fix: on board 059 the first fix closed one direction and the next audit blocked on the other.

Cited: 2026-10-07T03:41:47Z 059-simplifier-harder-eval-set; 2026-10-07T04:13:04Z 059-simplifier-harder-eval-set. Origin: lesson #2084c5b8 (overseer, -, 2026-10-07).

## 2026-10-10 — A suite run only inside a cloud session sees CLAUDE_CODE_SESSION_ID and never takes the pa

A suite run only inside a cloud session sees CLAUDE_CODE_SESSION_ID and never takes the path of the owner's own terminal. When code branches on the session (journal.py falls back to a working-tree id in .claude/state/), run the suites it touches once more with env -u CLAUDE_CODE_SESSION_ID before claiming the unit; CLAUDECODE an agent may not clear (block-dangerous.sh refuses it), and the suites strip it themselves where it matters.

Cited: 2026-10-10T07:49:44Z unknown OVERSEER_BLOCK (board 739, attempt 1); 2026-10-10T08:55:57Z unknown OVERSEER_BLOCK (board 739, attempt 2: the owner's-terminal case). Origin: lesson #650da1b1 (overseer, -, 2026-10-10).
