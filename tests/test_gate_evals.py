#!/usr/bin/env python3
"""The gate eval corpus (evals/scenarios/gate/cases.json) and its recorded baseline are sound.

Deterministic and offline: it checks the SHAPE of the instrument — every defect names the rule it
must be caught by, every layer has a clean case (no false blocks to measure otherwise), every
bypass kind has a defective case, a limit case sits next to the case that proves the other layer
catches it — and that the recorded baseline says what the README says it does. The measuring
itself (real ruff / mypy / pytest) is `python3 evals/run_gate_evals.py --engine-ref HEAD`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "evals/scenarios/gate/cases.json").read_text())["cases"]
LAYERS = {"post_write", "stop", "pre_commit", "ci"}
PASS = FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


ids = [c["id"] for c in CASES]
check("case ids are unique", len(ids) == len(set(ids)))
check("every case has a kind, layers and a why", all(
    c["kind"] in ("defective", "clean", "limit") and set(c["layers"]) <= LAYERS and c.get("why") for c in CASES))
check("every defective case names the rule that must catch it", all(c.get("rule") for c in CASES if c["kind"] == "defective"))
check("a post_write case names the file it edits", all(c.get("edited") for c in CASES if "post_write" in c["layers"]))
clean_layers = {layer for c in CASES if c["kind"] == "clean" for layer in c["layers"]}
check("every layer has a clean case (else its false blocks are unmeasured)", clean_layers == LAYERS, clean_layers)
defect_rules = {c["rule"] for c in CASES if c["kind"] == "defective"}
for rule in ("lint", "typecheck", "tests", "bypass/type-ignore", "bypass/noqa", "bypass/skip", "bypass/xfail", "bypass/config"):
    check(f"a defect is planted for {rule}", rule in defect_rules)
limits = [c for c in CASES if c["kind"] == "limit"]
check("each documented limit has a defective twin that another layer catches",
      all(any(c["kind"] == "defective" and "ci" in c["layers"] and c["setup"] == lim["setup"] for c in CASES) for lim in limits))
check("setup writes stay inside the sandbox", all(
    not Path(s["write"]["path"]).is_absolute() and ".." not in Path(s["write"]["path"]).parts
    for c in CASES for s in c["setup"] if "write" in s))

baseline = ROOT / "evals/baseline/linux-ubuntu-22.04/gate-evals-package-7.json"
if baseline.is_file():
    rec = json.loads(baseline.read_text())
    s = rec["summary"]
    check("the recorded baseline caught every defect with no false block",
          s["defects_caught"] == s["defective_cases"] and s["false_blocks"] == 0 and not s["failed"], s)
    check("the baseline times all four layers", set(rec["timings_ms"]) == LAYERS, set(rec["timings_ms"]))
    check("the baseline covers the corpus as it is now", {r["id"] for r in rec["results"]} == set(ids))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
