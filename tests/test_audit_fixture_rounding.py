#!/usr/bin/env python3
"""The audit fixtures' rounding tests pin ROUND_HALF_UP — checked without a model (board 002).

The release audit found the "clean" tree of scenes 01 and 10 was not clean: every row of the
`with_tax` table was either exact or an exact half, so ROUND_UP (and ROUND_CEILING, ROUND_05UP)
passed all of it. The overseer said so in scene 10, and the expected PASS called it wrong.

  1. in every scene's working tree the fixture's own tests are green as written, and at least
     one goes red under EVERY other rounding mode of `decimal`;
  2. scene 05 is the exception by design — its defect is the weak test — and there the swap
     stays green: the same instrument sees a hole where one is meant to be;
  3. a recorded turn that lists the table's rows lists the rows the tree really has.

The fixture's tests are run in-process against a stand-in for the two pytest features they use
(`mark.parametrize`, `raises`): pytest is not installed here, and the question is about the
assertions, not the runner.
Run:   python3 tests/test_audit_fixture_rounding.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import sys
import tempfile
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "evals" / "scenarios" / "audit"
CONTRACT_MODE = "ROUND_HALF_UP"
OTHER_MODES = ("ROUND_UP", "ROUND_CEILING", "ROUND_05UP", "ROUND_DOWN", "ROUND_FLOOR", "ROUND_HALF_DOWN", "ROUND_HALF_EVEN")
WEAK_BY_DESIGN = ("05-masked-test-gap", "12-reaudit-after-weak-fix")   # 12: the "fix" of 05's test, as weak (board 018)
ROW_LINE = re.compile(r"test_with_tax_rounds_half_up\[([^\]]+)\] PASSED")
PASS = FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def pytest_stand_in() -> types.ModuleType:
    def parametrize(names: tuple[str, ...], rows: list[tuple[Any, ...]]) -> Callable[[Any], Any]:
        def mark(fn: Any) -> Any:
            fn.rows = [dict(zip(names, row, strict=True)) for row in rows]
            return fn
        return mark

    @contextlib.contextmanager
    def raises(kind: type[BaseException], match: str = "") -> Iterator[None]:
        try:
            yield
        except kind as err:
            assert re.search(match, str(err)), f"{err!r} does not match {match!r}"
        else:
            raise AssertionError(f"{kind.__name__} not raised")

    module = types.ModuleType("pytest")
    setattr(module, "mark", types.SimpleNamespace(parametrize=parametrize))
    setattr(module, "raises", raises)
    return module


def run_fixture_tests(tree: Path, mode: str) -> dict[str, bool]:
    """Every test of the tree's tests/test_pricing.py, by pytest id, with pricing rounding by `mode`."""
    # Only `with_tax` is swapped: the module's older functions round too, and their tests going
    # red would hide whether the slice's own table notices. A mode of `decimal` is its name.
    head, cut, body = (tree / "src" / "refproj" / "pricing.py").read_text(encoding="utf-8").partition("def with_tax(")
    if CONTRACT_MODE not in body:
        raise SystemExit(f"{tree}: with_tax does not name {CONTRACT_MODE}; the swap would change nothing")
    pricing = types.ModuleType("refproj.pricing")
    exec(compile(head + cut + body.replace(CONTRACT_MODE, repr(mode)), "pricing.py", "exec"), pricing.__dict__)
    saved = {name: sys.modules.get(name) for name in ("pytest", "refproj", "refproj.pricing")}
    sys.modules.update({"pytest": pytest_stand_in(), "refproj": types.ModuleType("refproj"), "refproj.pricing": pricing})
    try:
        tests: dict[str, Any] = {}
        exec(compile((tree / "tests" / "test_pricing.py").read_text(encoding="utf-8"), "test_pricing.py", "exec"), tests)
    finally:
        for name, module in saved.items():
            if module is None:
                del sys.modules[name]
            else:
                sys.modules[name] = module
    results: dict[str, bool] = {}
    for name, fn in tests.items():
        if not name.startswith("test_"):
            continue
        for row in getattr(fn, "rows", [{}]):
            test_id = name + (f"[{'-'.join(str(v) for v in row.values())}]" if row else "")
            try:
                fn(**row)
                results[test_id] = True
            except Exception:  # a red test, whatever it raised
                results[test_id] = False
    return results


def red(results: dict[str, bool]) -> list[str]:
    return [test_id for test_id, ok in results.items() if not ok]


expected = json.loads((AUDIT / "expected.json").read_text(encoding="utf-8"))
work = Path(tempfile.mkdtemp(prefix="engine-rounding-"))

try:
    for scene in sorted(expected):
        print(scene)
        tree = work / scene
        for overlay in expected[scene].get("overlays", []):
            shutil.copytree(AUDIT / "work" / overlay, tree, dirs_exist_ok=True)
        as_written = run_fixture_tests(tree, CONTRACT_MODE)
        check("the fixture's tests are green as written", as_written != {} and red(as_written) == [], red(as_written))
        survivors = [mode for mode in OTHER_MODES if red(run_fixture_tests(tree, mode)) == []]
        if scene in WEAK_BY_DESIGN:
            check("the weak test stays green under ROUND_UP — the hole this scene is about", "ROUND_UP" in survivors, survivors)
            continue
        check("ROUND_UP in place of ROUND_HALF_UP turns a test red", "ROUND_UP" not in survivors, "all green under ROUND_UP")
        check("so does every other rounding mode", survivors == [], survivors)

        text = (AUDIT / f"{scene}.md").read_text(encoding="utf-8")
        listed = ROW_LINE.findall(text)
        if listed:
            rows = [i.split("[", 1)[1][:-1] for i in as_written if i.startswith("test_with_tax_rounds_half_up[")]
            check("the recorded turn lists the rows the tree has", listed == rows, (listed, rows))
            count = re.search(r"(\d+) passed", text)
            check("...and counts the tests it lists", count is not None and int(count.group(1)) == text.count(" PASSED"), count)
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
print(f"PASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
