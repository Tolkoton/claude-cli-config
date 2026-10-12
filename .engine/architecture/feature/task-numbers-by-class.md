# Feature task-numbers-by-class — a task's number is its class × 100 + its place in the class

Frame source: board task `tasks/doing/401-task-numbers-by-class-build.md` (the owner's text) and the
design it builds, `tasks/done/741-open-item-attended-session-task-numbers-600-699/design.md` (second
version, above the rule), with the owner's four answers in `task.md` beside it: «(1) так, (2) +10,
(3) за CLASSES.md, (4) так, але однакові номери розводить лише runner після синхронізації гілки».
Every numbered item of the task is an owner requirement; the critic checks how each is met, not
whether. Unattended: the owner is not asked. Nothing in this frame is PROVISIONAL — the acceptance
criteria are the task's own test list, and the autonomy grant is the task itself («Будуй окремою
задачею», placed in the runner's queue), so no ratification question is parked.

## Goal

A task's number says which class of work it belongs to: number = class × 100 + the task's ordinal in
the class. Whoever creates a task (the owner, a session, the runner, a hook) takes the next number of
its class from one function. A class that runs out of two digits continues in the identifier + 10
(799 → 1701), so a number never walks into another class. The runner takes classes in the order the
owner wrote them in `tasks/CLASSES.md`. Two files that got one number in two clones are told apart
by a script the runner runs after it synchronises the branch — the older keeps the number, the other
gets the next one of its class together with every reference to it — and nobody renumbers by hand.

## What is true today (checked on this board, 2026-10-11)

- `board.py` numbers open items from 700, rule questions from 800, gate questions from 900 — each
  "the first free number from there", with no upper bound (`open_item`, `rule_question`,
  `gate_question`); the runner's own tasks get "the largest number under 700, plus one" (`_own_number`);
  `hotfix.py next_number` has a third copy ("the largest under 800, plus one").
- **Class 7 is already full**: 700–799 hold 100 tasks, and the open items that came after took
  801–843 — the numbers of rule questions. The overflow the task calls urgent has happened.
- Numbers by hundred: 0 → 96 (000–099), 1 → 11 (100–110), 4 → 1 (401), 6 → 4 (600–603), 7 → 100,
  8 → 44 (800–843), 9 → 2 (900–901). No number is held by two files, in one column or across columns.
- The queue is `tasks/.first`, then the number ascending (`Board.queue`).
- The runner synchronises with `git pull --rebase --autostash` (`sync_branch`). It does not call
  `journal.py fold` anywhere (the task says "beside `journal.py fold`": there is no such call —
  the renumber step stands right after `sync_branch`).

## Acceptance criteria (the owner's, from the task's «Що зробити» and «Тести»)

- **A1** An open item never gets a number outside class 7 and its continuations: from 783 —
  784…799, then 1701, never 800. The same for rule questions (8) and gate questions (9).
- **A2** The first task of class 3 is 301, the tenth 310. A task without a `Клас:` line is in class
  1, after the largest number there. A `Клас:` line naming a class `CLASSES.md` does not have is
  refused with the file's name — never a silent class 1. ("Without a line → class 1" is shown where
  a number is given without one: the hotfix follow-up (S1), and S2's function that turns a task's
  text into its class — `None` line → class 1 — tested directly. The inbox takes no unnumbered
  file without the line — K4.)
- **A3** Two clones of one synthetic repository each create a class-3 task; after the merge there
  are two files 301. `board.py renumber` leaves 301 to the older, the other becomes 302;
  `Залежить від: 301` in the second branch's task becomes 302; `board.py check` is empty; an inbox
  answer under the old name finds 302; a second `renumber` changes nothing.
- **A4** `renumber` on a board without a clash changes no file.
- **A5** Moving a row of `CLASSES.md` changes which task `board.py next` gives; `tasks/.first` is
  still first.
- **A6** The initial `CLASSES.md` on today's board gives the same first task as the queue by number.
- **A7** Old tasks are not renamed; `Залежить від:`, reports and inbox answers with old numbers work
  as before.
- **A8** Documents: `tasks/CLASSES.md` and its template; `tasks/README.md` and its template say
  classes, the `Клас:` line, the order, `renumber`; `.claude/unattended/README.md` has the runner's
  step; `AGENTS.md` only if it fits the line budget.

## Build parameters

- Budgets/thresholds: none. No number in this feature is a quality threshold; "two digits per
  class" and "+10" are the owner's arithmetic.
- Policies: standard library only; UTC; ruff and `mypy --strict` clean on changed Python; every
  refusal names the file it refuses; whatever the board cannot do is an anomaly-journal entry and
  the board goes on (P3) — only a failure after which the runner cannot commit stops it, as today.
- Tests: negative case first; a script is not verified until it has been seen to refuse.
  `bash tests/run_all.sh --fast` after every slice, the full set once at the end.
- Risk tolerance: spikes run without asking; a passing spike never interrupts.
- Autonomy: all slices built in DAG order; interrupts only on the critical set.
- Principles that bear on the slices (in words): a deterministic script decides, never an agent's
  care (P1); the task board is the one place work is handed out (P2); a non-critical failure is
  written to the anomaly journal and does not stop the board (P3); the owner alone changes rules and
  priorities — here, by reordering rows (P4); between a clever and a simple solution take the
  simplest that works, nothing "for later" (P7).

## Premises (`.engine/premises/premise-log.md`, PR-numbers-01…04)

1. **PR-numbers-01** The three numbering sites of `board.py` and the two "own number" sites
   (`_own_number`, `hotfix.py next_number`) are the only places that issue a task number.
   Evidence: `grep -rn "ITEM_FIRST\|RULE_FIRST\|GATE_FIRST\|FIRST_RESERVED\|_own_number"` over
   `.claude/` and `engine.py` (2026-10-11): `board.py` and `hotfix.py:61,211` only. `verified`.
2. **PR-numbers-02** After `pull --rebase` and after a true merge, git alone tells which of two
   same-numbered files appeared first and which side a dependent task came from. Evidence: spike
   `.engine/artifacts/spikes/task-numbers-renumber-git-2026-10-11.{sh,txt}` — rebase: the keeper's
   add-commit is an ancestor of the other's; merge: neither is, the committer time decides; in both
   the renumbered file's add-commit is an ancestor of its own side's dependent and not of the other
   side's; `git log --diff-filter=A -- 'tasks/*/NAME.md'` finds the first appearance of a name
   that has moved between columns. git 2.34.1. `verified`.
3. **PR-numbers-03** `journal.py` can carry one more journal (session files under
   `.engine/journal/<name>/`, a shared file a fold writes, `text()` reading both). Evidence:
   `.claude/hooks/journal.py` `JOURNALS` — four journals declared as data, `add`, `text`, `fold`
   generic over them. `verified` by reading; the tracer does not touch it (S4 does).
4. **PR-numbers-04** (integration) One function of class arithmetic can serve every numbering site
   without changing what else those sites do. Evidence: the tracer bullet S1, which converts all
   five sites (the cross-directory one, `hotfix.py`, included). `unverified` until S1.

## Out of scope (deliberately)

- Renaming any existing task (A7). The open items 801–843 stay where they are; by their number they
  now read as class 8, and the next rule question comes after 843.
- `CLASSES.md` arriving through the inbox. The owner edits it in the branch; the inbox carries tasks
  and answers, and a new kind of owner's word through it is its own task. This departs from design
  741 §5 («через inbox, як будь-яку свою відповідь»); task 401 item 5 dropped those words. Logged
  AUTONOMOUS with its cost to reverse; said in the task's report.
- A cloud session calling `renumber` (the owner's amendment to answer 4).
- Rewriting a number in free text (reports, discussions): only `Залежить від:`, `tasks/.first`,
  the file or folder name and the task's own `# NNN —` heading follow; the map is `tasks/RENUMBERED.md`.
- Classes of more than one digit; a per-clone sub-range; a check "this number is in the wrong class".
- `AGENTS.md`, unless a line fits the 200-line budget.

## Звірка з цілями

- служить: G1 (номери не стикаються й не переповнюють клас без участі людини — runner розводить їх
  сам), G5 (`CLASSES.md` і `RENUMBERED.md` читає людина; відмова називає файл), D2 (кілька сесій на
  одній task board — крок до автономного циклу на сторонньому проєкті).
- вибір між варіантами розв'язав: P7 (продовження класу обчислюється з номера, без налаштування;
  порядок — рядки одного файла), P1 (номер дає скрипт, а не уважність агента), P3 (невдалий
  `renumber` — запис у журнал аномалій, task board іде далі), P2 (номер роздає одне місце).
- не-цілі й обмеження: N3 (паралельне виконання) — не чіпаємо й не будуємо: `renumber` лише
  прибирає наслідок двох клонів, задачі й далі роздає одна task board; інші не-цілі далеко.

## Decisions (agent; two-way doors, logged AUTONOMOUS in escalations.md)

- **K1 A class is one digit.** `number // 100` is the class identifier; its last digit is the class
  (17 → 7, 27 → 7). So classes are 0–9, which is exactly the owner's list; a `CLASSES.md` row with
  another number is an error named by `board.py check`. Rejected: a "continuation" column the code
  parses — a second source for what the number already says. The column exists for the reader only.
- **K2 Class 0 is what was there before classes.** It has a row (so the owner can place it in the
  order) and is never issued: `Клас: 0` is refused like an unknown class.
- **K3 The next number is the successor of the largest in the class, all columns, `done/` too** (the
  owner's wording): gaps are not filled; ordinal 00 is never issued (first is c01), the existing
  600, 700, 800, 900 stay; after c99 comes (c+10)01.
- **K4 An unnumbered inbox file is a task only with a `Клас:` line** (the task's wording); a stray
  `notes.md` is left alone, as today. In a file that carries its number the line is not read for
  numbering ("як зараз").
- **K5 (dropped — simplifier F-e372b498).** A `board.py next-number` command stood here; neither
  the task nor design 741 asks for it and the plan named nobody who would run it. A number is given
  by the five sites and by the inbox, and by nothing else.
- **K6 No `CLASSES.md` → the queue is by number, as today,** and a `Клас:` line is refused (there is
  no table to find it in). The fixed classes (1 for "no class", 4 for the runner's own tasks, 7, 8,
  9) need no table. A class missing from the table queues after the listed ones, by number.
- **K7 The initial row order is 0, 1, 2, …, 9.** Every number on the board is under 1000 today, so
  class order equals number order (A6: the same first task). A continuation (1701) queues with
  class 7, before 800 — the one place the new order differs from "by number"; class 7 is full, so
  the open items written after S1 are 17xx and will stand before the 8xx ones once S3 is in.
- **K8 Who keeps the number:** the file whose add-commit is an ancestor of the other's; neither —
  the earlier committer time; equal — the name. A file never committed is the youngest. A dependent's
  `Залежить від:` follows the renumbered file exactly when that file's add-commit is an ancestor of
  (or is) the dependent's add-commit (PR-numbers-02).
- **K9 `renumber` looks at the whole board,** not one column: two clones can leave one number in
  `done/` and in `todo/`. `board.py check` reports the same clash.
- **K10 `RENUMBERED` is a fifth journal of `journal.py`** (`tasks/RENUMBERED.md`, session files in
  `.engine/journal/renumbered/`): the mechanism board 739 built, not a second one.
- **K11 The runner's step:** `board renumber` right after `sync_branch`, before the inbox is read;
  what it moved is one commit of its own. A failure is an event and an anomaly entry, and the board
  goes on — `board.py check` keeps showing the clash.
- **K14 `renumber` never renames an answered question the runner acts on.** The owner-answer
  perimeter (`local_gate_answers`, `$ACCEPTED`, `owner_actions`, `close_escalations`) knows an
  answer by the file's name and sha256, and the runner lists the answers written on this machine
  BEFORE `sync_branch`. A rename between the two would let an answer written here pass as the
  owner's (P4). So a gate question or an action question that carries any answer is left where it
  is; the perimeter's code is not touched. `tests/test_owner_perimeter.py`: a question answered on
  this machine that is the younger twin is not renamed, is wiped and asked again, no action runs;
  the pass after that renames it. Rejected: carrying both lists across each move (the critic's
  fix) — it edits the guard itself to follow a rename, and a miss there fails open; leaving the
  file alone fails closed. Cost to reverse: one condition and one test.
- **K12 The hotfix follow-up task takes its number from the same function** (class 1), not from its
  own copy of the rule.
- **K13 The documents are a closing step, not a slice:** no code, checked by the text suites
  (`test_owner_terms`, `test_text_hygiene`, `test_context_budget`, `test_project_seeds`).

## Slices (the DAG)

- **S1 `task-class-overflow`** — delivers: one function of class arithmetic for every site that issues a number (A1) · contract out: `class_of`, `next_number` · depends on: — · **TRACER BULLET (build first)**
  In full: the class arithmetic in one new module,
  `.claude/unattended/task_classes.py`, and all five sites that issue a number taking it from there,
  each with its fixed class — open item 7, rule question 8, gate question 9, the runner's own tasks
  (`_own_number`) 4, the hotfix follow-up (`hotfix.py next_number`) 1 (A1, K12). None of them needs
  the table. On an empty board the first numbers become 701/801/901 (K3), so the suites that pin
  `700-`/`800-`/`900-` names move with the slice: `test_board`, `test_board_review`,
  `test_board_runner`, `test_gate_allows`, `test_lesson_queue`, `test_cleanup`, `test_maintain`,
  `test_hotfix`, `test_owner_perimeter`, `test_overseer_fresh` — "nothing else those sites do
  changes" means the text and the column of what they write, not these names.
- **S2 `numbers-class-table`** — delivers: the table of classes, the `Клас:` line and a number for an unnumbered inbox file (A2, A7) · contract out: `parse_classes`, `read_classes`, `queue_key` · depends on: S1
  In full: `tasks/CLASSES.md` (this repository's and the template's,
  seeded by `engine.py` like `tasks/README.md` — an `ownership.txt` row), its reader, the `Клас:`
  line of a task, the number for an unnumbered inbox file, the refusal of an unknown class (A2,
  A7). The refusal has one place: an unnumbered inbox file is not taken (it stays in the inbox, the
  line and the anomaly journal name it, like an unreadable `Режим:`). A file that already carries
  its number is never refused for
  its `Клас:` line — the line is not read there (K4).
- **S3 `numbers-queue-order`** — delivers: the queue in the order of the rows of `CLASSES.md`, for the runner and for the owner's review alike (A5, A6) · contract out: — · depends on: S2
  In full: one order for the runner and for the owner's review:
  `Board.queue` (so `board.py next` and `summary`) and `board_review.plan_section` — which sorts
  `todo/` itself and reads the board from a commit of the work branch, not from the disk — both use
  the one key `queue_key`: `tasks/.first` first, then the rows of `CLASSES.md`, lowest number inside
  a class; dependencies as now (A5, A6). The review feeds the key `src.show("tasks/CLASSES.md")`.
  `tests/test_board_review.py` asserts the plan's order equals `board.py next` after a row is
  moved.
- **S4 `numbers-renumber`** — delivers: `board.py renumber` after a merge left one number on two files (A3, A4) · contract out: — · depends on: S1, S2
  In full: `board.py renumber`, the `renumbered` journal, the inbox
  finding a task by its old name, `check` over the whole board, the runner's step after
  `sync_branch` (A3, A4). The runner's commit of that step carries the move AND its map entry:
  `board_commit` and `commit_journal` add only `tasks/` and `.engine/journal/anomalies` today, so
  the step's path set gains `.engine/journal/renumbered`, and `tests/test_board_runner.py` asserts
  the one commit holds both the renamed file and the entry and leaves the tree clean. `renumber`
  prints each move as `old name → new name`. Known limits of K8, each written into the contract and
  met with an anomaly-journal entry rather than a guess: a task that existed before the clash and
  was edited on the renumbered side to depend on the number keeps pointing at the keeper; a
  dependent that arrives after `renumber` has run — from the same second clone that had not pulled
  yet, or from a third — binds to the keeper. **What `renumber` does not move (K14):** a task in
  `doing/` (it is in hand: its session, its commits and the runner's state name it) and a question
  in `blocked/` that offers the runner an action or closes a gate escalation and carries an answer
  — the clash stays, `check` shows it, the anomaly journal says why, and the next pass moves it once
  the task has left `doing/` or the answer has been acted on or wiped. Also keyed by a task's name
  and stated in the contract: the weekly extra-sessions sum (`board.task_file`) finds a renamed task
  through the same old-name lookup the inbox uses; the `follow-up:` path in `.engine/debt.md` is not
  rewritten (a known limit, named in the map entry's wording). Two clones that create a file of the
  same NAME (`NNN-cleanup-<date>.md`) are an add/add conflict the runner stops on before `renumber`
  runs — unchanged, a limit. Built after S2: both change `import_inbox`.
- **Closing step — documents** (A8): `tasks/README.md` and `templates/project/tasks/README.md`,
  `tasks/TEMPLATE.md` and its template (the optional `Клас:` line), `.claude/unattended/README.md`,
  `.claude/commands/owner-review.md` (its line 90 tells the session to number new tasks "below 800"
  by hand — it points at the unnumbered inbox file with a `Клас:` line instead), `AGENTS.md` if a
  line fits. Also the texts that state a name's shape: `.claude/references/unattended.md`
  (`7NN-open-item-…`), `.claude/references/gate.md` and `docs/ARCHITECTURE.md` (`9NN-gate-escalation`,
  `8NN-rule-proposal`), the comment in `board-runner.sh` — each says "class 7 / 8 / 9" instead. The documents say where the map is read: `tasks/RENUMBERED.md` appears only after a
  `journal.py fold`, which nothing calls by itself — until then `journal.py show renumbered`.

One block (a small feature: one capability, the board's numbering) — no block labels.

## Inter-slice contracts

- S1 → S2: the class arithmetic (`task_classes.py`), below.
- S1 → S4: the same.
- S2 → S3: the table's reader and the queue's key, below.
- S2 → S4: `import_inbox` as S2 leaves it.

S1 gives (`task_classes.py`):
  - `class_of(number: int) -> int` — `number // 100 % 10`, always 0…9.
  - `next_number(taken: Iterable[int], klass: int) -> int` — the successor of the largest member of
    `taken` whose `class_of` is `klass`, in the sequence k01…k99, (k+10)01…(k+10)99, (k+20)01…;
    k01 when `taken` has none of the class. `ValueError` for a class outside 1…9.
  - `OPEN_ITEMS, RULES, GATES = 7, 8, 9`.
  - `OWN, UNCLASSED = 4, 1` — the runner's own tasks; a task nobody gave a class.
  - `board.py`: `Board.taken() -> set[int]` — every number in the four columns.
S2 gives S3 (`task_classes.py`):
  - `parse_classes(text: str) -> tuple[int, ...]` — the class numbers of the rows of a `CLASSES.md`
    text, in its order; `()` for an empty text. A row is a table row whose first cell is an integer.
    Pure: the review hands it text read from a commit.
  - `read_classes(tasks: Path) -> tuple[int, ...]` — `parse_classes` of `tasks/CLASSES.md`; `()`
    when there is no file.
  - `queue_key(classes: tuple[int, ...], first: list[str]) -> Callable[[str], tuple[int, int, int]]`
    — the sort key of a task FILE NAME: its rank in `first` (those not named — after), the rank of
    `class_of(its number)` in `classes` (a class not listed — after the listed), its number. With
    `classes == ()` this is today's order. The order comes from the number alone: a task's `Клас:`
    line never orders it (K4), so `Task.klass` is no part of this contract — it stays inside S2.
S2 gives S4: `import_inbox` as S2 leaves it (S4 adds the old-name lookup in front of the number
  lookup; it does not change how a number is given).

## Integration exit criterion

The tracer S1 runs end to end: the real `board.py open-item` on a synthetic board whose largest
class-7 number is 799 writes `1701-open-item-…md` and never an 8xx file
(`tests/test_task_classes.py`, the slice's contract-test file).
The feature is done when A1–A8 hold, shown by: `tests/test_task_classes.py` (A1), `tests/test_board.py`
(A2, A5, A6, A7),
a new `tests/test_renumber.py` with two real clones and a merge (A3, A4), `tests/test_board_runner.py`
(the runner's step and its own commit), and `bash tests/run_all.sh` green.

## Deferred to later features

- `CLASSES.md` through the inbox — why later: a new road for the owner's word needs the perimeter's
  rules (what the runner wipes, what counts as the owner's) — revisit trigger: the owner asks to
  reorder classes without git.
- `renumber` from a cloud session — why later: the owner's amendment — revisit trigger: cloud
  sessions come back into use.

## Open items requiring human decision

None. Round 2 of the critic did not end in PASS (below); its one blocking objection is a two-way
door and is decided here (K14), logged AUTONOMOUS in `.engine/overseer/escalations.md`.

## Appendix — critic round 1 (FEATURE_CRITIC_REVISE), what was done with it

- O1 (blocking: the review's plan has its own sort and reads git) — fixed: `parse_classes`,
  `queue_key`, `board_review.py` and a review-order test are in S3; `Task.klass` left the contract (N3).
- N1 (the runner's commit would leave the map entry uncommitted) — fixed in S4. N2 (where the map is
  read before a fold) — in the closing step. N4, N5 (S2 too fat; the premise's evidence) — the two
  fixed-class sites moved into S1; where the unknown-class refusal surfaces is stated in S2.
  N6 (suites that pin 700/800/900) — listed in S1. N7 (`owner-review.md`, `ownership.txt`) — in the
  closing step and S2. N8 (limits of K8) — named in S4. N9 (criteria cite no G line each) — they are
  the owner's own test list; the citation stands at feature level in «Звірка з цілями».

## Appendix — critic round 2 (FEATURE_CRITIC_REVISE; the last round)

- O1, in the critic's words: «S4's runner step renames blocked questions between
  `local_gate_answers` and `intake`, while the owner-answer perimeter (`LOCAL_ANSWERS`, `$ACCEPTED`)
  is keyed by file name + sha256, so a locally written answer on a renumbered question is accepted
  as the owner's». Decided by K14: such a question is not renamed at all (fails closed), with the
  negative test the critic asked for. The critic's own fix (carry the lists) is the rejected option.
- N1 (extra-sessions sum, `debt.md`) and N3 (a twin in `doing/`, same-name files) — in S4.
  N2 — the limit reworded. N4 (`queue_key` has no consumer until S3) — left in S2: it is the
  table's reader's neighbour and S3 then changes callers only. N5 — in A2. N6, N7 — logged.
  N8 — K7 reworded.

## Appendix — the simplifier before the slices were cut

- Architecture lens, F-e372b498 (`next-number` is an invented requirement) — applied: K5 dropped.
- Requirements lens, F-5d50f559 (per-session files for `RENUMBERED.md` were written for two
  writers; the owner's amendment left one, the runner) — an owner requirement (task 401 item 6), so
  it is built as written (K10) and the finding stands in `.engine/simplifier/report.md` for the owner.
