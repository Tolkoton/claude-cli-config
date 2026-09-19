#!/usr/bin/env python3
"""Show where two hook-scenario result files disagree.

    python3 evals/compare.py BASE.json CANDIDATE.json [--details]

Compares what the hooks DECIDED (the outcome sequence and, where a scenario
watches a file, whether it changed). Wording of a reason is not compared: it may
legitimately differ between engine versions. Pass --details to print it anyway.

Exit code 0: identical behaviour. 1: differences (listed). 2: unusable input.
A difference is not a verdict — it is a change that someone has to explain:
either a fix that was intended, or a regression that was not.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

JsonObj = dict[str, Any]


def load(path: Path) -> tuple[JsonObj, dict[str, JsonObj]]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        return report, {r["id"]: r for r in report["results"]}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"cannot read results from {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def behaviour(result: JsonObj | None) -> str:
    if result is None:
        return "(scenario not run)"
    text = " -> ".join(result["outcomes"])
    if "file_changed" in result:
        text += f", file changed: {str(result['file_changed']).lower()}"
    return text


def describe(report: JsonObj, path: Path) -> str:
    sandbox = report.get("sandbox", {})
    env = report.get("environment", {})
    parts = [
        f"engine {sandbox.get('engine_ref', '?')} ({str(sandbox.get('engine_commit', '?'))[:7]})",
        f"hooks {report.get('hooks_dir', '?')}",
        f"jq: {env.get('jq', '?')}",
        f"python {env.get('python', '?')}",
    ]
    label = report.get("label")
    return f"{path.name}: " + ", ".join(parts) + (f" — {label}" if label else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--details", action="store_true", help="also print each side's reason")
    args = parser.parse_args()

    base_report, base = load(args.base)
    cand_report, cand = load(args.candidate)
    print("BASE      " + describe(base_report, args.base))
    print("CANDIDATE " + describe(cand_report, args.candidate))
    print()

    ids = list(base) + [i for i in cand if i not in base]
    differences = 0
    for scenario_id in ids:
        left, right = behaviour(base.get(scenario_id)), behaviour(cand.get(scenario_id))
        if left == right:
            continue
        differences += 1
        print(f"  DIFF {scenario_id}")
        print(f"         base:      {left}")
        print(f"         candidate: {right}")
        if args.details:
            for side, source in (("base", base), ("candidate", cand)):
                detail = (source.get(scenario_id) or {}).get("detail")
                if detail:
                    print(f"         {side} reason: {detail}")

    same = len(ids) - differences
    if differences:
        print(f"\n{differences} scenario(s) differ, {same} identical")
        return 1
    print(f"identical behaviour in all {same} scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
