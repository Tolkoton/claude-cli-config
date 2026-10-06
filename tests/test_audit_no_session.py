#!/usr/bin/env python3
"""An audit that measured nothing is an instrument failure, not twelve wrong verdicts (board 014).

The operator's pre-release full audit of 2026-10-06 (audit-v0.12.0-release.json) ran 36 sessions
that each died in two seconds on «Failed to authenticate. API Error: 401 Invalid bearer token».
The runner recorded 36 runs with the verdict 'none', no error, $0.0 and `status: complete`;
compare_audits.py read that as twelve scenarios WORSE, and the board got a task about a
regression in verdict recording that did not exist.

Cases, on the `claude` shim of tests/test_audit_runner_resume.py (no real session, no cost):
  * the runner: a session the API refused is an ERROR, not a run with the verdict 'none'; the
    runner stops (the next sessions would answer the same), the file is `partial`, and
    `--resume` performs the lost run again;
  * the runner: sessions that ran and paid but left no verdict anywhere end in the status
    `no-verdicts`, exit 1 — never `complete`; one verdict among them and it is `complete`;
  * compare_audits.py on the real recording: no scenario is WORSE, each is NOT MEASURED, the
    result says the instrument failed, the exit status is 1;
  * compare_audits.py on a file with no verdict and no error at all: the same;
  * negative: one session without a verdict among sessions that have one is still a 'none'
    verdict and a real drop is still WORSE.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_audit_runner_resume import COST_FAILED, IDS, Harness  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "evals" / "baseline" / "linux-ubuntu-22.04"
GOOD, EMPTY = BASELINE / "audit-task-041.json", BASELINE / "audit-v0.12.0-release.json"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:600]}")


def compare(before: Path, after: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ROOT / "evals" / "compare_audits.py"), "--before", str(before),
                           "--after", str(after)], cwd=ROOT, capture_output=True, text=True, check=False)


def judgements(stdout: str) -> list[str]:
    return [line.split("|")[-2].strip() for line in stdout.splitlines() if line.startswith("| `")]


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="audit-no-session-"))
    try:
        h = Harness(work)
        print("the runner: the API refuses the login at the first session:")
        os.environ["SHIM_AUTH_AT_B"] = "1"
        r = h.run()
        del os.environ["SHIM_AUTH_AT_B"]
        check("the runner stops with exit 3 and names the 401", r.returncode == 3 and "401" in r.stdout and "--resume" in r.stdout,
              f"rc={r.returncode} {r.stdout[-400:]} {r.stderr[-200:]}")
        check("it ran no further session (1, not 3)", h.calls("prompt-b") == 1, h.log.read_text())
        res: dict[str, Any] = h.results()
        lost = res["scenarios"][0]["runs"]
        check("the run is an error, not a run with the verdict 'none'",
              len(lost) == 1 and str(lost[0].get("error", "")).startswith("session failed") and "marker" not in lost[0], str(lost))
        check("the file is partial, never complete", res["status"] == "partial" and res["pending"] == IDS, f"{res['status']} {res['pending']}")
        check("the scenario's verdicts read ERROR", res["scenarios"][0]["verdicts"] == {"ERROR": 1}, str(res["scenarios"][0]["verdicts"]))
        r = h.run("--resume")
        res = h.results()
        check("--resume performs the lost run again and the rest (3 sessions)", r.returncode == 0 and h.calls("prompt-b") == 3, f"rc={r.returncode} {h.log.read_text()}")
        check("and the file is complete with three verdicts",
              res["status"] == "complete" and [run.get("marker") for row in res["scenarios"] for run in row["runs"]] == ["PASS"] * 3, str(res["status"]))

        print("the runner: an API error that is not a refused login (529) at the second session:")
        h.out.unlink()
        os.environ.update(SHIM_AUTH_AT_B="2", SHIM_API_STATUS="529")
        r = h.run()
        res = h.results()
        rows = {row["id"]: row["runs"] for row in res["scenarios"]}
        check("the runner goes on: three sessions, exit 0", r.returncode == 0 and h.calls("prompt-b") == 3, f"rc={r.returncode} {r.stdout[-300:]}")
        check("the failed session is an error, its scenario pending, the file partial",
              str(rows[IDS[1]][0].get("error", "")).startswith("session failed") and res["pending"] == [IDS[1]] and res["status"] == "partial",
              f"{rows[IDS[1]]} {res['pending']} {res['status']}")
        check("the other two hold their verdicts", [rows[i][0].get("marker") for i in (IDS[0], IDS[2])] == ["PASS", "PASS"], str(rows))
        check("no login advice on an error that is not a login's", "login" not in rows[IDS[1]][0]["error"], rows[IDS[1]][0]["error"])
        del os.environ["SHIM_AUTH_AT_B"], os.environ["SHIM_API_STATUS"]
        r = h.run("--resume")
        res = h.results()
        check("--resume performs that one run again; what the lost one spent stays counted",
              h.calls("prompt-b") == 1 and res["status"] == "complete" and res["dropped_cost_usd"] == COST_FAILED,
              f"{h.calls('prompt-b')} {res['status']} {res['dropped_cost_usd']}")

        print("the runner: the API error came after the overseer's entry was in the ledger:")
        h.out.unlink()
        os.environ.update(SHIM_AUTH_AT_B="1", SHIM_API_STATUS="529", SHIM_LEDGER_FIRST="1")
        r = h.run()
        first = h.results()["scenarios"][0]["runs"][0]
        check("the verdict stands: a run read from the ledger, not a lost session",
              "error" not in first and first.get("marker") == "PASS" and first.get("verdict_source") == "ledger", str(first)[:300])
        del os.environ["SHIM_AUTH_AT_B"], os.environ["SHIM_API_STATUS"], os.environ["SHIM_LEDGER_FIRST"]

        print("negative — a session cut at --max-turns worked, and is a run:")
        h.out.unlink()
        os.environ["SHIM_MAX_TURNS_AT_B"] = "1"
        r = h.run()
        del os.environ["SHIM_MAX_TURNS_AT_B"]
        res = h.results()
        first = res["scenarios"][0]["runs"][0]
        check("it is recorded with its verdict and the turn-limit flag, not as «session failed»",
              "error" not in first and first.get("marker") == "PASS" and first.get("hit_turn_limit") is True, str(first)[:300])
        check("and the file is complete", r.returncode == 0 and res["status"] == "complete" and res["pending"] == [], f"rc={r.returncode} {res['status']}")

        print("the runner: every session ran and none left a verdict:")
        h.out.unlink()
        os.environ["SHIM_NO_VERDICT"] = "1"
        r = h.run()
        del os.environ["SHIM_NO_VERDICT"]
        res = h.results()
        check("the status is no-verdicts, not complete", res["status"] == "no-verdicts", str(res["status"]))
        check("exit 1 and the reason in words", r.returncode == 1 and "no session left a verdict" in r.stdout, f"rc={r.returncode} {r.stdout[-300:]}")
        check("the cost of the sessions is still recorded", res["total_cost_usd"] > 0, str(res["total_cost_usd"]))

        print("compare_audits.py: the recording of 2026-10-06 against the last good audit:")
        if GOOD.is_file() and EMPTY.is_file():
            r = compare(GOOD, EMPTY)
            marks = judgements(r.stdout)
            check("no scenario is WORSE", "WORSE" not in marks, str(marks))
            check("each of the twelve is NOT MEASURED", marks == ["NOT MEASURED"] * 12, str(marks))
            check("the sessions are listed with what they answered", r.stdout.count("Failed to authenticate") >= 36, r.stdout[-500:])
            check("the result names an instrument failure and the exit status is 1",
                  r.returncode == 1 and "instrument failed" in r.stdout.split("Result:")[-1], r.stdout[-300:])
        else:
            check("the two recordings are in evals/baseline", False, f"{GOOD} {EMPTY}")

        print("compare_audits.py: no verdict and no error anywhere in the file:")
        good = json.loads(GOOD.read_text(encoding="utf-8"))
        blank = copy.deepcopy(good)
        for row in blank["scenarios"]:
            for run in row["runs"]:
                run.update(marker=None, check=None, matched=False, verdict_source="none", reply_tail="Done.")
        (work / "blank.json").write_text(json.dumps(blank), encoding="utf-8")
        r = compare(GOOD, work / "blank.json")
        check("NOT MEASURED everywhere, nothing WORSE, exit 1",
              r.returncode == 1 and judgements(r.stdout) == ["NOT MEASURED"] * 12, str(judgements(r.stdout)))

        print("negative — a real 'none' among real verdicts is still a verdict:")
        one = copy.deepcopy(good)
        first = one["scenarios"][0]
        for run in first["runs"]:
            run.update(marker=None, check=None, matched=False, verdict_source="none", reply_tail="Done.")
        (work / "one.json").write_text(json.dumps(one), encoding="utf-8")
        r = compare(GOOD, work / "one.json")
        marks = judgements(r.stdout)
        check("that scenario is WORSE, the other eleven are the same",
              r.returncode == 1 and marks[0] == "WORSE" and marks[1:] == ["same"] * 11, str(marks))
        print("compare_audits.py: some sessions refused among sessions with verdicts (a file from before the fix):")
        mixed = copy.deepcopy(good)
        for run in mixed["scenarios"][0]["runs"]:
            run.update(marker=None, check=None, matched=False, verdict_source="none",
                       reply_tail="Failed to authenticate. API Error: 401 Invalid bearer token")
        (work / "mixed.json").write_text(json.dumps(mixed), encoding="utf-8")
        r = compare(GOOD, work / "mixed.json")
        marks = judgements(r.stdout)
        check("that scenario is NOT MEASURED, not WORSE; its sessions are listed as failed",
              r.returncode == 1 and marks[0] == "NOT MEASURED" and marks[1:] == ["same"] * 11 and r.stdout.count("session failed") == 3, str(marks))

        print("negative — a scenario only one file has is not a failure of the instrument:")
        fewer = copy.deepcopy(good)
        fewer["scenarios"] = fewer["scenarios"][:-1]
        (work / "fewer.json").write_text(json.dumps(fewer), encoding="utf-8")
        r = compare(work / "fewer.json", GOOD)
        check("a scenario added since: «only after», exit 0, no word of a failed instrument",
              r.returncode == 0 and judgements(r.stdout) == ["same"] * 11 + ["only after"] and "instrument failed" not in r.stdout.split("Result:")[-1], r.stdout[-300:])
        r = compare(GOOD, work / "fewer.json")
        check("a scenario dropped since: «only before», exit 0",
              r.returncode == 0 and judgements(r.stdout) == ["same"] * 11 + ["only before"], str(judgements(r.stdout)))
        r = compare(GOOD, GOOD)
        check("and a file against itself is all 'same', exit 0", r.returncode == 0 and judgements(r.stdout) == ["same"] * 12, r.stdout[-300:])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
