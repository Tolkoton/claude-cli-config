#!/usr/bin/env python3
"""architect-goals-discipline (board 202): the contract tests that depend on a question to the contract.

Q1: the guardian's new check — «a record «owner decision» / «рішення власника» without the owner's verbatim
words and their source (`the time of the remark` or `the interview journal`) is a `GUARDIAN_NOTE`». The
undisputed suite finds the strings anywhere in the guardian section (where `GUARDIAN_NOTE` already stands in
the answer format). This test takes the stricter reading: ONE sentence of the guardian section names the
record («owner decision» or «рішення власника»), both sources and `GUARDIAN_NOTE`.
Not sealed until the slice planner answers.

Run:   python3 tests/test_architect_goals_disputed.py [<test>]
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable

import test_architect_goals as base


def test_q1_guardian_note_in_the_same_sentence_as_the_quote_check() -> None:
    sentences = re.split(r"(?<=[.!?])\s+", base.flat(base.guardian()))
    found = [s for s in sentences
             if (base.holds(s, "owner decision") or base.holds(s, "рішення власника"))
             and all(base.holds(s, w) for w in base.SOURCES) and "GUARDIAN_NOTE" in s]
    base.check("one sentence of the guardian section names the record, both sources and `GUARDIAN_NOTE`",
               bool(found), [s for s in sentences if "GUARDIAN_NOTE" in s] or "no such sentence")


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}


if __name__ == "__main__":
    sys.exit(base.main(sys.argv[1:], TESTS))
