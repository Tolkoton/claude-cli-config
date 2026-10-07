#!/usr/bin/env python3
"""Measure the simplifier agent on a project with planted excess and with traps.

    python3 evals/run_simplifier_evals.py --runs 3 [--out FILE] [--max-usd 15]     # PAID: real sessions
    python3 evals/run_simplifier_evals.py --score ANSWER.json                      # free: score a saved answer
    python3 evals/run_simplifier_evals.py --sandbox DIR                            # free: build the project, print the request
    python3 evals/run_simplifier_evals.py --rescore RESULTS.json                   # free: count recorded answers again
    … --set hard | --set traps                                                     # another set, with any of the four

The project is evals/reference-project with evals/scenarios/simplifier/project/ laid over it:
six kinds of planted excess (an abstraction with one implementation, dead code, an unused
dependency, a guard against an impossible state, a slice "for the future", an invented
requirement) and four traps — things that look unneeded and are not (input validation at the
edge, error handling at the edge, a security check, a contract field only a rare path reads).
evals/scenarios/simplifier/expected.json names each.

`--set hard` takes evals/scenarios/simplifier-hard/ instead (board 059): the excess is subtler —
an abstraction whose second implementation only a test builds, a branch behind a flag nobody
sets, a duplicate written differently, a dependency only a test imports, a guard another function
already keeps, a requirement and a slice that cite a goal which does not ask for them — and
there are ten traps, each a neighbour of something planted (a rare error at the boundary, two
security checks, a field another service reads, an old data format, a requirement and a slice
that look like the planted ones and are needed).

`--set traps` takes evals/scenarios/simplifier-traps/ (board 729): the harder project with six
more traps laid over it, of kinds the agent's definition does not list under «Is it a trap?» — an
idempotency key, a retry with a pause, a file lock, a kill switch nothing in the repository sets,
a write order kept for recovery after a crash, a rounding the law asks for. It answers one
question: does the simplifier leave alone what nobody told it to leave alone.

One run = one fresh headless session of the `simplifier` agent (its own definition, its own
model, Read / Grep / Glob only) with the request `simplifier.py request` prints. The answer goes
through `simplifier.py`'s validator, as in real use, and is scored:

    recall         planted items found / planted items
    precision      findings that name a planted item (or excess the reference project had before
                   the overlay, `also_true`) / all valid findings
    traps touched  findings that name a trap, whatever action they propose — must be 0

Where a planted item and a trap share a file, `lines` in expected.json says which lines are whose.
A finding on a trap's own line is that trap touched, whatever else it names. Any other finding
that names both a planted item and a trap — by line or by word — is `ambiguous`: «R7 can go, R6
stays» and «R6 and R7 can both go» look the same to a scorer by words. It is counted in neither
recall, precision nor traps, shown in the row and the summary, and the run exits 1. A person reads
it and writes the reading into the results file — "read_by_hand": {"<finding id>": {"as":
"planted" | "trap", "why": "…"}} — and `--rescore` counts it so, keeping the reading in the row.
KNOWN LIMIT: a finding that drops a trap without any of the trap's words and away from its lines
(«this and the requirement above can go») is seen by nobody but a reader; every recorded finding
is in the file under `answer` for that reason.

A finding that names a `neutral` entry — something a careful reviewer may report or leave — is
counted neither way. The summary of several runs shows the spread: the lowest and the highest
recall and precision, and in how many runs each planted item was found and each trap touched.

Nothing is tuned to the result: a touched trap is reported as it is.

PAID RUNS. Sessions start only when the task in tasks/doing/ has the owner's «Платні прогони: так»
line, or the owner runs this by hand with --owner-approved (which does not count inside a Claude
Code session). No dollar number is required: the runner's BOARD_MAX_USD guards a loop. A number in
that line, or --max-usd, is a ceiling: the runs stop before it is passed.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # a suite may load this file by path
import environment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURE = HERE / "scenarios" / "simplifier"
SETS = {"basic": FIXTURE, "hard": HERE / "scenarios" / "simplifier-hard", "traps": HERE / "scenarios" / "simplifier-traps"}
LENSES = ("code", "requirements", "architecture")
RUN_TIMEOUT_S = 1200
SANDBOX_ENV = 'SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\nCOMPLEXITY_GATE="warn"\n'

TARGET_LINES = re.compile(r"^[^:]+:(\d+)(?:-(\d+))?(?=$|:)")   # path:line, path:first-last, path:line:column

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


def board_module() -> Any:
    """.claude/unattended/board.py — the board's one reader: it decides what the owner's
    «Платні прогони:» line says, for this session's own task in doing/ only."""
    spec = importlib.util.spec_from_file_location("engine_board", ROOT / ".claude" / "unattended" / "board.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load .claude/unattended/board.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["engine_board"] = module
    spec.loader.exec_module(module)
    return module


def paid_run_refusal(tasks_dir: Path, owner_approved: bool, in_session: bool) -> str | None:
    """Why paid sessions may not start, or None (tasks/README.md, «Платні прогони»)."""
    unread = board_module().line_unread(tasks_dir.resolve())
    if unread is not None:
        return f"refusing to start paid sessions: {unread}."
    if owner_approved and not in_session:
        return None
    reason = board_module().paid_refusal(tasks_dir.resolve())
    if reason is None:
        return None
    flag = " --owner-approved does not count inside a Claude Code session." if owner_approved else ""
    return (f"refusing to start paid sessions: {reason}.{flag} The owner writes «Платні прогони: так» in the task — "
            "no dollar number is needed — or runs this by hand with --owner-approved.")


def dollar_limit(tasks_dir: Path, asked: float | None) -> float | None:
    """The ceiling of this run: the smaller of --max-usd and the number in the task's line, when
    either is there; None is no ceiling — the owner's «так» is the consent, not a budget."""
    given = [limit for limit in (asked, board_module().paid_ceiling(tasks_dir.resolve())) if limit is not None]
    return min(given) if given else None


def over_limit(spent: float, next_cost: float, limit: float | None) -> str | None:
    """The line to print instead of starting a session that could pass the ceiling, or None."""
    if limit is None or spent + next_cost <= limit:
        return None
    return f"cost limit: ${spent:.2f} spent, a run may cost ${next_cost:.2f}, the limit is ${limit:.2f} — stopping"


def build_sandbox(target: Path, fixture: Path = FIXTURE) -> Path:
    """The reference project, the overlay on top (first the set its expected.json names in `over`,
    when it names one), the agent's definition, one commit."""
    reference = HERE / "reference-project"
    tracked = subprocess.run(["git", "-C", str(reference), "ls-files", "."], capture_output=True, text=True, check=True)
    for rel in tracked.stdout.splitlines():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reference / rel, target / rel)
    under = json.loads((fixture / "expected.json").read_text(encoding="utf-8")).get("over")
    for layer in ([fixture.parent / under] if under else []) + [fixture]:
        shutil.copytree(layer / "project", target, dirs_exist_ok=True)
    (target / "uv.lock").unlink(missing_ok=True)   # the lock of the project before the overlay
    manifest = target / "pyproject.toml"           # the engine's own gate note is not the project's
    manifest.write_text("".join(line for line in manifest.read_text(encoding="utf-8").splitlines(keepends=True)
                                if "gate-allow:" not in line), encoding="utf-8")
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


def on_line(finding: JsonObj, entry: JsonObj) -> bool:
    """The finding's target names a line inside one of the entry's `lines` for that file."""
    path = finding["target"].split("::")[0].split(":")[0]
    aimed = TARGET_LINES.search(finding["target"])
    if not aimed:
        return False
    first, last = int(aimed[1]), int(aimed[2] or aimed[1])
    return any(first <= end and start <= last for start, end in entry.get("lines", {}).get(path, []))


def matches(finding: JsonObj, entry: JsonObj, pointed: bool = False) -> bool:
    """By the words; but when the finding points at a line some entry owns (`pointed`), an entry
    that names its lines in that file matches by the line only — twins in one file are told apart
    by where the finding points."""
    path = finding["target"].split("::")[0].split(":")[0]
    if pointed and path in entry.get("lines", {}):
        return on_line(finding, entry)
    text = " ".join([finding["target"], finding["claim"], *(str(e.get("detail", "")) for e in finding["evidence"])]).lower()
    return path in entry["files"] and any(word.lower() in text for word in entry["any"])


def score(findings: list[JsonObj], expected: JsonObj, by_hand: JsonObj | None = None) -> JsonObj:
    """Each finding is counted once: a planted item first (of several it names, the one of its
    own category), then a trap, then a neutral entry (left out of precision), else unexpected.
    A finding on a trap's own line is that trap touched. Any other finding that names a planted
    item AND a trap — by its line or by its words — is `ambiguous`: it may be the planted item
    found («R7 can go, R6 stays») or the trap touched («R6 and R7 can both go»), and words cannot
    tell. It is in no figure until a person has read it: `by_hand` maps a finding's id to
    {"as": "planted" | "trap", "why": …}, and what was decided so stays in the row as `resolved`."""
    by_hand = by_hand or {}
    resolved: list[JsonObj] = []
    found: dict[str, list[str]] = {}
    touched: list[JsonObj] = []
    neutral: list[JsonObj] = []
    ambiguous: list[JsonObj] = []
    unexpected: list[JsonObj] = []
    also_true = 0
    for finding in findings:
        brief = {"target": finding["target"], "category": finding["category"], "action": finding["proposed_action"],
                 "claim": finding["claim"]}
        pointed = any(on_line(finding, e) for kind in ("planted", "traps", "neutral") for e in expected.get(kind, []))
        named = [e for e in expected["planted"] if matches(finding, e, pointed)]
        own = [e for e in named if e.get("category") == finding["category"]]
        planted = (own or named)[0]["id"] if named else None
        trap = next((e["id"] for e in expected["traps"] if matches(finding, e, pointed)), None)
        if not trap:   # on a line that is not the trap's, a trap may still be named in words
            trap = next((e["id"] for e in expected["traps"] if matches(finding, e)), None)
        read = by_hand.get(str(finding.get("id"))) if planted and trap else None
        if read:
            resolved.append({"id": finding["id"], "planted": planted, "trap": trap, **read, **brief})
            planted, trap = (planted, None) if read["as"] == "planted" else (None, trap)
        if planted and trap:
            ambiguous.append({"id": finding.get("id"), "planted": planted, "trap": trap, **brief})
        elif planted:
            found.setdefault(planted, []).append(finding["proposed_action"])
        elif any(matches(finding, e) for e in expected.get("also_true", [])):
            also_true += 1
        elif trap:
            touched.append({"trap": trap, **brief})
        elif any(matches(finding, e, pointed) for e in expected.get("neutral", [])):
            neutral.append(brief)
        else:
            unexpected.append(brief)
    total = len(expected["planted"])
    on_target = sum(len(actions) for actions in found.values()) + also_true
    judged = len(findings) - len(neutral) - len(ambiguous)
    return {
        "recall": round(len(found) / total, 3),
        "precision": round(on_target / judged, 3) if judged else None,
        "traps_touched": len(touched),
        "found": found,
        "missed": [e["id"] for e in expected["planted"] if e["id"] not in found],
        "touched": touched,
        "unexpected": unexpected,
        "neutral": neutral,
        "ambiguous": ambiguous,
        "resolved": resolved,
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
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
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
        "rejected": [{"errors": r["errors"], "finding": r["finding"]} for r in result["rejected"]],
        "lowered": sum(bool(f["validator"]) for f in result["findings"]),
        "answer": result["findings"],
    }


def rescore(path: Path) -> int:
    """Count the recorded answers of a results file again by the present expected.json."""
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("set") not in SETS:
        print(f"{path}: the file does not say which set it was run on (\"set\": {' or '.join(sorted(SETS))}) — not rescored", file=sys.stderr)
        return 2
    by_hand = report.get("read_by_hand", {})
    if any(read.get("as") not in ("planted", "trap") or not read.get("why") for read in by_hand.values()):
        print(f"{path}: every entry of read_by_hand needs \"as\": \"planted\" or \"trap\" and a \"why\" — not rescored", file=sys.stderr)
        return 2
    expected = json.loads((SETS[report["set"]] / "expected.json").read_text(encoding="utf-8"))
    for row in report["runs"]:
        if "error" not in row:
            row.update(score(row["answer"], expected, by_hand))
    report["summary"] = summary(report["runs"])
    report["rescored_utc"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return exit_code(report["summary"])


def exit_code(result: JsonObj) -> int:
    """0 only for a run that was scored, touched no trap and left nothing to read by hand."""
    return 0 if result["scored"] and result["traps_touched_total"] == 0 and result["ambiguous_total"] == 0 else 1


def tally(names: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def summary(runs: list[JsonObj]) -> JsonObj:
    good = [r for r in runs if "error" not in r]
    recalls = [r["recall"] for r in good]
    precisions = [r["precision"] for r in good if r["precision"] is not None]
    return {
        "runs": len(runs), "scored": len(good),
        "recall_mean": round(sum(recalls) / len(good), 3) if good else None,
        "recall_range": [min(recalls), max(recalls)] if good else None,
        "precision_mean": round(sum(precisions) / len(precisions), 3) if precisions else None,
        "precision_range": [min(precisions), max(precisions)] if precisions else None,
        "traps_touched_total": sum(r["traps_touched"] for r in good),
        "ambiguous_total": sum(len(r["ambiguous"]) for r in good),
        "read_by_hand_total": sum(len(r["resolved"]) for r in good),
        "found_in_runs": tally(name for r in good for name in r["found"]),
        "touched_in_runs": tally(name for r in good for name in {t["trap"] for t in r["touched"]}),
        "cost_usd": round(sum(r["cost_usd"] for r in runs), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--set", choices=sorted(SETS), default="basic", help="which project: basic (board 010), hard (board 059) or traps (board 729)")
    parser.add_argument("--out", type=environment.out_path, help="a baseline goes to evals/baseline/@env/")
    parser.add_argument("--score", type=Path, help="score a saved answer (a JSON list of findings) and stop; free")
    parser.add_argument("--rescore", type=Path, help="count a results file's recorded answers again by the present expected.json; free")
    parser.add_argument("--sandbox", type=Path, help="build the project here, print the request and stop; free")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the model of the agent's definition")
    parser.add_argument("--max-usd", type=float, default=None, help="a ceiling: stop before the runs together cost more (default: none)")
    parser.add_argument("--max-usd-per-run", type=float, default=5.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()
    if args.rescore:
        return rescore(args.rescore)
    fixture = SETS[args.set]
    expected = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
    simplifier = simplifier_module()

    if args.sandbox:
        args.sandbox.mkdir(parents=True)
        print(request_text(build_sandbox(args.sandbox, fixture), expected["scope"]))
        return 0
    with tempfile.TemporaryDirectory(prefix="engine-simplifier-eval-") as tmp:
        sandbox = build_sandbox(Path(tmp) / "project", fixture)
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
        limit = dollar_limit(args.tasks_dir, args.max_usd)
        runs: list[JsonObj] = []
        for number in range(1, args.runs + 1):
            stop = over_limit(sum(r["cost_usd"] for r in runs), args.max_usd_per_run, limit)
            if stop:
                print(stop)
                break
            row = run_once(sandbox, request, args, simplifier, expected)
            runs.append(row)
            shown = row.get("error") or (f"recall {row['recall']}, precision {row['precision']}, traps touched {row['traps_touched']}, "
                                         f"missed {row['missed']}, {len(row['unexpected'])} unexpected, {len(row['ambiguous'])} ambiguous")
            print(f"run {number}: {shown}  (${row['cost_usd']:.2f}, {', '.join(row.get('models', []))})")
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "set": args.set, "model": args.model or "the agent's own",
        "planted": [e["id"] for e in expected["planted"]], "traps": [e["id"] for e in expected["traps"]],
        "summary": summary(runs), "runs": runs,
    }
    print("\n" + json.dumps(report["summary"], indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return exit_code(report["summary"])


if __name__ == "__main__":
    sys.exit(main())
