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
another — a session that ran no audit is not a verdict. A scenario both files ran, with no valid
session on one side, is NOT MEASURED (never WORSE, never "same"), and a file without one verdict
in it is such on every scenario: the instrument failed (board 014). A scenario only one file has
is "only before" / "only after" and fails nothing. Last, «дії після вердикту»: every
session that went on acting after its verdict (edited files, wrote a second ledger entry).
The verdict counted is the first one; the rest is a breach of the overseer's role, listed
apart. Files recorded before board 003 carry no such field and list nothing.

THE RECORDED NOISE (board 058). Two noise runs for every comparison cost two full audits, so the
noise is measured once and kept: `--measure-noise N1.json N2.json` takes two (or more) complete
result files of ONE engine commit and environment, prints the noise scene by scene — the verdicts of every
session, the match rate of every run, the spread between the runs — and with `--out-record`
writes the record `audit-noise.json`. A comparison without `--noise` reads the record that lies
beside its `--before` file (`--noise-record FILE` names another, `--noise-record none` none) and
says in its header which one it used. The bound of a scenario is then the larger of its own
recorded spread and the record's threshold — the largest spread seen on any scene: a scene that
did not move in two runs is not thereby shown to be stiller than the scene that did. A difference
that is not zero and not larger than the bound is «у межах шуму» (within the noise), never
"better" or WORSE. With no record and no `--noise` the bound is 0 and the header says the noise
was not measured.

Exit status: 0 when every --must-fix scenario is FIXED and nothing is WORSE or NOT MEASURED, else 1
(`--measure-noise`: 0 when the record could be computed, 2 when the files are not runs of one engine).
Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from fractions import Fraction
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
# The same for a session the API refused (board 014): the whole reply is the CLI's error line.
LEGACY_FAILED_RE = re.compile(r"\A\s*(?:Failed to authenticate|API Error)\b")
NO_VERDICT_ANYWHERE = "no verdict in any session of this file — the instrument failed, the overseer was not measured"
NOT_MEASURED = "NOT MEASURED"
# The owner's name for a difference two runs of one engine also show (board 058).
WITHIN_NOISE = "у межах шуму"
NOISE_RECORD_NAME = "audit-noise.json"
NO_RECORD = "none"


def load(path: Path) -> JsonObj:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "scenarios" not in data:
        raise SystemExit(f"{path}: not an audit result file")
    runs = [r for s in data["scenarios"] for r in s.get("runs", [])]
    if runs and not any(r.get("marker") for r in runs):
        # Zero verdicts in a whole file is not N sessions that each chose to say nothing.
        for run in runs:
            if not error_of(run):
                run["error"] = f"{NO_VERDICT_ANYWHERE}; the session ended with {str(run.get('reply_tail') or '').strip()[-100:]!r}"
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
    if run.get("marker") is None and LEGACY_FAILED_RE.search(str(run.get("reply_tail") or "")):
        return f"session failed — the session answered {str(run.get('reply_tail')).strip()[:100]!r} and ran no audit"
    return ""


def valid_runs(scenario: JsonObj) -> list[JsonObj]:
    return [r for r in scenario.get("runs", []) if not error_of(r)]


def failed_runs(scenario: JsonObj) -> list[JsonObj]:
    return [r for r in scenario.get("runs", []) if error_of(r)]


def rate(scenario: JsonObj | None) -> Fraction | None:
    """Matched / valid sessions, as an exact fraction: «not larger than the noise» is a question
    of equality, and in floats 1 − 2/3 is larger than 2/3 − 1/3 (board 058)."""
    if scenario is None:
        return None
    valid = valid_runs(scenario)
    if not valid:
        return None
    return Fraction(sum(1 for r in valid if r.get("matched")), len(valid))


def exact(value: Any) -> Fraction:
    """A match rate or a noise read back from a record, where it is kept as a decimal number."""
    return Fraction(value).limit_denominator(10_000)


def as_number(value: Fraction | None) -> float | None:
    return None if value is None else float(value)


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


def fmt(x: Fraction | None) -> str:
    return "n/a" if x is None else f"{float(x):+.2f}" if x != 0 else "0.00"


def spread(rates: list[Fraction | None]) -> Fraction | None:
    """The noise of one scenario: the largest difference between the match rates of runs of one
    engine. None when fewer than two of the runs hold a valid session for it."""
    known = [r for r in rates if r is not None]
    return max(known) - min(known) if len(known) > 1 and len(known) == len(rates) else None


def measure_noise(runs: list[JsonObj], paths: list[str]) -> tuple[JsonObj | None, str]:
    """The noise record of two or more result files of one engine, or (None, why not). The
    files must be complete and name one commit, model and settings: anything else measures
    a difference between engines, which is the thing the noise is there to be told from."""
    for key in ("engine_commit", "model", "setting_sources", "runs_per_scenario"):
        values = {str(r.get(key)) for r in runs}
        if len(values) != 1:
            return None, f"the files differ in {key} ({', '.join(sorted(values))}) — the noise is the disagreement of runs of ONE engine"
    places = sorted({environment.recorded_in(r, Path(p)) for r, p in zip(runs, paths, strict=True)})
    if len(places) != 1:
        return None, f"the files were recorded in different environments ({', '.join(places)}) — a difference may be the environment's"
    partial = [p for r, p in zip(runs, paths, strict=True) if r.get("status", "complete") != "complete"]
    if partial:
        return None, f"not a complete recording: {', '.join(partial)} — finish it with --resume first"
    tables = [scenarios_of(r) for r in runs]
    scenes: JsonObj = {}
    for sid in sorted(set().union(*tables)):
        rows = [t.get(sid) for t in tables]
        verdicts = [[verdict_of(x) for x in (row or {}).get("runs", [])] for row in rows]
        valid = [v for per_run in verdicts for v in per_run if v != "ERROR"]
        scenes[sid] = {
            "expected": expected_of(next(row for row in rows if row)),
            "verdicts": verdicts,
            "matched": [counts(row) for row in rows],
            "rates": [as_number(rate(row)) for row in rows],
            "noise": as_number(spread([rate(row) for row in rows])),
            # Apart from the match rate: three BLOCK#4 and three BLOCK#1 on a scene that expects
            # neither is a rate of 0 twice and a verdict that is not stable.
            "distinct_verdicts": sorted(set(valid)),
        }
    defined = [float(s["noise"]) for s in scenes.values() if s["noise"] is not None]
    record: JsonObj = {
        "what": "the noise of the overseer audit: how far two recordings of ONE engine disagree (evals/README.md)",
        "environment": places[0], "engine_commit": runs[0].get("engine_commit"),
        "claude_version": sorted({str(r.get("claude_version")) for r in runs}), "model": runs[0].get("model"),
        "runs_per_scenario": runs[0].get("runs_per_scenario"), "sources": [Path(p).name for p in paths],
        "sessions": sum(len(v) for s in scenes.values() for v in s["verdicts"]),
        "threshold": float(max(map(exact, defined))) if defined else 0.0,
        "scenarios": scenes,
    }
    return record, ""


def noise_report(record: JsonObj, title: str) -> str:
    scenes: JsonObj = record["scenarios"]
    lines = [f"# {title}", "",
             f"- runs of one engine: {', '.join(f'`{s}`' for s in record['sources'])} — environment {record['environment']}, "
             f"engine {str(record['engine_commit'])[:7]}, {', '.join(record['claude_version'])}, model {record['model']}, "
             f"{record['runs_per_scenario']} sessions/scenario in each, {record['sessions']} sessions in all", "",
             "| scenario | expected | " + " | ".join(f"run {i + 1}" for i in range(len(record["sources"]))) + " | noise | verdicts |",
             "|---|---|" + "---|" * len(record["sources"]) + "---|---|"]
    for sid, scene in scenes.items():
        noise = scene["noise"]
        kinds = scene["distinct_verdicts"]
        steady = "always " + kinds[0] if len(kinds) == 1 else "vary: " + ", ".join(kinds) if kinds else "no valid session"
        lines.append(f"| `{sid}` | {scene['expected']} | " + " | ".join(scene["matched"])
                     + f" | {'n/a' if noise is None else f'{noise:.2f}'} | {steady} |")
    moved = [sid for sid, scene in scenes.items() if scene["noise"]]
    unsteady = [sid for sid, scene in scenes.items() if len(scene["distinct_verdicts"]) > 1]
    lines += ["",
              f"Noise threshold: **{record['threshold']:.2f}** — the largest spread of the match rate on any scene. "
              f"Scenes whose match rate moved between the runs: {', '.join(f'`{s}`' for s in moved) or 'none'}. "
              f"Scenes whose verdict was not the same in every session: {', '.join(f'`{s}`' for s in unsteady) or 'none'}.",
              "",
              "Noise = largest − smallest match rate among the runs (matched / valid sessions). In a comparison the bound "
              "of a scene is the larger of its own noise and the threshold; a difference that is not larger is "
              f"«{WITHIN_NOISE}».", "", "**Verdicts per session**", ""]
    for sid, scene in scenes.items():
        lines.append(f"- `{sid}`: " + "; ".join(f"run {i + 1} {v}" for i, v in enumerate(scene["verdicts"])))
    return "\n".join(lines) + "\n"


def load_record(path: Path) -> JsonObj:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), dict) or "threshold" not in data:
        raise SystemExit(f"{path}: not a noise record (write one with --measure-noise … --out-record)")
    return data


def compare(before: JsonObj, after: JsonObj, noise_runs: list[JsonObj], must_fix: set[str],
            record: JsonObj | None = None) -> tuple[str, bool, int]:
    b, a = scenarios_of(before), scenarios_of(after)
    tables = [scenarios_of(r) for r in noise_runs]
    ids = sorted(set(b) | set(a))

    noise: dict[str, Fraction | None] = {}
    for sid in ids:
        if record is not None:
            own = (record["scenarios"].get(sid) or {}).get("noise")
            noise[sid] = None if own is None else max(exact(own), exact(record["threshold"]))
        else:
            noise[sid] = spread([rate(t.get(sid)) for t in tables]) if tables else None
    defined = [v for v in noise.values() if v is not None]
    fallback = exact(record["threshold"]) if record is not None else max(defined) if defined else Fraction(0)

    lines: list[str] = []
    lines.append("| scenario | expected | before | after | diff | noise | real? | judgement |")
    lines.append("|---|---|---|---|---|---|---|---|")
    ok = True
    unmeasured = 0
    for sid in ids:
        sb, sa = b.get(sid), a.get(sid)
        rb, ra = rate(sb), rate(sa)
        diff = None if rb is None or ra is None else ra - rb
        threshold = noise[sid]
        threshold_text = f"{float(threshold):.2f}" if threshold is not None else f"n/a → {float(fallback):.2f}"
        bound = threshold if threshold is not None else fallback
        real = diff is not None and abs(diff) > bound
        within = diff is not None and diff != 0 and not real
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
                judgement, met = f"NOT FIXED ({WITHIN_NOISE})" if within else "NOT FIXED", False
            ok = ok and met
        elif sb is None or sa is None:
            # A scenario one file does not have at all (the set grows between releases): nothing
            # was lost and nothing failed, there is only nothing to compare it with.
            judgement = "only after" if sb is None else "only before"
        elif rb is None or ra is None:
            # Both files ran the scenario and one holds no valid session for it: nothing to
            # subtract, and "same" would read as a clean bill for a side that was never measured.
            judgement, ok, unmeasured = NOT_MEASURED, False, unmeasured + 1
        else:
            worse = real and diff is not None and diff < 0
            judgement = "WORSE" if worse else "better" if real else WITHIN_NOISE if within else "same"
            ok = ok and not worse
        lines.append(
            f"| `{sid}` | {expected_of(sb or sa or {})} | {counts(sb)} | {counts(sa)} | {fmt(diff)} | "
            f"{threshold_text} | {'yes' if real else 'no'} | {judgement} |"
        )
    lines.append("")
    lines.append(
        "Match rate = matched / valid sessions (a session with a tooling or usage-limit error is not valid). "
        + ("Noise = the larger of the scene's recorded spread and the record's threshold; for a scene the record does not "
           "have, the threshold. " if record is not None else
           "Noise = |rate(noise run 1) − rate(noise run 2)|; where undefined, the largest defined noise is the bound. ")
        + f"A difference is real only when larger than the noise; one that is not zero and not larger is «{WITHIN_NOISE}». "
        "FIXED = real improvement and at least two of three valid "
        "sessions match after; MET = it already matched at least two of three before and still does. WORSE = real drop. "
        f"{NOT_MEASURED} = both files ran the scenario and one has no valid session for it — a failure of the instrument, "
        "not a difference. only before / only after = the other file does not have the scenario; nothing to compare."
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
                 "(the overseer had nothing false to audit; older result files only)")
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
    return "\n".join(lines), ok, unmeasured


def header(before: JsonObj, after: JsonObj, noise_runs: list[JsonObj], paths: list[str],
           record: JsonObj | None = None, record_path: Path | None = None) -> str:
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
    if record is not None:
        rows.append(f"- noise: the record `{record_path}` — threshold {float(record['threshold']):.2f}, measured on "
                    f"{record.get('environment')}, engine {str(record.get('engine_commit'))[:7]}, "
                    f"{record.get('sessions')} sessions ({', '.join(map(str, record.get('sources', [])))})")
        if environment.recorded_in(before, Path(paths[0])) != record.get("environment"):
            rows.append("- **the noise record is another environment's**: its threshold may not be this one's")
    elif not noise_runs:
        rows.append(f"- noise: NOT MEASURED — no --noise and no record `{NOISE_RECORD_NAME}` beside the before file; "
                    "the bound is 0, so every difference reads as real")
    note = environment.cross_note(environment.recorded_in(before, Path(paths[0])), environment.recorded_in(after, Path(paths[1])), ("before", "after"))
    if note:
        rows += ["", f"**{note}**"]
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--before", type=environment.baseline_path)
    parser.add_argument("--after", type=environment.baseline_path)
    parser.add_argument("--noise", type=environment.baseline_path, nargs="*", default=[], help="two result files of ONE engine")
    parser.add_argument("--noise-record", default="",
                        help=f"the recorded noise to judge by (default: {NOISE_RECORD_NAME} beside the --before file); "
                             f"'{NO_RECORD}' = use no record")
    parser.add_argument("--measure-noise", type=environment.baseline_path, nargs="+", metavar="RUN.json",
                        help="measure the noise instead of comparing: two or more complete result files of ONE engine commit")
    parser.add_argument("--out-record", type=environment.out_path, help="with --measure-noise: write the noise record here")
    parser.add_argument("--must-fix", default="", help="comma-separated scenario ids that must be FIXED")
    parser.add_argument("--out", type=Path, help="write the markdown here as well as printing it")
    parser.add_argument("--title", default="Audit comparison")
    args = parser.parse_args()
    if args.measure_noise:
        if len(args.measure_noise) < 2 or args.before or args.after:
            parser.error("--measure-noise takes two or more result files and no --before/--after")
        made, why = measure_noise([load(p) for p in args.measure_noise], [str(p) for p in args.measure_noise])
        if made is None:
            print(f"no noise measured: {why}", file=sys.stderr)
            return 2
        text = noise_report(made, args.title if args.title != parser.get_default("title") else "Audit noise")
        print(text)
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        if args.out_record:
            args.out_record.write_text(json.dumps(made, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    if not args.before or not args.after:
        parser.error("--before and --after are required (or --measure-noise)")
    if len(args.noise) not in (0, 2):
        parser.error("--noise takes exactly two files (or none)")

    before, after = load(args.before), load(args.after)
    noise_runs = [load(p) for p in args.noise]
    # Fresh noise runs given by hand win over the record; else the record beside the before file.
    record_path = None if noise_runs or args.noise_record == NO_RECORD else (
        environment.baseline_path(args.noise_record) if args.noise_record else args.before.parent / NOISE_RECORD_NAME)
    if record_path is not None and not record_path.is_file():
        if args.noise_record:
            parser.error(f"--noise-record {record_path}: no such file")
        record_path = None
    record = load_record(record_path) if record_path else None
    must_fix = {s for s in args.must_fix.split(",") if s}
    body, ok, unmeasured = compare(before, after, noise_runs, must_fix, record)
    result = ("every must-fix scenario FIXED and nothing WORSE" if ok
              else f"NOT met — {unmeasured} scenario(s) {NOT_MEASURED}: the instrument failed, see the lost sessions below the table"
              if unmeasured else "NOT met — see the table")
    text = (
        f"# {args.title}\n\n"
        + header(before, after, noise_runs, [str(args.before), str(args.after), *map(str, args.noise)], record, record_path)
        + "\n\n"
        + body
        + f"\nResult: {result}\n"
    )
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
