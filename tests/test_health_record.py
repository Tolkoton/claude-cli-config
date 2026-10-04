#!/usr/bin/env python3
"""The machine records of the test run and of the golden set (board 035).

The owner's review takes «Здоров'я» from what the tools wrote about their own runs —
.claude/state/health/tests-full.json, tests-fast.json, golden.json — and not from what an agent
wrote about them. This suite runs the REAL tests/run_all.sh in a synthetic repository with one
green and one red suite, and calls the golden-set runner's own recorder:

  - a whole run leaves the record: time (UTC), commit, dirty tree or not, suites, green, the red by name;
  - the fast subset leaves its own file and does not touch the full one;
  - the negative cases: a filtered run and --list leave nothing, and a record is replaced, never appended;
  - the golden-set runner: its recorder, and a REAL partial run (--only; a temporary sandbox of HEAD,
    about a second), which must end normally and record nothing. The whole set's own record is seen
    by running it (46 s): the release check and the task's report do that, not this suite.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


def sh(cwd: Path, *cmd: str, **env: str) -> subprocess.CompletedProcess[str]:
    full = {k: v for k, v in os.environ.items() if k != "ENGINE_HEALTH_DIR"} | env
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, env=full, check=False)


def record(folder: Path, name: str) -> dict[str, Any]:
    path = folder / name
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data


repo = Path(tempfile.mkdtemp(prefix="health-"))
(repo / "tests").mkdir()
shutil.copy(ROOT / "tests/run_all.sh", repo / "tests/run_all.sh")
(repo / "tests/test_green.py").write_text("print('PASS 1')\n")
(repo / "tests/test_red.py").write_text("import sys\nprint('FAIL 1')\nsys.exit(1)\n")
(repo / "tests/fast-suites.txt").write_text("# the gate's subset\ntest_green.py\n")
(repo / ".gitignore").write_text(".claude/state/\n")
sh(repo, "git", "init", "-q", "-b", "main")
for key, value in (("user.name", "t"), ("user.email", "t@example.invalid")):
    sh(repo, "git", "config", key, value)
sh(repo, "git", "add", "-A")
sh(repo, "git", "commit", "-q", "-m", "base")
head = sh(repo, "git", "rev-parse", "HEAD").stdout.strip()
health = repo / ".claude/state/health"

print("tests/run_all.sh leaves a machine record of a whole run")
r = sh(repo, "bash", "tests/run_all.sh", "--list")
check("the negative case: --list runs nothing and records nothing", r.returncode == 0 and not health.exists(), r.stdout + r.stderr)
r = sh(repo, "bash", "tests/run_all.sh", "green")
check("the negative case: a filtered run is not a run of the set — no record", r.returncode == 0 and not health.exists(), r.stdout + r.stderr)
r = sh(repo, "bash", "tests/run_all.sh")
full = record(health, "tests-full.json")
check("the whole set: exit 1 (one suite is red), and the record is written", r.returncode == 1 and full != {}, r.stdout + r.stderr)
check("…the time in UTC, the commit, a clean tree", re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", str(full.get("recorded_utc"))) is not None
      and full.get("commit") == head and full.get("dirty") is False, full)
check("…how many suites ran, how many were green, the red one by name", full.get("suites") == 2 and full.get("green") == 1
      and full.get("red") == ["tests/test_red.py"] and full.get("mode") == "full", full)
check("…and nothing else is left in the directory", sorted(p.name for p in health.iterdir()) == ["tests-full.json"], list(health.iterdir()))
r = sh(repo, "bash", "tests/run_all.sh", "--fast")
fast = record(health, "tests-fast.json")
check("the fast subset: its own record, one of one green, and the full record untouched", r.returncode == 0 and fast.get("suites") == 1
      and fast.get("green") == 1 and fast.get("red") == [] and fast.get("mode") == "fast" and record(health, "tests-full.json") == full, fast)
(repo / "tests/test_red.py").write_text("print('PASS 1')\n")
r = sh(repo, "bash", "tests/run_all.sh")
again = record(health, "tests-full.json")
check("the red suite fixed but not committed: the record is replaced — two of two green — and says the tree was dirty", r.returncode == 0
      and again.get("green") == 2 and again.get("red") == [] and again.get("dirty") is True and again.get("commit") == head, again)
other = Path(tempfile.mkdtemp(prefix="health-dir-"))
r = sh(repo, "bash", "tests/run_all.sh", "--fast", ENGINE_HEALTH_DIR=str(other))
check("ENGINE_HEALTH_DIR names another directory", record(other, "tests-fast.json").get("green") == 1 and record(health, "tests-fast.json") == fast)

print("evals/run_hook_scenarios.py leaves a machine record of a whole run of the golden set")
spec = importlib.util.spec_from_file_location("run_hook_scenarios", ROOT / "evals/run_hook_scenarios.py")
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
os.environ["ENGINE_HEALTH_DIR"] = str(other)
runner.record_health(repo, "HEAD", [{"id": "a", "pass": True}, {"id": "b", "pass": False}, {"id": "c", "pass": True}],
                     Path("evals/baseline/box/results-task-033.json"), 1)
golden = record(other, "golden.json")
check("the record: time (UTC), the commit of the repository, the ref, scenarios, green, the red by id, the baseline and the differences",
      re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", str(golden.get("recorded_utc"))) is not None and golden.get("commit") == head
      and golden.get("engine_ref") == "HEAD" and golden.get("scenarios") == 3 and golden.get("green") == 2 and golden.get("red") == ["b"]
      and golden.get("compare") == "results-task-033.json" and golden.get("differences") == 1 and golden.get("dirty") is True, golden)
partial = Path(tempfile.mkdtemp(prefix="health-partial-"))
r = sh(ROOT, sys.executable, "evals/run_hook_scenarios.py", "--engine-ref", "HEAD", "--only", "no-scenario-has-this-id", ENGINE_HEALTH_DIR=str(partial))
check("the negative case, the REAL runner: a partial run (--only) ends normally and leaves no record", r.returncode == 0
      and "PASS 0/0" in r.stdout and list(partial.iterdir()) == [], r.stdout[-300:] + r.stderr[-300:])

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
