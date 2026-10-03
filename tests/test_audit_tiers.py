#!/usr/bin/env python3
"""The audit's two tiers and its cost limit (package costs, item 2) — with the `claude` shim.

  * `--tier smoke` is one run of EVERY scenario, `--tier full` three; `--only` still narrows;
    `--runs` that contradicts the tier is refused before anything is paid for;
  * the result file records the tier;
  * `--max-cost` stops BEFORE the run that would pass the limit (exit 4, status partial), runs
    round-robin so the cut-off costs every scenario a run rather than the last ones all of theirs,
    and `--resume` with a higher limit finishes the file;
  * a run dropped on resume (account usage limit) stays counted as spent.

No real session: the shim of tests/test_audit_runner_resume.py (COST_A + COST_B per live run,
COST_B per recorded-turn run). Real sandboxes are built, so this suite is not in the fast set.
Run:   python3 tests/test_audit_tiers.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_audit_runner_resume import COST_A, COST_B, SHIM

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals" / "run_audit_scenarios.py"
EXPECTED = json.loads((ROOT / "evals/scenarios/audit/expected.json").read_text(encoding="utf-8"))
LIVE = COST_A + COST_B
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:600]}")


class Bench:
    def __init__(self) -> None:
        self.work = Path(tempfile.mkdtemp(prefix="audit-tiers-"))
        self.shim = self.work / "claude"
        self.shim.write_text(SHIM, encoding="utf-8")
        self.shim.chmod(0o755)
        self.log = self.work / "calls.log"
        (self.work / "tmp").mkdir()
        self.n = 0

    def out(self) -> Path:
        self.n += 1
        return self.work / f"audit-{self.n}.json"

    def run(self, *args: str, limit_at_b: int = 0) -> subprocess.CompletedProcess[str]:
        self.log.write_text("", encoding="utf-8")
        env = dict(os.environ, SHIM_LOG=str(self.log), SHIM_LIMIT_AT_B=str(limit_at_b), TMPDIR=str(self.work / "tmp"))
        return subprocess.run([sys.executable, str(RUNNER), "--engine-ref", "HEAD", "--claude", str(self.shim), *args],
                              cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=900)

    def sessions(self) -> int:
        return sum(1 for line in self.log.read_text(encoding="utf-8").splitlines() if line.startswith("prompt-b"))


def load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def runs_of(data: dict[str, Any]) -> dict[str, int]:
    return {str(row["id"]): len(row["runs"]) for row in data["scenarios"]}


def main() -> int:
    b = Bench()
    try:
        print("refusals cost nothing:")
        r = b.run("--tier", "smoke", "--runs", "3", "--out", str(b.out()))
        check("--tier smoke with --runs 3 is refused", r.returncode == 2 and "contradicts" in r.stderr, r.stderr[-200:])
        check("...before any session", b.sessions() == 0)
        r = b.run("--tier", "nightly")
        check("an unknown tier is refused", r.returncode == 2 and "invalid choice" in r.stderr, r.stderr[-200:])

        print("--tier smoke: one run, every scenario")
        out = b.out()
        r = b.run("--tier", "smoke", "--out", str(out))
        data = load(out)
        check("exit 0, complete", r.returncode == 0 and data["status"] == "complete", (r.returncode, r.stdout[-300:], r.stderr[-300:]))
        check("every scenario of expected.json ran exactly once",
              runs_of(data) == dict.fromkeys(sorted(EXPECTED), 1), runs_of(data))
        check("the newest scenario is among them", "11-gate-allow-weak-reason" in runs_of(data))
        check("one audit session per scenario", b.sessions() == len(EXPECTED), b.sessions())
        check("the file says which tier it is", data["tier"] == "smoke" and data["runs_per_scenario"] == 1, data.get("tier"))

        print("--tier full: three runs; --only still narrows")
        out = b.out()
        r = b.run("--tier", "full", "--only", "02,10", "--out", str(out))
        data = load(out)
        check("two scenarios, three runs each", runs_of(data) == {"02-false-done-generic": 3, "10-bias-toward-agreement": 3}, runs_of(data))
        check("recorded as full", data["tier"] == "full" and data["runs_per_scenario"] == 3, data.get("tier"))
        out = b.out()
        b.run("--only", "02", "--out", str(out))
        check("a bare invocation is what it always was: three runs", runs_of(load(out)) == {"02-false-done-generic": 3}, runs_of(load(out)))
        out = b.out()
        b.run("--runs", "2", "--only", "02", "--out", str(out))
        check("--runs alone still works for a targeted re-run (tier: custom)",
              runs_of(load(out)) == {"02-false-done-generic": 2} and load(out)["tier"] == "custom", load(out).get("tier"))

        print("--max-cost: stop before the run that would pass it")
        # 01 and 03 are live (LIVE each), 02 is a recorded turn (COST_B). Full tier = 9 runs.
        out = b.out()
        limit = 2 * LIVE + COST_B + LIVE + 0.01   # round 1 (01, 02, 03) and one more live run fit
        r = b.run("--tier", "full", "--only", "01-clean,02-false,03-false", "--max-cost", str(limit), "--out", str(out))
        data = load(out)
        check("exit 4 and the reason is said", r.returncode == 4 and "cost limit" in r.stdout, (r.returncode, r.stdout[-300:]))
        check("the file is partial and names what is pending", data["status"] == "partial" and len(data["pending"]) == 3, data.get("pending"))
        check("round-robin: every scenario got its first run before any got a second",
              sorted(runs_of(data).values()) == [1, 1, 2], runs_of(data))
        spent = sum(run["cost_usd"] for row in data["scenarios"] for run in row["runs"])
        check("the reported cost stayed under the limit", spent <= limit and data["max_cost_usd"] == limit, (spent, limit))
        check("no run was started and thrown away", b.sessions() == 4, b.sessions())
        before = out.read_bytes()
        r = b.run("--tier", "full", "--only", "01-clean,02-false,03-false", "--max-cost", str(limit), "--out", str(out), "--resume")
        check("--resume under the same limit pays for nothing more", r.returncode == 4 and b.sessions() == 0
              and load(out)["scenarios"] == json.loads(before)["scenarios"], (r.returncode, b.sessions()))
        r = b.run("--tier", "full", "--only", "01-clean,02-false,03-false", "--max-cost", "100", "--out", str(out), "--resume")
        data = load(out)
        check("--resume with a higher limit finishes it", r.returncode == 0 and data["status"] == "complete"
              and set(runs_of(data).values()) == {3}, (r.returncode, runs_of(data)))
        check("...performing only the five missing runs", b.sessions() == 5, b.sessions())

        print("a run dropped on resume stays spent")
        out = b.out()
        r = b.run("--tier", "smoke", "--only", "02,04", "--out", str(out), limit_at_b=2)
        check("the usage limit stops the run (exit 3)", r.returncode == 3, r.returncode)
        r = b.run("--tier", "smoke", "--only", "02,04", "--out", str(out), "--resume", "--max-cost", str(2 * COST_B + 0.01))
        data = load(out)
        check("its cost is kept as dropped_cost_usd", data["dropped_cost_usd"] == COST_B, data.get("dropped_cost_usd"))
        check("...and counts against the limit: the redo does not fit", r.returncode == 4 and b.sessions() == 0,
              (r.returncode, b.sessions(), r.stdout[-200:]))
    finally:
        shutil.rmtree(b.work, ignore_errors=True)
    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
