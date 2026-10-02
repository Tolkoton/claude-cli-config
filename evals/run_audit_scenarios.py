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

SAVING. With --out, the whole result file is rewritten after EVERY run (to a temporary
file beside it, then moved into place, so a kill during the write leaves the previous
file whole). A crash on the tenth scenario keeps the nine already paid for — package 3c
lost about $25 that way, nine scenarios in memory and nothing on disk. `--resume` continues
such a file: recorded runs are kept, only the missing ones are performed. It refuses a file
recorded against a different engine COMMIT (not the ref string: `HEAD` moves), model,
settings layers or runs-per-scenario, and without `--resume` it refuses to replace an
existing --out at all. `--only` takes a comma-separated list of id fragments.

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
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JsonObj = dict[str, Any]

HERE = Path(__file__).resolve().parent
SCENARIOS = HERE / "scenarios" / "audit"
LEDGER = Path(".engine") / "overseer" / "ledger.md"
MARKER_RE = re.compile(r"OVERSEER_([A-Z_]+)")
# A verdict line as a model actually types it: the marker may sit behind markdown
# decoration (**bold**, a quote mark, a list dash, a heading). The Stop hook itself only
# recognises a bare marker at the start of a line — a decorated one is recorded here AND
# flagged (`marker_decorated`), because the hook would have missed it.
VERDICT_LINE_RE = re.compile(r"^(?P<deco>[ \t>*_`#-]*)OVERSEER_(?P<marker>[A-Z_]+)", re.MULTILINE)
# A ledger header that names the verdict without the OVERSEER_ prefix.
BARE_VERDICT_RE = re.compile(r"\b(ADR_REQUIRED|ESCALATE|BLOCK|PASS)\b")
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
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=CALL_TIMEOUT_S, check=False)
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
    return [b for b in blocks(after) if b not in seen]


def verdict_match(text: str) -> re.Match[str] | None:
    """The verdict line of a session's text: the LAST bare marker, else the last decorated one.

    Last, because the verdict closes the message while earlier lines may list or quote the
    possible verdicts ("- OVERSEER_PASS — when ...") — taking the first match read such a
    reply as PASS although it ended with OVERSEER_BLOCK. Bare before decorated, because a
    bare marker at the start of a line is the only form the Stop hook itself recognises."""
    matches = list(VERDICT_LINE_RE.finditer(text))
    bare = [m for m in matches if not m.group("deco").strip()]
    return (bare or matches)[-1] if matches else None


def read_verdict(entries: list[str], reply: str) -> JsonObj:
    """Marker and check number: from the newest new ledger entry, else from the reply."""
    for entry in entries:
        header = entry.splitlines()[0]
        found = MARKER_RE.search(header) or BARE_VERDICT_RE.search(header)
        if found:
            trigger = next((ln for ln in entry.splitlines() if "Trigger" in ln), header)
            check = CHECK_RE.search(trigger) or CHECK_RE.search(header)
            return {"marker": found.group(1), "check": int(check.group(1)) if check else None,
                    "source": "ledger", "line": header[:200], "decorated": False}
    found = verdict_match(reply)
    if not found:
        return {"marker": None, "check": None, "source": "none", "line": "", "decorated": False}
    end = reply.find("\n", found.start())
    line = reply[found.start() : end if end != -1 else len(reply)]
    check = CHECK_RE.search(line)
    return {"marker": found.group("marker"), "check": int(check.group(1)) if check else None,
            "source": "reply", "line": line.strip()[:200],
            "decorated": bool(found.group("deco").strip())}


def excerpt_around_marker(text: str) -> str:
    """The stretch of the session's own words that ends at its verdict line."""
    found = verdict_match(text)
    if not found:
        return ""
    end = text.find("\n", found.start())
    upto = text[: end if end != -1 else len(text)]
    return "\n".join(upto.splitlines()[-13:])[-EXCERPT_CHARS:]


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
         "--audit-fixtures"], capture_output=True, text=True, check=False)
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
        "marker_decorated": verdict["decorated"],
        # No verdict at all: keep the end of what the session said, to see why.
        "reply_tail": "" if verdict["marker"] else str(second.get("all_text") or
                                                       second.get("result", ""))[-EXCERPT_CHARS:],
        "result_subtype": second.get("subtype"),
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


def preflight_paths(expected: JsonObj, ids: list[str]) -> list[Path]:
    """Every scenario file, overlay directory and fixture the selected scenarios will read."""
    paths: list[Path] = []
    for scenario_id in ids:
        expect = expected[scenario_id]
        paths.append(SCENARIOS / f"{scenario_id}.md")
        paths.extend(SCENARIOS / "work" / overlay for overlay in expect.get("overlays", []))
        if expect.get("ledger_fixture"):
            paths.append(SCENARIOS / str(expect["ledger_fixture"]))
    return paths


def resolve_commit(ref: str) -> str | None:
    """The commit a ref names in this repository — what make_sandbox.sh builds from."""
    proc = subprocess.run(["git", "-C", str(HERE.parent), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                          capture_output=True, text=True, check=False)
    return proc.stdout.strip() or None


def save_results(path: Path, payload: JsonObj) -> None:
    """Write the whole file beside the target, then move it into place: a kill during the
    write leaves the previous file intact, never a truncated one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def resumable(path: Path, engine_commit: str, model: str, setting_sources: str, runs: int) -> tuple[JsonObj | None, str]:
    """The existing result file if this invocation may continue it, else (None, why not).

    Same engine COMMIT, model, settings layers and runs per scenario: a file that mixed two
    of any of these would look like one measurement and be none."""
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return None, f"not readable as JSON ({e})"
    if not isinstance(previous, dict) or not isinstance(previous.get("scenarios"), list):
        return None, "not a result file of this runner"
    if "engine_commit" not in previous:
        return None, "recorded before --resume existed (no engine_commit); start a new file"
    for key, mine in (("engine_commit", engine_commit), ("model", model),
                      ("setting_sources", setting_sources), ("runs_per_scenario", runs)):
        if previous.get(key) != mine:
            return None, f"{key} differs: file {previous.get(key)!r}, this run {mine!r}"
    return previous, ""


def refresh(row: JsonObj) -> None:
    runs = row["runs"]
    row["matched"] = sum(1 for r in runs if r.get("matched"))
    row["verdicts"] = dict(Counter(shown(r) for r in runs))


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--engine-ref", default="HEAD", help="tag, branch or commit of this repo")
    parser.add_argument("--runs", type=int, default=3, help="sessions per scenario (default 3)")
    parser.add_argument("--only", default="", help="run scenarios whose id contains one of these "
                                                   "comma-separated fragments")
    parser.add_argument("--out", type=Path, help="write machine-readable results here, after every run")
    parser.add_argument("--resume", action="store_true",
                        help="continue the file at --out: keep its recorded runs, perform the missing ones")
    parser.add_argument("--label", default="")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="passed to --model; default: your settings")
    parser.add_argument("--setting-sources", default="project,local",
                        help="settings layers for the sessions; the default leaves the user "
                             "layer out so the engine is measured alone. '' = Claude Code default")
    parser.add_argument("--max-turns", type=int, default=AUDIT_MAX_TURNS)
    parser.add_argument("--keep", action="store_true", help="keep the sandboxes for inspection")
    args = parser.parse_args()
    if args.resume and not args.out:
        parser.error("--resume needs --out")

    engine_commit = resolve_commit(args.engine_ref)
    if not engine_commit:
        print(f"engine ref {args.engine_ref!r} does not name a commit of this repository", file=sys.stderr)
        return 2
    model = args.model or "default"
    setting_sources = args.setting_sources or "default"

    expected = json.loads((SCENARIOS / "expected.json").read_text(encoding="utf-8"))
    fragments = [f for f in args.only.split(",") if f] or [""]
    ids = [i for i in sorted(expected) if any(f in i for f in fragments)]
    if not ids:
        print(f"no scenario id contains {args.only!r}", file=sys.stderr)
        return 2
    # Pre-flight: every file a scenario will need must exist BEFORE the first session is paid
    # for. Package 3c's post-move run crashed on a missing ledger fixture at scenario 10, after
    # nine scenarios (about $25) had run and nothing had been written.
    missing = [str(p) for p in preflight_paths(expected, ids) if not p.exists()]
    if missing:
        print("refusing to start: these scenario files are missing —\n  " + "\n  ".join(missing), file=sys.stderr)
        return 2
    version = ""
    if shutil.which(args.claude) or Path(args.claude).is_file():
        probe = subprocess.run([args.claude, "--version"], capture_output=True, text=True, check=False)
        version = probe.stdout.strip()
    if not version:
        print(f"'{args.claude}' is not runnable — is Claude Code installed and on PATH?",
              file=sys.stderr)
        return 2

    previous: JsonObj | None = None
    if args.out and args.out.exists():
        if not args.resume:
            print(f"{args.out} exists — pass --resume to continue it, or choose another --out. "
                  "It is not replaced: its runs were paid for.", file=sys.stderr)
            return 2
        previous, why = resumable(args.out, engine_commit, model, setting_sources, args.runs)
        if previous is None:
            print(f"cannot resume {args.out}: {why}", file=sys.stderr)
            return 2
        if previous.get("claude_version") != version:
            print(f"note: the file was recorded with {previous.get('claude_version')!r}, this is {version!r}")
    elif args.resume:
        print(f"nothing to resume at {args.out} — starting a new file")

    rows: dict[str, JsonObj] = {str(row["id"]): row for row in (previous or {}).get("scenarios", [])}
    for scenario_id in ids:
        rows.setdefault(scenario_id, {"id": scenario_id, "expected": expected[scenario_id],
                                      "runs": [], "matched": 0, "verdicts": {}})
    recorded = sum(len(rows[i]["runs"]) for i in ids)
    to_run = sum(max(0, args.runs - len(rows[i]["runs"])) for i in ids)

    def payload() -> JsonObj:
        pending = [i for i in sorted(rows) if len(rows[i]["runs"]) < args.runs]
        all_runs = [r for i in sorted(rows) for r in rows[i]["runs"]]
        return {
            "label": args.label or str((previous or {}).get("label", "")),
            "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engine_ref": args.engine_ref, "engine_commit": engine_commit, "claude_version": version,
            "model": model, "setting_sources": setting_sources, "runs_per_scenario": args.runs,
            "status": "complete" if not pending else "partial", "pending": pending,
            "total_cost_usd": round(sum(r.get("cost_usd", 0.0) for r in all_runs), 2),
            "scenarios": [rows[i] for i in sorted(rows)],
        }

    workdir = Path(tempfile.mkdtemp(prefix="engine-audit-"))
    print(f"{len(ids)} scenarios x {args.runs} runs = {to_run * 2} headless sessions"
          f"{f' ({recorded} runs already recorded)' if recorded else ''}"
          f"  (engine {args.engine_ref} = {engine_commit[:7]}, {version})\nsandboxes: {workdir}\n")
    try:
        for scenario_id in ids:
            row = rows[scenario_id]
            if len(row["runs"]) >= args.runs:
                print(f"  {scenario_id:40} {' '.join(shown(r) for r in row['runs']):34} recorded, skipped")
                continue
            text = (SCENARIOS / f"{scenario_id}.md").read_text(encoding="utf-8")
            for n in range(len(row["runs"]), args.runs):
                row["runs"].append(run_once(args, scenario_id, expected[scenario_id], text,
                                            workdir / f"{scenario_id}-run{n + 1}"))
                refresh(row)
                if args.out:
                    save_results(args.out, payload())
            runs = row["runs"]
            want = expected[scenario_id]["marker"] + (
                f"#{expected[scenario_id]['check']}" if "check" in expected[scenario_id] else "")
            print(f"  {scenario_id:40} {' '.join(shown(r) for r in runs):34} {row['matched']}/{len(runs)}"
                  f"   expected {want}")
            for r in runs:
                if "error" in r:
                    print(f"      ! {r['error']}")
                elif not r.get("matched"):
                    # Show WHY straight away — understanding a verdict must not cost a re-run.
                    why = r.get("ledger_entry") or r.get("verdict_excerpt") or r.get("reply_tail")
                    for line in str(why or "(the session said nothing)").splitlines()[:9]:
                        print(f"      | {line[:150]}")
    except KeyboardInterrupt:
        if args.out:
            print(f"\ninterrupted — the runs finished so far are in {args.out}; continue with --resume")
        else:
            print("\ninterrupted — nothing was saved (no --out)")
        return 130
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    final = payload()
    all_runs = [r for row in final["scenarios"] for r in row["runs"]]
    errors = sum(1 for r in all_runs if "error" in r)
    print(f"\nmatched {sum(row['matched'] for row in final['scenarios'])}/{len(all_runs)} runs, "
          f"{errors} tooling errors, reported cost ${final['total_cost_usd']}")
    if args.out:
        save_results(args.out, final)
        print(f"results written to {args.out} ({final['status']})")
    return 1 if all_runs and errors == len(all_runs) else 0


if __name__ == "__main__":
    sys.exit(main())
