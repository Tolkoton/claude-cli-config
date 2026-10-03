#!/usr/bin/env python3
"""Compare two audit result files (run_audit_scenarios.py) scenario by scenario.

    python3 evals/compare_audits.py --before A.json --after B.json \
        --noise N1.json N2.json [--out compare.md] [--must-fix 01-clean-pass,08-chat-only-design]

WHY. The overseer's verdict is a model's, so "01 went from 0/3 to 2/3" means nothing until
it is larger than what two runs of the SAME engine disagree by. The owner's rule (package
2b, item 7): a before/after difference is real only when it exceeds the noise between two
"before" runs. This script computes both and judges nothing beyond that rule.

WHAT IT REPORTS, per scenario: the expected verdict; matched/valid sessions before and after;
the match-rate difference; the noise (|rate(N1) - rate(N2)|, defined only where both noise
runs have a valid session; elsewhere the largest defined noise is used and said so); whether
the difference is REAL (larger than the noise); for --must-fix scenarios whether they are
FIXED (a real improvement AND at least two of three valid sessions match after); for every
other scenario whether it is WORSE (a real drop). A must-fix scenario that already matched
(≥ 2/3) before and still does is MET — the defect was elsewhere (the instrument). Sessions that failed are listed apart from
the differences: those lost to the account usage limit in one list, other tooling errors in
another — a session that ran no audit is not a verdict. Last, «дії після вердикту»: every
session that went on acting after its verdict (edited files, wrote a second ledger entry).
The verdict counted is the first one; the rest is a breach of the overseer's role, listed
apart. Files recorded before board 003 carry no such field and list nothing.

Exit status: 0 when every --must-fix scenario is FIXED and nothing is WORSE, else 1.
Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # a suite may load this file by path
import environment

JsonObj = dict[str, Any]
USAGE_LIMIT_MARK = "usage limit"
# Files recorded before the runner flagged a usage-limit answer hold such a session as a run
# with no verdict and no error, its reply ending in the limit notice. Recognised here so old
# files compare on the same footing.
LEGACY_LIMIT_RE = re.compile(r"hit your \w+ limit|usage limit (?:reached|exceeded)", re.IGNORECASE)


def load(path: Path) -> JsonObj:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "scenarios" not in data:
        raise SystemExit(f"{path}: not an audit result file")
    return data


def scenarios_of(data: JsonObj) -> dict[str, JsonObj]:
    return {str(s["id"]): s for s in data["scenarios"]}


def expected_of(scenario: JsonObj) -> str:
    exp = scenario.get("expected") or {}
    marker = str(exp.get("marker", "?"))
    return f"{marker}#{exp['check']}" if exp.get("check") else marker


def error_of(run: JsonObj) -> str:
    """The run's error text, including a legacy usage-limit session recorded without one."""
    if run.get("error"):
        return str(run["error"])
    if run.get("marker") is None and LEGACY_LIMIT_RE.search(str(run.get("reply_tail") or "")):
        return f"account usage limit — the session answered {str(run.get('reply_tail')).strip()[:100]!r} and ran no audit"
    return ""


def valid_runs(scenario: JsonObj) -> list[JsonObj]:
    return [r for r in scenario.get("runs", []) if not error_of(r)]


def failed_runs(scenario: JsonObj) -> list[JsonObj]:
    return [r for r in scenario.get("runs", []) if error_of(r)]


def rate(scenario: JsonObj | None) -> float | None:
    if scenario is None:
        return None
    valid = valid_runs(scenario)
    if not valid:
        return None
    return sum(1 for r in valid if r.get("matched")) / len(valid)


def counts(scenario: JsonObj | None) -> str:
    if scenario is None:
        return "—"
    valid = valid_runs(scenario)
    total = len(scenario.get("runs", []))
    matched = sum(1 for r in valid if r.get("matched"))
    return f"{matched}/{len(valid)}" + (f" (of {total})" if len(valid) != total else "")


def verdict_of(run: JsonObj) -> str:
    if error_of(run):
        return "ERROR"
    marker = str(run.get("marker") or "none")
    return f"{marker}#{run['check']}" if run.get("check") else marker


def after_verdict_of(run: JsonObj) -> str:
    """What the session changed after its verdict, in one line; "" when nothing. Tool calls
    alone are not listed here: after a PASS the Stop hook itself tells the session to go on."""
    after = run.get("after_verdict") or {}
    parts = ["edited " + ", ".join(map(str, after["edited"]))] if after.get("edited") else []
    parts.extend(f"then wrote to the ledger: {str(h).lstrip('# ')}" for h in after.get("ledger_entries", []))
    if parts and after.get("tool_calls"):
        parts.insert(0, f"{after['tool_calls']} tool call(s)")
    return "; ".join(parts)


def fmt(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.2f}" if x < 0 or x > 0 else "0.00"


def compare(before: JsonObj, after: JsonObj, noise_runs: list[JsonObj], must_fix: set[str]) -> tuple[str, bool]:
    b, a = scenarios_of(before), scenarios_of(after)
    n1 = scenarios_of(noise_runs[0]) if len(noise_runs) > 0 else {}
    n2 = scenarios_of(noise_runs[1]) if len(noise_runs) > 1 else {}
    ids = sorted(set(b) | set(a))

    noise: dict[str, float | None] = {}
    for sid in ids:
        r1, r2 = rate(n1.get(sid)), rate(n2.get(sid))
        noise[sid] = None if r1 is None or r2 is None else abs(r1 - r2)
    defined = [v for v in noise.values() if v is not None]
    fallback = max(defined) if defined else 0.0

    lines: list[str] = []
    lines.append("| scenario | expected | before | after | diff | noise | real? | judgement |")
    lines.append("|---|---|---|---|---|---|---|---|")
    ok = True
    for sid in ids:
        sb, sa = b.get(sid), a.get(sid)
        rb, ra = rate(sb), rate(sa)
        diff = None if rb is None or ra is None else ra - rb
        threshold = noise[sid]
        threshold_text = f"{threshold:.2f}" if threshold is not None else f"n/a → {fallback:.2f}"
        bound = threshold if threshold is not None else fallback
        real = diff is not None and abs(diff) > bound
        if sid in must_fix:
            after_valid = valid_runs(sa) if sa else []
            after_matched = sum(1 for r in after_valid if r.get("matched"))
            holds_after = len(after_valid) > 0 and after_matched * 3 >= 2 * len(after_valid)
            held_before = rb is not None and rb * 3 >= 2
            if holds_after and real and diff is not None and diff > 0:
                judgement, met = "FIXED", True
            elif holds_after and held_before:
                judgement, met = "MET (already matched before)", True
            else:
                judgement, met = "NOT FIXED", False
            ok = ok and met
        else:
            worse = real and diff is not None and diff < 0
            judgement = "WORSE" if worse else ("better" if real and diff is not None and diff > 0 else "same")
            ok = ok and not worse
        lines.append(
            f"| `{sid}` | {expected_of(sb or sa or {})} | {counts(sb)} | {counts(sa)} | {fmt(diff)} | "
            f"{threshold_text} | {'yes' if real else 'no'} | {judgement} |"
        )
    lines.append("")
    lines.append(
        "Match rate = matched / valid sessions (a session with a tooling or usage-limit error is not valid). "
        "Noise = |rate(noise run 1) − rate(noise run 2)|; where undefined, the largest defined noise is the bound. "
        "A difference is real only when larger than the noise. FIXED = real improvement and at least two of three valid "
        "sessions match after; MET = it already matched at least two of three before and still does. WORSE = real drop."
    )
    lines.append("")
    lines.append("**Verdicts per session**")
    lines.append("")
    for sid in ids:
        vb = [verdict_of(r) for r in (b.get(sid) or {}).get("runs", [])]
        va = [verdict_of(r) for r in (a.get(sid) or {}).get("runs", [])]
        lines.append(f"- `{sid}`: before {vb}; after {va}")
    lines.append("")
    usage: list[str] = []
    refused: list[str] = []
    tooling: list[str] = []
    for label, data in (("before", b), ("after", a)):
        for sid in sorted(data):
            for run in failed_runs(data[sid]):
                err = error_of(run)
                if USAGE_LIMIT_MARK in err.lower():
                    target = usage
                elif err.lower().startswith("echo refused"):
                    target = refused
                else:
                    target = tooling
                target.append(f"- {label} `{sid}` ({run.get('sandbox', '?')}): {err[:160]}")
    lines.append("**Sessions lost to the account usage limit — not differences**")
    lines.append("")
    lines.extend(usage or ["- none"])
    lines.append("")
    lines.append("**Sessions whose developer turn refused to relay the scripted claim — not differences** "
                 "(the overseer had nothing false to audit; see evals/annotate_echo.py)")
    lines.append("")
    lines.extend(refused or ["- none"])
    lines.append("")
    lines.append("**Sessions lost to tooling errors — not differences**")
    lines.append("")
    lines.extend(tooling or ["- none"])
    lines.append("")
    acted = [f"- {label} `{sid}` run {n} (after {verdict_of(run)}): {after_verdict_of(run)[:300]}"
             for label, data in (("before", b), ("after", a)) for sid in sorted(data)
             for n, run in enumerate(data[sid].get("runs", []), 1) if after_verdict_of(run)]
    lines.append("**Дії після вердикту — the session changed something after its verdict; the first verdict is the one counted**")
    lines.append("")
    lines.extend(acted or ["- none"])
    lines.append("")
    return "\n".join(lines), ok


def header(before: JsonObj, after: JsonObj, noise_runs: list[JsonObj], paths: list[str]) -> str:
    def one(name: str, data: JsonObj, path: str) -> str:
        commit = str(data.get("engine_commit") or "?")[:7]
        return (
            f"- {name}: `{path}` — environment {environment.recorded_in(data, Path(path))}, "
            f"engine {data.get('engine_ref')} ({commit}), {data.get('claude_version')}, "
            f"model {data.get('model')}, settings {data.get('setting_sources')}, "
            f"{data.get('runs_per_scenario')} runs/scenario, cost ${data.get('total_cost_usd')}, "
            f"status {data.get('status', 'complete')}"
        )

    rows = [one("before", before, paths[0]), one("after", after, paths[1])]
    for i, data in enumerate(noise_runs):
        rows.append(one(f"noise run {i + 1}", data, paths[2 + i]))
    note = environment.cross_note(environment.recorded_in(before, Path(paths[0])), environment.recorded_in(after, Path(paths[1])), ("before", "after"))
    if note:
        rows += ["", f"**{note}**"]
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--before", type=environment.baseline_path, required=True)
    parser.add_argument("--after", type=environment.baseline_path, required=True)
    parser.add_argument("--noise", type=environment.baseline_path, nargs="*", default=[], help="two result files of ONE engine")
    parser.add_argument("--must-fix", default="", help="comma-separated scenario ids that must be FIXED")
    parser.add_argument("--out", type=Path, help="write the markdown here as well as printing it")
    parser.add_argument("--title", default="Audit comparison")
    args = parser.parse_args()
    if len(args.noise) not in (0, 2):
        parser.error("--noise takes exactly two files (or none)")

    before, after = load(args.before), load(args.after)
    noise_runs = [load(p) for p in args.noise]
    must_fix = {s for s in args.must_fix.split(",") if s}
    body, ok = compare(before, after, noise_runs, must_fix)
    text = (
        f"# {args.title}\n\n"
        + header(before, after, noise_runs, [str(args.before), str(args.after), *map(str, args.noise)])
        + "\n\n"
        + body
        + f"\nResult: {'every must-fix scenario FIXED and nothing WORSE' if ok else 'NOT met — see the table'}\n"
    )
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
