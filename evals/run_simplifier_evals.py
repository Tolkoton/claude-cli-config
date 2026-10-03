#!/usr/bin/env python3
"""Measure the simplifier agent on a project with planted excess and with traps.

    python3 evals/run_simplifier_evals.py --runs 3 [--out FILE] [--max-usd 15]     # PAID: real sessions
    python3 evals/run_simplifier_evals.py --score ANSWER.json                      # free: score a saved answer
    python3 evals/run_simplifier_evals.py --sandbox DIR                            # free: build the project, print the request

The project is evals/reference-project with evals/scenarios/simplifier/project/ laid over it:
six kinds of planted excess (an abstraction with one implementation, dead code, an unused
dependency, a guard against an impossible state, a slice "for the future", an invented
requirement) and four traps — things that look unneeded and are not (input validation at the
edge, error handling at the edge, a security check, a contract field only a rare path reads).
evals/scenarios/simplifier/expected.json names each.

One run = one fresh headless session of the `simplifier` agent (its own definition, its own
model, Read / Grep / Glob only) with the request `simplifier.py request` prints. The answer goes
through `simplifier.py`'s validator, as in real use, and is scored:

    recall         planted items found / planted items
    precision      findings that name a planted item (or excess the reference project had before
                   the overlay, `also_true`) / all valid findings
    traps touched  findings that name a trap, whatever action they propose — must be 0

Nothing is tuned to the result: a touched trap is reported as it is.

PAID RUNS. Sessions start only when the task in tasks/doing/ has a «Платні прогони:» line with
a dollar limit, or the owner runs this by hand with --owner-approved (which does not count inside
a Claude Code session). --max-usd stops before the limit is passed.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURE = HERE / "scenarios" / "simplifier"
LENSES = ("code", "requirements", "architecture")
RUN_TIMEOUT_S = 1200
PAID_LINE_RE = re.compile(r"^Платні прогони:.*\d+\s*(?:долар|\$|USD)", re.MULTILINE | re.IGNORECASE)
SANDBOX_ENV = 'SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\nCOMPLEXITY_GATE="warn"\n'

JsonObj = dict[str, Any]


def simplifier_module() -> Any:
    """.claude/hooks/simplifier.py — the validator real use goes through."""
    hooks = ROOT / ".claude" / "hooks"
    sys.path.insert(0, str(hooks))
    spec = importlib.util.spec_from_file_location("simplifier", hooks / "simplifier.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load .claude/hooks/simplifier.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["simplifier"] = module
    spec.loader.exec_module(module)
    return module


def paid_run_refusal(tasks_dir: Path, owner_approved: bool, in_session: bool) -> str | None:
    """Why paid sessions may not start, or None (tasks/README.md, «Платні прогони»)."""
    if owner_approved and not in_session:
        return None
    doing = sorted((tasks_dir / "doing").glob("*.md")) if (tasks_dir / "doing").is_dir() else []
    if len(doing) == 1 and PAID_LINE_RE.search(doing[0].read_text(encoding="utf-8")):
        return None
    flag = " --owner-approved does not count inside a Claude Code session." if owner_approved else ""
    return ("refusing to start paid sessions: the task in tasks/doing/ has no «Платні прогони:» line with a "
            f"dollar limit.{flag} The owner writes that line in the task, or runs this by hand with --owner-approved.")


def build_sandbox(target: Path) -> Path:
    """The reference project, the overlay on top, the agent's definition, one commit."""
    reference = HERE / "reference-project"
    tracked = subprocess.run(["git", "-C", str(reference), "ls-files", "."], capture_output=True, text=True, check=True)
    for rel in tracked.stdout.splitlines():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reference / rel, target / rel)
    shutil.copytree(FIXTURE / "project", target, dirs_exist_ok=True)
    (target / "uv.lock").unlink(missing_ok=True)   # the lock of the project before the overlay
    (target / ".claude" / "agents").mkdir(parents=True)
    shutil.copy2(ROOT / ".claude" / "agents" / "simplifier.md", target / ".claude" / "agents" / "simplifier.md")
    (target / ".claude" / "project.env").write_text(SANDBOX_ENV, encoding="utf-8")
    with (target / ".gitignore").open("a", encoding="utf-8") as handle:
        handle.write(".claude/state/\n")
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-q", "-m", "the project under review"]):
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)
    return target


def request_text(sandbox: Path, scope: list[str]) -> str:
    proc = subprocess.run(
        [sys.executable, str(ROOT / ".claude" / "hooks" / "simplifier.py"), "request", "--lens", *LENSES, "--paths", *scope],
        cwd=sandbox, capture_output=True, text=True, check=True, env={**os.environ, "CLAUDE_PROJECT_DIR": str(sandbox)})
    return proc.stdout


def matches(finding: JsonObj, entry: JsonObj) -> bool:
    path = finding["target"].split("::")[0].split(":")[0]
    text = " ".join([finding["target"], finding["claim"], *(str(e.get("detail", "")) for e in finding["evidence"])]).lower()
    return path in entry["files"] and any(word.lower() in text for word in entry["any"])


def score(findings: list[JsonObj], expected: JsonObj) -> JsonObj:
    """Each finding is counted once: a planted item first, then a trap, else unexpected."""
    found: dict[str, list[str]] = {}
    touched: list[JsonObj] = []
    unexpected: list[JsonObj] = []
    also_true = 0
    for finding in findings:
        brief = {"target": finding["target"], "category": finding["category"], "action": finding["proposed_action"],
                 "claim": finding["claim"]}
        planted = next((e["id"] for e in expected["planted"] if matches(finding, e)), None)
        trap = next((e["id"] for e in expected["traps"] if matches(finding, e)), None)
        if planted:
            found.setdefault(planted, []).append(finding["proposed_action"])
        elif any(matches(finding, e) for e in expected.get("also_true", [])):
            also_true += 1
        elif trap:
            touched.append({"trap": trap, **brief})
        else:
            unexpected.append(brief)
    total = len(expected["planted"])
    on_target = sum(len(actions) for actions in found.values()) + also_true
    return {
        "recall": round(len(found) / total, 3),
        "precision": round(on_target / len(findings), 3) if findings else None,
        "traps_touched": len(touched),
        "found": found,
        "missed": [e["id"] for e in expected["planted"] if e["id"] not in found],
        "touched": touched,
        "unexpected": unexpected,
        "findings": len(findings),
    }


def run_once(sandbox: Path, request: str, args: argparse.Namespace, simplifier: Any, expected: JsonObj) -> JsonObj:
    command = [args.claude, "-p", request, "--agent", "simplifier", "--tools", "Read", "Grep", "Glob",
               "--output-format", "json", "--strict-mcp-config", "--max-budget-usd", str(args.max_usd_per_run)]
    if args.model:
        command += ["--model", args.model]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        proc = subprocess.run(command, cwd=sandbox, capture_output=True, text=True, timeout=RUN_TIMEOUT_S,
                              check=False, env=env, stdin=subprocess.DEVNULL)
        payload = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"error": f"the session gave no result: {type(exc).__name__}", "cost_usd": 0.0}
    row: JsonObj = {"cost_usd": round(float(payload.get("total_cost_usd") or 0.0), 4),
                    "models": sorted((payload.get("modelUsage") or {}).keys()), "turns": payload.get("num_turns")}
    answer = str(payload.get("result") or "")
    if payload.get("is_error"):
        return row | {"error": f"the session ended in an error: {answer[:300]}"}
    try:
        result = simplifier.validate(sandbox, simplifier.parse_answer(answer), simplifier.known_signal_ids(sandbox))
    except ValueError as exc:
        return row | {"error": f"the answer is not a JSON list of findings: {exc}", "answer": answer[:2000]}
    return row | score(result["findings"], expected) | {
        "rejected": [{"errors": r["errors"]} for r in result["rejected"]],
        "lowered": sum(bool(f["validator"]) for f in result["findings"]),
        "answer": result["findings"],
    }


def summary(runs: list[JsonObj]) -> JsonObj:
    good = [r for r in runs if "error" not in r]
    precisions = [r["precision"] for r in good if r["precision"] is not None]
    return {
        "runs": len(runs), "scored": len(good),
        "recall_mean": round(sum(r["recall"] for r in good) / len(good), 3) if good else None,
        "precision_mean": round(sum(precisions) / len(precisions), 3) if precisions else None,
        "traps_touched_total": sum(r["traps_touched"] for r in good),
        "cost_usd": round(sum(r["cost_usd"] for r in runs), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--score", type=Path, help="score a saved answer (a JSON list of findings) and stop; free")
    parser.add_argument("--sandbox", type=Path, help="build the project here, print the request and stop; free")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the model of the agent's definition")
    parser.add_argument("--max-usd", type=float, default=15.0, help="stop before the runs together cost more")
    parser.add_argument("--max-usd-per-run", type=float, default=5.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()
    expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
    simplifier = simplifier_module()

    if args.sandbox:
        args.sandbox.mkdir(parents=True)
        print(request_text(build_sandbox(args.sandbox), expected["scope"]))
        return 0
    with tempfile.TemporaryDirectory(prefix="simplifier-eval-") as tmp:
        sandbox = build_sandbox(Path(tmp) / "project")
        request = request_text(sandbox, expected["scope"])
        if args.score:
            result = simplifier.validate(sandbox, simplifier.parse_answer(args.score.read_text(encoding="utf-8")),
                                         simplifier.known_signal_ids(sandbox))
            print(json.dumps(score(result["findings"], expected) | {"rejected": len(result["rejected"])}, indent=2, ensure_ascii=False))
            return 0
        refusal = paid_run_refusal(args.tasks_dir, args.owner_approved, bool(os.environ.get("CLAUDECODE")))
        if refusal:
            print(refusal, file=sys.stderr)
            return 2
        runs: list[JsonObj] = []
        for number in range(1, args.runs + 1):
            spent = sum(r["cost_usd"] for r in runs)
            if spent + args.max_usd_per_run > args.max_usd:
                print(f"cost limit: ${spent:.2f} spent, a run may cost ${args.max_usd_per_run:.2f}, the limit is ${args.max_usd:.2f} — stopping")
                break
            row = run_once(sandbox, request, args, simplifier, expected)
            runs.append(row)
            shown = row.get("error") or (f"recall {row['recall']}, precision {row['precision']}, traps touched {row['traps_touched']}, "
                                         f"missed {row['missed']}, {len(row['unexpected'])} unexpected")
            print(f"run {number}: {shown}  (${row['cost_usd']:.2f}, {', '.join(row.get('models', []))})")
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "host": platform.node(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "planted": [e["id"] for e in expected["planted"]], "traps": [e["id"] for e in expected["traps"]],
        "summary": summary(runs), "runs": runs,
    }
    print("\n" + json.dumps(report["summary"], indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    scored = report["summary"]["scored"]
    return 0 if scored and report["summary"]["traps_touched_total"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
