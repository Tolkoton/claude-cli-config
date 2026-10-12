# Slice numbers-class-table — planning artifact

Driven by the feature `task-numbers-by-class` (`.engine/architecture/feature/task-numbers-by-class.md`,
slice S2). Frame supplied by the feature artifact; the owner is not asked. Stands on slice S1
(`task-class-overflow`, built, overseer PASS 20261012T004536Z-d372cb): `task_classes.class_of`,
`next_number`, `Board.taken`.

## Goal
The classes are written down in one file the owner reads and edits, `tasks/CLASSES.md`, and a task
can say which class it belongs to with one optional line, `Клас: <номер>`. A task file that
arrives in the inbox without a number and with that line gets the next number of its class when
it is taken. Measurable (the feature's A2): the first inbox file of class 3 becomes
`301-<name>.md`, the tenth `310-…`; a line naming a class the table does not have is refused with
the file's name, the file stays in the inbox and nothing is written to the board. (A task without
the line is class 1 — shown by S1's hotfix follow-up, the one place that numbers such a task.)

## Premise verified
- S1's contract out exists as built: `.claude/unattended/task_classes.py` (`class_of`,
  `next_number`, `UNCLASSED = 1`), `board.py` `Board.taken` — commit f121980, 2026-10-12.
- `import_inbox` today passes over every inbox file whose name is not `NNN-name.md`
  (`board.py` `import_inbox`: `if number is None or not source.is_file(): continue`) — so taking
  an unnumbered file is a new branch, and no file taken today changes its path — read 2026-10-12.
- A project file with `seed=` in `.claude/ownership.txt` is created by `engine.py install` when the
  project lacks it and is never overwritten (`.claude/ownership.txt:108-116`, the rows of
  `tasks/README.md` and `tasks/TEMPLATE.md`; `tests/test_board.py` «seeded once») — read 2026-10-12.
  `engine.py update` of a project installed BEFORE the row creates the file too: a seed target that
  is absent and not in the lock's `seeded` list is planned as a `seed` action (`engine.py:878`,
  `elif not target.exists() and target_path not in seeded_before`) — read 2026-10-12; asserted in
  a test (Hardest seams, 4). So an older project gets a table with example rows on its next update.
- No external system: untested — common knowledge (text parsing, the standard library).

## Out of scope (deliberately)
- The order of the queue. This slice writes the key (`queue_key`) and tests it as a function;
  `Board.queue` and the review keep today's order until slice S3 wires it in.
- `renumber`, the old-name lookup of the inbox, `check` over the whole board — slice S4.
- A `Клас:` line in a file that already carries its number: not read for numbering, never a
  reason to refuse the file (feature K4) — `105-x.md` with `Клас: 3` is task 105, as today.
- An unnumbered inbox file WITHOUT the line: left in the inbox untouched and unmentioned, as today.
- An unnumbered file dropped a second time (the owner's edited copy): it is a second task with the
  next number — the board cannot know it is the same one. To rewrite a task the owner uses its
  numbered name, which replaces the one in `todo/` as today; the closing step's documents say so.
- The line `ПОМИЛКА: tasks/CLASSES.md: …` in the owner's review (`board_review.py` builds its error
  lines itself, from a commit): slice S3, which already reads the table there.
- `CLASSES.md` arriving through the inbox (the feature's deferral); a command that prints the next
  number (dropped by the simplifier, F-e372b498).
- `tasks/README.md`, `tasks/TEMPLATE.md` and the other documents — the feature's closing step.
  This slice writes the two `CLASSES.md` files only.

## Seam (contract)
- Signature, added to `.claude/unattended/task_classes.py`:
  - `parse_classes(text: str) -> tuple[int, ...]`
  - `read_classes(tasks: Path) -> tuple[int, ...]`
  - `table_errors(text: str) -> list[str]`
  - `class_for(wanted: int, classes: tuple[int, ...]) -> int`
  - `queue_key(classes: tuple[int, ...], first: list[str]) -> Callable[[str], tuple[int, int, int]]`
- in `board.py`: `Task.klass: int | None` and `Task.class_error: str` (set by `parse`); a new
  branch of `import_inbox`; one more source of lines for `check`.
- Returns:
  - `parse_classes` — the class numbers of the table rows of the text, in the text's order. A row
    is a line that starts with `|` and whose first cell, stripped of spaces and tabs, is ASCII
    digits only (`[0-9]+`) with a value 0…9 (so `03` is 3; `+3`, `3.`, `№3` are not rows); a class
    seen a second time keeps its first place and is not repeated; every other line (the header, the `|---|` rule, prose, a row
    whose first cell is another integer or no integer) gives nothing. `()` for a text without rows.
  - `read_classes` — `parse_classes` of `<tasks>/CLASSES.md`; `()` when the file is absent.
  - `table_errors` — one sentence (Ukrainian, technical terms English) per defect of the table: a
    row whose first cell is an integer by the same definition (ASCII digits only) with a value
    outside 0…9 (one sentence per such row), and a class that has two or more rows (one sentence
    per class); `[]` for a sound table and for an empty text. A
    first cell that is not digits only (`-1`, `+12`, a word) is prose to both functions.
  - `class_for` — the class a task that NAMES one is numbered in: `wanted`, when it is 1…9 and is
    in `classes`. (A task that names none is class 1 — `UNCLASSED` — and no caller of this slice
    has such a task to number: an unnumbered inbox file without the line is not taken, and the
    hotfix follow-up numbers in class 1 since S1. So the function has no `None` branch.)
  - `queue_key` — a key over a task FILE NAME (`NNN-name.md` or a `done/` folder name): (its
    index in `first`, or `len(first)` when it is not named there; the index of `class_of(its
    number)` in `classes`, or `len(classes)` when the class is not listed; its number). A name
    without a number sorts with number 0, as `Board.files` does today — a number being what
    `board.number_of` reads: three or more ASCII digits and a `-` at the start of the name (so
    `12-fix.md` has no number). A name that stands twice
    in `first` has the index of its first place (what `board.first_rank` does today).
  - `Task.klass` — the integer of the one `Клас:` line of the task's header (the text above the
    first `## ` heading, HTML comments removed, as every other header line is read); `None`
    without a line. A `Клас:` line is a line that BEGINS with exactly `Клас:` (as the other header
    lines are matched: no indent, no list mark, this case); `  Клас: 3`, `- Клас: 3` and `клас: 3`
    are no line. The value is what follows `Клас:` on that same line, stripped of spaces, tabs
    and a trailing `\r` (a file saved with CRLF reads like any other, as the other header lines
    do); it is a class when it is ASCII digits only (`[0-9]+`; `03` is 3). `Task.class_error` —
    `""`, or why the line names no class (and then `klass` is `None`): two or more lines, or a value that is not digits only
    («Клас: три», `+3`, `3.`, and an EMPTY value — the value never runs on into the next line).
- Errors: `class_for` raises `ValueError` whose message says the class and why — class 0 («до
  класів, нових задач у ньому не буває»), a class that is not in `classes`, and any class at all when
  `classes` is `()` (there is no table to find it in). Nothing else raises.
- `import_inbox`, the new branch — an inbox file `<name>.md` whose name is NOT `NNN-name.md`:
  - no `Клас:` line and no `class_error` → passed over without a line, exactly as today;
  - an unreadable `Режим:` line → skipped as a numbered file is today (same line, same journal entry);
  - `class_error`, or `class_for` refuses → the line
    `<name>.md skipped: <why> — the board does not take it; the file stays in the inbox`, the file
    stays, nothing changes under `tasks/`, and one anomaly-journal entry naming the file and the
    reason is written, once per file and reason (the pattern of `_unread_mode`; the entry lands
    under `.engine/journal/anomalies/`);
  - otherwise → the number is `next_number(board.taken(), class)`, the task is written to
    `tasks/todo/<number>-<name>.md` (the number as `{number:03d}`), the inbox file is removed, and the
    line is `<name>.md imported: tasks/todo/<number>-<name>.md`. The text is written as it came,
    with one change: a first line that begins `# NNN —` (the template's placeholder, the three
    letters) gets the number in place of `NNN`.
- The order inside one call: every NUMBERED file of the inbox is taken first, in today's order;
  then the unnumbered ones, in name order. Each unnumbered file counts its number from
  `board.taken()` as it is at that moment UNITED WITH the numbers of the `NNN-name.md` files that
  are still in the inbox at that moment (a numbered file that was skipped — for an unreadable
  `Режим:`, say — stays there and still claims its number). So the unnumbered files get successive
  numbers, never the number of a task on the board, and never a number a file waiting in the inbox
  carries.
  (Today's loop sorts by `(number or 0, name)`, which would take the unnumbered ones FIRST: `a.md`
  with `Клас: 3` would become `todo/301-a.md`, and a hand-numbered `301-foo.md` of the same inbox
  would then "replace" it — the task gone from the board and from the inbox. The same loss, one
  call later, if `301-foo.md` is skipped for its mode while `a.md` takes 301: the corrected
  `301-foo.md` replaces it on the next import. The united set closes both.)
- A numbered inbox file goes the way it goes today, byte for byte; its `Клас:` line is not read.
- The shape, so that no existing function gets worse (the project's own measure gives
  `import_inbox` 22, `parse` 17, `summary` 19 against a limit of 13, and the budget measures a
  function that got worse): the unnumbered pass is one helper, `_take_unnumbered(board, inbox) ->
  list[str]`, called once after the numbered loop (`lines += …`), which itself only stops taking
  unnumbered names (it does that already); `parse` gets the line through one branch-free call of a
  helper `_class_line(header) -> tuple[int | None, str]`; `summary` and `check` get the table's
  lines by concatenation with the duplicate lines.
- The cases of an unnumbered file are tried in the order written above, and the first that
  applies wins: `notes.md` with no `Клас:` line and a bad `Режим:` is passed over without a line;
  a file with a bad `Режим:` and `Клас: три` is skipped for its mode.
- `board.py check` and `board.py summary` (both print the board's error lines): after the duplicate lines, one line
  `ПОМИЛКА: tasks/CLASSES.md: <sentence>` per entry of `table_errors`; `check` exits 1 when there is
  any line. A board without the file has no such line.
- The two files:
  - `tasks/CLASSES.md` (this repository's): a short introduction and one table,
    `| Клас | Назва | Що туди йде | Продовження |`, the rows in the order 0, 1, 2, …, 9 with the
    classes the owner approved (task 401 item 1): 0 — задачі до класів (000–099), нових не буває;
    1 — загальні задачі власника й задачі без класу; 2 — режими й рівні дизайну; 3 — gates, hook-и,
    overseer; 4 — task board, runner, паралельні агенти, і задачі догляду й прибирання, які runner
    кладе сам; 5 — виміри (evals, golden set, огляд); 6 — хмарні сесії й середовище; 7 — відкриті
    пункти; 8 — питання про правила; 9 — питання gates. The «Продовження» cell says in words where
    the class goes on (`1701–1799, далі 2701…`); the code does not read that cell.
  - `templates/project/tasks/CLASSES.md` (the seed): the same table shape, the rows in the order
    0, 1, …, 9; row 0 — задачі, створені до класів; rows 1, 4, 7, 8, 9 as above (the classes the
    engine itself numbers in), rows 2, 3, 5, 6 marked as an example the project's owner rewrites.
    `.claude/ownership.txt` gains `project  tasks/CLASSES.md  seed=templates/project/tasks/CLASSES.md`.
- Dependencies (injected): the text of the table (`parse_classes`, `table_errors`), the classes and
  the first-names (`queue_key`); `read_classes` and `import_inbox` read the board they are given.
- Does NOT do: quiet a refused file — it prints its `skipped:` line on every import while it lies
  in the inbox, as a file with a bad `Режим:` does today (the journal entry is written once);
  order the queue; read the «Продовження» cell; refuse or renumber a numbered file;
  take an unnumbered file without the line; change `Board.files`, `unblock`, or any other command.

## Decisions (with WHY)
- Q1: the table is a Markdown table read by its first cell — chosen because the owner reads and
  edits the file by hand and through GitHub, where a table renders, and "a line that starts with
  `|` and an integer" needs no format of its own. Rejected: a `key: value` or JSON file — exact
  for a parser, but a second document would then be needed to tell the owner what the classes
  mean, and two files drift. Rejected: reading the order from the «Продовження» cell or a
  priority column — the owner's answer (3) is "the order of the rows".
- Q2a: the reader keeps what it can of a table with a defect — chosen because a mistyped row must
  not stop the board (P3): the sound rows keep their meaning. Rejected: refusing to read a table
  with any defect — one typo would silently fall back to the order by number for every class.
- Q2b: a defect is reported by `check` and `summary` as a `ПОМИЛКА` line — chosen because it must
  not be silent either (G5), and those two already carry the board's error lines. Rejected: saying
  nothing — a class the owner believes listed would refuse its tasks at the inbox with no hint that
  the table is the cause. (The owner's review prints its own error lines; that one is S3's.)
- Q3: the unknown class is refused where the number is given — the inbox — with the anomaly-journal
  entry that an unreadable `Режим:` gets; chosen because that is the owner's test («відмова з
  назвою файла, не тихий клас 1») and the existing way an inbox file is refused, so the owner meets
  one behaviour, not two. Rejected: taking the file into class 1 with a warning — the owner's words
  rule it out. Rejected: putting the file into `blocked/` with a question — it would need a number,
  which is exactly what cannot be given.
- Q4: an unnumbered file needs the line to be taken (feature K4) — chosen because the task says
  «`назва.md` з рядком `Клас:`» and because the inbox also holds what is not a task; a line is an
  explicit "this is a task". Rejected: every `*.md` without a number is a class-1 task — a stray
  note would become a task of the board.
- Q5: a class that is NAMED needs the table: without it there is nothing that says the class
  exists, so `class_for` refuses every class when `classes` is `()`. ("No line → class 1", the
  owner's rule, needs no table and no code here: its one site is S1's hotfix follow-up.)
  Rejected: accepting any class 1…9 when there is no table — a typo (`Клас: 6` for 3) would then
  be checked on a project with a table and silently accepted on one without.
- Q6: the `# NNN —` placeholder of the first line is filled — chosen because the template's first
  line is `# NNN — Коротка назва задачі` and a task whose title still says NNN after it got 301
  misleads the reader of the review. Rejected: leaving the text byte for byte — simpler by three
  lines, and every such task would carry a wrong title forever. Nothing else in the text changes.
- Q7: `queue_key` is written here and wired in S3 (the feature's contract out of S2) — chosen
  because it is the table's reader's other half and is testable as a pure function now; S3 then
  changes callers only (`Board.queue`, `board_review.plan_section`). Rejected: writing it in S3
  (the feature-critic's round-2 note N4) — S3 would then both write the key and move two callers.
  The key restates the first-rank rule of `board.first_rank` because `task_classes.py` cannot
  import `board` (the import runs the other way); S3 moves `first_rank`'s callers to `queue_key`
  and deletes `first_rank` when none is left, so the rule ends in one place.
- Q8: numbered files first, then unnumbered, and an unnumbered file never takes a number that a
  numbered file still in the inbox carries — chosen because a number the owner wrote by hand is
  the owner's word and must land where it says, now or after the owner has corrected the file,
  while an unnumbered file has no claim on any particular number. The united set costs one set
  union: `next_number` takes any iterable. Rejected: numbered-first alone (the first draft of this
  rule) — a numbered file skipped for its `Режим:` is not on the board, the unnumbered file takes
  its number, and the corrected file deletes that task on the next import. Rejected: today's order
  with the inbox's numbers counted — it closes the same hole, but leaves an unnumbered file
  written before the numbered ones are judged, so what it counted from is not yet what the call
  will leave. Rejected: leaving the order — the lost task described in the Seam.
- Q9: the `Клас:` line is read by `parse`, into `Task`, beside every other header line — chosen
  because the header (above the first `## `, comments removed) is cut in exactly one place, and a
  second cutter for one line would drift from it; the cost is one regex per task read. Rejected: a
  pure `class_line(text)` in `task_classes.py` called only from the new branch — it keeps `Task`
  smaller, and would have to re-implement the header cut or import `board`, which it cannot.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
All of these are tested in the contract-test file `tests/test_task_class_table.py`, except Seam 4
(the builder's `tests/test_board.py`, beside the install it already runs).
- **Seam 1: "refused" must mean nothing moved** — test approach: after a refused file, compare the
  names AND bytes of everything under `tasks/` (the four columns and the root, `.first` included)
  with before — the journal entry is not under `tasks/` at all: it goes to this session's file
  under `.engine/journal/anomalies/` (`tasks/ANOMALIES.md` is written by a fold only); assert the inbox file is still there
  byte for byte; assert the journal entry appears once after TWO imports of the same file. Rules
  out asserting only the printed line.
- **Seam 2: the number is counted from the whole board at the moment each file lands** — test
  approach: ten class-3 files in one `import-inbox` call on a board with no class-3 number (301 …
  310, the owner's case), plus one class-7 file in the same call on a board holding
  `blocked/799-x.md` (→ 1701): mixed classes in one call, a continuation, no number given twice.
  And a board whose ONLY class-3 number is `done/304-old/` → the file becomes 305 (a `done/`
  number counts; `done/300-old/` would prove nothing — 301 comes out with or without it). Rules
  out a counter taken once before the loop, and a reader of one column.
- **Seam 2a: an unnumbered and a numbered file of one call** — test approach: one `import-inbox`
  call with `a.md` (`Клас: 3`) and `301-foo.md` on a board with no class-3 task: afterwards
  `todo/301-foo.md` and `todo/302-a.md` both exist, each with its own text, and two `imported`
  lines were printed, the numbered file's first. Rules out the loop order that deletes a task it has just written.
- **Seam 2b: a numbered file that stays in the inbox keeps its number** — test approach: one call
  with `301-foo.md` carrying `Режим: абищо` and `a.md` (`Клас: 3`) on a board with no class-3
  task: `301-foo.md` is skipped and still in the inbox, `a.md` becomes `todo/302-a.md`; then the
  mode line is corrected and a second call gives `todo/301-foo.md` beside `todo/302-a.md`, both
  texts intact. Rules out counting from the board alone.
- **Seam 3: today's inbox behaviour is untouched** — test approach: the existing `import-inbox`
  cases of `tests/test_board.py` and `tests/test_mode.py` stay as they are and stay green (and
  `tests/test_board_runner.py`, `tests/test_owner_perimeter.py`, which reach the inbox through the
  runner and the path guard); new cases: `105-x.md` carrying `Клас: 12` is task 105 in `todo/`;
  `106-y.md` carrying `Клас: три` (a `class_error`) is task 106 in `todo/` with its text, an
  `imported` line, no `skipped:` line, no journal entry, and `board.py next` offers it; `notes.md`
  with no line is still in the inbox and no line was printed. Rules out calling `class_for` on a
  numbered file, and — the closer copy of the existing pattern — treating `class_error` the way
  `mode_error` is treated (refusing in the numbered loop, dropping the task from `Board.ready`,
  a «не береться» line in `summary`).
- **Seam 4: the seed in a real install** — test approach: a synthetic `engine.py install` (as
  `tests/test_board.py` already runs one) has `tasks/CLASSES.md` byte-equal to the seed, an owner's
  edit of it survives `engine.py update`, and `parse_classes` of the seed is exactly
  `(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)`; and a project that was installed before the row — the
  installed project with `tasks/CLASSES.md` deleted and its name taken out of the lock's `seeded`
  list, which is what such a project's lock looks like — gets the file, byte-equal to the seed,
  from `engine.py update`.
- **Seam 6: the order of the rows is the order** — test approach: a table text whose rows are NOT
  in numeric order (7, 3, 1, then 3 again) → `parse_classes` gives `(7, 3, 1)`: the text's order,
  a repeated class at its first place; with those classes, `queue_key` puts a class-7 name before
  a class-3 name whatever their numbers (`799-x.md` and `1701-y.md` before `301-z.md`: a
  continuation ranks with its class), and a name whose class is not listed (`501-w.md`) after
  every listed one. Rules out a reader that returns the classes sorted and a key that ignores
  `classes` or ranks by the class digit — both of which pass every other test, because every other
  table is 0…9 in order.
- **Seam 5: the header only** — test approach: a `Клас:` line below the first `## ` heading (in
  «Що зробити») and one inside an HTML comment are not the task's class; two header lines are a
  `class_error`; `Клас:` with an empty value followed by a `Режим: соло` line is a `class_error`,
  not the class «Режим:» (the run-on a pattern copied from the neighbouring `\s*(\S+)` readers
  would make); `Клас: 3` in a CRLF file is class 3; `Клас: 3 (gates)` and `Клас: ٣` (a digit that
  is not ASCII — `int()`, `isdigit()` and `\d` all accept it) are a `class_error`, and a table row
  `| ٣ |` is prose. Rules out a regex over the whole text and a reader built on `\d` or `int()`.
The contract tests are the tester's, written before the code: each is RED against the tree as it
is (the functions and the branch do not exist), by construction.

## Invariants (rules that hold for every input in the stated domain)
- **I1** — `parse_classes` gives only classes, each once: every member is an integer 0…9 and no
  member repeats.
  - Domain: every text (any string, the empty one included).
  - Source: this contract's «Seam» (`parse_classes`); feature K1 (a class is one digit).
  - Broken by: returning every integer first cell (a row `| 12 |`), or the same class twice.
- **I2** — the key never changes the order inside a class: for two names of the same class that
  are both absent from `first`, the one with the smaller number sorts first, whatever `classes` is.
  - Domain: every `classes` (a tuple of distinct integers 0…9, `()` included), every `first`,
    every pair of names the key accepts (a name without a number counts as number 0).
  - Source: task 401 item 5 («усередині класу — найменший номер»).
  - Broken by: sorting by name inside a class; comparing numbers as text (`1701` before `799`).
- **I3** — with no table the key is today's order: for `classes == ()` and any `first`, sorting
  names by `queue_key` equals sorting them by (index in `first` or `len(first)`, number).
  - Domain: every list of names the key accepts (a name without a number counts as number 0),
    every `first` (a name may stand in it twice).
  - Source: feature K6 (no `CLASSES.md` → the queue is by number, as today).
  - Broken by: ranking a class when nothing is listed (e.g. by `class_of` itself: 1701 before 800).
- **I4** — a name in `first` sorts before every name that is not, whatever their classes and numbers.
  - Domain: every `classes`, every `first`, every pair of names one of which is in `first`.
  - Source: task 401 item 5 («`tasks/.first` … працюють, як зараз»).
  - Broken by: putting the class rank before the first-rank in the key.
- **I6** — the table's order is the order of classes: for two names that are both absent from
  `first` and whose classes both stand in `classes`, the one whose class stands earlier in
  `classes` sorts first, whatever their numbers; and of two names both absent from `first`, the one
  whose class stands in `classes` sorts before the one whose class does not.
  - Domain: every `classes` (distinct integers 0…9 in ANY order), every `first`, every such pair
    of names.
  - Source: task 401 item 5 («бере класи в порядку рядків `CLASSES.md`»); feature K6 (a class
    missing from the table queues after the listed ones).
  - Broken by: a key that ignores `classes`; a key that ranks by the class digit; a reader that
    sorts the classes.
- **I5** — `class_for` never invents a class: its result equals `wanted`, which is then in
  `classes` and is 1…9.
  - Domain: every integer `wanted`, every `classes`; the calls that raise are outside the rule.
  - Source: task 401 item 2 and its test («не тихий клас 1»).
  - Broken by: falling back to 1 for an unknown class; accepting class 0. (Its test includes a
    named class that is accepted — a function that refuses every named class would satisfy the
    rule and nothing else.)

No rule is written here for the two seams that hold state or parse a line. The `Клас:` line is
listed case by case in the «Seam»; a rule would retell the cases. `import_inbox`'s unnumbered
pass does have a rule, stated in the «Seam» («never the number of a task on the board, and never a
number a file waiting in the inbox carries») — it is tested by the three cases of Seams 2, 2a and
2b rather than lifted to an invariant: its domain is a board plus an inbox, which an example test
covers by construction and a rule here would not widen.

## Exit criterion
- The contract-test file `tests/test_task_class_table.py` (a suite of its own, built with
  `tests/hook_env.py`, added as a line `test_task_class_table.py` at the end of
  `tests/fast-suites.txt`, with the comment line and measured time the file's convention asks):
  `test_I1_…`…`test_I6_…`; Seam 6's table out of numeric order (`parse_classes` → `(7, 3, 1)`;
  the key: 799 and 1701 before 301, 501 after all); the reader on this repository's
  `tasks/CLASSES.md` → sorted, exactly 0…9, and `table_errors` → `[]` (not the order of the rows:
  the owner reorders them on purpose); the seed → exactly `(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)`;
  `table_errors` on
  a text with a row `| 12 |` and with class 3 twice → two sentences; `Task.klass` and
  `class_error` for the cases of Seam 5; and, through the real `board.py import-inbox` CLI on a
  synthetic board whose `tasks/CLASSES.md` is a copy of the seed:
  - ten files `a01.md`…`a10.md` with `Клас: 3`, no class-3 number on the board → `todo/301-a01.md`
    … `todo/310-a10.md`, the inbox empty, an `imported` line for each of the ten;
  - `done/304-old/` the only class-3 number → the file becomes `todo/305-<name>.md`;
  - Seam 2a: `a.md` (`Клас: 3`) and `301-foo.md` in one call → `todo/301-foo.md` and
    `todo/302-a.md`, both texts intact;
  - in the SAME call as the ten, a file with `Клас: 7` beside `blocked/799-x.md` →
    `todo/1701-<name>.md`;
  - Seam 2b: `301-foo.md` with `Режим: абищо` and `a.md` (`Клас: 3`) in one call → `301-foo.md`
    skipped and still in the inbox, `todo/302-a.md`; after the mode is corrected, a second call →
    `todo/301-foo.md` beside `todo/302-a.md`;
  - `Клас: 3` in a file saved with CRLF → taken, class 3;
  - a first line `# NNN — Назва` → `# 301 — Назва` in the written task, the rest byte for byte —
    the fixture carries `NNN` and a line `# NNN — інше` again further down, both untouched;
  - NEGATIVE, each with Seam 1's three assertions: `Клас: 12` (not in the table), `Клас: 0`,
    `Клас: три`, `Клас:` with an empty value followed by a `Режим: соло` line, two `Клас:` lines,
    and `Клас: 3` on a board WITHOUT `tasks/CLASSES.md` — the printed line begins
    `<name>.md skipped:` and names the reason (asserted: the prefix, and that the line carries
    the word `Клас` — the exact wording of a reason is the builder's);
  - NEGATIVE: `x.md` with `Клас: 3` and `Режим: абищо` → skipped with the mode's reason, still in
    the inbox, `todo/` unchanged; and `y.md` with `Клас: три` and `Режим: абищо` → skipped for its
    MODE (the first case that applies wins);
  - NEGATIVE: `Клас: 3 (gates)` and `Клас: ٣` → skipped, a `class_error`;
  - `notes.md` without the line: still in the inbox, no line printed;
  - `105-x.md` with `Клас: 12` → `todo/105-x.md`, as today; `106-y.md` with `Клас: три` →
    `todo/106-y.md`, an `imported` line, no `skipped:` line, no journal entry, and `board.py next`
    offers it (`summary` prints no «не береться» for it);
  - `board.py check` on a board whose table has `| 12 |` → exit 1 and a line
    `ПОМИЛКА: tasks/CLASSES.md: …`, and `board.py summary` on that board prints the same line; on
    the seed → `check` exits 0, no line.
- The seed (Seam 4), in `tests/test_board.py` beside the synthetic install it already runs:
  `tasks/CLASSES.md` installed byte-equal to `templates/project/tasks/CLASSES.md`; an edited one
  survives `engine.py update`; a project installed before the row (the file deleted and its name
  removed from the lock's `seeded` list) gets it from `engine.py update`, byte-equal to the seed.
- The owner's terms, in everything this slice writes for the owner: `tests/test_owner_terms.py`
  reads a fixed list of files, `OWNER_TEXT`, and none of these is in it — the slice adds
  `tasks/CLASSES.md`, `templates/project/tasks/CLASSES.md` AND `.claude/unattended/task_classes.py`
  (where the sentences of `table_errors` and of `class_for`'s refusal live; they reach the owner in
  the `skipped:` line, the anomaly-journal entry and the `ПОМИЛКА: tasks/CLASSES.md: …` line). The
  evidence is the suite's own three lines `ok   …` for those files, shown in the claiming turn;
  the suite's existing negatives already show that a retired rendering is caught.
  `tests/test_text_hygiene.py` stays green — it checks the seed (under `templates/`) for this
  repository's dates and records, nothing about terms.
- Both new documents are `git add`ed before the fast run: `tests/test_ownership.py` requires every
  seed to be a tracked file. `tests/test_owner_terms.py` and the new `tests/test_task_class_table.py`
  are made executable (the first is not today — ruff's EXE001 — and is a suite this slice changes).
- `bash tests/run_all.sh --fast` green, and each of these green when run by itself, because they
  drive the inbox, the seeds or `check`: `test_board`, `test_board_runner`, `test_board_review`,
  `test_owner_perimeter`, `test_mode`, `test_cleanup`, `test_maintain`, `test_ownership`,
  `test_project_seeds`, `test_engine_install`, `test_release`, `test_settings_proposal_install`,
  and `test_hotfix` (the one runtime check that `hotfix.py` still imports the module this slice
  edits). The full set is the feature's, once at the end; the PROGRESS entry says it was not run
  here, and names the suites that install the engine from `HEAD` and so cannot see this slice
  before its commit (`test_migration`, `test_state_migration`, `test_supervisor_retired`,
  `test_settings_wiring`, `test_install_move_notes`, `test_legacy_records_survive`, part of
  `test_engine_install`): their first update of an older project gains a `seed tasks/CLASSES.md`
  action, first seen after this slice's commit — by the next fast run for
  `test_legacy_records_survive` (it is in the fast subset), by the feature's full run for the rest.
  The hooks that import `board.parse` and whose suites are outside both lists (`test_lesson_queue`,
  `test_gate_allows`, `test_overseer_fresh`, `test_testing`, `test_journal`,
  `test_refusal_branches`) are likewise the full run's: `Task` gains two fields with defaults and
  is built in one place.
- One invocation of `uvx --offline ruff check` over `.claude/unattended/task_classes.py`,
  `.claude/unattended/board.py` and EVERY suite this slice changes or adds exits 0, and its output
  is shown in the claiming turn; `uvx --offline mypy --strict` on the two production files
  together with `.claude/hooks/hotfix.py` is clean.
- The smoke, a one-off on a copy (not a suite case): this repository's `tasks/` file names and its
  real `tasks/CLASSES.md` copied to a temporary root, an inbox holding `smoke.md` with `Клас: 3`;
  the real `board.py --root <copy> import-inbox <inbox>` prints
  `smoke.md imported: tasks/todo/<n>-smoke.md` where n is of class 3 and above every class-3
  number of the copy. The literal output goes into the PROGRESS entry.

## Complexity budget
base_commit: 8ef059dc1b5e21841faf5b1af186d95028101a17
max_new_files: 0
max_net_new_lines: 110
max_new_public_symbols: 7
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 13
max_nesting_depth: 3
justification: no new production file (the two CLASSES.md files are documents). Public names are the Seam's — parse_classes, read_classes, table_errors, class_for, queue_key in task_classes.py, and the two fields Task.klass and Task.class_error (the tool counts top-level functions and classes only: five). The lines are the five functions, the Клас: parsing and the unnumbered pass of import_inbox with its journal entry. No existing function is made more complex: the new code lives in helpers (_take_unnumbered, _class_line) that import_inbox, parse, summary and check call without a new branch.

## Deferred to later slices
- Wiring `queue_key` into `Board.queue` and the review — why later: S3 owns the order and its
  tests on the real board; S3 pays nothing extra, it changes callers only — revisit trigger: slice
  S3 `numbers-queue-order`, the next one built.
- The inbox finding a renumbered task by its old name — why later: there is no `renumber` yet;
  S4 pays a second edit of `import_inbox` and must put the lookup in front of both the numbered
  pass and `_take_unnumbered` — revisit trigger: slice S4 `numbers-renumber`.
- The table's `ПОМИЛКА` line in the owner's review — why later: `board_review.py` builds its error
  lines from a commit, and S3 is the slice that teaches it to read the table from one — revisit
  trigger: slice S3 `numbers-queue-order`.
- What the documents say about the line and the unnumbered file (`tasks/README.md`,
  `tasks/TEMPLATE.md`, `owner-review.md`) — why later: one pass over all documents when every
  behaviour exists; the price is text that stays wrong meanwhile (`tasks/README.md` «Номери від
  700 лишіть…», `owner-review.md` "below 800", wrong since S1) — revisit trigger: the feature's
  closing step, before task 401 closes. Facts that step must carry: an older project gets
  `tasks/CLASSES.md` with example rows on its next `engine.py update`; a `Клас:` line in the
  template must carry a value (a bare `Клас:` is refused); an unnumbered file dropped twice is two
  tasks.

## Open items requiring human decision (if any)
None.

## Critic notes (non-blocking)
- Phase 2: the same loss survives ACROSS calls and is today's deliberate rule: `a.md` became
  `todo/301-a.md`, and a hand-numbered `301-foo.md` dropped later replaces it. The closing step's
  documents must say it: a number written by hand in a class the inbox numbers replaces the task
  that holds it. A crash between the write to `todo/` and the removal from the inbox leaves an
  unnumbered file that becomes a second task on the next import (a numbered one is an idempotent
  `replaced`).
- Phase 2: a table row must begin with `|` at the start of its line; a row written with leading
  spaces or without the leading pipe renders on GitHub and is prose to the reader — the table's
  introduction says so. Q8 holds two decisions (the pass order; the united set), each with its own
  rejected alternative.
- Phase 3: an unnumbered name that begins with digits (`12-fix.md`) becomes `301-12-fix.md`, and
  the template's own name shape `NNN-name.md` becomes `301-NNN-name.md` — both work; the documents
  say "name the file without a number".
- Phase 3 took four critic rounds, each a new factual gap and each closed as asked (a same-call
  loss of a task; the same loss through a skipped numbered file; the row order untested; a
  numbered file refused for its `class_error`); no objection is left unaccepted. Logged AUTONOMOUS
  in `.engine/overseer/escalations.md`. The last round's note that `class_for(None)` had no caller
  was taken: the branch is gone.
- Phase 4: the contract suite pins this repository's ten rows (sorted 0…9, no defect); if the
  owner removes or mistypes a row the fast subset goes red, and that red means "the owner changed
  the table", not "fix the table". The feature's integration criterion named `tests/test_board.py`
  for A2; A2 is shown in `tests/test_task_class_table.py` (the feature artifact is corrected).
  Besides the suites named as the full run's, every other suite that loads `board.py` through a
  hook (`test_push_by_environment`, `test_shell_text`, `test_gate`, `test_audit_verdict_parsing`)
  is the full run's too.
