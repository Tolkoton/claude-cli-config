#!/usr/bin/env python3
"""Measure gate.py on files with deliberate defects and on clean files, and time every layer.

    python3 evals/run_gate_evals.py --engine-ref HEAD [--runs 3] [--out FILE]
    python3 evals/run_gate_evals.py --sandbox DIR [--out FILE]

Two questions, answered with real ruff, mypy and pytest in the reference project (no shims):

    defective  every file with a planted defect must be CAUGHT: gate.py exits 2 and names the
               defect's own rule (a block for an unrelated reason is not a catch)
    clean      no clean change may be blocked: exit 0 and no `block` finding, on every layer

and a third kind, `limit`: a case that documents what a layer deliberately does NOT see (the
Stop layer is incremental, so a type error committed earlier is invisible to it; `ci` catches it).
It asserts the miss, so a change that silently widens or narrows the layer shows up.

The time of every layer is recorded: wall clock per run (process start included), the gate's own
per-step timings, and min / median / max per layer over all cases and --runs repetitions.

The cases are data: evals/scenarios/gate/cases.json. Standard library only, Python 3.12+. Nothing
here talks to a model.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from run_hook_scenarios import SandboxError, apply_setup, git, reset_sandbox

JsonObj = dict[str, Any]
HERE = Path(__file__).resolve().parent
TIMEOUT_S = 600


def run_gate(sandbox: Path, layer: str, case: JsonObj) -> JsonObj:
    cmd = [sys.executable, str(sandbox / ".claude/hooks/gate.py"), "--layer", layer]
    stdin = ""
    if layer == "post_write":
        cmd.append("--hook")
        stdin = json.dumps({"tool_input": {"file_path": str(sandbox / case["edited"])}})
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=sandbox, input=stdin, capture_output=True, text=True,
                          timeout=TIMEOUT_S, check=False,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(sandbox)})
    wall_ms = int((time.perf_counter() - started) * 1000)
    report_path = sandbox / ".claude/state/gate/last-report.json"
    report: JsonObj = json.loads(report_path.read_text()) if report_path.is_file() else {}
    return {"exit": proc.returncode, "wall_ms": wall_ms, "stdout": proc.stdout, "report": report}


def prepare(sandbox: Path, base: str, case: JsonObj, layer: str) -> None:
    reset_sandbox(sandbox)
    git(sandbox, "reset", "-q", "--hard", base)  # a case that commits must not leak into the next
    apply_setup(sandbox, case.get("setup", []))
    if case.get("commit"):
        git(sandbox, "add", "-A")
        done = git(sandbox, "-c", "user.name=eval", "-c", "user.email=eval@example.invalid",
                   "commit", "-q", "-m", "case baseline", check=False)
        if done.returncode != 0:
            raise SandboxError(f"case {case['id']}: cannot commit its baseline: {done.stdout}{done.stderr}")
    for step in case.get("then", []):
        apply_setup(sandbox, [step])
    if layer == "pre_commit" or case.get("stage"):
        git(sandbox, "add", "-A")


def judge(case: JsonObj, layer: str, got: JsonObj) -> tuple[bool, str]:
    report = got["report"]
    blocking = [f for f in report.get("findings", []) if f.get("severity") == "block"]
    rules = sorted({f["rule"] for f in blocking})
    kind = case["kind"]
    if kind == "defective":
        want = case["rule"]
        caught = got["exit"] == 2 and any(r == want or r.startswith(want) for r in rules)
        return caught, f"exit {got['exit']}, blocking rules {rules}, wanted {want}"
    if kind == "limit":
        missed = got["exit"] == 0 and not blocking
        return missed, f"exit {got['exit']}, blocking rules {rules} (a documented miss must stay one)"
    if layer == "post_write":
        silent = got["exit"] == 0 and not got["stdout"].strip()
        return silent, f"exit {got['exit']}, stdout {got['stdout'][:80]!r}"
    clean = got["exit"] == 0 and not blocking
    return clean, f"exit {got['exit']}, blocking rules {rules}"


def run_post_write_defect(case: JsonObj, got: JsonObj) -> tuple[bool, str]:
    out = got["stdout"]
    try:
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
    except (ValueError, KeyError):
        context = ""
    shown = got["exit"] == 0 and case["rule"] in context
    return shown, f"exit {got['exit']}, additionalContext {context[:100]!r}"


def stats(values: list[int]) -> JsonObj:
    return {"n": len(values), "min_ms": min(values), "median_ms": int(statistics.median(values)),
            "max_ms": max(values)}


def run_all(sandbox: Path, cases: list[JsonObj], runs: int, only: str) -> tuple[list[JsonObj], JsonObj, bool]:
    base = git(sandbox, "rev-parse", "HEAD").stdout.strip()
    results: list[JsonObj] = []
    walls: dict[str, list[int]] = {}
    ok_all = True
    for case in cases:
        if only and only not in case["id"]:
            continue
        for layer in case["layers"]:
            samples: list[int] = []
            verdict, detail, step_ms = False, "", {}
            for run in range(runs):
                prepare(sandbox, base, case, layer)
                got = run_gate(sandbox, layer, case)
                samples.append(got["wall_ms"])
                walls.setdefault(layer, []).append(got["wall_ms"])
                if run == 0:
                    if layer == "post_write" and case["kind"] == "defective":
                        verdict, detail = run_post_write_defect(case, got)
                    else:
                        verdict, detail = judge(case, layer, got)
                    step_ms = got["report"].get("timings_ms", {}).get("steps", {})
            ok_all = ok_all and verdict
            print(f"  {'ok  ' if verdict else 'FAIL'} {case['kind']:9} {case['id']:38} {layer:10} "
                  f"{int(statistics.median(samples)):>6} ms  {detail if not verdict else ''}")
            results.append({"id": case["id"], "kind": case["kind"], "layer": layer, "why": case.get("why", ""),
                            "pass": verdict, "detail": detail, "wall_ms": samples, "steps_ms": step_ms})
    reset_sandbox(sandbox)
    return results, {layer: stats(v) for layer, v in sorted(walls.items())}, ok_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else "")
    parser.add_argument("--sandbox", type=Path)
    parser.add_argument("--engine-ref")
    parser.add_argument("--runs", type=int, default=3, help="repetitions per case and layer, for the timings")
    parser.add_argument("--cases", type=Path, default=HERE / "scenarios" / "gate" / "cases.json")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--only", default="")
    parser.add_argument("--label", default="")
    args = parser.parse_args()
    if bool(args.sandbox) == bool(args.engine_ref):
        parser.error("give exactly one of --sandbox and --engine-ref")
    temp: Path | None = None
    if args.engine_ref:
        temp = Path(tempfile.mkdtemp(prefix="engine-gate-"))
        args.sandbox = temp / "sandbox"
        build = subprocess.run(["bash", str(HERE / "make_sandbox.sh"), args.engine_ref, str(args.sandbox)],
                               capture_output=True, text=True, check=False)
        if build.returncode != 0:
            shutil.rmtree(temp, ignore_errors=True)
            print(build.stderr.strip() or "make_sandbox.sh failed", file=sys.stderr)
            return 2
    try:
        sandbox = args.sandbox.resolve()
        info = json.loads((sandbox / "SANDBOX-INFO.json").read_text())
        cases = json.loads(args.cases.read_text())["cases"]
        results, timings, ok_all = run_all(sandbox, cases, max(1, args.runs), args.only)
    except (SandboxError, OSError) as exc:
        print(f"sandbox error: {exc}", file=sys.stderr)
        return 2
    finally:
        if temp:
            shutil.rmtree(temp, ignore_errors=True)

    def count(kind: str) -> int:
        return len({r["id"] for r in results if r["kind"] == kind})

    failed = [r for r in results if not r["pass"]]
    summary = {
        "defective_cases": count("defective"),
        "defects_caught": len({r["id"] for r in results if r["kind"] == "defective" and r["pass"]}),
        "clean_cases": count("clean"),
        "false_blocks": len([r for r in results if r["kind"] == "clean" and not r["pass"]]),
        "documented_limits": count("limit"),
        "failed": [f"{r['id']}@{r['layer']}" for r in failed],
    }
    print(f"\ncaught {summary['defects_caught']}/{summary['defective_cases']} defects, "
          f"{summary['false_blocks']} false block(s) over {summary['clean_cases']} clean cases")
    for layer, st in timings.items():
        print(f"  {layer:10} median {st['median_ms']:>6} ms   min {st['min_ms']}   max {st['max_ms']}   (n={st['n']})")
    if args.out:
        report = {
            "label": args.label, "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sandbox": info, "environment": {"platform": platform.platform(), "python": platform.python_version()},
            "summary": summary, "timings_ms": timings, "results": results,
        }
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
