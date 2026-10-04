#!/usr/bin/env python3
"""The instrument of the planted-bug experiment, checked without a paid session (board 061).

  - no session starts unless the task in tasks/doing/ allows paid runs, and the limit is never
    more than the number that task names;
  - the count is the script's and refuses first: ready-made test files give «missed», «fails on
    both», «mirrors the bug» and «no tests» before one gives «caught»;
  - every scene is what it claims: a suite that tests everything but the trap passes on both
    implementations (the wrong one breaks nothing else), a suite that tests the trap fails on
    the wrong one only, and every test of it fails against the skeleton;
  - the arms see what they should: A the wrong implementation, B a skeleton with no body, and
    neither prompt names the trap.

Run:   python3 tests/test_tester_evals.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals/run_tester_evals.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def load() -> Any:
    spec = importlib.util.spec_from_file_location("run_tester_evals", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_tester_evals"] = module
    spec.loader.exec_module(module)
    return module


evals = load()
expected = json.loads(evals.fixture("expected.json"))

HEAD = {
    "boundary": "import pytest\nfrom decimal import Decimal\nfrom refproj.inventory import StockItem, needs_reorder\n\nW = StockItem('W-1', Decimal('2.50'), 4)\n\n",
    "rounding": "import pytest\nfrom decimal import Decimal\nfrom refproj.pricing import add_tax\n\n",
    "empty": "import pytest\nfrom decimal import Decimal\nfrom refproj.pricing import average\n\n",
    "order": "import pytest\nfrom decimal import Decimal\nfrom refproj.inventory import StockItem, transfer\n\n"
             "A = StockItem('W-1', Decimal('2.50'), 4)\nB = StockItem('W-1', Decimal('2.50'), 1)\nC = StockItem('X-9', Decimal('2.50'), 1)\n\n",
}
# Everything the contract says except the trap: green on both implementations.
AROUND = {
    "boundary": "def test_below():\n    assert needs_reorder(W, 5) is True\n\ndef test_above():\n    assert needs_reorder(W, 3) is False\n\n"
                "def test_negative():\n    with pytest.raises(ValueError, match='reorder point'):\n        needs_reorder(W, -1)\n",
    "rounding": "def test_plain():\n    assert add_tax(Decimal('10.00'), Decimal('20')) == Decimal('12.00')\n\n"
                "def test_rounds_up_past_the_tie():\n    assert add_tax(Decimal('0.51'), Decimal('5')) == Decimal('0.54')\n\n"
                "def test_negative():\n    with pytest.raises(ValueError, match='tax rate'):\n        add_tax(Decimal('1'), Decimal('-1'))\n",
    "empty": "def test_mean():\n    assert average([Decimal('1.00'), Decimal('2.00')]) == Decimal('1.50')\n\n"
             "def test_generator():\n    assert average(p for p in [Decimal('1.00'), Decimal('2.01')]) == Decimal('1.51')\n",
    "order": "def test_moves():\n    assert [i.on_hand for i in transfer(A, B, 3)] == [1, 4]\n\n"
             "def test_mismatch():\n    with pytest.raises(ValueError, match='different SKUs'):\n        transfer(A, C, 1)\n\n"
             "def test_too_many():\n    with pytest.raises(ValueError, match='only'):\n        transfer(A, B, 9)\n",
}
# The one test of the trap: red on the wrong implementation only.
TRAP = {
    "boundary": "def test_at_the_point():\n    assert needs_reorder(W, 4) is True\n",
    "rounding": "def test_tie_goes_to_the_even_cent():\n    assert add_tax(Decimal('0.50'), Decimal('5')) == Decimal('0.52')\n",
    "empty": "def test_nothing_to_average():\n    with pytest.raises(ValueError, match='no prices'):\n        average([])\n",
    "order": "def test_mismatch_wins_over_shortage():\n    with pytest.raises(ValueError, match='different SKUs'):\n        transfer(A, C, 9)\n",
}

print("paid runs: only with the owner's line, never past its number")
with tempfile.TemporaryDirectory() as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    (tasks / "doing/061-x.md").write_text("# 061\n\nАудит потрібен: ні\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDECODE": "1"}
    shim = Path(tmp) / "claude"
    shim.write_text(f"#!/bin/sh\necho started >> {tmp}/started\n", encoding="utf-8")
    shim.chmod(0o755)
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--owner-approved"], capture_output=True, text=True, env=env, check=False)
    check("refused without a «Платні прогони:» line, and --owner-approved does not count in a session; no session started",
          r.returncode == 2 and "refusing to start paid sessions" in r.stderr and not (Path(tmp) / "started").exists(), r.stderr)
    (tasks / "doing/061-x.md").write_text("# 061\n\nПлатні прогони: вісім прогонів, ліміт 10 доларів.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--max-usd", "0.5"], capture_output=True, text=True, env=env, check=False)
    check("with the line, a limit smaller than one run starts nothing", "cost limit" in r.stdout and not (Path(tmp) / "started").exists() and r.returncode == 1, r.stdout + r.stderr)
    shim.write_text(f"#!/bin/sh\necho started >> {tmp}/started\necho '{{\"total_cost_usd\": 6, \"result\": \"done\"}}'\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--max-usd", "50", "--max-usd-per-run", "6", "--scenes", "boundary"],
                       capture_output=True, text=True, env=env, check=False)
    started = (Path(tmp) / "started").read_text(encoding="utf-8").count("started")
    check("the task's 10 dollars cap a larger --max-usd: after a run of 6 dollars the second is not started", started == 1 and "the limit is $10.00" in r.stdout and r.returncode == 1, r.stdout + r.stderr)
    check("a session that wrote no test file is «no tests»", "boundary a: no_tests" in r.stdout, r.stdout)
    shim.write_text("#!/bin/sh\necho not json\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--scenes", "boundary"], capture_output=True, text=True, env=env, check=False)
    check("a session that gives no result is an error row, never an outcome", "boundary a: the session gave no result" in r.stdout and '"boundary/b": "error"' in r.stdout and r.returncode == 1, r.stdout)

print("the count: caught / missed / fails on both, on ready-made test files")
work = Path(tempfile.mkdtemp(prefix="engine-tester-evaltest-"))
name, scene = "boundary", expected["boundary"]
check("no file is «no tests», not caught", evals.score(None, name, scene, work) == {"outcome": "no_tests", "caught": False, "observed": "the test file was not written"})
got = evals.score(HEAD[name] + "X = 1\n", name, scene, work)
check("a file with no test in it is «no tests», not caught", got["outcome"] == "no_tests" and not got["caught"], got)
got = evals.score(HEAD[name] + AROUND[name], name, scene, work)
check("a suite that passes on both is «missed»", got["outcome"] == "missed" and not got["caught"], got)
got = evals.score(HEAD[name] + AROUND[name] + "\ndef test_wrong_expectation():\n    assert needs_reorder(W, 9) is False\n", name, scene, work)
check("a suite that fails on both is «fails on both», not caught", got["outcome"] == "fails_on_both" and not got["caught"], got)
got = evals.score(HEAD[name] + TRAP[name] + "\ndef test_wrong_expectation():\n    assert needs_reorder(W, 9) is False\n", name, scene, work)
check("…even when one of its tests is the trap's", got["outcome"] == "fails_on_both" and not got["caught"], got)
got = evals.score("import nothing_there\n\ndef test_x():\n    assert True\n", name, scene, work)
check("a file that does not import fails on both", got["outcome"] == "fails_on_both", got)
got = evals.score(HEAD[name] + "def test_at_the_point_copied_from_the_code():\n    assert needs_reorder(W, 4) is False\n", name, scene, work)
check("a suite that asserts what the wrong code does is «mirrors the bug», not caught", got["outcome"] == "mirrors_bug" and not got["caught"], got)
got = evals.score(HEAD[name] + AROUND[name] + "\n" + TRAP[name], name, scene, work)
check("a suite that fails on the wrong implementation and passes on the right one is «caught»", got["outcome"] == "caught" and got["caught"] and "1 failed, 3 passed" in got["observed"], got)

print("the scenes are what they claim")
for name in evals.SCENES:
    scene = expected[name]
    around, trap = evals.score(HEAD[name] + AROUND[name], name, scene, work), evals.score(HEAD[name] + TRAP[name], name, scene, work)
    check(f"{name}: the wrong implementation breaks the trap's line and nothing else", around["outcome"] == "missed" and trap["outcome"] == "caught", (around, trap))
    red = evals.run_suite(HEAD[name] + AROUND[name] + "\n" + TRAP[name], name, scene, "skeleton", work)
    count = (AROUND[name] + TRAP[name]).count("def test_")
    check(f"{name}: against the skeleton every test is red", not red["passed"] and red["last_line"].startswith(f"{count} failed"), red)
    skeleton = (evals.FIXTURE / "scenes" / name / "skeleton.py").read_text(encoding="utf-8")
    check(f"{name}: the skeleton has the function and no body", f"def {scene['function']}(" in skeleton and skeleton.rstrip().endswith("raise NotImplementedError"))
check("no scratch project is left behind by the scoring", not any(work.iterdir()), list(work.iterdir()))
shutil.rmtree(work)

print("the arms and the dry run")
check("eight runs: four scenes, two arms", len(evals.plan(list(evals.SCENES))) == 8 and evals.plan(["empty"]) == [("empty", "a"), ("empty", "b")])
with tempfile.TemporaryDirectory() as tmp:
    dry = Path(tmp) / "dry"
    r = subprocess.run([sys.executable, str(RUNNER), "--dry-run", str(dry)], capture_output=True, text=True, check=False)
    check("the dry run builds eight sandboxes and eight prompts", r.returncode == 0 and len(list(dry.glob("prompt-*.txt"))) == 8, r.stdout + r.stderr)
    for name in evals.SCENES:
        scene = expected[name]
        seen = {arm: (dry / f"{name}-{arm}" / evals.module_path(scene)).read_text(encoding="utf-8") for arm in "ab"}
        check(f"{name}: arm A sees the wrong implementation, arm B a skeleton",
              seen["a"] == (evals.FIXTURE / "scenes" / name / "wrong.py").read_text(encoding="utf-8") and seen["b"].rstrip().endswith("raise NotImplementedError"))
        check(f"{name}: both sandboxes have the contract and no test file of the slice yet",
              all((dry / f"{name}-{arm}/.engine/slices/{scene['slug']}.md").is_file() and not (dry / f"{name}-{arm}" / evals.test_path(scene)).exists() for arm in "ab"))
    a, b = ((dry / f"prompt-order-{arm}.txt").read_text(encoding="utf-8") for arm in "ab")
    check("both prompts name the same contract, test file and run command",
          all(".engine/slices/stock-transfer.md" in p and "tests/test_stock_transfer_contract.py" in p and "uvx --with pytest pytest -q" in p and "{" not in p for p in (a, b)))
    check("arm A is told the implementation is there; arm B that there is none to read", "Your implementation of it is already in" in a and "no\nimplementation to read" in b)
    check("neither prompt names the trap", not any(word in p for p in (a, b) for word in ("different SKUs", "first in this list", "trap", "wrong")), a)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
