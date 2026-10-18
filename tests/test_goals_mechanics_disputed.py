#!/usr/bin/env python3
"""goals-mechanics (board 201): the contract test that depends on a question to the contract.

Q1: `goals.py trace` on a sealed document whose `items` raise (a number used twice) — the Seam says
«`items` raising → `REFUSED: …`, exit 3. Then every error as `REFUSED: <sentence>` on stderr, and
ALWAYS one stdout line `elements outside «Пропозиції»: <total>`», and I4's Domain is «every run of
`trace` on a sealed document». Whether ALWAYS covers the run that stops at `items` is the question;
this test takes the reading that it does. Not sealed until the slice planner answers.

Run:   python3 tests/test_goals_mechanics_disputed.py [<test>]
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

import test_goals_mechanics as base


def test_trace_items_raising_still_prints_the_count() -> None:
    doc = base.DOC_CORE + "- G1. Ще раз.\n"
    root = base.project(doc, sealed=True, files={base.TRACE: base.matrix(*base.ALL_STANDING), base.DOMAIN: base.domain(), base.ADR: base.GOOD_ADR})
    r = base.run(base.GOALS, root, "trace")
    base.check("a sealed document with a number twice: REFUSED, exit 3, and the count line still printed",
               r.returncode == 3 and any(line.startswith("REFUSED: ") for line in r.stderr.splitlines())
               and "elements outside «Пропозиції»: 5" in r.stdout.splitlines(), base.out(r))


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}


if __name__ == "__main__":
    sys.exit(base.main(sys.argv[1:], TESTS))
