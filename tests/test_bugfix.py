#!/usr/bin/env python3
"""/bugfix — the full fix of a bug (board 074): the mechanical proof, the command, the bug record.

WHY. "The test really failed before the fix" used to be the builder's claim, which the overseer
checked against the records. `bugfix.py prove` checks it with a program: in a throwaway copy the
code BEFORE the fix plus the new test must fail, the code AFTER must pass. The same script the
other way round (`pins`) shows a test passes on the code before a deletion — the delete guard's
first way through (board 072).

Deterministic: every scene runs the real bugfix.py in a throwaway git repository. The refusals
come first: the proof is shown to REFUSE before it is shown to pass.

SCENES
  - the test passes without the fix — refused; the test fails with the fix too — refused; a
    genuine pair — proved;
  - nothing but the test differs from the base — refused; a command that could not run or ran
    out of time is not a failing test; `--expect`: failing for another reason — refused;
  - the fix was committed mid-task: the base comes from the bug record's budget section;
  - the working tree is left exactly as it was; an ignored file is not part of either copy;
  - `pins`: fails on the code before the deletion — refused; passes there — pinned, whatever the
    working tree has already deleted.
The command and the template are prose a model follows; what is free to check is their
structure: the eight steps in the approved order, the three attempts, the budget as a signal.

Run:   python3 tests/test_bugfix.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
BUGFIX = HOOKS / "bugfix.py"
PASS = FAIL = 0


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = load("engine", ROOT / "engine.py")
budget = load("complexity_budget", HOOKS / "complexity_budget.py")


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def text(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(doc: str, heading: str) -> str:
    """The body of the `## ` section whose heading starts with `heading`; '' when absent."""
    match = re.search(rf"^## {re.escape(heading)}.*?\n(.*?)(?=^## |\Z)", doc, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def flat(body: str) -> str:
    return " ".join(body.split())


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str) -> str:
    sh(root, "git", "add", "-A")
    done = sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    assert done.returncode == 0, done.stderr
    return sh(root, "git", "rev-parse", "HEAD").stdout.strip()


BUGGY = "def add(a, b):\n    return a - b\n\n\ndef double(a):\n    return a * 2\n"
FIXED = BUGGY.replace("a - b", "a + b")
TEST = ("from calc import add\n\n"
        "got = add(2, 2)\nassert got == 4, f'add(2, 2) gave {got}'\nprint('ok')\n")
RUN = "PYTHONPATH=. python3 tests/test_calc.py"


def project() -> Path:
    """A project with the bug committed: add() subtracts."""
    root = Path(tempfile.mkdtemp(prefix="bugfix-"))
    sh(root, "git", "init", "-q", "-b", "main")
    (root / "calc.py").write_text(BUGGY, encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests/test_old.py").write_text("print('old ok')\n", encoding="utf-8")
    (root / ".gitignore").write_text("local.cfg\n__pycache__/\n", encoding="utf-8")
    commit(root, "the project as it was")
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(BUGFIX), "--root", str(root), *args], capture_output=True, text=True, check=False)


def prove(root: Path, *args: str, cmd: str = RUN) -> subprocess.CompletedProcess[str]:
    return run(root, "prove", "--test", "tests/test_calc.py", "--cmd", cmd, *args)


def out(r: subprocess.CompletedProcess[str]) -> str:
    return r.stdout + r.stderr


roots: list[Path] = []


def fresh(fixed: bool = True, test: str = TEST) -> Path:
    root = project()
    roots.append(root)
    if fixed:
        (root / "calc.py").write_text(FIXED, encoding="utf-8")
    (root / "tests/test_calc.py").write_text(test, encoding="utf-8")
    return root


try:
    # --- prove: the three scenes of the task, the refusals first ----------------------------------
    print("prove")
    root = fresh(test="from calc import double\n\nassert double(2) == 4\n")
    r = prove(root)
    check("the test passes without the fix — refused", r.returncode == 1 and "REFUSED" in r.stdout
          and "passes on the code before the fix" in r.stdout, out(r))

    root = fresh(test=TEST.replace("== 4", "== 5"))
    r = prove(root)
    check("the test fails with the fix too — refused", r.returncode == 1 and "REFUSED" in r.stdout
          and "still fails on the code with the fix" in r.stdout, out(r))
    check("…and the refusal shows the output of the failing run", "add(2, 2) gave 4" in r.stdout, out(r))

    root = fresh()
    status_before = sh(root, "git", "status", "--porcelain").stdout
    r = prove(root)
    check("a genuine pair — proved", r.returncode == 0 and r.stdout.startswith("PROVED") and "REFUSED" not in r.stdout, out(r))
    check("the proof names the base commit, the test and both exit codes",
          sh(root, "git", "rev-parse", "--short", "HEAD").stdout.strip() in r.stdout and "tests/test_calc.py" in r.stdout
          and "before the fix: exit 1" in r.stdout and "with the fix: exit 0" in r.stdout, out(r))
    check("the proof shows why the test failed before the fix", "add(2, 2) gave 0" in r.stdout, out(r))
    check("the working tree is left exactly as it was", sh(root, "git", "status", "--porcelain").stdout == status_before
          and not (root / "tests/__pycache__").exists(), sh(root, "git", "status", "--porcelain").stdout)

    # --- prove: what is not a proof ---------------------------------------------------------------
    print("what is not a proof")
    root = fresh(fixed=False)
    r = prove(root)
    check("nothing but the test differs from the base — refused: there is no fix", r.returncode == 1
          and "REFUSED" in r.stdout and "no fix" in r.stdout, out(r))

    root = fresh()
    r = prove(root, cmd="no-such-runner tests/test_calc.py")
    check("a command that could not run is not a failing test", r.returncode == 1 and "REFUSED" in r.stdout
          and "could not run" in r.stdout, out(r))
    hangs = "PYTHONPATH=. python3 -c 'import calc, time; calc.add(2, 2) == 4 or time.sleep(5)'"
    r = prove(root, "--timeout", "1", cmd=hangs)
    check("a command that ran out of time before the fix is not a failing test, though it passes with the fix",
          r.returncode == 1 and "REFUSED" in r.stdout and "did not finish within the time limit of 1 s" in r.stdout, out(r))

    root = fresh(test="from calc import ad\n")
    (root / "calc.py").write_text(FIXED + "\n\nad = add\n", encoding="utf-8")
    r = prove(root)
    check("(the pair below passes the bare proof: it fails before and passes after)", r.returncode == 0, out(r))
    r = prove(root, "--expect", "add(2, 2) gave 0")
    check("--expect: the test fails before the fix for another reason — refused", r.returncode == 1
          and "REFUSED" in r.stdout and "not for the expected reason" in r.stdout and "ImportError" in r.stdout, out(r))
    root = fresh()
    r = prove(root, "--expect", "add(2, 2) gave 0")
    check("--expect: the symptom is in the failing output — proved", r.returncode == 0 and "PROVED" in r.stdout, out(r))

    r = run(root, "prove", "--test", "tests/test_absent.py", "--cmd", RUN)
    check("a test file that does not exist is a usage error, not a verdict", r.returncode == 2 and "PROVED" not in r.stdout, out(r))
    r = prove(root, "--base", "no-such-commit")
    check("a base that is not a commit is a usage error", r.returncode == 2 and "PROVED" not in r.stdout, out(r))

    # --- prove: which code is "before" and "after" --------------------------------------------------
    print("before and after")
    root = fresh()
    base = sh(root, "git", "rev-parse", "HEAD").stdout.strip()
    (root / ".engine/bugs").mkdir(parents=True)
    record = root / ".engine/bugs/001-add-subtracts.md"
    record.write_text(text(".claude/templates/bug-record.md").replace("base_commit:", f"base_commit: {base}  #", 1), encoding="utf-8")
    commit(root, "the fix and its test, committed mid-task")
    r = prove(root)
    check("the fix is already committed and no base is named — refused: HEAD has no fix to prove", r.returncode == 1
          and "no fix" in r.stdout, out(r))
    r = prove(root, "--record", ".engine/bugs/001-add-subtracts.md")
    check("the base comes from the bug record's budget section — proved", r.returncode == 0 and base[:7] in r.stdout, out(r))
    r = prove(root, "--base", base)
    check("…or from --base", r.returncode == 0 and "PROVED" in r.stdout, out(r))

    root = fresh(test=TEST + "import pathlib\nassert not pathlib.Path('local.cfg').exists(), 'an ignored file was copied'\n")
    (root / "local.cfg").write_text("machine state\n", encoding="utf-8")
    (root / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    r = prove(root)
    check("an ignored file is in neither copy", r.returncode == 0, out(r))
    (root / "tests/test_calc.py").write_text(TEST + "import helper\n", encoding="utf-8")
    r = prove(root)
    check("an untracked file of the change is part of the code with the fix", r.returncode == 0, out(r))
    (root / "tests/test_calc.py").write_text(TEST + "import os\nassert 'bugfix-prove-' in os.getcwd(), os.getcwd()\n", encoding="utf-8")
    r = prove(root)
    check("both runs happen in a temporary copy, never in the project", r.returncode == 0, out(r))
    leftovers = [p for p in Path(tempfile.gettempdir()).glob("bugfix-prove-*")]
    check("the temporary copies are removed", not leftovers, leftovers)

    # --- pins: the same script the other way round (the delete guard's first way through) -----------
    print("pins")
    PIN = "from calc import double\n\nassert double(3) == 6, 'double(3) is not 6'\n"
    root = project()
    roots.append(root)
    (root / "tests/test_double.py").write_text(PIN.replace("== 6", "== 7"), encoding="utf-8")
    r = run(root, "pins", "--test", "tests/test_double.py", "--cmd", "PYTHONPATH=. python3 tests/test_double.py")
    check("the test fails on the code before the deletion — refused: it pins nothing", r.returncode == 1
          and "REFUSED" in r.stdout and "fails on the code before the change" in r.stdout, out(r))
    (root / "tests/test_double.py").write_text(PIN, encoding="utf-8")
    r = run(root, "pins", "--test", "tests/test_double.py", "--cmd", "PYTHONPATH=. python3 tests/test_double.py")
    check("the test passes on the code before the deletion — pinned", r.returncode == 0 and r.stdout.startswith("PINNED"), out(r))
    (root / "calc.py").write_text(FIXED.split("\n\n\ndef double")[0] + "\n", encoding="utf-8")
    r = run(root, "pins", "--test", "tests/test_double.py", "--cmd", "PYTHONPATH=. python3 tests/test_double.py")
    check("…and it is the code BEFORE the change that is run: the working tree has already deleted the function",
          r.returncode == 0 and "PINNED" in r.stdout, out(r))
    r = run(root, "pins", "--test", "tests/test_double.py", "--cmd", "no-such-runner")
    check("pins: a command that could not run pins nothing", r.returncode == 1 and "could not run" in r.stdout, out(r))

    # --- the budget of a bug record is measured like a slice's --------------------------------------
    print("the budget in the bug record")
    root = fresh()
    base = sh(root, "git", "rev-parse", "HEAD").stdout.strip()
    (root / ".engine/bugs").mkdir(parents=True)
    (root / ".engine/bugs/001-add-subtracts.md").write_text(
        text(".claude/templates/bug-record.md").replace("base_commit:", f"base_commit: {base}  #", 1), encoding="utf-8")
    (root / ".engine/PROGRESS.md").write_text("## Bugfix 001-add-subtracts — IN PROGRESS\n- Record: `.engine/bugs/001-add-subtracts.md`\n", encoding="utf-8")
    found = budget.active_contract(root)
    check("the record PROGRESS.md marks IN PROGRESS is the active contract", found is not None and found.name == "001-add-subtracts.md", found)
    outcome = budget.evaluate(root)
    check("a one-line fix is inside the budget", outcome is not None and not outcome.exceeded, outcome and outcome.text)
    (root / "calc.py").write_text(FIXED + "".join(f"\nX{i} = {i}" for i in range(41)) + "\n", encoding="utf-8")
    outcome = budget.evaluate(root)
    check("41 new lines of working code are over it — the signal that calls the simplifier", outcome is not None
          and outcome.exceeded and "max_net_new_lines" in outcome.over, outcome and outcome.text)
    (root / "calc.py").write_text(FIXED, encoding="utf-8")
    (root / "extra.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    outcome = budget.evaluate(root)
    check("a new file and a new public name are over it too", outcome is not None and outcome.exceeded
          and {"max_new_files", "max_new_public_symbols"} <= set(outcome.over), outcome and outcome.over)
finally:
    for path in roots:
        shutil.rmtree(path, ignore_errors=True)

# --- the command: eight steps, in order -----------------------------------------------------------
print("the command")
command = text(".claude/commands/bugfix.md")
check("/bugfix exists with a description", command.startswith("---\ndescription:"), command[:120])
steps = re.findall(r"^## (\d)\. (.+)$", command, re.MULTILINE)
check("eight numbered steps, 1 to 8", [n for n, _ in steps] == list("12345678"), steps)
WORDS = ("record", "reproduce", "failing test", "cause", "fix", "proof", "gate", "lesson")
check("the steps are the approved ones, in the approved order",
      len(steps) == 8 and all(word in title.lower() for word, (_, title) in zip(WORDS, steps)), steps)

record_step = flat(section(command, "1."))
check("step 1: the record is `.engine/bugs/<number-name>.md`, made from the template, and is contract and report at once",
      ".engine/bugs/<number-name>.md" in record_step and ".claude/templates/bug-record.md" in record_step
      and "contract and the report" in record_step, record_step[:300])
check("step 1: symptom, expected, actual, where seen — and where the expected is written",
      all(w in record_step for w in ("symptom", "expected", "actual", "where it was seen", "where that is written")), record_step[:400])
check("step 1: the base commit is written before anything is changed", "git rev-parse HEAD" in record_step and "base_commit" in record_step)
repro = flat(section(command, "2."))
check("step 2: the command and its output; three attempts, then park with everything tried",
      "three attempts" in repro and "parked" in repro and "everything that was tried" in repro and "output" in repro, repro[:300])
check("step 2: no fix on a guess", "no fix on a guess" in repro and "unverified premise" in repro and "Article 1" in repro)
check("step 2: the three attempts are a guard against an endless loop, and an attempt is a different way",
      "endless loop" in repro and "different way" in repro)
check("step 2: parked means the board task goes to blocked/ or the item to parked.md, and the code is untouched",
      "tasks/blocked/" in repro and ".engine/overseer/parked.md" in repro and "no change to the working code" in repro)
failing = flat(section(command, "3."))
check("step 3: at the level where the user sees the bug, failing for the right reason",
      "where the user sees" in failing and "right reason" in failing, failing[:300])
check("step 3: code no test can reach — first a test that pins the present behaviour around it, then the smallest seam",
      "pins the present behaviour" in failing and "smallest seam" in failing and "bugfix.py pins" in failing)
check("step 3: no separate tester here", "tester" in failing and "not called" in failing)
cause = flat(section(command, "4."))
check("step 4: the cause is written before the fix, and tells where it showed from why it happened",
      "before the fix is written" in cause and "where it showed" in cause and "why it happened" in cause, cause[:300])
check("step 4: the same places are searched; neighbours are fixed within the budget or become tasks",
      "same cause" in cause and "search" in cause.lower() and "inside the budget" in cause and "new task" in cause)
fix = flat(section(command, "5."))
check("step 5: the budget — zero new files, public names, abstractions, dependencies; 40 new lines of working code",
      all(w in fix for w in ("zero new files", "zero new public names", "zero new abstractions", "zero new dependencies", "40 new lines of working code")), fix[:400])
check("step 5: 40 is a signal, not a ceiling — it calls the simplifier", "not a ceiling" in fix and "signal" in fix
      and "simplifier.py request --lens budget" in fix, fix[:400])
check("step 5: not justified — the fix becomes a slice through /plan-slice", "not justified" in fix and "`/plan-slice`" in fix and "slice" in fix)
check("step 5: the numbers are not edited and nothing is tidied on the way", "Do not edit the numbers" in fix and "No tidying" in fix)
check("the command never calls 40 a limit that forbids", not re.search(r"(?i)(at most|no more than|maximum of|must not exceed) 40", command))
proof = flat(section(command, "6."))
check("step 6: bugfix.py prove, with the record, the test, the command and the symptom",
      "bugfix.py prove" in proof and "--record" in proof and "--test" in proof and "--cmd" in proof and "--expect" in proof, proof[:300])
check("step 6: a refusal is not argued with, and the output is pasted into the record",
      "REFUSED" in proof and "not a proof" in proof and "into the record" in proof)
gate_step = flat(section(command, "7."))
check("step 7: the gate with «no worse», the overseer, and the regression test stays for good",
      "no worse" in gate_step and "overseer" in gate_step and "stays in the suite" in gate_step, gate_step[:300])
lesson = flat(section(command, "8."))
check("step 8: one question — why was it not caught earlier — with the four answers, into the lesson queue",
      "why was this not caught earlier" in lesson and all(w in lesson for w in ("a test was missing", "the contract was wrong", "a rule was missing", "external"))
      and "lesson_queue.py add" in lesson, lesson[:300])
check("step 8: a rule is the owner's to make", "only the owner" in lesson)

print("when it is not a bug, and the way up")
notbug = flat(section(command, "When it is not a bug"))
check("the expected is written nowhere and cannot be derived from the profile or the goals — a question for the owner, not a fix",
      "written nowhere" in notbug and ".engine/onboard/profile.md" in notbug and ".engine/goals.md" in notbug
      and "question for the owner" in notbug and "not a fix" in notbug and "Article 5" in notbug, notbug[:400])
check("…and it stands before the first step", 0 < command.find("## When it is not a bug") < command.find("## 1."))
check("unattended, the question goes to the board, not to the conversation", "tasks/blocked/" in notbug and "AskUserQuestion" in notbug)
check("the command names only scripts and files that exist", all((ROOT / rel).is_file() for rel in
      (".claude/hooks/bugfix.py", ".claude/hooks/lesson_queue.py", ".claude/hooks/simplifier.py", ".claude/hooks/complexity_budget.py",
       ".claude/templates/bug-record.md", ".claude/commands/plan-slice.md")))

# --- the bug record template ------------------------------------------------------------------------
print("the bug record template")
template = text(".claude/templates/bug-record.md")
heads = re.findall(r"^## (.+)$", template, re.MULTILINE)
check("the sections follow the steps, with the budget beside the fix",
      heads == ["1. Record", "2. Reproduction", "3. Failing test", "4. Cause", "5. Fix", "Complexity budget", "6. Proof",
                "7. Gate and overseer", "8. Lesson"], heads)
check("the type of work is written in the record", re.search(r"^type: bugfix$", template, re.MULTILINE) is not None)
check("the record: symptom, expected with where it is written, actual, where seen",
      all(w in section(template, "1.") for w in ("Symptom:", "Expected:", "Where the expected is written:", "Actual:", "Where it was seen:")))
check("the reproduction has room for exactly three attempts", re.findall(r"^### Attempt (\d)", section(template, "2."), re.MULTILINE) == ["1", "2", "3"])
check("the cause: where it showed, why it happened, the same places", all(w in section(template, "4.") for w in ("Where it showed:", "Why it happened:", "Same places")))
with tempfile.TemporaryDirectory() as tmp:
    filled = Path(tmp) / "001-x.md"
    filled.write_text(template.replace("base_commit:", "base_commit: abc1234  #", 1), encoding="utf-8")
    parsed = budget.parse_budget(filled)
check("the budget section is the ready small budget: 0 files, 40 lines, 0 names, 0 abstractions, 0 dependencies",
      parsed is not None and parsed.limits == {"max_new_files": 0, "max_net_new_lines": 40, "max_new_public_symbols": 0,
                                               "max_new_abstractions": 0, "max_new_dependencies": 0}, parsed)
check("the template says the 40 is a signal, not a ceiling", "signal, not a ceiling" in flat(template))
check("the lesson: the four answers", all(w in section(template, "8.") for w in ("a test was missing", "the contract was wrong", "a rule was missing", "external")))
ownership = engine.parse_ownership(text(".claude/ownership.txt"))
check("the template and the script ship with the engine; a bug record is the project's",
      engine.owner_of(ownership, ".claude/templates/bug-record.md") == "engine" and engine.owner_of(ownership, ".claude/hooks/bugfix.py") == "engine"
      and engine.owner_of(ownership, ".claude/commands/bugfix.md") == "engine" and engine.owner_of(ownership, ".engine/bugs/001-x.md") == "project")

# --- the overseer and the documents -------------------------------------------------------------------
print("the overseer and the documents")
overseer = flat(text(".claude/agents/overseer.md"))
check("the overseer: a bug record named in PROGRESS.md is the contract of the work",
      ".engine/bugs/<number-name>.md" in overseer and "is the contract" in overseer, "")
check("the overseer reruns the proof instead of believing the pasted one", "bugfix.py prove" in overseer and "run it yourself" in overseer)
hooks_doc = text(".claude/references/hooks.md")
check("hooks.md has the script's row", "| `bugfix.py` |" in hooks_doc and "prove" in hooks_doc and "pins" in hooks_doc)
check("the delete guard's first way through names the script", "bugfix.py pins" in text(".claude/hooks/delete_guard.py")
      and "bugfix.py pins" in text(".claude/references/gate.md"))
check("the limits say what the proof does not give", "## The bug-fix proof (board 074)" in text("docs/engine-limits.md"))
check("the engine's AGENTS.md names the command", "`/bugfix`" in text("AGENTS.md"))
check("the budget reference says a bug record carries a budget too", ".engine/bugs/" in text(".claude/references/complexity-budget.md"))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
