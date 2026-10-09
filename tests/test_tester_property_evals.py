#!/usr/bin/env python3
"""The property set of the tester instrument, checked without a paid session (board 063).

  - no session starts unless the task in tasks/doing/ allows paid runs; arm C alone is allowed
    the run command that brings the library;
  - every scene is what it claims: the wrong implementation passes the examples its contract
    gives and fails on the trap's input, and against the skeleton every test is red;
  - the two contracts of a scene differ by the «Invariants» section alone; arm A never sees it;
  - the three prompts differ by the paragraph on invariants and the run command, nothing else;
  - the count is the script's and refuses first: «missed», «fails on both» (a property test where
    there is no library), a narrowed generator, a trap reached and not noticed, before «caught»;
    on the control «fails on right» and an invented invariant before «clean».

Run:   python3 tests/test_tester_property_evals.py       Exit: 0 all green, 1 otherwise.
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

from tool_pins import spec

ROOT = Path(__file__).resolve().parent.parent
PYTEST = spec("pytest")          # the pinned releases (board 107, tests/tool_pins.py)
HYPOTHESIS = spec("hypothesis")
RUNNER = ROOT / "evals/run_tester_evals.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def load() -> Any:
    spec = importlib.util.spec_from_file_location("run_tester_evals", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_tester_evals"] = module
    spec.loader.exec_module(module)
    return module


evals = load()
scenes = evals.scenes_of("property")
TRAPS = [name for name in evals.PROPERTY_SCENES if name != "none"]
GIVEN = "from hypothesis import given, settings, HealthCheck\nfrom hypothesis import strategies as st\n\n"

HEAD = {
    "roundtrip": "import pytest\nfrom decimal import Decimal\nfrom refproj.pricing import format_price, parse_price\n\n",
    "conserve": "import pytest\nfrom decimal import Decimal\nfrom refproj.pricing import split_bill\n\n",
    "idempotent": "import pytest\nfrom refproj.inventory import normalize_sku\n\n",
    "bound": "import pytest\nfrom refproj.inventory import Shelf, hold, release\n\n",
    "none": "from decimal import Decimal\nfrom refproj.inventory import StockItem, shelf_value\n\n",
}
# Every example the contract gives, and its errors: green on both implementations.
OBVIOUS = {
    "roundtrip": "def test_prints():\n    assert [format_price(Decimal(p)) for p in ('12.5', '1234.5', '0')] == ['12.50', '1,234.50', '0.00']\n\n"
                 "def test_reads():\n    assert str(parse_price('1,234.50')) == '1234.50' and str(parse_price('1234.50')) == '1234.50'\n\n"
                 "def test_there_and_back_on_the_examples():\n    for p in ('0.00', '12.50', '1234.50', '999999.99'):\n        assert parse_price(format_price(Decimal(p))) == Decimal(p)\n\n"
                 "@pytest.mark.parametrize('text', ['12.5', '12', '1,23.00', '', 'abc'])\ndef test_not_a_price(text):\n    with pytest.raises(ValueError, match='not a price'):\n        parse_price(text)\n\n"
                 "@pytest.mark.parametrize('price', ['10000000.00', '-0.01', '0.001'])\ndef test_cannot_print(price):\n    with pytest.raises(ValueError, match='not a price'):\n        format_price(Decimal(price))\n",
    "conserve": "def test_even():\n    assert split_bill(Decimal('100.00'), 4) == [Decimal('25.00')] * 4\n\n"
                "def test_the_odd_cent_goes_first():\n    assert [str(s) for s in split_bill(Decimal('100.00'), 3)] == ['33.34', '33.33', '33.33']\n\n"
                "def test_one_and_nothing():\n    assert split_bill(Decimal('77.00'), 1) == [Decimal('77.00')] and split_bill(Decimal('0.00'), 2) == [Decimal('0.00')] * 2\n\n"
                "@pytest.mark.parametrize('people', [0, 101])\ndef test_people(people):\n    with pytest.raises(ValueError, match='people'):\n        split_bill(Decimal('1.00'), people)\n\n"
                "@pytest.mark.parametrize('amount', ['-0.01', '0.001', '1000000.00'])\ndef test_amount(amount):\n    with pytest.raises(ValueError, match='amount'):\n        split_bill(Decimal(amount), 2)\n",
    "idempotent": "@pytest.mark.parametrize('text', [' ab  12 ', 'ab_12', 'ab--12', 'AB-12', 'ab\\t12', 'ab----12', '-ab 12_'])\ndef test_one_spelling(text):\n    assert normalize_sku(text) == 'AB-12'\n\n"
                  "def test_a_normalized_number_stays():\n    assert normalize_sku(normalize_sku(' ab  12 ')) == 'AB-12'\n\n"
                  "@pytest.mark.parametrize('text', ['', ' - _ '])\ndef test_nothing_there(text):\n    with pytest.raises(ValueError, match='no article number'):\n        normalize_sku(text)\n",
    "bound": "S = Shelf('W-1', 5, 0)\n\ndef test_hold_then_release():\n    held = hold(S, 3)\n    assert (held.on_hand, held.held) == (2, 3)\n    back = release(held, 2)\n    assert (back.on_hand, back.held) == (4, 1) and S == Shelf('W-1', 5, 0)\n\n"
             "def test_too_many_to_hold():\n    with pytest.raises(ValueError, match='on hand'):\n        hold(S, 6)\n\n"
             "def test_too_many_to_release():\n    with pytest.raises(ValueError, match='held'):\n        release(Shelf('W-1', 2, 3), 4)\n\n"
             "@pytest.mark.parametrize('call', [hold, release])\ndef test_quantity(call):\n    with pytest.raises(ValueError, match='quantity must be positive'):\n        call(Shelf('W-1', 2, 3), 0)\n",
    "none": "def test_value():\n    assert shelf_value(StockItem('W-1', Decimal('2.50'), 4)) == Decimal('10.00')\n\n"
            "def test_empty():\n    assert shelf_value(StockItem('W-1', Decimal('2.50'), 0)) == Decimal('0.00')\n",
}
# One example on the input the contract does not list: red on the wrong implementation only.
TRAP = {
    "roundtrip": "def test_a_million():\n    assert parse_price(format_price(Decimal('1234567.89'))) == Decimal('1234567.89')\n",
    "conserve": "def test_a_share_that_rounds_up():\n    assert sum(split_bill(Decimal('200.00'), 3)) == Decimal('200.00')\n",
    "idempotent": "def test_two_kinds_in_a_row():\n    once = normalize_sku('ab - 12')\n    assert normalize_sku(once) == once\n",
    "bound": "def test_release_with_nothing_held():\n    with pytest.raises(ValueError, match='held'):\n        release(Shelf('W-1', 5, 0), 2)\n",
}
# The invariant as a property test over the contract's domain.
PROPERTY = {
    "roundtrip": "@given(st.decimals(min_value=0, max_value=Decimal('9999999.99'), places=2))\ndef test_I1_there_and_back(price):\n    assert parse_price(format_price(price)) == price\n",
    "conserve": "@given(st.integers(0, 99_999_999), st.integers(1, 100))\ndef test_I1_adds_up(cents, people):\n    amount = Decimal(cents) / 100\n    assert sum(split_bill(amount, people)) == amount\n",
    "idempotent": "@given(st.text(alphabet='abcXYZ019 \\t-_', min_size=1).filter(lambda t: any(c.isalnum() for c in t)))\ndef test_I1_twice_is_once(text):\n    once = normalize_sku(text)\n    assert normalize_sku(once) == once\n",
    "bound": "@given(st.integers(0, 20), st.integers(0, 20), st.lists(st.tuples(st.sampled_from([hold, release]), st.integers())))\ndef test_I1_never_negative(on_hand, held, calls):\n"
             "    shelf = Shelf('W-1', on_hand, held)\n    for call, quantity in calls:\n        try:\n            shelf = call(shelf, quantity)\n        except ValueError:\n            pass\n        assert shelf.on_hand >= 0 and shelf.held >= 0\n",
}

print("board 078: no leave for the sessions; arm C alone is allowed the library")
with tempfile.TemporaryDirectory() as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    (tasks / "doing/063-x.md").write_text("# 063\n\nАудит потрібен: ні\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDECODE": "1"}
    shim = Path(tmp) / "claude"
    shim.write_text(f"#!/bin/sh\necho started >> {tmp}/started\n", encoding="utf-8")
    shim.chmod(0o755)
    base = [sys.executable, str(RUNNER), "--set", "property", "--tasks-dir", str(tasks), "--claude", str(shim)]
    r = subprocess.run([*base, "--max-usd", "0.1"], capture_output=True, text=True, env=env, check=False)
    check("board 078: a task with no line is not refused — only the run's own ceiling stops it: under one run, nothing starts",
          "refusing" not in r.stderr and "cost limit" in r.stdout and not (Path(tmp) / "started").exists(), r.stdout + r.stderr)
    ready = Path(tmp) / "ready.py"
    ready.write_text(HEAD["conserve"] + OBVIOUS["conserve"] + "\n" + TRAP["conserve"], encoding="utf-8")
    shim.write_text(f"#!/bin/sh\necho \"$*\" | tr '\\n' ' ' >> {tmp}/argv; echo >> {tmp}/argv\ngrep -c Invariants .engine/slices/split-bill.md >> {tmp}/sections\n"
                    f"cp {ready} tests/test_split_bill_contract.py\necho '{{\"total_cost_usd\": 0.2, \"result\": \"done\"}}'\n", encoding="utf-8")
    out = Path(tmp) / "out.json"
    r = subprocess.run([*base, "--scenes", "conserve", "--repeat", "2", "--out", str(out)], capture_output=True, text=True, env=env, check=False)
    recorded = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    argv = (Path(tmp) / "argv").read_text(encoding="utf-8").splitlines() if (Path(tmp) / "argv").is_file() else []
    check("six sessions for one scene, three arms, two repeats — each scored «caught», recorded as the property set",
          r.returncode == 0 and len(argv) == 6 and r.stdout.count(": caught") == 6 and recorded.get("set") == "property"
          and recorded["summary"]["caught"] == {"a": "2 of 2", "b": "2 of 2", "c": "2 of 2"} and recorded["summary"]["cost_usd"] == 1.2
          and recorded["runs"][0]["tests"].startswith("import pytest") and recorded["runs"][0]["test_count"] == 9, r.stdout + r.stderr)
    check("arms A and B may run pytest only; arm C the command that brings Hypothesis",
          len(argv) == 6 and all(f"Bash(uvx --with {PYTEST} pytest:*)" in line for line in argv[:4]) and all(f"Bash(uvx --with {PYTEST} --with {HYPOTHESIS} pytest:*)" in line for line in argv[4:]), argv)
    check("the contract arm A was given has no «Invariants» section; B and C have it",
          (Path(tmp) / "sections").read_text(encoding="utf-8").split() == ["0", "0", "1", "1", "1", "1"], (Path(tmp) / "sections").read_text(encoding="utf-8"))
    r = subprocess.run([*base, "--scenes", "boundary"], capture_output=True, text=True, env=env, check=False)
    check("a scene of the other set is refused by name", r.returncode == 2 and "not a scene of the set «property»: boundary" in r.stderr, r.stderr)
    r = subprocess.run([sys.executable, str(RUNNER), "--table", str(out)], capture_output=True, text=True, check=False)
    check("--table prints scene × arm × repeat of a recording, free", r.returncode == 0 and "| `conserve` | 1. caught (9 tests, trap calls 1)<br>2. caught" in r.stdout and '"reached_the_trap": "2 of 2"' in r.stdout, r.stdout + r.stderr)

    out.write_text(json.dumps(recorded | {"runs": [recorded["runs"][0], recorded["runs"][2] | {"outcome": "missed", "caught": False}, {"scene": "none", "arm": "a", "cost_usd": 0.0, "error": "x"}]}), encoding="utf-8")
    again = Path(tmp) / "again.json"
    r = subprocess.run([sys.executable, str(RUNNER), "--rescore", str(out), "--out", str(again)], capture_output=True, text=True, check=False)
    counted = json.loads(again.read_text(encoding="utf-8")) if again.is_file() else {}
    check("--rescore counts the kept test files again, free: a recorded outcome that does not hold is named, an error row stays an error",
          r.returncode == 1 and "out.json run 2 (conserve/b): missed -> caught" in r.stdout and len(counted.get("outcomes_moved", [])) == 1
          and [row.get("outcome") for row in counted["runs"]] == ["caught", "caught", None] and counted["runs"][0]["fails_only_on_wrong"] == 1 and counted["runs"][0]["cost_usd"] == 0.2, r.stdout + r.stderr)

print("the scenes are what they claim")
work = Path(tempfile.mkdtemp(prefix="engine-tester-propertytest-"))
for name in TRAPS:
    scene = scenes[name]
    obvious, trap = evals.score_property(HEAD[name] + OBVIOUS[name], name, scene, "a", work), evals.score_property(HEAD[name] + OBVIOUS[name] + "\n" + TRAP[name], name, scene, "a", work)
    check(f"{name}: the wrong implementation passes every example of the contract, and no call of them reaches the trap", obvious["outcome"] == "missed" and obvious["trap_calls"] == 0 and obvious["calls"] > 0, obvious)
    check(f"{name}: …and fails on the trap's input, where the right one passes", trap["outcome"] == "caught" and trap["trap_calls"] >= 1 and "1 failed" in trap["observed"] and not trap["invariant_test_red"], trap)
    red = evals.run_suite(HEAD[name] + OBVIOUS[name] + "\n" + TRAP[name], name, scene, "skeleton", work)
    check(f"{name}: against the skeleton every test is red", not red["passed"] and "passed" not in red["last_line"], red)
    for example in [line.split("`")[1] for line in [scene["trap_input"]] if "`" in line]:
        check(f"{name}: the contract does not list the trap's input {example}", example not in evals.contract_text(name, scene, True))
for name in evals.PROPERTY_SCENES:
    scene = scenes[name]
    skeleton = evals.scene_file(name, scene, "skeleton.py").read_text(encoding="utf-8")
    check(f"{name}: the skeleton has every function of the slice and no body",
          all(skeleton.split(f"def {f}(")[1].split("\ndef ")[0].rstrip().endswith("raise NotImplementedError") for f in scene["functions"]) and skeleton.count("NotImplementedError") == len(scene["functions"]))
check("the control has no wrong implementation", not evals.scene_file("none", scenes["none"], "wrong.py").exists() and "wrong_does" not in scenes["none"])

print("the two contracts of a scene differ by the section alone")
for name in evals.PROPERTY_SCENES:
    scene = scenes[name]
    without, with_it, section = evals.contract_text(name, scene), evals.contract_text(name, scene, True), evals.scene_file(name, scene, "invariants.md").read_text(encoding="utf-8")
    check(f"{name}: with the section taken out the two are the same text, and the section stands before «Exit criterion»",
          with_it.replace(section + "\n", "") == without and section + "\n## Exit criterion" in with_it and "nvariant" not in without)
    fields = all(f"  - {field}: " in section for field in ("Domain", "Source", "Broken by")) and "  - Check: generative." in section and "**I1**" in section
    check(f"{name}: the section " + ("says «None» with the reason" if name == "none" else "has one invariant with its four fields, checked generatively"),
          section.splitlines()[1].startswith("None — ") and "**I" not in section if name == "none" else fields, section)

print("the count: on ready-made suites, the refusals first")
name, scene = "conserve", scenes["conserve"]
check("no file is «no tests»", evals.score_property(None, name, scene, "c", work)["outcome"] == "no_tests")
got = evals.score_property(HEAD[name] + GIVEN + PROPERTY[name], name, scene, "b", work)
check("a property test where there is no library fails on both: not caught", got["outcome"] == "fails_on_both" and not got["caught"] and got["uses_library"], got)
got = evals.score_property(HEAD[name] + GIVEN + OBVIOUS[name], name, scene, "c", work)
check("arm C, examples only: «missed», no call reached the trap, no seed of the search finds it", got["outcome"] == "missed" and got["trap_calls"] == 0 and got["search"] == "0 of 5", got)
narrowed = PROPERTY[name].replace("st.integers(1, 100)", "st.just(1)")
got = evals.score_property(HEAD[name] + GIVEN + narrowed, name, scene, "c", work)
check("arm C, a generator narrowed to one guest: «missed», the trap never reached — and the generator's lines are kept for the reader",
      got["outcome"] == "missed" and got["trap_calls"] == 0 and got["search"] == "0 of 5" and any("st.just(1)" in line for line in got["generator"]), got)
blind = PROPERTY[name].replace("assert sum(split_bill(amount, people)) == amount", "assert len(split_bill(amount, people)) == people")
got = evals.score_property(HEAD[name] + GIVEN + blind, name, scene, "c", work)
check("arm C, the trap reached by the generator and not noticed by the assertion: «missed» with trap calls", got["outcome"] == "missed" and got["trap_calls"] > 0, got)
got = evals.score_property(HEAD[name] + GIVEN + TRAP[name] + "\n" + narrowed, name, scene, "c", work)
check("arm C, an example on the trap beside a narrowed generator: «caught» on every seed — by the example, and the invariant's own test on none",
      got["outcome"] == "caught" and not got["invariant_test_red"] and got["search"] == "5 of 5" and got["property_search"] == "0 of 5"
      and "search 5 of 5, the invariant's test 0 of 5" in evals.table([got | {"scene": name, "arm": "c"}]), got)
quiet = PROPERTY[name].replace("@given", "@settings(suppress_health_check=[HealthCheck.filter_too_much])\n@given")
got = evals.score_property(HEAD[name] + GIVEN + quiet, name, scene, "c", work)
check("suppressed health checks are named in the row", got["health_checks_suppressed"] and "HEALTH CHECKS SUPPRESSED" in evals.shown(got), got)
for name in TRAPS:
    scene = scenes[name]
    got = evals.score_property(HEAD[name] + GIVEN + OBVIOUS[name] + "\n" + PROPERTY[name], name, scene, "c", work)
    check(f"{name}: the invariant as a property test over the contract's domain is «caught», and the search finds it on other seeds",
          got["outcome"] == "caught" and got["invariant_tests"] and got["invariant_test_red"] and not got["health_checks_suppressed"] and got["trap_calls"] > 0 and got["search"] != "0 of 5" and got["property_search"] == got["search"], got)
    if name == "conserve":   # the seed is fixed: a second count is the same count
        again = evals.score_property(HEAD[name] + GIVEN + OBVIOUS[name] + "\n" + PROPERTY[name], name, scene, "c", work)
        same = [(row["outcome"], row["test_count"], row["calls"], row["trap_calls"], row["search"]) for row in (got, again)]
        check("the count of a property test is the same on a second count: outcome, calls, calls that reached the trap", same[0] == same[1], same)
name, scene = "none", scenes["none"]
got = evals.score_property(HEAD[name] + OBVIOUS[name] + "\ndef test_strict():\n    assert str(shelf_value(StockItem('W-1', Decimal('2.5'), 2))) == '5.0'\n", name, scene, "b", work)
check("the control: a suite that fails on the right implementation is «fails on right»", got["outcome"] == "fails_on_right" and not got["invented_invariant"], got)
got = evals.score_property(HEAD[name] + OBVIOUS[name] + "\ndef test_I1_never_negative():\n    assert shelf_value(StockItem('W-1', Decimal('2.50'), 1)) >= 0\n", name, scene, "b", work)
check("the control: a test named for an invariant the contract does not have is an invented invariant", got["outcome"] == "clean" and got["invented_invariant"] and "INVENTED INVARIANT" in evals.shown(got), got)
got = evals.score_property(HEAD[name] + GIVEN + OBVIOUS[name] + "\n@given(st.integers(0, 9))\ndef test_grows(n):\n    assert shelf_value(StockItem('W-1', Decimal('2.50'), n)) >= 0\n", name, scene, "c", work)
check("the control: a property test where the contract names no invariant is an invented invariant too", got["outcome"] == "clean" and got["invented_invariant"], got)
got = evals.score_property(HEAD[name] + OBVIOUS[name], name, scene, "c", work)
check("the control: the contract's two cases and nothing else is «clean»", got["outcome"] == "clean" and not got["invented_invariant"] and got["test_count"] == 2 and "trap_calls" not in got, got)
name, scene = "roundtrip", scenes["roundtrip"]
stricter = "\ndef test_no_leading_zero():\n    with pytest.raises(ValueError):\n        parse_price('012.50')\n"
got = evals.score_property(HEAD[name] + OBVIOUS[name] + "\n" + TRAP[name] + stricter, name, scene, "a", work)
check("a suite that tests the trap and also reads the contract more strictly than the right implementation: «fails on both», with one test red on the wrong one only",
      got["outcome"] == "fails_on_both" and not got["caught"] and got["fails_only_on_wrong"] == 1 and "red on the wrong one only 1" in evals.table([got | {"scene": name, "arm": "a"}]), got)
check("no scratch project is left behind by the scoring", not any(work.iterdir()), list(work.iterdir()))
shutil.rmtree(work)

rows = [{"scene": "conserve", "arm": "a", "cost_usd": 0.1, "outcome": "missed", "caught": False, "test_count": 5, "trap_calls": 0},
        {"scene": "conserve", "arm": "c", "cost_usd": 0.3, "outcome": "caught", "caught": True, "test_count": 6, "trap_calls": 40, "search": "5 of 5"},
        {"scene": "conserve", "arm": "c", "cost_usd": 0.2, "outcome": "fails_on_both", "caught": False, "test_count": 6, "trap_calls": 3, "search": "5 of 5"},
        {"scene": "none", "arm": "a", "cost_usd": 0.1, "outcome": "clean", "caught": False, "test_count": 2, "invented_invariant": False},
        {"scene": "none", "arm": "c", "cost_usd": 0.1, "outcome": "clean", "caught": False, "test_count": 3, "invented_invariant": True},
        {"scene": "none", "arm": "c", "cost_usd": 0.0, "error": "x"}]
got = evals.summary(rows)
check("the summary keeps the control out of the catch and counts each arm's tests, cost, «fails on both» and clean controls",
      got["caught"] == {"a": "0 of 1", "c": "1 of 2"} and got["by_arm"]["c"] == {"fails_on_both": 1, "reached_the_trap": "2 of 2", "control_clean": "0 of 2", "tests": 15, "cost_usd": 0.6}
      and got["by_arm"]["a"]["control_clean"] == "1 of 1" and got["table"]["none/c#2"] == "error", got)
check("the table has a row a scene and a numbered line a repeat",
      "| `conserve` | 1. missed (5 tests, trap calls 0) | 1. caught (6 tests, trap calls 40, search 5 of 5)<br>2. fails_on_both (6 tests, trap calls 3, search 5 of 5) |" in evals.table(rows)
      and "| `none` | 1. clean (2 tests, trap calls —) | 1. clean; INVENTED INVARIANT (3 tests, trap calls —)<br>2. error |" in evals.table(rows), evals.table(rows))

print("the arms and the dry run")
with tempfile.TemporaryDirectory() as tmp:
    dry = Path(tmp) / "dry"
    r = subprocess.run([sys.executable, str(RUNNER), "--set", "property", "--dry-run", str(dry)], capture_output=True, text=True, check=False)
    check("the dry run builds fifteen sandboxes and fifteen prompts", r.returncode == 0 and len(list(dry.glob("prompt-*.txt"))) == 15, r.stdout + r.stderr)
    for name in evals.PROPERTY_SCENES:
        scene = scenes[name]
        seen = {arm: (dry / f"{name}-{arm}" / evals.module_path(scene)).read_text(encoding="utf-8") for arm in "abc"}
        contracts = {arm: (dry / f"{name}-{arm}/.engine/slices/{scene['slug']}.md").read_text(encoding="utf-8") for arm in "abc"}
        check(f"{name}: every arm sees the skeleton; arm A's contract has no «Invariants» section, B and C have the same one",
              all(text == evals.scene_file(name, scene, "skeleton.py").read_text(encoding="utf-8") for text in seen.values())
              and "nvariant" not in contracts["a"] and "## Invariants" in contracts["b"] and contracts["b"] == contracts["c"])
        check(f"{name}: no sandbox has the slice's tests, a wrong or right module beside it, or the library",
              all(not (dry / f"{name}-{arm}" / evals.test_path(scene)).exists() and "hypothesis" not in (dry / f"{name}-{arm}/pyproject.toml").read_text(encoding="utf-8")
                  and not list((dry / f"{name}-{arm}").rglob("wrong*")) and not list((dry / f"{name}-{arm}").rglob("right*")) for arm in "abc"))
    a, b, c = ((dry / f"prompt-conserve-{arm}.txt").read_text(encoding="utf-8") for arm in "abc")
    b_rules, c_rules = ((evals.PROPERTY / f"arm-{arm}-invariants.md").read_text(encoding="utf-8") for arm in "bc")
    check("arm A's prompt says nothing of invariants or a library", "nvariant" not in a and "ypothesis" not in a and "property" not in a.replace("property-", ""), a)
    check("arm B's prompt is arm A's plus its paragraph: a test per invariant, by examples, no library", b.replace(b_rules, "") == a and "no\n  property-based testing library" in b and "ypothesis" not in b, b)
    check("arm C's prompt is arm A's plus its paragraph and the run command that brings Hypothesis",
          c.replace(c_rules, "").replace(f"--with {HYPOTHESIS} ", "") == a and "you do not narrow it" in c and "suppress the library's health checks" in c
          and f"uvx --with {PYTEST} --with {HYPOTHESIS} pytest -q -p no:cacheprovider tests/test_split_bill_contract.py" in c)
    check("no prompt has an unfilled field or names a trap", not any(word in p for p in (a, b, c) for word in ("{", "trap", "wrong", "200.00", "rounds up")))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
