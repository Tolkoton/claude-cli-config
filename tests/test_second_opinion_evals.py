#!/usr/bin/env python3
"""The second-opinion measurement: the cases say what they claim, the scorer counts honestly,
nothing paid starts without the owner's word and the key. No model is called here: Gemini is a
local server, Claude a shim.

Run:   python3 tests/test_second_opinion_evals.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals" / "run_second_opinion_evals.py"
spec = importlib.util.spec_from_file_location("run_second_opinion_evals", RUNNER)
assert spec and spec.loader
runner: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

PASS = FAIL = 0
KEY = "eval-key-51c2d9"


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


doc = json.loads((runner.SCENARIO / "cases.json").read_text(encoding="utf-8"))
cases = doc["cases"]
work = Path(tempfile.mkdtemp(prefix="engine-second-opinion-evaltest-"))

print("CASES-*   cases.json describes projects that are really there")
truth = [c["truth"] for c in cases]
check("21 correct findings and 12 false ones, every id once", (truth.count("correct"), truth.count("false")) == (21, 12)
      and len({c["id"] for c in cases}) == len(cases), truth)
check("the false ones are the four traps and eight typical mistakes; the correct ones are planted or the owner's fifteen",
      [sum(c["kind"] == k for c in cases) for k in ("trap", "typical", "planted", "first-pass")] == [4, 8, 6, 15])
has_commit = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", doc["engine_commit"] + "^{commit}"], capture_output=True, check=False).returncode == 0
if not has_commit:  # a shallow clone: the engine cases cannot be built, the fixture ones can
    print(f"  note the commit {doc['engine_commit'][:10]} is not in this clone: the fifteen engine cases are skipped")
    doc["cases"] = cases = [c for c in cases if c["project"] == "fixture"]
    doc["engine_commit"] = "HEAD"
projects = runner.build_projects(work / "projects", doc)
requests = runner.requests_for(projects, doc)
for row in requests:
    case, prompt = row["case"], row["prompt"]
    target = case["finding"]["target"].split("::")[0].split(":")[0]
    ok = (projects[case["project"]] / target).is_file() and f"=== {target} (lines" in prompt and case["finding"]["claim"] in prompt
    if case["truth"] == "false":
        ok = ok and case["shown"] in prompt
    check(f"{case['id']}: the target exists and is in the request" + (", with the line that refutes the claim" if case["truth"] == "false" else ""),
          ok, prompt[:300])
check("no request carries the truth, the reason for it, or the simplifier's own records",
      not any(r["case"]["why"] in r["prompt"] or "=== .engine/simplifier/" in r["prompt"] or "=== .engine/lesson-queue.md" in r["prompt"] for r in requests))
check("a path::symbol target is shown around the symbol's definition, not from the top of the file",
      not has_commit or "=== engine.py (lines 1-" not in next(r["prompt"] for r in requests if r["case"]["finding"]["target"] == "engine.py::ref_commit"))
(projects["fixture"] / "p.json").write_text('{"A1": "1.03", "B2": "2.50"}', encoding="utf-8")
ran = subprocess.run([sys.executable, "-m", "refproj.report", "p.json", "json", "cash", "A1:2", "B2:1"], cwd=projects["fixture"],
                     capture_output=True, text=True, check=False, env={**os.environ, "PYTHONPATH": "src"})
check("the overlay is a working program: the report runs", ran.returncode == 0 and "due 4.55" in ran.stdout and "fragile only" in ran.stdout, ran.stdout + ran.stderr)

print("SCORE-*   caught, false alarms, the thresholds")


def answers(judge: str, false_caught: int, alarms: int, false_total: int = 10, correct_total: int = 10) -> list[dict[str, Any]]:
    rows = [{"judge": judge, "truth": "false", "kind": "trap", "verdict": "disagree" if i < false_caught else "agree",
             "verified": i == 0, "cost_usd": 0.01} for i in range(false_total)]
    rows += [{"judge": judge, "truth": "correct", "kind": "planted", "verdict": "disagree" if i < alarms else "agree",
              "verified": False, "cost_usd": 0.01} for i in range(correct_total)]
    return rows


def run(gemini: tuple[int, int], claude: tuple[int, int], complete: bool = True) -> dict[str, Any]:
    return {"complete": complete, "answers": answers("gemini", *gemini) + answers("claude", *claude)}


r = runner.rates(answers("gemini", 6, 1))
check("6 of 10 false caught, 1 of 10 correct alarmed", (r["caught"], r["false_alarms"], r["caught_with_a_checked_line"]) == (0.6, 0.1, 0.1), r)
r = runner.rates([{"truth": "false", "verdict": "unsure", "verified": False}, {"truth": "false", "verdict": "no_opinion", "verified": False}])
check("unsure and no_opinion are not a catch, and are counted", (r["caught"], r["unsure"], r["no_opinion"], r["false_alarms"]) == (0.0, 1, 1, None), r)
s = runner.summary([run((6, 1), (4, 0)), run((8, 1), (4, 0))])
check("two runs: the mean, the per-run figures, the cost", s["gemini"]["caught"] == 0.7 and s["gemini"]["caught_per_run"] == [0.6, 0.8]
      and s["claude"]["caught"] == 0.4 and s["cost_usd"] == 0.8, s)
check("0.7 caught, 0.1 alarms, 0.3 over the control: passed", s["thresholds"]["passed"] is True and s["thresholds"]["margin_over_control"] == 0.3, s["thresholds"])
check("catching under half fails", runner.summary([run((4, 0), (0, 0))])["thresholds"]["passed"] is False)
check("alarms on more than one in ten fail", runner.summary([run((9, 2), (0, 0))])["thresholds"]["passed"] is False)
check("a control that catches as much fails: the other model adds nothing", runner.summary([run((7, 0), (6, 0))])["thresholds"]["passed"] is False)
s = runner.summary([run((9, 0), (0, 0), complete=False)])
check("a run cut short is not judged", s["complete_runs"] == 0 and s["thresholds"]["passed"] is None and s["cost_usd"] == 0.4, s)

print("KEY-*     nothing starts without the key; no leave is asked (board 078) and every Claude session is booked")


class Gemini(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self) -> None:
        Gemini.calls += 1
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        text = json.dumps({"verdict": "disagree", "reason": "found by name", "counter_evidence": [{"ref": "src/refproj/exports.py:42", "detail": "globals()"}]})
        payload = {"candidates": [{"content": {"parts": [{"text": text}]}}], "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 500}}
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *args: Any) -> None:
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Gemini)
threading.Thread(target=server.serve_forever, daemon=True).start()
shim = work / "claude"
shim.write_text('#!/bin/sh\nhere="$(dirname "$0")"\nprintf \'%s\\n\' "$@" > "$here/argv"\necho "key=${GEMINI_API_KEY_SIMPLIFIER:-none}" >> "$here/started"\n'
                'echo \'{"result": "{\\"verdict\\": \\"agree\\", \\"reason\\": \\"no caller\\", \\"counter_evidence\\": []}", "total_cost_usd": 0.02}\'\n')
shim.chmod(0o755)
board = work / "tasks"
(board / "doing").mkdir(parents=True)
(board / "doing" / "013-x.md").write_text("# 013\n\nАудит потрібен: ні\n", encoding="utf-8")


def measure(*args: str, key: str | None = KEY) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY_SIMPLIFIER", "GEMINI_API_KEY")}
    env |= {"CLAUDECODE": "1", "SECOND_OPINION_API_BASE": f"http://127.0.0.1:{server.server_port}/v1beta",
            "BOARD_STATE_DIR": str(work / "books")} | ({"GEMINI_API_KEY_SIMPLIFIER": key} if key else {})
    return subprocess.run([sys.executable, str(RUNNER), "--only", "typical-string-dispatch", "--tasks-dir", str(board), "--claude", str(shim), *args],
                          capture_output=True, text=True, check=False, env=env)


done = measure("--runs", "1", key=None)
check("no key: refused before either judge is asked — the control included; no other leave is asked",
      done.returncode == 2 and "GEMINI_API_KEY_SIMPLIFIER" in done.stderr and Gemini.calls == 0 and not (work / "started").exists(), done.stderr)
done = measure("--runs", "2", "--max-usd", "0.2")
check("a limit below one call: the run is cut short before anything is asked", "cut short" in done.stdout and Gemini.calls == 0 and not (work / "started").exists(), done.stdout)
out = work / "result.json"
done = measure("--runs", "2", "--out", str(out))
result = json.loads(out.read_text()) if out.is_file() else {}
summary = result.get("summary", {})
check("with both: every case goes to both judges in every run", Gemini.calls == 2 and (work / "started").read_text().count("key=") == 2, done.stdout + done.stderr)
booked = [json.loads(line) for line in (work / "books" / "extra-sessions.jsonl").read_text(encoding="utf-8").splitlines()] if (work / "books" / "extra-sessions.jsonl").is_file() else []
check("the two Claude sessions are booked to the task in hand; the Gemini calls are not Claude's",
      [(b["task"], b["tool"]) for b in booked] == [("013-x", "run_second_opinion_evals")] * 2, booked)
check("the control never sees the key, has no tools, and gets the same system text",
      "key=none" in (work / "started").read_text() and "--tools\n\n" in (work / "argv").read_text() and "You did not make the claim" in (work / "argv").read_text())
check("the result: gemini caught it with a checked line, the control did not; cost from both",
      summary.get("gemini", {}).get("caught") == 1.0 and summary.get("gemini", {}).get("caught_with_a_checked_line") == 1.0
      and summary.get("claude", {}).get("caught") == 0.0 and summary.get("cost_usd") == 0.056, summary)
check("one false case alone cannot pass the thresholds, and the exit code says so", done.returncode == 1 and summary.get("thresholds", {}).get("passed") is None, summary.get("thresholds"))
check("the key is not in the result file", KEY not in out.read_text())
rescored = subprocess.run([sys.executable, str(RUNNER), "--score", str(out)], capture_output=True, text=True, check=False)
check("--score gives the same summary from the file, free", json.loads(rescored.stdout) == summary, rescored.stdout[:300])

server.shutdown()
shutil.rmtree(work, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
