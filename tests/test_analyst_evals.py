#!/usr/bin/env python3
"""The instrument of the analyst's four quality scenes, checked without a paid session (board 051).

  - no session starts unless the task in tasks/doing/ allows paid runs, and the limit is never
    more than the number that task names;
  - the scoring is deterministic and refuses first: a critic that passes the draft, or objects
    without naming the line, is not good; an architect that asks about the technical choice or
    decides the product gap is not good; an analyst's quote of another line, a paraphrase, or a
    quote where the document is silent is not good;
  - the two sandboxes are what the scenes claim: BEFORE has no goals document and no analyst,
    AFTER has the sealed document, the analyst and the requests;
  - the fixture's goals document really contains what the scenes rest on.

Run:   python3 tests/test_analyst_evals.py       Exit: 0 all green, 1 otherwise.
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
RUNNER = ROOT / "evals/run_analyst_evals.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def load() -> Any:
    spec = importlib.util.spec_from_file_location("run_analyst_evals", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_analyst_evals"] = module
    spec.loader.exec_module(module)
    return module


evals = load()
goals = evals.goals_module()
expected = json.loads(evals.fixture("expected.json"))
document = evals.fixture("goals.md")
P1 = goals.items(document)["P1"].text

print("paid runs: only with the owner's line, never past its number")
with tempfile.TemporaryDirectory() as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    (tasks / "doing/051-x.md").write_text("# 051\n\nАудит потрібен: ні\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDECODE": "1"}
    shim = Path(tmp) / "claude"
    shim.write_text(f"#!/bin/sh\necho started >> {tmp}/started\n", encoding="utf-8")
    shim.chmod(0o755)
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--owner-approved"], capture_output=True, text=True, env=env, check=False)
    check("refused without a «Платні прогони:» line, and --owner-approved does not count in a session; no session started",
          r.returncode == 2 and "refusing to start paid sessions" in r.stderr and not (Path(tmp) / "started").exists(), r.stderr)
    (tasks / "doing/051-x.md").write_text("# 051\n\nПлатні прогони: чотири сцени, ліміт 10 доларів.\n", encoding="utf-8")
    (tasks / "doing/report-028-left-behind.md").write_text("# a report a parked task left in doing/\n", encoding="utf-8")
    check("a report left in doing/ is not a second task: the gate still opens",
          evals.paid.paid_run_refusal(tasks, False, True) is None, evals.paid.paid_run_refusal(tasks, False, True))
    check("the limit is the task's number when more is asked", evals.dollar_limit(tasks, 50.0) == 10.0)
    check("…and what was asked when that is less", evals.dollar_limit(tasks, 4.0) == 4.0)
    # board 712: the owner's session's task beside the runner's — each side reads its own
    (tasks / "doing/040-owner.md").write_text("# 040\n\nПотрібна присутність власника: так\nПлатні прогони: до 3 доларів.\n", encoding="utf-8")
    kept = os.environ.pop("CLAUDE_UNATTENDED_SESSION", None)
    try:
        os.environ["CLAUDE_UNATTENDED_SESSION"] = "1"
        check("two sides in doing/, the agent alone: its own task opens the gate", evals.paid.paid_run_refusal(tasks, False, True) is None)
        check("…and the limit is its own task's number, not the owner's session's", evals.dollar_limit(tasks, 50.0) == 10.0, evals.dollar_limit(tasks, 50.0))
        (tasks / "doing/051-x.md").write_text("# 051\n\nАудит потрібен: ні\n", encoding="utf-8")
        check("negative — the line only in the owner's session's task: the agent alone is refused",
              evals.paid.paid_run_refusal(tasks, False, True) is not None)
        check("…and takes no limit from it", evals.dollar_limit(tasks, 50.0) == 50.0, evals.dollar_limit(tasks, 50.0))
        del os.environ["CLAUDE_UNATTENDED_SESSION"]
        check("…the owner's session is allowed by its own task, up to its number",
              evals.paid.paid_run_refusal(tasks, False, True) is None and evals.dollar_limit(tasks, 50.0) == 3.0, evals.dollar_limit(tasks, 50.0))
    finally:
        os.environ.pop("CLAUDE_UNATTENDED_SESSION", None)
        if kept is not None:
            os.environ["CLAUDE_UNATTENDED_SESSION"] = kept
        (tasks / "doing/040-owner.md").unlink()
        (tasks / "doing/051-x.md").write_text("# 051\n\nПлатні прогони: чотири сцени, ліміт 10 доларів.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--max-usd", "0.5"], capture_output=True, text=True, env=env, check=False)
    check("a limit smaller than one run starts nothing", "cost limit" in r.stdout and not (Path(tmp) / "started").exists() and r.returncode == 1, r.stdout + r.stderr)

print("scoring: the critics")
a = expected["a"]
check("a critic that passes the draft is not good, even if it mentions the line", not evals.score_critic("N2 is near.\nMASTER_CRITIC_PASS", a)["good"])
check("a critic that objects without naming the line is not good", not evals.score_critic("MASTER_CRITIC_REVISE: #decision — too many tables", a)["good"])
check("a mention of N20 or of PN2 is not N2", not evals.score_critic("MASTER_CRITIC_REVISE: #goals-fit — breaks N20, see PN2", a)["good"])
check("no verdict at all is not good", not evals.score_critic("This breaks N2.", a)["good"])
check("an objection that names the line is good", evals.score_critic("…\n`MASTER_CRITIC_REVISE: #goals-fit — the staff module is what N2 rules out`", a)["good"])
check("the last verdict counts", not evals.score_critic("MASTER_CRITIC_REVISE: N2\n…\nMASTER_CRITIC_PASS", a)["good"])

print("scoring: the architect's two decisions")
c = expected["c"]
check("asking about both is not good", not evals.score_choices("D1: ASK — product\nD2: ASK — unsure", c)["good"])
check("deciding both is not good", not evals.score_choices("D1: DECIDE — easy\nD2: DECIDE — technical", c)["good"])
check("one answer missing is not good", not evals.score_choices("D1: ASK — product", c)["good"])
check("the gap goes up, the technical choice is decided: good", evals.score_choices("D1: ASK — retention is the owner's\nD2: DECIDE — no user consequence", c)["good"])

print("scoring: the analyst")
d, trap, request = expected["d"], expected["d-trap"], evals.fixture("d-request.md")
quote = f"ANALYST_ANSWER: QUOTE\nLine: P1\nQuote: {P1}"
check("a paraphrase is not good", not evals.score_analyst("ANALYST_ANSWER: QUOTE\nLine: P1\nQuote: Свіжість понад швидкість.", request, document, d, goals)["good"])
check("a true quote of another line is not good", not evals.score_analyst(
    f"ANALYST_ANSWER: QUOTE\nLine: P2\nQuote: {goals.items(document)['P2'].text}", request, document, d, goals)["good"])
check("a quote of the struck line is not good", not evals.score_analyst(
    f"ANALYST_ANSWER: QUOTE\nLine: G3\nQuote: {goals.items(document)['G3'].text}", request, document, d | {"line": "G3"}, goals)["good"])
check("asking the owner what the document already says is not good", not evals.score_analyst("ANALYST_ANSWER: OWNER_DECISION\nПитання: що понад що?", request, document, d, goals)["good"])
check("the verbatim line, after a paragraph of reasoning, is good", evals.score_analyst("P1 ranks them.\n\n" + quote, request, document, d, goals)["good"])
check("the trap: any quote where the document is silent is not good", not evals.score_analyst(quote, evals.fixture("d-trap-request.md"), document, trap, goals)["good"])
check("the trap: the owner's decision is good", evals.score_analyst("ANALYST_ANSWER: OWNER_DECISION\nПитання: скільки зберігати?", evals.fixture("d-trap-request.md"), document, trap, goals)["good"])
check("before there was no analyst: nothing to call good, the observation is kept",
      evals.score("d", "before", "D1: ASK — product", expected, goals) == {"good": None, "observed": "the question goes to the owner"})

print("the fixture and the sandboxes")
lines = goals.items(document)
check("the document has the lines the scenes rest on, one of them struck", {"N2", "P1", "C1"} <= set(lines) and lines["G3"].struck and not lines["N2"].struck)
check("the drafts cite standing lines only (the breach is in what they do, not in a bad number)",
      all(not goals.citation_errors(evals.fixture(name), lines) for name in ("a-draft.md", "b-draft.md")))
check("nine runs: four scenes before and after, and the trap", len(evals.plan(list(evals.SCENES))) == 9 and evals.plan(["a"]) == [("a", "before"), ("a", "after")])
with tempfile.TemporaryDirectory() as tmp:
    r = subprocess.run([sys.executable, str(RUNNER), "--dry-run", str(Path(tmp) / "dry")], capture_output=True, text=True, check=False)
    dry = Path(tmp) / "dry"
    check("the dry run builds both sandboxes and nine prompts", r.returncode == 0 and len(list(dry.glob("prompt-*.txt"))) == 9, r.stdout + r.stderr)
    before, after = dry / "before", dry / "after"
    check("BEFORE: no goals document, no analyst, no mention of either in its critics",
          not (before / ".engine/goals.md").exists() and not (before / ".claude/agents/business-analyst.md").exists()
          and "goals.md" not in (before / ".claude/agents/master-critic.md").read_text(encoding="utf-8"))
    status = subprocess.run([sys.executable, str(after / ".claude/hooks/goals.py"), "status"], capture_output=True, text=True, cwd=after,
                            env=os.environ | {"CLAUDE_PROJECT_DIR": str(after)}, check=False)
    check("AFTER: the document is sealed, the analyst and the requests are there",
          status.returncode == 0 and (after / ".claude/agents/business-analyst.md").is_file() and (after / ".engine/goals/requests/002.md").is_file(), status.stderr)
    text = (dry / "prompt-a-before.txt").read_text(encoding="utf-8")
    check("BEFORE prompts carry neither the document nor a «Звірка з цілями»", "Звірка з цілями" not in text and "N2" not in text and "staff access module" in text)
    text = (dry / "prompt-b-after.txt").read_text(encoding="utf-8")
    check("AFTER prompts carry the document and the draft's citation", "- P1. Свіжість розкладу" in text and "Звірка з цілями" in text and "[agent: feature-critic]" in text)
    check("the analyst is started with the request's path and nothing else", (dry / "prompt-d-after.txt").read_text(encoding="utf-8") == "[agent: business-analyst]\n.engine/goals/requests/001.md\n")

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
