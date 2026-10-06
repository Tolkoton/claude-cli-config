#!/usr/bin/env python3
"""An agent does not answer for the owner: no write into the operator's directory, no clearing of the owner's variable (board 056).

"The owner answered" rests on two things an agent could fake with one command:
  - an answer is a file in the board's inbox, ~/engine-ops/tasks-inbox — so the whole operator's
    directory (the inbox, the runner's programs, its journal) is a guarded path: neither a shell
    command nor an editing tool writes there, reading stays free; the key of the second model
    kept there is a secret path, refused to a read as well;
  - the owner's terminal is told from an agent's shell by CLAUDECODE — so a command that clears
    or replaces it is refused: unset, `env -u`, `env -i`, `exec -c`, an assignment of anything
    but 1, `export -n`, and inline code that pops, deletes or overwrites it.
The negative cases: reading the variable, `CLAUDECODE=1 <command>`, other variables, reading
the operator's directory, files that only carry a like name.

Every case runs the real hook. Run: python3 tests/test_owner_perimeter.py   Exit: 0 green, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hook_env import hook_env, main_repo

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
P = main_repo("feat/x")
V = "CLAUDE" + "CODE"      # split, so that the hook under test does not refuse a shell command that handles THIS file
OPS = "~/engine-" + "ops"
KEY = f"{OPS}/simplifier-" + "key.sh"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def shell(cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(HOOKS / "block-dangerous.sh")], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": P}),
                          capture_output=True, text=True, env=hook_env(P), cwd=P, check=False)


def edit_denied(tool: str, path: str) -> bool:
    done = subprocess.run(["bash", str(HOOKS / "protect-paths.sh")], input=json.dumps({"tool_name": tool, "tool_input": {"file_path": path}}),
                          capture_output=True, text=True, env=hook_env(P), check=False)
    return '"permissionDecision"' in done.stdout and '"deny"' in done.stdout


REFUSED = [
    f"unset {V}", f"unset {V} && python3 engine.py release v1 --owner-approved", f"unset -v {V}", f"unset FOO {V}", f"cd x; unset {V}; make",
    f"env -u {V} python3 .claude/unattended/owner_action.py apply-settings abc", f"env -u{V} bash", f"env --unset={V} bash", f"env --unset {V} bash",
    f"env FOO=1 -u {V} bash", "env -i bash -c 'python3 engine.py release v1'", "env - python3 x.py", "env --ignore-environment python3 x.py",
    f"{V}= python3 evals/run_audit_scenarios.py --owner-approved", f'{V}="" python3 x.py', f"{V}='' python3 x.py", f"{V}=0 python3 x.py",
    f"export {V}=", f"export {V}=no", f"env {V}= python3 x.py", f"declare +x {V}", f"export -n {V}", f"typeset +x {V}",
    f"python3 -c 'import os; os.environ.pop(\"{V}\"); os.system(\"python3 engine.py release\")'",
    f"python3 -c 'import os; del os.environ[\"{V}\"]'", f"python3 -c 'import os; os.unsetenv(\"{V}\")'",
    f"python3 -c 'import os; os.environ[\"{V}\"] = \"\"'", f"node -e 'delete process.env.{V}; require(\"child_process\").execSync(\"x\")'",
    f"node -e 'process.env.{V} = \"\"'", f"python3 - <<'PY'\nimport os, subprocess\nenv = dict(os.environ); env.pop('{V}', None)\nsubprocess.run(['python3','engine.py','release'], env=env)\nPY",
    "exec -c bash",
    # the operator's directory
    f"echo x > {OPS}/tasks-inbox/001-answer.md", f"cp /tmp/722.md {OPS}/tasks-inbox/", f"cp /tmp/722.md $HOME/engine-ops/tasks-inbox/722.md",
    f"mv /tmp/a.md {OPS}/tasks-inbox/a.md", f"tee {OPS}/tasks-inbox/a.md < /tmp/a.md", f"cat > {OPS}/tasks-inbox/a.md <<'EOF'\nx\nEOF",
    f"sed -i s/a/b/ {OPS}/bin/claude", f"echo x >> {OPS}/board-runner.log", f"rm {OPS}/anomalies.md", f"rm -rf {OPS}", f"mkdir -p {OPS}/tasks-inbox && touch {OPS}/tasks-inbox/x.md",
    f"python3 -c 'open(os.path.expanduser(\"{OPS}/tasks-inbox/a.md\"),\"w\").write(\"x\")'", f"chmod +x {OPS}/bin/claude", "ln -s /tmp/x ../engine-ops/tasks-inbox/x.md",
    "cp a.md /srv/someone/engine-ops/tasks-inbox/a.md",
]
ALLOWED = [
    f"echo ${V}", f'echo "${{{V}:-unset}}"', f"env | grep {V}", f"printenv {V}", f"grep -rn {V} .claude/hooks/", f"[ -n \"${V}\" ] && echo in-session",
    f"{V}=1 python3 tests/test_board_runner.py", f'{V}="1" python3 x.py', f"env {V}=1 python3 x.py", f"export {V}=1",
    "env FOO=1 python3 x.py", "env | sort", "unset FOO", "unset -f helper", "env -u FOO python3 x.py", "export PATH=$PATH:/x", "git log --oneline -3",
    f"python3 -c 'import os; print(os.environ.get(\"{V}\"))'", f"python3 -c 'import os; print(\"{V}\" in os.environ)'",
    f"ls {OPS}", f"cat {OPS}/board-runner.log | tail -20", f"tail -5 {OPS}/anomalies.md", f"ls {OPS}/tasks-inbox/", f"grep -c board {OPS}/events.log",
    f"cp {OPS}/board-runner.log /tmp/log-copy.txt", f"diff {OPS}/tasks-inbox/a.md tasks/blocked/a.md", "echo x > docs/engine-ops-notes.md", "ls engine-ops-old/",
    "bash .claude/unattended/board-runner.sh --status",
]

print("a command that clears the owner's variable, or writes into the operator's directory, is refused")
for cmd in REFUSED:
    done = shell(cmd)
    check(f"refused: {cmd!r}", done.returncode == 2 and "block-dangerous.sh" in done.stderr, f"exit {done.returncode}: {done.stderr[:200]}")
done = shell(f"unset {V}")
check("the refusal names the variable and the owner's way", V in done.stderr and "tasks/blocked/" in done.stderr, done.stderr)

print("\nthe negative cases: reading the variable, setting it to 1, other variables, reading the operator's directory")
for cmd in ALLOWED:
    done = shell(cmd)
    check(f"allowed: {cmd!r}", done.returncode == 0, f"exit {done.returncode}: {done.stderr[:200]}")

print("\nthe key kept in the operator's directory is a secret: no reading either")
for cmd in (f"cat {KEY}", f". {KEY}", f"source {KEY} && env", f"grep KEY {KEY}", f"cp {KEY} /tmp/k"):
    done = shell(cmd)
    check(f"refused: {cmd!r}", done.returncode == 2 and "secret path" in done.stderr or done.returncode == 2 and "protected path" in done.stderr, done.stderr[:200])
check("negative — the journal beside it is read freely", shell(f"tail -20 {OPS}/board-runner.log").returncode == 0)

print("\nan editing tool does not write into the operator's directory either")
home = str(Path.home())
for tool, path in (("Write", f"{home}/engine-ops/tasks-inbox/732-answer.md"), ("Edit", f"{home}/engine-ops/bin/claude"), ("MultiEdit", f"{home}/engine-ops/anomalies.md"),
                   ("Write", "/srv/other/engine-ops/tasks-inbox/a.md"), ("Edit", f"{home}/engine-ops/simplifier-" + "key.sh")):
    check(f"{tool} {path.replace(home, '~')}: denied", edit_denied(tool, path))
for tool, path in (("Edit", f"{P}/docs/engine-ops-notes.md"), ("Write", f"{P}/tasks/todo/900-new.md"), ("Write", "/tmp/owner-review-20261006-1500/732-answer.md")):
    check(f"negative — {tool} {path.replace(P, '<project>')}: not denied", not edit_denied(tool, path))

print("\n/owner-review prepares the files and hands the owner the command (it no longer writes into the inbox)")
command = (ROOT / ".claude/commands/owner-review.md").read_text(encoding="utf-8")
check("the session's directory is under /tmp, and that write is not refused", "/tmp/owner-review-" in command and shell("mkdir -p /tmp/owner-review-20261006-1500").returncode == 0)
check("the one command the command file gives the owner is refused to an agent",
      shell(f"mkdir -p {OPS}/tasks-inbox && cp /tmp/owner-review-20261006-1500/732-answer.md {OPS}/tasks-inbox/").returncode == 2)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
