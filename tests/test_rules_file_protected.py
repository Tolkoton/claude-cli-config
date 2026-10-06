#!/usr/bin/env python3
"""`.engine/rules.md` is written one way only: `lesson_queue.py promote`, on the owner's «так» (board 054).

CLAUDE.md imports the file, so each line of it steers every conversation. Until board 054 an
agent could add a line with Edit or Write, or with a shell command, and only the diff showed it.
Now the path is on the one list of protected paths (protected-path-list.sh, GUARDED): both
hooks refuse a write, in every form, and reading stays free.

  - protect-paths.sh refuses Edit, Write and MultiEdit, by an absolute and a relative path;
  - block-dangerous.sh refuses every shell form of a write;
  - the negative cases: reading (cat, grep, git diff, git log), putting the committed text back
    (git checkout --, git restore), starting lesson_queue.py, and writing the files beside it
    (the lesson queue, the proposals, engine-rules.md, another rules.md) all pass.
The lawful way writes the file from a script, which no hook judges; that it needs the owner's
answer and refuses inside a session is tests/test_lesson_queue.py's.

Run:   python3 tests/test_rules_file_protected.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hook_env import hook_env, main_repo

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
PROJECT = main_repo("feat/x")
R = ".engine/rules.md"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def shell(cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(HOOKS / "block-dangerous.sh")], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": PROJECT}),
                          capture_output=True, text=True, env=hook_env(PROJECT), cwd=PROJECT, check=False)


def edit_denied(tool: str, path: str) -> bool:
    """protect-paths.sh denies by PRINTING a decision and exiting 0 (tests/test_guardrail_paths.py)."""
    done = subprocess.run(["bash", str(HOOKS / "protect-paths.sh")], input=json.dumps({"tool_name": tool, "tool_input": {"file_path": path}}),
                          capture_output=True, text=True, env=hook_env(PROJECT), check=False)
    return '"permissionDecision"' in done.stdout and '"deny"' in done.stdout


print("a shell write to the rules file is refused, in every form")
for name, cmd in [
    ("append with >>", f"echo '- a rule of my own' >> {R}"),
    ("overwrite with >", f"printf x > {R}"),
    ("a heredoc into it", f"cat >> {R} <<'EOF'\n- a rule of my own\nEOF"),
    ("tee -a", f"echo x | tee -a {R}"),
    ("sed -i", f"sed -i s/never/always/ {R}"),
    ("perl -pi", f"perl -pi -e s/never/always/ {R}"),
    ("cp into it", f"cp /tmp/x {R}"),
    ("mv into it", f"mv /tmp/x {R}"),
    ("mv it away", f"mv {R} /tmp/x"),
    ("rm", f"rm {R}"),
    ("truncate", f"truncate -s 0 {R}"),
    ("dd of=", f"dd if=/tmp/x of={R}"),
    ("python open for append", f"""python3 -c 'open("{R}","a").write("x")'"""),
    ("python write_text", f"""python3 -c 'from pathlib import Path; Path("{R}").write_text("x")'"""),
    ("git rm", f"git rm {R}"),
    ("git checkout of another revision", f"git checkout main~2 -- {R}"),
    ("git restore --source", f"git restore --source=HEAD~1 {R}"),
    ("by an absolute path, after cd", f"cd /tmp && echo x >> {PROJECT}/{R}"),
    ("after another command", f"git status; echo x >> {R}"),
]:
    done = shell(cmd)
    check(f"{name}: refused, the path named", done.returncode == 2 and R in done.stderr and "writes to a protected path" in done.stderr,
          f"{cmd!r} -> exit {done.returncode}: {done.stderr[:200]}")

print("\nan edit tool is refused too")
for tool, path in (("Edit", f"{PROJECT}/{R}"), ("Write", f"{PROJECT}/{R}"), ("MultiEdit", f"{PROJECT}/{R}"), ("Edit", R), ("Write", f"sub/project/{R}")):
    check(f"{tool} {path.replace(PROJECT, '<project>')}: denied", edit_denied(tool, path))

print("\nthe negative cases: reading, the remedy and the neighbours pass")
for name, cmd in [
    ("cat", f"cat {R}"),
    ("grep", f"grep -n RP- {R}"),
    ("wc, output redirected elsewhere", f"wc -l {R} > /tmp/count.txt"),
    ("git diff", f"git diff -- {R}"),
    ("git log", f"git log --oneline -3 -- {R}"),
    ("cp out of it", f"cp {R} /tmp/rules-copy.md"),
    ("git checkout -- (the committed text back)", f"git checkout -- {R}"),
    ("git restore (the committed text back)", f"git restore {R}"),
    ("the lawful way is started by name", "python3 .claude/hooks/lesson_queue.py promote abc123"),
    ("the lesson queue is the agent's to write", "echo '- a lesson' >> .engine/lesson-queue.md"),
    ("the proposals file too", "echo x >> .engine/rule-proposals.md"),
    ("another rules.md", "echo x > docs/rules.md"),
    ("a file that only ends alike", "echo x > .engine/old-rules.md"),
    ("engine-rules.md is not this file", "sed -i s/a/b/ .claude/engine-rules.md"),
]:
    done = shell(cmd)
    check(f"{name}: allowed", done.returncode == 0, f"{cmd!r} -> exit {done.returncode}: {done.stderr[:200]}")
for tool, path in (("Edit", f"{PROJECT}/.engine/lesson-queue.md"), ("Write", f"{PROJECT}/.engine/rule-proposals.md"),
                   ("Edit", f"{PROJECT}/docs/rules.md"), ("Edit", f"{PROJECT}/.engine/old-rules.md"), ("Edit", f"{PROJECT}/.claude/engine-rules.md")):
    check(f"{tool} {path.replace(PROJECT, '<project>')}: not denied", not edit_denied(tool, path))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
