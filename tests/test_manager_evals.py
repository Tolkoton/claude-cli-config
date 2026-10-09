#!/usr/bin/env python3
"""The instrument of the manager's decision scenes, checked without a paid session (board 062).

  - no session starts unless the task in tasks/doing/ allows paid runs, and the run stops
    BEFORE a session that could pass the task's dollar limit;
  - every scene is what it claims: the decision the design expects is allowed by testing.py's
    validator on the scene's own facts, and where a mandatory case fires the opposite decision
    is refused — so a scene never asks the manager for something the script would refuse;
  - the scenes cover the thirteen examples: seven of point (a), six of point (b), and every
    mandatory case that the examples show (O2, O3, O4, O5, O6, O7, O8 at both points);
  - the scoring refuses first: a wrong decision, a right decision whose reason names no fact,
    an answer with no JSON — before a right one passes;
  - the sandbox shows the manager its definition, the contract and the request — and neither
    the expected decision nor the names of the mandatory cases that fired.

Run:   python3 tests/test_manager_evals.py       Exit: 0 all green, 1 otherwise.
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
RUNNER = ROOT / "evals/run_manager_evals.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


spec = importlib.util.spec_from_file_location("run_manager_evals", RUNNER)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
sys.modules["run_manager_evals"] = runner
spec.loader.exec_module(runner)
testing = runner.testing
data = runner.load()
scenes: dict[str, Any] = data["scenes"]


def ideal(name: str) -> dict[str, Any]:
    """The decision the design expects, written out in full: what a manager that passes would answer."""
    expected = scenes[name]["expected"]
    if scenes[name]["point"] == "a":
        body = {"point": "a", "slice": name, "decision": expected["decision"], "reason": "REASON"}
        return body | ({"small": "one responsibility", "uniform": "no logic of its own"} if expected["decision"] == "builder" else {})
    checks = {kind: {"when": expected["checks"].get(kind, "none"), "reason": "REASON"} for kind in testing.KINDS}
    for kind, until in expected.get("until", {}).items():
        checks[kind]["until"] = until
    return {"point": "b", "slice": name, "reason": "REASON", "checks": checks, "block_large": expected.get("block_large")}


def opposite(name: str) -> dict[str, Any]:
    if scenes[name]["point"] == "a":
        return {"point": "a", "slice": name, "decision": "builder", "reason": "small", "small": "x", "uniform": "y"}
    return {"point": "b", "slice": name, "reason": "nothing", "checks": {kind: {"when": "none", "reason": "no"} for kind in testing.KINDS}}


print("the scenes are what they claim")
check("thirteen scenes: seven of point (a), six of point (b)", len(scenes) == 13 and sum(1 for s in scenes.values() if s["point"] == "a") == 7, len(scenes))
fired_anywhere: set[str] = set()
for name, scene in scenes.items():
    facts = runner.facts_of(data, name)
    fired = testing.mandatory(facts)
    fired_anywhere |= {f"{case.partition(':')[0]}{scene['point']}" for case in fired}
    # A scene of point (b) names only the checks the design's example names; the rest of the ideal answer is «none» —
    # which a mandatory case may forbid. Then the scene must have named that check.
    errors = testing.validate(ideal(name), facts)
    check(f"{name}: the expected decision is allowed by the script on the scene's own facts", errors == [], errors)
    if fired:
        check(f"{name}: a mandatory case fires ({', '.join(fired)}) and the opposite decision is refused", testing.validate(opposite(name), facts) != [], fired)
    elif scene["point"] == "a":
        check(f"{name}: no mandatory case — the decision is the manager's own judgement", testing.validate(opposite(name), facts) == [], testing.validate(opposite(name), facts))
check("the examples cover O2, O3, O4, O8 at point (a) and O5, O6, O7, O8 at point (b)",
      {"O2a", "O3a", "O4a", "O8a", "O5b", "O6b", "O7b", "O8b"} <= fired_anywhere, sorted(fired_anywhere))
check("two scenes of point (a) expect «do not switch», and no mandatory case fires in them",
      [n for n, s in scenes.items() if s["expected"].get("decision") == "builder"] == ["fourth-exporter", "rename-settings-key"])

print("the scoring refuses first")
name = "discount-threshold"
wrong = runner.score("```json\n" + json.dumps(opposite(name)) + "\n```", data, name)
check("a wrong decision does not pass, and the script would refuse it (O3)", not wrong["passed"] and not wrong["matched"] and any(e.startswith("O3") for e in wrong["script_refuses"]), wrong)
silent = runner.score("```json\n" + json.dumps(ideal(name)) + "\n```", data, name)
check("the right decision whose reason names no fact does not pass", silent["matched"] and not silent["names_fact"] and not silent["passed"], silent)
check("an answer with no JSON does not pass", not runner.score("The tester, I think.", data, name)["passed"])
good = runner.score("```json\n" + json.dumps(ideal(name) | {"reason": "the exit criterion carries a threshold the owner ratified"}) + "\n```", data, name)
check("the right decision with the fact named passes, and the script would not refuse it", good["passed"] and good["script_refuses"] == [], good)
name = "second-of-five"
late = ideal(name)
late["checks"]["integration"]["until"] = "feature-closed"
check("point (b): a deferral to another event than the design's does not match", "integration until" in " ".join(runner.score(json.dumps(late), data, name)["differs"]))
name = "block-closed-connected"
small = ideal(name) | {"block_large": False}
check("point (b): `block_large` is part of the decision where the scene sets it", "block_large" in " ".join(runner.score(json.dumps(small), data, name)["differs"]))
check("point (b): the expected decision with the fact named passes",
      runner.score(json.dumps(ideal(name) | {"reason": "the block is closed and connected to stock"}), data, name)["passed"])

print("the sandbox")
with tempfile.TemporaryDirectory() as tmp:
    out = subprocess.run([sys.executable, str(RUNNER), "--dry-run", tmp], capture_output=True, text=True, check=False)
    check("--dry-run builds thirteen sandboxes and runs nothing", out.returncode == 0 and len(list(Path(tmp).iterdir())) == 13, out.stdout + out.stderr)
    for name in ("discount-threshold", "block-closed-connected"):
        box = Path(tmp) / name
        request = json.loads((box / ".claude/state/testing/requests" / runner.REQUEST_ID / "request.json").read_text(encoding="utf-8"))
        everything = "\n".join(p.read_text(encoding="utf-8") for p in box.rglob("*") if p.is_file() and "agents" not in p.parts and p.name != "constitution.md")
        check(f"{name}: the definition, the contract and the request are there", (box / ".claude/agents/test-manager.md").is_file()
              and (box / request["facts"]["contract"]).is_file() and request["agent"] == "test-manager" and request["slice"] == name)
        check(f"{name}: neither the expected decision nor the fired cases are shown", '"expected"' not in everything and "mandatory" not in everything
              and not any(f'"O{n}' in everything for n in range(1, 9)), everything[:300])
    contract = (Path(tmp) / "discount-threshold/.engine/slices/discount-threshold.md").read_text(encoding="utf-8")
    check("the contract carries the mark the script reads, and the facts carry the same line",
          "(threshold owner-ratified)" in contract and runner.facts_of(data, "discount-threshold")["ratified_thresholds"][0] in contract)

print("board 078: no leave for the sessions; the run's own ceiling stands, each session is booked")
with tempfile.TemporaryDirectory() as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    (tasks / "doing/062-x.md").write_text("# 062\n\nАудит потрібен: ні\n", encoding="utf-8")
    books = Path(tmp) / "books"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDECODE": "1", "BOARD_STATE_DIR": str(books)}
    shim = Path(tmp) / "claude"
    shim.write_text(f"#!/bin/sh\necho started >> {tmp}/started\n", encoding="utf-8")
    shim.chmod(0o755)
    base = [sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim)]
    r = subprocess.run([*base, "--max-usd", "0.5"], capture_output=True, text=True, env=env, check=False)
    check("board 078: a task with no line is not refused — only the run's own ceiling stops it: under one run, nothing starts",
          "refusing" not in r.stderr and "cost limit" in r.stdout and not (Path(tmp) / "started").exists() and r.returncode == 1, r.stdout + r.stderr)
    answer = json.dumps(ideal("discount-threshold") | {"reason": "a ratified threshold"})
    shim.write_text(f"#!/bin/sh\necho \"$@\" >> {tmp}/started\ncat <<'EOF'\n" + json.dumps({"total_cost_usd": 3, "result": answer}) + "\nEOF\n", encoding="utf-8")
    r = subprocess.run([*base, "--max-usd", "5", "--max-usd-per-run", "3"], capture_output=True, text=True, env=env, check=False)
    started = (Path(tmp) / "started").read_text(encoding="utf-8")
    check("--max-usd 5: after a run of 3 dollars the second is not started",
          started.count("\n") == 1 and "the limit is $5.00" in r.stdout and r.returncode == 1, r.stdout + r.stderr)
    booked = [json.loads(line) for line in (books / "extra-sessions.jsonl").read_text(encoding="utf-8").splitlines()] if (books / "extra-sessions.jsonl").is_file() else []
    check("…and the one session it started is booked to the task in hand", [(b["task"], b["tool"], b["cost_usd"]) for b in booked] == [("062-x", "run_manager_evals", 3.0)], booked)
    check("the session runs as the agent test-manager with the launch line and read-only tools",
          f"-p TESTING_REQUEST {runner.REQUEST_ID} --agent test-manager --tools Read Grep Glob" in started, started)
    check("the one scene that ran is scored", "discount-threshold: passed — tester" in r.stdout, r.stdout)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
