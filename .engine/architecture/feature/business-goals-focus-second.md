# Feature business-goals-focus-second — decomposition

Frame source: board task `tasks/doing/202-business-goals-focus-second.md` (the owner's text: «Рішення
власника» 1–3, «Що зробити» §1–§5, «Чого не робити», «Готово, коли»). Every numbered item of the task is an
owner requirement; the critic checks how each is met, not whether. Unattended: the owner is not asked.
Nothing in this frame is PROVISIONAL — the acceptance criteria are the task's own list, and the autonomy
grant is the task itself (placed in the runner's queue with `Режим: конвеєр`). Builds on the feature
`business-goals-focus` (board 201, `.engine/architecture/feature/business-goals-focus.md`).

## Goal

Close the three misses scenes h, i, j of board 501 showed and the six failures of a real project's stages
M2–M4: a critic reads the mark `[не слова власника]` as «check the substance», never as «remove»; a person's
manual work is not taken for a mechanism of the system; an «owner decision» counts only with the owner's
verbatim words and their source; a risk the draft created by its own choice is fixed by changing the choice,
not by a mechanism; no number the goals do not name; every stage M1–M4 is shown on its own; the operator's
facts are read from `docs/infra.md`; a new requirement mid-stage goes to the analyst first. `feature-critic`
and `mvp-critic` gain necessity and proportionality in the same order as `master-critic`.

## Acceptance criteria (the owner's, from the task's «Готово, коли» and «Що зробити»)

- **A1** `master-critic` check 6 (необхідність): no «is not built»; the mark means «перевір суть»; an element
  whose substance the owner said (core or journal) stands; an element with no owner's words behind it is a
  note and a question for the owner — «питання, не видалення», never a BLOCKING removal.
- **A2** `master-critic` receives the interview journal `.engine/goals/interview.md` beside `product_frame`;
  `/master-architect` passes it (and to the guardian, as today).
- **A3** `master-critic` check 5 (покриття): a step a person does (the owner reads, writes, approves) is not a
  mechanism of the system where a goals line says the system does it; an amendment giving access («власник
  читає все») is a right, not a duty to write.
- **A4** `critic-core` §0: an owner requirement or decision is only what has the owner's verbatim words and a
  source (the time of the remark, or the interview journal); «рішення власника» without a quote is an agent
  decision, reviewed like any other. Applies to every critic.
- **A5** `master-critic`: a risk the draft created by its own choice — the fix in the objection is to change
  the choice, not to add a mechanism.
- **A6** `master-critic`: `MASTER_CRITIC_POC_REQUIRED` asks to measure and show, not for pass/fail
  thresholds; a threshold, budget or limit no G or C line names is an objection or a note.
- **A7** `feature-critic` and `mvp-critic`: necessity and proportionality of protective mechanisms, before
  inversion, premortem and the search for bypasses; one fix for an element without a source (remove it or
  move it to «Пропозиції»); the same rule of the mark as A1. Each reads the interview journal
  `.engine/goals/interview.md` itself when it exists (the owner's words, not the author's reasoning — Art. 6
  holds); their architects' calls are not changed. In `mvp-critic`, which has no inversion/premortem moves,
  necessity and proportionality come before its question 1 («Simpler?»).
- **A8** `/master-architect` «Читання цілей» has four checks: one person in two roles (a pair of lines that
  pull apart → a question with both lines verbatim); a non-goal never an option of a mechanism in a question
  (only «is anything needed at all»); research ideas only in «Пропозиції», never an option of a question; a
  done-when that needs people asked regularly is shown with its consequences (whom, how often, those who do
  not come back).
- **A9** `/master-architect` rules: an «owner decision» only with a quote and its source, else marked as the
  architect's; cause before protection; no invented numbers (PoC and walking skeleton measure and report, the
  owner judges); each stage M1–M4 shown separately with its own plain explanation and diagram, approval never
  asked for what is not in that message; `docs/infra.md` read at pre-flight (missing → one question listing
  what is needed; the operator writes it); a new requirement mid-stage goes to the analyst first (reason 4),
  into the design only once it has a goals line; the journal passed to master-critic and the guardian.
- **A10** `business-analyst` mode `guardian`: an «owner decision» without verbatim words and a source is a
  `GUARDIAN_NOTE`. Nothing else in the analyst changes.
- **A11** `templates/project/docs/infra.md` exists; `.claude/ownership.txt` seeds it (`project docs/infra.md
  seed=…`); `engine.py install` creates it in a project.
- **A12** Definition tests for all the above, green; golden set identical except what is intended; the
  context budget not exceeded; proposals 1756–1759 removed from `tasks/proposed/`, one report line each.

## Build parameters

- Budgets/thresholds: none (the task forbids numeric limits on questions and findings).
- Policies: text changes to definitions; the only file outside `.claude/` and `tests/` is the template and the
  ownership line; standard library only in tests; every example invented (the repository is public).
- Tests: each definition test first seen red against the base text; `bash tests/run_all.sh --fast` after
  every slice, the full set once at the end.
- Risk tolerance: spikes run without asking; a passing spike never interrupts.
- Autonomy: both slices built in DAG order; interrupts only on the critical set.
- Principles that bear on the slices (in words): what a script can check, a script checks — the seed is
  checked by an install test, the texts by definition tests (P1); numbers only as guards against looping,
  never quality limits — hence «no invented numbers» (P6); the simplest shape, a template not a new script
  (P7); protect against what really happened — every rule here comes from a scene or a real stage (P8).
- Not touched (the task's «Чого не робити»): `/plan-slice`, `slice-builder`, `overseer`,
  `.claude/constitution.md`, `.claude/settings.json`; the scene g and k rules stay (a non-goal is no source;
  necessity before bypasses).

## Premises verified

- PR-focus2-01 — a `project … seed=` line in `.claude/ownership.txt` makes `engine.py install` create the file
  once in a project: `tests/test_engine_install.py` («install: CLAUDE.md starts from its seed», «seed: a seed
  is created once») over the same mechanism the task-board seeds use, read 2026-10-19. Verified.
- PR-focus2-02 — no test pins the words «is not built» of check 6 (`grep -rn "is not built" tests/` → none),
  2026-10-19. Verified.
- PR-focus2-03 — `tests/test_ownership.py` requires every seed to be a tracked, non-shipped file; a seed under
  `templates/project/` is `project`-owned by the catch-all `project **`, read 2026-10-19. Verified.

## Out of scope (deliberately)

- The quality scenes — task 502.
- `/plan-slice`, `slice-builder`, `overseer` (the owner's list).
- A script that checks a quote behind «рішення власника»: the critic's and guardian's judgment.
- Anything from the real project: every example is invented.

## Звірка з цілями
- служить: G3 (бізнес — джерело правди: an owner decision only with the owner's words; a new requirement gets
  a goals line before design), G4 (складність під контролем: no mechanism for a self-made risk, no invented
  numbers, necessity before bypasses at every critic level)
- вибір між варіантами розв'язав: P1 (definition and install tests), P6 (numbers only from the goals), P7 (a
  template file, no new script or hook), P8 (each rule from a scene or a real stage)
- не-цілі й обмеження: N1–N5 lie apart; nothing here touches the platform, a catalogue, parallelism,
  sandboxing or memory commands.

## Slices (the DAG)

- **S1 critics-goals-discipline** — delivers: `.claude/agents/critic-core.md` §0 (the quote rule),
  `.claude/agents/master-critic.md` (receives the journal; check 5 manual work; check 6 the mark; cause first;
  no numbers; POC asks to measure), `.claude/agents/feature-critic.md` and `.claude/agents/mvp-critic.md`
  (necessity, proportionality, order, one fix, the mark, each reads the journal itself; in `master-critic` the
  check-6 rule is an explicit exception to the lens's «A breach is BLOCKING»); a definition test
  `tests/test_critics_goals.py` ·
  contract out: master-critic's input names `journal` (`.engine/goals/interview.md`) · depends on: — ·
  **TRACER BULLET (build first)**
- **S2 architect-goals-discipline** — delivers: `.claude/commands/master-architect.md` (the four checks of
  «Читання цілей», the quote rule, cause before protection, numbers only from the goals, each stage shown
  separately, `docs/infra.md` pre-flight, new requirement → analyst, the journal into the critic's input),
  `.claude/agents/business-analyst.md` (`guardian` note), `templates/project/docs/infra.md` and its seed line,
  `docs/OWNER-GUIDE.md` (what the owner sees: stages shown one by one, `docs/infra.md`); a definition test
  `tests/test_architect_goals.py` and an install check of the seed; the test also asserts `critic-core`,
  `/master-architect` and the `guardian` name the same two sources of an owner decision (the time of the remark,
  the interview journal) · contract out: — · depends on: S1
- **Closing step (after S2, not a slice):** proposals 1756–1759 removed from `tasks/proposed/`, one report line
  each; the full test set and the golden set once.

One block (a small feature).

## Inter-slice contracts

- S1 → S2: master-critic's «What you receive» names the input key `journal` = the path
  `.engine/goals/interview.md`; S2's proposal loop passes `journal` in the `Task(agent="master-critic", …)`
  input with that same key.

## Integration exit criterion

S2's definition test reads both files: the key master-critic says it receives (`journal`) appears in
`/master-architect`'s `Task(agent="master-critic", input={…})` line. Plus A1–A12, the fast set after each
slice, the full set and the golden set once at the end.

## Deferred to later features

- The quality scenes of these rules (h, i, j again, and new ones) — task 502.

## Open items requiring human decision

None.

## Critic rounds
- Round 1: FEATURE_CRITIC_REVISE (the mark rule's «journal» did not reach feature-critic and mvp-critic) —
  fixed: each reads `.engine/goals/interview.md` itself (option a, P7); notes taken: mvp-critic's anchor (before
  question 1), the same two sources pinned across three files (S2's test), check 6 an explicit exception to the
  generic BLOCKING line (S1), the closing step for A12.
- Round 2: FEATURE_CRITIC_PASS. Notes taken: feature-critic's «A breach is BLOCKING» gets the same explicit
  exception (S1); S2's integration test parses the `input={…}` of the one master-critic Task line, not the whole
  file; the report names any golden entry that changes.
- Simplifier: architecture lens — no finding; requirements lens — one flag-only note (the journal bullet of §3 repeats §1), the owner's text, left in the owner's report.
