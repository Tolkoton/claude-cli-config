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
          "touched_in_runs": {}, "cost_usd": 3.0})
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
