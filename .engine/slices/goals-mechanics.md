# Slice goals-mechanics — planning artifact

Driven by the feature `business-goals-focus` (`.engine/architecture/feature/business-goals-focus.md`,
slice S1, the tracer bullet). Frame supplied by the feature artifact and the owner's task
`tasks/doing/201-business-goals-focus.md` §1; the owner is not asked.

## Goal
What a script can check about level 0 and its use, `goals.py` checks: a new goals text has a core
(`## Ядро` naming a standing goal G) or is not sealed; an analyst may answer `NOT_REQUIRED` and the
answer is an outcome of its own; the domain map and the traceability matrix are decisions the review list
of an amendment reaches; and one subcommand checks that the traceability matrix covers every standing line
and that every design element has a source. Measurable: the feature's A1–A5 as tests of
`tests/test_goals.py`, each seen red against today's `goals.py` before it is green.

## Premise verified
- `is_decision` is the one gate of `check`, `unreconciled` and `affected` (and through `affected`, of
  `proposal` and `amend`): `.claude/hooks/goals.py` read 2026-10-18 — PR-goalsfocus-03.
- `board_review.py` maps every outcome of `goals.requests` through `REQUEST_ENDS[r.outcome]`
  (`.claude/unattended/board_review.py:621`), so a new outcome without a key there raises `KeyError` in the
  owner's review — read 2026-10-18; the slice adds the key.
- Every test or eval that seals a goals text today seals one WITHOUT a core: `tests/test_goals.py`
  (`DOCUMENT`, `AMENDED`, the first-seal block), `tests/test_refusal_branches.py` (goals block),
  `tests/test_board_runner.py` (`GOALS_TEXT`), `evals/scenarios/analyst/goals.md` (sealed by
  `run_analyst_evals.py` `sandbox`, checked by `tests/test_analyst_evals.py`) — `grep -rln goals.md
  tests evals | xargs grep -l seal`, 2026-10-18. They gain a core; see «Changed expectations».
- No script reads the template's «Затвердив власник» (PR-goalsfocus-02).
- No external system: untested — common knowledge (text parsing, the standard library).

## Out of scope (deliberately)
- The definitions and documents that tell agents to write these formats — slice S2.
- Checking that the words under «Ядро» are really the owner's, that a mark `[не слова власника]` stands
  where it should, or what the «Як читаю» column says — judgment, the fresh agent's (S2's `preseal`,
  `guardian`).
- Parsing the mark: it is text like any other (A3 is a test that nothing strips it).
- A script for the interview journal `.engine/goals/interview.md`: the analyst appends to it itself.
- The owner's review showing «no core» — `status` says it (the owner's text asks no more).
- Checking the matrix's «Елементи дизайну» column against the element tables, or the rows' «Статус».
- This repository's own `.engine/goals.md` is not edited: sealed without a core, it stays in force.

## Seam (contract)
All in `.claude/hooks/goals.py`; one key in `.claude/unattended/board_review.py`; the template.

- **The core.** `core_error(text: str) -> str` — `""`, or one English sentence why `text` has no core:
  - the section is a heading line `## Ядро` (or `## Core`), any trailing spaces; its body runs to the next
    line matching `HEADING` (`^#{1,4}\s`) or the end; HTML comments (`<!-- … -->`, also across lines) are
    removed from the body before reading it;
  - no such section → `no «## Ядро» section: the owner names the goals without which the product loses its
    sense`;
  - the goal numbers of the body are `G\d+` tokens by the `ID` rule (not part of a longer word); a cited G
    that is not a line of the document → `«Ядро» cites G9, which is not a line of the goals document`; a
    struck G → `«Ядро» cites G2, which is struck out`; (the first such, in body order, is the sentence)
  - no standing G cited at all → `«Ядро» names no standing goal G`.
  - Other kinds (P1, N2…) in the body are text; neither counted nor refused.
  - `items(text)` raising `ValueError` is not caught here: every caller already calls `items` first.
- **Where the core is required — every NEW text, nowhere else:**
  - `amendment(old, new)` appends `core_error(new)` to its errors when non-empty — so `proposal` (exit 3,
    `REFUSED: <sentence>`) and `amend` (exit 1, `amend: …`, nothing written) refuse a new text without one;
  - `cmd_seal`: after today's refusals, right before writing the seal (states `unsealed` attended, and
    `changed` with `--owner-approved` outside a session) → `REFUSED: <sentence>` on stderr, exit 3, no seal
    written; a document that is `sealed` returns as today, whatever its core;
  - `first_seal`: after the numbered-line check and the `sealed` early return → `first-seal: <sentence>`,
    exit 1, no seal (what `owner_action.py` turns into the refusal it reports today for exit 1);
  - `check`, `quote`, `requests`, `unreconciled`, `affected`, `status`'s exit code: unchanged — a document
    sealed without a core stays in force.
- **`status`**: prints today's line; then, when the document exists, has numbered lines and `core_error` is
  non-empty, a second stdout line: `no core: <sentence> — the next amendment must add it` (for `sealed`)
  or `no core: <sentence> — it is not sealed without one` (for `unsealed` / `changed`). Exit code as today.
  A document whose `items` raises: today's behaviour (status reads no items), no second line.
- **`NOT_REQUIRED`.** `ANSWER` matches `QUOTE|OWNER_DECISION|NOT_REQUIRED`. `request_outcome`: the last
  answer `NOT_REQUIRED` → `Request(path, reason, "not-required", <the value of the `Lines:` field read from
  the text AFTER that last `ANALYST_ANSWER:` line, as the quote path reads its fields, or "">)` — a test with
  an earlier answer carrying another `Lines:` pins it. `requests` prints it like the others (`…\tnot-required\t<lines>`). `cmd_quote` on such a
  request: `REFUSED: the analyst answers NOT_REQUIRED: there is no quote to check` on stderr, exit 3 —
  without today's tail «it goes to the owner» (a NOT_REQUIRED does not go to the owner).
  `board_review.REQUEST_ENDS["not-required"] = "документ цього не вимагає (NOT_REQUIRED) — не будується, вас не турбували"`.
- **`is_decision`** also true for exactly `.engine/architecture/domain-map.md` and
  `.engine/architecture/traceability.md`.
- **Citations of the matrix.** `cited(text)` is unchanged; a new `citations(path, text) -> tuple[bool,
  list[str]]` returns, for `TRACE_REL`, `(the matrix has a row, the first-cell numbers of its rows in order,
  without repeats; a row whose first cell is not a line number gives nothing)`, and `cited(text)` for every other path. `citation_errors` (and through it `unreconciled` and
  `cmd_check`) and `affected` all read through `citations` (so `citation_errors` takes the path) — one
  function, so `check`, `unreconciled` and the review list read the matrix's rows alike. `cmd_check`'s `ok:`
  line (`cites …`) also reads through `citations(rel, …)`, so the matrix's ok line lists its rows' numbers. For the matrix, «no section» reads `the matrix has no
  row`.
- **The matrix** — `TRACE_REL = ".engine/architecture/traceability.md"`. Its table is the first block of
  consecutive lines starting with `|` whose first row's first cell (stripped) is `Рядок` (or `Line`); the
  second row of the block is the `|---|` rule; every later row of the block is a row. A cell is the text
  between two `|`, stripped. A row's first cell is a line number when it matches `^[GPNCDQ]\d+$` exactly.
- **The element tables** — in `.engine/architecture/domain-map.md` and `architecture-map.md` (`MAPS`): every
  block of consecutive `|` lines whose first row's first cell is `Елемент` (or `Element`); the column whose
  header cell is `Джерело` (or `Source`) is the source. A row's section is the nearest heading line above it
  that starts with exactly `## ` (level 2); it is a PROPOSAL when that heading's text is `Пропозиції` (or
  `Proposals`). Sources in a source cell: the `ID` tokens, and the paths matching
  `docs/adr/[^\s|)\]]+\.md`.
- **`trace_errors(show: Show, lines: dict[str, Item], exists: Callable[[str], bool]) -> tuple[list[str],
  int]`** — (the errors, the number of element rows outside «Пропозиції» in both maps together). Errors, each one sentence naming the file:
  - the matrix absent or with no table: `.engine/architecture/traceability.md: no matrix (a table whose
    first column is «Рядок»)`;
  - a row whose first cell is not a line number: `…traceability.md: a row names no line: «<cell>»`;
  - a number with two rows: `…: G1 has two rows`; a number not in the document: `…: G9 is not a line of
    the goals document`; a struck number: `…: G2 is struck out of the goals document`;
  - a standing line (any kind G P N C D Q, not struck) with no row: `…: G3 has no row`;
  - a map that does not exist is not checked (before M1 writes it there is nothing to check); a map that
    exists with no element table: `<map>: no element table (a table whose first column is
    «Елемент»)`; an element table with no source column: `<map>: the element table has no «Джерело» column`;
  - outside «Пропозиції», for each row (`«<element>»` = its first cell): an `ID` token in the source cell that
    is not a line, or is struck → the same two sentences as the matrix's, prefixed by `<map>: «<element>»`;
    an ADR path that is not a file → `<map>: «<element>»: <path> is not a file`; and when no VALID source is
    left — a standing G, P, C or D, or an ADR path that is a file — `<map>: «<element>» has no source (a G,
    P, C or D line, or an owner's decision in docs/adr/): remove it or move it to «## Пропозиції»`, or, when
    the cell named a standing N, `<map>: «<element>»: its only source is the non-goal N1 — a non-goal is a
    boundary, not a source: remove it or move it to «## Пропозиції»`. (Q is not a source; P is.)
  - rows in «Пропозиції» are neither refused nor counted.
- **`goals.py trace`** (`cmd_trace(root) -> int`): the document must be `sealed`, else today's `check`
  behaviour (the state line, `STATE_EXIT`); `items` raising → `REFUSED: …`, exit 3. Then every error as
  `REFUSED: <sentence>` on stderr, and ALWAYS one stdout line `elements outside «Пропозиції»: <total>`; exit 3 when there is an error, 0 otherwise. The help line in the module docstring names it.
- **The template** `templates/project/.engine/goals.md`: the header line is `Версія: 0` (no «Затвердив
  власник»); the header comment says the approval state is `goals.py status`'s, explains the core and the
  one mark `[не слова власника]` (right after words the owner did not say: the analyst's wording, a reason
  «бо …», a sign «видно з того», an example, an option the owner chose from the analyst's; approval does
  not remove it); a section `## Ядро` right after «Для кого і навіщо», its body a comment with an invented
  example (`- G1 — «<дослівні слова власника>»`). The seed is installed once (`ownership.txt` `seed=`):
  projects that have the file keep theirs.
- **`.claude/references/hooks.md`**: the row of `goals.py` names `trace` among its subcommands.
- Dependencies (injected): `Show` (the text of a path), `exists` (is a path a file) for `trace_errors`;
  `core_error`, `citations` are pure over text.
- Does NOT do: parse the mark; read the interview journal; check the matrix's other columns; refuse a
  sealed document without a core; touch `feature-critic`, `mvp-critic`, any definition.

## Decisions (with WHY)
- Q1: The core is required inside `amendment()` plus the two seal paths — chosen because `amendment` is the
  one judge of every new text that `proposal` and `amend` share, so the rule cannot be in one and missing
  from the other. Rejected: a separate check in `cmd_proposal` and `amend` — two copies to keep equal.
- Q2: A sealed document without a core stays `sealed` with exit 0, and `status` says it in a second line —
  chosen because the owner wrote «Чинні документи цілей без ядра не ламати»; every gate keyed on `status`'s
  exit (`goals.py status` in `/master-architect`) keeps working. Rejected: a new state `sealed-no-core` —
  every consumer of `state()` (board_review, mode, tests) would need a branch for it.
- Q3: Owner decisions as sources are ADR paths under `docs/adr/` that exist — chosen because the
  master-architect already writes an ADR per owner-ratified decision, and a file's existence is a fact a
  script checks. Rejected: a new register of owner decisions with its own numbers (`O1…`) — a second record
  kind, a new format; free text «рішення власника …» — unverifiable.
- Q4: A source cell that also holds an N plus a standing G is valid — the owner's text says «не-ціль N
  САМА ПО СОБІ джерелом бути не може»; only an element with no valid source is refused, with the N named.
- Q5: The matrix's citations are its rows' first cells (not a «Звірка з цілями» section) — chosen because
  the matrix IS the citation of every line; a second section restating every number would rot. The matrix is
  a decision (`is_decision`) so an amendment of any line lists it for review.
- Q6: One subcommand `trace` over the matrix and both maps — chosen because the owner asked for one check
  that prints the count (the master-architect reads that count each critic round). Rejected: two
  subcommands — one call is what the architect needs after a round.
- Q7: Tables are found by the first header cell (`Рядок`, `Елемент`) — chosen because it is the most stable
  mark an architect writes and reads; a heading-based rule would break when the architect renames a heading.

## Hardest seams (test-confidence points)
- **Seam 1: a core in a comment.** The template's example `<!-- - G1 — «…» -->` inside `## Ядро` must not
  count: a test seals the template filled with lines but the core only in the comment → refused. Rules out
  reading IDs without removing comments.
- **Seam 2: old document stays in force.** A document sealed by today's `goals.py` (no core) → `status` exit
  0 with the second line, `check` and `quote` as before; then a proposal without a core is refused and with
  one is accepted. Rules out a rule that breaks every installed project.
- **Seam 3: the N-only element.** `| Детектор | … | N1 |` outside «Пропозиції» → refused naming N1; the same
  row with `N1, G2` → fine; the same row under `## Пропозиції` → not refused, and the printed count does not include it. Rules out a check
  that only looks for «some ID».
- **Seam 4: struck and missing lines in the matrix.** A struck G with no row is fine; a struck G WITH a row
  is refused; a standing Q with no row is refused (every kind is covered). Rules out checking G only.
- **Seam 5: the review list.** After `amend` changes P1, a `domain-map.md` that cites P1 in its «Звірка з
  цілями» and a `traceability.md` with a P1 row are both in `to-review.md`; a matrix without a P1 row is not.
- **Seam 6: `REQUEST_ENDS`.** The owner's review rendered with a NOT_REQUIRED request does not raise and
  shows the Ukrainian sentence.

## Invariants (rules that hold for every input in the stated domain)
- **I1** — No new text is sealed or accepted as an amendment without a core naming a standing goal G.
  - Domain: every text given to `seal` (unsealed or changed-with-owner-flag), `first-seal`, `proposal`, `amend`.
  - Source: the owner's task §1 «Новий текст без ядра … відхиляють `seal`, `first-seal`, `proposal` і `amend`».
  - Broken by: a check added to `proposal` only; reading IDs inside HTML comments; accepting a struck G.
- **I2** — A document sealed before this slice keeps its state and exit codes in every command, as far as
  the core is concerned (a missing core never changes a state or an exit code; the intended widening of
  `check` to `domain-map.md`, «Changed expectations», is not about the core).
  - Domain: any sealed document without a «## Ядро» section.
  - Source: the owner's task, «Чинні документи цілей без ядра не ламати».
  - Broken by: requiring the core in `state()`, `check` or `status`'s exit.
- **I3** — An element outside «Пропозиції» passes `trace` only with at least one valid source, and a
  non-goal is never one.
  - Domain: every row of every element table of both maps.
  - Source: the owner's task §1, the matrix check, bullets 2 and 3.
  - Broken by: accepting any ID token; accepting N; refusing rows in «Пропозиції».
- **I4** — `trace` prints the count of elements outside «Пропозиції» whether or not it refuses.
  - Domain: every run of `trace` on a sealed document.
  - Source: the owner's task §1, bullet 4 («скрипт друкує, скільки елементів…»).
  - Broken by: printing the count only on success.

## Exit criterion
`tests/test_goals.py` gains two lists of tests.

(a) **RED-first** — each seen red against the base commit's `goals.py` before it is green: the four
refusals of a core-less new text (`seal`, `first-seal` through `owner_action.py seal-goals`, `proposal`,
`amend-goals`) and the core-in-a-comment refusal (Seam 1); `status`'s «no core» second line on an old sealed
document (Seam 2, the line only); `NOT_REQUIRED` in `requests` and refused by `quote` without «goes to the
owner»; `trace`'s refusals (Seams 3, 4, a row naming nothing, a map without an element table) with the count
printed, and its pass; Seam 5's review list; the NOT_REQUIRED sentence in the owner's review (Seam 6, in
`tests/test_board_review.py` or the suite that renders the goals section).

(b) **Characterization** — green on the base commit by construction and kept green, written as such and
never claimed red: A3's quote pair (accepted verbatim with `[не слова власника]`, refused with the mark
dropped) and I2's old document in force (`status` exit 0, `check` and `quote` as before).

`bash tests/run_all.sh --fast` green, AND, outside the fast subset, `python3 tests/test_board_review.py`
(Seam 6), `python3 tests/test_refusal_branches.py` and `python3 tests/test_board_runner.py` (their changed
fixtures) each green; `uvx --offline ruff check` and `uvx --offline mypy --strict` clean on
`goals.py` and `board_review.py`. Smoke: `goals.py trace` in a temporary synthetic project (a sealed
document with a core, a matrix, a domain map with one element per kind of source) prints the count and
exits 0; with one source removed it refuses that element.

### Changed expectations (fixtures that seal a new text gain a core)
`tests/test_goals.py` `DOCUMENT`/`AMENDED`, `tests/test_refusal_branches.py` goals block,
`tests/test_board_runner.py` `GOALS_TEXT`, `evals/scenarios/analyst/goals.md`: each gains a `## Ядро`
section naming its G1. The test of `tests/test_goals.py` that writes the template's header line is not
changed (it is a fixture's own text).

`evals/scenarios/analyst/domain-map.md` gains a «Звірка з цілями» section (it becomes a decision; without
the section `check` in that eval's sandbox would refuse it) — an input of the paid analyst eval changes
with `goals.md`'s core; a later comparison with a stored result of that eval names this slice.

Intended, outside I2: a project's existing `domain-map.md` without «Звірка з цілями» is now listed by
`check` with no arguments (its exit goes from 0 to 3), by `unreconciled` and in the owner's review —
the owner's text asks for the section; nothing blocks on it (no hook or gate runs `check`).

## Deferred to later slices
- The definitions that make agents write the core, the matrix and the tables — S2.
- «No core» in the owner's review — revisit trigger: the owner asks for it.

## Open items requiring human decision
None.

## Critic notes (non-blocking)
- cold reader 2: CRITIC_PASS. Notes taken: non-number rows give no citation; an absent map is not checked;
  the eval's domain-map fixture gains the section. Noted: for a matrix whose rows name nothing, `check`'s
  sentence speaks of «Звірка з цілями» — cosmetic, `trace` names the rows.
- slice-planner-critic round 1: REVISE (fabricated RED: A3 and I2 tests are green on base) — the Exit
  criterion now splits RED-first and characterization; the widening of `check` is stated under «Changed
  expectations»; the budget names its private helpers and is 160 lines.
- cold reader: REVISE (false-DONE: Seam 6 and two changed fixtures live outside `--fast`) — the Exit criterion
  names the three suites; notes taken: `cmd_check`'s ok line through `citations`, I2 narrowed to the core,
  `Lines:` read after the last answer.
- feature-critic round 2: `cmd_check` once exceeded the per-function complexity limit — `trace` is its own
  function `cmd_trace`, not more branches in `cmd_check`.

## Complexity budget
base_commit: 86863ddf85c58aef441b8245fdb20ddf0d0d2d4f
max_new_files: 0
max_net_new_lines: 160
max_new_public_symbols: 6
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 13
max_nesting_depth: 3
justification: the public symbols are core_error, citations, trace_errors, cmd_trace, TRACE_REL, MAPS; table parsing lives in private helpers (`_table`, `_element_rows`, `_source_errors`) so trace_errors stays under the cyclomatic limit; 160 lines for two table formats with nine refusal sentences (slice-planner-critic note 3)
