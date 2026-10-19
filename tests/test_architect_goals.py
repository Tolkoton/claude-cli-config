#!/usr/bin/env python3
"""The architect keeps to the owner's goals (board 202, slice architect-goals-discipline): the contract tests.

Written from the sealed contract `.engine/slices/architect-goals-discipline.md` before the texts were
changed, by the slice tester. Every expected string is copied by hand from the contract's «Seam (contract)»,
«Hardest seams» and «Exit criterion»; nothing is computed by the text under test.

  1. `.claude/commands/master-architect.md` — `journal` in the master-critic call (Seam 1), the four checks
     inside M1 step 1 (Seam 2), the section `# Owner decisions, causes, numbers, stages` and its five rules
     (Seam 3 for the two sources), Pre-flight's `docs/infra.md`;
  2. `.claude/agents/business-analyst.md` — the guardian's quote check (Seam 3);
  3. `templates/project/docs/infra.md`, `.claude/ownership.txt`, and the seed landing in a fresh project (Seam 4);
  4. `docs/OWNER-GUIDE.md`; 5. `tests/fast-suites.txt`.

Strings the contract writes on one line may wrap in the file: whitespace is collapsed before every search.
English phrases are compared case-insensitively (a phrase may open a sentence).

Run:   python3 tests/test_architect_goals.py            # every case
       python3 tests/test_architect_goals.py <test>     # one case by its name
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import traceback
import types
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHITECT = ROOT / ".claude/commands/master-architect.md"
ANALYST = ROOT / ".claude/agents/business-analyst.md"
CORE = ROOT / ".claude/agents/critic-core.md"
TEMPLATE = ROOT / "templates/project/docs/infra.md"
OWNERSHIP = ROOT / ".claude/ownership.txt"
GUIDE = ROOT / "docs/OWNER-GUIDE.md"
FAST = ROOT / "tests/fast-suites.txt"

JOURNAL = ".engine/goals/interview.md"
CALL = 'Task(agent="master-critic"'
RULES = "# Owner decisions, causes, numbers, stages"
SOURCES = ("the time of the remark", "the interview journal")
SEED_RULE = ["project", "docs/infra.md", "seed=templates/project/docs/infra.md"]

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


def until_heading(path: Path, heading: str, stops: tuple[str, ...]) -> str:
    """From the line starting with `heading` to the next line starting with one of `stops`."""
    lines = text(path).splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
    if start is None:
        return ""
    body = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith(stops):
            break
        body.append(line)
    return "\n".join(body)


def step1() -> str:
    """M1 step 1: between `## M1, step 1` and `## M1, step 2` (Seam 2)."""
    return between(text(ARCHITECT), "## M1, step 1", "## M1, step 2")


def rules_section() -> str:
    """The new section: between `# Owner decisions, causes, numbers, stages` and `# Pre-flight`."""
    return between(text(ARCHITECT), RULES, "# Pre-flight")


def preflight() -> str:
    """From `# Pre-flight` to the next `# ` heading."""
    return until_heading(ARCHITECT, "# Pre-flight", ("# ",))


def guardian() -> str:
    """The guardian section: from ``## Mode `guardian` `` to the next `## ` or the end."""
    return until_heading(ANALYST, "## Mode `guardian`", ("## ",))


# ------------------------------------------------------------------ 1. /master-architect


def test_seam1_journal_is_a_key_of_the_master_critic_call() -> None:
    lines = text(ARCHITECT).splitlines()
    holding = [i for i, line in enumerate(lines) if CALL in line]
    check(f"exactly one line of master-architect.md holds `{CALL}`", len(holding) == 1, holding)
    keys: list[str] = []
    if holding:
        m = re.search(r"input=\{([^}]*)\}", lines[holding[0]])
        keys = [k.strip() for k in m.group(1).split(",")] if m else []
    check("the call's input={…} is exactly {phase, draft, product_frame, journal, maps}",
          sorted(keys) == sorted(["phase", "draft", "product_frame", "journal", "maps"]), keys)


def test_seam1_call_comment_names_the_journal_file() -> None:
    lines = text(ARCHITECT).splitlines()
    i = next((n for n, line in enumerate(lines) if CALL in line), None)
    comment = ""
    if i is not None:
        own = lines[i].split("#", 1)[1] if "#" in lines[i].split(CALL, 1)[1] else ""
        rest = []
        for line in lines[i + 1:]:
            if not line.strip().startswith("#"):
                break
            rest.append(line)
        comment = own + " " + " ".join(rest)
    check(f"the comment of the master-critic call names `journal` and `{JOURNAL}`",
          "journal" in comment and JOURNAL in comment, comment or "no comment at the call")


def test_seam2_four_reading_checks_inside_m1_step1() -> None:
    body = step1()
    check("master-architect has M1 step 1 (`## M1, step 1` … `## M1, step 2`)", bool(body), "absent")
    for word in ("one person in two roles", "both lines verbatim", "never an option",
                 "whether anything is needed at all", "only in «Пропозиції»", "whom, how often",
                 "those who do not come back"):
        check(f"M1 step 1 holds `{word}`", holds(body, word), flat(body)[-600:])


def test_rules_section_stands_between_goals_and_preflight() -> None:
    value = text(ARCHITECT)
    a, b, c = value.find("# The goals during every stage"), value.find(RULES), value.find("# Pre-flight")
    check(f"`{RULES}` stands after «The goals during every stage» and before `# Pre-flight`",
          a >= 0 and b > a and c > b, (a, b, c))


def test_seam3_rule_owner_decision_only_with_a_quote() -> None:
    body = rules_section()
    check("the section names «owner decision» or «рішення власника»",
          holds(body, "owner decision") or holds(body, "рішення власника"), flat(body)[:600] or "no section")
    for word in (*SOURCES, "рішення архітектора"):
        check(f"the section holds `{word}`", holds(body, word), flat(body)[:600] or "no section")


def test_rule_cause_before_protection() -> None:
    check("the section holds `change the choice`", holds(rules_section(), "change the choice"),
          flat(rules_section())[:600] or "no section")


def test_rule_no_invented_numbers() -> None:
    check("the section holds `measure and report`", holds(rules_section(), "measure and report"),
          flat(rules_section())[:600] or "no section")


def test_rule_each_stage_shown_separately() -> None:
    check("the section holds `what is not in this message`", holds(rules_section(), "what is not in this message"),
          flat(rules_section())[:600] or "no section")


def test_rule_new_requirement_goes_to_the_analyst() -> None:
    check("the section holds `reason 4`", holds(rules_section(), "reason 4"), flat(rules_section())[:600] or "no section")


def test_preflight_reads_docs_infra() -> None:
    body = preflight()
    check("master-architect has `# Pre-flight`", bool(body), "absent")
    for word in ("docs/infra.md", "one question", "the operator writes it", "templates/project/docs/infra.md"):
        check(f"Pre-flight holds `{word}`", holds(body, word), flat(body))


# ------------------------------------------------------------------ 2. the guardian


def test_seam3_guardian_quote_check() -> None:
    body = guardian()
    check("business-analyst has the guardian section", bool(body), "absent")
    check("the guardian section names «owner decision» or «рішення власника»",
          holds(body, "owner decision") or holds(body, "рішення власника"), flat(body)[:700])
    for word in (*SOURCES, "GUARDIAN_NOTE"):
        check(f"the guardian section holds `{word}`", holds(body, word), flat(body)[:700])


def test_seam3_same_sources_in_critic_core() -> None:
    sec = between(text(CORE), "## 0.", "## 1.")
    for word in SOURCES:
        check(f"critic-core §0 holds `{word}` (the wording the architect and the guardian share)", holds(sec, word),
              flat(sec)[:500])


# ------------------------------------------------------------------ 3. the seed


def test_template_four_headings() -> None:
    value = text(TEMPLATE)
    check("templates/project/docs/infra.md exists", bool(value), "absent")
    headings = [line for line in value.splitlines() if line.startswith("#")]
    for word in ("Хмарний проєкт", "Регіон", "Доступ для runner-а", "Що вже розгорнуто"):
        check(f"the template has a heading `{word}`", any(word in h for h in headings), headings)
    check("the template names its reader `/master-architect`", "/master-architect" in value, "absent")


def load_engine() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("engine_under_test", ROOT / "engine.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ownership_line_seeds_docs_infra_first() -> None:
    lines = [line.split("#", 1)[0].split() for line in text(OWNERSHIP).splitlines()]
    check(f"ownership.txt has the line `{'  '.join(SEED_RULE)}`", SEED_RULE in lines, "absent")
    engine = load_engine()
    rules = engine.parse_ownership(text(OWNERSHIP))
    first = next((r for r in rules if r.regex.match("docs/infra.md")), None)
    check("the FIRST rule matching docs/infra.md is project with seed=templates/project/docs/infra.md",
          first is not None and first.owner == "project" and first.seed == "templates/project/docs/infra.md",
          first and (first.owner, first.pattern, first.seed, first.line))


def test_seam4_seed_lands_in_a_fresh_project() -> None:
    sys.path.insert(0, str(ROOT / "tests"))
    import test_project_seeds as seeds  # the installer harness that installs from the working tree

    with tempfile.TemporaryDirectory(prefix="architect-goals-seed-") as tmp:
        where = Path(tmp)
        eng = seeds.engine_repo_from_working_tree(where)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(where / "projects.txt")}
        proj = where / "fresh"
        proj.mkdir()
        seeds.git(proj, "init", "-q", "-b", "main")
        r = subprocess.run([sys.executable, str(eng / "engine.py"), "install", str(proj), "--ref", "v99.0.0", "--no-register"],
                           capture_output=True, text=True, env=env, check=False)
        check("install exits 0", r.returncode == 0, r.stdout + r.stderr)
        got = proj / "docs/infra.md"
        check("after install docs/infra.md exists in the project", got.is_file(), "absent")
        check("the project's docs/infra.md equals the template, byte for byte",
              got.is_file() and TEMPLATE.is_file() and got.read_bytes() == TEMPLATE.read_bytes(), "differs or absent")


# ------------------------------------------------------------------ 4. the owner's guide


def test_owner_guide_names_infra_and_owner_decision() -> None:
    body = until_heading(GUIDE, "### Документ цілей і зупинка «Читання цілей»", ("# ", "## ", "### "))
    check("OWNER-GUIDE has «Документ цілей і зупинка «Читання цілей»»", bool(body), "absent")
    for word in ("docs/infra.md", "рішення власника"):
        check(f"under that heading OWNER-GUIDE holds `{word}`", holds(body, word), flat(body)[-500:])


# ------------------------------------------------------------------ 5. the fast set


def test_suite_in_the_fast_set() -> None:
    names = [line.strip() for line in text(FAST).splitlines() if line.strip() and not line.startswith("#")]
    check("tests/test_architect_goals.py is a line of tests/fast-suites.txt", "test_architect_goals.py" in names, names[-5:])


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
