#!/usr/bin/env python3
"""The table of classes (board 401, slice numbers-class-table): the DISPUTED contract tests.

Each case here depends on a question the slice tester put to the sealed contract
`.engine/slices/numbers-class-table.md` and takes the stricter of two honest readings. The file
holds disputed tests only and is not sealed until the slice planner answers:

  Q1  is the tail ` — the board does not take it; the file stays in the inbox` part of the line a
      file refused for its class gets, or are the prefix and the word `Клас` all that is fixed?
  Q2  «the text is written as it came» — are the CR bytes of a CRLF file kept in the task?
  Q3  a row `| 12 |` written twice — two sentences (one per row), or a third for "a class with two rows"?

The undisputed tests, and every helper used here, are in tests/test_task_class_table.py.

Run:   python3 tests/test_task_class_table_disputed.py            # every case
       python3 tests/test_task_class_table_disputed.py <test>     # one case by its name
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

import test_task_class_table as base


def test_q1_the_line_of_a_file_refused_for_its_class_ends_as_every_skipped_line() -> None:
    wrong = {}
    for name, line, table in (("twelve", "Клас: 12", "seed"), ("words", "Клас: три", "seed"), ("no-table", "Клас: 3", None)):
        root = base.new_board("todo/101-a", table=table)
        base.drop(root, f"{name}.md", base.task("Задача", line))
        lines = base.take(root)
        if not (len(lines) == 1 and lines[0].startswith(f"{name}.md skipped: ") and lines[0].endswith(base.TAIL) and len(lines[0]) > len(f"{name}.md skipped: {base.TAIL}")):
            wrong[name] = lines
    base.check("Q1: `Клас: 12`, `Клас: три` and `Клас: 3` without a table — the line is `<name>.md skipped: <why> — the board does not take it; "
               "the file stays in the inbox`, the tail word for word", not wrong, wrong)


def test_q2_a_crlf_file_is_written_with_its_cr_bytes() -> None:
    root = base.new_board("todo/101-a")
    text = base.task("Windows", "Клас: 3").replace("\n", "\r\n")
    base.drop(root, "crlf.md", text)
    lines = base.take(root)
    written = (root / "tasks/todo/301-crlf.md").read_bytes() if (root / "tasks/todo/301-crlf.md").is_file() else b"(no file)"
    base.check("Q2: a file saved with CRLF and taken as 301 is written byte for byte, every CR kept", written == text.encode("utf-8"), (lines, written[:80]))


def test_q3_a_row_outside_0_to_9_written_twice_is_two_sentences() -> None:
    errors = base.classes().table_errors
    got = errors(base.table_of("1", "12", "3", "12"))
    base.check("Q3: the row `| 12 |` twice in a table that is sound otherwise — two sentences, one per such row, and none for a repeated class",
               isinstance(got, list) and len(got) == 2, got)


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}

if __name__ == "__main__":
    sys.exit(base.main(sys.argv[1:], TESTS))
