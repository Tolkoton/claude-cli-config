#!/usr/bin/env python3
"""The simplifier eval: the fixture says what it claims, the scorer counts honestly, no session
starts without the owner's word. No model is called here.

Run:   python3 tests/test_simplifier_evals.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals" / "run_simplifier_evals.py"
FIXTURE = ROOT / "evals" / "scenarios" / "simplifier"
spec = importlib.util.spec_from_file_location("run_simplifier_evals", RUNNER)
assert spec and spec.loader
runner: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def finding(target: str, claim: str, action: str = "confirm", category: str = "dead_code") -> dict[str, Any]:
    return {"target": target, "category": category, "claim": claim, "proposed_action": action,
            "evidence": [{"source": "judgement", "ref": "", "detail": ""}]}


expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))

print("FIXTURE-* expected.json describes the project that is really there")
check("six kinds of planted excess, four traps", len(expected["planted"]) == 6 and len(expected["traps"]) == 4, expected)
work = Path(tempfile.mkdtemp(prefix="engine-simplifier-evaltest-"))
sandbox = runner.build_sandbox(work / "project")
for entry in expected["planted"] + expected["traps"] + expected["also_true"]:
    texts = [(sandbox / f).read_text(encoding="utf-8") for f in entry["files"] if (sandbox / f).is_file()]
    check(f"{entry['id']}: its files exist and carry one of its words",
          len(texts) == len(entry["files"]) and any(word in text for word in entry["any"] for text in texts), entry)
request = runner.request_text(sandbox, expected["scope"])
check("the request carries the deterministic leads for the dead code and the unused dependency",
      "_legacy_total_v1" in request and "requests is declared" in request and "LENS: code, requirements, architecture" in request, request[:600])
trap_words = ("parse_order_line", "load_price_list", "receipt_path", "refund_reference")
check("no deterministic signal points at a trap", not any(word in request for word in trap_words), request)
check("the agent's own definition is in the sandbox", (sandbox / ".claude/agents/simplifier.md").is_file())
tests = subprocess.run(["uvx", "--with", "pytest", "pytest", "-q", "-p", "no:cacheprovider"], cwd=sandbox,
                       capture_output=True, text=True, check=False)
check("the project under review is a working project: its own tests pass", tests.returncode == 0, tests.stdout[-300:])

print("SCORE-*   recall, precision, traps touched")
perfect = [
    finding("src/refproj/discounts.py:9", "DiscountPolicy has one implementation", category="premature_abstraction"),
    finding("src/refproj/pricing.py:24", "_legacy_total_v1 has no caller", "auto_remove"),
    finding("pyproject.toml:6", "requests is never imported", category="redundant_dependency"),
    finding("src/refproj/pricing.py:14", "the factor < 0 guard cannot fire", category="defensive_for_impossible"),
    finding(".engine/slices/currency-rates.md", "currency conversion serves no goal", category="speculative_slice"),
    finding("docs/goals.md:22", "R6 traces to no goal", category="invented_requirement"),
]
s = runner.score(perfect, expected)
check("all six found, nothing else: recall 1, precision 1, no trap", (s["recall"], s["precision"], s["traps_touched"], s["missed"]) == (1.0, 1.0, 0, []), s)
s = runner.score(perfect[:3], expected)
check("three of six: recall 0.5, the missed ones are named", s["recall"] == 0.5 and len(s["missed"]) == 3 and "invented-requirement" in s["missed"], s)
s = runner.score(perfect[:2] + [finding("src/refproj/receipts.py:11", "the is_relative_to check is redundant", "flag_only")], expected)
check("a trap named even as flag_only counts as touched, and lowers precision",
      s["traps_touched"] == 1 and s["touched"][0]["trap"] == "security-check" and s["precision"] == 0.667, s)
for target, claim, trap in (
        ("src/refproj/orders.py:33", "quantity is checked again in reserve()", "input-validation-at-the-edge"),
        ("src/refproj/orders.py:42", "load_price_list wraps errors nobody raises", "error-handling-at-the-edge"),
        ("src/refproj/orders.py:22", "refund_reference is hardly read", "contract-field-read-on-a-rare-path")):
    s = runner.score([finding(target, claim)], expected)
    check(f"{trap} is recognised", s["traps_touched"] == 1 and s["touched"][0]["trap"] == trap, s)
s = runner.score(perfect[:1] + [finding("src/refproj/inventory.py:25", "reserved_value has no production caller")], expected)
check("excess the reference project already had counts for precision, not for recall",
      s["precision"] == 1.0 and s["recall"] == round(1 / 6, 3) and s["traps_touched"] == 0, s)
s = runner.score(perfect[:1] + [finding("src/refproj/cli.py:14", "ON_HAND could be inlined")], expected)
check("a finding about nothing planted is unexpected and lowers precision", s["precision"] == 0.5 and len(s["unexpected"]) == 1, s)
s = runner.score(perfect[:1] * 3, expected)
check("the same planted item found three times is one item of recall", s["recall"] == round(1 / 6, 3) and s["precision"] == 1.0, s)
check("an empty answer: recall 0, precision undefined", runner.score([], expected)["precision"] is None)
check("a summary skips a failed run and adds its cost",
      runner.summary([{"error": "x", "cost_usd": 1.0}, {**runner.score(perfect, expected), "cost_usd": 2.0}])
      == {"runs": 2, "scored": 1, "recall_mean": 1.0, "precision_mean": 1.0, "traps_touched_total": 0, "cost_usd": 3.0})

print("PAID-*    no session without the owner's word")
board = work / "tasks"
(board / "doing").mkdir(parents=True)
check("no task in doing/: refused", runner.paid_run_refusal(board, False, True) is not None)
(board / "doing" / "010-x.md").write_text("# 010\n\nАудит потрібен: ні\n")
check("a task without the line: refused", runner.paid_run_refusal(board, False, True) is not None)
check("--owner-approved inside a session does not count", "does not count" in str(runner.paid_run_refusal(board, True, True)))
check("--owner-approved in the owner's terminal: allowed", runner.paid_run_refusal(board, True, False) is None)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: лише евалуація, не більше 30 доларів.\n")
check("the task's «Платні прогони» line with a dollar limit: allowed", runner.paid_run_refusal(board, False, True) is None)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: ні.\n")
check("the line without a dollar limit: refused", runner.paid_run_refusal(board, False, True) is not None)
shim = work / "claude"
shim.write_text("#!/bin/sh\necho started >> \"$(dirname \"$0\")/started\"\n")
shim.chmod(0o755)
done = subprocess.run([sys.executable, str(RUNNER), "--runs", "1", "--tasks-dir", str(board), "--claude", str(shim)],
                      capture_output=True, text=True, check=False, env={**os.environ, "CLAUDECODE": "1"})
check("the runner itself refuses with exit 2 and starts nothing",
      done.returncode == 2 and "refusing to start paid sessions" in done.stderr and not (work / "started").exists(), done.stderr)

shutil.rmtree(work, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
