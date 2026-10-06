#!/usr/bin/env python3
"""A suite that runs a hook takes the hook's environment from tests/hook_env.py (board 800).

The Stop gate runs TEST_CMD with CLAUDE_PROJECT_DIR naming this repository; by hand the
variable is unset. A suite that lets a hook inherit it is green by hand and red from the gate
(tests/test_deny_gaps.py, 2026-10-02, X7). Three things are held here:

  1. the helper: hook_env() never hands on the inherited value, main_repo() is on `main`;
  2. the mistake itself, on the real block-dangerous.sh: inherited from an unattended/*
     repository the commit is ALLOWED, through the helper it is refused;
  3. the check: every tests/test_*.py that runs a hook imports the helper, or stands in
     tests/hook-env-exempt.txt with its reason. The list holds the suites written before the
     helper and may only shrink: a line for a suite that is gone, runs no hook or already
     uses the helper is itself a finding.

"Runs a hook" is read from the source, coarsely and on the safe side: the suite imports
subprocess and one of its string literals names the hooks or the unattended directory. A
suite that only mentions such a path is exempted by a line saying so.

Run:   python3 tests/test_hook_env.py
Exit:  0 = all green, 1 = at least one case failed.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import hook_env, main_repo, sandbox_dir

TESTS = Path(__file__).resolve().parent
HOOK = TESTS.parent / ".claude" / "hooks" / "block-dangerous.sh"
EXEMPT = "hook-env-exempt.txt"
HOOK_PATH = re.compile(r"(?:^|/)(?:hooks|unattended)(?:/|$)")

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:600]}")


def imports(tree: ast.AST, module: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name == module for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == module:
            return True
    return False


def runs_hook(tree: ast.AST) -> bool:
    literals = (node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str))
    return imports(tree, "subprocess") and any(HOOK_PATH.search(text) for text in literals)


def exemptions(tests: Path) -> tuple[dict[str, str], list[str]]:
    """The exempt list as {suite: reason}, and what is wrong with the list itself."""
    listed: dict[str, str] = {}
    wrong: list[str] = []
    path = tests / EXEMPT
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, _, reason = line.partition("#")
        name, reason = name.strip(), reason.strip()
        if not reason:
            wrong.append(f"{EXEMPT}: {name} has no reason after '#'")
        if name in listed:
            wrong.append(f"{EXEMPT}: {name} is listed twice")
        listed[name] = reason
    return listed, wrong


def findings(tests: Path) -> list[str]:
    """Every way the suites under `tests` break the rule; empty when they keep it."""
    listed, found = exemptions(tests)
    for suite in sorted(tests.glob("test_*.py")):
        try:
            tree = ast.parse(suite.read_text(encoding="utf-8"))
        except SyntaxError as error:
            found.append(f"{suite.name}: cannot be read as Python ({error.msg}, line {error.lineno})")
            continue
        hook, helper, exempt = runs_hook(tree), imports(tree, "hook_env"), suite.name in listed
        if hook and not helper and not exempt:
            found.append(f"{suite.name}: runs a hook without tests/hook_env.py — build the hook's environment with "
                         f"hook_env(<the suite's own project>), which pins CLAUDE_PROJECT_DIR to it")
        if exempt and helper:
            found.append(f"{EXEMPT}: {suite.name} uses the helper now — delete its line")
        if exempt and not hook:
            found.append(f"{EXEMPT}: {suite.name} runs no hook — delete its line")
    for name in sorted(set(listed) - {suite.name for suite in tests.glob("test_*.py")}):
        found.append(f"{EXEMPT}: {name} does not exist — delete its line")
    return found


def blocked(cmd: str, env: dict[str, str]) -> bool:
    done = subprocess.run(["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
                          capture_output=True, text=True, check=False, env=env)
    return done.returncode == 2


def branch_of(repo: str) -> str:
    return subprocess.run(["git", "-C", repo, "branch", "--show-current"], capture_output=True, text=True, check=False).stdout.strip()


def the_helper() -> None:
    print("the helper:")
    gate = main_repo("unattended/2026-10-06")  # what the Stop gate hands a suite: a repository on an unattended branch
    before = os.environ.get("CLAUDE_PROJECT_DIR")
    os.environ["CLAUDE_PROJECT_DIR"] = gate
    try:
        fresh, again = hook_env(), hook_env()
        check("no project given: a fresh empty directory, not the inherited value",
              fresh["CLAUDE_PROJECT_DIR"] != gate and os.listdir(fresh["CLAUDE_PROJECT_DIR"]) == [], fresh["CLAUDE_PROJECT_DIR"])
        check("...and a new one each time", fresh["CLAUDE_PROJECT_DIR"] != again["CLAUDE_PROJECT_DIR"])
        own = sandbox_dir()
        check("a project given: exactly that one, a Path as well as a string",
              hook_env(own)["CLAUDE_PROJECT_DIR"] == own and hook_env(Path(own))["CLAUDE_PROJECT_DIR"] == own)
        laid = hook_env(own, PATH="/shims", MARK="1")
        check("extra variables are laid over the caller's environment",
              laid["PATH"] == "/shims" and laid["MARK"] == "1" and laid.get("HOME") == os.environ.get("HOME"))
        try:
            hook_env(CLAUDE_PROJECT_DIR=gate)
            refused = False
        except ValueError:
            refused = True
        check("the variable itself among the extras is refused", refused)
        main = main_repo()
        check("main_repo() is a repository on main, another branch on request",
              branch_of(main) == "main" and branch_of(gate) == "unattended/2026-10-06", (branch_of(main), branch_of(gate)))

        print("the mistake, on the real block-dangerous.sh:")
        check("inherited from the gate, the commit is ALLOWED (the suite would be red from the gate)",
              not blocked("git commit -m x", dict(os.environ)))
        check("through the helper the same commit is refused", blocked("git commit -m x", hook_env(main)))
        check("...and with no project at all", blocked("git commit -m x", hook_env()))
    finally:
        if before is None:
            del os.environ["CLAUDE_PROJECT_DIR"]
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = before


BARE = 'import subprocess\nHOOK = ".claude/hooks/block-dangerous.sh"\nsubprocess.run(["bash", HOOK], check=False)\n'
SPLIT = 'import subprocess\nfrom pathlib import Path\nHOOK = Path(".") / ".claude" / "hooks" / "x.sh"\nsubprocess.run(["bash", str(HOOK)], check=False)\n'
HARNESS = 'from subprocess import run\nrun(["python3", ".claude/unattended/board.py"], check=False)\n'
HELPED = 'import subprocess\nfrom hook_env import hook_env\nsubprocess.run(["bash", ".claude/hooks/x.sh"], env=hook_env(), check=False)\n'
QUIET = 'import subprocess\nsubprocess.run(["git", "status"], check=False)\n'
READS = 'from pathlib import Path\nprint(Path(".claude/hooks/x.sh").read_text())\n'


def tests_dir(suites: dict[str, str], exempt: str | None = None) -> Path:
    root = Path(sandbox_dir("hook-env-check-"))
    for name, source in suites.items():
        (root / name).write_text(source, encoding="utf-8")
    if exempt is not None:
        (root / EXEMPT).write_text(exempt, encoding="utf-8")
    return root


def the_check() -> None:
    print("the check, on synthetic suites:")
    found = findings(tests_dir({"test_new.py": BARE}))
    check("a new suite that runs a hook without the helper is caught, by name",
          len(found) == 1 and found[0].startswith("test_new.py: runs a hook without tests/hook_env.py"), found)
    check("...with the hook's path built from parts", len(findings(tests_dir({"test_new.py": SPLIT}))) == 1)
    check("...and a script of the unattended harness, subprocess imported by name", len(findings(tests_dir({"test_new.py": HARNESS}))) == 1)
    check("the same suite with the helper passes", findings(tests_dir({"test_new.py": HELPED})) == [])
    check("a suite that runs no hook is not asked for it", findings(tests_dir({"test_git.py": QUIET, "test_reads.py": READS})) == [])
    check("a helper file is not a suite", findings(tests_dir({"helper.py": BARE})) == [])
    check("an exempted suite passes", findings(tests_dir({"test_old.py": BARE}, "# the old ones\n\ntest_old.py  # pins it by hand\n")) == [])
    found = findings(tests_dir({"test_old.py": BARE, "test_new.py": BARE}, "test_old.py  # pins it by hand\n"))
    check("...and exempts nobody else", len(found) == 1 and found[0].startswith("test_new.py:"), found)
    found = findings(tests_dir({"test_old.py": BARE}, "test_old.py\n"))
    check("an exemption without a reason is a finding", len(found) == 1 and "no reason" in found[0], found)
    found = findings(tests_dir({"test_old.py": BARE}, "test_old.py # a\ntest_old.py # b\n"))
    check("a suite listed twice is a finding", len(found) == 1 and "listed twice" in found[0], found)
    found = findings(tests_dir({}, "test_gone.py  # pins it by hand\n"))
    check("a line for a suite that is gone is a finding", len(found) == 1 and "does not exist" in found[0], found)
    found = findings(tests_dir({"test_old.py": HELPED}, "test_old.py  # pins it by hand\n"))
    check("a line for a suite that moved to the helper is a finding", len(found) == 1 and "uses the helper now" in found[0], found)
    found = findings(tests_dir({"test_old.py": QUIET}, "test_old.py  # pins it by hand\n"))
    check("a line for a suite that runs no hook is a finding", len(found) == 1 and "runs no hook" in found[0], found)
    found = findings(tests_dir({"test_broken.py": "def (:\n"}))
    check("a suite that is not Python is a finding, not a pass", len(found) == 1 and "cannot be read" in found[0], found)


def this_repository() -> None:
    print("this repository:")
    found = findings(TESTS)
    check("every suite that runs a hook uses the helper or is exempted with a reason", not found, "\n".join(found))
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch)
        for path in [*TESTS.glob("test_*.py"), TESTS / EXEMPT]:
            (copy / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        (copy / "test_tomorrow.py").write_text(BARE, encoding="utf-8")
        found = findings(copy)
        check("...and one more suite beside them, without the helper, is the only finding",
              len(found) == 1 and found[0].startswith("test_tomorrow.py:"), found)


def main() -> int:
    the_helper()
    the_check()
    this_repository()
    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
