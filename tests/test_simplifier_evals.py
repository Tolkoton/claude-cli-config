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
      == {"runs": 2, "scored": 1, "recall_mean": 1.0, "recall_range": [1.0, 1.0], "precision_mean": 1.0,
          "precision_range": [1.0, 1.0], "traps_touched_total": 0, "ambiguous_total": 0, "read_by_hand_total": 0,
          "found_in_runs": {e["id"]: 1 for e in sorted(expected["planted"], key=lambda e: e["id"])},
          "touched_in_runs": {}, "touched_proposed": {}, "touched_after_validator": {}, "cost_usd": 3.0})
trap_run = perfect[:3] + [finding("src/refproj/receipts.py:11", "the is_relative_to check is redundant"),
                          finding("src/refproj/receipts.py:9", "receipt_path resolves twice")]
s = runner.summary([{**runner.score(perfect, expected), "cost_usd": 1.0}, {**runner.score(trap_run, expected), "cost_usd": 1.0}])
check("board 059 — the spread of several runs: the lowest and highest recall and precision, per item and per trap",
      (s["recall_range"], s["precision_range"]) == ([0.5, 1.0], [0.6, 1.0]) and s["found_in_runs"]["dead-code"] == 2
      and s["found_in_runs"]["invented-requirement"] == 1 and s["touched_in_runs"] == {"security-check": 1}, s)
check("…and a summary of no scored run has no spread", runner.summary([{"error": "x", "cost_usd": 1.0}])["recall_range"] is None)

print("HARD-*    board 059 — the harder set: subtler excess, more traps, neutral entries")
hard_dir = runner.SETS["hard"]
hard = json.loads((hard_dir / "expected.json").read_text(encoding="utf-8"))
check("seven planted, ten traps, and it is another project than the basic one",
      len(hard["planted"]) == 7 and len(hard["traps"]) == 10 and hard_dir != FIXTURE and runner.SETS["basic"] == FIXTURE, hard_dir)
hard_box = runner.build_sandbox(work / "hard", hard_dir)
for entry in hard["planted"] + hard["traps"] + hard["also_true"] + hard["neutral"]:
    texts = [(hard_box / f).read_text(encoding="utf-8") for f in entry["files"] if (hard_box / f).is_file()]
    check(f"hard / {entry['id']}: its files exist and carry one of its words",
          len(texts) == len(entry["files"]) and any(word in text for word in entry["any"] for text in texts) and entry["why"], entry)
check("the basic project is not the hard one: no wholesale branch there, no DiscountPolicy with two implementations",
      "wholesale" not in (sandbox / "src/refproj/cli.py").read_text() and "wholesale" in (hard_box / "src/refproj/cli.py").read_text())
source = {rel: (hard_box / rel).read_text(encoding="utf-8") for rel in
          ("src/refproj/cli.py", "src/refproj/discounts.py", "src/refproj/refunds.py", "pyproject.toml")}
callers = subprocess.run(["grep", "-rn", "--include=*.py", "-e", "wholesale=", "-e", "FixedAmountDiscount(", "-e", "import yaml", str(hard_box / "src"), str(hard_box / "tests")],
                         capture_output=True, text=True, check=False).stdout.replace(str(hard_box) + "/", "")
check("the excess is what expected.json says: nobody passes wholesale, only tests build FixedAmountDiscount or import yaml",
      "wholesale=" not in callers and "FixedAmountDiscount(" in callers and "import yaml" in callers
      and all(line.startswith("tests/") for line in callers.splitlines() if ":class " not in line) and "pyyaml" in source["pyproject.toml"], callers)
check("the gate's note in the fixture's pyproject does not reach the project the simplifier reads",
      "gate-allow" in (hard_dir / "project/pyproject.toml").read_text() and "gate-allow" not in (hard_box / "pyproject.toml").read_text()
      and (hard_box / "pyproject.toml").read_text() + next(line + "\n" for line in (hard_dir / "project/pyproject.toml").read_text().splitlines()
                                                           if "gate-allow" in line) == (hard_dir / "project/pyproject.toml").read_text())
hard_request = runner.request_text(hard_box, hard["scope"])
hard_trap_words = ("parse_order_line", "load_price_list", "receipt_path", "refund_reference", "pin_matches", "ReceiptError",
                   "export_record", "CURRENCY", "isinstance", "stock-levels")
check("hard: no deterministic signal points at a trap", not any(word in hard_request for word in hard_trap_words), hard_request)
check("hard: the signals do not name the subtle excess — the dead branch, the second implementation, the duplicate",
      not any(word in hard_request for word in ("wholesale", "FixedAmountDiscount", "refund_amount", "on_hand")), hard_request)
tests = subprocess.run(["uvx", "--with", "pytest", *(part for name in hard["test_with"] for part in ("--with", name)),
                        "pytest", "-q", "-p", "no:cacheprovider"], cwd=hard_box, capture_output=True, text=True, check=False)
check("hard: the project under review is a working project: its own tests pass", tests.returncode == 0, tests.stdout[-300:])
hard_perfect = [
    finding("src/refproj/discounts.py:27", "FixedAmountDiscount is built only by its test", category="premature_abstraction"),
    finding("src/refproj/cli.py:22", "the wholesale branch: nobody passes the flag"),
    finding("src/refproj/refunds.py:15", "refund_amount repeats the loop of charge", category="duplication"),
    finding("pyproject.toml:6", "pyyaml is imported by one test only", category="redundant_dependency"),
    finding("src/refproj/cli.py:30", "left.on_hand < 0 cannot be true after reserve()", category="defensive_for_impossible"),
    finding("docs/goals.md:27", "R7: nobody asked for a PDF", category="invented_requirement"),
    finding(".engine/slices/price-list-cache.md", "the cache is for a list nobody has yet", category="speculative_slice"),
]
s = runner.score(hard_perfect, hard)
check("hard: all seven found, nothing else: recall 1, precision 1, no trap",
      (s["recall"], s["precision"], s["traps_touched"], s["missed"]) == (1.0, 1.0, 0, []), s)
for target, claim, trap in (
        ("src/refproj/orders.py:28", "parse_order_line checks quantity twice", "input-validation-at-the-edge"),
        ("src/refproj/orders.py:45", "the JSONDecodeError branch has no test", "error-handling-at-the-edge"),
        ("src/refproj/receipts.py:38", "the OSError handler is never exercised", "rare-error-at-the-boundary"),
        ("src/refproj/receipts.py:18", "is_relative_to repeats what the caller knows", "security-check-path"),
        ("src/refproj/refunds.py:12", "hmac.compare_digest where == would do", "security-check-constant-time"),
        ("src/refproj/orders.py:21", "refund_reference is hardly read", "contract-field-read-on-a-rare-path"),
        ("src/refproj/receipts.py:8", "CURRENCY never varies and nothing reads it", "contract-field-for-another-service"),
        ("src/refproj/orders.py:47", "the isinstance(raw, list) branch has no test", "old-data-format"),
        ("docs/goals.md:25", "R6 was not stated by the owner", "requirement-derived-at-planning"),
        (".engine/slices/stock-levels.md", "S6 is not built: speculative", "slice-a-goal-needs")):
    s = runner.score([finding(target, claim)], hard)
    check(f"hard / {trap} is recognised when touched", s["traps_touched"] == 1 and s["touched"][0]["trap"] == trap, s)
s = runner.score(hard_perfect[:1] + [finding("src/refproj/inventory.py:19", "reserve repeats the quantity must be positive check"),
                                     finding("src/refproj/cli.py:18", "ON_HAND is a constant")], hard)
check("a neutral entry is counted neither way: precision stays 1, no trap, nothing unexpected",
      s["precision"] == 1.0 and s["traps_touched"] == 0 and len(s["neutral"]) == 2 and not s["unexpected"] and s["findings"] == 3, s)
s = runner.score([finding("src/refproj/inventory.py:19", "reserve repeats the quantity must be positive check")], hard)
check("negative — only neutral findings: precision is undefined, not 0 and not 1", s["precision"] is None and s["recall"] == 0.0, s)
s = runner.score([finding("src/refproj/inventory.py:19", "reserve repeats the quantity must be positive check")], expected)
check("negative — the basic set has no neutral list: the same finding there is unexpected", len(s["unexpected"]) == 1 and s["precision"] == 0.0, s)
s = runner.score(hard_perfect[:1] + [finding("src/refproj/pricing.py:6", "CENT could be inlined")], hard)
check("hard: a finding about nothing listed is unexpected and lowers precision", s["precision"] == 0.5 and len(s["unexpected"]) == 1, s)
guard = finding("src/refproj/cli.py:33-34", "the left.on_hand < 0 check can go", category="defensive_for_impossible")
guard["evidence"] = [{"source": "read", "ref": "tests/test_inventory.py:14", "detail": "pins the behaviour the guard duplicates"}]
s = runner.score([guard], hard)
check("a finding is not given to another planted item for one loose word: the guard whose evidence says «duplicates» is the guard "
      "(the first paid run, session 3, counted it as the duplication)", list(s["found"]) == ["guard-impossible-across-functions"], s)
both = finding("src/refproj/cli.py:32-37", "the wholesale branch and the on_hand < 0 guard", category="defensive_for_impossible")
check("…and of two planted items a finding names, the one of its own category is taken; without such a one, the first",
      list(runner.score([both], hard)["found"]) == ["guard-impossible-across-functions"]
      and list(runner.score([{**both, "category": "shallow_module"}], hard)["found"]) == ["dead-branch-behind-a-flag"], runner.score([both], hard))
print("TWIN-*    a trap beside a planted item is not hidden by it (the overseer's BLOCK no.4 on board 059)")
for entry in hard["planted"] + hard["traps"] + hard["neutral"]:
    for rel, ranges in entry.get("lines", {}).items():
        rows = (hard_box / rel).read_text(encoding="utf-8").splitlines()
        check(f"hard / {entry['id']}: every line range named in {rel} carries one of its words",
              rel in entry["files"] and all(any(w.lower() in "\n".join(rows[a - 1:b]).lower() for w in entry["any"]) for a, b in ranges), ranges)
for target, claim, detail, trap in (
        ("docs/goals.md:25", "R6 and R7 are both marked planning, not owner: both can be dropped", "", "requirement-derived-at-planning"),
        ("docs/goals.md:25-26", "written at planning like R7; the is_relative_to check it stands for can go", "", "requirement-derived-at-planning"),
        (".engine/architecture/feature-dag.json:10", "S6 and S7 are not built and can both be dropped", "", "slice-a-goal-needs"),
        ("src/refproj/refunds.py:12", "hmac.compare_digest where == would do", "refund_amount is the only caller's neighbour", "security-check-constant-time"),
        ("src/refproj/cli.py:43", "pin_matches can go, like the wholesale branch", "", "security-check-constant-time"),
        ("src/refproj/cli.py:61", "the ReceiptError catch can go, like the RuntimeError guard", "", "rare-error-at-the-boundary"),
        ("src/refproj/refunds.py:24-28", "refund_note duplicates what refund_amount knows", "", "contract-field-read-on-a-rare-path")):
    f = finding(target, claim)
    f["evidence"] = [{"source": "judgement", "ref": "", "detail": detail}]
    s = runner.score([f], hard)
    check(f"aimed at the trap's own lines and naming the planted neighbour: {trap} is touched, nothing is found — {target}",
          s["traps_touched"] == 1 and s["touched"][0]["trap"] == trap and not s["found"] and s["recall"] == 0.0 and s["precision"] == 0.0, s)
print("TWIN-2-*  the other direction (the overseer's second BLOCK no.4): aimed at the planted item's line, naming the trap too")
for target, claim, planted_id, trap in (
        ("docs/goals.md:27", "R6 and R7 are both marked planning, not owner: both can be dropped", "requirement-with-a-borrowed-goal", "requirement-derived-at-planning"),
        (".engine/architecture/feature-dag.json:11", "S6 and S7 are not built and can both be dropped", "slice-for-later-with-a-goal-tag", "slice-a-goal-needs"),
        ("src/refproj/cli.py:33-34", "the RuntimeError guard and the ReceiptError catch can both go", "guard-impossible-across-functions", "rare-error-at-the-boundary"),
        ("src/refproj/refunds.py:15-21", "refund_amount and pin_matches are both more than is needed: remove both", "duplication-with-small-differences", "security-check-constant-time"),
        ("src/refproj/cli.py:36", "the wholesale branch and the pin_matches check can go", "dead-branch-behind-a-flag", "security-check-constant-time"),
        ("docs/goals.md:27", "R7 goes beyond G3, which R5 and R6 already deliver", "requirement-with-a-borrowed-goal", "requirement-derived-at-planning")):
    s = runner.score([{**finding(target, claim), "id": "F-1"}], hard)
    check(f"on the planted item's line with the trap's word in it: ambiguous, whichever it means — not found, not a silent zero — {target} «{claim[:40]}»",
          not s["found"] and s["traps_touched"] == 0 and s["precision"] is None
          and [(a["id"], a["planted"], a["trap"]) for a in s["ambiguous"]] == [("F-1", planted_id, trap)], s)
benign = {**finding("docs/goals.md:27", "R7 goes beyond G3, which R5 and R6 already deliver", category="invented_requirement"), "id": "F-ok"}
both_go = {**finding("docs/goals.md:27", "R6 and R7 are both marked planning: both can be dropped"), "id": "F-bad"}
by_hand = {"F-ok": {"as": "planted", "why": "R6 is named as what stays"}, "F-bad": {"as": "trap", "why": "it drops R6 too"}}
s = runner.score([benign, both_go], hard, by_hand)
check("read by hand, each ambiguous finding is counted as the reader said — and the row keeps who decided and why",
      list(s["found"]) == ["requirement-with-a-borrowed-goal"] and s["traps_touched"] == 1 and s["touched"][0]["trap"] == "requirement-derived-at-planning"
      and s["precision"] == 0.5 and not s["ambiguous"] and sorted((r["id"], r["as"], r["why"]) for r in s["resolved"])
      == [("F-bad", "trap", "it drops R6 too"), ("F-ok", "planted", "R6 is named as what stays")], s)
s = runner.score([benign, both_go], hard, {"F-ok": by_hand["F-ok"]})
check("negative — a reading covers only the finding it names: the other stays ambiguous", len(s["ambiguous"]) == 1 and s["ambiguous"][0]["id"] == "F-bad"
      and len(s["resolved"]) == 1, s)
s = runner.score([{**finding("src/refproj/discounts.py:27", "FixedAmountDiscount is built only by its test"), "id": "F-ok"}], hard, by_hand)
check("negative — a reading cannot touch a finding that is not ambiguous", list(s["found"]) == ["abstraction-almost-used"] and not s["resolved"], s)
s = runner.score([finding("src/refproj/cli.py:18", "ON_HAND and the pin_matches check can go")], hard)
check("on a neutral entry's line, a trap named in words is still a trap touched — the line of something harmless hides nothing",
      s["traps_touched"] == 1 and s["touched"][0]["trap"] == "security-check-constant-time" and not s["neutral"], s)
s = runner.summary([{**runner.score([benign, both_go], hard, by_hand), "cost_usd": 1.0}])
check("the summary says how many findings were counted by a reader's word", s["read_by_hand_total"] == 2 and s["ambiguous_total"] == 0, s)
s = runner.score([{**finding("docs/goals.md:25:27", "R6 can go"), "id": "F-2"}], hard)
check("a target written path:line:column is read by its line, not by its column", s["traps_touched"] == 1 and not s["found"], s)
for target, claim in (("docs/goals.md", "R6 and R7 are both marked planning: both can be dropped"),
                      ("docs/goals.md:25-27", "the two planning requirements can be dropped"),
                      (".engine/architecture/feature-dag.json", "S6 and S7 are not built: drop both slices"),
                      ("src/refproj/cli.py", "pin_matches can go, like the wholesale branch")):
    s = runner.score(hard_perfect[:1] + [finding(target, claim)], hard)
    check(f"no line, or a range over both twins: the finding is ambiguous — in neither recall nor precision, never a silent zero — {target}",
          len(s["ambiguous"]) == 1 and s["ambiguous"][0]["trap"] and s["ambiguous"][0]["planted"] and list(s["found"]) == ["abstraction-almost-used"]
          and s["traps_touched"] == 0 and s["precision"] == 1.0, s)
s = runner.score([finding("src/refproj/cli.py:22", "the wholesale branch: nobody passes the flag")], hard)
check("a line no entry owns (one off, a blank line) falls back to the words: the finding is not lost", list(s["found"]) == ["dead-branch-behind-a-flag"], s)
s = runner.score([finding("src/refproj/cli.py:16", "ON_HAND is a constant")], hard)
check("negative — the line wins over the words: a finding on the PIN check's line is that trap, whatever it talks about",
      s["traps_touched"] == 1 and s["touched"][0]["trap"] == "security-check-constant-time", s)
s = runner.summary([{**runner.score(hard_perfect + [finding("docs/goals.md", "R6 and R7 can both be dropped")], hard), "cost_usd": 1.0}])
check("the summary counts the ambiguous findings, so a run that needs reading by hand says so", s["ambiguous_total"] == 1, s)
check("…and it is 0, not absent, when there is none", runner.summary([{**runner.score(hard_perfect, hard), "cost_usd": 1.0}])["ambiguous_total"] == 0)
check("the basic set, which names no lines, scores a planted item as before", runner.score(perfect, expected)["recall"] == 1.0
      and runner.score(perfect, expected)["ambiguous"] == [])
s = runner.score([finding("src/refproj/pricing.py:14", "the factor < 0 guard and _legacy_total_v1")], expected)
check("…and a line-less entry still matches by its words whatever line the finding names", "guard-against-impossible-state" in s["found"] or "dead-code" in s["found"], s)
recorded = work / "recorded.json"
answer = [{**f, "protected": False, "chesterton_checked": True, "test_safety": "none", "traceability": "none found",
           "reversal_risk": "low"} for f in hard_perfect[:2] + [guard]]
recorded.write_text(json.dumps({"set": "hard", "summary": {"recall_mean": 0.0}, "runs": [
    {"cost_usd": 1.5, "recall": 0.0, "found": {"duplication-with-small-differences": ["confirm"]}, "answer": answer, "turns": 30},
    {"cost_usd": 0.5, "error": "the session gave no result: TimeoutExpired"}]}))
done = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(recorded)], capture_output=True, text=True, check=False)
again = json.loads(recorded.read_text())
check("--rescore counts the recorded answers again by the present expected.json, free: the scores and the summary change, "
      "the answers, the costs, the failed run and the set stay",
      done.returncode == 0 and sorted(again["runs"][0]["found"]) == ["abstraction-almost-used", "dead-branch-behind-a-flag", "guard-impossible-across-functions"]
      and again["runs"][0]["recall"] == round(3 / 7, 3) and again["runs"][0]["answer"] == answer and again["runs"][0]["turns"] == 30
      and "error" in again["runs"][1] and again["summary"]["cost_usd"] == 2.0 and again["summary"]["scored"] == 1
      and again["rescored_utc"] and again["set"] == "hard", done.stdout + done.stderr)
recorded.write_text(json.dumps({"set": "hard", "read_by_hand": {"F-ok": by_hand["F-ok"]}, "runs": [{"cost_usd": 1.0, "answer": [benign, both_go]}]}))
done = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(recorded)], capture_output=True, text=True, check=False)
again = json.loads(recorded.read_text())
check("--rescore applies the file's `read_by_hand`, and exits 1 while a finding is still ambiguous",
      done.returncode == 1 and again["summary"]["ambiguous_total"] == 1 and list(again["runs"][0]["found"]) == ["requirement-with-a-borrowed-goal"]
      and again["read_by_hand"] == {"F-ok": by_hand["F-ok"]}, done.stdout + done.stderr)
recorded.write_text(json.dumps({"set": "hard", "read_by_hand": by_hand, "runs": [{"cost_usd": 1.0, "answer": [benign]}]}))
done = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(recorded)], capture_output=True, text=True, check=False)
check("…and exits 0 when every ambiguous finding was read and no trap is touched", done.returncode == 0
      and json.loads(recorded.read_text())["summary"]["ambiguous_total"] == 0, done.stdout + done.stderr)
recorded.write_text(json.dumps({"set": "hard", "read_by_hand": {"F-ok": {"as": "fine", "why": "x"}}, "runs": [{"cost_usd": 1.0, "answer": [benign]}]}))
before = recorded.read_text()
done = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(recorded)], capture_output=True, text=True, check=False)
check("negative — a reading that says neither «planted» nor «trap», or gives no reason, is refused and the file is not rewritten",
      done.returncode == 2 and "read_by_hand" in done.stderr and recorded.read_text() == before, done.stdout + done.stderr)
recorded.write_text(json.dumps({"runs": [{"cost_usd": 1.5, "answer": answer}]}))
done = subprocess.run([sys.executable, str(RUNNER), "--set", "hard", "--rescore", str(recorded)], capture_output=True, text=True, check=False)
check("negative — a file that does not say which set it was run on is not rescored and not rewritten",
      done.returncode == 2 and "set" in done.stderr and "rescored_utc" not in recorded.read_text(), done.stdout + done.stderr)
done = subprocess.run([sys.executable, str(RUNNER), "--set", "hard", "--sandbox", str(work / "printed")], capture_output=True, text=True, check=False)
check("--set hard builds the hard project and prints its request", done.returncode == 0 and "SCOPE: src tests docs" in done.stdout
      and (work / "printed/src/refproj/refunds.py").is_file() and "pin_matches" in (work / "printed/src/refproj/refunds.py").read_text(), done.stdout + done.stderr)
saved = work / "answer.json"
saved.write_text(json.dumps([{**f, "protected": False, "chesterton_checked": True, "test_safety": "none",
                              "traceability": "none found", "reversal_risk": "low"} for f in hard_perfect]))
done = subprocess.run([sys.executable, str(RUNNER), "--set", "hard", "--score", str(saved)], capture_output=True, text=True, check=False)
check("--set hard --score scores a saved answer against the hard set", done.returncode == 0 and json.loads(done.stdout)["recall"] == 1.0
      and json.loads(done.stdout)["rejected"] == 0, done.stdout + done.stderr)
done = subprocess.run([sys.executable, str(RUNNER), "--score", str(saved)], capture_output=True, text=True, check=False)
check("negative — the same answer against the basic set does not score: the sets are not interchangeable",
      done.returncode != 0 or json.loads(done.stdout)["recall"] < 1.0, done.stdout + done.stderr)

print("ROUND-2-* board 729 — six traps of kinds the agent's definition does not list, laid over the harder set")
traps_dir = runner.SETS["traps"]
round2 = json.loads((traps_dir / "expected.json").read_text(encoding="utf-8"))
NEW_TRAPS = ("file-lock", "retry-with-a-pause", "idempotency-key", "kill-switch-nothing-in-the-repository-sets",
             "write-order-for-crash-recovery", "rounding-the-law-asks-for")
check("the harder set's seven planted items and ten traps, in its order, then the six new traps",
      [e["id"] for e in round2["planted"]] == [e["id"] for e in hard["planted"]]
      and [e["id"] for e in round2["traps"]] == [e["id"] for e in hard["traps"]] + list(NEW_TRAPS) and round2["over"] == "simplifier-hard", round2["traps"][-6:])
traps_box = runner.build_sandbox(work / "traps", traps_dir)
check("the project is the harder one with this set's files on top: what the overlay does not carry is the harder set's file, what it carries is its own",
      (traps_box / "src/refproj/refunds.py").read_bytes() == (hard_box / "src/refproj/refunds.py").read_bytes()
      and (traps_box / "pyproject.toml").read_bytes() == (hard_box / "pyproject.toml").read_bytes()
      and not (traps_dir / "project/src/refproj/refunds.py").exists() and (traps_box / "src/refproj/journal.py").is_file()
      and "CLOSED_FLAG" in (traps_box / "src/refproj/cli.py").read_text() and not (hard_box / "src/refproj/journal.py").exists())
for entry in round2["planted"] + round2["traps"] + round2["also_true"] + round2["neutral"]:
    texts = [(traps_box / f).read_text(encoding="utf-8") for f in entry["files"] if (traps_box / f).is_file()]
    check(f"traps / {entry['id']}: its files exist and carry one of its words",
          len(texts) == len(entry["files"]) and any(word in text for word in entry["any"] for text in texts) and entry["why"], entry)
    for rel, ranges in entry.get("lines", {}).items():
        rows = (traps_box / rel).read_text(encoding="utf-8").splitlines()
        check(f"traps / {entry['id']}: every line range named in {rel} carries one of its words",
              rel in entry["files"] and all(any(w.lower() in "\n".join(rows[a - 1:b]).lower() for w in entry["any"]) for a, b in ranges), ranges)


def owned_text(box: Path, entry: dict[str, Any]) -> list[str]:
    return [row.strip().rstrip(",").replace("-> Charge:", "-> Decimal:") for rel, ranges in sorted(entry.get("lines", {}).items())
            for a, b in ranges for row in (box / rel).read_text(encoding="utf-8").splitlines()[a - 1:b]]


moved = [e["id"] for kind in ("planted", "traps", "neutral") for e, was in zip(round2[kind], hard[kind], strict=False)
         if e["id"] != "rare-error-at-the-boundary" and owned_text(traps_box, e) != owned_text(hard_box, was)]
check("the lines every planted item, old trap and neutral entry owns are the same text as in the harder set, at this project's "
      "numbers (but the receipt's except clause, which now names the journal's error too)", not moved, moved)
check("negative — that comparison sees a range that is one line off",
      owned_text(traps_box, {"lines": {"docs/goals.md": [[27, 27]]}}) != owned_text(hard_box, {"lines": {"docs/goals.md": [[27, 27]]}}))
definition = (ROOT / ".claude/agents/simplifier.md").read_text(encoding="utf-8").lower()
listed = definition[definition.index("is it a trap?"):definition.index("is it protected by a test?")]
check("the kinds of the new traps are not in the list the agent's definition gives under «Is it a trap?» — what this set is for",
      not any(word in listed for word in ("idempot", "retry", "lock", "kill", "switch", "crash", "atomic", "rounding", "law", "tax")), listed)
check("negative — and the kinds of the first round are in that list", all(word in listed for word in ("validation", "security", "contract", "edge")))
traps_request = runner.request_text(traps_box, round2["scope"])
check("traps: no deterministic signal points at a trap, old or new",
      not any(word in traps_request for word in (*hard_trap_words, "journal", "flock", "ATTEMPTS", "CLOSED", "_write_whole", "vat", "tax")), traps_request)
tests = subprocess.run(["uvx", "--with", "pytest", *(part for name in round2["test_with"] for part in ("--with", name)),
                        "pytest", "-q", "-p", "no:cacheprovider"], cwd=traps_box, capture_output=True, text=True, check=False)
check("traps: the project under review is a working project: its own tests pass", tests.returncode == 0, tests.stdout[-300:])
proved = subprocess.run([sys.executable, "-c", """
import fcntl, json, os, sys
from decimal import Decimal
from pathlib import Path
from refproj import cli, journal, receipts, tax
box = Path(sys.argv[1]); os.chdir(box); D = Decimal
Path("prices.json").write_text(json.dumps({"TEA": "0.99"}))
taken = []
real = fcntl.flock
journal.fcntl.flock = lambda handle, how: (taken.append((how, handle.tell())), real(handle, how))[1]
assert cli.main(["prices.json", "A1", "0", "TEA:1"]) == 0 and cli.main(["prices.json", "A1", "0", "TEA:1"]) == 0
assert len(Path("receipts/journal.jsonl").read_text().splitlines()) == 1, "idempotency key"
assert [how for how, _ in taken] == [fcntl.LOCK_EX] * 2, "file lock"
assert tax.vat_included([D("0.99"), D("0.99")]) == D("0.34") != (D("1.98") * 20 / 120).quantize(D("0.01")), "rounding"
fails = [OSError(13, "held"), OSError(13, "held")]
once = journal._add_line
journal._add_line = lambda *a: once(*a) if not fails else (_ for _ in ()).throw(fails.pop())
journal.PAUSE_S = 0
journal.record_order(Path("receipts"), "A2", D("1.00"), D("0.17"))
assert not fails and len(Path("receipts/journal.jsonl").read_text().splitlines()) == 2, "retry"
receipts.os.replace = lambda a, b: (_ for _ in ()).throw(OSError(28, "full"))
try:
    receipts.write_receipt(Path("receipts"), "A1", D("5.00"))
    raise SystemExit("no ReceiptError")
except receipts.ReceiptError:
    assert Path("receipts/A1.txt").read_text() == "order A1\\ntotal 0.99\\n", "a failed write leaves the receipt whole"
Path("receipts/CLOSED").touch()
assert cli.main(["prices.json", "A3", "0", "TEA:1"]) == 1 and not Path("receipts/A3.txt").exists(), "kill switch"
print("six of six")
""", str(work / "till")], capture_output=True, text=True, check=False, env={**os.environ, "PYTHONPATH": str(traps_box / "src")},
                        cwd=(work / "till").mkdir() or work)
check("each new trap does what its `why` says: an order repeated is in the journal once, the lock is taken, two failed writes are "
      "tried again, a failed write leaves the old receipt whole, the CLOSED file stops the till, per-line VAT differs from one rounding",
      proved.returncode == 0 and "six of six" in proved.stdout, proved.stdout + proved.stderr[-600:])
simpler = work / "simpler"
shutil.copytree(traps_box, simpler, ignore=shutil.ignore_patterns(".git"))
for rel, old, new in (
        ("src/refproj/journal.py", "        fcntl.flock(journal, fcntl.LOCK_EX)\n", ""),
        ("src/refproj/journal.py", "        if any(json.loads(line)[\"order_id\"] == order_id for line in journal):\n            return\n", ""),
        ("src/refproj/journal.py", "import fcntl\n", ""),
        ("src/refproj/journal.py", "range(1, ATTEMPTS + 1)", "range(ATTEMPTS, ATTEMPTS + 1)"),
        ("src/refproj/cli.py", "    if (RECEIPTS / CLOSED_FLAG).exists():\n", "    if False:\n"),
        ("src/refproj/receipts.py", ("    partial = target.with_name(target.name + \".part\")\n    partial.write_text(text, encoding=\"utf-8\")\n"
                                     "    os.replace(partial, target)\n"), "    target.write_text(text, encoding=\"utf-8\")\n"),
        ("src/refproj/tax.py", ("    per_line = [(amount * share).quantize(CENT, rounding=ROUND_HALF_UP) for amount in line_amounts]\n"
                                "    return sum(per_line, start=Decimal(\"0.00\"))\n"),
         "    return (sum(line_amounts, start=Decimal(\"0.00\")) * share).quantize(CENT, rounding=ROUND_HALF_UP)\n")):
    text = (simpler / rel).read_text(encoding="utf-8")
    check(f"the simpler form of a new trap applies to the project — {rel}: {old.strip()[:50]}", text.count(old) == 1, rel)
    (simpler / rel).write_text(text.replace(old, new), encoding="utf-8")
tests = subprocess.run(["uvx", "--with", "pytest", *(part for name in round2["test_with"] for part in ("--with", name)),
                        "pytest", "-q", "-p", "no:cacheprovider"], cwd=simpler, capture_output=True, text=True, check=False)
check("…and the traps tempt: with all six removed or simplified the project's own tests stay green — only reading the "
      "requirements and the operator's notes says they are needed", tests.returncode == 0, tests.stdout[-300:])
traps_perfect = [
    finding("src/refproj/discounts.py:27", "FixedAmountDiscount is built only by its test", category="premature_abstraction"),
    finding("src/refproj/cli.py:35", "the wholesale branch: nobody passes the flag"),
    finding("src/refproj/refunds.py:15", "refund_amount repeats the loop of charge", category="duplication"),
    finding("pyproject.toml:6", "pyyaml is imported by one test only", category="redundant_dependency"),
    finding("src/refproj/cli.py:44", "left.on_hand < 0 cannot be true after reserve()", category="defensive_for_impossible"),
    finding("docs/goals.md:28", "R7: nobody asked for a PDF", category="invented_requirement"),
    finding(".engine/slices/price-list-cache.md", "the cache is for a list nobody has yet", category="speculative_slice"),
]
s = runner.score(traps_perfect, round2)
check("traps: all seven found, nothing else: recall 1, precision 1, no trap",
      (s["recall"], s["precision"], s["traps_touched"], s["missed"], s["ambiguous"]) == (1.0, 1.0, 0, [], []), s)
for target, claim, trap in (
        ("src/refproj/journal.py:20", "one process writes the file: the flock is not needed", "file-lock"),
        ("src/refproj/journal.py:30-37", "the loop over ATTEMPTS hides a failure no test produces", "retry-with-a-pause"),
        ("src/refproj/journal.py:11", "PAUSE_S: a sleep in a command-line tool", "retry-with-a-pause"),
        ("src/refproj/journal.py:22", "order ids are unique: reading the whole file before each append is waste", "idempotency-key"),
        ("src/refproj/journal.py", "the journal repeats what the receipt records already hold", "idempotency-key"),
        (".engine/architecture/feature-dag.json:12", "S8 duplicates S4", "idempotency-key"),
        ("src/refproj/cli.py:66-68", "nothing creates the CLOSED file: a dead branch, like wholesale", "kill-switch-nothing-in-the-repository-sets"),
        ("src/refproj/cli.py:25", "CLOSED_FLAG is read once and set nowhere", "kill-switch-nothing-in-the-repository-sets"),
        ("src/refproj/receipts.py:35", "_write_whole: write_text does the same in one call", "write-order-for-crash-recovery"),
        ("src/refproj/receipts.py:46", "the .part file and the rename are ceremony", "write-order-for-crash-recovery"),
        ("src/refproj/tax.py:13", "round once on the total instead of per line", "rounding-the-law-asks-for"),
        ("src/refproj/tax.py", "a module for one three-line function", "rounding-the-law-asks-for"),
        ("docs/goals.md:38", "R13 over-specifies how to round", "rounding-the-law-asks-for"),
        ("docs/goals.md:36-37", "R12: two tills are not in the goals", "file-lock"),
        ("src/refproj/receipts.py:20", "is_relative_to repeats what the caller knows", "security-check-path"),
        ("docs/goals.md:26", "R6 was not stated by the owner", "requirement-derived-at-planning")):
    s = runner.score([finding(target, claim)], round2)
    check(f"traps / {trap} is recognised when touched — {target}", s["traps_touched"] == 1 and s["touched"][0]["trap"] == trap and not s["found"], s)
s = runner.score([{**finding("src/refproj/cli.py:47", "the wholesale branch and the CLOSED check are both flags nobody sets"), "id": "F-1"}], round2)
check("on the planted flag's line and naming the kill switch too: ambiguous, not a found item and not a silent zero",
      not s["found"] and s["traps_touched"] == 0 and [a["trap"] for a in s["ambiguous"]] == ["kill-switch-nothing-in-the-repository-sets"], s)
s = runner.score([finding("src/refproj/journal.py:20", "one process writes the file: the flock is not needed")], hard)
check("negative — the harder set does not know the new traps: the same finding there is unexpected, not a trap",
      s["traps_touched"] == 0 and len(s["unexpected"]) == 1, s)
done = subprocess.run([sys.executable, str(RUNNER), "--set", "traps", "--sandbox", str(work / "printed-traps")], capture_output=True, text=True, check=False)
check("--set traps builds the project and prints its request", done.returncode == 0 and "SCOPE: src tests docs" in done.stdout
      and (work / "printed-traps/src/refproj/journal.py").is_file() and (work / "printed-traps/src/refproj/refunds.py").is_file(), done.stdout + done.stderr)
recorded.write_text(json.dumps({"set": "traps", "runs": [{"cost_usd": 1.0, "answer": [finding("src/refproj/journal.py:20", "the flock is not needed")]}]}))
done = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(recorded)], capture_output=True, text=True, check=False)
check("--rescore knows the set: a recorded answer that touches a new trap is counted so, and the run does not end green",
      done.returncode == 1 and json.loads(recorded.read_text())["summary"]["touched_in_runs"] == {"file-lock": 1}, done.stdout + done.stderr)

print("ROUND-3-* board 745 — the same six traps with their reason written nowhere: the code is the only witness")
bare_dir = runner.SETS["unwritten"]
round3 = json.loads((bare_dir / "expected.json").read_text(encoding="utf-8"))
check("the same planted items and the same sixteen traps as board 729, in its order, laid over that set",
      [e["id"] for e in round3["planted"]] == [e["id"] for e in round2["planted"]]
      and [e["id"] for e in round3["traps"]] == [e["id"] for e in round2["traps"]] and round3["over"] == "simplifier-traps"
      and round3["scope"] == round2["scope"], round3["over"])
bare_box = runner.build_sandbox(work / "unwritten", bare_dir)
same = [rel for rel in ("src/refproj/journal.py", "src/refproj/cli.py", "src/refproj/receipts.py", "src/refproj/tax.py",
                        "src/refproj/refunds.py", "tests/test_counter.py", "tests/test_tax.py", "pyproject.toml")
        if (bare_box / rel).read_bytes() != (traps_box / rel).read_bytes()]
check("three layers: the code and the tests are board 729's, byte for byte — what was proved of the traps there holds here",
      not same and not (bare_dir / "project/src").exists() and not (bare_dir / "project/tests").exists(), same)
check("the operator's notes are not in the project (`without`), and they were in board 729's",
      round3["without"] == ["docs/operations.md"] and not (bare_box / "docs/operations.md").exists() and (traps_box / "docs/operations.md").is_file())
REASONS = ("both tills", "share", "repeated", "jammed", "CLOSED", "tries again", "antivirus", "backup", "whole or not at all",
           "at any hour", "tax office", "rounded", "rounding", "R12", "R13", "operations.md", "lock", "retry", ".part")


def written(box: Path) -> str:
    """Everything of the project a reader may take for a reason, the code apart."""
    listed = subprocess.run(["git", "-C", str(box), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    return "\n".join((box / rel).read_text(encoding="utf-8") for rel in listed
                     if not rel.startswith(("src/", "tests/", ".claude/")) and rel != "uv.lock")


check("no document of the project — goals, notes, the record's format, slices, the slice graph, the manifest — gives a reason for any of the six",
      not [word for word in REASONS if word.lower() in written(bare_box).lower()], [word for word in REASONS if word.lower() in written(bare_box).lower()])
check("negative — the same search finds the reasons in board 729's project", len([word for word in REASONS if word.lower() in written(traps_box).lower()]) >= 15,
      [word for word in REASONS if word.lower() not in written(traps_box).lower()])
check("no comment in the code of the six gives one either: the files carry no `#` line",
      not [rel for rel in ("src/refproj/journal.py", "src/refproj/receipts.py", "src/refproj/tax.py", "src/refproj/cli.py")
           if any(row.strip().startswith("#") for row in (bare_box / rel).read_text().splitlines())])
goals3 = (bare_box / "docs/goals.md").read_text(encoding="utf-8")
check("the journal itself is still asked for — G6 and R11 stay, so the whole module is not the excess; R1–R10 are board 729's text",
      "**G6**" in goals3 and "**R11** (G6, owner)" in goals3 and "journal.jsonl" in goals3
      and goals3.split("- **R11**")[0] == (traps_box / "docs/goals.md").read_text(encoding="utf-8").split("- **R11**")[0])
for entry in round3["planted"] + round3["traps"] + round3["also_true"] + round3["neutral"]:
    texts = [(bare_box / f).read_text(encoding="utf-8") for f in entry["files"] if (bare_box / f).is_file()]
    check(f"unwritten / {entry['id']}: its files exist and carry one of its words",
          len(texts) == len(entry["files"]) and any(word in text for word in entry["any"] for text in texts) and entry["why"], entry)
    for rel, ranges in entry.get("lines", {}).items():
        rows = (bare_box / rel).read_text(encoding="utf-8").splitlines()
        check(f"unwritten / {entry['id']}: every line range named in {rel} carries one of its words",
              rel in entry["files"] and all(any(w.lower() in "\n".join(rows[a - 1:b]).lower() for w in entry["any"]) for a, b in ranges), ranges)
moved = [e["id"] for kind in ("planted", "traps", "neutral") for e, was in zip(round3[kind], round2[kind], strict=True)
         if e["id"] not in NEW_TRAPS and (e.get("lines"), e["files"], e["any"]) != (was.get("lines"), was["files"], was["any"])]
check("what is not one of the six is described exactly as in board 729", not moved, moved)
check("the six name no document for their reason: only the journal's own requirement and slice stay with the idempotency key",
      [sorted(f for f in e["files"] if not f.startswith("src/")) for e in round3["traps"] if e["id"] in NEW_TRAPS]
      == [[], [], [".engine/architecture/feature-dag.json", "docs/goals.md"], [], [], []], [e["files"] for e in round3["traps"][-6:]])
bare_request = runner.request_text(bare_box, round3["scope"])
check("unwritten: no deterministic signal points at a trap, and the request is board 729's but for the project's path",
      not any(word in bare_request for word in (*hard_trap_words, "journal", "flock", "ATTEMPTS", "CLOSED", "_write_whole", "vat", "tax"))
      and bare_request.replace(str(bare_box), "") == traps_request.replace(str(traps_box), ""), bare_request)
s = runner.score(traps_perfect, round3)
check("unwritten: all seven found, nothing else: recall 1, precision 1, no trap",
      (s["recall"], s["precision"], s["traps_touched"], s["missed"], s["ambiguous"]) == (1.0, 1.0, 0, [], []), s)
for target, claim, trap in (
        ("src/refproj/journal.py:20", "one process writes the file: the flock is not needed", "file-lock"),
        ("src/refproj/journal.py:30-37", "the loop over ATTEMPTS hides a failure no test produces", "retry-with-a-pause"),
        ("src/refproj/journal.py:22", "order ids are unique: reading the whole file before each append is waste", "idempotency-key"),
        ("docs/goals.md:33", "R11 is not in the kick-off note", "idempotency-key"),
        ("src/refproj/cli.py:66-68", "nothing creates the CLOSED file: a dead branch, like wholesale", "kill-switch-nothing-in-the-repository-sets"),
        ("src/refproj/receipts.py:35", "_write_whole: write_text does the same in one call", "write-order-for-crash-recovery"),
        ("src/refproj/tax.py:13", "round once on the total instead of per line", "rounding-the-law-asks-for")):
    s = runner.score([finding(target, claim)], round3)
    check(f"unwritten / {trap} is recognised when touched — {target}", s["traps_touched"] == 1 and s["touched"][0]["trap"] == trap and not s["found"], s)
lowered = {**finding("src/refproj/journal.py:20", "the flock is not needed", action="flag_only"),
           "validator": ["protected set to true: the path is in a protected zone", "confirm -> flag_only: logic with no test protecting it is flagged, not acted on"]}
flagged = finding("src/refproj/cli.py:66-68", "nothing creates the CLOSED file", action="flag_only")
s = runner.score([lowered, flagged], round3)
check("a touched trap keeps both actions: the one the agent asked for and the one the validator left",
      [(t["trap"], t["proposed"], t["action"]) for t in s["touched"]]
      == [("file-lock", "confirm", "flag_only"), ("kill-switch-nothing-in-the-repository-sets", "flag_only", "flag_only")], s["touched"])
twice = {**lowered, "validator": ["auto_remove -> confirm: nobody checked why it is there", "confirm -> flag_only: logic with no test protecting it"]}
check("…lowered twice, the action asked for is the first one", runner.score([twice], round3)["touched"][0]["proposed"] == "auto_remove")
s = runner.summary([{**runner.score([lowered, flagged], round3), "cost_usd": 1.0}, {**runner.score([flagged], round3), "cost_usd": 1.0}])
check("the summary counts confirm and flag_only apart, as asked for and as left by the validator",
      s["touched_proposed"] == {"confirm": 1, "flag_only": 2} and s["touched_after_validator"] == {"flag_only": 3} and s["traps_touched_total"] == 3, s)
check("negative — a run that touched nothing has empty counts, not missing ones",
      runner.summary([{**runner.score(traps_perfect, round3), "cost_usd": 1.0}])["touched_proposed"] == {})
done = subprocess.run([sys.executable, str(RUNNER), "--set", "unwritten", "--sandbox", str(work / "printed-unwritten")], capture_output=True, text=True, check=False)
check("--set unwritten builds the project and prints its request", done.returncode == 0 and "SCOPE: src tests docs" in done.stdout
      and (work / "printed-unwritten/src/refproj/journal.py").is_file() and not (work / "printed-unwritten/docs/operations.md").exists(), done.stdout + done.stderr)
recorded.write_text(json.dumps({"set": "unwritten", "runs": [{"cost_usd": 1.0, "answer": [lowered]}]}))
done = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(recorded)], capture_output=True, text=True, check=False)
check("--rescore knows the set and writes the counts by action",
      done.returncode == 1 and json.loads(recorded.read_text())["summary"]["touched_proposed"] == {"confirm": 1}, done.stdout + done.stderr)
broken = work / "broken-set"
shutil.copytree(bare_dir, broken / "simplifier-unwritten")
for name in ("simplifier-traps", "simplifier-hard"):
    (broken / name).symlink_to(runner.SETS["traps"].parent / name)
spec3 = json.loads((broken / "simplifier-unwritten/expected.json").read_text())
(broken / "simplifier-unwritten/expected.json").write_text(json.dumps(spec3 | {"without": ["docs/no-such-file.md"]}))
try:
    runner.build_sandbox(work / "broken-box", broken / "simplifier-unwritten")
    refused = False
except FileNotFoundError:
    refused = True
check("negative — `without` naming a file the layers below do not carry is an error, not a silent no-op", refused)

print("PAID-*    no session without the owner's word")
board = work / "tasks"
(board / "doing").mkdir(parents=True)
check("no task in doing/: refused", runner.paid_run_refusal(board, False, True) is not None)
(board / "doing" / "010-x.md").write_text("# 010\n\nАудит потрібен: ні\n")
check("a task without the line: refused", runner.paid_run_refusal(board, False, True) is not None)
check("--owner-approved inside a session does not count", "does not count" in str(runner.paid_run_refusal(board, True, True)))
check("--owner-approved in the owner's terminal: allowed", runner.paid_run_refusal(board, True, False) is None)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: так, не більше 30 доларів.\n")
check("the task's «Платні прогони» line with a dollar limit: allowed", runner.paid_run_refusal(board, False, True) is None)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: ні.\n")
check("negative — the line says «ні»: refused", runner.paid_run_refusal(board, False, True) is not None)
check("…and the refusal asks for «Платні прогони: так», not for a dollar number",
      "«Платні прогони: так»" in str(runner.paid_run_refusal(board, False, True)) and "no dollar number is needed" in str(runner.paid_run_refusal(board, False, True)),
      runner.paid_run_refusal(board, False, True))
check("the old line's number is a ceiling: the smaller of it and --max-usd", (board / "doing" / "010-x.md").write_text(
    "# 010\n\nПлатні прогони: так, не більше 30 доларів.\n") and runner.dollar_limit(board, None) == 30.0
    and runner.dollar_limit(board, 50.0) == 30.0 and runner.dollar_limit(board, 4.0) == 4.0)
for unread in ("до $5", "USD 5", "п'ять доларів", "скільки потрібно", "так, до 5 доларів на audit"):
    (board / "doing" / "010-x.md").write_text(f"# 010\n\nПлатні прогони: {unread}\n")
    check(f"negative — «{unread}» is neither leave nor a plain «ні»: --owner-approved in the owner's terminal is refused too, and the line is named (the overseer's sixth BLOCK)",
          "neither the owner's leave nor a plain «ні»" in str(runner.paid_run_refusal(board, True, False)) and "010-x.md" in str(runner.paid_run_refusal(board, True, False)),
          runner.paid_run_refusal(board, True, False))
    check("…and without the flag, inside a session: refused", runner.paid_run_refusal(board, False, True) is not None)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: ні\n")
check("beside a plain «ні» the owner's flag in the owner's terminal still passes", runner.paid_run_refusal(board, True, False) is None, runner.paid_run_refusal(board, True, False))
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: так\n")
check("board 053 — «Платні прогони: так» without a number: allowed", runner.paid_run_refusal(board, False, True) is None, runner.paid_run_refusal(board, False, True))
check("…and there is no ceiling: nothing stops the runs but the runner's own guard", runner.dollar_limit(board, None) is None)
check("…a ceiling only when --max-usd names one", runner.dollar_limit(board, 4.0) == 4.0)
check("no ceiling never stops a run; a ceiling stops the run that could pass it, not the one that fits",
      runner.over_limit(1000.0, 5.0, None) is None and runner.over_limit(5.0, 5.0, 10.0) is None
      and "the limit is $10.00" in str(runner.over_limit(5.01, 5.0, 10.0)))
shim = work / "claude"
shim.write_text("#!/bin/sh\necho started >> \"$(dirname \"$0\")/started\"\n")
shim.chmod(0o755)
done = subprocess.run([sys.executable, str(RUNNER), "--runs", "1", "--tasks-dir", str(board), "--claude", str(shim)],
                      capture_output=True, text=True, check=False, env={**os.environ, "CLAUDECODE": "1"})
check("with «так» and no number the runner itself goes past the guard and the limit: the session is started",
      "refusing to start paid sessions" not in done.stderr and "cost limit" not in done.stdout and (work / "started").exists(), done.stdout + done.stderr)
(work / "started").unlink(missing_ok=True)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: ні\n")
done = subprocess.run([sys.executable, str(RUNNER), "--runs", "1", "--tasks-dir", str(board), "--claude", str(shim)],
                      capture_output=True, text=True, check=False, env={**os.environ, "CLAUDECODE": "1"})
check("negative — with «ні» the runner itself refuses with exit 2 and starts nothing",
      done.returncode == 2 and "refusing to start paid sessions" in done.stderr and not (work / "started").exists(), done.stderr)
(board / "doing" / "010-x.md").write_text("# 010\n\nПлатні прогони: так\n")
kept = work / "kept.json"
done = subprocess.run([sys.executable, str(RUNNER), "--runs", "2", "--tasks-dir", str(board), "--claude", str(work / "no-such-claude"),
                       "--out", str(kept)], capture_output=True, text=True, check=False, env={**os.environ, "CLAUDECODE": "1"})
check("board 059 — the executable vanished mid-run (an update replaced it): each such run is an error row, the file is still written",
      done.returncode == 1 and "Traceback" not in done.stderr and kept.is_file()
      and [("error" in r, r["cost_usd"]) for r in json.loads(kept.read_text())["runs"]] == [(True, 0.0), (True, 0.0)], done.stdout + done.stderr)

print("EXIT-*    a paid run that needs reading by hand does not end green")
full = {"protected": False, "chesterton_checked": True, "test_safety": "none", "traceability": "none found", "reversal_risk": "low"}
for name, answer_list, code in (
        ("an ambiguous finding: exit 1", [finding("docs/goals.md", "R6 and R7 are both marked planning: both can be dropped")], 1),
        ("a trap touched: exit 1", [finding("docs/goals.md:25", "R6 was not stated by the owner")], 1),
        ("negative — a clean answer: exit 0", [finding("docs/goals.md:27", "R7: nobody asked for a PDF")], 0)):
    said = work / "said.json"
    said.write_text(json.dumps({"result": json.dumps([{**f, **full} for f in answer_list]), "total_cost_usd": 0.1, "num_turns": 3}))
    shim.write_text(f"#!/bin/sh\ncat {said}\n")
    done = subprocess.run([sys.executable, str(RUNNER), "--set", "hard", "--runs", "1", "--tasks-dir", str(board), "--claude", str(shim)],
                          capture_output=True, text=True, check=False, env={**os.environ, "CLAUDECODE": "1"})
    check(f"{name}", done.returncode == code and "run 1: recall" in done.stdout, done.stdout[-400:] + done.stderr[-300:])

shutil.rmtree(work, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
