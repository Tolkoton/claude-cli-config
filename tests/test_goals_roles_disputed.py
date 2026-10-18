#!/usr/bin/env python3
"""goals-roles (board 201): the contract tests that depend on a question to the contract.

Q1: Seam 5 places «Читання цілей» «inside the M1 section before the line that begins M1's design
(`M1 починається з ядра` or its English form)». The English form is not written; this test takes
`M1 починається з ядра`, or `M1 starts|begins with|from the core`, and the M1 section as the text
from the first heading naming M1 to the first heading naming M2.
Q2: «the pipeline line names the analyst's guard of the goals» — no string is given; this test
takes the word `guardian` on the pipeline line of `/business-analyst` in both AGENTS.md files.
Not sealed until the slice planner answers.

Run:   python3 tests/test_goals_roles_disputed.py [<test>]
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable

import test_goals_roles as base

DESIGN_LINE = re.compile(r"M1 починається з ядра|M1 (?:starts|begins) (?:with|from) the core", re.IGNORECASE)
HEADING = re.compile(r"^#{1,6}\s")


def m1_section() -> str:
    lines = base.text(base.ARCHITECT).splitlines()
    start = next((i for i, line in enumerate(lines) if HEADING.match(line) and re.search(r"\bM1\b", line)), None)
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        if body and HEADING.match(line) and re.search(r"\bM2\b", line):
            break
        body.append(line)
    return base.flat(" ".join(body))


def test_seam5_architect_reading_of_goals_inside_m1_before_its_design() -> None:
    section = m1_section()
    stop = section.find("«Читання цілей»")
    design = DESIGN_LINE.search(section)
    check_ok = stop >= 0 and design is not None and stop < design.start()
    base.check("inside the M1 section, «Читання цілей» stands before the line that begins M1's design",
               check_ok, {"stop at": stop, "design at": design.start() if design else None, "section": section[:300]})


def test_agents_pipeline_line_names_the_guardian() -> None:
    for path in (base.ROOT / "AGENTS.md", base.ROOT / "templates/project/AGENTS.md"):
        line = next((row for row in base.text(path).splitlines() if row.startswith("`/business-analyst`")), "")
        base.check(f"{path.relative_to(base.ROOT)}: the pipeline line of /business-analyst names `guardian`", "guardian" in line, line)


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}


if __name__ == "__main__":
    sys.exit(base.main(sys.argv[1:], TESTS))
