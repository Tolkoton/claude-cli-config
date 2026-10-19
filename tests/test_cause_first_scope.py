#!/usr/bin/env python3
"""Board 203: «cause first» holds only when no goals line needs the cause; advice on a non-goal follows the reading.

Definition tests, read as the agents read the texts:
  master-critic   the rule names the condition «required by no line of the goals», the mechanism that passed check 7
                  stays when the other choice weakens a goals line, BLOCKING only with an explanation and the line
                  numbers (else NON_BLOCKING_NOTE), both invented examples;
  master-architect «Cause before protection» carries the same condition; the stop «Читання цілей» holds the rule that
                  advice on a non-goal follows the reading — a request to the business analyst, reason 4;
  feature-critic, mvp-critic  the same narrowed rule.
What 202 got right stays: `change the choice`, «нічого не будуємо», «never an option» (tests of 202 hold the rest).

Run:   python3 tests/test_cause_first_scope.py            # every case
       python3 tests/test_cause_first_scope.py <test>     # one case by its name
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import re
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_CRITIC = ROOT / ".claude/agents/master-critic.md"
FEATURE_CRITIC = ROOT / ".claude/agents/feature-critic.md"
MVP_CRITIC = ROOT / ".claude/agents/mvp-critic.md"
MASTER_ARCHITECT = ROOT / ".claude/commands/master-architect.md"

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900].replace('Error', 'Err.')}")


def read(path: Path) -> str:
    """Whitespace collapsed: a string may wrap across a line break in the definition."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")) if path.is_file() else ""


def between(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i:] if j < 0 else text[i:j]


def test_master_critic_rule_names_the_condition() -> None:
    rule = between(read(MASTER_CRITIC), "**Cause first", "**No invented numbers.**")
    check("master-critic has the rule «Cause first»", bool(rule))
    check("its title names `only when no goals line needs the cause`", "only when no goals line needs the cause" in rule, rule[:300])
    check("it holds when the choice `is required by no line of the goals`", "is required by no line of the goals" in rule, rule)
    check("and another choice removes the risk `taking nothing that a goals line requires`",
          "taking nothing that a goals line requires" in rule, rule)
    check("the fix is still `change the choice`", "change the choice" in rule, rule)


def test_master_critic_mechanism_stays_when_a_goal_needs_the_cause() -> None:
    rule = between(read(MASTER_CRITIC), "**Cause first", "**No invented numbers.**")
    check("`weakens what a goals line requires` → the mechanism `stays`",
          "weakens what a goals line requires" in rule and "passed check 7 stays" in rule, rule)
    check("the other choice `may be a note`", "may be a note" in rule, rule)


def test_master_critic_blocking_only_with_line_numbers() -> None:
    rule = between(read(MASTER_CRITIC), "**Cause first", "**No invented numbers.**")
    blocking = [s for s in re.split(r"(?<=\.)\s+", rule) if "BLOCKING objection by this rule" in s]
    check("one sentence says when a BLOCKING objection by this rule may stand", bool(blocking), rule)
    s = blocking[0] if blocking else ""
    check("it needs the explanation `why the other choice takes nothing the goals require`",
          "why the other choice takes nothing the goals require" in s, s)
    check("it needs `the line numbers`", "the line numbers" in s, s)
    check("without them it is a `NON_BLOCKING_NOTE`", "without that it is a NON_BLOCKING_NOTE" in rule, rule)


def test_master_critic_two_invented_examples() -> None:
    rule = between(read(MASTER_CRITIC), "**Cause first", "**No invented numbers.**")
    check("example where the rule holds: separate files", "separate files (the rule holds)" in rule, rule)
    check("example where it does not: free text a goal requires, the check stays",
          "free text" in rule and "the check stays (the rule does not hold)" in rule, rule)


def test_master_architect_cause_before_protection_narrowed() -> None:
    rule = between(read(MASTER_ARCHITECT), "**Cause before protection", "**No invented numbers.**")
    check("/master-architect has «Cause before protection»", bool(rule))
    check("it names `only when no goals line needs the cause`", "only when no goals line needs the cause" in rule, rule)
    check("the choice is one `that no line of the goals requires`", "that no line of the goals requires" in rule, rule)
    check("`change the choice` stays", "change the choice" in rule, rule)
    check("the mechanism that `passed proportionality stays` when a goals line is weakened",
          "weakens what a goals line requires" in rule and "passed proportionality stays" in rule, rule)


def test_reading_the_goals_advice_follows_the_reading() -> None:
    step1 = between(read(MASTER_ARCHITECT), "## M1, step 1", "## M1, step 2")
    check("M1 step 1 found", bool(step1))
    rule = between(step1, "**Your advice follows your reading.**", "**Ideas from research**")
    check("M1 step 1 holds «Your advice follows your reading»", bool(rule), step1[:400])
    check("advice never recommends a mechanism against a line read as «нічого не будуємо»",
          "never recommends a mechanism" in rule and "«нічого не будуємо»" in rule, rule)
    check("something to build after all → `a request to the business analyst`", "a request to the business analyst" in rule, rule)
    check("named as `reason 4`", "reason 4" in rule, rule)
    for kept in ("A non-goal reads «нічого не будуємо»", "**A non-goal is never an option**"):
        check(f"202's `{kept}` stays", kept in step1)


def test_feature_and_mvp_critic_carry_the_narrowed_rule() -> None:
    for path in (FEATURE_CRITIC, MVP_CRITIC):
        text = read(path)
        rule = between(text, "Cause first — only when no goals line needs the cause", "The mark `")
        check(f"{path.name} has the narrowed «Cause first»", bool(rule))
        for word in ("a choice no goals line requires", "takes nothing a goals line requires",
                     "weakens what a goals line requires", "with the line numbers", "without that, a note"):
            check(f"{path.name}: `{word}`", word in rule, rule)


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
