#!/usr/bin/env python3
"""The planted-bug experiment: does a tester who never saw the code catch what its author misses (boards 061, 713)?

    python3 evals/run_tester_evals.py [--out FILE] [--scenes boundary …] [--arms c] [--repeat 3] [--max-usd 10]   # PAID: real sessions
    python3 evals/run_tester_evals.py --dry-run DIR                                        # free: the sandboxes and the prompts
    python3 evals/run_tester_evals.py --score FILE --scene boundary                        # free: score a ready test file

Four scenes on the reference project (evals/scenarios/tester/scenes/). Each is a slice contract
in the /plan-slice format with one trap — a line that is natural to read the wrong way — a
skeleton without bodies, an implementation that breaks exactly that line, and a right one.

    boundary   a bound that is inclusive            rounding   a rounding rule unlike the module's
    empty      an empty input that is an error      order      which check wins when two apply

Three arms; every agent writes its tests to one named file:

    a  as today    sees the contract and the WRONG implementation (the builder tests its own code)
    b  the tester  sees the contract and the skeleton only; its prompt is the draft of the
                   tester's definition (design of board 060, section 2), kept in the fixture
    c  the real builder (board 713)  sees the contract and the skeleton and writes BOTH the
                   implementation and the tests: the misreading, if any, is its own

THE SCRIPT COUNTS, not a model. The file the agent wrote is run against both implementations:

    caught          fails on the wrong one, passes on the right one
    missed          passes on both
    fails_on_both   fails on both: it proved nothing, and is a line of its own
    mirrors_bug     passes on the wrong one, fails on the right one: the tests copied the bug
    no_tests        the file is not there, or holds no test

In arm C the script also judges the code the agent wrote, with the scene's hidden
reference_tests.py (the contract's lines; the trap's is the test named in expected.json):

    right     every reference test passes        trapped   only the trap's test fails
    broken    another reference test fails       none      the module is still the skeleton

and runs the agent's tests on the agent's code. `self_deceived` — trapped code under its own
green tests — is the case a blind tester exists for.

Nothing is tuned to the result: a scene that did not go as hoped is recorded as it is. Eight
runs show a coarse difference between the arms, not a fine one.

PAID RUNS. As in run_analyst_evals.py: sessions start only when the task in tasks/doing/ has the
owner's «Платні прогони: так» line, or the owner runs this by hand with --owner-approved (which
does not count inside a Claude Code session). No dollar number is required; one in that line, or
--max-usd, is a ceiling (the smaller of the two) the runs stop before.

THE PROPERTY SET (board 063, the spike of the design of board 048): `--set property`.

    python3 evals/run_tester_evals.py --set property [--out FILE] [--scenes …] [--arms c] [--repeat 3]    # PAID
    python3 evals/run_tester_evals.py --set property --dry-run DIR                                       # free
    python3 evals/run_tester_evals.py --set property --score FILE --scene conserve --arm c               # free
    python3 evals/run_tester_evals.py --table FILE [FILE …]                                              # free: scene × arm × repeat
    python3 evals/run_tester_evals.py --rescore FILE [FILE …] [--out FILE]                               # free: count the kept test files again

Do an «Invariants» section in the slice contract and a property-based testing library catch more
than examples? Five scenes (evals/scenarios/tester-property/scenes/), one per form of rule and a
control. The trap here is not a line of the contract but AN INPUT THE CONTRACT DOES NOT LIST,
though its rule covers it; the wrong implementation passes every example the contract gives.

    roundtrip    a printed price reads back the same     conserve   the shares add up to the bill
    idempotent   normalizing twice is normalizing once   bound      nothing on the shelf goes negative
    none         the control: a thin wrapper, no invariant

Three arms, the same tester prompt (arm-tester.md), the contract and the skeleton; only tests are written:

    a  the contract without the «Invariants» section; example tests
    b  the contract with the section; example tests — there is no library
    c  the contract with the section; Hypothesis, brought by `uvx` (nothing is installed)

The two contracts of a scene differ by the section alone: contract.md, and invariants.md put in
before «Exit criterion». The script counts as above; arm C is run with `--hypothesis-seed=0`, so
the count is the same every time. It also records, per run: the number of tests; `trap_calls` —
calls of the slice's functions on which the wrong implementation differs from the right one
(the suite REACHED the trap, caught or not); `fails_only_on_wrong` — tests red on the wrong
implementation and green on the right one, which says what a «fails on both» suite did to the trap;
`invariant_test_red` — one of them is the test named for an invariant (`test_I…`), not a neighbouring example; in arm C `search` — on how many of five other
seeds the suite fails on the wrong implementation — and `property_search` — on how many of them
the invariant's own test is red (an example beside it fails on every seed) — the lines of the file that make the
generator, and whether health checks are suppressed. The control has no wrong implementation:
`clean` or `fails_on_right`, and `invented_invariant` (a `test_I…` or the library in the file).

Standard library only, Python 3.12+; the scoring runs pytest through `uvx`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # a suite may load this file by path
import environment
import run_analyst_evals as analyst

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURE = HERE / "scenarios" / "tester"
REFERENCE = HERE / "reference-project"
SCENES = ("boundary", "rounding", "empty", "order")
ARMS = {"a": ("wrong", "arm-a-builder.md"), "b": ("skeleton", "arm-b-tester-draft.md"), "c": ("skeleton", "arm-c-builder-real.md")}
WRITES_CODE = ("c",)
REFERENCE_TESTS = "tests/test_reference_of_the_scene.py"
PYTEST = ("uvx", "--with", "pytest", "pytest", "-q", "-p", "no:cacheprovider")
TOOLS = ("Read", "Grep", "Glob", "Write", "Edit", "Bash")
RUN_TIMEOUT_S = 900
PROPERTY = HERE / "scenarios" / "tester-property"
PROPERTY_SCENES = ("roundtrip", "conserve", "idempotent", "bound", "none")
# arm: (its contract has the «Invariants» section, the library is there, the paragraph its prompt gets)
PROPERTY_ARMS = {"a": (False, False, None), "b": (True, False, "arm-b-invariants.md"), "c": (True, True, "arm-c-invariants.md")}
HYPOTHESIS = ("uvx", "--with", "pytest", "--with", "hypothesis", "pytest", "-q", "-p", "no:cacheprovider")
SEED, SEARCH_SEEDS = 0, (1, 2, 3, 4, 5)
OUTCOMES = {(False, True): "caught", (True, True): "missed", (False, False): "fails_on_both", (True, False): "mirrors_bug"}

JsonObj = dict[str, Any]


def fixture(name: str) -> str:
    return (FIXTURE / name).read_text(encoding="utf-8")


def scenes_of(kind: str) -> JsonObj:
    """The scenes of a set; a scene of the property set is marked, and everything below asks the scene."""
    if kind == "property":
        return {name: entry | {"property": True} for name, entry in json.loads((PROPERTY / "expected.json").read_text(encoding="utf-8")).items()}
    return dict(json.loads(fixture("expected.json")))


def scene_file(name: str, scene: JsonObj, rel: str) -> Path:
    return (PROPERTY if scene.get("property") else FIXTURE) / "scenes" / name / rel


def contract_text(name: str, scene: JsonObj, invariants: bool = False) -> str:
    """The scene's contract; with `invariants`, the same text with the section put in before «Exit criterion»."""
    text = scene_file(name, scene, "contract.md").read_text(encoding="utf-8")
    if not invariants:
        return text
    head, mark, tail = text.partition("## Exit criterion")
    return head + scene_file(name, scene, "invariants.md").read_text(encoding="utf-8") + "\n" + mark + tail


def pytest_command(scene: JsonObj, arm: str) -> tuple[str, ...]:
    return HYPOTHESIS if scene.get("property") and PROPERTY_ARMS[arm][1] else PYTEST


def test_path(scene: JsonObj) -> str:
    return f"tests/test_{scene['slug'].replace('-', '_')}_contract.py"


def module_path(scene: JsonObj) -> str:
    return f"src/refproj/{scene['module']}.py"


# ------------------------------------------------------------------ sandboxes and prompts


def build_sandbox(target: Path, name: str, scene: JsonObj, implementation: str, invariants: bool = False) -> Path:
    """The reference project with the slice's contract and one of its three modules: skeleton, wrong, right."""
    tracked = subprocess.run(["git", "-C", str(REFERENCE), "ls-files", "."], capture_output=True, text=True, check=True)
    for rel in tracked.stdout.splitlines():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REFERENCE / rel, target / rel)
    shutil.copy2(scene_file(name, scene, f"{implementation}.py"), target / module_path(scene))
    (target / ".engine/slices").mkdir(parents=True)
    (target / f".engine/slices/{scene['slug']}.md").write_text(contract_text(name, scene, invariants), encoding="utf-8")
    return target


def prompt(scene: JsonObj, arm: str) -> str:
    run = " ".join((*pytest_command(scene, arm), test_path(scene)))
    if scene.get("property"):
        rules = PROPERTY_ARMS[arm][2]
        return (PROPERTY / "arm-tester.md").read_text(encoding="utf-8").format(
            contract=f".engine/slices/{scene['slug']}.md", module_path=module_path(scene), functions=", ".join(f"`{f}`" for f in scene["functions"]),
            test_path=test_path(scene), run=run, invariants=(PROPERTY / rules).read_text(encoding="utf-8") if rules else "")
    return fixture(ARMS[arm][1]).format(contract=f".engine/slices/{scene['slug']}.md", module_path=module_path(scene),
                                        function=scene["function"], test_path=test_path(scene), run=run)


# ------------------------------------------------------------------ scoring (free, deterministic)


def pytest_verdict(project: Path, *selection: str, runner: tuple[str, ...] = PYTEST, env: dict[str, str] | None = None) -> JsonObj:
    proc = subprocess.run([*runner, *selection], cwd=project, capture_output=True, text=True, check=False, env=env)
    lines = proc.stdout.strip().splitlines()
    return {"passed": proc.returncode == 0, "empty": proc.returncode == 5, "last_line": lines[-1] if lines else proc.stderr.strip()[-200:],
            "failed": sorted({line[7:].split(" - ")[0] for line in lines if line.startswith("FAILED ")})}


def run_suite(tests: str, name: str, scene: JsonObj, implementation: str, work: Path, runner: tuple[str, ...] = PYTEST) -> JsonObj:
    """pytest's verdict on `tests` against one implementation: passed, and whether anything was collected."""
    project = build_sandbox(work / f"{name}-{implementation}", name, scene, implementation)
    (project / test_path(scene)).write_text(tests, encoding="utf-8")
    verdict = pytest_verdict(project, test_path(scene), runner=runner)
    shutil.rmtree(project)
    return verdict


def trap_calls(tests: str, name: str, scene: JsonObj, work: Path, runner: tuple[str, ...]) -> JsonObj:
    """How many calls of the slice's functions the suite makes, and on how many the wrong implementation differs."""
    project = build_sandbox(work / f"{name}-watched", name, scene, "right")
    with (project / module_path(scene)).open("a", encoding="utf-8") as module:
        module.write((PROPERTY / "watch.py").read_text(encoding="utf-8"))
    (project / test_path(scene)).write_text(tests, encoding="utf-8")
    log = work / f"{name}-calls.log"
    log.write_text("", encoding="utf-8")
    watch = {"SCENE_WRONG": str(scene_file(name, scene, "wrong.py")), "SCENE_WATCH": ",".join(scene["functions"]), "SCENE_LOG": str(log)}
    pytest_verdict(project, test_path(scene), runner=runner, env=os.environ | watch)
    lines = log.read_text(encoding="utf-8").split()
    shutil.rmtree(project)
    log.unlink()
    return {"calls": len(lines), "trap_calls": lines.count("trap")}


def score_property(tests: str | None, name: str, scene: JsonObj, arm: str, work: Path) -> JsonObj:
    """The property set's count: as `score`, with the library's seed fixed, and the facts the spike asks for."""
    if tests is None:
        return {"outcome": "no_tests", "caught": False, "observed": "the test file was not written"}
    library = PROPERTY_ARMS[arm][1]
    runner = (*HYPOTHESIS, f"--hypothesis-seed={SEED}") if library else PYTEST
    right = run_suite(tests, name, scene, "right", work, runner)
    facts: JsonObj = {"test_count": sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|errors?)\b", right["last_line"])),
                      "invariant_tests": re.findall(r"^def (test_I\d\w*)", tests, re.M), "uses_library": "hypothesis" in tests}
    if library:
        facts |= {"health_checks_suppressed": "suppress_health_check" in tests,
                  "generator": [line.strip() for line in tests.splitlines() if re.search(r"\bst\.|strategies|@given|@settings|@example|assume\(|\.filter\(|\.map\(", line)]}
    if "wrong_does" not in scene:   # the control: there is no wrong implementation and no trap
        outcome = "no_tests" if right["empty"] else "clean" if right["passed"] else "fails_on_right"
        return {"outcome": outcome, "caught": False, "observed": f"right: {right['last_line']}",
                "invented_invariant": bool(facts["invariant_tests"]) or facts["uses_library"]} | facts
    wrong = run_suite(tests, name, scene, "wrong", work, runner)
    outcome = "no_tests" if wrong["empty"] or right["empty"] else OUTCOMES[(wrong["passed"], right["passed"])]
    row = {"outcome": outcome, "caught": outcome == "caught", "observed": f"wrong: {wrong['last_line']} | right: {right['last_line']}"} | facts
    only = set(wrong["failed"]) - set(right["failed"])
    row |= trap_calls(tests, name, scene, work, runner) | {"fails_only_on_wrong": len(only), "invariant_test_red": any("::test_I" in test for test in only)}
    if library:
        seeds = [run_suite(tests, name, scene, "wrong", work, (*HYPOTHESIS, f"--hypothesis-seed={seed}")) for seed in SEARCH_SEEDS]
        row["search"] = f"{sum(1 for verdict in seeds if not verdict['passed'])} of {len(seeds)}"
        row["property_search"] = f"{sum(1 for verdict in seeds if any('::test_I' in test for test in verdict['failed']))} of {len(seeds)}"
    return row


def judge_code(module: str, tests: str | None, name: str, scene: JsonObj, work: Path) -> JsonObj:
    """Arm C: is the module the agent wrote right, trapped or broken — and do its own tests pass on it?"""
    if module == fixture(f"scenes/{name}/skeleton.py"):
        return {"code": "none", "own_tests_green": False, "self_deceived": False, "code_observed": "the module is still the skeleton"}
    project = build_sandbox(work / f"{name}-written", name, scene, "skeleton")
    (project / module_path(scene)).write_text(module, encoding="utf-8")
    (project / REFERENCE_TESTS).write_text(fixture(f"scenes/{name}/reference_tests.py"), encoding="utf-8")
    around = pytest_verdict(project, REFERENCE_TESTS, "--deselect", f"{REFERENCE_TESTS}::{scene['trap_test']}")
    trap = pytest_verdict(project, f"{REFERENCE_TESTS}::{scene['trap_test']}")
    (project / REFERENCE_TESTS).unlink()
    own = None
    if tests is not None:
        (project / test_path(scene)).write_text(tests, encoding="utf-8")
        own = pytest_verdict(project, test_path(scene))
    shutil.rmtree(project)
    code = "broken" if not around["passed"] else "right" if trap["passed"] else "trapped"
    green = bool(own and own["passed"])
    return {"code": code, "own_tests_green": green, "self_deceived": code == "trapped" and green,
            "code_observed": f"reference: {around['last_line']} | trap: {trap['last_line']} | own tests on own code: {own['last_line'] if own else 'no tests'}"}


def score(tests: str | None, name: str, scene: JsonObj, work: Path) -> JsonObj:
    """The trap is caught when the suite fails on the wrong implementation and passes on the right one."""
    if tests is None:
        return {"outcome": "no_tests", "caught": False, "observed": "the test file was not written"}
    wrong, right = (run_suite(tests, name, scene, implementation, work) for implementation in ("wrong", "right"))
    outcome = "no_tests" if wrong["empty"] or right["empty"] else OUTCOMES[(wrong["passed"], right["passed"])]
    return {"outcome": outcome, "caught": outcome == "caught", "observed": f"wrong: {wrong['last_line']} | right: {right['last_line']}"}


def plan(scenes: list[str], arms: list[str] | None = None, repeat: int = 1) -> list[tuple[str, str]]:
    return [(scene, arm) for scene in scenes for arm in (arms or list(ARMS)) for _ in range(repeat)]


def shown(row: JsonObj) -> str:
    if "error" in row:
        return "error"
    notes = [f"code {row['code']}" + ("; SELF-DECEIVED" if row["self_deceived"] else "")] if "code" in row else []
    notes += ["INVENTED INVARIANT"] if row.get("invented_invariant") else []
    notes += ["HEALTH CHECKS SUPPRESSED"] if row.get("health_checks_suppressed") else []
    return "; ".join([row["outcome"], *notes])


def summary(runs: list[JsonObj]) -> JsonObj:
    table: JsonObj = {}
    for r in runs:   # a repeated scene and arm: order/c, order/c#2, …
        key, again = f"{r['scene']}/{r['arm']}", sum(1 for k in table if k.split("#")[0] == f"{r['scene']}/{r['arm']}")
        table[f"{key}#{again + 1}" if again else key] = shown(r)
    arms = [arm for arm in ARMS if any(r["arm"] == arm for r in runs)]
    caught = {arm: f"{sum(1 for r in runs if r['arm'] == arm and r.get('caught'))} of {sum(1 for r in runs if r['arm'] == arm)}" for arm in arms}
    result: JsonObj = {"runs": len(runs), "caught": caught, "cost_usd": round(sum(r["cost_usd"] for r in runs), 4), "table": table}
    control = [r for r in runs if r["scene"] == "none"]
    if any("test_count" in r for r in runs):   # the property set: the control is not a trap, and the arms are compared by more than the catch
        trapped = [r for r in runs if r["scene"] != "none"]
        result["caught"] = {arm: f"{sum(1 for r in trapped if r['arm'] == arm and r.get('caught'))} of {sum(1 for r in trapped if r['arm'] == arm)}" for arm in arms}
        result["by_arm"] = {arm: {
            "fails_on_both": sum(1 for r in trapped if r["arm"] == arm and r.get("outcome") == "fails_on_both"),
            "reached_the_trap": f"{sum(1 for r in trapped if r['arm'] == arm and r.get('trap_calls'))} of {sum(1 for r in trapped if r['arm'] == arm)}",
            "control_clean": f"{sum(1 for r in control if r['arm'] == arm and r.get('outcome') == 'clean' and not r['invented_invariant'])} of {sum(1 for r in control if r['arm'] == arm)}",
            "tests": sum(r.get("test_count", 0) for r in runs if r["arm"] == arm),
            "cost_usd": round(sum(r["cost_usd"] for r in runs if r["arm"] == arm), 4)} for arm in arms}
    written = [r for r in runs if "code" in r]
    if written:
        result["code_written"] = {kind: sum(1 for r in written if r["code"] == kind) for kind in ("right", "trapped", "broken", "none")}
        result["self_deceived"] = f"{sum(1 for r in written if r['self_deceived'])} of {len(written)}"
    return result


def table(runs: list[JsonObj]) -> str:
    """Scene × arm × repeat as a markdown table: what the report of a spike shows."""
    arms = [arm for arm in ARMS if any(r["arm"] == arm for r in runs)]
    lines = ["| scene | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for name in dict.fromkeys(r["scene"] for r in runs):
        cells = []
        for arm in arms:
            mine = [r for r in runs if r["scene"] == name and r["arm"] == arm]
            cells.append("<br>".join(f"{n}. {shown(r)}" + (f" ({r['test_count']} tests, trap calls {r.get('trap_calls', '—')}" + (f", search {r['search']}" if "search" in r else "") + (f", the invariant's test {r['property_search']}" if "property_search" in r else "") + (f", red on the wrong one only {r['fails_only_on_wrong']}" if r.get("outcome") == "fails_on_both" and "fails_only_on_wrong" in r else "") + ")" if "test_count" in r else "")
                                     for n, r in enumerate(mine, 1)))
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------ the paid part


def run_once(sandbox: Path, text: str, args: argparse.Namespace, runner: tuple[str, ...] = PYTEST) -> JsonObj:
    allowed = " ".join(runner).split(" -q")[0]   # uvx --with pytest pytest, or the same with the library
    command = [args.claude, "-p", text, "--tools", *TOOLS, "--permission-mode", "acceptEdits", "--allowedTools", f"Bash({allowed}:*)",
               "--output-format", "json", "--strict-mcp-config", "--max-budget-usd", str(args.max_usd_per_run)]
    command += ["--model", args.model] if args.model else []
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    try:
        proc = subprocess.run(command, cwd=sandbox, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, check=False,
                              env={**env, "CLAUDE_PROJECT_DIR": str(sandbox)}, stdin=subprocess.DEVNULL)
        payload = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"error": f"the session gave no result: {type(exc).__name__}", "cost_usd": 0.0}
    row: JsonObj = {"cost_usd": round(float(payload.get("total_cost_usd") or 0.0), 4),
                    "models": sorted((payload.get("modelUsage") or {}).keys()), "turns": payload.get("num_turns")}
    answer = str(payload.get("result") or "")
    if payload.get("is_error"):
        return row | {"error": f"the session ended in an error: {answer[:300]}"}
    return row | {"answer": answer}


def rescore(paths: list[Path], work: Path) -> tuple[list[JsonObj], list[str]]:
    """The runs of property-set recordings counted again from the test files they kept; and the rows whose outcome moved."""
    scenes, runs, moved = scenes_of("property"), [], []
    for path in paths:
        for n, run in enumerate(json.loads(path.read_text(encoding="utf-8"))["runs"], 1):
            fresh = dict(run) if "error" in run else {k: run[k] for k in ("scene", "arm", "sees", "cost_usd", "models", "turns", "answer", "tests", "touched_module") if k in run}
            fresh |= {} if "error" in run else score_property(run["tests"], run["scene"], scenes[run["scene"]], run["arm"], work)
            moved += [f"{path.name} run {n} ({run['scene']}/{run['arm']}): {run.get('outcome')} -> {fresh.get('outcome')}"] if fresh.get("outcome") != run.get("outcome") else []
            runs.append(fresh | {"recorded_in": path.name})
    return runs, moved


def sees(scene: JsonObj, arm: str) -> tuple[str, bool]:
    """The module an arm is given, and whether its contract has the «Invariants» section."""
    return ("skeleton", PROPERTY_ARMS[arm][0]) if scene.get("property") else (ARMS[arm][0], False)


def arm_says(kind: str, arm: str) -> str:
    if kind == "property":
        return ("the contract with the «Invariants» section" if PROPERTY_ARMS[arm][0] else "the contract without the «Invariants» section") + \
               ("; Hypothesis through uvx" if PROPERTY_ARMS[arm][1] else "; example tests, no library") + "; sees the skeleton, writes tests only"
    return f"sees the contract and the {ARMS[arm][0]} module" + ("; writes the implementation too" if arm in WRITES_CODE else "")


def one_run(name: str, arm: str, scene: JsonObj, work: Path, args: argparse.Namespace) -> JsonObj:
    """One session in its own sandbox, then the file it wrote scored against both implementations."""
    seen, invariants = sees(scene, arm)
    sandbox = work / f"{name}-{arm}"
    if sandbox.exists():   # --repeat: the same scene and arm again, in a fresh sandbox
        shutil.rmtree(sandbox)
    sandbox = build_sandbox(sandbox, name, scene, seen, invariants)
    row = {"scene": name, "arm": arm, "sees": seen} | run_once(sandbox, prompt(scene, arm), args, pytest_command(scene, arm))
    written = sandbox / test_path(scene)
    tests = written.read_text(encoding="utf-8") if written.is_file() else None
    given = scene_file(name, scene, f"{seen}.py").read_text(encoding="utf-8")
    module = (sandbox / module_path(scene)).read_text(encoding="utf-8")
    row |= {"tests": tests, "touched_module": module != given}
    if "error" in row:
        return row
    if scene.get("property"):
        return row | score_property(tests, name, scene, arm, work / "scoring")
    row |= score(tests, name, scene, work / "scoring")
    return row | {"module": module} | judge_code(module, tests, name, scene, work / "scoring") if arm in WRITES_CODE else row


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--out", type=environment.out_path, help="a recording goes to evals/baseline/@env/")
    parser.add_argument("--set", choices=("planted", "property"), default="planted", help="planted: the four scenes of board 061; property: the five of board 063")
    parser.add_argument("--scenes", nargs="+", help="default: every scene of the set")
    parser.add_argument("--arms", nargs="+", choices=list(ARMS), default=list(ARMS))
    parser.add_argument("--repeat", type=int, default=1, help="sessions per scene and arm")
    parser.add_argument("--dry-run", type=Path, help="build every sandbox here, write every prompt beside them and stop; free")
    parser.add_argument("--score", type=Path, help="score this ready test file against --scene and stop; free")
    parser.add_argument("--scene", help="the scene --score is for")
    parser.add_argument("--arm", choices=list(ARMS), default="c", help="the property set: the arm --score counts as (c brings the library)")
    parser.add_argument("--rescore", nargs="+", type=Path, help="the property set: count the test files these recordings kept again, print the table and stop; free. With --out, write the rows (the test files stay in the recordings)")
    parser.add_argument("--table", nargs="+", type=Path, help="print scene × arm × repeat and the summary of these recordings together and stop; free")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the session's model")
    parser.add_argument("--max-usd", type=float, default=None, help="a ceiling: stop before the runs together cost more (default: none)")
    parser.add_argument("--max-usd-per-run", type=float, default=1.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()
    if args.table:
        runs = [run for path in args.table for run in json.loads(path.read_text(encoding="utf-8"))["runs"]]
        print(table(runs) + "\n\n" + json.dumps({k: v for k, v in summary(runs).items() if k != "table"}, indent=2, ensure_ascii=False))
        return 0
    if args.rescore:
        with tempfile.TemporaryDirectory(prefix="engine-tester-eval-") as tmp:
            runs, moved = rescore(args.rescore, Path(tmp))
        print(table(runs) + "\n\n" + json.dumps({k: v for k, v in summary(runs).items() if k != "table"}, indent=2, ensure_ascii=False))
        print("\n".join(["every outcome is as recorded"] if not moved else ["OUTCOMES THAT MOVED:", *moved]))
        if args.out:
            args.out.write_text(json.dumps({"rescored_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(), "set": "property",
                                            "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
                                            "rescored_from": [path.name for path in args.rescore], "outcomes_moved": moved, "summary": summary(runs),
                                            "runs": [{k: v for k, v in run.items() if k not in ("tests", "answer")} for run in runs]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"results written to {args.out}")
        return 1 if moved else 0
    expected = scenes_of(args.set)
    unknown = [name for name in [*(args.scenes or []), *([args.scene] if args.scene else [])] if name not in expected]
    if unknown:
        parser.error(f"not a scene of the set «{args.set}»: {', '.join(unknown)} (it has {', '.join(expected)})")
    todo = plan(args.scenes or list(expected), args.arms, args.repeat)

    if args.score:
        if not args.scene:
            parser.error("--score needs --scene")
        with tempfile.TemporaryDirectory(prefix="engine-tester-eval-") as tmp:
            tests, scene = args.score.read_text(encoding="utf-8"), expected[args.scene]
            result = score_property(tests, args.scene, scene, args.arm, Path(tmp)) if scene.get("property") else score(tests, args.scene, scene, Path(tmp))
        print(f"{args.scene}: {shown(result)} — {result['observed']}" + (f" | {json.dumps({k: v for k, v in result.items() if k not in ('outcome', 'caught', 'observed')}, ensure_ascii=False)}" if scene.get("property") else ""))
        return 0 if result["caught"] or result["outcome"] == "clean" else 1
    if args.dry_run:
        for name, arm in dict.fromkeys(todo):
            build_sandbox(args.dry_run / f"{name}-{arm}", name, expected[name], *sees(expected[name], arm))
            (args.dry_run / f"prompt-{name}-{arm}.txt").write_text(prompt(expected[name], arm), encoding="utf-8")
        print(f"{len(dict.fromkeys(todo))} prompts and sandboxes in {args.dry_run}; nothing was run")
        return 0
    refusal = analyst.paid.paid_run_refusal(args.tasks_dir, args.owner_approved, bool(os.environ.get("CLAUDECODE")))
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    limit = analyst.dollar_limit(args.tasks_dir, args.max_usd)
    runs: list[JsonObj] = []
    with tempfile.TemporaryDirectory(prefix="engine-tester-eval-") as tmp:
        for name, arm in todo:
            stop = analyst.paid.over_limit(sum(r["cost_usd"] for r in runs), args.max_usd_per_run, limit)
            if stop:
                print(stop)
                break
            row = one_run(name, arm, expected[name], Path(tmp), args)
            runs.append(row)
            line = row.get("error") or f"{shown(row)} — {row['observed']}" + (f" | {row['code_observed']}" if "code" in row else "")
            line += f" | {row['test_count']} tests, trap calls {row.get('trap_calls', '—')}" + (f", search {row['search']}" if "search" in row else "") if "test_count" in row else ""
            print(f"{name} {arm}: {line}  (${row['cost_usd']:.2f}, {', '.join(row.get('models', []))})", flush=True)
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "limit_usd": limit, "planned": [f"{s}/{a}" for s, a in todo], "set": args.set, "arms": {arm: arm_says(args.set, arm) for arm in args.arms},
        "scenes": {name: entry["what"] for name, entry in expected.items()}, "summary": summary(runs), "runs": runs,
    }
    print("\n" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return 0 if len(runs) == len(todo) and not any("error" in r for r in runs) else 1


if __name__ == "__main__":
    sys.exit(main())
