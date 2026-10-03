#!/usr/bin/env python3
"""complexity_budget.py: every limit, every trap, the switch, and the budget-raise guard.

Each case builds a real temporary git repository: a base commit, a slice contract with a
budget measured from it, and a change in the working tree. The hook is run the way Claude
Code runs it (JSON on stdin, CLAUDE_PROJECT_DIR set).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "complexity_budget.py"
PASS = FAIL = 0

PRICING = '''"""Prices."""


def total(prices: list[int]) -> int:
    return sum(prices)


def _legacy_branchy(a: int) -> int:
    if a == 1:
        return 1
    if a == 2:
        return 2
    if a == 3:
        return 3
    if a == 4:
        return 4
    if a == 5:
        return 5
    if a == 6:
        return 6
    return 0
'''
PYPROJECT = '[project]\nname = "demo"\nversion = "0"\ndependencies = []\n\n[dependency-groups]\ndev = ["pytest>=8"]\n'
BUDGET = """## Complexity budget
base_commit: {base}
max_new_files: 1
max_net_new_lines: 30
max_new_public_symbols: 2
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 5
max_nesting_depth: 2
justification: none
"""


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}   {detail[:200]}")


def sh(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def make_repo(gate: str = "block", budget: str = BUDGET, active: bool = True) -> Path:
    repo = Path(tempfile.mkdtemp(prefix="budget-"))
    (repo / "src" / "demo").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / ".engine" / "slices").mkdir(parents=True)
    (repo / ".claude" / "state" / "overseer").mkdir(parents=True)
    (repo / "src" / "demo" / "pricing.py").write_text(PRICING)
    (repo / "tests" / "test_pricing.py").write_text("def test_total() -> None:\n    assert True\n")
    (repo / "pyproject.toml").write_text(PYPROJECT)
    (repo / ".claude" / "project.env").write_text(f'SOURCE_DIRS="src"\nCOMPLEXITY_GATE="{gate}"\n')
    (repo / ".gitignore").write_text(".engine/PROGRESS.md\n.claude/state/overseer/.budget-*\n"
                                     ".claude/state/overseer/complexity-report.md\n")
    sh(repo, "init", "-q", "-b", "main")
    sh(repo, "add", "-A")
    sh(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    base = sh(repo, "rev-parse", "HEAD")
    (repo / ".engine" / "slices" / "tax.md").write_text(
        "# Slice tax\n\n## Goal\nAdd tax.\n\n" + budget.format(base=base) + "\n## Exit criterion\nTests.\n")
    if active:
        (repo / ".engine/PROGRESS.md").write_text(
            "# PROGRESS\n\n## Slice tax — IN PROGRESS\nPlanning artifact: `.engine/slices/tax.md`.\n")
    return repo


def run_hook(repo: Path, stop_hook_active: bool = False) -> tuple[str, str]:
    """Returns (decision, text): decision is 'block', 'warn' or 'allow'."""
    proc = subprocess.run(
        [sys.executable, str(HOOK), "hook"], capture_output=True, text=True, cwd=repo,
        input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": stop_hook_active}),
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}, check=False)
    if proc.returncode != 0:
        return f"exit {proc.returncode}", proc.stderr
    if not proc.stdout.strip():
        return "allow", ""
    payload = json.loads(proc.stdout)
    if payload.get("decision") == "block":
        return "block", payload["reason"]
    return "warn", payload.get("systemMessage", "")


def add(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def append(repo: Path, rel: str, text: str) -> None:
    with open(repo / rel, "a", encoding="utf-8") as handle:
        handle.write(text)


SMALL = '\n\ndef with_tax(price: int, rate: int) -> int:\n    return price + price * rate // 100\n'

print("WITHIN-*  a change that fits the budget ends the turn")
repo = make_repo()
append(repo, "src/demo/pricing.py", SMALL)
decision, text = run_hook(repo)
check("one small public function -> allow", decision == "allow", text)
check("report file says 'within budget'",
      "within budget" in (repo / ".claude/state/overseer/complexity-report.md").read_text())

print("LIMIT-*   each limit blocks, names its field and what counted")
repo = make_repo()
add(repo, "src/demo/a.py", "A = 1\n")
add(repo, "src/demo/b.py", "B = 1\n")
decision, text = run_hook(repo)
check("two new production files (untracked) against a limit of 1 -> block",
      decision == "block" and "max_new_files: 2 used, 1 allowed" in text, text)
check("the advice forbids editing the budget", "Do not edit the budget" in text, text)

repo = make_repo()
append(repo, "src/demo/pricing.py", "\n" + "\n".join(f"X{i} = {i}" for i in range(40)) + "\n")
decision, text = run_hook(repo)
check("41 net new production lines against 30 -> block", decision == "block" and "max_net_new_lines" in text, text)

repo = make_repo()
append(repo, "src/demo/pricing.py", "".join(f"\n\ndef f{i}() -> int:\n    return {i}\n" for i in range(3)))
decision, text = run_hook(repo)
check("three new public functions against 2 -> block",
      decision == "block" and "max_new_public_symbols: 3 used" in text, text)

repo = make_repo()
append(repo, "src/demo/pricing.py",
       "\n\nfrom abc import ABC, abstractmethod\n\n\nclass _Rounder(ABC):\n    @abstractmethod\n"
       "    def go(self) -> int: ...\n")
decision, text = run_hook(repo)
check("a new abstract base class against 0 -> block (private name still counts)",
      decision == "block" and "max_new_abstractions: 1 used" in text and "_Rounder" in text, text)

repo = make_repo()
(repo / "pyproject.toml").write_text(PYPROJECT.replace("dependencies = []", 'dependencies = ["requests>=2"]'))
decision, text = run_hook(repo)
check("a new runtime dependency -> block, named", decision == "block" and "requests" in text, text)

repo = make_repo()
(repo / "pyproject.toml").write_text(PYPROJECT.replace('"pytest>=8"', '"pytest>=8", "Radon[toml]>=6"'))
decision, text = run_hook(repo)
check("a new DEV dependency counts too, name normalised", decision == "block" and "radon" in text, text)

BRANCHY = "\n\ndef _route(a: int) -> int:\n" + "".join(
    f"    if a == {i}:\n        return {i}\n" for i in range(7)) + "    return 0\n"
repo = make_repo()
append(repo, "src/demo/pricing.py", BRANCHY)
decision, text = run_hook(repo)
check("a new function with complexity 8 against 5 -> block, function named",
      decision == "block" and "max_cyclomatic_per_function" in text and "_route = 8" in text, text)

repo = make_repo()
append(repo, "src/demo/pricing.py",
       "\n\ndef _deep(a: int) -> int:\n    if a:\n        for i in range(a):\n            while i:\n"
       "                return i\n    return 0\n")
decision, text = run_hook(repo)
check("nesting depth 3 against 2 -> block", decision == "block" and "max_nesting_depth" in text, text)

print("TRAP-*    what must NOT be charged to the slice")
repo = make_repo()
add(repo, "tests/test_a.py", "\n".join(f"def test_{i}() -> None:\n    assert True\n" for i in range(40)))
add(repo, "tests/test_b.py", "def test_b() -> None:\n    assert True\n")
decision, text = run_hook(repo)
check("two new test files and 120 test lines -> allow (tests are never limited)", decision == "allow", text)
check("...but they are reported", "tests: +" in (repo / ".claude/state/overseer/complexity-report.md").read_text())

repo = make_repo()
append(repo, "src/demo/pricing.py", "\n\nY = 1\n")
decision, text = run_hook(repo)
check("legacy function of complexity 7 in a touched file -> allow (not this slice's debt)",
      decision == "allow", text)

repo = make_repo()
source = (repo / "src/demo/pricing.py").read_text().replace(
    "    return 0\n", "    if a == 7:\n        return 7\n    return 0\n")
(repo / "src/demo/pricing.py").write_text(source)
decision, text = run_hook(repo)
check("the same legacy function made WORSE (7 -> 8) -> block",
      decision == "block" and "_legacy_branchy = 8" in text, text)

repo = make_repo()
add(repo, "docs/notes.md", "x\n" * 500)
add(repo, "scripts/tool.py", "print(1)\n" * 50)
decision, text = run_hook(repo)
check("files outside SOURCE_DIRS (docs, scripts) -> allow", decision == "allow", text)

repo = make_repo()
source = (repo / "src/demo/pricing.py").read_text()
(repo / "src/demo/pricing.py").write_text(source[: source.index("def _legacy_branchy")])
append(repo, "src/demo/pricing.py", "\n".join(f"Z{i} = {i}" for i in range(35)) + "\n")
decision, text = run_hook(repo)
check("35 lines added, 16 deleted: net +19 against 30 -> allow (deleting pays lines back)",
      decision == "allow", text)

print("SWITCH-*  off / warn / no slice / no budget")
for gate in ("off", ""):
    repo = make_repo(gate=gate)
    add(repo, "src/demo/a.py", "A = 1\n")
    add(repo, "src/demo/b.py", "B = 1\n")
    decision, text = run_hook(repo)
    check(f"COMPLEXITY_GATE='{gate}' -> allow, no report file",
          decision == "allow" and not (repo / ".claude/state/overseer/complexity-report.md").exists(), text)

repo = make_repo(gate="warn")
add(repo, "src/demo/a.py", "A = 1\n")
add(repo, "src/demo/b.py", "B = 1\n")
decision, text = run_hook(repo)
check("warn: never blocks, tells the user, writes the report",
      decision == "warn" and "complexity-report.md" in text
      and "EXCEEDED" in (repo / ".claude/state/overseer/complexity-report.md").read_text(), text)

repo = make_repo(active=False)
add(repo, "src/demo/a.py", "A = 1\n")
add(repo, "src/demo/b.py", "B = 1\n")
check("no slice IN PROGRESS -> allow", run_hook(repo)[0] == "allow")

repo = make_repo(budget="")
add(repo, "src/demo/a.py", "A = 1\n")
add(repo, "src/demo/b.py", "B = 1\n")
check("active contract without a budget section -> allow", run_hook(repo)[0] == "allow")

repo = make_repo()
add(repo, "src/demo/a.py", "A = 1\n")
add(repo, "src/demo/b.py", "B = 1\n")
check("stop_hook_active -> allow (loop guard)", run_hook(repo, stop_hook_active=True)[0] == "allow")

repo = make_repo(budget=BUDGET.replace("max_new_files", "max_new_fils"))
decision, text = run_hook(repo)
check("a misspelt field -> block with the reason, not a silently missing limit",
      decision == "block" and "unknown budget field 'max_new_fils'" in text, text)

print("RAISE-*   the limits the slice began with stay in force")
repo = make_repo()
add(repo, "src/demo/a.py", "A = 1\n")
check("first look, within budget -> allow", run_hook(repo)[0] == "allow")
add(repo, "src/demo/b.py", "B = 1\n")
contract = repo / ".engine/slices/tax.md"
contract.write_text(contract.read_text().replace("max_new_files: 1", "max_new_files: 5"))
decision, text = run_hook(repo)
check("budget edited 1 -> 5 mid-slice: still blocked at 1, and the raise is reported",
      decision == "block" and "1 allowed" in text and "BUDGET RAISED" in text, text)
for memo in (repo / ".claude/state/overseer").glob(".budget-*.json"):
    memo.unlink()
check("owner deletes the memo file (re-baseline) -> the new limit applies", run_hook(repo)[0] == "allow")

print("VALIDATE-* the contract check run at slice approval")


def validate(repo: Path) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(HOOK), "validate", ".engine/slices/tax.md"],
                          capture_output=True, text=True, cwd=repo,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}, check=False)
    return proc.returncode, proc.stdout


code, out = validate(make_repo())
check("a complete budget -> OK", code == 0 and out.startswith("OK"), out)
code, out = validate(make_repo(budget=""))
check("no budget section -> INVALID", code == 1 and "no '## Complexity budget'" in out, out)
code, out = validate(make_repo(budget=BUDGET.replace("max_new_dependencies: 0", "max_new_dependencies: 2")))
check("new dependencies allowed without a justification -> INVALID", code == 1 and "justification" in out, out)
code, out = validate(make_repo(budget=BUDGET.replace("{base}", "deadbeef")))
check("base_commit that is not a commit -> INVALID", code == 1 and "not a commit" in out, out)
code, out = validate(make_repo(budget=BUDGET.replace("max_new_files: 1\n", "")))
check("a core limit missing -> INVALID", code == 1 and "max_new_files is missing" in out, out)

print("CALL-*    an overrun calls the simplifier; an accepted overrun ends the turn")
SIMPLIFIER = ROOT / ".claude" / "hooks" / "simplifier.py"
CONFIRM = [{"target": "src/demo/a.py", "category": "speculative_slice", "claim": "a.py is not needed by the slice",
            "evidence": [{"source": "judgement", "ref": "", "detail": "the contract names one file"}],
            "protected": False, "chesterton_checked": True, "test_safety": "characterization_exists",
            "proposed_action": "confirm", "traceability": "none", "reversal_risk": "low"}]


def accept(repo: Path, reason: str, findings: object, in_session: bool = True) -> tuple[int, str]:
    (repo / "verdict.json").write_text(json.dumps(findings))
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(repo)}
    proc = subprocess.run([sys.executable, str(SIMPLIFIER), "accept", "--reason", reason, "--verdict", "verdict.json"],
                          capture_output=True, text=True, cwd=repo, env=env, check=False)
    return proc.returncode, proc.stdout + proc.stderr


for gate in ("call", "block"):
    repo = make_repo(gate=gate)
    add(repo, "src/demo/a.py", "A = 1\n")
    add(repo, "src/demo/b.py", "B = 1\n")
    decision, text = run_hook(repo)
    check(f"COMPLEXITY_GATE='{gate}': the overrun holds the turn and names the simplifier and the figures",
          decision == "block" and "simplifier" in text and "max_new_files: 2 used, 1 allowed" in text
          and "simplifier.py accept" in text, text)
(repo / "tests" / "test_a.py").write_text("from demo import a\n")
code, out = accept(repo, "two modules keep parsing apart from pricing, as the exit criterion names both", CONFIRM)
check("accept is refused while the simplifier's verdict still holds a confirm finding", code != 0 and "confirm" in out, out)
check("...and the turn is still held", run_hook(repo)[0] == "block")
code, out = accept(repo, "ok", [])
check("accept is refused without a real reason", code != 0 and "reason" in out, out)
code, out = accept(repo, "two modules keep parsing apart from pricing, as the exit criterion names both", [])
check("accept with a clean verdict records the overrun", code == 0, out)
sidecar = repo / ".engine/slices/overruns/tax.md"
check("the reason is written next to the contract", sidecar.is_file() and "keep parsing apart" in sidecar.read_text()
      and "max_new_files: 2" in sidecar.read_text(), sidecar.read_text() if sidecar.is_file() else "absent")
ledger = repo / ".engine/overseer/ledger.md"
check("...and in the ledger", ledger.is_file() and "COMPLEXITY_OVERRUN_ACCEPTED" in ledger.read_text()
      and "keep parsing apart" in ledger.read_text())
check("the sealed contract itself is untouched", "keep parsing apart" not in (repo / ".engine/slices/tax.md").read_text())
decision, text = run_hook(repo)
report_text = (repo / ".claude/state/overseer/complexity-report.md").read_text()
check("the accepted overrun ends the turn; the report keeps both the excess and the reason",
      decision == "allow" and "accepted" in report_text and "max_new_files" in report_text, text + report_text)
add(repo, "src/demo/c.py", "C = 1\n")
decision, text = run_hook(repo)
check("growing past the accepted figure calls the simplifier again", decision == "block" and "3 used" in text, text)

repo = make_repo(gate="call")
check("accept with nothing exceeded has nothing to record", accept(repo, "a reason of two words", [])[0] != 0)

print("DEFAULT-* the project's default limits (project.env) and their calibration")
NO_FUNCTION_LIMITS = BUDGET.replace("max_cyclomatic_per_function: 5\n", "").replace("max_nesting_depth: 2\n", "")
repo = make_repo(budget=NO_FUNCTION_LIMITS)
append(repo, "src/demo/pricing.py", BRANCHY)
check("no per-function limit in the contract and none in project.env -> allow", run_hook(repo)[0] == "allow")
append(repo, ".claude/project.env", 'COMPLEXITY_MAX_CYCLOMATIC="6"\n')
decision, text = run_hook(repo)
check("the project's default applies where the contract is silent",
      decision == "block" and "max_cyclomatic_per_function: 6 allowed" in text, text)


def budget_cli(repo: Path, *args: str, in_session: bool) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(repo)}
    if in_session:
        env["CLAUDECODE"] = "1"
    proc = subprocess.run([sys.executable, str(HOOK), *args], capture_output=True, text=True, cwd=repo, env=env, check=False)
    return proc.returncode, proc.stdout + proc.stderr


repo = make_repo()
code, out = budget_cli(repo, "calibrate", in_session=True)
check("calibrate reads the existing functions and proposes both limits",
      code == 0 and "2 functions" in out and "COMPLEXITY_MAX_CYCLOMATIC" in out and "set-defaults 7 2" in out, out)
before = (repo / ".claude/project.env").read_text()
code, out = budget_cli(repo, "set-defaults", "7", "2", in_session=True)
check("set-defaults is the owner's command: refused inside a session, nothing written",
      code == 2 and "owner" in out and (repo / ".claude/project.env").read_text() == before, out)
code, out = budget_cli(repo, "set-defaults", "7", "2", in_session=False)
after = (repo / ".claude/project.env").read_text()
check("in the owner's terminal it writes the two keys",
      code == 0 and 'COMPLEXITY_MAX_CYCLOMATIC="7"' in after and 'COMPLEXITY_MAX_NESTING="2"' in after, out + after)
budget_cli(repo, "set-defaults", "9", "3", in_session=False)
after = (repo / ".claude/project.env").read_text()
check("a second run replaces the values, never duplicates the keys",
      after.count("COMPLEXITY_MAX_CYCLOMATIC") == 1 and 'COMPLEXITY_MAX_CYCLOMATIC="9"' in after, after)

for leftover in Path(tempfile.gettempdir()).glob("budget-*"):
    shutil.rmtree(leftover, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
