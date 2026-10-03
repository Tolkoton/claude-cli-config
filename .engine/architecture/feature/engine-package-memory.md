# Feature engine-package-memory — event-driven self-learning

Frame source: `docs/plan/package-memory.md` (the owner's text, verbatim). Every numbered item is an
owner requirement; the critic checks how each is met, not whether. Branch
`unattended/2026-10-03-package-memory` from the end of package A (`0e2b0fa`). Rules carried over
from `docs/plan/night-1.md`: tests, golden set, ruff and `mypy --strict` after every slice; UTC;
new commits only; no paid sessions.

## Goal

What the work learns stops depending on a model remembering to write it down: hooks append
candidates to a queue from the events the engine already produces (a gate block, an overseer
BLOCK, a parked item, an escalation), the agent adds what only it can see (a non-obvious cause),
the queue is triaged when a unit is verified, and nothing reaches the persistent context except
through the overseer and a line-budgeted file.

## Out of scope (deliberately)

- `.claude/settings.json` (owner-only). Everything that can ride on hooks already wired does; the
  one thing that cannot (the stuck counter on Bash results) is a parked proposal with its own
  test and one command (`docs/tasks/lesson-hooks.json`, `apply-lesson-hooks.py`).
- The overseer's text (`.claude/skills/overseer/SKILL.md`): unchanged. "The overseer checks the
  proposals" is a deterministic gate in `promote`, not a new overseer rule.
- Writing CLAUDE.md. Never, by anything here.

## Decisions (agent; two-way unless stated; logged AUTONOMOUS in escalations.md)

- **M1 carriers, not new hook entries.** SessionStart → `env-check.sh` (the wired SessionStart
  hook; silent when there is nothing to say); Stop collection and the stuck counter → `gate.py`
  (runs every Stop and every post-write); verdict collection and the review request →
  `overseer_stop.py` (the one place that parses verdicts). All of it lives in one module,
  `lesson_queue.py`, so a later move to dedicated settings entries changes wiring, not behaviour.
- **M2 the queue's identity.** A candidate's id is a hash of source + the essence with digits
  and spacing normalised; every id ever seen is kept in machine state, so a triaged and removed
  candidate is not re-collected from a source that still contains it (parked.md is append-only).
- **M3 sources.** gate (blocking findings of a Stop block), overseer (`OVERSEER_BLOCK:` on its
  own line, collected by the overseer hook — not from the ledger, which would double-count),
  parked (PARKED entries, not their RESUMED twin), escalation (every kind except AUTONOMOUS,
  which is a decision log, not a lesson), agent (`lesson_queue.py add`).
- **M4 the review is a request, the filing is a command.** After an overseer PASS the continue
  text gains `LESSON_REVIEW_REQUESTED` when the queue is not empty; the agent files with
  `resolve <id> --to memory|rule|engine|discard`. `memory` demands two ledger citations (the
  memory file's own citation-or-prune rule), `rule` demands text and a reason and writes a
  PROPOSAL, a resolved candidate leaves the queue.
- **M5 stuck = the same failure three times.** The key is the failure's fingerprint, digits
  normalised; the third in a row answers with the stuck protocol as `additionalContext`, a
  success resets, it never blocks. Fed by post-write lint, Stop blocks, and (once wired) Bash
  failures.
- **M6 the digest is bounded** (1200 characters): the latest memory headings, the queue's size,
  proposals waiting, and the clean-up proposal when the queue passes 30 entries or 14 days have
  passed since the last `cleanup-done` (the first call only starts the clock).
- **M7 promotion is the overseer's gate in code.** `promote <id>` appends to `.engine/rules.md`
  only when the ledger holds an entry naming `rule-proposal <id>` that contains OVERSEER_PASS,
  and refuses — leaving the file as it was — when CLAUDE.md plus its imports would pass 200
  lines. CLAUDE.md imports `.engine/rules.md` (seed, ownership entry, budget test included).
- **M8 the skill's old text said the opposite** (queue in `.claude/`, never write MEMORY.md
  silently): the queue moves to `.engine/lesson-queue.md` everywhere in the skill; rule 2 now
  distinguishes attended confirmation from the hook's request.

## Slice DAG

| id | slice | verification |
|---|---|---|
| B1 | `lesson_queue.py`: queue, collectors, add, resolve, promote | tests/test_lesson_queue.py |
| B2 | carriers: gate, overseer hook, SessionStart | same suite, hook-level cases |
| B3 | skill text, `.engine/rules.md` import, seed, ownership, budget test | test_context_budget, test_ownership, test_text_hygiene |
| B4 | golden scenarios for the new behaviour; new reference | evals run, compare to results-package-7.json |
| B5 | the parked wiring proposal | tests/test_lesson_hooks_proposal.py |

## Hardest seams

1. **Dedup across a triage**: without the seen-id set, parked.md would refill the queue the
   moment it was emptied.
2. **Never into the persistent context**: three separate guards — no code path writes CLAUDE.md,
   `rules.md` is written only by `promote`, `promote` needs the ledger PASS and the line budget.
3. **The carriers' failure must not change their own verdicts**: every call into the module is
   best-effort (the gate's and overseer hook's outputs are byte-identical when the queue is empty).

## Revisions after the critic (FEATURE_CRITIC_REVISE, fresh context, after the first build)

- **Blocking 1 — history backfill.** The first `collect` on a project only seeds: what parked.md
  and escalations.md already hold is marked seen, not queued; a parked item with a RESUMED twin and
  an escalation with `Status: CLOSED|RESUMED|RESOLVED` are never candidates. Run against this
  repository's real files the first call now queues nothing (it queued 18).
- **Blocking 2 — "the overseer checks the proposals".** A pending proposal alone now triggers a
  `RULE_PROPOSALS_PENDING` request that tells the reviewing session exactly how to run the overseer
  on it; `promote` accepts only a ledger chunk HEADED `rule-proposal <id>` that carries the verdict
  marker alone on a line (a chunk that merely quotes the id and the marker does not count). The
  overseer skill text is still unchanged (night rule 0.4): the gate is only as strong as the
  ledger's integrity, which is the same trust every other ledger-based check here rests on.
- **Should-fix, all done:** carriers catch TypeError/KeyError/AttributeError too (a corrupt state
  file cannot change a hook's verdict); the review request repeats only when the queue or the
  proposals changed, else every third PASS; stuck keys use the sorted set of all blocking/warning
  findings, an empty text is never counted; a rule text with an `@path` is refused; the seen-id
  cap is 20000.
- **Decision M9 (critic #4):** the review is requested after a PASS only. A BLOCK means the unit is
  not finished and the agent is fixing it; candidates wait for the next PASS rather than interrupt a
  repair. Cost to reverse: one condition in `_lesson_review`.
