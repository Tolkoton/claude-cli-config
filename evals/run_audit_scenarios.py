#!/usr/bin/env python3
"""Run the audit scenarios in headless Claude Code sessions and record the verdicts.

    python3 evals/run_audit_scenarios.py --engine-ref HEAD --runs 3 \
        --out evals/baseline/<machine>/audit-<ref>.json

WHY THIS EXISTS. The overseer's judgement is a model's, so one run proves little: the
baseline needs every scenario several times, and later comparisons need 10-15 runs per
variant. Done by hand that is dozens of sessions and nobody does it twice. This script
makes it one command. It is the non-deterministic twin of run_hook_scenarios.py.

WHAT ONE RUN DOES
  1. builds a FRESH sandbox (engine from --engine-ref + the audit fixtures): no run sees
     another run's ledger entries, so check #12 (three passes in a row) cannot leak in.
     Then it lays the scenario's WORK over it, uncommitted: the code the scripted turn
     talks about really exists (scenarios/audit/work/, chosen in expected.json). A
     text-only turn cannot pass an honest audit: the overseer opens the repository,
     finds none of the claimed code, and blocks for false-DONE whatever the scenario
     was meant to probe — which is exactly what the first real trial showed;
  2. `claude -p <prompt A>`: the session replies with the scripted developer turn;
  3. `claude -p <prompt B> --resume <session>`: "Run overseer on the last turn.";
  4. reads the verdict from the NEW ENTRY IN THE LEDGER (the overseer must write one),
     falling back to the marker line in the reply. The ledger is the reliable source:
     after an OVERSEER_PASS the Stop hook tells the session to continue, so the final
     reply of a PASS run is often not the verdict any more.

It records; it does not judge. Exit code 0 unless the tooling itself failed. It never
passes --dangerously-skip-permissions and never runs a session inside this repository.

COST. Every run is two real sessions on your account. Start with `--runs 1`.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JsonObj = dict[str, Any]

HERE = Path(__file__).resolve().parent
SCENARIOS = HERE / "scenarios" / "audit"
LEDGER = Path(".claude") / "overseer" / "ledger.md"
MARKER_RE = re.compile(r"OVERSEER_([A-Z_]+)")
CHECK_RE = re.compile(r"#(\d{1,2})\b")
# Why 4: prompt A only asks the session to repeat a text; more turns means it wandered off.
ECHO_MAX_TURNS = 4
# Why 30: an audit reads a handful of state files and writes one ledger entry (about 10
# turns here). The cap mostly bounds what a PASS run spends after the hook says "continue".
AUDIT_MAX_TURNS = 30
CALL_TIMEOUT_S = 1200
ENTRY_CHARS = 900
EXCERPT_CHARS = 700


def fenced_block_after(heading: str, text: str) -> str:
    """The first ``` block that follows a markdown heading containing `heading`."""
    match = re.search(rf"^##[^\n]*{re.escape(heading)}[^\n]*\n(.*?)^```\n(.*?)^```", text,
                      re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"no fenced block under a heading containing {heading!r}")
    return match.group(2).rstrip("\n")


def parse_json_output(stdout: str) -> JsonObj | None:
    """`--output-format json` prints one object; tolerate stray lines around it."""
    start, end = stdout.find("{"), stdout.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def parse_stream(stdout: str) -> JsonObj | None:
    """`--output-format stream-json`: one JSON object per line. Returns the final `result`
    object with every assistant text block of the session joined under `all_text`."""
    texts: list[str] = []
    final: JsonObj | None = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
        elif event.get("type") == "result":
            final = event
    if final is None:
        return None
    return final | {"all_text": "\n\n".join(texts)}


def call_claude(binary: str, prompt: str, cwd: Path, extra: list[str],
                stream: bool = False) -> tuple[JsonObj | None, str]:
    """Run one headless call. Returns (parsed result or None, short error text).

    stream=True keeps EVERY assistant message, not only the last one. The audit call needs
    that: after an OVERSEER_PASS the Stop hook makes the session continue, so the verdict
    message — and anything it had to contain — is no longer the final reply."""
    fmt = ["--output-format", "stream-json", "--verbose"] if stream else ["--output-format", "json"]
    cmd = [binary, "-p", prompt, *fmt, *extra]
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=CALL_TIMEOUT_S)
    except FileNotFoundError:
        return None, f"'{binary}' not found on PATH"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {CALL_TIMEOUT_S} s"
    payload = (parse_stream(proc.stdout) if stream else None) or parse_json_output(proc.stdout)
    if payload is None:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["no output"]
        return None, f"exit {proc.returncode}, unparseable output: {tail[0][:160]}"
    return payload, ""


def new_ledger_entries(before: str, after: str) -> list[str]:
    """Entry blocks ('## ...' header plus its bullet lines) present only in `after`."""
    def blocks(text: str) -> list[str]:
        parts = re.split(r"(?m)^(?=## )", text)
        return [p.strip() for p in parts if p.startswith("## ")]
    seen = set(blocks(before))
    return [b for b in blocks(after) if b not in seen and MARKER_RE.search(b.splitlines()[0])]


def read_verdict(entries: list[str], reply: str) -> JsonObj:
    """Marker and check number: from the newest new ledger entry, else from the reply."""
    source, text = ("ledger", entries[0]) if entries else ("reply", reply)
    marker_match = None
    if source == "ledger":
        marker_match = MARKER_RE.search(text.splitlines()[0])
    else:
        for line in text.splitlines():            # a verdict stands at the start of a line
            if line.lstrip().startswith("OVERSEER_"):
                marker_match = MARKER_RE.search(line)
                text = line
                break
    if not marker_match:
        return {"marker": None, "check": None, "source": "none", "line": ""}
    trigger = next((ln for ln in text.splitlines() if "Trigger" in ln), text)
    check = CHECK_RE.search(trigger) or CHECK_RE.search(text.splitlines()[0])
    return {"marker": marker_match.group(1), "check": int(check.group(1)) if check else None,
            "source": source, "line": text.splitlines()[0][:200]}


def excerpt_around_marker(text: str) -> str:
    """The stretch of the session's own words that ends at its verdict line."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("OVERSEER_"):
            return "\n".join(lines[max(0, index - 12) : index + 1])[-EXCERPT_CHARS:]
    return ""


def cost_of(payload: JsonObj | None) -> float:
    if not payload:
        return 0.0
    value = payload.get("total_cost_usd", payload.get("cost_usd", 0.0))
    return float(value) if isinstance(value, (int, float)) else 0.0


def run_once(args: argparse.Namespace, scenario_id: str, expect: JsonObj, text: str,
             sandbox: Path) -> JsonObj:
    result: JsonObj = {"sandbox": sandbox.name}
    build = subprocess.run(
        ["bash", str(HERE / "make_sandbox.sh"), args.engine_ref, str(sandbox),
         "--audit-fixtures"], capture_output=True, text=True)
    if build.returncode != 0:
        return result | {"error": f"sandbox: {build.stderr.strip()[:200]}"}
    # The scenario's work goes in AFTER the sandbox's initial commit, so it shows up as
    # this turn's uncommitted change — what an overseer looks at first.
    for overlay in expect.get("overlays", []):
        shutil.copytree(SCENARIOS / "work" / overlay, sandbox, dirs_exist_ok=True)
    for gone in expect.get("remove", []):
        (sandbox / gone).unlink(missing_ok=True)
    if expect.get("ledger_fixture"):
        shutil.copyfile(SCENARIOS / expect["ledger_fixture"], sandbox / LEDGER)
    ledger_file = sandbox / LEDGER
    before = ledger_file.read_text(encoding="utf-8") if ledger_file.is_file() else ""

    common: list[str] = []
    if args.setting_sources:
        common += ["--setting-sources", args.setting_sources]
    if args.model:
        common += ["--model", args.model]

    first, err = call_claude(args.claude, fenced_block_after("Prompt A", text), sandbox,
                             ["--max-turns", str(ECHO_MAX_TURNS), *common])
    if not first or not first.get("session_id"):
        return result | {"error": f"prompt A: {err or 'no session_id in the output'}"}
    second, err = call_claude(args.claude, fenced_block_after("Prompt B", text), sandbox,
                              ["--resume", str(first["session_id"]),
                               "--max-turns", str(args.max_turns), *common], stream=True)
    if not second:
        return result | {"error": f"prompt B: {err}"}

    after = ledger_file.read_text(encoding="utf-8") if ledger_file.is_file() else ""
    entries = new_ledger_entries(before, after)
    # Everything the session said during the audit, plus what it wrote into the ledger.
    reply = "\n\n".join([str(second.get("all_text") or second.get("result", "")), *entries])
    verdict = read_verdict(entries, reply)
    matched = verdict["marker"] == expect["marker"]
    if matched and "check" in expect:
        matched = verdict["check"] == expect["check"]
    if matched and "must_contain" in expect:
        matched = expect["must_contain"].lower() in reply.lower()
    return result | {
        "marker": verdict["marker"], "check": verdict["check"], "verdict_source": verdict["source"],
        "verdict_line": verdict["line"], "ledger_entry_written": bool(entries), "matched": matched,
        # Kept so a surprising verdict can be understood without paying for another run.
        "ledger_entry": entries[0][:ENTRY_CHARS] if entries else "",
        "verdict_excerpt": excerpt_around_marker(str(second.get("all_text") or "")),
        "hit_turn_limit": bool(second.get("is_error")) and "max" in str(second.get("subtype", "")),
        "cost_usd": round(cost_of(first) + cost_of(second), 4),
        "duration_ms": int(first.get("duration_ms", 0)) + int(second.get("duration_ms", 0)),
        "audit_turns": second.get("num_turns"),
        "permission_denials": len(second.get("permission_denials") or []),
    }


def shown(run: JsonObj) -> str:
    if "error" in run:
        return "ERROR"
    if not run["marker"]:
        return "none"
    return str(run["marker"]) + (f"#{run['check']}" if run["check"] is not None else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--engine-ref", default="HEAD", help="tag, branch or commit of this repo")
    parser.add_argument("--runs", type=int, default=3, help="sessions per scenario (default 3)")
    parser.add_argument("--only", default="", help="run scenarios whose id contains this")
    parser.add_argument("--out", type=Path, help="write machine-readable results here")
    parser.add_argument("--label", default="")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="passed to --model; default: your settings")
    parser.add_argument("--setting-sources", default="project,local",
                        help="settings layers for the sessions; the default leaves the user "
                             "layer out so the engine is measured alone. '' = Claude Code default")
    parser.add_argument("--max-turns", type=int, default=AUDIT_MAX_TURNS)
    parser.add_argument("--keep", action="store_true", help="keep the sandboxes for inspection")
    args = parser.parse_args()

    expected = json.loads((SCENARIOS / "expected.json").read_text(encoding="utf-8"))
    ids = [i for i in sorted(expected) if args.only in i]
    if not ids:
        print(f"no scenario id contains {args.only!r}", file=sys.stderr)
        return 2
    version = ""
    if shutil.which(args.claude) or Path(args.claude).is_file():
        probe = subprocess.run([args.claude, "--version"], capture_output=True, text=True)
        version = probe.stdout.strip()
    if not version:
        print(f"'{args.claude}' is not runnable — is Claude Code installed and on PATH?",
              file=sys.stderr)
        return 2

    workdir = Path(tempfile.mkdtemp(prefix="engine-audit-"))
    print(f"{len(ids)} scenarios x {args.runs} runs = {len(ids) * args.runs * 2} headless sessions"
          f"  (engine {args.engine_ref}, {version})\nsandboxes: {workdir}\n")
    report_rows: list[JsonObj] = []
    try:
        for scenario_id in ids:
            text = (SCENARIOS / f"{scenario_id}.md").read_text(encoding="utf-8")
            runs = [run_once(args, scenario_id, expected[scenario_id], text,
                             workdir / f"{scenario_id}-run{n + 1}") for n in range(args.runs)]
            hits = sum(1 for r in runs if r.get("matched"))
            want = expected[scenario_id]["marker"] + (
                f"#{expected[scenario_id]['check']}" if "check" in expected[scenario_id] else "")
            print(f"  {scenario_id:40} {' '.join(shown(r) for r in runs):34} {hits}/{len(runs)}"
                  f"   expected {want}")
            for r in runs:
                if "error" in r:
                    print(f"      ! {r['error']}")
            report_rows.append({"id": scenario_id, "expected": expected[scenario_id], "runs": runs,
                                "matched": hits, "verdicts": dict(Counter(shown(r) for r in runs))})
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    all_runs = [r for row in report_rows for r in row["runs"]]
    errors = sum(1 for r in all_runs if "error" in r)
    total_cost = round(sum(r.get("cost_usd", 0.0) for r in all_runs), 2)
    print(f"\nmatched {sum(row['matched'] for row in report_rows)}/{len(all_runs)} runs, "
          f"{errors} tooling errors, reported cost ${total_cost}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "label": args.label, "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engine_ref": args.engine_ref, "claude_version": version,
            "model": args.model or "default",
            "setting_sources": args.setting_sources or "default",
            "runs_per_scenario": args.runs,
            "total_cost_usd": total_cost, "scenarios": report_rows,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return 1 if errors == len(all_runs) else 0


if __name__ == "__main__":
    sys.exit(main())
