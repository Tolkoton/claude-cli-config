#!/usr/bin/env python3
"""Feature business-goals-focus-second as one block: the integration tests that depend on questions (board 202).

Q1: A4 «critic-core §0: an owner requirement or decision is only what has the owner's verbatim words and a
source … Applies to every critic.» mvp-critic does not inherit critic-core (S1 contract, cold reader 2: «it does
not inherit critic-core … so it already reviews everything»). Reading taken (the stricter one): «every critic»
includes mvp-critic, so mvp-critic itself carries the quote rule — it names both sources of an owner decision,
or says it inherits critic-core.

Q2: A12 «proposals 1756–1759 removed from `tasks/proposed/`, one report line each.» The artifact puts this in
the closing step «after S2, not a slice», while the integration exit criterion lists A1–A12. Reading taken:
the closing step belongs to this block's integration — the four proposals are gone and the task's report
names each number. Until the closing step runs this test fails: a finding for the close, not a fault of the code.

Run:   python3 tests/test_business_goals_focus_second_block_disputed.py [<test>]
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import test_business_goals_focus_second_block as block

ROOT = Path(__file__).resolve().parent.parent


def test_A4_mvp_critic_carries_the_quote_rule() -> None:
    mvp = block.read(block.MVP_CRITIC)
    check_sources = all(source in mvp for source in block.SOURCES)
    block.check("mvp-critic names both sources of an owner decision, or inherits critic-core",
                check_sources or "critic-core" in mvp)


def test_A12_proposals_removed_with_a_report_line_each() -> None:
    proposed = ROOT / "tasks/proposed"
    for number in ("1756", "1757", "1758", "1759"):
        left = sorted(p.name for p in proposed.glob(f"{number}-*"))
        block.check(f"proposal {number} is removed from tasks/proposed/", not left, left)
    reports = sorted([*ROOT.glob("tasks/done/202-*/report.md"), *ROOT.glob("tasks/doing/202-*/report.md")])
    block.check("the task's report exists (tasks/done/202-…/report.md)", bool(reports), "no report yet")
    text = reports[0].read_text(encoding="utf-8") if reports else ""
    for number in ("1756", "1757", "1758", "1759"):
        block.check(f"the report names proposal {number}", number in text)


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}

if __name__ == "__main__":
    sys.exit(block.main(sys.argv[1:], TESTS))
