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
    by running it (46 s): the release check and the task's report do that, not this suite;
  - board 087: the suites run in parallel — two suites that each wait for the other pass only
    when both run at once — and what is printed, the exit code and the verdicts in the record are
    those of a run one at a time; the record carries the wall time, the jobs and every suite's time,
    and the next run starts the longest first.
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
    full = {k: v for k, v in os.environ.items() if k not in ("ENGINE_HEALTH_DIR", "ENGINE_TEST_JOBS")} | env
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

print("board 087: the suites run in parallel, and the result is the one of a run one at a time")
check("the record carries the wall time of the run, the jobs and the time of every suite", isinstance(again.get("seconds"), float)
      and isinstance(again.get("jobs"), int) and again["jobs"] >= 1 and sorted(again.get("suite_seconds", {})) == ["tests/test_green.py", "tests/test_red.py"]
      and all(isinstance(v, float) for v in again["suite_seconds"].values()), again)
(repo / "tests/test_red.py").write_text("import sys\nprint('FAIL 1')\nsys.exit(1)\n")
one, two = (sh(repo, "bash", "tests/run_all.sh", "--jobs", n) for n in ("1", "2"))
check("one job and two: the same lines, the same exit code", one.returncode == two.returncode == 1 and one.stdout == two.stdout
      and "  FAIL  tests/test_red.py" in one.stdout and "FAIL: 1 of 2 suites red" in one.stdout, one.stdout + two.stdout)
strip = lambda data: {k: v for k, v in data.items() if k not in ("recorded_utc", "seconds", "jobs", "suite_seconds")}
r = sh(repo, "bash", "tests/run_all.sh", "--jobs=1")
alone = record(health, "tests-full.json")
r = sh(repo, "bash", "tests/run_all.sh", ENGINE_TEST_JOBS="2")
both = record(health, "tests-full.json")
check("…and the same record, but for the time and the jobs (--jobs=1, then ENGINE_TEST_JOBS=2)", strip(alone) == strip(both)
      and alone.get("jobs") == 1 and both.get("jobs") == 2 and both.get("red") == ["tests/test_red.py"], (alone, both))
for bad in (["--jobs", "0"], ["--jobs", "two"], ["--jobs=-1"], ["--jobs"]):
    r = sh(repo, "bash", "tests/run_all.sh", *bad)
    check(f"the negative case: {' '.join(bad)} is refused (exit 2), nothing runs", r.returncode == 2 and "ok " not in r.stdout and "jobs" in r.stderr, r.stdout + r.stderr)
r = sh(repo, "bash", "tests/run_all.sh", ENGINE_TEST_JOBS="many")
check("…and so is ENGINE_TEST_JOBS=many", r.returncode == 2 and "jobs" in r.stderr, r.stdout + r.stderr)
(repo / "tests/test_red.py").write_text("print('PASS 1')\n")   # the tree as the cases below found it: dirty

pair = Path(tempfile.mkdtemp(prefix="health-pair-"))
(pair / "tests").mkdir()
shutil.copy(ROOT / "tests/run_all.sh", pair / "tests/run_all.sh")
# Each suite says it has started and waits for the other's word: green only when both run at once.
MEET = ("import sys, time\nfrom pathlib import Path\nhere = Path(__file__).parent\n(here / '{me}.started').touch()\n"
        "with (here / 'starts.log').open('a') as log:\n    log.write('{me}\\n')\n"
        "limit = time.monotonic() + {wait}\nwhile time.monotonic() < limit and not (here / '{other}.started').exists():\n    time.sleep(0.02)\n"
        "met = (here / '{other}.started').exists()\nprint('PASS 1' if met else 'FAIL alone')\nsys.exit(0 if met else 1)\n")
(pair / "tests/test_a.py").write_text(MEET.format(me="a", other="z", wait=20))
(pair / "tests/test_z.py").write_text(MEET.format(me="z", other="a", wait=20))
sh(pair, "git", "init", "-q", "-b", "main")


def fresh() -> None:
    for left in pair.glob("tests/*.started"):
        left.unlink()
    (pair / "tests/starts.log").unlink(missing_ok=True)


r = sh(pair, "bash", "tests/run_all.sh", "--jobs", "2")
check("two suites that wait for each other are both green with two jobs: they ran at once", r.returncode == 0 and "PASS: 2 suites green" in r.stdout, r.stdout + r.stderr)
check("…and the lines stand in the order of the list", [line.split()[1] for line in r.stdout.splitlines() if line.startswith("  ok")] == ["tests/test_a.py", "tests/test_z.py"], r.stdout)
fresh()
(pair / "tests/test_a.py").write_text(MEET.format(me="a", other="z", wait=1))
r = sh(pair, "bash", "tests/run_all.sh", "--jobs", "1")
check("the negative case: with one job the first waits alone and is red — one job is one at a time", r.returncode == 1
      and "  FAIL  tests/test_a.py" in r.stdout and "  ok    tests/test_z.py" in r.stdout, r.stdout + r.stderr)
(pair / "tests/test_a.py").write_text(MEET.format(me="a", other="z", wait=20))
(pair / "tests/test_m.py").write_text("from pathlib import Path\nwith (Path(__file__).parent / 'starts.log').open('a') as log:\n    log.write('m\\n')\nprint('PASS 1')\n")
state = pair / ".claude/state/health"
fresh()
(state / "tests-full.json").write_text(json.dumps({"suite_seconds": {"tests/test_a.py": 5.0, "tests/test_m.py": 0.1, "tests/test_z.py": 9.0}}))
r = sh(pair, "bash", "tests/run_all.sh", "--jobs", "2")
starts = (pair / "tests/starts.log").read_text().split()
check("the longest suites of the previous run start first: the short one starts last, and its line is still the second", r.returncode == 0
      and sorted(starts[:2]) == ["a", "z"] and starts[2:] == ["m"]
      and [line.split()[1] for line in r.stdout.splitlines() if line.startswith("  ok")] == ["tests/test_a.py", "tests/test_m.py", "tests/test_z.py"], (starts, r.stdout + r.stderr))
fresh()
(state / "tests-full.json").write_text(json.dumps({"suite_seconds": {"tests/test_a.py": 5.0, "tests/test_z.py": 9.0}}))
(pair / "tests/test_m.py").write_text((pair / "tests/test_m.py").read_text() + "import time\ntime.sleep(0.5)\n")
r = sh(pair, "bash", "tests/run_all.sh", "--jobs", "2")
starts = (pair / "tests/starts.log").read_text().split()
check("a suite the previous run did not time starts among the first, ahead of a timed one", r.returncode == 0
      and sorted(starts[:2]) == ["m", "z"] and starts[2:] == ["a"], (starts, r.stdout + r.stderr))
(state / "tests-full.json").write_text("not json")
fresh()
r = sh(pair, "bash", "tests/run_all.sh", "--jobs", "2")
check("the negative case: a previous record that cannot be read changes nothing — the run is green and leaves a whole record", r.returncode == 0
      and record(state, "tests-full.json").get("green") == 3, r.stdout + r.stderr)
(pair / "tests/test_m.py").unlink()
(pair / "tests/test_a.py").write_text("import time\nfrom pathlib import Path\nword = Path(__file__).parent / 'z.finished'\nlimit = time.monotonic() + 20\n"
                                      "while time.monotonic() < limit and not word.exists():\n    time.sleep(0.02)\nprint('PASS 1' if word.exists() else 'FAIL alone')\n")
(pair / "tests/test_z.py").write_text("from pathlib import Path\nprint('PASS 1')\n(Path(__file__).parent / 'z.finished').touch()\n")
r = sh(pair, "bash", "tests/run_all.sh", "--jobs", "2")
check("the first suite of the list finishes last, and its line is still the first", r.returncode == 0
      and [line.split() for line in r.stdout.splitlines() if line.startswith("  ok")] == [["ok", "tests/test_a.py", "PASS", "1"], ["ok", "tests/test_z.py", "PASS", "1"]], r.stdout + r.stderr)
shutil.rmtree(pair, ignore_errors=True)

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
