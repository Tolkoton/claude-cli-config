# Feature business-goals-focus — decomposition

Frame source: board task `tasks/doing/201-business-goals-focus.md` (the owner's text: «Рішення власника»
1–4, «Що зробити» §1–§6, «Чого не робити», «Готово, коли»). Every numbered item of the task is an owner
requirement; the critic checks how each is met, not whether. Unattended: the owner is not asked. Nothing in
this frame is PROVISIONAL — the acceptance criteria are the task's own list, and the autonomy grant is the
task itself (placed in the runner's queue with `Режим: конвеєр`).

## Goal

Level 0 stops being a flat list the architects read past. The goals document names its core (the goals
without which the product loses its sense, with the owner's own words under them) and marks everything that
is not the owner's words; the analyst keeps a journal of the conversation, has a fresh preseal check before
the owner approves, may answer an architect «the document does not require this», and guards the goals
during the architecture (mode `guardian`). The master-architect starts M1 with a separate stop «Читання
цілей», designs the core first and deepest, gives every design element a source, and converges with the
master-critic by a condition (oscillation, divergence) instead of a round number; the master-critic checks
coverage, necessity, proportionality and the consistency of arguments before it hunts for bypasses. What a
script can check — the core, the answer `NOT_REQUIRED`, the traceability matrix and the element tables — a
script checks (P1).

## Acceptance criteria (the owner's, from the task's «Готово, коли» and «Що зробити»)

- **A1** `goals.py`: a new text without a `## Ядро` section naming at least one standing goal G is refused
  by `seal`, `first-seal`, `proposal` and `amend`; a document already sealed without a core stays in force
  and `status` says it has no core (the next amendment must add one).
- **A2** `goals.py`: the answer `ANALYST_ANSWER: NOT_REQUIRED` is recognised, and `requests` shows it as an
  outcome of its own.
- **A3** `goals.py quote`: the mark `[не слова власника]` is part of the line's text — a quote is compared
  with it as it stands.
- **A4** A traceability check (a `goals.py` subcommand): refuses a standing line of the goals document
  without a row in `.engine/architecture/traceability.md`, a row naming a number that does not exist or is
  struck, an element of the tables of `domain-map.md` / `architecture-map.md` with no source outside
  `## Пропозиції`, and an element whose only source is a non-goal; it prints how many elements stand outside
  «Пропозиції».
- **A5** After an amendment, `domain-map.md` and `traceability.md` that cite a changed line land in
  `to-review.md`, as ADRs do.
- **A6** Definitions: `/master-architect` has no `round == 4` and has the stop «Читання цілей»; the agent
  `business-analyst` has three modes with exact output forms; the lens `goals-fit` of `master-critic` has
  the four new checks.
- **A7** Golden set identical except what is intended; the context budget (200 lines) not exceeded; the
  full test set green.
- **A8** Documents: `.claude/references/business-analysis.md`, `docs/OWNER-GUIDE.md`, the template
  `templates/project/.engine/goals.md` (core, mark, no «Затвердив власник»), `AGENTS.md` if it fits.
- **A9** The report says what changed for the owner in plain language, technical terms English.

## Build parameters

- Budgets/thresholds: none. The task forbids numeric limits on questions to the owner and on findings;
  loops stop on a condition (repeat, divergence); `BOARD_MAX_USD` guards an endless loop, as everywhere (P6).
- Policies: standard library only; ruff and `mypy --strict` clean on changed Python; every refusal names
  the file and the line it refuses; no new hook (the check is a script); existing sealed documents without
  a core are never broken.
- Tests: negative case first; a script is not verified until it has been seen to refuse.
  `bash tests/run_all.sh --fast` after every slice, the full set once at the end.
- Risk tolerance: spikes run without asking; a passing spike never interrupts.
- Autonomy: both slices built in DAG order; interrupts only on the critical set.
- Principles that bear on the slices (in words): a deterministic script decides what it can, the model's
  judgment is the fresh agent's (P1); numbers only as guards against looping, never as quality limits (P6);
  the simplest working shape, nothing «на виріст» (P7); protect against what happens in real work (P8).
- Not touched (the task's «Чого не робити»): `feature-critic`, `mvp-critic`, `/plan-slice`,
  `slice-builder`, `overseer`, `.claude/constitution.md`, `.claude/settings.json`. Nothing from the real
  project: every example is invented.

## Premises verified

- PR-goalsfocus-01 — the agent `business-analyst` can be started with a prompt other than a request path:
  no hook guards its start (`grep -ln subagent_type .claude/hooks/*.py` → only `overseer_verdict.py`,
  `overseer_stop.py`, `reader.py`, `testing.py`, which guard their own agents), 2026-10-18. Verified.
- PR-goalsfocus-02 — no script reads the header line «Затвердив власник» (`grep -rn` over `*.py`: only the
  fixture text in `tests/test_goals.py`), 2026-10-18. Verified.
- PR-goalsfocus-03 — `is_decision` is the gate of which files `check` (no arguments), `unreconciled`
  (and the owner's review, `board_review.py:643`) and `affected` (and through it `proposal`/`amend`'s review
  list) look at; but `affected` reads line numbers only through `cited()`, i.e. only inside a «Звірка з
  цілями» section (`goals.py` `cited`, `affected`), read 2026-10-18. So extending `is_decision` alone does
  NOT put the matrix in `to-review.md`: S1 also reads the matrix's citations from its rows (below).
  Verified (restated after feature-critic round 1).
- PR-goalsfocus-04 — every test or eval that seals a goals text today seals one without a core:
  `tests/test_goals.py`, `tests/test_refusal_branches.py` (goals block), `tests/test_board_runner.py`
  (`GOALS_TEXT`), `evals/scenarios/analyst/goals.md` (sealed by `run_analyst_evals.py`, checked by
  `tests/test_analyst_evals.py`), 2026-10-18. Each gains a core section — an intended difference (A7); the
  eval scene's text is otherwise unchanged.

## Out of scope (deliberately)

- `feature-critic`, `mvp-critic` and the feature level: if they need the same, a proposal in `proposed/`.
- The quality scenes of the new modes (task 501), and changing `evals/run_analyst_evals.py` scoring.
- A script that writes the interview journal: the analyst appends to it with its own tools.
- Checking that the words under «Ядро» really are the owner's — that is `preseal`'s judgment, not a script's.
- Rewriting this repository's own `.engine/goals.md` (the owner's document; it stays in force without a core).

## Звірка з цілями
- служить: G3 (бізнес — джерело правди: every element has a line of the goals as its source), G4
  (складність під контролем: an element without a source is a proposal, not design)
- вибір між варіантами розв'язав: P1 (what a script can check, a script checks), P6 (the loop stops on a
  condition, not a number), P7 (two slices, no new hook), P8 (the failures of a real first project)
- не-цілі й обмеження: N2–N5 lie apart; nothing here touches the catalogue, parallelism, sandboxing or
  manual memory commands.

## Slices (the DAG)

- **S1 goals-mechanics** — delivers: `goals.py` — the core (`## Ядро`) required of every new text and
  reported by `status`; the answer `NOT_REQUIRED` as an outcome; `is_decision` over `domain-map.md` and
  `traceability.md`; the traceability check subcommand over the matrix and the element tables; the template
  `templates/project/.engine/goals.md` (core section, the mark, no «Затвердив власник»). · contract out: the
  formats of `## Ядро`, of the matrix table and of the element tables, the subcommand's name and output —
  stable, consumed by S2's definitions; the fixtures of PR-goalsfocus-04 gain a core · depends on: — · **TRACER BULLET (build first)**
- **S2 goals-roles** — delivers: the definitions and documents — `.claude/agents/business-analyst.md` (modes
  `consult` + `NOT_REQUIRED`, `preseal`, `guardian`; its description rewritten: `consult` still starts with the request path and nothing else,
  `preseal` from `/business-analyst`, `guardian` from `/master-architect`), `.claude/commands/business-analyst.md` (journal, core,
  mark, non-goal, preseal step), `.claude/commands/master-architect.md` (the stop, M1 core first, element
  tables, guardian, narrow amendment, questions, no running ahead, premises, convergence),
  `.claude/agents/master-critic.md` (`goals-fit` four checks, the order, `domain` core first, premises
  against documentation), `.claude/references/business-analysis.md`, `docs/OWNER-GUIDE.md`, `AGENTS.md`; and a
  test of the definitions · contract out: — · depends on: S1

One block (a small feature).

## How the two new decisions cite the goals (feature-critic round 1)

- `traceability.md`: its citations ARE its rows — `goals.py` reads, for this one path, the first-cell line
  numbers of the matrix as what it cites (no «Звірка з цілями» section restating every number). An amendment
  of any line with a row lists the matrix in `to-review.md`.
- `domain-map.md`: carries a «Звірка з цілями» section like an ADR (the owner's text: «`domain-map.md` теж має
  розділ «Звірка з цілями»»); S2's `/master-architect` text requires it. Its element table's source column is
  checked by `trace`, not read as citations.
- Intended widening: `check` with no argument, `unreconciled` and the owner's review now also look at these
  two files. An old `domain-map.md` without the section is listed as not reconciled — nothing blocks it, the
  review shows it, exactly as an ADR without one is shown today.

## Inter-slice contracts

- S1 → S2: the formats S1's script reads, which S2's definitions tell the agents to write: the `## Ядро`
  section; the `NOT_REQUIRED` answer form; the matrix `.engine/architecture/traceability.md` and the element
  tables of `domain-map.md` / `architecture-map.md` with the section `## Пропозиції`; the subcommand that
  checks them. S2 copies them from S1's sealed contract and the built script, never invents its own.

## Integration exit criterion

A permanent test in S2's test of the definitions: the example matrix and element table that
`/master-architect` itself shows are extracted from the definition and run through S1's subcommand on a
synthetic project — exit 0 with the count printed; with one element's source removed, that element is
refused by name. So the text and the parser cannot drift apart unnoticed. Plus A1–A9.

## Deferred to later features

- The same necessity/coverage discipline for `feature-critic` and `mvp-critic` — why later: the owner kept
  them out of this task — revisit trigger: a proposal in `proposed/` after this task.
- The quality scenes of `preseal` and `guardian` — task 501.

## Open items requiring human decision

None.

## Critic rounds
- Round 1: FEATURE_CRITIC_REVISE (PR-goalsfocus-03 false for A5; core-less fixtures not named) — fixed: the
  section «How the two new decisions cite the goals», PR-03 restated, PR-04 added; notes 3 and 4 taken (the
  permanent integration test in S2; the agent's description rewritten in S2).
- Round 2: FEATURE_CRITIC_PASS. Notes taken: `templates/project/AGENTS.md` in S2; `check`, `unreconciled` and
  `affected` read the matrix through one function (S1); `.claude/references/hooks.md` names `trace` (S1).
- Simplifier: requirements lens — no finding; architecture lens — F-38e61790 (one count, not per map),
  applied to S1's contract.
