# Slice critics-goals-discipline — planning artifact

Driven by the feature `business-goals-focus-second` (`.engine/architecture/feature/business-goals-focus-second.md`,
slice S1, tracer bullet). Frame supplied by the feature artifact and the owner's task
`tasks/doing/202-business-goals-focus-second.md` §1–§2; the owner is not asked.

## Goal
The critics stop guarding what the owner never said and stop removing what the owner did say. Measurable: a new
suite `tests/test_critics_goals.py` whose every check is red against the base commit's definitions and green
after (A1–A7 of the feature).

## Premise verified
- «is not built» is at `.claude/agents/master-critic.md` check 6 and no test pins it (`grep -rn "is not built"
  tests/` → only an unrelated `tests/test_testing.py` line), 2026-10-19.
- `tests/test_goals_roles.py` pins in `master-critic.md` the four check names, their order before `inversion`,
  `premortem` and the bypasses, `WebFetch` and «Пропозиції»; this slice keeps all of them (read 2026-10-19).
- No external system: untested — common knowledge.

## Out of scope (deliberately)
- `/master-architect`, the analyst, the template — S2.
- `/feature-architect`'s and `/mvp-architect`'s calls of their critics: the critics read the journal themselves
  (feature artifact, round 1).
- `/plan-slice`, `slice-builder`, `overseer` (the owner's list); the scene g and k rules stay.
- Code: none. Definitions and one test suite.

## Seam (contract)
The texts, each with what the test reads in it (exact strings in backticks):

- **`.claude/agents/critic-core.md` §0** — the owner's own written text keeps its status: the feature frame,
  the plan (`docs/plan/*.md`), the "ЩО ЗРОБИТИ" items of the owner's task stay owner requirements, and the
  string `ЩО ЗРОБИТИ` stays in §0. The quote rule governs a mark in a draft: an owner requirement or owner
  decision that a draft claims is one only with the owner's verbatim words and their source:
  `the time of the remark` or `the interview journal` (`.engine/goals/interview.md`) — or the owner's written
  text named above, quoted. A mark «owner decision» / «рішення власника» without a quote is an agent
  decision and is reviewed like any other. The clause that made any mark untouchable — `anything the draft
  marks as an owner requirement or owner decision` — is replaced: the string is absent from §0 (between `## 0.`
  and `## 1.`). The section keeps its title `## 0. Owner requirements are not under review`.
- **`.claude/agents/master-critic.md`**:
  - «What you receive» names `journal` — the interview journal `.engine/goals/interview.md`, the owner's words,
    not the architect's reasoning (Art. 6 holds); used by checks 5 and 6.
  - Check 5 (покриття): a step a person does (the owner reads, writes, approves) `is no mechanism of the
    system` where the line says the system does it; an amendment giving access (`власник читає все`) is a right of
    access, not a duty to write.
  - Check 6 (необхідність): no `is not built`. The mark `[не слова власника]` means `перевір суть`: an element
    whose substance the owner said (in «Ядро» or in the journal) stands; an element resting on a line marked
    `[не слова власника]` whose substance the owner never said is a NON_BLOCKING_NOTE and a question for the owner — `питання, не видалення`. Stated as an
    explicit exception to the lens's line «A breach is BLOCKING»: that sentence names the mark itself as the
    exception (`except` and `[не слова власника]` in the same sentence) — only an element resting on marked
    words; a mechanism built around a non-goal and an element with no source stay BLOCKING (scene g), and the
    sentence `A mechanism built around a non-goal is a breach` stays in check 6.
  - Cause first: a risk the draft created by its own choice — the fix the objection names is changing that
    choice, not adding a mechanism. The words `change the choice`.
  - No numbers: a threshold, budget or limit no G or C line names is an objection or a note;
    `MASTER_CRITIC_POC_REQUIRED` asks to measure and show, not for pass/fail thresholds: the verdict line
    `MASTER_CRITIC_POC_REQUIRED:` itself holds `measure and show`; the sentence on invented numbers holds
    `no G or C line names`.
- **`.claude/agents/feature-critic.md`**, lens `goals-fit`: checks `необхідність` and `пропорційність захисних
  механізмів` (content as in master-critic: a source G/P/C/D or an owner's ADR, a non-goal no source; a
  protective mechanism needs a line, a plausible scenario at the stated scale and a named cost), placed before
  the words `inversion`, `premortem` and the bypasses in the sentence that orders them; the one fix for an
  element without a source — remove it or move it to «Пропозиції», never strengthen; the mark rule
  (`перевір суть`, `питання, не видалення`, inside the `goals-fit` lens) as an explicit exception to its «A
  breach is BLOCKING», named in that same sentence (`except` and `[не слова власника]`); reads
  `.engine/goals/interview.md` itself when it exists. The remove-or-move fix governs the architect's elements;
  an acceptance criterion citing no G or D stays `FEATURE_CRITIC_ESCALATE`, as today.
- **`.claude/agents/mvp-critic.md`**: the same two checks and one fix, placed before question `1. **Simpler?**`,
  and applied only when the goals document was given — an MVP does not require one; the block from its first
  check to `1. **Simpler?**` holds `goals document`, `перевір суть` and `питання, не видалення`; reads `.engine/goals/interview.md` itself when it exists.
- **`tests/test_critics_goals.py`** (new, in `tests/fast-suites.txt`).
- Dependencies: none — text only.
- Does NOT do: change any command file or script.

## Decisions (with WHY)
- Q1: The critics at the feature and MVP levels read the journal themselves — chosen because it is the owner's
  words (Art. 6 holds) and no architect call changes (P7). Rejected: a `journal` key in both architects' calls —
  two more files for the same effect; its best case — the critic gets the journal explicitly, as master-critic
  will — does not outweigh P7 and the frame's «their architects' calls are not changed».
- Q2: Check 6's rule as an explicit exception to the lens's «A breach is BLOCKING» — chosen because the generic
  line would otherwise override it (feature-critic round 1, note 4). Rejected: rewording the generic line — it
  governs checks 1–4 too, where BLOCKING is right.
- Q3: One new suite, not more checks in `tests/test_goals_roles.py` — chosen because that suite is board 201's
  sealed contract tests; a new suite keeps each slice's tests its own. Rejected: extending the old suite.

## Hardest seams (test-confidence points)
- **Seam 1: the exception, not mere presence.** The test reads check 6's own text (from `6. **необхідність**`
  to `7. **`) and finds there `перевір суть` and `питання, не видалення`, and nowhere in the file `is not built`.
  Rules out the words standing in another check where they bind nothing. The same for check 5 (from
  `5. **покриття**` to `6. **`): `is no mechanism of the system` and `власник читає все`. And the BLOCKING line of
  each lens names the exception: the sentence holding «A breach is BLOCKING» holds both `except` and
  `[не слова власника]`; and `A mechanism built around a non-goal is a breach` still stands in check 6.
- **Seam 2: order by position, inside one sentence.** In feature-critic `inversion` and `premortem` already
  stand earlier in the file, so position in the file proves nothing: the test takes the `goals-fit` lens (from
  `**\`goals-fit\`**` to the next `## `), finds the one sentence that orders them (as `tests/test_goals_roles.py`
  does) and compares positions inside it. In feature-critic's `goals-fit` lens `необхідність` and `пропорційність
  захисних механізмів` stand before `inversion`, `premortem` and `bypass` in the ordering sentence; in
  mvp-critic both stand before `1. **Simpler?**`. A text naming them after fails.
- **Seam 3: the quote rule replaces the old clause.** Inside critic-core §0 (between `## 0.` and `## 1.`): the
  two sources present AND `ЩО ЗРОБИТИ` still present AND the string `anything the draft marks as an owner requirement or owner decision`
  absent. Rules out a build that adds the quote sentence beside the clause that keeps an unquoted mark
  untouchable.

## Invariants (rules that hold for every input in the stated domain)
None — the slice writes text and lists its checks case by case; no rule over a domain of inputs applies.

## Exit criterion
`tests/test_critics_goals.py`, every check first seen red against the base definitions: Seams 1–3; master-critic
names `journal` and `.engine/goals/interview.md` in «What you receive», check 5's manual work and right of
access, `change the choice`, `measure and show`; feature-critic and mvp-critic name `.engine/goals/interview.md`,
the two checks, the one fix and the mark rule; and `tests/test_goals_roles.py` stays green. `bash
tests/run_all.sh --fast` green. Smoke: the suite run by hand once with its output in PROGRESS.

## Deferred to later slices
- `/master-architect` passing `journal` to the critic — S2 (feature contract S1 → S2).
- The quality scenes — task 502.

## Open items requiring human decision
None.

## Critic notes (non-blocking)
- slice-planner-critic round 1: REVISE (Seam 3 would pass with the old clause kept) — fixed: the clause is
  replaced and its absence tested. Notes taken: mvp-critic's two checks only with a goals document; the
  exception named in each BLOCKING line and tested; check 5's exact string and scope; Q1's steelman; Seam 2
  inside one sentence of the lens.
- cold reader 1: REVISE (the exception named «check 6» whole would unblock non-goal breaches) — fixed: the
  exception names the mark only, and the non-goal sentence is pinned. Notes taken: mvp-critic's block anchored
  before `1. **Simpler?**`; `measure and show` on the verdict line; the mark strings scoped to each lens; the
  justification names the test file.
- cold reader 2: REVISE (the quote rule worded as «only» could strip the owner's written task items of their
  status) — fixed: the owner's written text keeps its status and `ЩО ЗРОБИТИ` is pinned; the quote rule governs a
  mark in a draft. Notes taken: `no G or C line names` pinned; check 6's note sentence names the mark; feature-
  critic's escalate rule for acceptance criteria kept beside the new fix. Not taken: a quote line in mvp-critic —
  it does not inherit critic-core and has no «untouchable owner decision» clause, so it already reviews
  everything; said in the report. Not re-read a third time: logged AUTONOMOUS in
  `.engine/overseer/escalations.md` (board-202-s1-cold-reader-twice).

## Complexity budget
base_commit: 833d43fbf84a59133323871c4589ef75e33ff84f
max_new_files: 0
max_net_new_lines: 0
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 13
max_nesting_depth: 3
justification: none — no production code; the one new file, tests/test_critics_goals.py, is a test
