#!/usr/bin/env python3
"""Board 204: the business analyst asks the owner only what is needed now and what only the owner knows.

The definition tests of the task's «Готово, коли»:
  1. the check «питання власникові — зараз?» stands in `.claude/references/business-analysis.md` (§0)
     and is named in every mode of the agent and in the `/business-analyst` conversation;
  2. the trap «деталь наперед» in §5, next to «рішення замість проблеми», with the core's own rule;
  3. `preseal`: a consequence is information, the question field `—`, the re-check after the owner's
     answers (`--changed`) that does not look for consequences — and what scenes e, f, k hold stays;
  4. `consult`: «when in doubt» stays for the document's silence; a doubt over «how» behind a two-way
     door is `NOT_REQUIRED` with the smallest form «вирішує архітектор як two-way door»;
  5. the template path `/business-analyst` names exists in a fresh install, equal to the seed;
  6. `docs/OWNER-GUIDE.md`, «Новий проєкт»: the goals at step 0 are a direction, a prototype first;
  7. no numeric limit was introduced.

Run:   python3 tests/test_ask_owner_now.py
Exit:  0 = all green, 1 = at least one case failed.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / ".claude/references/business-analysis.md"
AGENT = ROOT / ".claude/agents/business-analyst.md"
COMMAND = ROOT / ".claude/commands/business-analyst.md"
GUIDE = ROOT / "docs/OWNER-GUIDE.md"
TEMPLATE_REL = ".claude/references/goals-template.md"
SEED = ROOT / "templates/project/.engine/goals.md"
CHECK_HEADING = "## 0. A question to the owner — now?"

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


def flat(value: str) -> str:
    return " ".join(value.split())


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(path: Path, heading: str) -> str:
    """The body under `heading` up to the next heading of the same or a higher level, whitespace collapsed."""
    lines = text(path).splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    try:
        start = lines.index(heading)
    except ValueError:
        return ""
    body: list[str] = []
    fenced = False
    for line in lines[start + 1 :]:
        fenced ^= line.strip().startswith("```")
        hashes = len(line) - len(line.lstrip("#"))
        if not fenced and 0 < hashes <= level and line[hashes : hashes + 1] == " ":
            break
        body.append(line)
    return flat("\n".join(body))


def agent_mode(mode: str) -> str:
    return section(AGENT, f"## Mode `{mode}` — " + {
        "consult": "the answer to an architect's request",
        "preseal": "before the owner approves",
        "guardian": "the goals during the architecture",
    }[mode])


# ------------------------------------------------------------------ 1. the check, and where it is named


def test_the_check_stands_in_the_reference() -> None:
    body = section(REFERENCE, CHECK_HEADING)
    check(f"business-analysis.md has «{CHECK_HEADING}»", bool(body), "absent")
    for word in ("only the owner can answer it", "the answer is needed now", "both",
                 "one-way door", "how something will work", "two-way door", "«Verdict routing»",
                 "what only a try will show", "neither a question nor a line",
                 "they make it themselves, as a two-way door"):
        check(f"§0 holds «{word}»", word in body, body[:300])
    for mode in ("consult", "preseal", "guardian", "/business-analyst"):
        check(f"§0 names it as one check for `{mode}`", mode in body)


def test_every_mode_and_the_conversation_name_the_check() -> None:
    agent = flat(text(AGENT))
    check("the agent reads §0 in every mode", "§0 always" in agent)
    check("the agent states the check once for all modes", "A question to the owner — now? (§0)" in agent)
    for mode in ("consult", "preseal", "guardian"):
        check(f"mode `{mode}` names §0", "§0" in agent_mode(mode), agent_mode(mode)[:200])
    command = flat(text(COMMAND))
    check("/business-analyst names the check (method §0)", "Ask only what is needed now (method §0)" in command)
    check("…and both of its conditions", "only the owner can answer it and the answer is needed now" in command)
    ref = section(REFERENCE, "## 11. During the architecture — `guardian`")
    check("guardian in the reference names §0", "§0" in ref, ref[:200])


# ------------------------------------------------------------------ 2. the trap «деталь наперед»


def test_the_trap_detail_ahead_of_time() -> None:
    body = section(REFERENCE, "## 5. Before the owner approves — reread the draft against the traps")
    check("§5 has the trap «A detail ahead of time»", "**A detail ahead of time.**" in body)
    check("…next to «A solution instead of a problem»", "**A solution instead of a problem.**" in body)
    for word in ("how the thing will work", "a case nobody has seen yet",
                 "loses its sense", "«видно з того»", "the guardian would demand from the very first version"):
        check(f"the trap holds «{word}»", word in body, body[:300])


# ------------------------------------------------------------------ 3. preseal


def test_preseal_consequences_are_information_and_the_dash() -> None:
    ref = section(REFERENCE, "## 10. Before the seal — `preseal`")
    mode = agent_mode("preseal")
    for where, body in (("the reference §10", ref), ("the agent's mode", mode)):
        check(f"{where}: a consequence is told in one line as information",
              "one line" in body and "information" in body, body[:300])
        check(f"{where}: a question only on a contradiction, a non-goal or constraint, a one-way door",
              "contradicts another line" in body and "crosses a non-goal or a constraint" in body and "one-way door" in body)
        check(f"{where}: with nothing to ask, the question field is `—`", "the question field is `—`" in body)
    check("the format of PRESEAL_FINDING stays as it was",
          "PRESEAL_FINDING: <вид> | <рядки> | <слова власника або пояснення> | <питання до власника>" in mode)
    for kind in ("contradiction", "unmarked", "risk-reason", "consequence", "late-choice", "lost-emphasis", "no-core"):
        check(f"the kind `{kind}` stays", f"`{kind}`" in mode)
    check("a finding whose question fails §0 is no question", "is no question" in ref and "is no question" in mode)


def test_preseal_recheck_after_the_owners_answers() -> None:
    ref = section(REFERENCE, "## 10. Before the seal — `preseal`")
    mode = agent_mode("preseal")
    command = flat(text(COMMAND))
    check("the reference has «The re-check after the owner's answers»", "**The re-check after the owner's answers.**" in ref)
    check("the launch form names the changed lines: `--changed <lines>`",
          "preseal <draft> <journal> --changed <lines>" in ref and "--changed <lines>" in flat(text(AGENT)))
    for where, body in (("reference", ref), ("agent", mode)):
        for word in ("verbatim", "contradict", "the mark"):
            check(f"{where}: the re-check checks «{word}»", word in body)
        check(f"{where}: the re-check does not look for the consequences of the answers",
              "not choices made late" in body and ("does not look for the consequences" in body
                                                     or "Do not look for the consequences" in body))
    check("/business-analyst runs preseal again with `--changed`", "again, fresh, with `--changed <lines>`" in command)
    check("/business-analyst tells a `—` finding as information", "is told to the owner as information, not asked" in command)


def test_what_the_scenes_hold_stays() -> None:
    """Scenes e, f, f-trap, k, k-neg: preseal still finds what it found; consult's doubt still goes to the owner."""
    mode = agent_mode("preseal")
    for word in ("**contradictions**", "one person has two roles", "**words that are not the owner's**",
                 "risk language", "settled late in the conversation", "the consequences", "**the owner's emphases**",
                 "**the core**"):
        check(f"preseal still looks for «{word}»", word in mode)
    consult = agent_mode("consult")
    check("consult: «When in doubt, this one» stays", "**When in doubt, this one**" in consult)
    check("…with its first question whether the thing is needed at all", "whether the thing is needed at all" in consult)
    guardian = agent_mode("guardian")
    check("guardian still blocks a core goal with no mechanism",
          "a goal of the core has no mechanism that does what its line says" in guardian)


# ------------------------------------------------------------------ 4. consult


def test_consult_doubt_over_how() -> None:
    for where, body in (("agent", agent_mode("consult")),
                        ("reference §7", section(REFERENCE, "## 7. The request and the two answers"))):
        check(f"{where}: the doubt of «when in doubt» is the document's silence on what the owner wants",
              "silence on what the owner wants" in body, body[-600:])
        check(f"{where}: a doubt over «how» behind a two-way door is NOT_REQUIRED",
              "over **how**, behind a two-way door" in body and "`NOT_REQUIRED`" in body)
        check(f"{where}: its smallest form is «вирішує архітектор як two-way door»",
              "«вирішує архітектор як two-way door»" in body)


# ------------------------------------------------------------------ 5. the template path


def test_the_template_path_exists_in_a_fresh_install() -> None:
    command = text(COMMAND)
    named = re.findall(r"in the format of `([^`]+)`", command)
    check("/business-analyst names one template path", named == [TEMPLATE_REL], named)
    check("…not the engine-only templates/ path", "templates/project/.engine/goals.md" not in command)
    template = ROOT / TEMPLATE_REL
    check("the template equals the seed of .engine/goals.md, byte for byte",
          template.is_file() and template.read_bytes() == SEED.read_bytes(), "differs or absent")

    sys.path.insert(0, str(ROOT / "tests"))
    import test_project_seeds as seeds  # the installer harness that installs from the working tree

    with tempfile.TemporaryDirectory(prefix="ask-owner-now-") as tmp:
        where = Path(tmp)
        eng = seeds.engine_repo_from_working_tree(where)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(where / "projects.txt")}
        proj = where / "fresh"
        proj.mkdir()
        seeds.git(proj, "init", "-q", "-b", "main")
        r = subprocess.run([sys.executable, str(eng / "engine.py"), "install", str(proj), "--ref", "v99.0.0", "--no-register"],
                           capture_output=True, text=True, env=env, check=False)
        check("install exits 0", r.returncode == 0, r.stdout + r.stderr)
        got = proj / TEMPLATE_REL
        check(f"after install {TEMPLATE_REL} exists in the project", got.is_file(), "absent")
        check("…equal to the engine's, byte for byte", got.is_file() and got.read_bytes() == template.read_bytes())
        check("the seeded .engine/goals.md is the same text",
              (proj / ".engine/goals.md").is_file() and (proj / ".engine/goals.md").read_bytes() == template.read_bytes())


# ------------------------------------------------------------------ 6. the owner's guide


def test_owner_guide_new_project() -> None:
    body = section(GUIDE, "## Новий проєкт: від теки до першої задачі")
    check("OWNER-GUIDE has «Новий проєкт»", bool(body), "absent")
    for word in ("Документ цілей на кроці 0 — це напрям: ядро, що понад що, межі",
                 "чи продукт узагалі допомагає людям", "спершу прототип (`/mvp-architect` або ескіз)",
                 "повний дизайн (`/master-architect`) — після нього"):
        check(f"«Новий проєкт» holds «{word}»", word in body, body[:400])


# ------------------------------------------------------------------ 7. no numeric limit


def test_no_numeric_limit() -> None:
    for path in (REFERENCE, AGENT, COMMAND):
        body = flat(text(path))
        check(f"{path.relative_to(ROOT)} still says there is no limit",
              "no limit" in body or "no numeric limit" in body.lower() or "There is no limit" in body)
        for bad in re.findall(r"(?:at most|no more than|up to) \d+ (?:questions|rounds|findings)", body):
            check(f"{path.relative_to(ROOT)} has no numeric limit", False, bad)


def main() -> int:
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for fn in tests:
        print(fn.__name__)
        fn()
    print(f"{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
