#!/usr/bin/env python3
"""A task's number comes from its class (board 401, slice task-class-overflow): the contract tests.

Written from the sealed contract `.engine/slices/task-class-overflow.md` before the code existed,
by the slice tester. Every expected number here is written by hand from the contract.

  1. the arithmetic alone (`.claude/unattended/task_classes.py`): `class_of`, `next_number`, the
     boundary c99 -> (c+10)01, a gap that is not filled, the refusal of a class outside 1...9, and
     the four invariants I1...I4 on inputs chosen from their «Domain»;
  2. `Board.taken` and `board.py` loaded by path in a FRESH interpreter started from a foreign cwd
     (in-process an import this suite made itself would hide a missing path insert — so this suite
     never puts `.claude/unattended` on `sys.path` and never registers `task_classes`);
  3. the real sites on synthetic boards seeded with file NAMES — the `open-item` CLI, the real
     `rule_question` and `gate_question`, the `cleanup-task` and `maintain-task` CLI — the
     assertion being the name of the file written.

The hotfix follow-up is not here: the contract puts it into the existing case of tests/test_hotfix.py.

Run:   python3 tests/test_task_classes.py            # every case
       python3 tests/test_task_classes.py <test>     # one case by its name (test_I1_..., ...)
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import traceback
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from hook_env import hook_env, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / ".claude/unattended/board.py"
CLASSES = ROOT / ".claude/unattended/task_classes.py"
COLUMNS = ("todo", "doing", "blocked", "done")
TASK = "# Задача\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Що зробити\n- щось\n\n## Готово, коли\n- готово\n\n## Питання до власника\n{ask}"
ASK = "1. Що?\n   Відповідь:\n"

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


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


def new_board(*names: str) -> Path:
    """A synthetic project whose board holds `names` (`<column>/<stem>`); a task of blocked/ asks its owner."""
    root = Path(sandbox_dir("task-classes-"))
    for column in COLUMNS:
        (root / "tasks" / column).mkdir(parents=True)
        (root / "tasks" / column / ".gitkeep").touch()
    for name in names:
        column, _, stem = name.partition("/")
        if column == "done":
            (root / "tasks/done" / stem).mkdir()
            (root / "tasks/done" / stem / "task.md").write_text(TASK.format(ask=""), encoding="utf-8")
            (root / "tasks/done" / stem / "report.md").write_text("# report\n", encoding="utf-8")
        else:
            (root / "tasks" / column / f"{stem}.md").write_text(TASK.format(ask=ASK if column == "blocked" else ""), encoding="utf-8")
    return root


def env_of(root: Path) -> dict[str, str]:
    return {k: v for k, v in hook_env(root).items() if not k.startswith("BOARD_") and k not in ("CLAUDE_UNATTENDED_SESSION", "CLAUDECODE")}


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(BOARD), "--root", str(root), *args], cwd=root, capture_output=True, text=True, check=False, env=env_of(root))


def names_of(root: Path) -> list[str]:
    """Every numbered name of the board, as `<column>/<name>`."""
    return sorted(f"{column}/{p.name}" for column in COLUMNS for p in (root / "tasks" / column).glob("[0-9]*"))


def numbers_of(root: Path) -> list[int]:
    return sorted(int(name.split("/")[1].split("-")[0]) for name in names_of(root))


def today_board() -> Path:
    """Today's board as the contract describes it: 799 and 801-843 present, 901 the largest of class 9."""
    return new_board("done/799-open-item-last", *(f"todo/{n}-open-item-n{n}" for n in range(801, 844)), "blocked/901-gate-escalation-old")


def open_item(root: Path, title: str) -> str:
    r = cli(root, "open-item", "--to", "todo", "--title", title, "--what", "щось сталося", "--do", "зробити")
    return r.stdout.strip() if r.returncode == 0 else f"exit {r.returncode}: {r.stdout}{r.stderr}"


def ask_rule(root: Path) -> str:
    b = board_module()
    made = b.rule_question(b.Board(root / "tasks"), "ab12cd34", "Show the RED before the GREEN.", "audit 06 caught it twice", "lesson #ab12cd34", "", "a" * 64)
    return f"{Path(made).parent.name}/{Path(made).name}" if made is not None else "None"


def ask_gate(root: Path) -> str:
    b = board_module()
    made = b.gate_question(b.Board(root / "tasks"), "2026-10-03T10:15:00Z", blocks=3, slice_name="tax", files=["src/a.py"],
                           reasons=["LINT FAILED (ruff check):"], report=".claude/state/gate/last-report.json")
    return f"{Path(made).parent.name}/{Path(made).name}" if made is not None else "None"


def runner_board(*names: str) -> Path:
    """A board on which the runner may place its own tasks: the project has /maintain and the simplifier."""
    root = new_board(*names)
    for rel in (".claude/commands/maintain.md", ".claude/hooks/simplifier.py", ".claude/project.env"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("", encoding="utf-8")
    return root


def hundreds_digit(number: int) -> int:
    """The class of a number read off its decimal text — not by the formula under test."""
    return int(str(number).zfill(3)[-3])


# ------------------------------------------------------------------ 1. the arithmetic alone


def test_class_of_is_the_last_digit_of_the_hundreds() -> None:
    class_of = classes().class_of
    by_hand = {0: 0, 7: 0, 99: 0, 100: 1, 101: 1, 199: 1, 401: 4, 600: 6, 700: 7, 783: 7, 799: 7, 800: 8, 843: 8, 999: 9, 1000: 0, 1001: 0,
               1701: 7, 1799: 7, 1801: 8, 2701: 7, 9999: 9, 10901: 9, 123456: 4}
    got = {n: class_of(n) for n in by_hand}
    check("class_of: 783 and 1701 and 2701 are class 7, 10901 class 9, 1000 class 0 — always 0...9", got == by_hand, got)


def test_first_number_of_a_class_with_none_taken() -> None:
    nxt = classes().next_number
    got = [nxt(set(), 7), nxt([], 1), nxt(frozenset(), 9), nxt({603, 250, 1001}, 4), nxt({801, 843, 901}, 7)]
    check("no number of the class: the first is c01 — 701, 101, 901; 401 beside 603; 701 beside 801-901", got == [701, 101, 901, 401, 701], got)


def test_successor_of_the_largest_inside_a_hundred() -> None:
    nxt = classes().next_number
    got = [nxt({783}, 7), nxt({401}, 4), nxt({801, 843, 820}, 8), nxt({798}, 7), nxt({1701}, 7), nxt({700}, 7)]
    check("m + 1 while the ordinal is under 99: 783 -> 784, 401 -> 402, 843 -> 844, 798 -> 799, 1701 -> 1702, 700 -> 701",
          got == [784, 402, 844, 799, 1702, 701], got)


def test_gap_under_the_largest_is_not_filled() -> None:
    nxt = classes().next_number
    got = [nxt({701, 703}, 7), nxt({801, 843}, 8), nxt({905}, 9)]
    check("701 and 703 -> 704, never 702; 801 and 843 -> 844; 905 alone -> 906, not 901", got == [704, 844, 906], got)


def test_boundary_c99_continues_in_the_identifier_plus_ten() -> None:
    nxt = classes().next_number
    got = [nxt({799}, 7), nxt({1799}, 7), nxt({9999}, 9), nxt({899}, 8), nxt({999}, 9), nxt({199}, 1), nxt({499}, 4), nxt({784, 799}, 7)]
    check("799 -> 1701, 1799 -> 2701, 9999 -> 10901, 899 -> 1801, 999 -> 1901, 199 -> 1101, 499 -> 1401",
          got == [1701, 2701, 10901, 1801, 1901, 1101, 1401, 1701], got)


def test_todays_board_numbers_from_the_function() -> None:
    nxt = classes().next_number
    taken = {799, *range(801, 844)}
    got = (nxt(taken, 7), nxt(taken, 8))
    check("a board that holds 799 AND 801-843: the open item is 1701, the rule question 844", got == (1701, 844), got)


def test_value_error_names_the_class_outside_1_to_9() -> None:
    nxt = classes().next_number
    wrong: list[str] = []
    for klass, taken in ((0, set()), (10, set()), (0, {701, 99}), (10, {799, 1001}), (-1, {101}), (17, {1701})):
        try:
            wrong.append(f"class {klass} gave {nxt(taken, klass)}")
        except ValueError as error:
            if str(klass) not in str(error):
                wrong.append(f"class {klass}: the message does not name it: {error}")
    check("classes 0 and 10 (and -1, 17) are refused with a ValueError that names the class, the board empty or not", not wrong, wrong)
    # Nothing else fails: the classes at both ends of 1...9 answer, `taken` empty.
    check("...and classes 1 and 9 are not refused", (nxt(set(), 1), nxt(set(), 9)) == (101, 901))


# ------------------------------------------------------------------ the invariants (inputs chosen from the «Domain»)

# (taken, k) — every `taken` a finite set of non-negative integers, every k in 1...9.
EDGES: list[tuple[frozenset[int], int]] = [
    *((frozenset(), k) for k in range(1, 10)),                       # the empty set, every class
    *((frozenset({0}), k) for k in range(1, 10)),                    # zero alone
    *((frozenset({k * 100 + 99}), k) for k in range(1, 10)),         # the last ordinal of the first hundred
    *((frozenset({k * 100}), k) for k in range(1, 10)),              # the old c00 of every class
    (frozenset({799, *range(800, 844)}), 7), (frozenset({799, *range(800, 844)}), 8),   # 799 beside the next class's hundred
    (frozenset({1799}), 7), (frozenset({1700}), 7), (frozenset({9999}), 9), (frozenset({10999}), 9), (frozenset({99999}), 9),
    (frozenset({99}), 1), (frozenset({1000}), 1), (frozenset({99, 1000, 1099}), 9),      # class 0 only
    (frozenset({10**12 + 799}), 7),                                  # far up
    (frozenset({199, 1199}), 1), (frozenset({399, 1399, 2399, 401}), 3), (frozenset({399, 1399, 2399, 401}), 4),
    (frozenset({799, 1701}), 7), (frozenset({784, 1701}), 7), (frozenset({701, 703}), 7),
]


def test_I1_the_number_belongs_to_the_class_asked_for() -> None:
    mod = classes()
    wrong = []
    for taken, k in EDGES:
        got = mod.next_number(taken, k)
        if mod.class_of(got) != k or hundreds_digit(got) != k:
            wrong.append((sorted(taken)[:4], k, got))
    check(f"I1: on {len(EDGES)} boards — empty, zero, c99, c00, 799 beside 800-843, far up — the number is of class k", not wrong, wrong)
    # A lawful call after one that was refused, and two lawful calls one after the other on the growing set.
    held = {799}
    try:
        mod.next_number(held, 0)
    except ValueError:
        pass
    first = mod.next_number(held, 7)
    second = mod.next_number(held | {first}, 7)
    third = mod.next_number(held | {first, second}, 8)
    check("I1: after a refused class 0 the same board still answers in class 7, twice, and then in class 8",
          [hundreds_digit(first), hundreds_digit(second), hundreds_digit(third)] == [7, 7, 8]
          and [mod.class_of(first), mod.class_of(second), mod.class_of(third)] == [7, 7, 8], (first, second, third))


def test_I2_the_number_is_new_and_above_every_number_of_its_class() -> None:
    nxt = classes().next_number
    # (taken, k, the largest member of taken of class k — found by hand; None when the class is empty)
    cases: list[tuple[set[int], int, int | None]] = [
        (set(), 7, None), ({0}, 1, None), ({800, 801}, 7, None),
        ({701, 703}, 7, 703), ({701, 799, 1701, 1705}, 7, 1705), ({784, 1701}, 7, 1701), ({799, 1701}, 7, 1701),
        ({2701, 799, 1799}, 7, 2701), ({799, 800}, 7, 799), ({799, 800}, 8, 800), ({799, *range(800, 844)}, 8, 843),
        ({700}, 7, 700), ({9999, 999, 1999}, 9, 9999), ({199, 101, 1100}, 1, 1100), ({401, 603, 1401, 499}, 4, 1401),
        ({10**12 + 799, 799}, 7, 10**12 + 799), ({899, 1801, 1899, 2801}, 8, 2801),
    ]
    wrong = []
    for taken, k, largest in cases:
        got = nxt(taken, k)
        if got in taken or (largest is not None and got <= largest):
            wrong.append((sorted(taken)[:5], k, got))
    check(f"I2: on {len(cases)} boards — a gap, a continuation begun early, the naive answer already taken — the number is not in "
          "`taken` and is above the largest of its class", not wrong, wrong)
    # Issued one after another, every number is new: four from 798 cross the boundary without a repeat.
    held, given = {798}, []
    for _ in range(4):
        given.append(nxt(held, 7))
        held.add(given[-1])
    check("I2: four numbers in a row from 798 are four different numbers, each above the one before", len(set(given)) == 4 and given == sorted(given)
          and given[0] > 798, given)


def test_I3_the_ordinal_00_is_never_given() -> None:
    nxt = classes().next_number
    more: list[tuple[frozenset[int], int]] = [(frozenset({799, 1700}), 7), (frozenset({1699}), 6), (frozenset({600, 700, 800, 900}), 8),
                                              (frozenset({899, 900}), 8), (frozenset({99, 100}), 1), (frozenset({2799, 1799, 799}), 7)]
    wrong = [(sorted(taken)[:4], k, got) for taken, k in [*EDGES, *more] if (got := nxt(taken, k)) % 100 == 0]
    check(f"I3: on {len(EDGES) + len(more)} boards — an empty class, c99, 1799, 9999, the old 600-900 — the ordinal is never 00", not wrong, wrong)


def test_I4_numbers_of_other_classes_do_not_matter() -> None:
    nxt = classes().next_number
    # (taken, k, numbers of OTHER classes to add — each checked by hand: its hundreds digit is not k)
    cases: list[tuple[set[int], int, set[int]]] = [
        (set(), 7, {0, 99, 800, 899, 999, 1601, 1801, 10**6}),
        ({783}, 7, {600, 800, 843, 1801, 2899, 9999}),
        ({799}, 7, {800, 801, 1601, 1800, 1801}),
        ({401}, 4, {399, 500, 603, 699, 1500}),
        ({101, 103}, 1, {201, 1001, 1201, 9901}),
        ({999}, 9, {1001, 1899, 10001, 10801}),
        ({799, 843}, 8, {901, 1701, 1799, 2701}),
        (set(), 4, {1, 99, 300, 399, 500, 603, 699, 700, 999}),
        ({0, 1000}, 1, {2, 99, 1099, 10099}),
    ]
    wrong = []
    for taken, k, others in cases:
        alone, beside = nxt(taken, k), nxt(taken | others, k)
        half = set(sorted(others)[: len(others) // 2])
        in_two_steps = nxt((taken | half) | (others - half), k)
        if not alone == beside == in_two_steps:
            wrong.append((sorted(taken), k, alone, beside, in_two_steps))
    check(f"I4: on {len(cases)} boards the answer for class k is the same with numbers of other classes added — below it, above it, "
          "in the next hundred, far up", not wrong, wrong)


# ------------------------------------------------------------------ 2. Board.taken, and board.py loaded by path


def test_board_taken_is_every_number_of_the_four_columns() -> None:
    root = new_board("todo/101-a", "todo/1701-open-item-far", "doing/250-b", "blocked/603-y", "blocked/844-rule-proposal-z", "done/401-x", "done/099-old")
    b = board_module()
    taken = b.Board(root / "tasks").taken()
    check("Board.taken: a set with the numbers of todo/, doing/, blocked/ and done/ together", taken == {101, 1701, 250, 603, 844, 401, 99} and isinstance(taken, set), taken)
    check("...and of an empty board the empty set", b.Board(new_board() / "tasks").taken() == set())


FRESH = """
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("board", sys.argv[1])
board = importlib.util.module_from_spec(spec)
sys.modules["board"] = board
spec.loader.exec_module(board)
made = board.rule_question(board.Board(Path(sys.argv[2]) / "tasks"), "ab12cd34", "A rule.", "why", "lesson #ab12cd34", "", "a" * 64)
print("WROTE", made.name)
"""


def test_board_loaded_by_path_from_a_foreign_cwd_numbers_a_task() -> None:
    root = new_board()
    cwd = tempfile.mkdtemp(prefix="task-classes-cwd-", dir=sandbox_dir("task-classes-"))
    env = {k: v for k, v in env_of(root).items() if k != "PYTHONPATH" or os.environ.get("HOOKCOV_DIR")}
    r = subprocess.run([sys.executable, "-c", FRESH, str(BOARD), str(root)], cwd=cwd, capture_output=True, text=True, check=False, env=env)
    # The interpreter's own error is cut to its last line: the suite reports a failed case, whatever the cause.
    said = (r.stdout + r.stderr).strip().splitlines()[-1:] or ["(nothing)"]
    check("a fresh interpreter in a temporary cwd loads board.py by path — no path set up — and it imports cleanly", r.returncode == 0, said[0].replace("Error", "Err."))
    check("...and the board loaded so gives the first rule question the number 801", r.stdout.strip().startswith("WROTE 801-rule-proposal-"), r.stdout.strip()[:200])


# ------------------------------------------------------------------ 3. the real sites


def test_open_item_cli_seventeen_calls_from_783() -> None:
    root = new_board("todo/783-open-item-x")
    said = [open_item(root, f"Відкритий пункт номер {n}") for n in range(1, 18)]
    want = [*range(784, 800), 1701]
    numbers = [int(Path(line).name.split("-")[0]) if line.startswith("tasks/todo/") and Path(line).name.split("-")[0].isdigit() else line for line in said]
    check("seventeen `open-item --to todo` calls on a board with 783: the names printed are 784...799, then 1701", numbers == want, numbers)
    check("...every one of them an open item written to todo/", all("-open-item-" in line and (root / line).is_file() for line in said), said)
    check("...the board holds 783...799 and 1701 and nothing else; no file appears in 800-899", numbers_of(root) == [*range(783, 800), 1701], numbers_of(root))


def test_rule_question_after_899_is_1801() -> None:
    root = new_board("done/899-rule-proposal-old")
    made = ask_rule(root)
    check("rule_question on a board with 899: blocked/1801-rule-proposal-...", made.startswith("blocked/1801-rule-proposal-"), made)
    check("...and nothing is written in 900-999: the board holds 899 and 1801", numbers_of(root) == [899, 1801], names_of(root))


def test_gate_question_after_999_is_1901() -> None:
    root = new_board("done/999-gate-escalation-old")
    made = ask_gate(root)
    check("gate_question on a board with 999: blocked/1901-gate-escalation-...", made.startswith("blocked/1901-gate-escalation-"), made)
    check("...and nothing is written in 1000-1099: the board holds 999 and 1901", numbers_of(root) == [999, 1901], names_of(root))


def test_todays_board_open_item_is_1701() -> None:
    root = today_board()
    said = open_item(root, "Ще один відкритий пункт")
    check("today's board (799, 801-843, 901): the open item is tasks/todo/1701-open-item-...", said.startswith("tasks/todo/1701-open-item-") and (root / said).is_file(), said)
    check("...and the board gained that one number only", numbers_of(root) == [799, *range(801, 844), 901, 1701], numbers_of(root))


def test_todays_board_rule_question_is_844() -> None:
    root = today_board()
    made = ask_rule(root)
    check("today's board (799, 801-843, 901): the rule question is blocked/844-rule-proposal-...", made.startswith("blocked/844-rule-proposal-"), made)
    check("...and the board gained that one number only", numbers_of(root) == [799, *range(801, 845), 901], numbers_of(root))


def test_todays_board_gate_question_is_902() -> None:
    root = today_board()
    made = ask_gate(root)
    check("today's board (799, 801-843, 901): the gate question is blocked/902-gate-escalation-...", made.startswith("blocked/902-gate-escalation-"), made)
    check("...and the board gained that one number only", numbers_of(root) == [799, *range(801, 844), 901, 902], numbers_of(root))


def test_runner_task_with_no_class_4_number_is_401() -> None:
    for command, kind in (("cleanup-task", "cleanup"), ("maintain-task", "maintain")):
        root = runner_board("done/040-old")
        r = cli(root, command, "--today", "2026-10-05")
        check(f"{command}: no class-4 number on the board -> tasks/todo/401-{kind}-2026-10-05.md",
              r.stdout.strip() == f"tasks/todo/401-{kind}-2026-10-05.md" and (root / "tasks/todo" / f"401-{kind}-2026-10-05.md").is_file(), r.stdout + r.stderr)


def test_runner_task_counts_done_and_not_a_foreign_class() -> None:
    for command, kind in (("cleanup-task", "cleanup"), ("maintain-task", "maintain")):
        root = runner_board("done/401-x", "blocked/603-y")
        r = cli(root, command, "--today", "2026-10-05")
        check(f"{command}: done/401-x/ and blocked/603-y.md present -> tasks/todo/402-{kind}-2026-10-05.md (not 401, not 604)",
              r.stdout.strip() == f"tasks/todo/402-{kind}-2026-10-05.md" and (root / "tasks/todo" / f"402-{kind}-2026-10-05.md").is_file(), r.stdout + r.stderr)


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}


def main(argv: list[str]) -> int:
    global FAIL
    wanted = argv or list(TESTS)
    unknown = [name for name in wanted if name not in TESTS]
    if unknown:
        print(f"no case named {', '.join(unknown)}; the cases: {', '.join(TESTS)}")
        return 2
    for name in wanted:
        print(name)
        try:
            TESTS[name]()
        # gate-allow: the suite's own runner must count a case that raises as a failed case and still run the next one
        except Exception as error:  # noqa: BLE001
            FAIL += 1
            last = traceback.extract_tb(error.__traceback__)[-1]
            print(f"  FAIL {name} raised {type(error).__name__.replace('Error', 'Err.')}: {str(error)[:300]}   ({Path(last.filename).name}:{last.lineno})")
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
