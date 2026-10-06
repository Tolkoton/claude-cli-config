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

PAID RUNS. As in run_analyst_evals.py: sessions start only when the task in tasks/doing/ has a
«Платні прогони:» line with a dollar limit, or the owner runs this by hand with
--owner-approved (which does not count inside a Claude Code session). The limit is the smaller
of --max-usd and the number in that line; the runs stop before it is passed.

Standard library only, Python 3.12+; the scoring runs pytest through `uvx`.
"""

from __future__ import annotations

import argparse
import json
import os
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
OUTCOMES = {(False, True): "caught", (True, True): "missed", (False, False): "fails_on_both", (True, False): "mirrors_bug"}

JsonObj = dict[str, Any]


def fixture(name: str) -> str:
    return (FIXTURE / name).read_text(encoding="utf-8")


def test_path(scene: JsonObj) -> str:
    return f"tests/test_{scene['slug'].replace('-', '_')}_contract.py"


def module_path(scene: JsonObj) -> str:
    return f"src/refproj/{scene['module']}.py"


# ------------------------------------------------------------------ sandboxes and prompts


def build_sandbox(target: Path, name: str, scene: JsonObj, implementation: str) -> Path:
    """The reference project with the slice's contract and one of its three modules: skeleton, wrong, right."""
    tracked = subprocess.run(["git", "-C", str(REFERENCE), "ls-files", "."], capture_output=True, text=True, check=True)
    for rel in tracked.stdout.splitlines():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REFERENCE / rel, target / rel)
    shutil.copy2(FIXTURE / "scenes" / name / f"{implementation}.py", target / module_path(scene))
    (target / ".engine/slices").mkdir(parents=True)
    shutil.copy2(FIXTURE / "scenes" / name / "contract.md", target / f".engine/slices/{scene['slug']}.md")
    return target


def prompt(scene: JsonObj, arm: str) -> str:
    return fixture(ARMS[arm][1]).format(contract=f".engine/slices/{scene['slug']}.md", module_path=module_path(scene),
                                        function=scene["function"], test_path=test_path(scene), run=" ".join((*PYTEST, test_path(scene))))


# ------------------------------------------------------------------ scoring (free, deterministic)


def pytest_verdict(project: Path, *selection: str) -> JsonObj:
    proc = subprocess.run([*PYTEST, *selection], cwd=project, capture_output=True, text=True, check=False)
    lines = proc.stdout.strip().splitlines()
    return {"passed": proc.returncode == 0, "empty": proc.returncode == 5, "last_line": lines[-1] if lines else proc.stderr.strip()[-200:]}


def run_suite(tests: str, name: str, scene: JsonObj, implementation: str, work: Path) -> JsonObj:
    """pytest's verdict on `tests` against one implementation: passed, and whether anything was collected."""
    project = build_sandbox(work / f"{name}-{implementation}", name, scene, implementation)
    (project / test_path(scene)).write_text(tests, encoding="utf-8")
    verdict = pytest_verdict(project, test_path(scene))
    shutil.rmtree(project)
    return verdict


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
    return row["outcome"] + (f"; code {row['code']}" + ("; SELF-DECEIVED" if row["self_deceived"] else "") if "code" in row else "")


def summary(runs: list[JsonObj]) -> JsonObj:
    table: JsonObj = {}
    for r in runs:   # a repeated scene and arm: order/c, order/c#2, …
        key, again = f"{r['scene']}/{r['arm']}", sum(1 for k in table if k.split("#")[0] == f"{r['scene']}/{r['arm']}")
        table[f"{key}#{again + 1}" if again else key] = shown(r)
    arms = [arm for arm in ARMS if any(r["arm"] == arm for r in runs)]
    caught = {arm: f"{sum(1 for r in runs if r['arm'] == arm and r.get('caught'))} of {sum(1 for r in runs if r['arm'] == arm)}" for arm in arms}
    result: JsonObj = {"runs": len(runs), "caught": caught, "cost_usd": round(sum(r["cost_usd"] for r in runs), 4), "table": table}
    written = [r for r in runs if "code" in r]
    if written:
        result["code_written"] = {kind: sum(1 for r in written if r["code"] == kind) for kind in ("right", "trapped", "broken", "none")}
        result["self_deceived"] = f"{sum(1 for r in written if r['self_deceived'])} of {len(written)}"
    return result


# ------------------------------------------------------------------ the paid part


def run_once(sandbox: Path, text: str, args: argparse.Namespace) -> JsonObj:
    command = [args.claude, "-p", text, "--tools", *TOOLS, "--permission-mode", "acceptEdits", "--allowedTools", "Bash(uvx --with pytest pytest:*)",
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


def one_run(name: str, arm: str, scene: JsonObj, work: Path, args: argparse.Namespace) -> JsonObj:
    """One session in its own sandbox, then the file it wrote scored against both implementations."""
    seen = ARMS[arm][0]
    sandbox = work / f"{name}-{arm}"
    if sandbox.exists():   # --repeat: the same scene and arm again, in a fresh sandbox
        shutil.rmtree(sandbox)
    sandbox = build_sandbox(sandbox, name, scene, seen)
    row = {"scene": name, "arm": arm, "sees": seen} | run_once(sandbox, prompt(scene, arm), args)
    written = sandbox / test_path(scene)
    tests = written.read_text(encoding="utf-8") if written.is_file() else None
    given = (FIXTURE / "scenes" / name / f"{seen}.py").read_text(encoding="utf-8")
    module = (sandbox / module_path(scene)).read_text(encoding="utf-8")
    row |= {"tests": tests, "touched_module": module != given}
    if "error" in row:
        return row
    row |= score(tests, name, scene, work / "scoring")
    return row | {"module": module} | judge_code(module, tests, name, scene, work / "scoring") if arm in WRITES_CODE else row


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--out", type=environment.out_path, help="a recording goes to evals/baseline/@env/")
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    parser.add_argument("--arms", nargs="+", choices=list(ARMS), default=list(ARMS))
    parser.add_argument("--repeat", type=int, default=1, help="sessions per scene and arm")
    parser.add_argument("--dry-run", type=Path, help="build every sandbox here, write every prompt beside them and stop; free")
    parser.add_argument("--score", type=Path, help="score this ready test file against --scene and stop; free")
    parser.add_argument("--scene", choices=SCENES, help="the scene --score is for")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the session's model")
    parser.add_argument("--max-usd", type=float, default=10.0, help="stop before the runs together cost more")
    parser.add_argument("--max-usd-per-run", type=float, default=1.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()
    expected = json.loads(fixture("expected.json"))
    todo = plan(args.scenes, args.arms, args.repeat)

    if args.score:
        if not args.scene:
            parser.error("--score needs --scene")
        with tempfile.TemporaryDirectory(prefix="engine-tester-eval-") as tmp:
            result = score(args.score.read_text(encoding="utf-8"), args.scene, expected[args.scene], Path(tmp))
        print(f"{args.scene}: {result['outcome']} — {result['observed']}")
        return 0 if result["caught"] else 1
    if args.dry_run:
        for name, arm in dict.fromkeys(todo):
            build_sandbox(args.dry_run / f"{name}-{arm}", name, expected[name], ARMS[arm][0])
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
            spent = sum(r["cost_usd"] for r in runs)
            if spent + args.max_usd_per_run > limit:
                print(f"cost limit: ${spent:.2f} spent, a run may cost ${args.max_usd_per_run:.2f}, the limit is ${limit:.2f} — stopping")
                break
            row = one_run(name, arm, expected[name], Path(tmp), args)
            runs.append(row)
            line = row.get("error") or f"{shown(row)} — {row['observed']}" + (f" | {row['code_observed']}" if "code" in row else "")
            print(f"{name} {arm}: {line}  (${row['cost_usd']:.2f}, {', '.join(row.get('models', []))})", flush=True)
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "limit_usd": limit, "planned": [f"{s}/{a}" for s, a in todo], "arms": {arm: f"sees the contract and the {ARMS[arm][0]} module" + ("; writes the implementation too" if arm in WRITES_CODE else "") for arm in args.arms},
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
