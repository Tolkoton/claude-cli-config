#!/usr/bin/env python3
"""Feature business-goals-focus as one block: the integration test that depends on a question (board 201).

Q1: A9 «The report says what changed for the owner in plain language, technical terms English.» The
report is written at the task's close (`tasks/done/201-…/report.md`), after this block's integration
step, and «what changed for the owner» has no list in the artifact. Reading taken: the report exists
under the task's folder (in `doing/` or `done/`) and names the three things the owner meets anew — the
stop «Читання цілей», «Ядро» and the mark `[не слова власника]` (the A8 owner-guide words). Until the
report is written this test fails: a finding for the close, not a fault of the code.

Run:   python3 tests/test_business_goals_focus_block_disputed.py [<test>]
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import test_business_goals_focus_block as block

ROOT = Path(__file__).resolve().parent.parent


def test_A9_the_report_names_what_changed_for_the_owner() -> None:
    reports = sorted([*ROOT.glob("tasks/done/201-*/report.md"), *ROOT.glob("tasks/doing/201-*/report.md")])
    block.check("the task's report exists (tasks/done/201-…/report.md)", bool(reports), "no report yet")
    text = reports[0].read_text(encoding="utf-8") if reports else ""
    for word in ("Читання цілей", "Ядро", "[не слова власника]"):
        block.check(f"the report names {word}", word in text)


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}

if __name__ == "__main__":
    sys.exit(block.main(sys.argv[1:], TESTS))
