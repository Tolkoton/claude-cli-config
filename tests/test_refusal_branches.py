#!/usr/bin/env python3
"""Refusals and fail-closed paths that no suite and no golden-set scenario ran (board 086).

`evals/hook_coverage.py` traced every suite and the golden set and listed the lines and branches
of the hooks and scripts nothing reached. Most of what was left is defensive (a file that cannot
be read, a usage message). The cases here are the rest: a refusal a script exists to make, a
guard that must fail closed, a record that must not be written twice — each of them code that
could have been deleted or inverted with every suite still green.

In-process where the function can be called, a real run of the script where the decision is its
exit code. No model, no network.

Run:   python3 tests/test_refusal_branches.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from hook_env import hook_env, sandbox_dir, trace_env

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
UNATTENDED = ROOT / ".claude" / "unattended"
PASS = 0
FAIL = 0
# An unattended run is something a case here sets up for itself; the one this suite happens to be
# started from (the board runner) must not answer for it.
os.environ.pop("CLAUDE_UNATTENDED_SESSION", None)


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def load(path: Path) -> Any:
    """The module at `path`, imported under a name of its own (its directory importable, as when run)."""
    name = "refusal_branches_" + path.stem.replace("-", "_")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def quiet(call: Any, *args: Any) -> tuple[Any, str]:
    """call(*args) with its output caught: (what it returned or the SystemExit code, stdout + stderr)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            result = call(*args)
        except SystemExit as stop:
            result = stop.code
    return result, out.getvalue()


def project(prefix: str = "refusal-") -> Path:
    """An empty git repository with one commit, on `main`."""
    root = Path(sandbox_dir(prefix))
    git(root, "init", "-q", "-b", "main")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")
    return root


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, capture_output=True, text=True, check=False)


def script(path: Path, root: Path, *args: str, stdin: str = "", **env: str) -> subprocess.CompletedProcess[str]:
    interpreter = [sys.executable] if path.suffix == ".py" else ["bash"]
    return subprocess.run([*interpreter, str(path), *args], cwd=root, input=stdin, capture_output=True, text=True, check=False,
                          env=hook_env(root, **env))


def has(errors: list[str], phrase: str) -> bool:
    return any(phrase in e for e in errors)


# ---------------------------------------------------------------------------------------------
print("testing.py — what a tester's hand-in is refused for")
testing = load(HOOKS / "testing.py")
r = project()
CONTRACT = "# discount\n\n## Behaviours\n- A discount of 10% is applied to orders over 100.\n- The total is rounded half-up to cents.\n"
(r / ".engine/slices").mkdir(parents=True)
(r / ".engine/slices/discount.md").write_text(CONTRACT, encoding="utf-8")
(r / "tests").mkdir()
(r / "tests/test_discount.py").write_text("def test_over_100():\n    assert False\n", encoding="utf-8")
(r / "src").mkdir()
(r / "src/discount.py").write_text("def discount(total):\n    return total\n", encoding="utf-8")
REQUEST = {"id": "20261008T120000Z-aaaaaa", "agent": "slice-tester", "mode": "contract", "slice": "discount", "expect": "red"}
GOOD_TEST = {"test": "tests/test_discount.py::test_over_100", "file": "tests/test_discount.py", "behaviour": "10% over 100",
             "contract_line": "A discount of 10% is applied to orders over 100."}
GOOD = {"mode": "contract", "slice": "discount", "run": "python3 -m pytest {test}", "tests": [GOOD_TEST], "questions": []}
check("a hand-in in the right shape has nothing wrong with it (the cases below each break one thing)",
      testing.handin_errors(r, REQUEST, GOOD) == [], testing.handin_errors(r, REQUEST, GOOD))
check("another slice's hand-in is refused", has(testing.handin_errors(r, REQUEST, GOOD | {"slice": "pricing"}), "must repeat the request: 'contract', 'discount'"))
check("another mode's hand-in is refused", has(testing.handin_errors(r, REQUEST, GOOD | {"mode": "block"}), "must repeat the request"))
check("`run` without the {test} placeholder is refused: the script must run ONE test",
      has(testing.handin_errors(r, REQUEST, GOOD | {"run": "python3 -m pytest"}), "`run` is the command that runs ONE test"))
for label, broken in (("no tests", []), ("tests not a list", "all of them"), ("a test that is not an object", ["test_over_100"])):
    check(f"{label}: refused", testing.handin_errors(r, REQUEST, GOOD | {"tests": broken}) == ["`tests` is a non-empty list of objects"],
          testing.handin_errors(r, REQUEST, GOOD | {"tests": broken}))
check("a question without the reading the tester took is refused",
      testing.handin_errors(r, REQUEST, GOOD | {"questions": [{"id": "Q1", "text": "inclusive?"}]}) == ["`questions` is a list of {id, text, reading_taken} — or an empty list"])
check("a test without its behaviour is refused", has(testing.handin_errors(r, REQUEST, GOOD | {"tests": [GOOD_TEST | {"behaviour": " "}]}), "every test has `test`"))
check("the same test listed twice is refused", has(testing.handin_errors(r, REQUEST, GOOD | {"tests": [GOOD_TEST, GOOD_TEST]}), "listed twice"))
check("a behaviour with no line of the contract behind it is an invented requirement",
      has(testing.handin_errors(r, REQUEST, GOOD | {"tests": [GOOD_TEST | {"contract_line": "Orders over 100 ship free."}]}), "invented requirement"))
check("a test file that does not exist is refused",
      has(testing.handin_errors(r, REQUEST, GOOD | {"tests": [GOOD_TEST | {"file": "tests/test_missing.py"}]}), "tests/test_missing.py is not an existing test file"))
check("...and so is the implementation passed off as a test file",
      has(testing.handin_errors(r, REQUEST, GOOD | {"tests": [GOOD_TEST | {"file": "src/discount.py"}]}), "src/discount.py is not an existing test file"))
check("a test that leans on a question nobody asked is refused",
      has(testing.handin_errors(r, REQUEST, GOOD | {"tests": [GOOD_TEST | {"question": "Q9"}]}), "'Q9' is not the id of one of `questions`"))
check("the code exists (catch-up): every test must say what breakage it would catch",
      has(testing.handin_errors(r, REQUEST | {"expect": "recorded"}, GOOD), "`catches` names the breakage"))

print("testing.py — RED before the code: a `keeps` test must pass, any other must fail")
keeps = GOOD | {"run": "bash -c 'exit 1' {test}", "tests": [GOOD_TEST | {"keeps": True}]}
errors, results = testing.red_errors(r, REQUEST, keeps)
check("a test marked `keeps` that fails before the change is refused", has(errors, "marked `keeps`") and results[0]["outcome"] == "failed", errors)
errors, _ = testing.red_errors(r, REQUEST, GOOD | {"run": "bash -c 'exit 0' {test}"})
check("a contract test green against the skeleton is refused", has(errors, "PASSES against the skeleton"), errors)
errors, results = testing.red_errors(r, REQUEST, GOOD | {"run": "no-such-runner-086 {test}"})
check("a runner that is not installed is not a RED", has(errors, "could not run (exit 127)") and has(errors, "not a result of the test"), errors)
check("a run that hit the time limit is no result", testing.Run("t", None, "").outcome == "no result (time limit)")

print("testing.py — a dispute's answer")
OBJECTION = {"id": "20261008T120000Z-bbbbbb", "agent": "slice-tester", "mode": "objection", "slice": "discount", "round": 1}
ITEM = {"test": "tests/test_discount.py::test_over_100", "verdict": "test_right", "reason": "the contract says over 100"}
check("an answer for another slice is refused",
      testing.record_objection(r, OBJECTION, {"mode": "objection", "slice": "pricing", "items": [ITEM]}) == ["`mode` and `slice` must repeat the request: 'objection', 'discount'"])
for label, items in (("no items", []), ("a verdict outside the three", [ITEM | {"verdict": "builder_right"}]), ("an item without a reason", [ITEM | {"reason": ""}])):
    got = testing.record_objection(r, OBJECTION, {"mode": "objection", "slice": "discount", "items": items})
    check(f"{label}: refused", len(got) == 1 and "`items` is a non-empty list" in got[0], got)
check("nothing of the refused answers reached the ledger", not (r / testing.LEDGER_REL).exists())

print("testing.py — the manager's decision")
FACTS_A = {"point": "a", "slice": "discount", "hardest_seams": ["rounding"]}
FACTS_B = {"point": "b", "slice": "discount", "events_due": [], "mutation_cmd_set": False}
check("a decision that is no object is refused", testing.schema_errors(["tester"], FACTS_A) == ["the decision is not a JSON object"])
check("point (a): a word other than tester or builder is refused",
      has(testing.schema_errors({"point": "a", "slice": "discount", "decision": "nobody", "reason": "x"}, FACTS_A), "`decision` is `tester` or `builder`"))
check("point (b): checks without all three kinds are refused",
      has(testing.schema_errors({"point": "b", "slice": "discount", "reason": "x", "checks": {"catch_up": {"when": "none", "reason": "x"}}}, FACTS_B),
          "`checks` holds exactly these keys"))
NONE = {"when": "none", "reason": "nothing to check"}
bad_when = {"point": "b", "slice": "discount", "reason": "x", "checks": {"catch_up": NONE, "integration": {"when": "later", "reason": "x"}, "mutation": NONE}}
check("point (b): a `when` outside now/defer/none is refused", has(testing.schema_errors(bad_when, FACTS_B), "`checks.integration` needs `when`"))
written = testing.enforced(bad_when, FACTS_B, "refused twice")
check("refused twice: the script writes `none` where the manager gave no valid answer, and keeps what it said",
      written["checks"]["integration"] == {"when": "none", "reason": "no valid decision of the manager for this check"}
      and written["checks"]["catch_up"] == NONE and written["by_script"] is True and written["manager_said"] == bad_when, written)

print("testing.py — requests that are refused")
check("the manager is not asked about a slice with no contract", testing.request_manager(r, {}, "nowhere", "a")[0] == 2)
check("nor the tester", testing.request_tester(r, "nowhere", "contract", None)[0] == 2)
code, note = testing.request_tester(r, "discount", "block", None)
check("integration tests are written only after the manager said `integration: now`", code == 1 and "REFUSED: integration tests" in note, note)
code, note = testing.request_tester(r, "discount", "contract", None)
check("the tester is not called before the manager decided it is needed", code == 1 and "nobody decided" in note, note)
check("none of the refusals left a pending request", testing.pending(r) is None)
code, note = testing.mutation_result(r, "discount", 3, 1, "x")
check("a mutation result with no run recorded is refused", code == 1 and "no mutation run is recorded" in note, note)
testing.append_row(r, {"type": "decision", "point": "b", "slice": "discount", "checks": {"mutation": {"when": "now", "reason": "a large block"}}}, "t", [])
code, note = testing.mutation(r, {"MUTATION_CMD": ""}, "discount", 5)
check("a mutation run with MUTATION_CMD empty is refused: the engine installs no tool", code == 1 and "MUTATION_CMD is empty" in note, note)
code, out = quiet(testing.main, ["request", "discount"])
check("`request` with neither --point nor --tester is a usage error", code == 2 and "one of --point a|b" in out, out)

print("testing.py — the audit gate reads the recorded decision again")
gate_root = project()
(gate_root / ".engine/slices").mkdir(parents=True)
(gate_root / ".engine/slices/discount.md").write_text(CONTRACT, encoding="utf-8")
check("no sealed contract: testing does not stand in the way", testing.audit_block(gate_root, "discount") is None)
(gate_root / testing.CONTRACT_SEALS_REL).mkdir(parents=True)
(gate_root / testing.CONTRACT_SEALS_REL / "discount.sha256").write_text("0" * 64 + "\n", encoding="utf-8")
check("a sealed contract with no decision at point (a) holds the audit", "no decision of the testing manager" in (testing.audit_block(gate_root, "discount") or ""))
request = testing.new_request(gate_root, {"agent": "test-manager", "point": "a", "slice": "discount", "facts": FACTS_A})
testing.append_row(gate_root, {"type": "decision", "point": "a", "slice": "discount", "decision": "builder", "reason": "small", "request": request["id"]}, "t", [])
why = testing.audit_block(gate_root, "discount") or ""
check("a recorded «builder» that contradicts a mandatory case (a hardest seam) holds the audit, whoever wrote the row",
      "contradicts a mandatory case" in why and "O1" in why, why)

print("testing.py — the overseer's BLOCKs on check #4 are counted for the next slice")
(r / ".claude/state/overseer").mkdir(parents=True)
(r / testing.OVERSEER_ROWS_REL).write_text("\n".join([
    json.dumps({"slice": "discount", "verdict": "BLOCK", "check": 4}), "not json",
    json.dumps({"slice": "discount", "verdict": "BLOCK", "check": 7}), json.dumps({"slice": "pricing", "verdict": "BLOCK", "check": 4}),
    json.dumps({"slice": "discount", "verdict": "PASS", "check": None}), json.dumps({"slice": "discount", "verdict": "BLOCK", "check": 4}), json.dumps([4])]) + "\n",
    encoding="utf-8")
check("only this slice's BLOCKs on check 4 count; a broken line is stepped over", testing.overseer_blocks_4(r, "discount") == 2, testing.overseer_blocks_4(r, "discount"))
check("no verdict file: none", testing.overseer_blocks_4(gate_root, "discount") == 0)

# ---------------------------------------------------------------------------------------------
print("lesson_queue.py — a proposal that may not become a rule")
lessons = load(HOOKS / "lesson_queue.py")
r = project()
(r / ".engine").mkdir()


def propose(ident: str, rule: str, state: str = "PROPOSED") -> None:
    with (r / lessons.PROPOSALS_REL).open("a", encoding="utf-8") as handle:
        handle.write(f"\n## RP-{ident} — 2026-10-08 — {state}\n- Rule: {rule}\n- Why: it bit twice\n- From: a lesson\n- Status: {state}\n")


propose("aaaa1111", "Read @.claude/secret-notes.md before every commit.")
propose("bbbb2222", "Run the fast suite before staging.", "REJECTED")
propose("cccc3333", "Name the file you are editing.")
ok, note = lessons.promote(r, "aaaa1111", owner_flag=True)
check("a rule whose text holds an @path is never promoted, the owner's flag or not: CLAUDE.md would load the path as an import",
      ok is False and "@path" in note and not (r / lessons.RULES_REL).exists(), note)
ok, note = lessons.promote(r, "bbbb2222", owner_flag=True)
check("a rejected proposal is not promoted", ok is False and "already REJECTED" in note and not (r / lessons.RULES_REL).exists(), note)
ok, note = lessons.promote(r, "dddd4444", owner_flag=True)
check("an unknown proposal is not promoted", ok is False and "no proposal RP-dddd4444" in note, note)
ok, note = lessons.promote(r, "cccc3333")
check("without the owner's «так» nothing is promoted", ok is False and "the owner has not said" in note and not (r / lessons.RULES_REL).exists(), note)
ok, note = lessons.promote(r, "cccc3333", owner_flag=True, in_session=True)
check("inside a session the owner's flag does not count", ok is False and not (r / lessons.RULES_REL).exists(), note)
ok, note = lessons.ask_owner(r, "bbbb2222")
check("a closed proposal is not asked of the owner again", ok is False and "already REJECTED" in note, note)
ok, note = lessons.reject(r, "bbbb2222", "no")
check("...nor rejected twice", ok is False and "already REJECTED" in note, note)
ok, note = lessons.promote(r, "cccc3333", owner_flag=True)
check("the positive case: the owner's flag outside a session promotes the clean rule",
      ok is True and "- Name the file you are editing. (RP-cccc3333," in (r / lessons.RULES_REL).read_text(encoding="utf-8"), note)
ok, note = lessons.promote(r, "cccc3333", owner_flag=True)
check("...once", ok is False and "already APPROVED" in note and (r / lessons.RULES_REL).read_text(encoding="utf-8").count("RP-cccc3333") == 1, note)

# ---------------------------------------------------------------------------------------------
print("complexity_budget.py — a budget that cannot be measured is not a budget that passed")
budget = load(HOOKS / "complexity_budget.py")
r = project()
head = git(r, "rev-parse", "HEAD").stdout.strip()
(r / ".engine/slices").mkdir(parents=True)


def contract(name: str, *lines: str) -> Path:
    path = r / ".engine/slices" / f"{name}.md"
    path.write_text(f"# {name}\n\n## Complexity budget\n" + "".join(f"- {line}\n" for line in lines) + "\n## Exit\n- done\n", encoding="utf-8")
    return path


def budget_error(path: Path) -> str:
    try:
        budget.parse_budget(path)
    except budget.BudgetError as exc:
        return str(exc)
    return ""


CORE = ("max_new_files: 1", "max_new_dependencies: 0", "max_cyclomatic_per_function: 10")
check("the positive case: a whole budget is read", budget.parse_budget(contract("ok", f"base_commit: {head}", *CORE)).limits["max_new_files"] == 1)
check("a limit that is no whole number is an error, not a missing limit",
      "max_new_files must be a whole number, got 'a few'" in budget_error(contract("words", f"base_commit: {head}", "max_new_files: a few")))
check("a budget without its base commit is an error", "base_commit is missing" in budget_error(contract("nobase", *CORE)))
check("a mode other than hard or signal is an error", "mode must be 'hard' or 'signal'" in budget_error(contract("mode", f"base_commit: {head}", "mode: soft", *CORE)))
check("a misspelt field is an error: a typo must not switch a limit off",
      "unknown budget field 'max_new_file'" in budget_error(contract("typo", f"base_commit: {head}", "max_new_file: 1")))
outcome = budget.evaluate(r, contract("ghost", "base_commit: 0123456789abcdef0123456789abcdef01234567", *CORE))
check("a base commit that is not in the repository reads as EXCEEDED, never as within budget",
      outcome is not None and outcome.exceeded is True and "is not a commit in this repository" in outcome.text, outcome)
outcome = budget.evaluate(r, contract("typo", f"base_commit: {head}", "max_new_file: 1"))
check("...and so does a budget that cannot be read", outcome is not None and outcome.exceeded is True and "cannot be read" in outcome.text, outcome)
done = script(HOOKS / "complexity_budget.py", r, "validate", str(contract("abstr", f"base_commit: {head}", "max_new_abstractions: 2", *CORE)))
check("validate: new abstractions without a justification are INVALID",
      done.returncode == 1 and "max_new_abstractions above 0 needs a justification" in done.stdout, done.stdout + done.stderr)
done = script(HOOKS / "complexity_budget.py", r, "validate", str(contract("words", f"base_commit: {head}", "max_new_files: a few")))
check("validate: an unreadable budget is INVALID", done.returncode == 1 and "INVALID: max_new_files must be a whole number" in done.stdout, done.stdout + done.stderr)
done = script(HOOKS / "complexity_budget.py", r, "validate", str(contract("ok", f"base_commit: {head}", *CORE)))
check("validate: the whole budget passes", done.returncode == 0, done.stdout + done.stderr)

# ---------------------------------------------------------------------------------------------
print("goals.py — what may be sealed")
goals = load(HOOKS / "goals.py")
r = project()
code, out = quiet(goals.cmd_seal, r, True, False)
check("no goals document: nothing to seal", code == goals.EXIT_NONE and "no goals document" in out, out)
(r / ".engine").mkdir()
(r / goals.GOALS_REL).write_text("# Goals\n\nWe want it to be good.\n", encoding="utf-8")
code, out = quiet(goals.cmd_seal, r, True, False)
check("a document with no numbered line is not sealed: nothing a decision could cite",
      code == goals.EXIT_REFUSED and "has no numbered line" in out and goals.state(r) == "unsealed", out)
(r / goals.GOALS_REL).write_text("# Goals\n\n- G1. Fast.\n- G1. Cheap.\n", encoding="utf-8")
code, out = quiet(goals.cmd_seal, r, True, False)
check("a number used twice is not sealed", code == goals.EXIT_REFUSED and "G1 is numbered twice" in out and goals.state(r) == "unsealed", out)
(r / goals.GOALS_REL).write_text("# Goals\n\n- G1. Fast.\n- G2. Cheap.\n", encoding="utf-8")
code, out = quiet(goals.cmd_seal, r, False, False)
check("the positive case: the first approval seals", code == goals.EXIT_OK and goals.state(r) == "sealed", out)
code, out = quiet(goals.cmd_seal, r, False, False)
check("sealing a sealed document says so and changes nothing", code == goals.EXIT_OK and out.strip() == goals.STATE_TEXT["sealed"], out)
(r / goals.GOALS_REL).write_text("# Goals\n\n- G1. Fast.\n- G2. Cheap.\n- G3. Whatever the agent adds.\n", encoding="utf-8")
code, out = quiet(goals.cmd_seal, r, False, False)
check("a changed document is not sealed again without the owner", code == goals.EXIT_REFUSED and goals.state(r) == "changed", out)
code, out = quiet(goals.cmd_seal, r, True, True)
check("...and inside a session the owner's flag does not count", code == goals.EXIT_USAGE and goals.state(r) == "changed", out)
(r / ".engine/goals").mkdir()
(r / goals.PROPOSED_REL).write_text("# Goals\n\n- G1. Fast.\n- G2. Cheap.\n- G4. New.\n", encoding="utf-8")
code, out = quiet(goals.amend, r, goals.digest(r / goals.PROPOSED_REL), False)
check("an amendment is applied to the approved document only, never over a changed one",
      code == 1 and "applied to the approved document only" in out and "G3" in (r / goals.GOALS_REL).read_text(encoding="utf-8"), out)
code, out = quiet(goals.cmd_check, r, [])
check("check: a changed document is not in force", code == goals.EXIT_REFUSED and "CHANGED" in out, out)

# ---------------------------------------------------------------------------------------------
print("hotfix.py — a debt is written for an urgent fix only")
r = project()
(r / ".engine/hotfix").mkdir(parents=True)
(r / ".engine/hotfix/001-login.md").write_text("# login\n\n- Symptom: nobody can log in\n", encoding="utf-8")
done = script(HOOKS / "hotfix.py", r, "debt", "--record", ".engine/hotfix/001-login.md")
check("a card that is not an urgent fix leaves no debt", done.returncode == 2 and "is not the card of an urgent fix" in done.stdout
      and not (r / ".engine/debt.md").exists(), done.stdout + done.stderr)
(r / ".engine/hotfix/002-pay.md").write_text("# pay\n\ntype: hotfix\n\n- Symptom: payments fail\n", encoding="utf-8")
done = script(HOOKS / "hotfix.py", r, "debt", "--record", ".engine/hotfix/002-pay.md")
check("an urgent fix whose card has no budget section leaves no debt: the hard limit cannot be measured",
      done.returncode == 1 and "has no `## Complexity budget` section" in done.stdout and not (r / ".engine/debt.md").exists(), done.stdout + done.stderr)
done = script(HOOKS / "hotfix.py", r, "close", "--record", ".engine/hotfix/002-pay.md", "--bugfix", ".engine/bugs/002-pay.md")
check("closing a debt that was never written is refused", done.returncode == 2 and "has no debt named 002-pay" in done.stdout, done.stdout + done.stderr)

# ---------------------------------------------------------------------------------------------
print("the deny hooks without their list of protected paths refuse, they do not wave the call through")


def hooks_copy(without: str = "") -> Path:
    """A copy of the hooks directory, as an install lays it, optionally with one file missing."""
    target = Path(sandbox_dir("refusal-hooks-")) / ".claude" / "hooks"
    shutil.copytree(HOOKS, target, ignore=shutil.ignore_patterns("__pycache__"))
    if without:
        (target / without).unlink()
    return target


def envelope(tool: str, **tool_input: str) -> str:
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})


r = project()
whole, broken = hooks_copy(), hooks_copy(without="protected-path-list.sh")
done = script(whole / "block-dangerous.sh", r, stdin=envelope("Bash", command="ls -la"))
check("the positive case: with the list beside it block-dangerous.sh lets `ls` through", done.returncode == 0, done.stderr)
done = script(broken / "block-dangerous.sh", r, stdin=envelope("Bash", command="ls -la"))
check("block-dangerous.sh without the list: the command cannot be checked, so it is refused (exit 2)",
      done.returncode == 2 and "protected-path-list.sh" in done.stderr and "cannot be checked" in done.stderr, done.stderr)
done = script(whole / "protect-paths.sh", r, stdin=envelope("Edit", file_path=str(r / "src/app.py")))
check("the positive case: with the list protect-paths.sh lets an ordinary file through", done.returncode == 0 and "deny" not in done.stdout, done.stdout + done.stderr)
done = script(broken / "protect-paths.sh", r, stdin=envelope("Edit", file_path=str(r / "src/app.py")))
check("protect-paths.sh without the list: refused (exit 2), with the way to restore it",
      done.returncode == 2 and "protected-path-list.sh" in done.stderr and "engine.py update" in done.stderr, done.stderr)

print("a hook that needs python3 says so when there is none")


def path_without(*absent: str) -> str:
    """A PATH holding links to the tools the shell hooks use — except the ones named."""
    folder = Path(sandbox_dir("refusal-path-"))
    for tool in ("bash", "sh", "cat", "dirname", "basename", "git", "grep", "sed", "tr", "head", "cut", "jq", "python3", "env", "date", "id", "uname", "pwd", "ls", "rm", "mktemp"):
        found = shutil.which(tool)
        if found and tool not in absent:
            (folder / tool).symlink_to(found)
    return str(folder)


BASH = shutil.which("bash") or "bash"


def bare(path: Path, root: Path, search: str, *args: str, stdin: str = "", **extra: str) -> subprocess.CompletedProcess[str]:
    """The script in an environment built from nothing: this PATH and the project, no more."""
    env = {"PATH": search, "HOME": os.environ.get("HOME", "/"), "CLAUDE_PROJECT_DIR": str(root), **extra, **trace_env()}
    return subprocess.run([BASH, str(path), *args], cwd=root, input=stdin, capture_output=True, text=True, check=False, env=env)


no_python = path_without("python3")
done = bare(HOOKS / "verify-on-stop.sh", r, no_python, stdin="{}")
check("verify-on-stop.sh without python3 BLOCKS the turn: a Stop gate that cannot run must not read as verified",
      done.returncode == 2 and "python3 is required" in done.stderr and "not verified" in done.stderr, done.stdout + done.stderr)
(r / "notes.json").write_text('{"b":1,   "a":2}\n', encoding="utf-8")
before = (r / "notes.json").read_text(encoding="utf-8")
done = bare(HOOKS / "format-on-edit.sh", r, no_python, stdin=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(r / "notes.json")}}))
check("format-on-edit.sh without python3 formats nothing, says so, and never fails the edit",
      done.returncode == 0 and "python3 not found" in done.stderr and (r / "notes.json").read_text(encoding="utf-8") == before, done.stdout + done.stderr)

print("env-check.sh and env-probe.sh — the cases nothing ran")
poetry = project()
(poetry / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
(poetry / "poetry.lock").write_text("", encoding="utf-8")
done = bare(HOOKS / "env-check.sh", poetry, path_without("poetry"), ENGINE_PROC_VERSION="/nonexistent/version")
check("a project with poetry.lock on a machine without poetry is told so at the start of the session",
      done.returncode == 0 and "missing on this machine" in done.stdout and "- poetry — this project has poetry.lock" in done.stdout, done.stdout + done.stderr)
done = bare(UNATTENDED / "env-probe.sh", r, path_without(), CLAUDE_UNATTENDED_SESSION="1")
check("env-probe.sh names a supervised unattended session", "unattended-supervised" in done.stdout and "attended-local" not in done.stdout, done.stdout + done.stderr)
(r / ".claude/state/overseer").mkdir(parents=True)
(r / ".claude/state/overseer/mode").write_text("unattended\n", encoding="utf-8")
done = bare(UNATTENDED / "env-probe.sh", r, path_without())
check("...and one that is unattended by the mode file alone", "unattended-mode-file" in done.stdout and "attended-local" not in done.stdout, done.stdout + done.stderr)

print("commit_checkpoint.sh — the last line of defence is the script's own")
CHECKPOINT = UNATTENDED / "commit_checkpoint.sh"


def staged_repo(branch: str) -> Path:
    root = project("refusal-checkpoint-")
    if branch != "main":
        git(root, "switch", "-qc", branch)
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    git(root, "add", "README.md")
    return root


def commits(root: Path) -> int:
    return int(git(root, "rev-list", "--count", "--all").stdout.strip() or 0)


AUTHOR = {"GIT_AUTHOR_NAME": "t", "GIT_COMMITTER_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_EMAIL": "t@t"}
on_main = staged_repo("main")
shim = Path(path_without("git"))
(shim / "git").write_text(f'#!{BASH}\n# A git whose `switch` reports success and switches nothing.\n'
                          f'for word in "$@"; do [ "$word" = switch ] && exit 0; done\nexec {shutil.which("git")} "$@"\n', encoding="utf-8")
(shim / "git").chmod(0o755)
done = bare(CHECKPOINT, on_main, str(shim), "unit-1", **AUTHOR)
check("a `git switch` that did not switch: the script re-reads the branch and REFUSES to commit on main",
      done.returncode == 1 and "REFUSING to commit on branch 'main'" in done.stderr and commits(on_main) == 1
      and git(on_main, "branch", "--show-current").stdout.strip() == "main", done.stdout + done.stderr)
done = bare(CHECKPOINT, on_main, path_without(), "unit-1", **AUTHOR)
check("the positive case: with a git that switches, the same change is committed on unattended/<date>",
      done.returncode == 0 and commits(on_main) == 2 and git(on_main, "branch", "--show-current").stdout.strip().startswith("unattended/"), done.stdout + done.stderr)
refused = staged_repo("unattended/2026-10-08")
hook = refused / ".git/hooks/pre-commit"
hook.parent.mkdir(exist_ok=True)
hook.write_text(f"#!{BASH}\nexit 1\n", encoding="utf-8")
hook.chmod(0o755)
done = bare(CHECKPOINT, refused, path_without(), "unit-2", **AUTHOR)
check("a commit that git refuses is a failure of the checkpoint (exit 1), never a silent success",
      done.returncode == 1 and "commit failed for unit-2" in done.stderr and commits(refused) == 1, done.stdout + done.stderr)

# ---------------------------------------------------------------------------------------------
print("engine.py — an ownership file that is wrong stops the installer")
engine = load(ROOT / "engine.py")


def ownership_error(text: str) -> str:
    try:
        engine.parse_ownership(text)
    except engine.EngineError as exc:
        return str(exc)
    return ""


check("the positive case: a rule with a seed is read",
      [(x.owner, x.pattern, x.seed) for x in engine.parse_ownership("# who owns what\nproject CLAUDE.md seed=templates/project/CLAUDE.md\nengine .claude/hooks/**\n")]
      == [("project", "CLAUDE.md", "templates/project/CLAUDE.md"), ("engine", ".claude/hooks/**", None)])
check("a line with one field", "expected '<owner> <pattern> [seed=<file>]'" in ownership_error("engine\n"))
check("a line with four", "expected '<owner> <pattern>" in ownership_error("engine a b c\n"))
check("an owner nobody defined", "unknown owner 'nobody'" in ownership_error("nobody docs/**\n"))
check("a third field that is no seed", "the third field must be seed=<file>" in ownership_error("project CLAUDE.md template\n"))
check("an empty seed", "the third field must be seed=<file>" in ownership_error("project CLAUDE.md seed=\n"))
check("a seed for a file the engine owns", "only project files have a seed" in ownership_error("engine CLAUDE.md seed=x.md\n"))
check("a seed for a pattern", "a seeded rule must name exactly one file" in ownership_error("project docs/*.md seed=x.md\n"))
check("a seed for a directory", "a seeded rule must name exactly one file" in ownership_error("project docs/ seed=x.md\n"))
check("a file of comments only", "has no rules" in ownership_error("# nothing yet\n\n"))
rules = engine.parse_ownership("engine .claude/hooks/gate.p?\nuser user/**\n")
check("`?` is one character and never a slash", engine.owner_of(rules, ".claude/hooks/gate.py") == "engine"
      and engine.owner_of(rules, ".claude/hooks/gate.p/") is None and engine.owner_of(rules, ".claude/hooks/gate.pyc") is None)
check("a path no rule names has no owner and never ships", engine.owner_of(rules, "docs/readme.md") is None)

# ---------------------------------------------------------------------------------------------
print("baseline.py — a snapshot of the wrong shape is no snapshot")
baseline = load(HOOKS / "baseline.py")
part = baseline.COUNTED[0]
check("the positive case: a snapshot is read, zero counts dropped",
      (baseline.parse(json.dumps({"tests": ["t::b", "t::a"], part: {"a.py": {"E501": 2, "F401": 0}}})) or {}).get(part) == {"a.py": {"E501": 2}})
check("not an object", baseline.parse("[1, 2]") is None)
check("tests that are not a list", baseline.parse(json.dumps({"tests": "all of them"})) is None)
check("a counted part that is not a table", baseline.parse(json.dumps({"tests": [], part: ["a.py"]})) is None)
check("a file whose rules are not a table", baseline.parse(json.dumps({"tests": [], part: {"a.py": 3}})) is None)
check("not JSON at all", baseline.parse("{") is None and baseline.parse(None) is None)

# ---------------------------------------------------------------------------------------------
print("owner_action.py — an answer about something that is no longer there does nothing")
owner = load(UNATTENDED / "owner_action.py")
r = project()
code, out = quiet(owner.apply_settings, r, "0" * 64)
check("apply-settings with no proposal: stale, nothing applied", code == owner.EXIT_STALE and "one is missing" in out and not (r / owner.LIVE).exists(), out)
code, out = quiet(owner.reject_rule, r, "f" * 64)
check("a «ні» for a rule proposal nobody made: stale", code == owner.EXIT_STALE and "nothing to close" in out, out)
code, out = quiet(owner.update_deps, r, "0" * 64)
check("update-deps with no list: stale", code == owner.EXIT_STALE and "it is missing" in out, out)
(r / ".engine/maintain").mkdir(parents=True)
(r / owner.UPDATES).write_text("[]\n", encoding="utf-8")
code, out = quiet(owner.update_deps, r, "0" * 64)
check("update-deps with a list that changed after the owner's answer: stale, nothing updated", code == owner.EXIT_STALE and "nothing is updated" in out, out)
approved = hashlib.sha256((r / owner.UPDATES).read_bytes()).hexdigest()
code, out = quiet(owner.update_deps, r, approved)
check("update-deps on main: refused — every update is a commit, and commits are made on unattended/* only",
      code == owner.EXIT_REFUSED and "unattended/* branch only" in out and git(r, "rev-list", "--count", "HEAD").stdout.strip() == "1", out)

print("settings_check.py — a settings file of the wrong shape")
settings = load(UNATTENDED / "settings_check.py")


def shape_error(value: object) -> str:
    try:
        settings.handlers(value)
    except TypeError as exc:
        return str(exc)
    return ""


WIRED = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" record'}, {"type": "prompt"}]}]}}
check("the positive case: handlers are listed; one without a command is not a handler",
      settings.handlers(WIRED) == [("Stop", 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" record')])
check("`hooks` that is a list", shape_error({"hooks": []}) == "`hooks` is not an object")
check("an event that is not a list", shape_error({"hooks": {"Stop": {}}}) == "`hooks.Stop` is not a list")
check("a group without its handlers", shape_error({"hooks": {"Stop": [{"matcher": "x"}]}}) == "a group of `hooks.Stop` has no list of handlers")
check("an unreadable shape wires no overseer handler", settings.overseer_handlers({"hooks": {"Stop": "all"}}) == set()
      and settings.overseer_handlers(WIRED) == {("Stop", "record")})
done = script(UNATTENDED / "settings_check.py", r, "--root", str(r))
check("no proposal and no live settings: exit 2, said", done.returncode == settings.EXIT_MISSING and "is missing" in done.stderr, done.stdout + done.stderr)

print("board_state.py — a command it does not know changes nothing")
state_dir = Path(sandbox_dir("refusal-state-"))
done = script(UNATTENDED / "board_state.py", r, str(state_dir), "begin", "001-task")
check("the positive case: begin writes the task", done.returncode == 0 and "001-task" in (state_dir / "costs.json").read_text(encoding="utf-8"), done.stderr)
before = (state_dir / "costs.json").read_text(encoding="utf-8")
done = script(UNATTENDED / "board_state.py", r, str(state_dir), "finish", "001-task")
check("finish without an outcome: exit 2, the file untouched", done.returncode == 2 and "cannot finish" in done.stderr
      and (state_dir / "costs.json").read_text(encoding="utf-8") == before, done.stderr)
done = script(UNATTENDED / "board_state.py", r, str(state_dir), "begin")
check("a command without its task: exit 2", done.returncode == 2 and "needs a task" in done.stderr, done.stderr)
done = script(UNATTENDED / "board_state.py", r, str(state_dir), "get", "001-task", "colour")
check("an unknown field is an error, never an empty answer the runner would read as zero",
      done.returncode != 0 and "unknown field 'colour'" in done.stderr and done.stdout.strip() == "", done.stdout + done.stderr)

# ---------------------------------------------------------------------------------------------
print("gate.py — a check that does not finish")
gate = load(HOOKS / "gate.py")
gate.STEP_TIMEOUT_S = 1
rc, out, _ = gate.run_shell(r, "sleep 5")
check("a step past its time limit fails (124) and says so: a hung check is not a passed one", rc == 124 and "timed out after 1 s" in out, (rc, out))
rc, out, _ = gate.run_shell(r, "echo done")
check("(a step that finishes is its own exit code)", rc == 0 and out.strip() == "done", (rc, out))

print("overseer_verdict.py — the evidence the overseer is given, and a request by hand")
verdict = load(HOOKS / "overseer_verdict.py")
text = verdict.render_evidence([], True)
check("a turn that called no tool is said to have run nothing", "No tool was called in this turn" in text, text)
text = verdict.render_evidence([
    {"tool": "Bash", "input": {"command": "pytest -q"}, "result": "", "is_error": False},
    {"tool": "Bash", "input": {"command": "ruff check"}, "result": None, "is_error": True},
    {"tool": "Agent", "input": {"subagent_type": "overseer", "prompt": "OVERSEER_REQUEST 1"}, "result": "x", "is_error": False},
    {"tool": "Read", "input": {"file_path": "a.py"}, "result": "x", "is_error": False}], True)
check("a command with no output is shown as such, not as missing", "1. Bash: `pytest -q`\n   (no output)" in text, text)
check("a command with no recorded result is told apart from one with none to show", "2. Bash (FAILED): `ruff check`\n   (no result recorded)" in text, text)
check("an earlier audit and any other tool are listed in their place", "3. — an overseer audit ran here" in text and "4. Read" in text, text)
entry = verdict.ledger_entry({"utc": "2026-10-08T12:00:00Z", "request": "r1", "slice": "s", "unit_key": "u", "attempt": 1, "verdict": "ESCALATE",
                              "reason": "the owner's threshold", "check": None},
                             {"verdict": "ESCALATE", "escalation": {"question": "Is 5% the threshold?"}, "evidence": ["a ledger entry"]})
check("an ESCALATE carries its question into the ledger", "- Escalation:" in entry and "Is 5% the threshold?" in entry, entry)
plain = verdict.ledger_entry({"utc": "2026-10-08T12:00:00Z", "request": "r1", "slice": "s", "unit_key": "u", "attempt": 1, "verdict": "PASS",
                              "reason": "every claim has its evidence", "check": None}, {"verdict": "PASS", "evidence": ["a ledger entry"]})
check("(a PASS carries none)", "Escalation" not in plain, plain)

print("gate_allows.py — how an exemption without a reason reads to the overseer")
allows = load(HOOKS / "gate_allows.py")
shown = allows.render([allows.Allow("a.py", 3, "noqa", "E501", "", False), allows.Allow("b.py", 9, "noqa", "F401", "ok", False),
                       allows.Allow("c.py", 1, "contract", "PROJECT_MARKER", "the marker moved with the package", True)])
check("no reason reads MISSING", "a.py:3 [noqa: E501] reason: MISSING" in shown, shown)
check("a reason too short for the gate is quoted and marked", 'b.py:9 [noqa: F401] reason: "ok" (too short for the gate itself)' in shown, shown)
check("a real reason is quoted as it is", 'c.py:1 [contract: PROJECT_MARKER] reason: "the marker moved with the package"' in shown
      and "too short" not in shown.splitlines()[-1], shown)
check("nothing to judge is the empty string", allows.render([]) == "")

# ---------------------------------------------------------------------------------------------
print("simplifier.py nightly — the command the runner's cleanup task names, run for real (tests/test_cleanup.py puts a fake in its place)")
r = project()
(r / ".claude").mkdir()
(r / ".claude/project.env").write_text('SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\n', encoding="utf-8")
(r / "src").mkdir()
(r / "src/a.py").write_text("def one(x):\n    return x\n\n\nprint(one(1))\n", encoding="utf-8")
git(r, "add", "-A")
git(r, "commit", "-qm", "code")
done = script(HOOKS / "simplifier.py", r, "nightly")
recorded = r / ".claude/state/simplifier/signals-full.json"
check("the first night: the signals are written, nothing to compare with, no call",
      done.returncode == 0 and "signal(s) in .claude/state/simplifier/signals-full.json" in done.stdout
      and "no sharp growth: the nightly cleanup reviews the signals only" in done.stdout and recorded.is_file(), done.stdout + done.stderr)
check("...and the reversal rate is printed for the owner's report", "Reversal rate:" in done.stdout, done.stdout)
(r / "src/b.py").write_text("".join(
    f"def branchy_{i}(x):\n    if x > {i}:\n        for y in range(x):\n            if y % 2:\n                x += y\n    return x\n\n\n" for i in range(40))
    + "print(" + ", ".join(f"branchy_{i}(1)" for i in range(40)) + ")\n", encoding="utf-8")
done = script(HOOKS / "simplifier.py", r, "nightly")
check("a night after the code grew sharply: SIMPLIFIER CALL, with what grew",
      done.returncode == 0 and "SIMPLIFIER CALL: " in done.stdout and "grew from" in done.stdout and "no sharp growth" not in done.stdout, done.stdout + done.stderr)
done = script(HOOKS / "simplifier.py", r, "nightly")
check("every night is recorded: three runs, three rows of history",
      done.returncode == 0 and len((r / ".claude/state/simplifier/metrics.jsonl").read_text(encoding="utf-8").splitlines()) == 3, done.stdout + done.stderr)

# ---------------------------------------------------------------------------------------------
print("engine.py — what an update does to a file the project deleted, a lost executable bit, and an engine that ships a link")
eng = Path(sandbox_dir("refusal-engine-"))
git(eng, "init", "-q", "-b", "main")
OWNERSHIP = ("machine  .claude/state/\n"
             "project  docs/guide.md  seed=templates/guide.md\n"
             "engine   .claude/**\n"
             "project  **\n")
for rel, text, mode in ((".claude/ownership.txt", OWNERSHIP, 0o644), (".claude/hooks/a.sh", "echo a1\n", 0o755),
                        (".claude/hooks/b.sh", "echo b1\n", 0o755), ("templates/guide.md", "# Guide\n", 0o644)):
    (eng / rel).parent.mkdir(parents=True, exist_ok=True)
    (eng / rel).write_text(text, encoding="utf-8")
    (eng / rel).chmod(mode)
git(eng, "add", "-A")
git(eng, "commit", "-qm", "v1")
git(eng, "tag", "v1.0.0")
(eng / ".claude/hooks/a.sh").write_text("echo a2\n", encoding="utf-8")
git(eng, "commit", "-qam", "v2")
git(eng, "tag", "v2.0.0")
(eng / ".claude/hooks/link.sh").symlink_to("a.sh")
git(eng, "add", "-A")
git(eng, "commit", "-qm", "v3: a link among the hooks")
git(eng, "tag", "v3.0.0")
git(eng, "rm", "-q", ".claude/hooks/link.sh", "templates/guide.md")
git(eng, "commit", "-qm", "v4: the seed is gone")
git(eng, "tag", "v4.0.0")
shutil.copy2(ROOT / "engine.py", eng / "engine.py")
PROJECTS = str(eng.parent / (eng.name + "-projects.txt"))


def installer(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(eng / "engine.py"), *args], capture_output=True, text=True, check=False,
                          env={**os.environ, "ENGINE_PROJECTS_FILE": PROJECTS})


target = project("refusal-installed-")
done = installer("install", str(target), "--ref", "v1.0.0")
check("the positive case: v1 installs, with the executable bit and the seed",
      done.returncode == 0 and os.access(target / ".claude/hooks/a.sh", os.X_OK) and (target / "docs/guide.md").read_text(encoding="utf-8") == "# Guide\n",
      done.stdout + done.stderr)
(target / ".claude/hooks/b.sh").unlink()
(target / ".claude/hooks/a.sh").chmod(0o644)
done = installer("update", str(target), "--ref", "v1.0.0")
check("a file the project deleted is not brought back by an update — the update says so and asks for attention (exit 1)",
      done.returncode == 1 and not (target / ".claude/hooks/b.sh").exists() and "deleted in the project" in done.stdout, done.stdout + done.stderr)
check("a hook that lost its executable bit gets it back: a hook that cannot run enforces nothing",
      os.access(target / ".claude/hooks/a.sh", os.X_OK) and "executable bit" in done.stdout, done.stdout + done.stderr)
done = installer("update", str(target), "--ref", "v2.0.0")
check("the next version still leaves the deleted file deleted, and updates the rest",
      done.returncode == 1 and not (target / ".claude/hooks/b.sh").exists() and (target / ".claude/hooks/a.sh").read_text(encoding="utf-8") == "echo a2\n",
      done.stdout + done.stderr)
done = installer("update", str(target), "--ref", "v2.0.0", "--take", ".claude/hooks/b.sh")
check("--take brings it back on request", done.returncode == 0 and (target / ".claude/hooks/b.sh").read_text(encoding="utf-8") == "echo b1\n", done.stdout + done.stderr)
before = (target / ".claude/hooks/a.sh").read_text(encoding="utf-8")
done = installer("update", str(target), "--ref", "v3.0.0")
check("an engine version that holds a symbolic link among its files is refused whole: only files ship",
      done.returncode != 0 and "only files ship" in done.stderr and not (target / ".claude/hooks/link.sh").exists()
      and (target / ".claude/hooks/a.sh").read_text(encoding="utf-8") == before, done.stdout + done.stderr)
done = installer("update", str(target), "--ref", "v4.0.0")
check("an engine version whose ownership map names a seed it does not have is refused",
      done.returncode != 0 and "seed templates/guide.md (for docs/guide.md) is missing" in done.stderr, done.stdout + done.stderr)
done = installer("update")
check("update with neither a project nor --all is refused", done.returncode != 0 and "give either a project directory or --all" in done.stderr, done.stdout + done.stderr)
done = installer("install", "--personal", "--no-register", "--ref", "v1.0.0")
check("--personal with a project install's flag is refused", done.returncode != 0 and "--no-register applies to a project install, not to --personal" in done.stderr,
      done.stdout + done.stderr)
done = installer("install", str(target), "--home", str(eng), "--ref", "v1.0.0")
check("--home with a project install is refused", done.returncode != 0 and "--home applies to --personal only" in done.stderr, done.stdout + done.stderr)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
