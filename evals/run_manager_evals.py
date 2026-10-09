#!/usr/bin/env python3
"""The testing manager's decisions on thirteen scenes (board 062; the design of board 060, section 3).

    python3 evals/run_manager_evals.py --out evals/baseline/@env/manager-evals-<label>.json   # PAID: 13 short read-only sessions
    python3 evals/run_manager_evals.py --scenes discount-threshold fourth-exporter
    python3 evals/run_manager_evals.py --dry-run DIR                           # free: every sandbox, nothing is run
    python3 evals/run_manager_evals.py --score ANSWER.txt --scene NAME         # free: score a ready answer

THE QUESTION. The script holds the mandatory cases whatever the manager says; what only a run
can show is the manager's own judgement: does it arrive at the mandatory answer itself, does it
say «do not switch» where the design says so and only there, and does its reason name the fact.

A SCENE (evals/scenarios/manager/scenes.json) is one request as testing.py would write it: the
slice contract and the facts. The sandbox holds the two agent definitions, the constitution,
the contract and the request; the session runs as the agent `test-manager` with the launch
line `TESTING_REQUEST <id>` and the tools Read, Grep, Glob. Its answer is scored by this
script with testing.py's own validator:
  matched         the decision is the one the design expects (for point (b): every check the
                  scene names, the event of a deferral, and `block_large` where the scene sets it);
  names_fact      the reasons name the fact the decision rests on (the scene's pattern);
  script_refuses  testing.py would refuse the answer — a mandatory case the manager did not
                  reach itself, or an answer out of shape. Recorded, not hidden: the script
                  catches it in live work, and here it is the measure of the definition.
A scene passes when it is matched and names the fact. A scene that does not pass is recorded
as it is — it is work on the manager's definition, not something to rerun until green.

EXTRA SESSIONS (board 078). The sessions this starts are ordinary work, like a test: no leave is
asked for. Each one is booked to the task in hand (.claude/state/board/extra-sessions.jsonl;
board_state.py) so the runner's summary and the owner's review show where the limit goes.
--max-usd is a ceiling the runs stop before; --owner-approved is still accepted, and changes nothing.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # a suite may load this file by path
import environment
import run_analyst_evals as analyst

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import testing

FIXTURE = HERE / "scenarios" / "manager" / "scenes.json"
SHIPPED = (".claude/agents/test-manager.md", ".claude/agents/slice-tester.md", ".claude/constitution.md")
TOOLS = ("Read", "Grep", "Glob")
REQUEST_ID = "20260101T000000Z-scene0"
RUN_TIMEOUT_S = 600
CONTRACT = """# Slice {slug} — planning artifact

## Goal
{goal}

## Seam (contract)
{seam}

## Hardest seams (test-confidence points — distinct from the contract Seam above)
{seams}

## Exit criterion
{exit}

## Deferred to later slices
- none
"""

JsonObj = dict[str, Any]


def load() -> JsonObj:
    data: JsonObj = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- none"


def facts_of(data: JsonObj, name: str) -> JsonObj:
    scene = data["scenes"][name]
    facts: JsonObj = {"point": scene["point"], "slice": name, "contract": f".engine/slices/{name}.md"} | data["base"][scene["point"]] | scene["facts"]
    if scene["point"] == "a":
        facts["hardest_seams"] = [seam.split("**")[1] for seam in scene["contract"]["hardest_seams"]]
    return facts


def build_sandbox(target: Path, data: JsonObj, name: str) -> Path:
    """What the manager reads: its definition, the contract, the request with the facts, an empty ledger."""
    contract = data["scenes"][name]["contract"]
    for rel in SHIPPED:
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target / rel)
    files = {
        f".engine/slices/{name}.md": CONTRACT.format(slug=name, goal=contract["goal"], seam=bullets(contract["seam"]),
                                                    seams=bullets(contract["hardest_seams"]), exit=bullets(contract["exit"])),
        ".engine/testing/ledger.md": testing.LEDGER_HEADER,
        (testing.REQUESTS_REL / REQUEST_ID / "request.json").as_posix(): json.dumps(
            {"id": REQUEST_ID, "agent": testing.MANAGER, "point": data["scenes"][name]["point"], "slice": name, "facts": facts_of(data, name)},
            indent=2, ensure_ascii=False) + "\n",
    }
    for rel, text in files.items():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_text(text, encoding="utf-8")
    return target


# ------------------------------------------------------------------ scoring (free, deterministic)


def reasons(decision: JsonObj) -> str:
    parts = [decision.get("reason"), decision.get("small"), decision.get("uniform")]
    parts += [entry.get("reason") for entry in (decision.get("checks") or {}).values() if isinstance(entry, dict)]
    return " ".join(str(part) for part in parts if part)


def matches(decision: JsonObj, expected: JsonObj) -> list[str]:
    """Where the decision differs from the one the design expects; empty when it is that decision."""
    wrong = []
    if "decision" in expected and decision.get("decision") != expected["decision"]:
        wrong.append(f"decision: {decision.get('decision')!r}, expected {expected['decision']!r}")
    checks = decision.get("checks") if isinstance(decision.get("checks"), dict) else {}
    for kind, when in expected.get("checks", {}).items():
        said = (checks.get(kind) or {}).get("when") if isinstance(checks.get(kind), dict) else None
        if said != when:
            wrong.append(f"{kind}: {said!r}, expected {when!r}")
    for kind, until in expected.get("until", {}).items():
        said = (checks.get(kind) or {}).get("until") if isinstance(checks.get(kind), dict) else None
        if said != until:
            wrong.append(f"{kind} until: {said!r}, expected {until!r}")
    if "block_large" in expected and decision.get("block_large") is not expected["block_large"]:
        wrong.append(f"block_large: {decision.get('block_large')!r}, expected {expected['block_large']!r}")
    return wrong


def shown(decision: JsonObj) -> str:
    if "decision" in decision:
        return str(decision.get("decision"))
    checks = decision.get("checks") if isinstance(decision.get("checks"), dict) else {}
    parts = [f"{kind}: {entry.get('when')}" + (f" until {entry.get('until')}" if entry.get("when") == "defer" else "")
             for kind, entry in checks.items() if isinstance(entry, dict)]
    return "; ".join(parts) + (f"; block_large: {decision['block_large']}" if decision.get("block_large") is not None else "")


def score(answer: str, data: JsonObj, name: str) -> JsonObj:
    scene = data["scenes"][name]
    facts = facts_of(data, name)
    decision, problem = testing.parse_answer(answer)
    if decision is None:
        return {"matched": False, "names_fact": False, "script_refuses": [problem], "passed": False, "decision": None, "differs": [problem]}
    differs = matches(decision, scene["expected"])
    names = re.search(scene["names"], reasons(decision), re.IGNORECASE) is not None
    return {"matched": not differs, "names_fact": names, "script_refuses": testing.validate(decision, facts), "passed": not differs and names,
            "decision": decision, "shown": shown(decision), "differs": differs, "mandatory": testing.mandatory(facts)}


def summary(runs: list[JsonObj]) -> JsonObj:
    scored = [r for r in runs if "error" not in r]
    return {"runs": len(runs), "errors": len(runs) - len(scored), "passed": sum(1 for r in scored if r["passed"]),
            "matched": sum(1 for r in scored if r["matched"]), "named_the_fact": sum(1 for r in scored if r["names_fact"]),
            "the_script_would_refuse": sorted(r["scene"] for r in scored if r["script_refuses"]),
            "not_passed": sorted(r["scene"] for r in scored if not r["passed"]), "cost_usd": round(sum(r["cost_usd"] for r in runs), 4)}


# ------------------------------------------------------------------ one session


def run_once(sandbox: Path, args: argparse.Namespace) -> JsonObj:
    command = [args.claude, "-p", testing.launch_line(REQUEST_ID), "--agent", testing.MANAGER, "--tools", *TOOLS, "--output-format", "json",
               "--strict-mcp-config", "--max-budget-usd", str(args.max_usd_per_run)]
    command += ["--model", args.model] if args.model else []
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    try:
        proc = subprocess.run(command, cwd=sandbox, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, check=False,
                              env={**env, "CLAUDE_PROJECT_DIR": str(sandbox)}, stdin=subprocess.DEVNULL)
        payload = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"error": f"the session gave no result: {type(exc).__name__}", "cost_usd": 0.0}
    row: JsonObj = {"cost_usd": round(float(payload.get("total_cost_usd") or 0.0), 4),
                    "models": sorted((payload.get("modelUsage") or {}).keys()), "turns": payload.get("num_turns")}
    answer = str(payload.get("result") or "")
    if payload.get("is_error"):
        return row | {"error": f"the session ended in an error: {answer[:300]}"}
    return row | {"answer": answer}


def main() -> int:
    data = load()
    names = list(data["scenes"])
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--out", type=environment.out_path, help="a recording goes to evals/baseline/@env/")
    parser.add_argument("--scenes", nargs="+", choices=names, default=names)
    parser.add_argument("--dry-run", type=Path, help="build every sandbox here and stop; free")
    parser.add_argument("--score", type=Path, help="score this ready answer against --scene and stop; free")
    parser.add_argument("--scene", choices=names, help="the scene --score is for")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the session's model")
    parser.add_argument("--max-usd", type=float, default=None, help="a ceiling: stop before the runs together cost more (default: none)")
    parser.add_argument("--max-usd-per-run", type=float, default=0.6)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()

    if args.score:
        if not args.scene:
            parser.error("--score needs --scene")
        result = score(args.score.read_text(encoding="utf-8"), data, args.scene)
        print(f"{args.scene}: {'passed' if result['passed'] else 'NOT passed'} — {result.get('shown')}; differs: {result['differs'] or 'no'}; "
              f"names the fact: {result['names_fact']}; the script would refuse: {result['script_refuses'] or 'no'}")
        return 0 if result["passed"] else 1
    if args.dry_run:
        for name in args.scenes:
            build_sandbox(args.dry_run / name, data, name)
        print(f"{len(args.scenes)} sandboxes in {args.dry_run}; nothing was run")
        return 0
    limit = args.max_usd
    runs: list[JsonObj] = []
    with tempfile.TemporaryDirectory(prefix="engine-manager-eval-") as tmp:
        for name in args.scenes:
            stop = analyst.shared.over_limit(sum(r["cost_usd"] for r in runs), args.max_usd_per_run, limit)
            if stop:
                print(stop)
                break
            row = {"scene": name, "point": data["scenes"][name]["point"], "expected": data["scenes"][name]["expected"]} | run_once(build_sandbox(Path(tmp) / name, data, name), args)
            if "error" not in row:
                row |= score(row["answer"], data, name)
            runs.append(row)
            analyst.shared.book_session(args.tasks_dir, "run_manager_evals", row.get("cost_usd", 0.0))
            said = row.get("error") or f"{'passed' if row['passed'] else 'NOT passed'} — {row.get('shown')}" + (f" [differs: {'; '.join(row['differs'])}]" if row["differs"] else "")
            print(f"{name}: {said}  (${row['cost_usd']:.2f}, {', '.join(row.get('models', []))})", flush=True)
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "limit_usd": limit, "planned": list(args.scenes), "scenes": {name: data["scenes"][name]["what"] for name in names}, "summary": summary(runs), "runs": runs,
    }
    print("\n" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return 0 if len(runs) == len(args.scenes) and not any("error" in r for r in runs) else 1


if __name__ == "__main__":
    sys.exit(main())
