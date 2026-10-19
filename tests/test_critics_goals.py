#!/usr/bin/env python3
"""The critics keep to the owner's goals (board 202, slice critics-goals-discipline): the contract tests.

Written from the sealed contract `.engine/slices/critics-goals-discipline.md` before the definitions
were changed, by the slice tester. Every expected string here is copied by hand from the contract's
«Seam (contract)», «Hardest seams» and «Exit criterion»; nothing is computed by the text under test.

  1. `.claude/agents/critic-core.md` §0 — the quote rule replaces the old clause (Seam 3);
  2. `.claude/agents/master-critic.md` — `journal` in «What you receive», check 5 (Seam 1), check 6 and
     the exception in the BLOCKING sentence (Seam 1), `change the choice`, `measure and show`,
     `no G or C line names`;
  3. `.claude/agents/feature-critic.md` — the `goals-fit` lens: the order (Seam 2), the one fix, the mark
     rule, the exception in the BLOCKING sentence, the journal, the escalate rule kept;
  4. `.claude/agents/mvp-critic.md` — the two checks before `1. **Simpler?**` (Seam 2), their block, the
     one fix, the journal;
  5. `tests/fast-suites.txt`.

Strings the contract writes on one line may wrap in the file: whitespace is collapsed before every search.
English phrases are compared case-insensitively (a phrase may open a sentence).

Run:   python3 tests/test_critics_goals.py            # every case
       python3 tests/test_critics_goals.py <test>     # one case by its name
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import re
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / ".claude/agents/critic-core.md"
MASTER = ROOT / ".claude/agents/master-critic.md"
FEATURE = ROOT / ".claude/agents/feature-critic.md"
MVP = ROOT / ".claude/agents/mvp-critic.md"
FAST = ROOT / "tests/fast-suites.txt"

MARK = "[не слова власника]"
JOURNAL = ".engine/goals/interview.md"
OLD_CLAUSE = "anything the draft marks as an owner requirement or owner decision"
SIMPLER = "1. **Simpler?**"
NEED = re.compile(r"необхідн\w*")
PROP = re.compile(r"пропорційн\w*\s+захисних\s+механізм\w*")

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900].replace('Error', 'Err.')}")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def flat(value: str) -> str:
    """Whitespace collapsed: a string the contract writes on one line may be wrapped in the file."""
    return " ".join(value.split())


def holds(value: str, needle: str) -> bool:
    """`needle` in `value`, whitespace collapsed and case folded."""
    return flat(needle).casefold() in flat(value).casefold()


def between(value: str, start: str, end: str) -> str:
    """From the first `start` to the first `end` after it (to the end when `end` is absent); '' without `start`."""
    i = value.find(start)
    if i < 0:
        return ""
    j = value.find(end, i + len(start))
    return value[i:] if j < 0 else value[i:j]


def section(path: Path, heading: str) -> str:
    """From the line starting with `heading` to the next line starting with `## `."""
    lines = text(path).splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
    if start is None:
        return ""
    body = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def lens(path: Path) -> str:
    """The `goals-fit` lens: from **`goals-fit`** to the next `## ` line (Seam 2)."""
    lines = text(path).splitlines()
    start = next((i for i, line in enumerate(lines) if "**`goals-fit`**" in line), None)
    if start is None:
        return ""
    body = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def sentences(value: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", flat(value))


def blocking_sentences(value: str) -> list[str]:
    return [s for s in sentences(value) if "a breach is blocking" in s.casefold()]


def core_section0() -> str:
    """critic-core §0: between `## 0.` and `## 1.`."""
    return between(text(CORE), "## 0.", "## 1.")


def master_check(number: int) -> str:
    """master-critic's check `number` of goals-fit: from `<n>. **<name>**` to `<n+1>. **`."""
    names = {5: "покриття", 6: "необхідність"}
    return between(text(MASTER), f"{number}. **{names[number]}**", f"{number + 1}. **")


def mvp_before_simpler() -> str:
    """mvp-critic's body (after the front matter) up to `1. **Simpler?**`; '' when that anchor is gone."""
    value = text(MVP)
    body = value.split("---", 2)[2] if value.startswith("---") else value
    i = body.find(SIMPLER)
    return body[:i] if i >= 0 else ""


# ------------------------------------------------------------------ 1. critic-core §0


def test_core_section0_keeps_its_title_and_the_owners_written_text() -> None:
    sec = core_section0()
    check("critic-core §0 keeps its title `## 0. Owner requirements are not under review`",
          "## 0. Owner requirements are not under review" in text(CORE), "title absent")
    for word in ("docs/plan/*.md", "ЩО ЗРОБИТИ"):
        check(f"critic-core §0 still names the owner's written text `{word}`", holds(sec, word), flat(sec)[:400])


def test_seam3_quote_rule_replaces_the_old_clause() -> None:
    sec = core_section0()
    check("critic-core §0 exists (between `## 0.` and `## 1.`)", bool(sec), "no §0")
    for word in ("the time of the remark", "the interview journal"):
        check(f"critic-core §0 names the quote source `{word}`", holds(sec, word), flat(sec)[:600])
    check("critic-core §0 still names `ЩО ЗРОБИТИ`", holds(sec, "ЩО ЗРОБИТИ"), flat(sec)[:400])
    check(f"the old clause `{OLD_CLAUSE}` is absent from critic-core §0", not holds(sec, OLD_CLAUSE),
          "the clause that made any mark untouchable is still there")


# ------------------------------------------------------------------ 2. master-critic


def test_master_receives_the_journal() -> None:
    sec = section(MASTER, "## What you receive")
    check("master-critic has a «What you receive» section", bool(sec), "absent")
    for word in ("journal", JOURNAL):
        check(f"master-critic's «What you receive» names `{word}`", holds(sec, word), flat(sec)[:500])


def test_seam1_check5_manual_work_and_right_of_access() -> None:
    body = master_check(5)
    check("master-critic has check 5 `5. **покриття**`", bool(body), "absent")
    for word in ("is no mechanism of the system", "власник читає все"):
        check(f"check 5 (from `5. **покриття**` to `6. **`) holds `{word}`", holds(body, word), flat(body)[:700])


def test_seam1_check6_mark_means_check_the_substance() -> None:
    body = master_check(6)
    check("master-critic has check 6 `6. **необхідність**`", bool(body), "absent")
    for word in ("перевір суть", "питання, не видалення"):
        check(f"check 6 (from `6. **необхідність**` to `7. **`) holds `{word}`", holds(body, word), flat(body)[:700])


def test_seam1_master_no_is_not_built() -> None:
    check("`is not built` stands nowhere in master-critic.md", not holds(text(MASTER), "is not built"),
          "the phrase is still in the file")


def test_seam1_master_check6_keeps_the_non_goal_breach() -> None:
    body = master_check(6)
    check("check 6 still holds `A mechanism built around a non-goal is a breach`",
          holds(body, "A mechanism built around a non-goal is a breach"), flat(body)[:700])


def test_seam1_master_blocking_sentence_names_the_exception() -> None:
    found = blocking_sentences(lens(MASTER))
    ok = any("except" in s.casefold() and MARK in s for s in found)
    check(f"in master-critic's goals-fit lens the sentence holding «A breach is BLOCKING» holds `except` and `{MARK}`",
          ok, found or "no sentence holds «A breach is BLOCKING»")


def test_master_cause_first_change_the_choice() -> None:
    check("master-critic holds `change the choice`", holds(text(MASTER), "change the choice"), "absent")


def test_master_poc_verdict_line_measure_and_show() -> None:
    lines = text(MASTER).splitlines()
    start = next((i for i, line in enumerate(lines) if "MASTER_CRITIC_POC_REQUIRED:" in line), None)
    item = ""
    if start is not None:
        body = [lines[start]]
        for line in lines[start + 1:]:
            if not line.startswith((" ", "\t")) or not line.strip():
                break
            body.append(line)
        item = " ".join(body)
    check("the verdict line `MASTER_CRITIC_POC_REQUIRED:` holds `measure and show`",
          holds(item, "measure and show"), item or "no verdict line `MASTER_CRITIC_POC_REQUIRED:`")


def test_master_invented_numbers_no_g_or_c_line_names() -> None:
    check("master-critic holds `no G or C line names`", holds(text(MASTER), "no G or C line names"), "absent")


# ------------------------------------------------------------------ 3. feature-critic


def test_seam2_feature_two_checks_before_inversion_premortem_bypass() -> None:
    found = sentences(lens(FEATURE).casefold())
    ordered = False
    for s in found:
        a, b = NEED.search(s), PROP.search(s)
        c, d, e = s.find("inversion"), s.find("premortem"), s.find("bypass")
        if a and b and min(c, d, e) >= 0:
            ordered = ordered or max(a.start(), b.start()) < min(c, d, e)
    check("in feature-critic's goals-fit lens the sentence that orders them puts `необхідність` and "
          "`пропорційність захисних механізмів` before `inversion`, `premortem` and `bypass`", ordered, found)


def test_feature_one_fix_proposals() -> None:
    check("feature-critic's goals-fit lens names the one fix «Пропозиції»", holds(lens(FEATURE), "Пропозиції"),
          flat(lens(FEATURE))[:500])


def test_feature_mark_rule_inside_goals_fit() -> None:
    body = lens(FEATURE)
    for word in ("перевір суть", "питання, не видалення"):
        check(f"feature-critic's goals-fit lens holds `{word}`", holds(body, word), flat(body)[:500])


def test_feature_blocking_sentence_names_the_exception() -> None:
    found = blocking_sentences(lens(FEATURE))
    ok = any("except" in s.casefold() and MARK in s for s in found)
    check(f"in feature-critic's goals-fit lens the sentence holding «A breach is BLOCKING» holds `except` and `{MARK}`",
          ok, found or "no sentence holds «A breach is BLOCKING»")


def test_feature_reads_the_journal() -> None:
    check(f"feature-critic names `{JOURNAL}`", holds(text(FEATURE), JOURNAL), "absent")


def test_feature_acceptance_criterion_without_source_stays_escalate() -> None:
    check("feature-critic's goals-fit lens keeps `FEATURE_CRITIC_ESCALATE`", "FEATURE_CRITIC_ESCALATE" in lens(FEATURE),
          flat(lens(FEATURE))[-500:])


# ------------------------------------------------------------------ 4. mvp-critic


def test_seam2_mvp_two_checks_before_simpler() -> None:
    head = mvp_before_simpler().casefold()
    check(f"mvp-critic keeps `{SIMPLER}`", SIMPLER in text(MVP), "anchor absent")
    check(f"`необхідність` stands before `{SIMPLER}`", bool(NEED.search(head)), "absent before it")
    check(f"`пропорційність захисних механізмів` stands before `{SIMPLER}`", bool(PROP.search(flat(head))), "absent before it")


def test_mvp_block_goals_document_and_mark_rule() -> None:
    head = mvp_before_simpler()
    for word in ("goals document", "перевір суть", "питання, не видалення"):
        check(f"mvp-critic before `{SIMPLER}` holds `{word}`", holds(head, word), flat(head)[-600:])


def test_mvp_one_fix_proposals() -> None:
    check(f"mvp-critic names the one fix «Пропозиції» before `{SIMPLER}`", holds(mvp_before_simpler(), "Пропозиції"), "absent")


def test_mvp_reads_the_journal() -> None:
    check(f"mvp-critic names `{JOURNAL}`", holds(text(MVP), JOURNAL), "absent")


# ------------------------------------------------------------------ 5. the fast set


def test_suite_in_the_fast_set() -> None:
    names = [line.strip() for line in text(FAST).splitlines() if line.strip() and not line.startswith("#")]
    check("tests/test_critics_goals.py is a line of tests/fast-suites.txt", "test_critics_goals.py" in names, names[-5:])


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
