#!/usr/bin/env python3
"""Measure the second opinion: does Gemini catch a wrong simplifier finding, and does a fresh Claude catch as much?

    python3 evals/run_second_opinion_evals.py --runs 3 --out evals/baseline/@env/second-opinion-evals.json   # PAID
    python3 evals/run_second_opinion_evals.py --list            # free: the cases and the size of each request
    python3 evals/run_second_opinion_evals.py --score FILE      # free: the summary of a recorded result

evals/scenarios/second-opinion/cases.json holds findings with a known truth: `correct` (removing
the target is safe) and `false` (the target is needed). Each case is put to two judges with the
SAME request — the one .claude/hooks/second_opinion.py builds in real use:

    gemini   the model of SECOND_OPINION_MODEL, through the hook's own code
    claude   a fresh headless session with no tools and the same system text — the control:
             without it nobody can tell "a different model helps" from "a second look helps"

Two figures per judge, per run and in the mean: caught = `disagree` on a false finding;
false alarms = `disagree` on a correct one. An answer that is missing or broken counts as not
caught and no alarm, and is reported. The thresholds are the owner's (board 012, answer 6):
Gemini catches at least half of the false findings, raises an alarm on at most one correct
finding in ten, and catches noticeably more than the control — taken here as 0.15 more of the
false findings. Nothing is tuned to the result.

The fixture cases are judged on evals/reference-project + scenarios/simplifier/project + scenarios/
second-opinion/project; the engine cases on this repository as it was at `engine_commit`.

PAID RUNS. As run_simplifier_evals.py: only on a «Платні прогони:» line with a dollar limit in the
task in tasks/doing/, or the owner's --owner-approved outside a session. Without the key
(GEMINI_API_KEY_SIMPLIFIER) nothing starts at all: half a measurement is not a measurement.
--max-usd stops before the limit is passed; a run that was cut short is not in the summary.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import environment
import run_simplifier_evals as fixture

second: Any = importlib.import_module("second_opinion")
budget: Any = importlib.import_module("complexity_budget")

SCENARIO = HERE / "scenarios" / "second-opinion"
JUDGES = ("gemini", "claude")
MIN_CAUGHT, MAX_ALARMS, MIN_MARGIN = 0.5, 0.1, 0.15
CALL_RESERVE_USD = 0.3
CLAUDE_TIMEOUT_S = 300
JsonObj = dict[str, Any]


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)


def build_projects(work: Path, doc: JsonObj) -> dict[str, Path]:
    """The two repositories the cases are judged on."""
    sandbox = fixture.build_sandbox(work / "fixture")
    shutil.copytree(SCENARIO / "project", sandbox, dirs_exist_ok=True)
    engine = work / "engine"
    engine.mkdir()
    archive = git(ROOT, "archive", doc["engine_commit"])
    if archive.returncode != 0:
        raise RuntimeError(f"this clone does not hold the commit {doc['engine_commit'][:10]} the engine cases are judged on")
    subprocess.run(["tar", "-x", "-C", str(engine)], input=archive.stdout, check=True)
    for repo, args in ((sandbox, ["add", "-A"]), (sandbox, ["commit", "-q", "-m", "second-opinion overlay"]),
                       (engine, ["init", "-q", "-b", "main"]), (engine, ["add", "-A"]), (engine, ["commit", "-q", "-m", "the engine before board 011"])):
        done = git(repo, "-c", "user.name=eval", "-c", "user.email=eval@example.invalid", *args)
        if done.returncode != 0:
            raise RuntimeError(done.stderr.decode("utf-8", "replace"))
    return {"fixture": sandbox, "engine": engine}


def requests_for(projects: dict[str, Path], doc: JsonObj) -> list[JsonObj]:
    rows = []
    for case in doc["cases"]:
        root = projects[case["project"]]
        env = budget.project_env(root) | {"SIMPLIFY_EXCLUDE": "", "SIMPLIFIER_PROTECTED": ""}
        prompt, sent = second.collect(root, env, case["finding"])
        rows.append({"case": case, "prompt": prompt, "sent": sent})
    return rows


def ask_gemini(prompt: str, config: JsonObj, key: str) -> tuple[JsonObj | None, float, str]:
    raw, error = second.ask(second.body_for(prompt), config["model"], key)
    answer, tokens = second.parsed(raw) if raw else (None, {"in": 0, "out": 0})
    return answer, second.cost_usd(config, tokens), error


def ask_claude(prompt: str, args: argparse.Namespace, cwd: Path) -> tuple[JsonObj | None, float, str]:
    command = [args.claude, "-p", prompt, "--system-prompt", second.SYSTEM, "--tools", "", "--output-format", "json",
               "--strict-mcp-config", "--max-budget-usd", str(args.max_usd_per_call)]
    if args.claude_model:
        command += ["--model", args.claude_model]
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", second.KEY_VAR)}
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_S, check=False,
                              env=env, stdin=subprocess.DEVNULL)
        payload = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return None, 0.0, f"the session gave no result: {type(exc).__name__}"
    cost = round(float(payload.get("total_cost_usd") or 0.0), 6)
    if payload.get("is_error"):
        return None, cost, f"the session ended in an error: {str(payload.get('result'))[:200]}"
    return second.answer_object(str(payload.get("result") or "")), cost, ""


def rates(rows: list[JsonObj]) -> JsonObj:
    """caught and false alarms over the given answers (one judge, any number of runs)."""
    false = [r for r in rows if r["truth"] == "false"]
    correct = [r for r in rows if r["truth"] == "correct"]

    def share(part: list[JsonObj], test: Any) -> float | None:
        return round(sum(1 for r in part if test(r)) / len(part), 3) if part else None
    return {
        "caught": share(false, lambda r: r["verdict"] == "disagree"),
        "caught_with_a_checked_line": share(false, lambda r: r["verdict"] == "disagree" and r["verified"]),
        "false_alarms": share(correct, lambda r: r["verdict"] == "disagree"),
        "false_alarms_with_a_checked_line": share(correct, lambda r: r["verdict"] == "disagree" and r["verified"]),
        "unsure": sum(r["verdict"] == "unsure" for r in rows), "no_opinion": sum(r["verdict"] == "no_opinion" for r in rows),
        "false_findings": len(false), "correct_findings": len(correct),
    }


def summary(runs: list[JsonObj]) -> JsonObj:
    whole = [r for r in runs if r.get("complete")]
    out: JsonObj = {"runs": len(runs), "complete_runs": len(whole), "cost_usd": round(sum(a["cost_usd"] for r in runs for a in r["answers"]), 4)}
    for judge in JUDGES:
        answers = [a for r in whole for a in r["answers"] if a["judge"] == judge]
        per_run = [rates([a for a in r["answers"] if a["judge"] == judge]) for r in whole]
        out[judge] = rates(answers) | {
            "caught_per_run": [p["caught"] for p in per_run], "false_alarms_per_run": [p["false_alarms"] for p in per_run],
            "caught_by_kind": {kind: rates([a for a in answers if a["kind"] == kind])["caught"] for kind in ("trap", "typical")},
            "false_alarms_by_kind": {kind: rates([a for a in answers if a["kind"] == kind])["false_alarms"] for kind in ("planted", "first-pass")},
            "cost_usd": round(sum(a["cost_usd"] for a in answers), 4),
        }
    gemini, claude = out["gemini"], out["claude"]
    if whole and None not in (gemini["caught"], gemini["false_alarms"], claude["caught"]):
        margin = round(gemini["caught"] - claude["caught"], 3)
        checks = {f"gemini catches at least {MIN_CAUGHT} of the false findings": gemini["caught"] >= MIN_CAUGHT,
                  f"gemini raises an alarm on at most {MAX_ALARMS} of the correct ones": gemini["false_alarms"] <= MAX_ALARMS,
                  f"gemini catches at least {MIN_MARGIN} more than the control": margin >= MIN_MARGIN}
        out["thresholds"] = {"margin_over_control": margin, "checks": checks, "passed": all(checks.values())}
    else:
        out["thresholds"] = {"passed": None, "why": "no complete run to judge"}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", type=environment.out_path, help="a baseline goes to evals/baseline/@env/")
    parser.add_argument("--list", action="store_true", help="print the cases and the size of each request, and stop; free")
    parser.add_argument("--score", type=Path, help="print the summary of a recorded result and stop; free")
    parser.add_argument("--only", default="", help="only the cases whose id contains this")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--claude-model", default="fable", help="the control's model: the one the simplifier agent itself runs on")
    parser.add_argument("--max-usd", type=float, default=15.0, help="stop before both judges together cost more")
    parser.add_argument("--max-usd-per-call", type=float, default=1.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()
    if args.score:
        print(json.dumps(summary(json.loads(args.score.read_text(encoding="utf-8"))["runs"]), indent=2, ensure_ascii=False))
        return 0
    doc = json.loads((SCENARIO / "cases.json").read_text(encoding="utf-8"))
    doc["cases"] = [c for c in doc["cases"] if args.only in c["id"]]
    config = second.settings(budget.project_env(ROOT))
    with tempfile.TemporaryDirectory(prefix="engine-second-opinion-eval-") as tmp:
        requests = requests_for(build_projects(Path(tmp), doc), doc)
        if args.list:
            for row in requests:
                print(f"{row['case']['truth']:<8} {row['case']['id']:<40} {len(row['prompt']):>7} chars  {row['case']['finding']['target']}")
            chars = sum(len(r["prompt"]) for r in requests)
            print(f"\n{len(requests)} cases, {chars} characters of request in all (about {chars // 4} tokens per judge per run)")
            return 0
        refusal = fixture.paid_run_refusal(args.tasks_dir, args.owner_approved, bool(os.environ.get("CLAUDECODE")))
        key = os.environ.get(second.KEY_VAR, "").strip()
        refusal = refusal or (second.refusal(config, key) and f"nothing started — {second.refusal(config, key)}. The measurement needs both judges.")
        if refusal:
            print(refusal, file=sys.stderr)
            return 2
        empty = Path(tmp) / "empty"
        empty.mkdir()
        runs: list[JsonObj] = []
        spent = 0.0
        for number in range(1, args.runs + 1):
            run: JsonObj = {"run": number, "complete": True, "answers": []}
            runs.append(run)
            for row in requests:
                for judge in JUDGES:
                    if spent + CALL_RESERVE_USD > args.max_usd:
                        run["complete"] = False
                        break
                    answer, cost, error = ask_gemini(row["prompt"], config, key) if judge == "gemini" else ask_claude(row["prompt"], args, empty)
                    spent += cost
                    opinion = second.no_opinion(error) if error else second.checked(answer, row["sent"])
                    case = row["case"]
                    run["answers"].append({"case": case["id"], "truth": case["truth"], "kind": case["kind"], "judge": judge,
                                           "cost_usd": cost, **opinion})
                if not run["complete"]:
                    break
            shown = {judge: rates([a for a in run["answers"] if a["judge"] == judge]) for judge in JUDGES}
            print(f"run {number}{'' if run['complete'] else ' (cut short by the cost limit)'}: "
                  + "; ".join(f"{j} caught {s['caught']}, false alarms {s['false_alarms']}, no opinion {s['no_opinion']}" for j, s in shown.items())
                  + f"  (${spent:.2f} so far)")
            if not run["complete"]:
                print(f"cost limit: ${spent:.2f} spent, the limit is ${args.max_usd:.2f} — stopping")
                break
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(),
        "engine_commit": git(ROOT, "rev-parse", "HEAD").stdout.decode().strip(), "cases_engine_commit": doc["engine_commit"],
        "models": {"gemini": config["model"], "claude": args.claude_model}, "summary": summary(runs), "runs": runs,
    }
    print("\n" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return 0 if report["summary"]["thresholds"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
