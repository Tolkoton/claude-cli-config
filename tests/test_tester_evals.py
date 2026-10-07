#!/usr/bin/env python3
"""The instrument of the planted-bug experiment, checked without a paid session (boards 061, 713).

  - no session starts unless the task in tasks/doing/ allows paid runs, and the limit is never
    more than the number that task names;
  - the count is the script's and refuses first: ready-made test files give «missed», «fails on
    both», «mirrors the bug» and «no tests» before one gives «caught»;
  - every scene is what it claims: a suite that tests everything but the trap passes on both
    implementations (the wrong one breaks nothing else), a suite that tests the trap fails on
    the wrong one only, and every test of it fails against the skeleton;
  - the arms see what they should: A the wrong implementation, B and C a skeleton with no body,
    and no prompt names the trap;
  - arm C's code is judged by the script: the scene's right module is «right», its wrong one
    «trapped», and trapped code under green tests of its own is «self-deceived».

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
    (tasks / "doing/061-x.md").write_text("# 061\n\nПлатні прогони: так, до 10 доларів.\n", encoding="utf-8")
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
    blind = Path(tmp) / "blind_tests.py"
    blind.write_text(HEAD["boundary"] + AROUND["boundary"], encoding="utf-8")
    shim.write_text(f"#!/bin/sh\ncp {evals.FIXTURE}/scenes/boundary/wrong.py src/refproj/inventory.py\ncp {blind} tests/test_reorder_flag_contract.py\n"
                    "echo '{\"total_cost_usd\": 0.2, \"result\": \"done\"}'\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(RUNNER), "--tasks-dir", str(tasks), "--claude", str(shim), "--scenes", "boundary", "--arms", "c", "--repeat", "2", "--out", str(Path(tmp) / "out.json")],
                       capture_output=True, text=True, env=env, check=False)
    recorded = json.loads((Path(tmp) / "out.json").read_text(encoding="utf-8")) if (Path(tmp) / "out.json").is_file() else {}
    check("arm C, a session that wrote the misreading and tests that agree with it: «missed», code «trapped», self-deceived — twice with --repeat 2",
          r.returncode == 0 and r.stdout.count("boundary c: missed; code trapped; SELF-DECEIVED") == 2 and recorded.get("summary", {}).get("self_deceived") == "2 of 2"
          and recorded["runs"][0]["module"].rstrip().endswith("item.on_hand < reorder_point") and list(recorded["arms"]) == ["c"], r.stdout + r.stderr)

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

print("arm C: the code the agent wrote is judged by the script")
for name in evals.SCENES:
    scene = expected[name]
    right, wrong = (evals.fixture(f"scenes/{name}/{kind}.py") for kind in ("right", "wrong"))
    blind, seeing = HEAD[name] + AROUND[name], HEAD[name] + AROUND[name] + "\n" + TRAP[name]
    got = [evals.judge_code(right, seeing, name, scene, work), evals.judge_code(wrong, blind, name, scene, work), evals.judge_code(wrong, seeing, name, scene, work)]
    check(f"{name}: the right module is «right»; the wrong one is «trapped», and self-deceived only under green tests of its own",
          [(g["code"], g["own_tests_green"], g["self_deceived"]) for g in got] == [("right", True, False), ("trapped", True, True), ("trapped", False, False)], got)
name, scene = "boundary", expected["boundary"]
got = evals.judge_code(evals.fixture("scenes/boundary/skeleton.py"), HEAD[name] + TRAP[name], name, scene, work)
check("a module left as the skeleton is «none», never right", got["code"] == "none" and not got["self_deceived"], got)
got = evals.judge_code(evals.fixture("scenes/boundary/right.py").replace("item.on_hand <= reorder_point", "True"), None, name, scene, work)
check("a module that fails another line of the contract is «broken», and no tests are not green tests", got["code"] == "broken" and not got["own_tests_green"], got)
rows = [{"scene": "order", "arm": "c", "cost_usd": 0.1, "outcome": "missed", "caught": False, "code": "trapped", "self_deceived": True},
        {"scene": "order", "arm": "c", "cost_usd": 0.1, "outcome": "caught", "caught": True, "code": "right", "self_deceived": False},
        {"scene": "order", "arm": "c", "cost_usd": 0.0, "error": "x"}]
got = evals.summary(rows)
check("the summary counts the code and the self-deceived, and keeps repeated runs apart",
      got["code_written"] == {"right": 1, "trapped": 1, "broken": 0, "none": 0} and got["self_deceived"] == "1 of 2" and got["caught"] == {"c": "1 of 3"}
      and got["table"] == {"order/c": "missed; code trapped; SELF-DECEIVED", "order/c#2": "caught; code right", "order/c#3": "error"}, got)
check("no scratch project is left behind by the scoring", not any(work.iterdir()), list(work.iterdir()))
shutil.rmtree(work)

print("the arms and the dry run")
check("twelve runs: four scenes, three arms; --arms and --repeat narrow and multiply",
      len(evals.plan(list(evals.SCENES))) == 12 and evals.plan(["empty"], ["a", "b"]) == [("empty", "a"), ("empty", "b")] and evals.plan(["empty"], ["c"], 3) == [("empty", "c")] * 3)
with tempfile.TemporaryDirectory() as tmp:
    dry = Path(tmp) / "dry"
    r = subprocess.run([sys.executable, str(RUNNER), "--dry-run", str(dry)], capture_output=True, text=True, check=False)
    check("the dry run builds twelve sandboxes and twelve prompts", r.returncode == 0 and len(list(dry.glob("prompt-*.txt"))) == 12, r.stdout + r.stderr)
    for name in evals.SCENES:
        scene = expected[name]
        seen = {arm: (dry / f"{name}-{arm}" / evals.module_path(scene)).read_text(encoding="utf-8") for arm in "abc"}
        check(f"{name}: arm A sees the wrong implementation, arms B and C a skeleton",
              seen["a"] == (evals.FIXTURE / "scenes" / name / "wrong.py").read_text(encoding="utf-8") and all(seen[arm].rstrip().endswith("raise NotImplementedError") for arm in "bc"))
        check(f"{name}: every sandbox has the contract, no test file of the slice yet and no reference tests",
              all((dry / f"{name}-{arm}/.engine/slices/{scene['slug']}.md").is_file() and not (dry / f"{name}-{arm}" / evals.test_path(scene)).exists()
                  and not list((dry / f"{name}-{arm}").rglob("*reference*")) for arm in "abc"))
    a, b, c = ((dry / f"prompt-order-{arm}.txt").read_text(encoding="utf-8") for arm in "abc")
    check("every prompt names the same contract, test file and run command",
          all(".engine/slices/stock-transfer.md" in p and "tests/test_stock_transfer_contract.py" in p and "uvx --with pytest pytest -q" in p and "{" not in p for p in (a, b, c)))
    check("arm A is told the implementation is there; arm B that there is none to read", "Your implementation of it is already in" in a and "no\nimplementation to read" in b)
    check("arm C is told to write both the implementation and the tests", "You write both the\nimplementation and the slice's tests" in c and "no body yet" in c)
    check("no prompt names the trap", not any(word in p for p in (a, b, c) for word in ("different SKUs", "first in this list", "trap", "wrong")), a)
    r = subprocess.run([sys.executable, str(RUNNER), "--dry-run", str(Path(tmp) / "dry-c"), "--arms", "c", "--repeat", "3", "--scenes", "order"], capture_output=True, text=True, check=False)
    check("--arms c --repeat 3 on one scene is one sandbox and one prompt in a dry run", r.returncode == 0 and [p.name for p in (Path(tmp) / "dry-c").glob("prompt-*.txt")] == ["prompt-order-c.txt"], r.stdout + r.stderr)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
