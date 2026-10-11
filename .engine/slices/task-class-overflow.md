# Slice task-class-overflow — planning artifact

Driven by the feature `task-numbers-by-class` (`.engine/architecture/feature/task-numbers-by-class.md`,
slice S1, the tracer bullet). Frame supplied by the feature artifact; the owner is not asked.

## Goal
Every place that gives a task its number takes it from one function of class arithmetic, with the
class fixed at that place: an open item 7, a rule question 8, a gate question 9, a task the runner
places itself 4, the follow-up of an urgent fix 1. A number is class × 100 + ordinal; a class that
has used c01…c99 continues in the identifier + 10. Measurable: on a board whose largest class-7
number is 783 the next open items are 784…799, then 1701 — never 800 (the feature's A1); the same
for 8 and 9.

## Premise verified
- PR-numbers-01 — the five sites are the only ones that issue a number: `grep -rn
  "ITEM_FIRST\|RULE_FIRST\|GATE_FIRST\|FIRST_RESERVED\|_own_number"` outside `tests/` names
  `.claude/unattended/board.py` and `.claude/hooks/hotfix.py:61,211` only among tracked files; every other creator
  (`lesson_queue.py`, `gate.py`, `overseer_verdict.py`, `testing.py`) calls `board.open_item`,
  `rule_question` or `gate_question` — 2026-10-11.
- Four-digit names are read everywhere a name is read: `TASK_NAME`/`DONE_NAME` are `\d{3,}`,
  `DEPENDS` reads `\d+`, the runner's globs are `[0-9]*` (`board.py:218-220`,
  `board-runner.sh` `publish_gate_questions`) — 2026-10-11.
- No external system: untested — common knowledge (integer arithmetic, the standard library).
- PR-numbers-04 (one function serves every site) is what this slice proves.

## Out of scope (deliberately)
- `tasks/CLASSES.md`, the `Клас:` line, a number for an inbox file — slice S2.
- The order of the queue — S3. `renumber` and `check` over the whole board — S4.
- Renaming any existing task: 600, 700, 800, 900 and the open items 801–843 stay as they are.
- Documents (`tasks/README.md`, the templates) — the feature's closing step.

## Seam (contract)
- Signature, new module `.claude/unattended/task_classes.py`:
  - `UNCLASSED, OWN, OPEN_ITEMS, RULES, GATES = 1, 4, 7, 8, 9`
  - `class_of(number: int) -> int`
  - `next_number(taken: Iterable[int], klass: int) -> int`
  - in `board.py`: `Board.taken(self) -> set[int]`
- Returns: `class_of` — `number // 100 % 10`, always 0…9. `next_number` — with m the largest member
  of `taken` whose `class_of` is `klass`: `klass * 100 + 1` when there is none; `m + 1` when
  `m % 100 < 99`; otherwise `(m // 100 + 10) * 100 + 1`. `Board.taken` — every number of the four
  columns (the union of `Board.numbers`).
- Errors: `next_number` raises `ValueError` naming the class when `klass` is not 1…9 (class 0 is
  what was there before classes and is never issued). Nothing else fails; `taken` may be empty.
- Dependencies (injected): `taken` — the caller reads the board; the module opens no file. The
  numbers are non-negative: they are read from task names (`\d{3,}`).
- How the module is found: `board.py` puts ITS OWN directory on `sys.path` (beside the `hooks/`
  insert it has at line 212) before `import task_classes`, because `board.py` is also loaded by
  path with no path set up — `tests/test_owner_terms.py:60` (in the fast subset),
  `tests/test_hotfix.py:57`, `evals/run_audit_scenarios.py` `board_module()` (the audit runner).
  `hotfix.py` inserts `../unattended` built from `__file__`, as `gate.py` and `maintain.py` do, and
  calls `task_classes.next_number` through the module (its own function of that name stays). No
  by-path loader in `tests/` or `evals/` gets a path insert to make the import work. A third kind
  of consumer copies `board.py` file by file into a synthetic engine: the copy list of
  `tests/test_release.py` (`COPIED`, line 30) gains `.claude/unattended/task_classes.py`, as it
  gained `mode.py` and `journal.py` when `board.py` began to import those.
- Who collects `taken`: `Board.taken` for the four sites of `board.py` (`_own_number` globbed `*`
  in every column until now; `Board.numbers` reads `*.md` task files and the folders of `done/` —
  the same numbers on a well-formed board (checked on this one: no number is seen by one reader
  and not the other). What the narrower reader no longer counts is a thing that is not a task — a
  loose `NNN-x.md` file in `done/`, a directory in `todo/` — and one reader for all four sites is
  worth more than counting those); `hotfix.py` keeps its own glob `tasks/*/*`.
- Callers after the slice: `open_item` → `next_number(board.taken(), OPEN_ITEMS)`; `rule_question`
  → `RULES`; `gate_question` → `GATES`; `_own_number` → `OWN`; `hotfix.py next_number(tasks)` →
  `UNCLASSED` over the numbers it already collects. `ITEM_FIRST`, `RULE_FIRST`, `GATE_FIRST`,
  `FIRST_RESERVED` and `hotfix.py`'s `FIRST_ORDINARY, FIRST_RESERVED` go: no reader is left, and
  every docstring that states the old rule is corrected with them (`board.py:138` «a gate question
  is numbered from 900», `board.py:977` `_own_number`, `hotfix.py:209` `next_number`, and the
  name shapes `9NN-gate-`, `8NN-rule-proposal`, `7NN-open-item` at `board.py:73, 96, 164`).
- Does NOT do: read `CLASSES.md` or a task's text; fill a gap under the largest number; touch the
  text, the column or the file-name pattern of what a site writes.

## Decisions (with WHY)
- Q1: a module of its own, not more lines in `board.py` — chosen because `hotfix.py` needs the
  arithmetic and has its own copy of the rule today; a pure 30-line module both can import ends the
  copy and can be tested alone. Rejected: functions inside `board.py` with `hotfix.py` importing `board` (other
  hooks do) — it works, and costs nothing new in files, but it puts the whole board (and its two
  sibling imports) behind one number for `hotfix.py`, and behind every test that wants the
  function alone; the module is also what the feature's inter-slice contract names. Rejected:
  leaving `hotfix.py`'s
  copy and fixing it in place — two rules for one number is the defect being removed.
- Q2: the successor of the largest, not the first free number — chosen because it is the owner's
  wording («найбільший порядковий номер у класі в усіх колонках, `done/` включно, плюс один») and a
  gap is a number some report or `Залежить від:` may still name. Rejected: first free (today's rule
  for 7, 8, 9) — it re-issues the number of a task that was deleted or renumbered away.
- Q3: ordinal 00 is never issued; the first of a class is c01 — chosen because the owner's examples
  are «101 — перша задача класу 1», «перша задача класу 3 — 301», «1701–1799». Consequence, wanted
  and visible: on an empty board the first open item is 701, the first rule question 801, the first
  gate question 901 (were 700, 800, 900). Rejected: keep c00 as the first — contradicts 301.
- Q4: `class_of` is `// 100 % 10`, with no table — chosen because the continuation rule (+10) makes
  the last digit of the identifier the class for every number, so nothing has to be configured and
  nothing can disagree with the number. Rejected: a lookup of continuations in `CLASSES.md` — a
  second source for what the number already says (feature K1).
- Q5: `ValueError` for a class outside 1…9, not a silent class 1 — chosen because every caller in
  this slice passes a constant, so the error can only be a programming mistake, and S2's refusal of
  an unknown `Клас:` line needs the function to refuse rather than guess.
- Q6: `_own_number` keeps its name and becomes one line; the runner's own tasks keep the `:03d`
  file-name format — chosen to leave `maintain_task` and `cleanup_task` untouched.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: the boundary c99 → (c+10)01, and a continuation's own boundary** — test approach:
  example tests on 799 → 1701, 1799 → 2701, 9999 → 10901, on a gap under the largest (701 and 703
  → 704, never 702), and on a board that holds 799 AND 801–843 (today's board): the open item is
  1701, the rule question 844. Rules out the anti-pattern of testing only "max + 1" inside one
  hundred.
- **Seam 2: the real sites, not the function** — test approach: the real `board.py open-item` CLI
  and the real `rule_question` / `gate_question` / `maintain_task` / `hotfix.py debt` on synthetic
  boards seeded with file NAMES; the assertion is the name of the file written and that no file
  appears in a foreign hundred. Rules out a green unit test over a function no site calls. "Counting
  one column only" is a defect of `Board.taken`, not of the function: the existing checks that pin
  a number in `done/` for `open_item` and `gate_question` (`tests/test_board.py`, the `done/` seeds
  near lines 535–541 and 783) are the ones that catch it and must stay as strict as they are.
- **Seam 3: the suites that pin today's first numbers** (`700-`, `800-`, `900-`, `001-maintain`…:
  `test_board`, `test_board_review`, `test_board_runner`, `test_gate_allows`, `test_lesson_queue`,
  `test_cleanup`, `test_maintain`, `test_hotfix`, `test_owner_perimeter`, `test_overseer_fresh`) —
  test approach: each changed expectation is a NAME only and is changed to the number the contract
  derives (701, 801, 901, 401, 101, and the numbers after them); an expectation about text, column,
  count or order that turns red is a finding, not something to edit. The full list of changed lines
  goes into the PROGRESS entry. Nine of the ten are outside `--fast`, so each is run by itself.
  A seed that only exists to make a number taken moves with the names it guards: in
  `tests/test_board.py` the gate case's `done/902-old` (line 782) becomes `done/903-old` and its
  expectation `904-`, or the check no longer shows that `done/` is counted.
- **Seam 4: a sibling import in files that are loaded by path** — test approach:
  `tests/test_hotfix.py` runs the engine's own `hotfix.py` against a synthetic project, so a path
  built from the project root or the cwd fails there; `board.py` loaded with
  `importlib.util.spec_from_file_location` from a foreign cwd must import cleanly — a case of the
  contract-test file, beside the by-path loads `test_owner_terms` and `test_hotfix` already do.

## Invariants (rules that hold for every input in the stated domain)
- **I1** — the number given belongs to the class asked for: `class_of(next_number(taken, k)) == k`.
  - Domain: every finite set `taken` of non-negative integers (empty included), every k in 1…9.
  - Source: task 401 item 3 («Номер ніколи не заходить у чужий клас»); the feature's A1.
  - Broken by: "first free from k00 with no upper bound" (today's rule: 799 → 800).
- **I2** — the number given is new and above every number of its class: it is not in `taken` and is
  greater than every member of `taken` whose `class_of` is k.
  - Domain: as I1.
  - Source: task 401 item 2 («найбільший порядковий номер у класі в усіх колонках … плюс один»).
  - Broken by: filling a gap (701 and 703 taken → 702).
- **I3** — the ordinal 00 is never given: `next_number(taken, k) % 100 != 0`.
  - Domain: as I1.
  - Source: design 741 §3 («1701–1799»), task 401 («перша задача класу 3 — 301»).
  - Broken by: `(m // 100 + 10) * 100` at the boundary; `k * 100` on an empty class.
- **I4** — other classes do not matter: adding to `taken` any numbers whose `class_of` is not k
  leaves `next_number(taken, k)` unchanged.
  - Domain: as I1, the added numbers any non-negative integers of other classes.
  - Source: this contract's «Seam» (the largest member of `taken` whose `class_of` is `klass`).
  - Broken by: `max(taken) + 1`; today's `_own_number` ("the largest under 700").

## Exit criterion
- The contract-test file `tests/test_task_classes.py` (a suite of its own, added as the last line
  of `tests/fast-suites.txt`, so `--fast` runs it): the pure function — `test_I1_…`…`test_I4_…`,
  799 → 1701, 1799 → 2701, 9999 → 10901, 701 and 703 → 704, `ValueError` for classes 0 and 10 —
  and `board.py` loaded by path importing cleanly in a FRESH interpreter started from a temporary
  cwd (`python3 -c …`; in-process the suite's own import of the module would hide a missing path
  insert). The suite builds the environment of what it runs with `tests/hook_env.py`
  (`tests/test_hook_env.py` refuses a new suite that does not).
- The sites, each through its real entry point on a synthetic board seeded with file NAMES, the
  assertion being the name of the file written. The cases of `board.py`'s four sites live in the
  same contract-test file, `tests/test_task_classes.py`; the hotfix follow-up is the existing case
  of `tests/test_hotfix.py`, whose seed gains one class-1 number outside `todo/` (`done/103-x/`) so
  that the expectation shows the site reads the board:
  - the real `board.py open-item` CLI, seventeen calls with seventeen different titles and no
    `--key`, on a board whose `todo/` holds
    `783-open-item-x.md` and nothing in 784–799: the names are 784…799, then `1701-…`; no file
    appears in 800–899;
  - `rule_question` on a board with `899-…` → `1801-rule-proposal-…`; `gate_question` with
    `999-…` → `1901-gate-escalation-…`;
  - "today's board" (799 and 801–843 present, 901 the largest of class 9): open item `1701-…`,
    rule question `844-…`, gate question `902-…`;
  - the runner's own task (`cleanup-task` and `maintain-task`, each): no class-4 number on the
    board → `401-…`; `done/401-x/` and `blocked/603-y.md` present → `402-…` (a `done/` number
    counts, a foreign class does not — today's rule answers 604 here). The foreign task is seeded
    in `blocked/`, not `todo/`: `cleanup_task` places nothing while a task can be taken, and that
    rule is not this slice's. Preconditions of the two commands, unchanged: the synthetic root
    holds `.claude/commands/maintain.md` and `.claude/hooks/simplifier.py`, and the 401 and 402
    cases are separate boards (a second task of the kind is not placed while one is open);
  - `hotfix.py debt` on its suite's seed plus `done/103-x/` → `104-hotfix-followup-…` (with no
    class-1 number a site that read no board at all would also answer 101).
- The smoke, a one-off against a copy (not a suite case — once this slice is live the real board
  moves): the real CLI `python3 .claude/unattended/board.py --root <copy> open-item --to todo …`
  on a temporary copy of THIS repository's `tasks/` file names. With M the largest number of the
  copy whose `number // 100 % 10` is 7: the printed name's number is above M, of class 7, its
  ordinal is not 00, and the copy gains no file in 800–899. The literal output and M go into the
  PROGRESS entry.
- `bash tests/run_all.sh` — the FULL set — green at the end of this slice. Not the fast subset plus
  a list of suites: the slice changes what `board.py` imports, and the suites that load, copy or
  reach `board.py` through another hook cannot be listed reliably (two attempts at a list each
  missed one: `test_release` copies the file alone; `test_lesson_queue` and `test_overseer_fresh`
  name neither file). The board's rule "the full set once, at the end of the task" is kept for the
  later slices; this one, the tracer every later slice stands on, pays for a full run of its own.
  A red check that is a cascade of a name pin inside one compound check is listed as such, line by
  line, in the PROGRESS entry.
- `uvx --offline ruff check` and `uvx --offline mypy --strict` (neither tool is on PATH here), each
  as ONE invocation naming `.claude/unattended/task_classes.py`, `.claude/unattended/board.py` and
  `.claude/hooks/hotfix.py` together (alone, `hotfix.py` cannot resolve the cross-directory
  import), are clean; ruff also on the changed suites.
- Over tracked files, `git grep -n "ITEM_FIRST\|RULE_FIRST\|GATE_FIRST\|FIRST_RESERVED\|FIRST_ORDINARY"
  -- .claude engine.py evals tests` finds nothing (an old audit's copy of `board.py` under the
  git-ignored `.claude/state/` still holds the names and is nobody's to edit).

## Complexity budget
base_commit: edf7569a1e84af9f5c3ec651aeeb79f942ca365a
max_new_files: 1
max_net_new_lines: 45
max_new_public_symbols: 8
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 13
max_nesting_depth: 3
justification: one new file, .claude/unattended/task_classes.py (the module the feature's inter-slice contract names; board.py and hotfix.py both import it). Public names are the ones the Seam lists - class_of, next_number, UNCLASSED, OWN, OPEN_ITEMS, RULES, GATES - and Board.taken. The sites lose their own loops and constants, so the net is the module itself.

## Deferred to later slices
- The table of classes and the `Клас:` line — why later: the fixed classes need no table —
  revisit trigger: slice S2 `numbers-class-table`.
- The queue's order with 17xx numbers (they sort after 9xx until then) — why later: S3 owns the
  order — revisit trigger: slice S3 `numbers-queue-order`.

## Open items requiring human decision (if any)
None.

## Critic notes (non-blocking)
- This contract was first written and sealed as `numbers-class-overflow` with a budget section the
  validator refused (a required line was missing); the seal is not the agent's to lift, so the
  same text with the two missing budget lines is sealed under this slug. The old file is removed.
- Phase 4 took four critic rounds, each a new factual defect of the criterion (a literal that the
  slice's own success makes stale; a grep over git-ignored state; a case `cleanup-task` cannot
  show; a suite outside both lists that copies `board.py` alone). Each was fixed as the critic
  asked; no fork was left to rule on. Logged AUTONOMOUS in `.engine/overseer/escalations.md`.
- Phase 5: the 17xx-after-9xx order stays until S3; S2 and S3 are registered only in the feature
  artifact and task 401 — the PROGRESS entry of this slice says so. The open items 801–843 read as
  class 8 by their number and will queue with rule questions in S3 (accepted by the feature).
- Phase 3: the invariants alone do not pin "successor" (an implementation that always jumps to the
  next continuation satisfies I1–I4); the examples 783 → 784 and 701, 703 → 704 do — on purpose, a
  "successor" rule would retell the formula.
- Phase 2: on an installed project whose old sequential numbers already filled 100–199 or 400–499
  the next hotfix follow-up or runner's task is 1101 or 1401 — right by the owner's rule, and until
  S3 such a task queues last; the PROGRESS entry and the documents say so.
- Phase 2: Q6 holds two decisions (the name `_own_number` stays; the `:03d` format stays) under
  one reason — both leave `maintain_task` and `cleanup_task` untouched.
