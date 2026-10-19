#!/usr/bin/env python3
"""Feature business-goals-focus-second as one block: the integration tests (board 202, slice tester, mode `block`).

Written from the feature artifact `.engine/architecture/feature/business-goals-focus-second.md` («Inter-slice
contracts», «Integration exit criterion», the acceptance criteria A1–A12) and the strings the two sealed slice
contracts name (`.engine/slices/critics-goals-discipline.md`, `.engine/slices/architect-goals-discipline.md`).
The texts are read as the agents read them; every expected string is written by hand from those documents.

  link_*   the S1 → S2 connection: the key master-critic says it receives is the key /master-architect passes;
  A1–A12   one test per acceptance criterion, both slices together.

A4 «applies to every critic» for mvp-critic and A12's closing step depend on questions to the artifact:
tests/test_business_goals_focus_second_block_disputed.py.

Run:   python3 tests/test_business_goals_focus_second_block.py            # every case
       python3 tests/test_business_goals_focus_second_block.py <test>     # one case by its name
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import traceback
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITIC_CORE = ROOT / ".claude/agents/critic-core.md"
MASTER_CRITIC = ROOT / ".claude/agents/master-critic.md"
FEATURE_CRITIC = ROOT / ".claude/agents/feature-critic.md"
MVP_CRITIC = ROOT / ".claude/agents/mvp-critic.md"
SLICE_CRITIC = ROOT / ".claude/agents/slice-planner-critic.md"
MASTER_ARCHITECT = ROOT / ".claude/commands/master-architect.md"
ANALYST_AGENT = ROOT / ".claude/agents/business-analyst.md"
OWNER_GUIDE = ROOT / "docs/OWNER-GUIDE.md"
INFRA_TEMPLATE = ROOT / "templates/project/docs/infra.md"
OWNERSHIP = ROOT / ".claude/ownership.txt"
JOURNAL = ".engine/goals/interview.md"
MARK = "[не слова власника]"
SOURCES = ("the time of the remark", "the interview journal")

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900].replace('Error', 'Err.')}")


def flat(text: str) -> str:
    """Whitespace collapsed: a string may wrap across a line break in the definition."""
    return re.sub(r"\s+", " ", text)


def read(path: Path) -> str:
    return flat(path.read_text(encoding="utf-8")) if path.is_file() else ""


def between(text: str, start: str, end: str | None) -> str:
    """The text from `start` up to the first `end` after it (to the end when `end` is None or absent)."""
    i = text.find(start)
    if i < 0:
        return ""
    if end is None:
        return text[i:]
    j = text.find(end, i + len(start))
    return text[i:] if j < 0 else text[i:j]


def heading_section(path: Path, starts: str) -> str:
    """A markdown section by the start of its heading line, up to the next heading of the same or higher level."""
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines):
        if line.startswith(starts):
            level = len(line) - len(line.lstrip("#"))
            body = [line]
            for later in lines[n + 1:]:
                lvl = len(later) - len(later.lstrip("#"))
                if later.startswith("#") and later[lvl:lvl + 1] == " " and lvl <= level:
                    break
                body.append(later)
            return flat("\n".join(body))
    return ""


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;])\s+(?=[A-ZА-ЯІЇЄҐ«`*(\[])", text) if s]


def critic_call_input(text: str) -> list[str]:
    """The keys of `input={…}` in the one line holding `Task(agent="master-critic"`."""
    lines = [line for line in text.splitlines() if 'Task(agent="master-critic"' in line]
    if len(lines) != 1:
        return []
    m = re.search(r"input=\{([^}]*)\}", lines[0])
    return [k.strip() for k in m.group(1).split(",")] if m else []


# ── the S1 → S2 connection ────────────────────────────────────────────────────────────────────────────────


def test_link_journal_key_received_is_the_key_passed() -> None:
    receive = heading_section(MASTER_CRITIC, "## What you receive")
    check("master-critic «What you receive» names the key `journal`", "journal" in receive, receive[:300])
    check(f"… and the path {JOURNAL}", JOURNAL in receive)
    raw = MASTER_ARCHITECT.read_text(encoding="utf-8")
    keys = critic_call_input(raw)
    check("/master-architect's one master-critic Task line passes `journal` in its input", "journal" in keys, keys)
    check("… beside the keys it passed before (phase, draft, product_frame, maps)",
          {"phase", "draft", "product_frame", "maps"} <= set(keys), keys)


# ── the acceptance criteria ───────────────────────────────────────────────────────────────────────────────


def test_A1_check6_mark_means_check_the_substance() -> None:
    text = read(MASTER_CRITIC)
    check6 = between(text, "6. **необхідність**", "7. **")
    check("check 6 found", bool(check6))
    check("nowhere in master-critic «is not built»", "is not built" not in text)
    check("check 6 holds `перевір суть`", "перевір суть" in check6, check6[:400])
    check("check 6 holds `питання, не видалення`", "питання, не видалення" in check6)
    check("check 6 makes the marked element a NON_BLOCKING_NOTE", "NON_BLOCKING_NOTE" in check6)
    check("the non-goal breach still stands in check 6", "A mechanism built around a non-goal is a breach" in check6)
    blocking = [s for s in sentences(text) if "A breach is BLOCKING" in s]
    check("the sentence «A breach is BLOCKING» names the mark as its exception",
          any("except" in s and MARK in s for s in blocking), blocking)


def test_A2_master_critic_receives_the_journal() -> None:
    receive = heading_section(MASTER_CRITIC, "## What you receive")
    check("«What you receive» names `journal` = the interview journal path",
          "journal" in receive and JOURNAL in receive, receive[:400])
    keys = critic_call_input(MASTER_ARCHITECT.read_text(encoding="utf-8"))
    check("/master-architect passes `journal` to master-critic", "journal" in keys, keys)
    check(f"/master-architect says `journal` is {JOURNAL}", JOURNAL in read(MASTER_ARCHITECT))


def test_A3_check5_manual_work_is_no_mechanism() -> None:
    check5 = between(read(MASTER_CRITIC), "5. **покриття**", "6. **")
    check("check 5 found", bool(check5))
    check("check 5: a person's step `is no mechanism of the system`", "is no mechanism of the system" in check5, check5[:400])
    check("check 5: the amendment `власник читає все` is a right of access", "власник читає все" in check5)


def test_A4_critic_core_quote_rule() -> None:
    text = read(CRITIC_CORE)
    sec0 = between(text, "## 0.", "## 1.")
    check("§0 keeps its title", "## 0. Owner requirements are not under review" in text)
    for source in SOURCES:
        check(f"§0 names the source `{source}`", source in sec0)
    check(f"§0 names the journal {JOURNAL}", JOURNAL in sec0)
    check("§0 keeps `ЩО ЗРОБИТИ`", "ЩО ЗРОБИТИ" in sec0)
    check("§0 no longer makes any mark untouchable",
          "anything the draft marks as an owner requirement or owner decision" not in sec0)
    check("§0 names «рішення власника»", "рішення власника" in sec0)
    for critic in (MASTER_CRITIC, FEATURE_CRITIC, SLICE_CRITIC):
        check(f"{critic.name} inherits critic-core (so the rule applies to it)", "critic-core" in read(critic))


def test_A5_cause_first_change_the_choice() -> None:
    check("master-critic names `change the choice`", "change the choice" in read(MASTER_CRITIC))


def test_A6_poc_measures_no_invented_numbers() -> None:
    text = read(MASTER_CRITIC)
    # The verdict line is one list item of «Verdicts», wrapped over several physical lines: up to the next item.
    poc = [between(text[i:], "MASTER_CRITIC_POC_REQUIRED:", " - `") for i in [m.start() for m in re.finditer("MASTER_CRITIC_POC_REQUIRED:", text)]]
    check("the verdict line MASTER_CRITIC_POC_REQUIRED: holds `measure and show`",
          any("measure and show" in item for item in poc), poc)
    check("a number no G or C line names is an objection or a note: `no G or C line names`",
          "no G or C line names" in read(MASTER_CRITIC))


def test_A7_feature_and_mvp_critic_necessity_first() -> None:
    lens = between(read(FEATURE_CRITIC), "**`goals-fit`**", "## ")
    check("feature-critic has the `goals-fit` lens", bool(lens))
    order = [s for s in sentences(lens) if "inversion" in s and "premortem" in s and "необхідність" in s]
    check("one sentence of the lens orders the checks", bool(order), lens[:600])
    s = order[0] if order else ""
    first = max(s.find("необхідність"), s.find("пропорційність захисних механізмів"))
    check("in it, необхідність and пропорційність захисних механізмів stand before inversion, premortem and bypass",
          "пропорційність захисних механізмів" in s and "bypass" in s
          and 0 <= first < min(s.find("inversion"), s.find("premortem"), s.find("bypass")), s)
    check("the lens names «Пропозиції» as the place for an element without a source", "Пропозиції" in lens)
    check("the lens holds the mark rule `перевір суть`", "перевір суть" in lens)
    check("the lens holds `питання, не видалення`", "питання, не видалення" in lens)
    blocking = [x for x in sentences(read(FEATURE_CRITIC)) if "A breach is BLOCKING" in x]
    check("feature-critic's «A breach is BLOCKING» names the mark as its exception",
          any("except" in x and MARK in x for x in blocking), blocking)
    check(f"feature-critic reads {JOURNAL} itself", JOURNAL in read(FEATURE_CRITIC))
    mvp = read(MVP_CRITIC)
    head = mvp[:mvp.find("1. **Simpler?**")] if "1. **Simpler?**" in mvp else ""
    check("mvp-critic keeps question `1. **Simpler?**`", bool(head))
    for word in ("необхідність", "пропорційність", "goals document", "перевір суть", "питання, не видалення", "Пропозиції"):
        check(f"mvp-critic names `{word}` before question 1", word in head)
    check(f"mvp-critic reads {JOURNAL} itself", JOURNAL in mvp)


def test_A8_four_checks_inside_reading_the_goals() -> None:
    step1 = between(read(MASTER_ARCHITECT), "## M1, step 1", "## M1, step 2")
    check("M1 step 1 found", bool(step1))
    for word in ("one person in two roles", "both lines verbatim", "never an option", "whether anything is needed at all",
                 "only in «Пропозиції»", "whom, how often", "those who do not come back"):
        check(f"M1 step 1 holds `{word}` (a capital at the start of a sentence counts)", word.lower() in step1.lower())


def test_A9_master_architect_rules_and_preflight() -> None:
    text = read(MASTER_ARCHITECT)
    rules = between(text, "# Owner decisions, causes, numbers, stages", "# Pre-flight")
    check("the rules section stands before Pre-flight", bool(rules) and "# Pre-flight" in text[text.find(rules):])
    for word in (*SOURCES, "рішення архітектора", "change the choice", "measure and report",
                 "what is not in this message", "reason 4", "M1", "M2", "M3", "M4"):
        check(f"the rules section holds `{word}`", word in rules)
    pre = heading_section(MASTER_ARCHITECT, "# Pre-flight")
    for word in ("docs/infra.md", "one question", "the operator writes it", "templates/project/docs/infra.md"):
        check(f"Pre-flight holds `{word}`", word in pre)
    check("the journal goes to master-critic", "journal" in critic_call_input(MASTER_ARCHITECT.read_text(encoding="utf-8")))


def test_A10_guardian_notes_an_unquoted_owner_decision() -> None:
    guardian = heading_section(ANALYST_AGENT, "## Mode `guardian`")
    check("the guardian section found", bool(guardian))
    check("it names «рішення власника» or «owner decision»", "рішення власника" in guardian or "owner decision" in guardian)
    for source in SOURCES:
        check(f"it names the source `{source}`", source in guardian)
    check("the unquoted decision is a GUARDIAN_NOTE", "GUARDIAN_NOTE" in guardian)


def test_A11_infra_seed_lands_in_a_new_project() -> None:
    template = INFRA_TEMPLATE.read_text(encoding="utf-8") if INFRA_TEMPLATE.is_file() else ""
    check("templates/project/docs/infra.md exists", bool(template))
    for heading in ("Хмарний проєкт", "Регіон", "Доступ для runner-а", "Що вже розгорнуто"):
        check(f"the template has `{heading}`", heading in template)
    lines = [line.split() for line in OWNERSHIP.read_text(encoding="utf-8").splitlines()]
    check("ownership seeds it: `project docs/infra.md seed=templates/project/docs/infra.md`",
          ["project", "docs/infra.md", "seed=templates/project/docs/infra.md"] in lines)
    sys.path.insert(0, str(ROOT / "tests"))
    import test_project_seeds as seeds  # the slice's own installer harness: the working tree as an engine repository
    with tempfile.TemporaryDirectory(prefix="focus2-block-") as tmp:
        where = Path(tmp)
        eng = seeds.engine_repo_from_working_tree(where)
        proj = where / "fresh"
        proj.mkdir()
        seeds.git(proj, "init", "-q", "-b", "main")
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(where / "projects.txt")}
        r = subprocess.run([sys.executable, str(eng / "engine.py"), "install", str(proj), "--ref", "v99.0.0", "--no-register"],
                           capture_output=True, text=True, env=env, check=False)
        check("engine.py install exits 0", r.returncode == 0, r.stdout + r.stderr)
        infra = proj / "docs/infra.md"
        check("the new project has docs/infra.md equal to the template",
              infra.is_file() and infra.read_bytes() == INFRA_TEMPLATE.read_bytes())
    guide = read(OWNER_GUIDE)
    check("OWNER-GUIDE names docs/infra.md", "docs/infra.md" in guide)


def test_A12_definition_tests_and_context_budget_green() -> None:
    for suite in ("test_critics_goals.py", "test_architect_goals.py", "test_architect_goals_disputed.py",
                  "test_goals_roles.py", "test_context_budget.py"):
        r = subprocess.run([sys.executable, str(ROOT / "tests" / suite)], cwd=ROOT, capture_output=True, text=True, check=False)
        check(f"tests/{suite} is green", r.returncode == 0, (r.stdout + r.stderr)[-600:])
    fast = (ROOT / "tests/fast-suites.txt").read_text(encoding="utf-8")
    for suite in ("test_critics_goals.py", "test_architect_goals.py"):
        check(f"{suite} is in the fast set", suite in fast)


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
