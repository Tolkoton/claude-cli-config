#!/usr/bin/env python3
"""The table of classes and the `Клас:` line (board 401, slice numbers-class-table): the contract tests.

Written from the sealed contract `.engine/slices/numbers-class-table.md` before the code existed,
by the slice tester. Every expected value here is written by hand from the contract.

  1. the table alone (`.claude/unattended/task_classes.py`): `parse_classes`, `read_classes`,
     `table_errors`, `class_for`, `queue_key`, and the six invariants I1...I6 on inputs chosen
     from their «Domain»;
  2. `Task.klass` and `Task.class_error`, read by `board.parse` (Seam 5: the header only);
  3. the real `board.py import-inbox`, `check`, `summary` and `next` CLI on synthetic boards whose
     `tasks/CLASSES.md` is a copy of the seed (Seams 1, 2, 2a, 2b, 3).

The seed in a real install (Seam 4) is not here: the contract puts it into tests/test_board.py.
The tests that depend on a question to the contract are in tests/test_task_class_table_disputed.py.

Run:   python3 tests/test_task_class_table.py            # every case
       python3 tests/test_task_class_table.py <test>     # one case by its name (test_I1_..., ...)
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from hook_env import hook_env, sandbox_dir
from journals import journal_text

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / ".claude/unattended/board.py"
CLASSES = ROOT / ".claude/unattended/task_classes.py"
SEED = ROOT / "templates/project/tasks/CLASSES.md"
REPO_TABLE = ROOT / "tasks/CLASSES.md"
COLUMNS = ("todo", "doing", "blocked", "done")
ALL = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
ASK = "1. Що?\n   Відповідь:\n"
TAIL = " — the board does not take it; the file stays in the inbox"
BAD_MODE = "«Режим: абищо» — такого режиму немає: ескіз, соло, конвеєр" + TAIL   # the line a numbered file gets today
HEAD = "| Клас | Назва | Що туди йде | Продовження |\n|---|---|---|---|\n"

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700].replace('Error', 'Err.')}")


def by_path(name: str, path: Path) -> ModuleType:
    """A module loaded from its file, the way the suites and the audit runner load board.py: no path is set up."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_loaded: dict[str, ModuleType] = {}


def classes() -> ModuleType:
    # Under a name of its own: registered as `task_classes` it would answer board.py's import for it.
    if "classes" not in _loaded:
        _loaded["classes"] = by_path("task_classes_under_test", CLASSES)
    return _loaded["classes"]


def board_module() -> ModuleType:
    if "board" not in _loaded:
        _loaded["board"] = by_path("board", BOARD)
    return _loaded["board"]


def task(name: str = "Задача", *header: str) -> str:
    """A task as the owner writes one; `header` are the lines of its header (`Клас: 3`, `Режим: соло`)."""
    lines = "".join(f"{line}\n" for line in header)
    return f"# {name}\n\nЗалежить від: —\n{lines}Аудит потрібен: ні\n\n## Що зробити\n- щось для «{name}»\n\n## Готово, коли\n- готово\n\n## Питання до власника\n"


def new_board(*names: str, table: str | None = "seed") -> Path:
    """A synthetic project: the board holds `names` (`<column>/<stem>`), `tasks/CLASSES.md` is a copy of the
    seed (or the text given, or absent for None), and `inbox/` is empty."""
    root = Path(sandbox_dir("class-table-"))
    for column in COLUMNS:
        (root / "tasks" / column).mkdir(parents=True)
        (root / "tasks" / column / ".gitkeep").touch()
    for name in names:
        column, _, stem = name.partition("/")
        if column == "done":
            (root / "tasks/done" / stem).mkdir()
            (root / "tasks/done" / stem / "task.md").write_text(task(stem), encoding="utf-8")
            (root / "tasks/done" / stem / "report.md").write_text("# report\n", encoding="utf-8")
        else:
            (root / "tasks" / column / f"{stem}.md").write_text(task(stem) + (ASK if column == "blocked" else ""), encoding="utf-8")
    if table is not None:
        (root / "tasks/CLASSES.md").write_bytes(SEED.read_bytes() if table == "seed" else table.encode("utf-8"))
    (root / "inbox").mkdir()
    return root


def drop(root: Path, name: str, text: str) -> Path:
    """A file put into the inbox, byte for byte as given (no newline translation)."""
    path = root / "inbox" / name
    path.write_bytes(text.encode("utf-8"))
    return path


def env_of(root: Path) -> dict[str, str]:
    return {k: v for k, v in hook_env(root).items() if not k.startswith("BOARD_") and k not in ("CLAUDE_UNATTENDED_SESSION", "CLAUDECODE")}


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(BOARD), "--root", str(root), *args], cwd=root, capture_output=True, text=True, check=False, env=env_of(root))


def take(root: Path) -> list[str]:
    """One `import-inbox` call; the lines it printed."""
    r = cli(root, "import-inbox", str(root / "inbox"))
    return r.stdout.splitlines() if r.returncode == 0 else [f"exit {r.returncode}: {r.stdout}{r.stderr}"]


def tree(folder: Path) -> dict[str, bytes | None]:
    """Every name under `folder` with its bytes (None for a directory): what «nothing changed» is compared on."""
    return {str(p.relative_to(folder)): (p.read_bytes() if p.is_file() else None) for p in sorted(folder.rglob("*"))}


def todo_of(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "tasks/todo").glob("*.md"))


def inbox_of(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "inbox").iterdir())


def text_of(path: Path) -> str:
    return path.read_bytes().decode("utf-8") if path.is_file() else f"(no file {path.name})"


def entries(journal: str) -> int:
    return sum(1 for line in journal.splitlines() if line.startswith("## "))


def table_of(*cells: str) -> str:
    """A CLASSES.md text: the header, the rule, and one row per first cell given."""
    return "# Класи задач\n\nВступ.\n\n" + HEAD + "".join(f"| {cell} | назва | що йде | — |\n" for cell in cells)


# ------------------------------------------------------------------ 1. the table alone


def test_parse_classes_gives_the_rows_in_the_texts_order() -> None:
    parse = classes().parse_classes
    got = parse(table_of("7", "3", "1", "3"))
    check("Seam 6: rows 7, 3, 1, then 3 again -> (7, 3, 1): the text's order, a repeated class at its first place", got == (7, 3, 1) and isinstance(got, tuple), got)
    got = parse(table_of("9", "0", "5"))
    check("...rows 9, 0, 5 -> (9, 0, 5), not sorted", got == (9, 0, 5), got)
    got = parse(table_of("3", "12", "7", "3", "1"))
    check("...a table with a defect keeps its sound rows: 3, 12, 7, 3, 1 -> (3, 7, 1)", got == (3, 7, 1), got)


def test_parse_classes_a_row_is_a_first_cell_of_ascii_digits_0_to_9() -> None:
    parse = classes().parse_classes
    by_hand: list[tuple[str, tuple[int, ...]]] = [
        ("| 3 | назва | що | — |\n", (3,)),
        ("| 03 | назва |\n", (3,)),                                  # `03` is 3
        ("|7|назва|\n", (7,)),                                      # no spaces round the cell
        ("| \t 5\t | назва |\n", (5,)),                             # spaces and tabs are stripped
        ("| 0 | до класів |\n| 9 | gates |\n", (0, 9)),             # both ends of 0...9
        ("| 3 | 12 | 7 |\n", (3,)),                                 # the first cell only
        ("| +3 | x |\n| 3. | x |\n| №3 | x |\n", ()),               # not rows
        ("| 12 | x |\n| 10 | x |\n| 100 | x |\n", ()),              # another integer
        ("| -1 | x |\n| три | x |\n|  | x |\n|| 3 |\n", ()),        # no integer; an empty first cell
        ("| ٣ | x |\n", ()),                                        # a digit that is not ASCII is prose
        (HEAD, ()),                                                 # the header and the `|---|` rule
        ("Клас 3 — gates.\n3 | назва |\n  | 4 | з відступом |\n", ()),   # prose; no leading pipe; a line that does not START with `|`
        ("", ()),
        ("# Класи задач\n\nТаблиці ще немає.\n", ()),
    ]
    got = [(text, parse(text)) for text, _ in by_hand]
    wrong = [(text, result) for (text, want), (_, result) in zip(by_hand, got, strict=True) if result != want or not isinstance(result, tuple)]
    check(f"{len(by_hand)} texts: `03` is 3; `+3`, `3.`, `№3`, `12`, `-1`, a word, `٣`, the header, the rule and prose give nothing; () without rows", not wrong, wrong)


def test_read_classes_reads_the_boards_table() -> None:
    read = classes().read_classes
    root = new_board(table=table_of("7", "3", "1"))
    got = read(root / "tasks")
    check("read_classes(<tasks>): the rows of <tasks>/CLASSES.md in its order — (7, 3, 1)", got == (7, 3, 1), got)
    got = read(new_board(table=None) / "tasks")
    check("...and () when the board has no CLASSES.md", got == (), got)


def test_repository_table_is_exactly_the_ten_classes_and_sound() -> None:
    mod = classes()
    got = mod.read_classes(ROOT / "tasks")
    check("this repository's tasks/CLASSES.md: sorted, exactly 0...9 (the order of its rows is the owner's)", tuple(sorted(got)) == ALL and len(got) == 10, got)
    errors = mod.table_errors(REPO_TABLE.read_text(encoding="utf-8"))
    check("...and table_errors of it is []", errors == [], errors)


def test_seed_table_is_exactly_0_to_9_in_order() -> None:
    got = classes().parse_classes(SEED.read_text(encoding="utf-8"))
    check("the seed templates/project/tasks/CLASSES.md -> exactly (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)", got == ALL, got)


def test_table_errors_one_sentence_per_defect() -> None:
    errors = classes().table_errors

    def sentences(text: str) -> int | str:
        got = errors(text)
        return len(got) if isinstance(got, list) and all(isinstance(s, str) and s.strip() for s in got) else f"not sentences: {got!r}"

    got = sentences(table_of("1", "3", "12", "7", "3"))
    check("a row `| 12 |` and class 3 twice -> two sentences", got == 2, got)
    got = sentences(table_of("3", "1", "3", "3"))
    check("class 3 in three rows -> one sentence: one per class, not per row", got == 1, got)
    got = sentences(table_of("3", "1", "3", "1"))
    check("classes 3 and 1 twice each -> two sentences", got == 2, got)
    got = sentences(table_of("12", "40", "1"))
    check("rows `| 12 |` and `| 40 |` -> two sentences: one per such row", got == 2, got)
    got = sentences(table_of("1", "010"))
    check("`| 010 |` is the integer 10, outside 0...9 -> one sentence", got == 1, got)
    got = sentences(table_of("03", "3"))
    check("`| 03 |` and `| 3 |` are class 3 twice -> one sentence", got == 1, got)
    sound = [errors(table_of(*(str(n) for n in ALL))), errors(table_of("7", "3", "1")), errors(""), errors("# Класи задач\n\nТаблиці ще немає.\n")]
    check("a sound table (0...9, and 7, 3, 1), the empty text and a text without rows -> []", sound == [[], [], [], []], sound)
    prose = errors(table_of("1", "-1", "+12", "слово", "٣", "3.") + "| -1 | x |\n| +12 | x |\n")
    check("a first cell that is not digits only (`-1`, `+12`, a word, `٣`, `3.`) is prose, twice or not: no sentence", prose == [], prose)


def test_class_for_refuses_with_a_value_error_that_names_the_class() -> None:
    class_for = classes().class_for
    wrong: list[str] = []
    for wanted, table in ((0, ALL), (0, (0,)), (12, ALL), (5, (7, 3, 1)), (2, (3,)), (10, ALL), (-1, ALL), (3, ()), (1, ()), (9, ()), (0, ())):
        try:
            wrong.append(f"class_for({wanted}, {table}) gave {class_for(wanted, table)}")
        except ValueError as error:
            if str(wanted) not in str(error):
                wrong.append(f"class_for({wanted}, {table}): the message does not say the class: {error}")
    check("class 0 (listed or not), a class that is not in the table (12, 5 of (7, 3, 1), 10, -1) and every class when the table is (): "
          "ValueError, and its message says the class", not wrong, wrong)
    fine = [class_for(3, ALL), class_for(1, (1,)), class_for(9, (9, 0)), class_for(7, (7, 3, 1))]
    check("...and nothing else raises: 3 of 0...9, 1 of (1,), 9 of (9, 0), 7 of (7, 3, 1) answer", fine == [3, 1, 9, 7], fine)


def test_queue_key_takes_the_classes_in_the_order_of_the_rows() -> None:
    key = classes().queue_key((7, 3, 1), [])
    got = sorted(["301-z.md", "501-w.md", "1701-y.md", "799-x.md"], key=key)
    check("Seam 6: with classes (7, 3, 1) — 799-x and 1701-y before 301-z (a continuation ranks with its class), 501-w (not listed) after all",
          got == ["799-x.md", "1701-y.md", "301-z.md", "501-w.md"], got)
    got = sorted(["101-a.md", "501-w.md", "302-b.md", "301-z.md", "2701-c.md", "799-x.md"], key=key)
    check("...and six names: class 7 (799, 2701), class 3 (301, 302), class 1 (101), then the unlisted 501",
          got == ["799-x.md", "2701-c.md", "301-z.md", "302-b.md", "101-a.md", "501-w.md"], got)


def test_queue_key_is_first_rank_then_class_rank_then_number() -> None:
    key = classes().queue_key((7, 3, 1), ["301-z.md", "notes.md", "301-z.md"])
    by_hand = {
        "301-z.md": (0, 1, 301),      # twice in `first`: the index of its first place
        "notes.md": (1, 3, 0),        # no number -> number 0, class 0, which is not listed -> len(classes)
        "799-x.md": (3, 0, 799),      # not in `first` -> len(first)
        "1701-y.md": (3, 0, 1701),
        "101-a.md": (3, 2, 101),
        "501-w.md": (3, 3, 501),
        "304-old": (3, 1, 304),       # a done/ folder name
        "12-fix.md": (3, 3, 0),       # two digits are no number
        "0099-q.md": (3, 3, 99),      # class 0, not listed
    }
    got = {name: tuple(key(name)) for name in by_hand}
    check("the key of nine names with classes (7, 3, 1) and first [301-z, notes, 301-z]: (index in first or 3, index of the class or 3, number)", got == by_hand, got)
    bare = classes().queue_key((), [])
    got_bare = [tuple(bare("301-z.md")), tuple(bare("notes.md"))]
    check("...and with no table and no first: (0, 0, 301) and (0, 0, 0)", got_bare == [(0, 0, 301), (0, 0, 0)], got_bare)


# ------------------------------------------------------------------ the invariants (inputs chosen from the «Domain»)


def test_I1_parse_classes_gives_only_classes_each_once() -> None:
    parse = classes().parse_classes
    # (text, the classes by hand — None where the contract does not fix the answer and only the rule is asserted)
    cases: list[tuple[str, tuple[int, ...] | None]] = [
        ("", ()), ("\n", ()), ("|", ()), ("||", ()), ("| |", ()), ("|\n|\n", ()),
        ("| 12 |\n", ()), ("| 10 |\n| 99 |\n| 100 |\n", ()),                       # every integer first cell, were it returned
        ("| 3 |\n| 3 |\n", (3,)), ("| 3 |\n| 03 |\n| 003 |\n", (3,)),             # the same class twice, written three ways
        ("| 0 |\n| 9 |\n| 0 |\n| 9 |\n", (0, 9)),                                 # both edges, each repeated
        ("| 9 |\n| 8 |\n| 7 |\n| 6 |\n| 5 |\n| 4 |\n| 3 |\n| 2 |\n| 1 |\n| 0 |\n", (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)),
        ("| 1 |\n| 12 |\n| 1 |\n| 2 |\n", (1, 2)),                                # a sound row, a bad one, a repeat
        ("| 000000000000000000000000000007 |\n", (7,)),                           # digits only, the value 7
        ("| 99999999999999999999999999999 |\n", ()),
        ("| ٣ |\n| ³ |\n| ３ |\n| Ⅲ |\n", ()),                                    # digits that are not ASCII
        ("| -0 |\n| +0 |\n| 0.0 |\n| 1e0 |\n| 0x1 |\n| 1_0 |\n", ()),
        ("| 3 | x |\r\n| 4 | y |\r\n", (3, 4)),                                   # a file saved with CRLF
        ("| 5 | останній рядок без нового рядка |", (5,)),
        ("| 3 | 3 | 3 |\n", (3,)),
        (table_of("7", "3", "1", "3") + table_of("1", "2"), (7, 3, 1, 2)),        # two tables in one text
        ("| 3\n|4\n", None), ("|3|\r|4|\r", None), ("| 3 |\x0b| 4 |\x0c| 5 |\u2028| 6 |", None), ("|\t|\x00|9|", None),
        ("| 3  | x |\n| 4 | y |\n", None), ("|" * 500 + "\n" + "| 1 |" * 50, None),
    ]
    wrong = []
    for text, want in cases:
        got = parse(text)
        lawful = isinstance(got, tuple) and all(type(n) is int and 0 <= n <= 9 for n in got) and len(set(got)) == len(got)
        if not lawful or (want is not None and got != want):
            wrong.append((text[:60], got))
    check(f"I1: on {len(cases)} texts — empty, a lone pipe, `| 12 |`, a class three times as 3, 03 and 003, both edges repeated, digits that are not "
          "ASCII, CRLF — every member is an integer 0...9 and none repeats", not wrong, wrong)


def test_I2_inside_a_class_the_smaller_number_sorts_first() -> None:
    queue_key = classes().queue_key
    # (classes, first, the name with the smaller number, the other — both of one class, both absent from `first`)
    cases: list[tuple[tuple[int, ...], list[str], str, str]] = [
        ((7, 3, 1), [], "799-x.md", "1701-y.md"),                 # as text 1701 sorts before 799
        ((), [], "799-x.md", "1701-y.md"),                        # no table
        ((3,), [], "799-b.md", "1701-a.md"),                      # the class is not listed; the names sort the other way
        ((7,), [], "2701-a.md", "10701-b.md"),                    # as text 10701 sorts before 2701
        (ALL, ["101-q.md"], "305-zz.md", "1301-aa.md"),           # a `first` that names neither
        ((9, 8, 7, 6, 5, 4, 3, 2, 1, 0), ["305-zz.md", "305-zz.md"], "301-b.md", "302-a.md"),
        ((1,), [], "101-b.md", "102-a.md"),                       # neighbours
        ((9, 0), [], "notes.md", "005-x.md"),                     # a name without a number counts as number 0, class 0
        ((), ["x.md"], "12-fix.md", "099-b.md"),                  # two digits are no number: 0 against 99
        ((0,), [], "000-zero.md", "099-last.md"),                 # zero written out
        ((3, 7), [], "304-old", "1304-new"),                      # done/ folder names
        ((4,), [], "401-a.md", "99401-a.md"),                     # far up
    ]
    wrong = []
    for table, first, smaller, larger in cases:
        key = queue_key(table, first)
        if not key(smaller) < key(larger) or sorted([larger, smaller], key=key) != [smaller, larger]:
            wrong.append((table, first, smaller, larger, key(smaller), key(larger)))
    check(f"I2: on {len(cases)} pairs of one class — 799 and 1701, 2701 and 10701, a class that is not listed, no table, a name without a number — "
          "the smaller number sorts first", not wrong, wrong)


def test_I3_with_no_table_the_key_is_todays_order() -> None:
    queue_key = classes().queue_key
    # (names, first, the names sorted by (index in first or len(first), number) — by hand; equal keys keep the order given)
    cases: list[tuple[list[str], list[str], list[str]]] = [
        (["1701-a.md", "800-b.md", "799-c.md", "101-d.md"], [], ["101-d.md", "799-c.md", "800-b.md", "1701-a.md"]),   # ranked by class_of, 1701 would precede 800
        (["900-a.md", "1001-b.md", "899-c.md"], ["999-zz.md"], ["899-c.md", "900-a.md", "1001-b.md"]),                # a `first` that names none of them
        (["301-a.md", "notes.md", "1701-b.md", "205-c.md", "005-d.md"], ["1701-b.md", "205-c.md", "1701-b.md"],
         ["1701-b.md", "205-c.md", "notes.md", "005-d.md", "301-a.md"]),                                               # a name twice in `first`; a name without a number
        (["101-a.md", "notes.md"], ["101-a.md", "notes.md"], ["101-a.md", "notes.md"]),
        (["notes.md", "101-a.md"], ["101-a.md", "notes.md"], ["101-a.md", "notes.md"]),                                # a name without a number in `first`
        (["b.md", "12-a.md", "000-c.md"], [], ["b.md", "12-a.md", "000-c.md"]),                                        # three names of number 0: equal keys
        (["2701-x.md", "10701-y.md", "701-z.md", "304-old", "1304-new"], [], ["304-old", "701-z.md", "1304-new", "2701-x.md", "10701-y.md"]),
        (["501-a.md"], ["501-a.md"], ["501-a.md"]),
        ([], [], []), ([], ["101-a.md"], []),
    ]
    wrong = []
    for names, first, want in cases:
        got = sorted(names, key=queue_key((), first))
        if got != want:
            wrong.append((names, first, got))
    check(f"I3: on {len(cases)} lists with classes == () — 1701 beside 800, a name twice in first, names without a number, the empty list — "
          "the order is by (index in first, number)", not wrong, wrong)


def test_I4_a_name_in_first_sorts_before_every_name_that_is_not() -> None:
    queue_key = classes().queue_key
    # (classes, first, a name that is in first, a name that is not)
    cases: list[tuple[tuple[int, ...], list[str], str, str]] = [
        ((7, 3, 1), ["301-z.md"], "301-z.md", "799-x.md"),                    # the other's class stands earlier in the table
        ((7, 3, 1), ["101-a.md"], "101-a.md", "701-x.md"),                    # the last class of the table against the first
        ((1,), ["1701-y.md"], "1701-y.md", "101-a.md"),                       # an unlisted class and a larger number, in first
        ((3,), ["501-w.md", "301-a.md", "501-w.md"], "501-w.md", "301-b.md"),
        ((), ["901-a.md"], "901-a.md", "001-b.md"),                           # no table
        ((7,), ["a.md", "b.md", "902-c.md"], "902-c.md", "701-a.md"),         # the last place of first
        (ALL, ["9999-z.md"], "9999-z.md", "notes.md"),                        # the other has number 0, the first class of the table
        ((0,), ["901-a.md", "901-a.md"], "901-a.md", "notes.md"),             # the other has number 0 and a listed class
        ((9, 8, 7), ["notes.md"], "notes.md", "901-a.md"),                    # a name without a number, in first
        ((3, 1), ["1304-new"], "1304-new", "101-old"),                        # done/ folder names
    ]
    wrong = []
    for table, first, named, other in cases:
        key = queue_key(table, first)
        if not key(named) < key(other) or sorted([other, named], key=key) != [named, other]:
            wrong.append((table, first, named, other, key(named), key(other)))
    check(f"I4: on {len(cases)} pairs — the other's class earlier in the table, a smaller number, no table, the last place of first, a name without "
          "a number — the name in first sorts first", not wrong, wrong)


def test_I5_class_for_never_invents_a_class() -> None:
    class_for = classes().class_for
    tables: list[tuple[int, ...]] = [(), (0,), (3,), (1, 9), (7, 3, 1), (9, 8, 7, 6, 5, 4, 3, 2, 1, 0), ALL]
    wanted_all = [-10**6, -3, -1, 0, 1, 2, 3, 5, 9, 10, 11, 12, 13, 100, 101, 301, 10**9]
    # The calls that must answer, by hand: `wanted` is 1...9 and stands in the table.
    answers = {(3, (3,)), (1, (1, 9)), (9, (1, 9)), (7, (7, 3, 1)), (3, (7, 3, 1)), (1, (7, 3, 1)),
               *((n, (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)) for n in (1, 2, 3, 5, 9)), *((n, ALL) for n in (1, 2, 3, 5, 9))}
    wrong = []
    for table in tables:
        for wanted in wanted_all:
            try:
                got = class_for(wanted, table)
            except ValueError:
                if (wanted, table) in answers:
                    wrong.append(f"class_for({wanted}, {table}) refused a class that is 1...9 and in the table")
                continue
            if got != wanted or type(got) is not int or wanted not in table or not 1 <= wanted <= 9:
                wrong.append(f"class_for({wanted}, {table}) gave {got!r}")
    check(f"I5: on {len(tables) * len(wanted_all)} calls — no table, a table of class 0 only, both edges 1 and 9, 0, 10, 12, a negative, far up — "
          "the result is `wanted`, in the table and 1...9; the named class that is there is accepted", not wrong, wrong)
    # A lawful call after one that was refused, and two lawful calls one after the other.
    try:
        class_for(12, ALL)
    except ValueError:
        pass
    after = [class_for(1, ALL), class_for(9, ALL), class_for(9, ALL)]
    check("I5: after a refused class 12 the same table still answers 1, then 9, then 9 again", after == [1, 9, 9], after)


def test_I6_the_tables_order_is_the_order_of_classes() -> None:
    queue_key = classes().queue_key
    down = (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
    # (classes, first, the name that sorts first, the other) — both absent from `first`; classes checked by hand
    cases: list[tuple[tuple[int, ...], list[str], str, str]] = [
        ((7, 3, 1), [], "1701-y.md", "301-z.md"),                 # both listed: 7 stands before 3, the number is larger
        ((7, 3, 1), [], "399-z.md", "101-a.md"),                  # 3 before 1
        ((7, 3, 1), [], "799-x.md", "101-a.md"),                  # the first row against the last
        ((7, 3, 1), ["999-q.md", "999-q.md"], "2701-y.md", "301-z.md"),
        (down, [], "901-a.md", "101-b.md"),                       # the table upside down
        (down, [], "101-b.md", "notes.md"),                       # class 0 listed last; a name without a number is class 0
        (down, [], "1801-a.md", "701-b.md"),
        ((0, 9), [], "notes.md", "901-a.md"),                     # class 0 listed first
        ((5, 4), ["notes.md"], "599-a.md", "401-b.md"),           # neighbours, the higher digit first
        ((7, 3, 1), [], "101-a.md", "001-b.md"),                  # listed against not listed: class 0 is missing, its number is smaller
        ((7, 3, 1), ["999-q.md"], "301-z.md", "201-w.md"),        # ...class 2 is missing
        ((3,), [], "1301-a.md", "201-b.md"),                      # one row
        ((2,), [], "201-x.md", "notes.md"),                       # a name without a number, its class 0 not listed
        ((9,), [], "9901-x.md", "12-fix.md"),
        ((1, 3), [], "104-old", "303-new"),                       # done/ folder names
    ]
    wrong = []
    for table, first, earlier, later in cases:
        key = queue_key(table, first)
        if not key(earlier) < key(later) or sorted([later, earlier], key=key) != [earlier, later]:
            wrong.append((table, first, earlier, later, key(earlier), key(later)))
    check(f"I6: on {len(cases)} pairs — a table out of numeric order, upside down, of one row, a continuation, a class that is not listed — "
          "the class that stands earlier sorts first, and a listed class before one that is not", not wrong, wrong)


# ------------------------------------------------------------------ 2. Task.klass and Task.class_error


def klass_of(text: str) -> tuple[object, object]:
    parsed = board_module().parse(text)
    return parsed.klass, parsed.class_error


def named_no_class(text: str) -> bool:
    klass, error = klass_of(text)
    return klass is None and isinstance(error, str) and bool(error.strip())


def test_klass_is_the_integer_of_the_header_line() -> None:
    by_hand: list[tuple[str, int]] = [("Клас: 3", 3), ("Клас:3", 3), ("Клас: 03", 3), ("Клас:\t 7 \t", 7), ("Клас: 0", 0), ("Клас: 9", 9), ("Клас: 12", 12)]
    got = [(line, klass_of(task("Задача", line))) for line, _ in by_hand]
    check("`Клас: 3`, `Клас:3`, `Клас: 03` are 3; spaces and tabs round the value are stripped; 0, 9 and 12 are read as they stand — class_error \"\"",
          got == [(line, (want, "")) for line, want in by_hand], got)
    under_the_title = klass_of("# 301 — Задача\nКлас: 5\n\n## Що зробити\n- щось\n")
    check("...a line straight under the title, in a task with no other header line", under_the_title == (5, ""), under_the_title)
    none = klass_of(task("Задача"))
    check("...and a task without the line: klass None, class_error \"\"", none == (None, ""), none)


def test_klass_is_read_from_the_header_only() -> None:
    below = task("Задача", "Клас: 3").replace("- щось для «Задача»\n", "- щось\nКлас: 5\n")
    check("Seam 5: a `Клас: 5` line below the first `## ` heading (in «Що зробити») is not the task's class: 3, no error", klass_of(below) == (3, ""), klass_of(below))
    commented = task("Задача", "<!--", "Клас: 4", "-->", "Клас: 3", "<!-- Клас: 6", "Клас: 7 -->")
    check("...a `Клас:` line inside an HTML comment is not read: 3, no error", klass_of(commented) == (3, ""), klass_of(commented))
    both = task("Задача", "<!--", "Клас: 4", "-->", "Клас: 3") + "Клас: 5\n\n## Ще розділ\nКлас: 6\n"
    check("...a comment above and two lines under headings: still 3, no error", klass_of(both) == (3, ""), klass_of(both))
    only_below = task("Задача").replace("- щось для «Задача»\n", "Клас: 5\n")
    only_comment = task("Задача", "<!--", "Клас: 4", "-->")
    got = [klass_of(only_below), klass_of(only_comment)]
    check("...and with no header line, the one below the heading or in the comment gives no class and no error", got == [(None, ""), (None, "")], got)


def test_klass_line_begins_with_exactly_the_word() -> None:
    text = task("Задача", "  Клас: 4", "- Клас: 5", "клас: 6", "Клас: 3", "\tКлас: 7", "* Клас: 8", "КЛАС: 9", "> Клас: 2")
    check("an indented line, a list item, `клас:` and `КЛАС:` are no line: beside them `Клас: 3` is the one line — 3, no error", klass_of(text) == (3, ""), klass_of(text))
    alone = [klass_of(task("Задача", line)) for line in ("  Клас: 3", "- Клас: 3", "клас: 3")]
    check("...and each of `  Клас: 3`, `- Клас: 3`, `клас: 3` alone gives no class and no error", alone == [(None, ""), (None, ""), (None, "")], alone)
    check("...while the line itself is read (the same task with `Клас: 3`)", klass_of(task("Задача", "Клас: 3")) == (3, ""), klass_of(task("Задача", "Клас: 3")))


def test_two_class_lines_are_a_class_error() -> None:
    texts = {"two different": task("Задача", "Клас: 3", "Клас: 4"), "the same twice": task("Задача", "Клас: 3", "Клас: 3"),
             "apart": task("Задача", "Клас: 3", "Режим: соло", "Клас: 3"), "three": task("Задача", "Клас: 1", "Клас: 2", "Клас: 3"),
             "one sound, one empty": task("Задача", "Клас: 3", "Клас:")}
    wrong = {name: klass_of(text) for name, text in texts.items() if not named_no_class(text)}
    check("two or more `Клас:` lines in the header — different, the same twice, apart, three, one of them empty — klass None and a class_error", not wrong, wrong)


def test_a_value_that_is_not_digits_only_is_a_class_error() -> None:
    values = ["три", "+3", "3.", "3 (gates)", "٣", "-1", "3,5", "3 4", "№3", "0x3", "**3**", "³"]
    wrong = {value: klass_of(task("Задача", f"Клас: {value}")) for value in values if not named_no_class(task("Задача", f"Клас: {value}"))}
    check(f"{len(values)} values — «три», `+3`, `3.`, `3 (gates)`, `٣` (a digit that is not ASCII) — klass None and a class_error", not wrong, wrong)
    empty = {"at the end of the header": task("Задача", "Клас:"), "spaces only": task("Задача", "Клас:   \t"),
             "before `Режим: соло`": task("Задача", "Клас:", "Режим: соло"), "before a digit line": task("Задача", "Клас:", "3"),
             "before a blank line and `3`": "# Задача\n\nКлас:\n\n3\n\n## Що зробити\n- щось\n"}
    wrong = {name: klass_of(text) for name, text in empty.items() if not named_no_class(text)}
    check("an EMPTY value is a class_error — the value never runs on into the next line (`Режим: соло`, a line `3`)", not wrong, wrong)


def test_klass_in_a_file_saved_with_crlf() -> None:
    text = task("Задача", "Клас: 3").replace("\n", "\r\n")
    check("`Клас: 3` in a text whose every line ends with CRLF is class 3, no error", klass_of(text) == (3, ""), klass_of(text))
    spaced = task("Задача", "Клас: 07 \t").replace("\n", "\r\n")
    check("...and `Клас: 07 <tab>` before the CRLF is 7", klass_of(spaced) == (7, ""), klass_of(spaced))
    empty = task("Задача", "Клас:", "Режим: соло").replace("\n", "\r\n")
    check("...while an empty value in a CRLF file is still a class_error", named_no_class(empty), klass_of(empty))


# ------------------------------------------------------------------ 3. the inbox: an unnumbered file with the line


def ten_and_one() -> tuple[Path, list[str], dict[str, str]]:
    """The owner's case: ten class-3 files and one class-7 file in one call, on a board with no class-3 number and blocked/799-x."""
    root = new_board("blocked/799-x", "todo/101-a", "done/250-b")
    texts = {f"a{n:02d}": task(f"Задача a{n:02d}", "Клас: 3") for n in range(1, 11)} | {"b-open": task("Відкрите", "Клас: 7")}
    for name, text in texts.items():
        drop(root, f"{name}.md", text)
    return root, take(root), texts


def test_ten_class_3_files_become_301_to_310() -> None:
    root, lines, texts = ten_and_one()
    want = [f"a{n:02d}.md imported: tasks/todo/3{n:02d}-a{n:02d}.md" for n in range(1, 11)]
    check("ten files a01.md...a10.md with `Клас: 3`, no class-3 number on the board: an `imported` line for each, 301-a01 ... 310-a10, in name order",
          [line for line in lines if line.startswith("a")] == want, lines)
    wrong = [n for n in range(1, 11) if text_of(root / f"tasks/todo/3{n:02d}-a{n:02d}.md") != texts[f"a{n:02d}"]]
    check("...each written to tasks/todo/ with its own text, as it came", not wrong, (wrong, todo_of(root)))
    check("...and the inbox is empty", inbox_of(root) == [], inbox_of(root))


def test_a_class_7_file_of_the_same_call_continues_after_799() -> None:
    root, lines, texts = ten_and_one()
    check("in the same call as the ten, a file with `Клас: 7` beside blocked/799-x.md: `b-open.md imported: tasks/todo/1701-b-open.md`, the last line",
          lines[-1:] == ["b-open.md imported: tasks/todo/1701-b-open.md"] and len(lines) == 11, lines)
    check("...written with its text", text_of(root / "tasks/todo/1701-b-open.md") == texts["b-open"], todo_of(root))
    want = sorted(["101-a.md", "1701-b-open.md", *(f"3{n:02d}-a{n:02d}.md" for n in range(1, 11))])
    check("...todo/ holds the eleven and the task that was there: no number given twice, none in class 8", todo_of(root) == want, todo_of(root))
    check("...and blocked/799-x.md is where it was", (root / "tasks/blocked/799-x.md").is_file())


def test_a_number_in_done_counts() -> None:
    root = new_board("done/304-old", "todo/101-a", "blocked/603-y")
    text = task("Пізніша", "Клас: 3")
    drop(root, "later.md", text)
    lines = take(root)
    check("done/304-old/ the only class-3 number: `later.md imported: tasks/todo/305-later.md`", lines == ["later.md imported: tasks/todo/305-later.md"], lines)
    check("...the task is tasks/todo/305-later.md with its text, the inbox empty", text_of(root / "tasks/todo/305-later.md") == text and inbox_of(root) == [], (todo_of(root), inbox_of(root)))


def test_seam_2a_a_numbered_file_of_the_same_call_keeps_its_number() -> None:
    root = new_board("todo/101-a")
    unnumbered, numbered = task("Без номера", "Клас: 3"), task("301 — З номером")
    drop(root, "a.md", unnumbered)
    drop(root, "301-foo.md", numbered)
    lines = take(root)
    check("Seam 2a: a.md (`Клас: 3`) and 301-foo.md in one call: two `imported` lines, the numbered file's first",
          lines == ["301-foo.md imported: tasks/todo/301-foo.md", "a.md imported: tasks/todo/302-a.md"], lines)
    check("...todo/301-foo.md and todo/302-a.md both exist, each with its own text",
          text_of(root / "tasks/todo/301-foo.md") == numbered and text_of(root / "tasks/todo/302-a.md") == unnumbered, todo_of(root))
    check("...and the inbox is empty", inbox_of(root) == [], inbox_of(root))


def test_seam_2b_a_numbered_file_that_stays_in_the_inbox_keeps_its_number() -> None:
    root = new_board("todo/101-a")
    unnumbered, bad, good = task("Без номера", "Клас: 3"), task("301 — З номером", "Режим: абищо"), task("301 — З номером", "Режим: соло")
    drop(root, "a.md", unnumbered)
    drop(root, "301-foo.md", bad)
    lines = take(root)
    check("Seam 2b: 301-foo.md with `Режим: абищо` is skipped and still in the inbox",
          lines[:1] == [f"301-foo.md skipped: {BAD_MODE}"] and inbox_of(root) == ["301-foo.md"] and not (root / "tasks/todo/301-foo.md").exists(), (lines, inbox_of(root)))
    check("...and a.md (`Клас: 3`) of the same call becomes tasks/todo/302-a.md, not 301",
          lines[1:] == ["a.md imported: tasks/todo/302-a.md"] and text_of(root / "tasks/todo/302-a.md") == unnumbered, (lines, todo_of(root)))
    drop(root, "301-foo.md", good)
    lines = take(root)
    check("...after the mode line is corrected a second call imports 301-foo.md", lines == ["301-foo.md imported: tasks/todo/301-foo.md"], lines)
    check("...and todo/301-foo.md stands beside todo/302-a.md, both texts intact",
          text_of(root / "tasks/todo/301-foo.md") == good and text_of(root / "tasks/todo/302-a.md") == unnumbered and todo_of(root) == ["101-a.md", "301-foo.md", "302-a.md"],
          todo_of(root))


def test_a_crlf_file_is_taken_in_class_3() -> None:
    root = new_board("todo/101-a")
    text = task("Windows", "Клас: 3").replace("\n", "\r\n")
    drop(root, "crlf.md", text)
    lines = take(root)
    check("`Клас: 3` in a file saved with CRLF: `crlf.md imported: tasks/todo/301-crlf.md`", lines == ["crlf.md imported: tasks/todo/301-crlf.md"], lines)
    written = text_of(root / "tasks/todo/301-crlf.md")
    check("...the task is written with its text (line ends aside) and the inbox is empty",
          written.replace("\r\n", "\n") == text.replace("\r\n", "\n") and inbox_of(root) == [], (written[:120], inbox_of(root)))


def test_the_placeholder_of_the_first_line_gets_the_number() -> None:
    root = new_board("todo/101-a")
    rest = ("\nЗалежить від: —\nКлас: 3\nАудит потрібен: ні\n\n## Що зробити\n- замінити NNN у назві файла NNN-name.md\n# NNN — інше\n\n"
            "## Готово, коли\n- NNN лишилось у тексті\n\n## Питання до власника\n")
    drop(root, "named.md", "# NNN — Назва\n" + rest)
    lines = take(root)
    check("a file whose first line is `# NNN — Назва` is taken as 301", lines == ["named.md imported: tasks/todo/301-named.md"], lines)
    written = text_of(root / "tasks/todo/301-named.md")
    check("...its first line is `# 301 — Назва`", written.split("\n")[0] == "# 301 — Назва", written[:80])
    check("...and the rest is byte for byte — `NNN` further down and the line `# NNN — інше` untouched", written == "# 301 — Назва\n" + rest, written)


# ------------------------------------------------------------------ Seam 1: «refused» means nothing moved


def refused(name: str, text: str, table: str | None = "seed", word: str = "Клас") -> None:
    """Seam 1's three assertions for one refused file: nothing under tasks/ changed (names and bytes), the inbox
    file is there byte for byte, the journal entry is written once after TWO imports — and the line is printed."""
    root = new_board("todo/101-a", "todo/301-b", "doing/250-c", "blocked/799-x", "done/304-old", table=table)
    (root / "tasks/.first").write_text("301-b.md\n", encoding="utf-8")
    dropped = drop(root, f"{name}.md", text)
    before = tree(root / "tasks")
    first_lines = take(root)
    first_journal = journal_text(root, "anomalies")
    second_lines = take(root)
    said = [line for line in first_lines if line.startswith(f"{name}.md ")]
    check(f"{name}.md: the line begins `{name}.md skipped:` and carries the word `{word}`",
          len(said) == 1 and said[0].startswith(f"{name}.md skipped: ") and word in said[0] and len(first_lines) == 1, first_lines)
    check("...nothing changed under tasks/: the same names and the same bytes in the four columns and the root, .first and CLASSES.md included",
          tree(root / "tasks") == before, sorted(set(tree(root / "tasks")) ^ set(before)))
    check("...the file is still in the inbox, byte for byte", inbox_of(root) == [f"{name}.md"] and dropped.read_bytes() == text.encode("utf-8"), inbox_of(root))
    check("...one anomaly-journal entry names the file, under .engine/journal/anomalies/",
          f"{name}.md" in first_journal and entries(first_journal) == 1 and any((root / ".engine/journal/anomalies").glob("*.md")), first_journal)
    check("...the second import prints the line again and writes no second entry",
          second_lines == first_lines and journal_text(root, "anomalies") == first_journal, (second_lines, journal_text(root, "anomalies")[len(first_journal):]))


def test_refused_a_class_the_table_does_not_have() -> None:
    refused("twelve", task("Задача", "Клас: 12"))
    refused("five", task("Задача", "Клас: 5"), table=table_of("7", "3", "1"))


def test_refused_class_0() -> None:
    refused("zero", task("Задача", "Клас: 0"))


def test_refused_a_class_named_in_words() -> None:
    refused("words", task("Задача", "Клас: три"))


def test_refused_an_empty_value_before_a_mode_line() -> None:
    refused("empty", task("Задача", "Клас:", "Режим: соло"))


def test_refused_two_class_lines() -> None:
    refused("twice", task("Задача", "Клас: 3", "Клас: 4"))


def test_refused_a_named_class_on_a_board_without_the_table() -> None:
    refused("no-table", task("Задача", "Клас: 3"), table=None)


def test_refused_a_value_with_a_note_after_the_digit() -> None:
    refused("noted", task("Задача", "Клас: 3 (gates)"))


def test_refused_a_digit_that_is_not_ascii() -> None:
    refused("arabic", task("Задача", "Клас: ٣"))


def test_an_unreadable_mode_is_skipped_as_a_numbered_file_is() -> None:
    root = new_board("todo/101-a", "todo/301-b")
    text = task("Задача", "Клас: 3", "Режим: абищо")
    dropped = drop(root, "x.md", text)
    before = tree(root / "tasks")
    lines = take(root)
    journal = journal_text(root, "anomalies")
    check("x.md with `Клас: 3` and `Режим: абищо`: skipped with the mode's reason — the line a numbered file gets today", lines == [f"x.md skipped: {BAD_MODE}"], lines)
    check("...still in the inbox, todo/ and the rest of tasks/ unchanged", dropped.read_bytes() == text.encode("utf-8") and tree(root / "tasks") == before, todo_of(root))
    check("...the journal names the file in one entry", "x.md" in journal and entries(journal) == 1, journal)
    again = take(root)
    check("...and a second import prints the line and writes no second entry", again == lines and journal_text(root, "anomalies") == journal, again)


def test_a_bad_mode_wins_over_a_class_error() -> None:
    root = new_board("todo/101-a")
    text = task("Задача", "Клас: три", "Режим: абищо")
    dropped = drop(root, "y.md", text)
    before = tree(root / "tasks")
    lines = take(root)
    check("y.md with `Клас: три` and `Режим: абищо` is skipped for its MODE — one line, the mode's (the first case that applies wins)",
          lines == [f"y.md skipped: {BAD_MODE}"], lines)
    check("...still in the inbox, nothing under tasks/ changed", dropped.read_bytes() == text.encode("utf-8") and tree(root / "tasks") == before, todo_of(root))


# ------------------------------------------------------------------ Seam 3: today's inbox behaviour is untouched (`keeps`)


def test_an_unnumbered_file_without_the_line_is_passed_over() -> None:
    root = new_board("todo/101-a")
    plain, bad_mode = task("Нотатки"), task("Нотатки", "Режим: абищо")
    drop(root, "notes.md", plain)
    drop(root, "memo.md", bad_mode)
    before = tree(root / "tasks")
    lines = take(root)
    check("notes.md without the `Клас:` line: no line is printed", lines == [], lines)
    check("...it is still in the inbox, byte for byte, and nothing under tasks/ changed",
          text_of(root / "inbox/notes.md") == plain and tree(root / "tasks") == before, (inbox_of(root), todo_of(root)))
    check("...and memo.md — no `Клас:` line and a bad `Режим:` — is passed over the same way: in the inbox, no journal entry",
          text_of(root / "inbox/memo.md") == bad_mode and journal_text(root, "anomalies").count("memo.md") == 0, journal_text(root, "anomalies"))


def test_a_numbered_file_does_not_have_its_class_line_read() -> None:
    root = new_board("todo/101-a")
    text = task("105 — Задача", "Клас: 12")
    drop(root, "105-x.md", text)
    lines = take(root)
    check("105-x.md carrying `Клас: 12` is task 105 in todo/, as today", lines == ["105-x.md imported: tasks/todo/105-x.md"], lines)
    check("...byte for byte, and the inbox is empty", text_of(root / "tasks/todo/105-x.md") == text and inbox_of(root) == [], (todo_of(root), inbox_of(root)))


def test_a_numbered_file_with_a_class_error_is_taken_and_offered() -> None:
    root = new_board()
    text = task("106 — Задача", "Клас: три")
    drop(root, "106-y.md", text)
    lines = take(root)
    check("106-y.md carrying `Клас: три`: an `imported` line and no `skipped:` line", lines == ["106-y.md imported: tasks/todo/106-y.md"], lines)
    check("...task 106 in todo/ with its text", text_of(root / "tasks/todo/106-y.md") == text and inbox_of(root) == [], (todo_of(root), inbox_of(root)))
    check("...no journal entry", "106-y.md" not in journal_text(root, "anomalies"), journal_text(root, "anomalies"))
    offered = cli(root, "next")
    check("...`board.py next` offers it", offered.stdout.strip() == "tasks/todo/106-y.md", offered.stdout + offered.stderr)
    summary = cli(root, "summary").stdout
    check("...and `summary` prints no «не береться» for it", "не береться" not in summary and "106-y.md" in summary, summary)


# ------------------------------------------------------------------ `check` and `summary`


def test_check_and_summary_print_the_tables_errors() -> None:
    prefix = "ПОМИЛКА: tasks/CLASSES.md: "
    root = new_board("todo/101-a", table=SEED.read_text(encoding="utf-8") + "| 12 | Зайвий | такого класу немає | — |\n")
    checked, summary = cli(root, "check"), cli(root, "summary")
    said = [line for line in checked.stdout.splitlines() if line.startswith(prefix)]
    check("`check` on a board whose table has a row `| 12 |`: exit 1 and one line `ПОМИЛКА: tasks/CLASSES.md: <sentence>`",
          checked.returncode == 1 and len(said) == 1 and bool(said[0][len(prefix):].strip()), (checked.returncode, checked.stdout + checked.stderr))
    check("...and `summary` on that board prints the same line", len(said) == 1 and said[0] in summary.stdout.splitlines(), summary.stdout + summary.stderr)

    root = new_board("todo/020-one", "todo/020-two", table=table_of("1", "3", "12", "7", "3"))
    for command in ("check", "summary"):
        lines = cli(root, command).stdout.splitlines()
        table_at = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        twin_at = [i for i, line in enumerate(lines) if line.startswith("ПОМИЛКА: один номер 020")]
        check(f"`{command}`: a row `| 12 |` and class 3 twice give two lines, after the line of the duplicate number 020",
              len(table_at) == 2 and len(twin_at) == 1 and twin_at[0] < table_at[0], lines)

    sound = cli(new_board("todo/101-a"), "check")
    check("`check` on the seed: exit 0 and no line", sound.returncode == 0 and "ПОМИЛКА" not in sound.stdout, sound.stdout + sound.stderr)
    bare = new_board("todo/101-a", table=None)
    absent = cli(bare, "check")
    check("...and a board without the file has no such line, in `check` or in `summary`",
          absent.returncode == 0 and "CLASSES.md" not in absent.stdout + cli(bare, "summary").stdout, absent.stdout + absent.stderr)


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}


def main(argv: list[str], tests: dict[str, Callable[[], None]] | None = None) -> int:
    global FAIL
    cases = TESTS if tests is None else tests
    wanted = argv or list(cases)
    unknown = [name for name in wanted if name not in cases]
    if unknown:
        print(f"no case named {', '.join(unknown)}; the cases: {', '.join(cases)}")
        return 2
    for name in wanted:
        print(name)
        try:
            cases[name]()
        # gate-allow: the suite's own runner must count a case that raises as a failed case and still run the next one
        except Exception as error:  # noqa: BLE001
            FAIL += 1
            last = traceback.extract_tb(error.__traceback__)[-1]
            print(f"  FAIL {name} raised {type(error).__name__.replace('Error', 'Err.')}: {str(error)[:300]}   ({Path(last.filename).name}:{last.lineno})")
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
