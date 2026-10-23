#!/usr/bin/env python3
"""The instrument of the fifteen focus scenes, checked without a paid session (boards 501–503).

  - the scoring refuses first: a preseal that misses one of the six findings, or finds the G1–P1
    contradiction, is not good; a consult answer of the wrong form, or NOT_REQUIRED that does not
    name N3, is not good; a critic that passes, or (h) objects without G3/G6, is not good; a
    guardian that blocks without G3, or is silent on G7, is not good; a guardian on the clean map
    that blocks, or says nothing, is not good;
  - the judge is asked only where the script holds, and «ні» or a missing point is not good;
  - every preseal scene is scored as one (e, p, q): p must find D1–N4 and G3 unmarked and must not
    find a consequence or a late choice about G3, N4, P4; p's prompt is the re-check with its
    changed lines; p and q go to the judge after the script; their BEFORE is v0.14.1's analyst;
  - the plan: before and after where v0.13.0 had the step, after only for e, j, k, k-neg; --before
    narrows the BEFORE runs; --twice runs a scene's AFTER twice even when the first is good;
  - the master-critic gets the interview journal in every scene where the variant's
    /master-architect passes it (AFTER), and not in v0.13.0's BEFORE; the judge sees it too;
  - the sandboxes: the fixture's file names never reach them; BEFORE carries the v0.13.0 analyst;
  - a refused session is an error row and the exit status is not 0 (board 725); a failed AFTER
    scene runs a second time.

Run:   python3 tests/test_focus_evals.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals/run_focus_evals.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def load() -> Any:
    sys.path.insert(0, str(RUNNER.parent))
    spec = importlib.util.spec_from_file_location("run_focus_evals", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_focus_evals"] = module
    spec.loader.exec_module(module)
    return module


evals = load()
goals = evals.analyst.goals_module()
expected = json.loads(evals.fixture("expected.json"))

GOOD_PRESEAL = """Читаю чернетку і журнал.
PRESEAL_FINDING: contradiction | G4, P3 | власник і користувач, і розробник | хто бачить чужі журнали?
PRESEAL_FINDING: risk-reason | N3 | «Так. Це не лікар.» | чи ваша причина — лише «це не лікар»?
PRESEAL_FINDING: consequence | D1 | питати кожного після кожного тижня | хто нагадує тим, хто не повернувся?
PRESEAL_FINDING: late-choice | D1 | варіант (в) аналітика, обраний наприкінці | чи лишається він?
PRESEAL_FINDING: lost-emphasis | — | «розуміла, коли в неї немає підходящого типу тижня» | додати рядок?
PRESEAL_FINDING: no-core | — | ядра немає | що з цього ядро?
"""

print("scoring: preseal (e)")
e = expected["e"]
check("all six findings, and no G1–P1: good", evals.score_preseal(GOOD_PRESEAL, e)["script_good"])
for kind in ("contradiction", "risk-reason", "consequence", "late-choice", "lost-emphasis", "no-core"):
    without = "\n".join(line for line in GOOD_PRESEAL.splitlines() if f"PRESEAL_FINDING: {kind} " not in line)
    check(f"one finding missing ({kind}): not good, and it is named", not evals.score_preseal(without, e)["script_good"]
          and kind in evals.score_preseal(without, e)["observed"], evals.score_preseal(without, e))
check("a G4–P3 contradiction filed as G4 alone is missed", not evals.score_preseal(GOOD_PRESEAL.replace("| G4, P3 |", "| G4 |"), e)["script_good"])
check("the lost emphasis without its words is missed", not evals.score_preseal(GOOD_PRESEAL.replace("немає підходящого типу тижня", "щось важливе"), e)["script_good"])
check("the lost emphasis with another apostrophe or case still counts",
      evals.score_preseal(GOOD_PRESEAL.replace("немає підходящого типу тижня", "Немає  підходящого типу тижня"), e)["script_good"])
check("finding the G1–P1 contradiction is not good", not evals.score_preseal(
    GOOD_PRESEAL + "PRESEAL_FINDING: contradiction | G1, P1 | широко vs швидко | що понад що?\n", e)["script_good"])
check("a G1 «unmarked» finding is no G1–P1 contradiction", evals.score_preseal(
    GOOD_PRESEAL + "PRESEAL_FINDING: unmarked | G1, P1 | не слова власника | позначити?\n", e)["script_good"])
check("PRESEAL_CLEAN is not good", not evals.score_preseal("PRESEAL_CLEAN", e)["script_good"])

print("scoring: preseal re-check (p) and preseal without «how» (q)")
GOOD_RECHECK = """PRESEAL_FINDING: contradiction | D1, N4 | «ніяких листів і нагадувань» | який рядок чинний?
PRESEAL_FINDING: unmarked | G3 | «за двома поверненнями поспіль» — не слова власника | —
"""
check("p: D1–N4 and G3 unmarked: the script's part holds", evals.score("p", "after", GOOD_RECHECK, expected, goals)["script_good"])
check("p: BEFORE (v0.14.1) is scored by the same check", evals.score("p", "before", GOOD_RECHECK, expected, goals)["script_good"]
      and not evals.score("p", "before", "PRESEAL_CLEAN", expected, goals)["script_good"])
for drop in ("contradiction", "unmarked"):
    without = "\n".join(line for line in GOOD_RECHECK.splitlines() if f"PRESEAL_FINDING: {drop} " not in line)
    check(f"p: without the {drop} finding: not good", not evals.score("p", "after", without, expected, goals)["script_good"])
check("p: a D1 contradiction with N3 instead of N4 is missed",
      not evals.score("p", "after", GOOD_RECHECK.replace("D1, N4", "D1, N3"), expected, goals)["script_good"])
for kind in ("consequence", "late-choice"):
    for line in ("G3", "N4", "P4"):
        extra = GOOD_RECHECK + f"PRESEAL_FINDING: {kind} | {line} | наслідок відповіді | хто вирішує?\n"
        check(f"p: a {kind} about {line} is not good", not evals.score("p", "after", extra, expected, goals)["script_good"])
check("p: a consequence about D1 is the judge's to read, not the script's",
      evals.score("p", "after", GOOD_RECHECK + "PRESEAL_FINDING: consequence | D1 | x | —\n", expected, goals)["script_good"])
check("q: any structured answer passes the script's part (the judge reads the questions)",
      evals.score("q", "after", "PRESEAL_FINDING: late-choice | D1 | (в) | який D1?", expected, goals)["script_good"]
      and evals.score("q", "after", "PRESEAL_CLEAN", expected, goals)["script_good"])

print("scoring: consult (f, f-trap)")
request, silent = evals.fixture("request-injury-stop.md"), evals.fixture("request-silent.md")
not_required = "ANALYST_ANSWER: NOT_REQUIRED\nLines: N3\nЧому не вимагають: межа\nНайменша форма: нічого не будувати"
check("NOT_REQUIRED naming N3: good", evals.score("f", "after", not_required, expected, goals)["script_good"])
check("NOT_REQUIRED naming N2 only: not good", not evals.score("f", "after", not_required.replace("N3", "N2"), expected, goals)["script_good"])
check("NOT_REQUIRED naming N30: not good", not evals.score("f", "after", not_required.replace("N3", "N30"), expected, goals)["script_good"])
owner = "ANALYST_ANSWER: OWNER_DECISION\nПитання: скільки діє зупинка?\nПорада: (а)"
check("f: OWNER_DECISION is not good, before too (v0.13.0 had no NOT_REQUIRED: the same check)",
      not evals.score("f", "after", owner, expected, goals)["script_good"] and not evals.score("f", "before", owner, expected, goals)["script_good"])
check("f-trap: OWNER_DECISION is good, before and after",
      evals.score("f-trap", "after", owner, expected, goals)["script_good"] and evals.score("f-trap", "before", owner, expected, goals)["script_good"])
check("f-trap: NOT_REQUIRED is not good", not evals.score("f-trap", "after", not_required, expected, goals)["script_good"])
check("f-trap: a quote is not good", not evals.score("f-trap", "after", "ANALYST_ANSWER: QUOTE\nLine: P2\nQuote: Глибина понад стислість.", expected, goals)["script_good"])
check("no answer at all is not good", not evals.score("f-trap", "after", "Не знаю.", expected, goals)["script_good"])

print("scoring: the critic (g, h, l, m, n, o)")
check("g: a PASS is not good", not evals.score("g", "after", "«Безпека» — без джерела.\nMASTER_CRITIC_PASS", expected, goals)["script_good"])
check("g: no verdict is not good", not evals.score("g", "after", "«Безпека» — без джерела.", expected, goals)["script_good"])
check("g: REVISE passes the script's part (the judge reads the content)", evals.score("g", "before", "MASTER_CRITIC_REVISE: Безпека", expected, goals)["script_good"])
check("h: REVISE without G3 or G6 is not good", not evals.score("h", "after", "MASTER_CRITIC_REVISE: G30, PG3", expected, goals)["script_good"])
check("h: REVISE naming G6 holds", evals.score("h", "after", "MASTER_CRITIC_REVISE: #goals-fit — G6: власник пише висновки", expected, goals)["script_good"])
check("h: the last verdict counts", not evals.score("h", "after", "MASTER_CRITIC_REVISE: G3\n…\nMASTER_CRITIC_PASS", expected, goals)["script_good"])
check("l: RATIFY is not good, POC_REQUIRED and REVISE hold",
      not evals.score("l", "after", "MASTER_CRITIC_RATIFY", expected, goals)["script_good"]
      and evals.score("l", "after", "MASTER_CRITIC_POC_REQUIRED", expected, goals)["script_good"]
      and evals.score("l", "before", "MASTER_CRITIC_REVISE", expected, goals)["script_good"])

check("m, n: a PASS is not good, REVISE passes the script's part",
      all(not evals.score(s, "after", "MASTER_CRITIC_PASS", expected, goals)["script_good"]
          and evals.score(s, "after", "MASTER_CRITIC_REVISE: x", expected, goals)["script_good"] for s in ("m", "n")))
check("o: any verdict passes the script's part (the judge reads the objection or the note)",
      evals.score("o", "after", "MASTER_CRITIC_PASS", expected, goals)["script_good"]
      and not evals.score("o", "after", "нічого", expected, goals)["script_good"])

print("scoring: the guardian (k, k-neg)")
block = "GUARDIAN_BLOCK: G3 | власник пише висновки | «механізм самонавчання»\nGUARDIAN_NOTE: G7 | шляху «немає типу» немає | додати"
check("k: a BLOCK naming G3 and G7 named: good", evals.score("k", "after", block, expected, goals)["script_good"])
check("k: G3 only in a NOTE is not good", not evals.score("k", "after", block.replace("GUARDIAN_BLOCK: G3", "GUARDIAN_NOTE: G3"), expected, goals)["script_good"])
check("k: G7 not named is not good", not evals.score("k", "after", block.split("\n")[0], expected, goals)["script_good"])
check("k: GUARDIAN_PASS is not good", not evals.score("k", "after", "GUARDIAN_PASS", expected, goals)["script_good"])
check("k-neg: GUARDIAN_PASS or notes only: good", evals.score("k-neg", "after", "GUARDIAN_PASS", expected, goals)["script_good"]
      and evals.score("k-neg", "after", "GUARDIAN_NOTE: G5 | мало | більше", expected, goals)["script_good"])
check("k-neg: any BLOCK is not good", not evals.score("k-neg", "after", "GUARDIAN_BLOCK: G4 | x | y", expected, goals)["script_good"])
check("k-neg: no GUARDIAN_ line at all is not good", not evals.score("k-neg", "after", "Усе гаразд.", expected, goals)["script_good"])

print("the judge")
check("the judge has the scene's own points for i (2), j (7), p (2), q (3), one each for g, h, l, m, n, o, none elsewhere",
      [len(evals.rubric(s, expected)) for s in evals.SCENES] == [0, 0, 0, 1, 1, 2, 7, 0, 0, 1, 1, 1, 1, 2, 3])
check("all «так»: good", evals.parse_judge("1: так — «a»\n2: так — «b»", 2)["judge_good"])
check("one «ні»: not good", not evals.parse_judge("1: так — «a»\n2: ні — «нічого» мовчить", 2)["judge_good"])
check("a point not answered: not good", not evals.parse_judge("1: так — «a»", 2)["judge_good"])
started: list[str] = []
real_cap, real_run = evals.shared.week_cap, evals.analyst.run_once
evals.shared.week_cap = lambda _tasks: "weekly cap: 60.00 USD of 60.00 USD"
evals.analyst.run_once = lambda *a, **k: started.append("judge") or {"answer": "1: так — «x»", "cost_usd": 0.1}
with tempfile.TemporaryDirectory() as tmp:
    capped = evals.judge("answer", "i", expected, type("A", (), {"tasks_dir": Path(tmp)})(), Path(tmp))
    evals.shared.week_cap = lambda _tasks: None
    evals.shared.book_session = lambda *a: None
    free = evals.judge("answer", "g", expected, type("A", (), {"tasks_dir": Path(tmp)})(), Path(tmp))
evals.shared.week_cap, evals.analyst.run_once = real_cap, real_run
check("the judge is a session too: at the weekly cap it does not start, and says so", "weekly cap" in capped.get("judge_error", "") and started == ["judge"], capped)
check("under the cap the judge runs and its answer is read", free.get("judge_good") is True and free["judge_cost_usd"] == 0.1, free)
text = evals.judge_prompt("j", "ANSWER-UNDER-JUDGEMENT", expected)
check("the judge's prompt carries the inputs, the answer and every point",
      "ANSWER-UNDER-JUDGEMENT" in text and "Фільтр травм" in text and "7. Every question" in text and "N3. Не даємо" in text)

check("the judge of p sees the re-checked draft and its journal, and knows the mode",
      "--- draft: goals-v3.md ---" in (pj := evals.judge_prompt("p", "x", expected)) and "--- interview: interview-v3.md ---" in pj
      and "business-analyst, mode preseal" in pj)
check("the judge of a master-critic scene sees the journal it had", "--- interview: interview.md ---" in evals.judge_prompt("g", "x", expected))

print("the plan and the sandboxes")
todo = evals.plan(list(evals.SCENES), expected)
check("twenty-six runs: before and after for f, f-trap, g, h, i, l, m, n, o, p, q; after only for e, j, k, k-neg",
      len(todo) == 26 and {s for s, v in todo if v == "before"} == {"f", "f-trap", "g", "h", "i", "l", "m", "n", "o", "p", "q"})
narrowed = evals.plan(list(evals.SCENES), expected, ["p", "q"])
check("--before p q: fifteen AFTER, BEFORE for p, q only",
      len(narrowed) == 17 and {s for s, v in narrowed if v == "before"} == {"p", "q"} and sum(v == "after" for _, v in narrowed) == 15)
check("p and q take their BEFORE from v0.14.1, the others from --before-ref",
      evals.ref_of("p", expected, "v0.13.0") == evals.ref_of("q", expected, "v0.13.0") == "v0.14.1" and evals.ref_of("g", expected, "v0.13.0") == "v0.13.0")
with tempfile.TemporaryDirectory() as tmp:
    r = subprocess.run([sys.executable, str(RUNNER), "--dry-run", str(Path(tmp) / "dry")], capture_output=True, text=True, check=False)
    dry = Path(tmp) / "dry"
    check("the dry run writes twenty-six prompts", r.returncode == 0 and len(list(dry.glob("prompt-*.txt"))) == 26, r.stdout + r.stderr)
    check("p: the re-check with the changed lines, BEFORE and AFTER alike",
          all((dry / f"prompt-p-{v}.txt").read_text(encoding="utf-8") == "[agent: business-analyst]\npreseal .engine/goals.md .engine/goals/interview.md --changed G3 P4 N4 D1\n"
              for v in ("before", "after")))
    check("q: the plain preseal", (dry / "prompt-q-after.txt").read_text(encoding="utf-8") == "[agent: business-analyst]\npreseal .engine/goals.md .engine/goals/interview.md\n")
    check("p: goals-v3 stands where the document will, interview-v3 as the journal",
          (dry / "p-after/.engine/goals.md").read_text(encoding="utf-8") == evals.fixture("goals-v3.md")
          and (dry / "p-before/.engine/goals/interview.md").read_text(encoding="utf-8") == evals.fixture("interview-v3.md"))
    check("p, q BEFORE carry the v0.14.1 analyst (no re-check), AFTER the working tree's",
          all("--changed" not in (dry / f"{s}-before/.claude/agents/business-analyst.md").read_text(encoding="utf-8")
              and "NOT_REQUIRED" in (dry / f"{s}-before/.claude/agents/business-analyst.md").read_text(encoding="utf-8")
              and "--changed" in (dry / f"{s}-after/.claude/agents/business-analyst.md").read_text(encoding="utf-8") for s in ("p", "q")))
    critic_after = [(dry / f"prompt-{s}-after.txt").read_text(encoding="utf-8") for s in ("g", "h", "i", "l", "m", "n", "o")]
    check("every master-critic AFTER prompt carries the journal, before the draft",
          all("\njournal:\n" + evals.fixture("interview.md") in t and t.index("journal:") < t.index("draft:") for t in critic_after))
    check("v0.13.0's /master-architect passed no journal: no BEFORE prompt carries one",
          not any("\njournal:\n" in (dry / f"prompt-{s}-before.txt").read_text(encoding="utf-8") for s in ("g", "h", "i", "l", "m", "n", "o")))
    check("m: the sandbox has the interview where the critic may read it", (dry / "m-after/.engine/goals/interview.md").is_file()
          and (dry / "n-after/.engine/goals/interview.md").is_file())
    names = [p.name for p in dry.rglob("*") if "/.git/" not in str(p)]
    check("no fixture file name reaches a sandbox («clean», «rev2», «v1»)", not any(n for n in names if any(w in n for w in ("clean", "rev2", "-v1", "-v2"))))
    check("k-neg's sandbox has the clean map as the domain map, goals-v2 and the interview",
          (dry / "k-neg-after/.engine/architecture/domain-map.md").read_text(encoding="utf-8") == evals.fixture("domain-map-clean.md")
          and (dry / "k-neg-after/.engine/goals.md").read_text(encoding="utf-8") == evals.fixture("goals-v2.md")
          and (dry / "k-neg-after/.engine/goals/interview.md").is_file())
    check("e: the draft stands where the document will", (dry / "e-after/.engine/goals.md").read_text(encoding="utf-8") == evals.fixture("goals-v1.md"))
    before_def = (dry / "f-before/.claude/agents/business-analyst.md").read_text(encoding="utf-8")
    check("BEFORE carries the v0.13.0 analyst (no NOT_REQUIRED), AFTER the working tree's",
          "NOT_REQUIRED" not in before_def and "NOT_REQUIRED" in (dry / "f-after/.claude/agents/business-analyst.md").read_text(encoding="utf-8"))
    check("the consult prompt is the request's bare path", (dry / "prompt-f-before.txt").read_text(encoding="utf-8") == "[agent: business-analyst]\n.engine/goals/requests/003.md\n")
    j = (dry / "prompt-j-after.txt").read_text(encoding="utf-8")
    check("j: a plain session with the working tree's master-architect definition", j.startswith("[agent: none]") and "Читання цілей" in j
          and (dry / "j-after/docs/research/research-note.md").is_file())

print("sessions: a refused one is an error, a failed AFTER scene runs twice (shim, no cost)")
REFUSED = {"type": "result", "is_error": True, "result": "Failed to authenticate. API Error: 401", "total_cost_usd": 0, "num_turns": 1}
PASSED = {"type": "result", "is_error": False, "result": "GUARDIAN_PASS", "total_cost_usd": 0.1, "num_turns": 1}
with tempfile.TemporaryDirectory() as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    (tasks / "doing/501-x.md").write_text("# 501\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    env["EXTRA_SESSIONS_WEEK_USD"] = ""

    def shim(payload: dict[str, Any]) -> Path:
        path = Path(tmp) / "claude"
        path.write_text(f"#!/bin/sh\necho x >> {tmp}/calls\ncat <<'EOF'\n{json.dumps(payload)}\nEOF\n", encoding="utf-8")
        path.chmod(0o755)
        (Path(tmp) / "calls").unlink(missing_ok=True)
        return path

    out = Path(tmp) / "out.json"
    r = subprocess.run([sys.executable, str(RUNNER), "--scenes", "k-neg", "--tasks-dir", str(tasks), "--claude", str(shim(REFUSED)), "--out", str(out)],
                       capture_output=True, text=True, env=env, check=False)
    data = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    check("refused: an error row, no score, `no-results`, exit not 0",
          r.returncode != 0 and data.get("status") == "no-results" and "good" not in data["runs"][0] and "401" in data["runs"][0]["error"], r.stdout + r.stderr)
    r = subprocess.run([sys.executable, str(RUNNER), "--scenes", "k-neg", "--tasks-dir", str(tasks), "--claude", str(shim(PASSED)), "--out", str(out)],
                       capture_output=True, text=True, env=env, check=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    check("answered and good: one session, `complete`, exit 0",
          r.returncode == 0 and data["status"] == "complete" and len(data["runs"]) == 1 and data["runs"][0]["good"], r.stdout + r.stderr)
    r = subprocess.run([sys.executable, str(RUNNER), "--scenes", "k", "--tasks-dir", str(tasks), "--claude", str(shim(PASSED)), "--out", str(out)],
                       capture_output=True, text=True, env=env, check=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    check("not good after: a second attempt, both kept, the first counts for `complete`",
          [(x["attempt"], x["good"]) for x in data["runs"]] == [(1, False), (2, False)] and data["status"] == "complete"
          and len((Path(tmp) / "calls").read_text().split()) == 2, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, str(RUNNER), "--scenes", "k", "--tasks-dir", str(tasks), "--claude", str(shim(PASSED)), "--resume", str(out)],
                       capture_output=True, text=True, env=env, check=False)
    check("--resume runs nothing already recorded", not (Path(tmp) / "calls").exists() and r.returncode == 0, r.stdout + r.stderr)
    out.unlink()
    r = subprocess.run([sys.executable, str(RUNNER), "--scenes", "k-neg", "--twice", "k-neg", "--tasks-dir", str(tasks), "--claude", str(shim(PASSED)), "--out", str(out)],
                       capture_output=True, text=True, env=env, check=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    check("--twice: a good first AFTER still gets a second attempt",
          [(x["attempt"], x["good"]) for x in data["runs"]] == [(1, True), (2, True)] and r.returncode == 0, r.stdout + r.stderr)
    out.unlink()
    r = subprocess.run([sys.executable, str(RUNNER), "--scenes", "k-neg", "--tasks-dir", str(tasks), "--claude", str(shim(PASSED)), "--out", str(out)],
                       capture_output=True, text=True, env=env, check=False)
    check("without --twice a good first AFTER is not repeated", len(json.loads(out.read_text(encoding="utf-8"))["runs"]) == 1, r.stdout + r.stderr)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
