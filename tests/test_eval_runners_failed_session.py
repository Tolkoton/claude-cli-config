#!/usr/bin/env python3
"""A session the API refused is an error of the instrument, not a result (board 725).

Board 014 taught run_audit_scenarios.py this; here the same question is put to the four other
runners that start sessions of Claude — run_analyst_evals.py, run_manager_evals.py,
run_tester_evals.py, run_simplifier_evals.py — on a `claude` SHIM (no real session, no cost) that
answers the way Claude Code does when the login is refused: `is_error`, `api_error_status` 401,
«Failed to authenticate. API Error: 401 Invalid bearer token».

Cases, for each runner:
  * every session is an error row naming the 401, with no score in it; the exit status is not 0;
  * the file says `no-results`, never `complete`, and its summary counts the sessions as errors —
    no «0 of N» that reads as N measured sessions that all did badly;
  * negative: sessions that answered give a file that says `complete` and counts no error;
  * one session answered and one refused: `partial`, one error, and the exit status is still not 0;
  * a run stopped by its ceiling before every planned session is `partial`;
  * in-process: one refused session among scored ones leaves the scored ones' counts as they are.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REFUSED = {"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error", "api_error_status": 401,
           "result": "Failed to authenticate. API Error: 401 Invalid bearer token", "total_cost_usd": 0, "num_turns": 1}
ANSWERED = {"type": "result", "subtype": "success", "is_error": False, "result": "[]", "total_cost_usd": 0.25, "num_turns": 1}
SCORE_KEYS = {"good", "passed", "caught", "outcome", "recall", "precision"}
# runner -> (the arguments of a small run, how many sessions that is)
RUNNERS: dict[str, tuple[list[str], int]] = {
    "run_analyst_evals": (["--scenes", "a"], 2),
    "run_manager_evals": ([], 0),   # the first two scenes: filled in below
    "run_tester_evals": (["--scenes", "boundary", "--arms", "a", "b"], 2),
    "run_simplifier_evals": (["--runs", "2"], 2),
}
PASS = FAIL = 0


def check(name: str, ok: bool, detail: Any = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:600]}")


def load(name: str) -> Any:
    sys.path.insert(0, str(ROOT / "evals"))
    spec = importlib.util.spec_from_file_location(name, ROOT / "evals" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(name: str, work: Path, payload: dict[str, Any], extra: list[str], then: dict[str, Any] | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """One run of a runner on the shim: every session answers `payload`; with `then`, every session after the first answers that."""
    shim, calls = work / "claude", work / "calls"
    calls.unlink(missing_ok=True)
    shim.write_text(f"#!/bin/sh\nfirst=1; [ -e {calls} ] && first=0; echo call >> {calls}\nif [ $first = 1 ]; then cat <<'EOF'\n" + json.dumps(payload)
                    + "\nEOF\nelse cat <<'EOF'\n" + json.dumps(then or payload) + "\nEOF\nfi\n", encoding="utf-8")
    shim.chmod(0o755)
    out = work / f"{name}.json"
    out.unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_UNATTENDED_SESSION"} | {"CLAUDECODE": "1", "BOARD_STATE_DIR": str(work / "books")}
    done = subprocess.run([sys.executable, str(ROOT / "evals" / f"{name}.py"), "--tasks-dir", str(work / "tasks"), "--claude", str(shim),
                           "--out", str(out), *extra], cwd=ROOT, capture_output=True, text=True, env=env, check=False, timeout=600)
    return done, (json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {})


def main() -> int:
    manager = load("run_manager_evals")
    scenes = list(manager.load()["scenes"])[:2]
    RUNNERS["run_manager_evals"] = (["--scenes", *scenes], 2)
    with tempfile.TemporaryDirectory(prefix="engine-failed-session-") as tmp:
        work = Path(tmp)
        (work / "tasks" / "doing").mkdir(parents=True)
        (work / "tasks" / "doing" / "725-x.md").write_text("# 725\n\nАудит потрібен: ні\n", encoding="utf-8")
        for name, (extra, sessions) in RUNNERS.items():
            print(f"{name}: the API refuses the login (401) at every session")
            done, report = run(name, work, REFUSED, extra)
            rows = report.get("runs", [])
            check("the exit status is not 0, and there is no traceback", done.returncode != 0 and "Traceback" not in done.stderr, f"rc={done.returncode} {done.stderr[-400:]}")
            check("every session is an error row that names the 401, with no score in it",
                  len(rows) == sessions and all("401" in str(r.get("error")) and not SCORE_KEYS & set(r) for r in rows), rows)
            check("the file says `no-results`, never `complete`", report.get("status") == "no-results", report.get("status"))
            check("the summary counts them as errors, not as measured sessions", report.get("summary", {}).get("errors") == sessions, report.get("summary"))
            check("the line printed for each names the error", done.stdout.count("the session ended in an error") >= sessions, done.stdout[-400:])

            print(f"{name}: negative — the sessions answered")
            done, report = run(name, work, ANSWERED, extra)
            rows = report.get("runs", [])
            check("no error row, the summary counts no error, the file says `complete`",
                  len(rows) == sessions and not any("error" in r for r in rows) and report.get("summary", {}).get("errors") == 0
                  and report.get("status") == "complete", f"{report.get('status')} {report.get('summary')} {done.stderr[-300:]}")

            print(f"{name}: one session answered, the next was refused")
            done, report = run(name, work, ANSWERED, extra, then=REFUSED)
            rows = report.get("runs", [])
            check("the file says `partial` and counts one error of two sessions",
                  ["error" in r for r in rows] == [False, True] and report.get("status") == "partial" and report.get("summary", {}).get("errors") == 1,
                  f"{report.get('status')} {report.get('summary')}")
            check("the exit status is not 0: a run with a refused session does not end green", done.returncode == 1, f"rc={done.returncode} {done.stderr[-300:]}")

            done, report = run(name, work, ANSWERED, [*extra, "--max-usd", "0.4", "--max-usd-per-run", "0.25"])
            check("a run its ceiling stopped after one session of two is `partial`, exit status not 0",
                  len(report.get("runs", [])) == 1 and report.get("status") == "partial" and "cost limit" in done.stdout and done.returncode == 1,
                  f"rc={done.returncode} {report.get('status')} {done.stdout[-300:]}")

    print("in-process: one refused session among scored ones")
    failed = {"error": "the session ended in an error: Failed to authenticate. API Error: 401 Invalid bearer token", "cost_usd": 0.0}
    analyst = load("run_analyst_evals")
    got = analyst.summary([{"scene": "a", "variant": "after", "good": True, "cost_usd": 0.1}, {"scene": "b", "variant": "after"} | failed])
    check("analyst: «after» is 1 good of 1 measured, 1 error — not 1 of 2",
          (got["after_good"], got["after_total"], got["errors"], got["table"]["b/after"]) == (1, 1, 1, "error"), got)
    tester = load("run_tester_evals")
    got = tester.summary([{"scene": "boundary", "arm": "a", "outcome": "caught", "caught": True, "cost_usd": 0.1},
                          {"scene": "boundary", "arm": "a"} | failed, {"scene": "boundary", "arm": "b"} | failed])
    check("tester: arm a caught «1 of 1», arm b «0 of 0», 2 errors — a refused session is in no denominator",
          (got["caught"], got["errors"], got["runs"]) == ({"a": "1 of 1", "b": "0 of 0"}, 2, 3), got)
    got = tester.summary([{"scene": "split", "arm": "a", "outcome": "caught", "caught": True, "test_count": 3, "trap_calls": 1, "cost_usd": 0.1},
                          {"scene": "split", "arm": "a"} | failed])
    check("tester, the property set: caught and reached-the-trap are «1 of 1»",
          (got["caught"]["a"], got["by_arm"]["a"]["reached_the_trap"], got["errors"]) == ("1 of 1", "1 of 1", 1), got)
    shared = analyst.shared
    check("the status: complete only with every planned session there and scored",
          [shared.status([{"x": 1}], 1), shared.status([{"x": 1}], 2), shared.status([{"x": 1}, failed], 2), shared.status([failed], 1), shared.status([], 2)]
          == ["complete", "partial", "partial", "no-results", "no-results"])
    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
