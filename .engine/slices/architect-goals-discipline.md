# Slice architect-goals-discipline — planning artifact

Driven by the feature `business-goals-focus-second` (`.engine/architecture/feature/business-goals-focus-second.md`,
slice S2). Frame supplied by the feature artifact and the owner's task
`tasks/doing/202-business-goals-focus-second.md` §3–§4; the owner is not asked. Stands on S1
`critics-goals-discipline` (sealed, built, commit 1d24f9f): master-critic's «What you receive» names `journal`.

## Goal
`/master-architect` reads the goals the way the owner meant them and stops inventing what the owner never said:
four checks at the stop «Читання цілей», an «owner decision» only with a quote, cause before protection, numbers
only from the goals, each stage shown on its own, the operator's facts from `docs/infra.md`, a new requirement
through the analyst first; the guardian notes an unquoted «owner decision»; a project gets `docs/infra.md` from
its seed. Measurable: a new suite `tests/test_architect_goals.py` red against the base text and green after, and
an install check in `tests/test_project_seeds.py` red before the seed line and green after (A8–A11 and the
integration exit criterion of the feature).

## Premise verified
- S1's contract out: `.claude/agents/master-critic.md` «What you receive» names `journal` = `.engine/goals/interview.md`
  (commit 1d24f9f, overseer PASS 20261019T075835Z-cb0024).
- `/master-architect` has exactly one `Task(agent="master-critic", input={phase, draft, product_frame, maps})`
  line (`.claude/commands/master-architect.md:46`, read 2026-10-19).
- `tests/test_project_seeds.py` installs from a temporary engine repository built from the working tree, so a new
  seed line and template are seen by it (its docstring and `engine_repo_from_working_tree`, read 2026-10-19).
- A `project <path> seed=<file>` line creates the file once on install when the project lacks it
  (`.claude/ownership.txt` header; `tests/test_engine_install.py` «seed: a seed is created once»).
- `tests/test_goals_roles.py` pins in `/master-architect`: «Читання цілей» before the line beginning M1's design,
  `goals.py trace`, the guardian, «Записав так», `oscillation`, `divergence`, no `round == 4`, the two examples
  behind `<!-- example: … -->`; this slice keeps them all. Other readers of the text, kept green by the fast set:
  `tests/test_business_goals_focus_block.py`, `tests/test_goals.py`, `tests/test_model_roles.py`;
  `evals/run_focus_evals.py` scene j reads the whole definition (task 502's scenes, not this slice).
- No external system: untested — common knowledge.

## Out of scope (deliberately)
- The critics — S1. `/feature-architect`, `/mvp-architect` calls — unchanged (feature artifact, round 1).
- `/plan-slice`, `slice-builder`, `overseer`, the constitution, `settings.json`.
- The analyst's other modes and `/business-analyst` (task §4: «Решту не змінювати»).
- A script that checks quotes or reads `docs/infra.md`: judgment of the architect, the critic and the guardian.
- Anything from the real project: every example is invented.

## Seam (contract)
The texts, each with what the test reads in it (exact strings in backticks; a test collapses whitespace):

- **`.claude/commands/master-architect.md`**:
  - The proposal loop's critic call is `Task(agent="master-critic", input={phase, draft, product_frame, journal,
    maps})`, with a comment that `journal` = `.engine/goals/interview.md`. The test parses the `input={…}` of the
    one line holding `Task(agent="master-critic"` and finds the key `journal` there (S1 → S2 contract).
  - M1 step 1, «Читання цілей», gains four checks, inside the step (between `## M1, step 1` and `## M1, step 2`),
    each with its string: `one person in two roles` (for every pair of lines, do they pull apart for a person who
    has two roles — the owner as a user and as the developer; if so, a question to the owner with `both lines
    verbatim`); a non-goal is `never an option` of a mechanism in a question — a question about a non-goal asks
    only `whether anything is needed at all`; ideas from research stand `only in «Пропозиції»`, never an option in
    a question; a done-when line that needs people asked regularly is shown to the owner with its consequences —
    `whom, how often` and `those who do not come back`.
  - A section `# Owner decisions, causes, numbers, stages` (between «The goals during every stage» and
    «Pre-flight») with:
    - **owner decision only with a quote**: every record «owner decision» / «рішення власника» in the architect's
      artifacts carries the owner's verbatim words and their source — `the time of the remark` or `the interview
      journal`; without a quote it is the architect's decision and is marked `рішення архітектора`;
    - **cause before protection**: before adding a mechanism against a risk, check whether the risk comes from
      the draft's own choice; if so, `change the choice`;
    - **no invented numbers**: thresholds, budgets and limits only those a G or C line names; a PoC and the
      walking skeleton `measure and report`, and the owner judges the result by reading it;
    - **each stage shown separately**: M1, M2, M3 and M4 — each with its own plain explanation and its own
      diagram; approval is never asked for `what is not in this message`; the simplifier's findings and the
      others stand in that same message;
    - **a new requirement mid-stage** goes first as a request to the business analyst (`reason 4` of
      `.claude/references/business-analysis.md` §6 — the goals are changing); it enters the design only once it
      has a line in the goals.
    - The test reads these five rules only between `# Owner decisions, causes, numbers, stages` and
      `# Pre-flight`, and the Pre-flight strings only from `# Pre-flight` to the next `# ` heading.
  - **Pre-flight** reads `docs/infra.md` — the cloud project, the region, the runner's access, what is already
    deployed; if the file is missing, `one question` to the owner listing what is needed; `the operator writes
    it`; template `templates/project/docs/infra.md`.
  - The source wording (the time of the remark, the interview journal) is the same as in `critic-core` §0.
- **`.claude/agents/business-analyst.md`**, mode `guardian`: one more check, over the whole artifact (not per
  line of the matrix), and always a note, never BLOCKING — a record «owner decision» /
  «рішення власника» without the owner's verbatim words and their source (`the time of the remark` or `the
  interview journal`) is a `GUARDIAN_NOTE`. The test reads the guardian section (from `## Mode \`guardian\`` to the
  next `## ` or the end).
- **`templates/project/docs/infra.md`** (new): a short template for the operator — headings `Хмарний проєкт`,
  `Регіон`, `Доступ для runner-а`, `Що вже розгорнуто`; who writes it (the operator) and who reads it
  (`/master-architect` pre-flight); invented placeholders only.
- **`.claude/ownership.txt`**: `project  docs/infra.md  seed=templates/project/docs/infra.md`, placed before any
  rule that would match `docs/infra.md` first.
- **`docs/OWNER-GUIDE.md`**: under «Документ цілей і зупинка «Читання цілей»» — the four new checks in plain
  words, «рішення власника» only with your words, each stage shown on its own, and `docs/infra.md` (what to write
  there and that the architect asks once if it is missing). Ukrainian, technical terms English.
- **`tests/test_architect_goals.py`** (new, in `tests/fast-suites.txt`) and **`tests/test_project_seeds.py`**
  (one more check: after install `docs/infra.md` exists and equals the template).
- Dependencies: none — text, one ownership line and one template.
- Does NOT do: change any script or hook.

## Decisions (with WHY)
- Q1: The four reading checks live inside M1 step 1, the rules in one new section — chosen because the checks
  belong to the stop and the rules bind every stage; one place each keeps them findable. Rejected: scattering the
  rules into M2/M3/M4 — four copies to keep in step.
- Q2: The install check extends `tests/test_project_seeds.py` — chosen because it already installs from the
  working tree; a second installer harness would duplicate it. Rejected: a pure `owner_of` check in the new suite —
  it would not show the file actually lands in a project (P1: the behaviour, not the table).
- Q3: The template has headings and placeholders only — chosen because the operator writes it and the repository
  is public (the owner's rule 3). Rejected: a filled example — invites copying invented values as facts.

## Hardest seams (test-confidence points)
- **Seam 1: the key in the call, not in the file.** The word `journal` already stands near the guardian calls;
  the test parses the `input={…}` of the one `Task(agent="master-critic"` line. Red at base.
- **Seam 2: inside the stop.** The four check strings are searched only between `## M1, step 1` and
  `## M1, step 2`; a text putting them elsewhere fails.
- **Seam 3: the same two sources in three files.** `the time of the remark` and `the interview journal` in
  `critic-core` §0, in `/master-architect` and in the guardian section. Drift between them fails.
- **Seam 4: the seed lands.** `tests/test_project_seeds.py` installs into a fresh project and finds
  `docs/infra.md` byte-equal to the template; red without the ownership line.

## Invariants (rules that hold for every input in the stated domain)
None — the slice writes text and one seed line and lists its checks case by case; no rule over a domain of inputs
applies.

## Exit criterion
`tests/test_architect_goals.py`, every check first seen red against the base text: Seams 1–3; the section's five
rules by their strings; Pre-flight's `docs/infra.md`, `one question`, `the operator writes it`; the guardian's
`GUARDIAN_NOTE` sentence; the template's four headings; the ownership line; OWNER-GUIDE names `docs/infra.md` and
«рішення власника». `tests/test_project_seeds.py` Seam 4. `tests/test_goals_roles.py` stays green. `bash
tests/run_all.sh --fast` green (context budget included). Smoke: both suites run by hand once with the output in
PROGRESS. The template is staged (`git add`) before the fast run: `tests/test_ownership.py` requires every seed
to be a tracked file.

## Deferred to later slices
- The quality scenes — task 502.
- The feature's closing step (proposals 1756–1759 removed, the full set and the golden set) — after this slice,
  by the feature, not by the slice.

## Open items requiring human decision
None.

## Critic notes (non-blocking)
- slice-planner-critic round 1: PASS. Notes taken: the rules and Pre-flight strings scoped to their sections; the
  guardian check artifact-wide and a note; the other readers named; the template staged before the fast run;
  `reason 4` cited to its source.
- cold reader: PASS. Notes taken: the new section holds no fenced block with `# ` lines; the closing step named
  under «Deferred». Q2's rejected option is cheaper and needs no git — still rejected: it would not show the file
  lands in a project.

## Complexity budget
base_commit: 1d24f9f4f074aa8e5ca03d253876a01f4410b85f
max_new_files: 0
max_net_new_lines: 0
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 13
max_nesting_depth: 3
justification: none — no production code; the new files are a test and a project template
