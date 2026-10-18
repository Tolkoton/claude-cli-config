# Slice goals-roles — planning artifact

Driven by the feature `business-goals-focus` (`.engine/architecture/feature/business-goals-focus.md`,
slice S2). Frame supplied by the feature artifact and the owner's task
`tasks/doing/201-business-goals-focus.md` §2–§6; the owner is not asked. Stands on S1 `goals-mechanics`
(the formats and `goals.py trace`, sealed contract `.engine/slices/goals-mechanics.md`).

## Goal
The agents are told, in their definitions, to do what the owner decided: the analyst keeps the journal,
asks for the core, marks what is not the owner's words, runs `preseal` before approval, answers
`NOT_REQUIRED` and guards the goals (`guardian`); the master-architect has the stop «Читання цілей»,
starts M1 with the core, gives every element a source, converges by a condition; the master-critic checks
coverage, necessity, proportionality and consistency first. Measurable: a new suite
`tests/test_goals_roles.py` whose every check is red against the base commit's definitions and green after,
including one that runs S1's `goals.py trace` on the example tables `/master-architect` itself shows.

## Premise verified
- S1's contract out: the formats of `## Ядро`, the matrix, the element tables, `NOT_REQUIRED`, and
  `goals.py trace` — `.engine/slices/goals-mechanics.md` (sealed). Build order: S1 is built and green before
  this slice's first test runs (Seams 1–2 call the built script).
- No hook guards the start of the agent `business-analyst` (PR-goalsfocus-01), so its new modes need only
  its definition.
- `master-critic` has no `tools:` line: it has every tool, WebFetch included (read 2026-10-18).
- `tests/test_context_budget.py` counts CLAUDE.md + AGENTS.md + imports ≤ 200 lines (green 2026-10-18).
- No external system: untested — common knowledge.

## Out of scope (deliberately)
- `feature-critic`, `mvp-critic`, `/plan-slice`, `slice-builder`, `overseer` — the owner's «Чого не робити»;
  shown once as slice evidence (Seam 3), never pinned by a permanent test.
- `.claude/constitution.md`, `.claude/settings.json`; no new hook.
- The quality scenes of `preseal`/`guardian` (task 501); `evals/run_analyst_evals.py` scoring.
- Any detail of the real project: every example is invented (a bookshop, a clinic queue — not the case).
- Code: S1 holds all of it. This slice writes definitions, documents and one test suite.

## Seam (contract)
The texts, each with what the test reads in it (exact strings in backticks):

- **`.claude/agents/business-analyst.md`** — one definition, three modes; the first word of the prompt
  names the mode: `consult <request path>` (or a bare request path — the architects' form today, still
  `consult`), `preseal <draft> <journal>`, `guardian <goals> <journal> <matrix> <artifact>`. The description
  names the three modes and who starts each — `consult` by `/master-architect` or `/feature-architect`,
  `preseal` by `/business-analyst`, `guardian` by `/master-architect` — and no sentence says «only by
  architects». Never the architect's reasoning, in any mode. Output forms,
  verbatim in fenced blocks:
  - `consult`: the two existing forms plus
    ```
    ANALYST_ANSWER: NOT_REQUIRED
    Lines: <рядки, на які спирався запит>
    Чому не вимагають: <...>
    Найменша форма: <нічого не будувати — або одне речення>
    ```
    with the owner's four rules (no standing line requires it; a non-goal is a boundary not a requirement;
    words marked `[не слова власника]` are by themselves no requirement; in doubt `OWNER_DECISION` whose
    first question is whether it is needed at all).
  - `preseal`: lines `PRESEAL_FINDING: <вид> | <рядки> | <слова власника або пояснення> | <питання до
    власника>` or the one line `PRESEAL_CLEAN`; kinds exactly `contradiction`, `unmarked`, `risk-reason`,
    `consequence`, `late-choice`, `lost-emphasis`, `no-core`; what it looks for (the owner's five bullets);
    decides and changes nothing; no limit on the number of findings.
  - `guardian`: lines `GUARDIAN_BLOCK: …` and `GUARDIAN_NOTE: …`, or `GUARDIAN_PASS`; the five questions per
    line; BLOCKING only for the owner's two cases (a core goal without a mechanism that does what the line
    says; a contradiction with a written line).
  - tools stay `Read, Grep, Glob`.
- **`.claude/commands/business-analyst.md`** — the journal `.engine/goals/interview.md` (each question and
  the owner's verbatim answer, with the time; append only); the core question `«Якби працювала лише одна з
  цих цілей — яка?»` written into `## Ядро` with the owner's words; the mark `[не слова власника]` on every
  wording not the owner's; a non-goal is a boundary with the owner's reason, no risk language without his
  words; options as hints allowed, a choice from them marked and taken to the pre-seal check with
  consequences; the pre-seal step — the agent `business-analyst` in mode `preseal` with the paths of the
  draft and the journal, every finding discussed with the owner, as many questions as needed, no limit,
  and only then the whole document shown for approval; the §5 reread stays and does not replace `preseal`.
- **`.claude/commands/master-architect.md`**:
  - the stop `«Читання цілей»` as the first step of M1: the left part of the matrix (how each standing line
    is read, the smallest form and what it forces to build), core first and deepest; a non-goal reads
    «нічого не будуємо» unless a G requires it; an open line with a default reads «діє значення за
    замовчуванням» and is not asked; then `guardian`; the owner gets the reading in plain words, core first,
    with questions where uncertain or heavy; after the answers `«Записав так: …»` and the record of the
    decision (an ADR in `docs/adr/`, the source S1 accepts); only then M1's design;
  - M1 starts from the core: the vision paragraph from «Ядро», the core mechanisms at the level of concepts
    (what they consist of, how they work, input, output), then bounded contexts and the context map; depth
    by status (core domain / supporting / generic);
  - the matrix and element-table formats, one fenced example of each, marked so the test can extract them:
    the matrix block follows the line `<!-- example: traceability -->`, the element table the line
    `<!-- example: elements -->`; both exactly in S1's format; the section `## Пропозиції` with a cost in one
    line; ideas from `docs/research/` and the architect's own stay there until the owner takes them;
    «Звірка з цілями» in `domain-map.md` too;
  - `python3 .claude/hooks/goals.py trace` after every stage draft, every critic round and every owner
    amendment; the guardian at the end of every stage M1–M4 (after MASTER_CRITIC_PASS, before the owner's
    review) and after every owner amendment;
  - the owner's amendment applied narrowly, then a section `«Що ще змінилося в дизайні через цю правку»`,
    `trace`, the guardian again;
  - questions to the owner without a numeric limit, to the end of the topic: not asked when the document
    answers (a line or a default); each with the verbatim quote of the line it comes from, the problem in
    plain words, the consequence of each option, advice; `«Записав так: …»` after the answer, an ambiguous
    answer clarified first; internal labels only explained; the critic rounds' report in a file, one line to
    the owner;
  - an amendment's text only from the analyst's answer or the owner's verbatim words;
  - no running ahead: the next stage's draft only after the previous is approved; technology in M2 except
    what the C lines already fix;
  - premises: each with a source (documentation, commit, PoC) or `unverified`; a claim about an outside
    platform checked against its official documentation before `verified`; nothing unverified told to the
    owner as fact;
  - convergence: the line `round == 4` is gone; the loop with master-critic runs to PASS; stop and revisit the
    base on `oscillation` (the same objection returns) or `divergence` (fixing an objection would add a
    mechanism with no row in the matrix — the element is removed or moved to «Пропозиції», never
    strengthened); `BOARD_MAX_USD` guards an endless loop unattended.
- **`.claude/agents/master-critic.md`** — the lens `goals-fit` gains four checks named `покриття`,
  `необхідність`, `пропорційність захисних механізмів`, `узгодженість доводів`, with the owner's content
  for each; the order: necessity and proportionality before inversion, premortem and the search for
  bypasses, bypasses only for elements that passed both; the one fix for an element without a source is
  removing it or moving it to «Пропозиції», never strengthening; lens `domain` core domain first; technical
  premises checked against official documentation (`WebFetch`), else `MASTER_CRITIC_POC_REQUIRED`.
- **`.claude/references/business-analysis.md`** — the core, the mark, the journal, `preseal`,
  `NOT_REQUIRED`, `guardian`; general method only (no project detail).
- **`docs/OWNER-GUIDE.md`** — the new stop «Читання цілей» and what the owner sees there; the core and the
  mark in the goals document; Ukrainian, technical terms English.
- **`AGENTS.md`** and **`templates/project/AGENTS.md`** — the pipeline line names the analyst's guard of the
  goals, within the context budget.
- **`tests/test_goals_roles.py`** (new, in `tests/fast-suites.txt`): the checks of the Exit criterion.
- Dependencies (injected): none — text and one subprocess of `goals.py trace` on a temporary project.
- Does NOT do: change any script; change the five definitions the owner listed.

## Decisions (with WHY)
- Q1: One definition file for the three modes — chosen because the owner said «той самий business analyst,
  з тим самим методом»; one file keeps one method and one blind-reading rule. Rejected: three agents — three
  descriptions to keep in step, and an agent picked by name could skip the method.
- Q2: A bare request path stays `consult` — chosen because `/feature-architect` (not touched by this task)
  starts the agent with the path alone today; changing that call is outside the owner's list. Rejected: a
  required `consult` keyword — it would break `/feature-architect`'s call, which this task may not edit.
- Q3: The examples of the matrix and element table live in `/master-architect` behind marker comments, and
  the test runs `trace` on them — chosen because the text and the parser then cannot drift (feature-critic
  round 1, note 3). Rejected: a separate example file — one more file the architect does not read.
- Q4: The owner decisions the stop records go into an ADR — chosen because that is the source S1's `trace`
  accepts (S1 Q3). Rejected: recording the decision in the matrix itself (its «Статус» column) — `trace` would
  not accept it as a source, and a matrix cell is not a dated record of the owner's words.

## Hardest seams (test-confidence points)
- **Seam 1: example vs parser.** Extract the two fenced examples, write them as `traceability.md` and
  `domain-map.md` beside a sealed goals document whose lines the examples name (the test builds it from the
  example's numbers), run `goals.py trace` → exit 0, the count line; remove one element's source → refused
  naming that element. The example cites only G/P/C/D lines and, if it names an ADR path, the test writes that
file in the temporary project. Rules out an example nobody runs.
- **Seam 2: NOT_REQUIRED form vs `goals.py`.** The form copied out of the agent definition, filled, written
  as a request → `goals.py requests` says `not-required`. Rules out a form the script does not read.
- **Seam 3: untouched definitions — slice evidence, not a test.** `git diff 86863dd --
  .claude/agents/feature-critic.md .claude/agents/mvp-critic.md .claude/commands/plan-slice.md
  .claude/skills/slice-builder .claude/agents/overseer.md` is empty; its output goes into this slice's PROGRESS
  entry for the overseer. Not a permanent test: the owner's «не чіпати» binds this task, and a pinned diff would
  turn red on the first lawful later edit (and needs the base commit in a shallow clone).
- **Seam 4: absence of the round limit.** `round == 4` absent from `/master-architect`, while `oscillation`
  and `divergence` are present. Rules out deleting the stop without a condition.
- **Seam 5: order and place, not mere presence.** Checks of order compare positions in the text: in
  `master-critic`, inside the `goals-fit` lens, `необхідність` and `пропорційність захисних механізмів` stand
  before the words `inversion`, `premortem` and the search for bypasses in the sentence that orders them; in
  `/master-architect`, «Читання цілей» stands inside the M1 section before the line that begins M1's design
  (`M1 починається з ядра` or its English form). A text naming all of them in the wrong order fails. Red at
  base (none of these words is there).

## Invariants (rules that hold for every input in the stated domain)
None — the slice writes text and lists its checks case by case; no rule over a domain of inputs applies.

## Exit criterion
`tests/test_goals_roles.py`, every check in it first seen red against the base commit's definitions (each
names something the base text lacks or still has): Seams 1, 2, 4 and 5; the three modes and their exact forms
and the seven kinds in the agent; the four named checks in `master-critic`; `«Читання цілей»`, `goals.py
trace`, guardian calls, `«Записав так»` in `/master-architect`; `interview.md`, the core question,
`[не слова власника]`, `preseal` in `/business-analyst`; the method reference names the six things (`Ядро`, `[не слова власника]`, `interview.md`, `preseal`,
`NOT_REQUIRED`, `guardian`);
OWNER-GUIDE names «Читання цілей», «Ядро» and the mark. Seam 3 is evidence in PROGRESS (an empty diff), not a
check of the suite. `bash tests/run_all.sh --fast` green (context budget included). Smoke: Seam 1 run by
hand once with its output in the slice's PROGRESS entry.

## Deferred to later slices
- The quality scenes — task 501 (already on the owner's list).
- The same discipline for feature-critic/mvp-critic — why later: the owner kept them out of this task —
  written at the task's close as one `tasks/proposed/` item (`board.py open-item --to proposed`) whose title
  names feature-critic and mvp-critic; the report names its file.

## Open items requiring human decision
None.

## Critic notes (non-blocking)
- cold reader 2: REVISE (the budget measured from 86863dd would ascribe S1's lines to this slice) — the base
  becomes S1's checkpoint commit, written at sealing after S1 is committed; notes taken: Seam 1's ADR paths,
  the description names who starts each mode, the six strings named. Not re-read a third time: logged
  AUTONOMOUS in `.engine/overseer/escalations.md` (board-201-s2-cold-reader-twice).
- cold reader 1: REVISE — the round-1 fixes below had not reached the file (a replacement script that did not
  check its matches); applied now, each replacement asserted.
- slice-planner-critic round 1: REVISE (Seam 3 green at base, and a permanent pin of five definitions) — Seam 3
  is now PROGRESS evidence; positions instead of presence (Seam 5); Q2/Q4 rejected alternatives; the deferred
  proposal named; the premise restated as a build order.

## Complexity budget
base_commit: 0b0ef00cf7e002bdbab293328461da35b9afb92b
max_new_files: 0
max_net_new_lines: 0
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 13
max_nesting_depth: 3
justification: none — no production code; the new suite is a test
