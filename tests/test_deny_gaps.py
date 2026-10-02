#!/usr/bin/env python3
"""S7 regression: the four evasion gaps in block-dangerous.sh, plus proof that
closing them did not start blocking ordinary commands.

Written as a Python file rather than a shell heredoc on purpose: the hook scans
the whole command text, so a heredoc containing these literals is blocked by the
very hook under test. See the NOTE at the top of block-dangerous.sh.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / ".claude/hooks/block-dangerous.sh"


def _pinned_main_repo() -> str:
    """A throwaway repository on `main` for CLAUDE_PROJECT_DIR.

    The hook's commit rule reads the branch of CLAUDE_PROJECT_DIR. By hand the variable is
    unset and the rule refuses every commit; under the Stop gate Claude Code sets it to this
    repository, and on an unattended/<date> branch the same cases came back ALLOWED. The
    suite was green by hand and red from the gate the first time TEST_CMD ran it there
    (package 3c fix round). Pin the branch, as test_deny_hooks.py does."""
    root = tempfile.mkdtemp(prefix="deny-gaps-main-")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    Path(root, "f.txt").write_text("x", encoding="utf-8")
    git("add", "f.txt")
    git("commit", "-qm", "init")
    git("branch", "-M", "main")
    return root


ENV = dict(os.environ, CLAUDE_PROJECT_DIR=_pinned_main_repo())


def blocked(cmd: str) -> bool:
    r = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True,
        text=True, check=False, env=ENV)
    return r.returncode == 2


MUST_BLOCK = [
    ("gap1 compound walks past the caret anchor", "cd /tmp && git commit -m x"),
    ("gap1 semicolon separator",                  "echo hi; git commit -m x"),
    ("gap2 global option hides the subcommand",   "git -C /some/repo commit -m x"),
    ("gap2 --no-pager before the subcommand",     "git --no-pager commit -m x"),
    ("gap3 quoted home variable",                 'rm -rf "$HOME"'),
    ("gap3 braced home variable",                 "rm -rf ${HOME}"),
    ("gap4 tab-indented privilege escalation",    "\tsudo rm -f /etc/hosts"),
    ("gap4 separator-preceded escalation",        "true && sudo rm -f /etc/hosts"),
    ("baseline plain commit",                     "git commit -m x"),
    ("baseline unquoted home variable",           "rm -rf $HOME"),
]

MUST_ALLOW = [
    ("ordinary status",              "git status"),
    ("ordinary staging",             "git add .claude/hooks"),
    ("ordinary log",                 "git -C . log --oneline -5"),
    ("substring is not the command", "sudoku --help"),
    ("commit as a word prefix",      "git committer --help"),
    ("name ending in git",           "mygit commit"),
    ("targeted delete",              "rm -rf ./build"),
    ("home in an unrelated path",    "ls $HOME/projects"),
    ("python invocation",            "python3 tests/test_deny_gaps.py"),
]

fails = []
print("must BLOCK:")
for name, cmd in MUST_BLOCK:
    ok = blocked(cmd)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if not ok:
        fails.append(f"{name!r} was ALLOWED: {cmd!r}")

print("\nmust ALLOW:")
for name, cmd in MUST_ALLOW:
    ok = not blocked(cmd)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if not ok:
        fails.append(f"{name!r} was BLOCKED: {cmd!r}")

print()
if fails:
    print(f"FAIL ({len(fails)}):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print(f"PASS {len(MUST_BLOCK)} blocked / {len(MUST_ALLOW)} allowed")
