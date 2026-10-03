#!/usr/bin/env python3
"""run_audit_scenarios.py keeps what it has paid for.

Package 3c's post-move audit crashed on the tenth scenario; nine scenarios (about $25) had
run and nothing was on disk, because the result file was written once, at the end. Now the
file is rewritten after every run and `--resume` continues it. This suite proves that with
a `claude` SHIM — no real session, no cost: a script that answers `--version`, prompt A
(json with a session_id) and prompt B (stream-json with an OVERSEER_PASS line and a cost),
logs every call, and on request kills its parent — the runner — with SIGKILL at the prompt-A
call of a given run. That is a crash in the middle of the paid work, not a tidy exception.

Cases:
  * killed at run 3 of 3 (one run per scenario, three scenarios): the file exists, is valid
    JSON, says `partial`, holds exactly the two finished runs with their cost and names the
    third as pending; the engine COMMIT is recorded, not just the ref string;
  * `--resume`: the shim is called only for the missing run (call log), the file is
    `complete`, the cost is the sum of three, nothing recorded earlier changed;
  * `--resume` again: nothing to do, no session call, exit 0;
  * an existing --out without `--resume` is refused and left byte for byte;
  * `--resume` against another engine commit, or another --runs, is refused, file untouched;
  * `--only` takes a comma-separated list.

Real sandboxes are built (make_sandbox.sh, about 1.5 s each); the engine ref is HEAD.
The SHIM and the Harness are imported by tests/test_audit_turn_fixture.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals" / "run_audit_scenarios.py"
# Three LIVE scenarios (prompt A + prompt B), by fragment. 02, 04 and 10 are recorded-turn
# scenarios since night program 1 (one session, no echo) and have their own suite,
# tests/test_audit_turn_fixture.py; this one is about the crash-and-resume bookkeeping.
ONLY = "01-clean,03-false,05-masked"
IDS = ["01-clean-pass", "03-false-done-partial-exit-criterion", "05-masked-test-gap"]
COST_A, COST_B = 0.5, 0.75

SHIM = r'''#!/usr/bin/env python3
"""A stand-in for `claude`: answers like the real CLI's --output-format json / stream-json,
logs every call, and kills its parent at the prompt-A call number given in SHIM_KILL_AT_A."""
import json, os, signal, sys
argv = sys.argv[1:]
log = os.environ["SHIM_LOG"]
def record(kind):
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(kind + "\t" + os.getcwd() + "\n")
if argv == ["--version"]:
    record("version"); print("claude-shim 0.0.1"); sys.exit(0)
prompt = argv[argv.index("-p") + 1]
stream = "stream-json" in argv
if not stream:  # prompt A
    with open(log, encoding="utf-8") as fh:
        a_calls = sum(1 for line in fh if line.startswith("prompt-a"))
    record("prompt-a")
    kill_at = int(os.environ.get("SHIM_KILL_AT_A", "0"))
    if kill_at and a_calls + 1 == kill_at:
        record("kill"); os.kill(os.getppid(), signal.SIGKILL); sys.exit(1)
    refuse_at = int(os.environ.get("SHIM_REFUSE_AT_A", "0"))
    if refuse_at and a_calls + 1 == refuse_at:
        echoed = "I can't send that text as written: I haven't run the tests in this session."
    else:
        import re as _re
        block = _re.search(r"-----BEGIN-----\n(.*?)\n-----END-----", prompt, _re.S)
        echoed = block.group(1) if block else "echoed"
    print(json.dumps({"type": "result", "subtype": "success", "session_id": "shim-%d" % (a_calls + 1),
                      "result": echoed, "total_cost_usd": @COST_A@, "duration_ms": 10, "num_turns": 1}))
    sys.exit(0)
record("prompt-b")
with open(log, encoding="utf-8") as fh:
    b_calls = sum(1 for line in fh if line.startswith("prompt-b"))
limit_at = int(os.environ.get("SHIM_LIMIT_AT_B", "0"))
text = ("You've hit your session limit · resets 7pm (Europe/Berlin)" if limit_at and b_calls == limit_at
        else "Audit of the last turn.\nAll twelve checks hold.\nOVERSEER_PASS")
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}))
sid = argv[argv.index("--resume") + 1] if "--resume" in argv else "shim-fixture"   # a recorded-turn run has no prompt A to resume
print(json.dumps({"type": "result", "subtype": "success", "session_id": sid,
                  "total_cost_usd": @COST_B@, "duration_ms": 20, "num_turns": 3, "permission_denials": []}))
'''.replace("@COST_A@", str(COST_A)).replace("@COST_B@", str(COST_B))

PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:500]}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Harness:
    def __init__(self, work: Path) -> None:
        self.work = work
        self.shim = work / "bin" / "claude"
        self.shim.parent.mkdir()
        self.shim.write_text(SHIM, encoding="utf-8")
        self.shim.chmod(0o755)
        self.log = work / "calls.log"
        self.tmp = work / "tmp"   # where the runner's sandboxes go, so a kill leaves nothing in /tmp
        self.tmp.mkdir()
        self.out = work / "results" / "audit.json"

    def run(self, *extra: str, kill_at_a: int = 0, limit_at_b: int = 0, refuse_at_a: int = 0, engine_ref: str = "HEAD",
            runs: int = 1, only: str = ONLY) -> subprocess.CompletedProcess[str]:
        self.log.write_text("", encoding="utf-8")
        env = dict(os.environ, SHIM_LOG=str(self.log), SHIM_KILL_AT_A=str(kill_at_a),
                   SHIM_LIMIT_AT_B=str(limit_at_b), SHIM_REFUSE_AT_A=str(refuse_at_a), TMPDIR=str(self.tmp))
        return subprocess.run(
            [sys.executable, str(RUNNER), "--tasks-dir", str(ROOT / "tests/fixtures/board-audit-yes"),
             "--engine-ref", engine_ref, "--runs", str(runs), "--only", only,
             "--claude", str(self.shim), "--out", str(self.out), *extra],
            cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=600)

    def calls(self, kind: str) -> int:
        return sum(1 for line in self.log.read_text(encoding="utf-8").splitlines() if line.startswith(kind))

    def results(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.out.read_text(encoding="utf-8"))
        return loaded


def main() -> int:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    parent = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD~1"], capture_output=True, text=True, check=True).stdout.strip()
    work = Path(tempfile.mkdtemp(prefix="audit-resume-"))
    try:
        h = Harness(work)

        print("the crash: SIGKILL at the prompt-A call of run 3 (scenario 3 of 3, one run each):")
        r = h.run(kill_at_a=3)
        check("the runner died of the signal (returncode -9)", r.returncode == -9, f"rc={r.returncode} stderr={r.stderr[-300:]}")
        check("the shim recorded the kill", h.calls("kill") == 1, h.log.read_text())
        check("the result file exists", h.out.is_file())
        res = h.results()
        check("and is valid JSON (the write is temp + replace)", bool(res))
        check("no half-written .tmp beside it", not list(h.out.parent.glob("*.tmp")), str(list(h.out.parent.iterdir())))
        check("status is partial", res.get("status") == "partial", str(res.get("status")))
        done = [row["id"] for row in res["scenarios"] if row["runs"]]
        check("exactly the two finished scenarios hold a run", done == IDS[:2], str(done))
        check("the third is pending", res.get("pending") == [IDS[2]], str(res.get("pending")))
        costs = [run["cost_usd"] for row in res["scenarios"] for run in row["runs"]]
        check("each saved run carries its cost (A + B)", costs == [COST_A + COST_B] * 2, str(costs))
        check("total cost is the two runs", res["total_cost_usd"] == round(2 * (COST_A + COST_B), 2), str(res["total_cost_usd"]))
        check("the engine COMMIT is recorded, not only the ref", res.get("engine_commit") == head and res.get("engine_ref") == "HEAD", str(res.get("engine_commit")))
        check("the verdict of a saved run was read from the shim's reply", res["scenarios"][0]["runs"][0]["marker"] == "PASS" and res["scenarios"][0]["matched"] == 1, json.dumps(res["scenarios"][0]["runs"][0])[:300])
        check("the dead runner's sandboxes stayed under TMPDIR (so this suite can remove them)",
              any(p.name.startswith("engine-audit-") for p in h.tmp.iterdir()), str(list(h.tmp.iterdir())))
        before = sha(h.out)
        saved_runs = {row["id"]: row["runs"] for row in res["scenarios"] if row["runs"]}

        print("the refusals:")
        r = h.run()
        check("an existing --out without --resume is refused (exit 2)", r.returncode == 2 and "--resume" in r.stderr, f"rc={r.returncode} {r.stderr[-200:]}")
        check("and the file is untouched", sha(h.out) == before)
        check("no session was paid for", h.calls("prompt") == 0, h.log.read_text())
        r = h.run("--resume", engine_ref=parent)
        check("--resume against another engine commit is refused", r.returncode == 2 and "engine_commit differs" in r.stderr, r.stderr[-200:])
        check("file untouched", sha(h.out) == before)
        r = h.run("--resume", runs=2)
        check("--resume with another --runs is refused", r.returncode == 2 and "runs_per_scenario differs" in r.stderr, r.stderr[-200:])
        check("file untouched", sha(h.out) == before)
        check("none of the refusals ran a session", h.calls("prompt") == 0, h.log.read_text())

        print("the resume:")
        r = h.run("--resume")
        check("exit 0", r.returncode == 0, f"rc={r.returncode} {r.stderr[-300:]}")
        check("exactly one run was performed: one prompt A and one prompt B", h.calls("prompt-a") == 1 and h.calls("prompt-b") == 1, h.log.read_text())
        res = h.results()
        check("status is complete, nothing pending", res.get("status") == "complete" and res.get("pending") == [], f"{res.get('status')} {res.get('pending')}")
        check("the two recorded runs are unchanged", all(row["runs"] == saved_runs[row["id"]] for row in res["scenarios"] if row["id"] in saved_runs))
        check("the third scenario now has its run", [len(row["runs"]) for row in res["scenarios"]] == [1, 1, 1], str([len(row["runs"]) for row in res["scenarios"]]))
        check("total cost is the sum of three", res["total_cost_usd"] == round(3 * (COST_A + COST_B), 2), str(res["total_cost_usd"]))
        check("the recorded, skipped scenarios are shown as such", r.stdout.count("recorded, skipped") == 2, r.stdout[-600:])

        print("resume with nothing left:")
        r = h.run("--resume")
        check("exit 0 and no session call", r.returncode == 0 and h.calls("prompt") == 0, f"rc={r.returncode} {h.log.read_text()}")
        check("still complete", h.results().get("status") == "complete")

        print("resume into a file recorded before --resume existed:")
        legacy = h.out.with_name("legacy.json")
        legacy.write_text(json.dumps({"label": "old", "engine_ref": "HEAD", "scenarios": []}), encoding="utf-8")
        print("a refused echo: the shim answers prompt A of run 2 with a refusal instead of the scripted turn:")
        h.out.unlink()
        r = h.run(refuse_at_a=2)
        check("the runner finishes (exit 0): a refusal is recorded, not fatal", r.returncode == 0, f"rc={r.returncode} {r.stderr[-300:]}")
        check("prompt B was not sent for the refused run (2 prompt-B calls for 3 runs)", h.calls("prompt-b") == 2, h.log.read_text())
        res = h.results()
        rows = {row["id"]: row for row in res["scenarios"]}
        lost = rows[IDS[1]]["runs"][0]
        check("the refused run carries echo=refused and an 'echo refused' error, no verdict",
              lost.get("echo") == "refused" and str(lost.get("error", "")).startswith("echo refused") and "marker" not in lost, str(lost))
        check("a relayed run carries echo=relayed", rows[IDS[0]]["runs"][0].get("echo") == "relayed", str(rows[IDS[0]]["runs"][0]))
        check("the file is complete (a refusal is not pending)", res["status"] == "complete", str(res.get("status")))
        r = h.run("--resume")
        check("--resume does not redo a refused run (no session call)", r.returncode == 0 and h.calls("prompt-a") == 0, h.log.read_text())

        print("the account usage limit: the shim answers the limit notice at prompt B of run 2:")
        h.out.unlink()
        r = h.run(limit_at_b=2)
        check("the runner stops with exit 3 and says how to continue", r.returncode == 3 and "--resume" in r.stdout, f"rc={r.returncode} {r.stdout[-300:]}")
        check("it ran no further session (2 prompt-A calls, not 3)", h.calls("prompt-a") == 2, h.log.read_text())
        res = h.results()
        rows = {row["id"]: row for row in res["scenarios"]}
        check("run 1 is recorded as a verdict", rows[IDS[0]]["runs"] and rows[IDS[0]]["runs"][0].get("marker") == "PASS", str(rows[IDS[0]]["runs"]))
        lost = rows[IDS[1]]["runs"]
        check("run 2 is recorded as a usage-limit error, not as a verdict",
              len(lost) == 1 and str(lost[0].get("error", "")).startswith("account usage limit") and "marker" not in lost[0], str(lost))
        check("the file is partial with the third scenario pending", res["status"] == "partial" and res["pending"] == [IDS[2]], str(res.get("pending")))
        r = h.run("--resume")
        check("--resume performs the lost run again and the missing one (2 prompt-A calls)", r.returncode == 0 and h.calls("prompt-a") == 2, f"rc={r.returncode} {h.log.read_text()}")
        res = h.results()
        rows = {row["id"]: row for row in res["scenarios"]}
        check("the lost run is replaced by a verdict", rows[IDS[1]]["runs"][0].get("marker") == "PASS" and len(rows[IDS[1]]["runs"]) == 1, str(rows[IDS[1]]["runs"]))
        check("the file is complete", res["status"] == "complete" and res["pending"] == [], str(res.get("status")))

        r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(ROOT / "tests/fixtures/board-audit-yes"),
                            "--only", ONLY, "--claude", str(h.shim), "--out", str(legacy), "--resume"],
                           cwd=ROOT, env=dict(os.environ, SHIM_LOG=str(h.log), TMPDIR=str(h.tmp)), capture_output=True, text=True, check=False)
        check("refused with the reason", r.returncode == 2 and "no engine_commit" in r.stderr, r.stderr[-200:])

        print("--only as a list:")
        check("the three fragments selected exactly the three scenarios", [row["id"] for row in h.results()["scenarios"]] == IDS)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
