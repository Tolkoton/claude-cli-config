#!/usr/bin/env python3
"""The Stop gate in a tree a board runner works in (board 305): whose work it judges.

Every case runs the real gate.py (and env-check.sh) in a throwaway git repository. The "runner" is
a live `sleep` whose PID stands in .claude/state/board/lock; its unfinished work is a red file in
the tree. The session's transcript is a JSONL file of the shape Claude Code writes, handed to the
hook in its envelope. The project's lint is a configured LINT_CMD that, like a real one, looks at
the whole tree and names every broken file. Nothing here talks to a model or the network.

Run:   python3 tests/test_shared_tree.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / ".claude" / "hooks" / "gate.py"
ENV_CHECK = ROOT / ".claude" / "hooks" / "env-check.sh"
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
shell_readonly = importlib.import_module("shell_readonly")

PASS = FAIL = 0
SLEEPERS: list[subprocess.Popen[bytes]] = []
LINT = """#!/usr/bin/env bash
cd "$(dirname "$0")"
rc=0
for f in *.py; do
  if grep -q BROKEN "$f"; then echo "$f:1:1: E999 broken"; rc=1; fi
done
exit $rc
"""


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:600]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def new_repo() -> Path:
    """A project whose lint is configured; the runner's red file is already in the tree."""
    root = Path(tempfile.mkdtemp(prefix="shared-tree-"))
    sh(root, "git", "init", "-q", "-b", "main")
    (root / ".claude").mkdir()
    (root / "lint.sh").write_text(LINT)
    (root / ".claude" / "project.env").write_text(f'CODE_EXTENSIONS="py"\nLINT_CMD="bash {root}/lint.sh"\n')
    (root / ".gitignore").write_text(".claude/state/\n")
    (root / "mine.py").write_text("x = 1\n")
    (root / "runner.py").write_text("y = 1\n")
    for column in ("todo", "doing", "blocked", "done", "proposed"):
        (root / "tasks" / column).mkdir(parents=True)
        (root / "tasks" / column / ".gitkeep").write_text("")
    sh(root, "git", "add", "-A")
    sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    (root / "tasks" / "doing" / "302-runner-task.md").write_text(
        "# The runner's task\n\nКлас: 2\nЗалежить від: —\nПотрібна присутність власника: ні\n")
    (root / "runner.py").write_text('y = 1  # BROKEN: raise NotImplementedError("slice in progress")\n')
    return root


def live_runner(root: Path) -> int:
    proc = subprocess.Popen(["sleep", "600"])
    SLEEPERS.append(proc)
    (root / ".claude" / "state" / "board").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "state" / "board" / "lock").write_text(f"{proc.pid}\n")
    (root / ".claude" / "state" / "board" / "status").write_text("state=running task=302-runner-task since=now\n")
    return proc.pid


def dead_runner(root: Path) -> None:
    proc = subprocess.Popen(["true"])
    proc.wait()
    (root / ".claude" / "state" / "board").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "state" / "board" / "lock").write_text(f"{proc.pid}\n")


def tool_use(name: str, tool_input: dict[str, Any], cwd: Path) -> str:
    return json.dumps({"type": "assistant", "cwd": str(cwd),
                       "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": name, "input": tool_input}]}})


def transcript(root: Path, *uses: tuple[str, dict[str, Any]], agents: list[list[tuple[str, dict[str, Any]]]] | None = None) -> str:
    """A session transcript holding these tool calls; `agents`: the transcripts of its subagents."""
    folder = Path(tempfile.mkdtemp(prefix="shared-tree-transcript-"))
    main = folder / "session.jsonl"
    lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "do it"}})]
    lines += [tool_use(name, tool_input, root) for name, tool_input in uses]
    main.write_text("\n".join(lines) + "\n")
    for number, agent in enumerate(agents or []):
        sub = folder / "session" / "subagents"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / f"agent-{number}.jsonl").write_text("\n".join(tool_use(n, i, root) for n, i in agent) + "\n")
    return str(main)


def stop(root: Path, path: str | None, session: str = "present", unattended: bool = False) -> dict[str, Any]:
    env = {k: v for k, v in hook_env(root).items() if k not in ("VIRTUAL_ENV", "CLAUDE_UNATTENDED_SESSION")}
    if unattended:
        env["CLAUDE_UNATTENDED_SESSION"] = "1"
    envelope: dict[str, Any] = {"stop_hook_active": False, "session_id": session}
    if path:
        envelope["transcript_path"] = path
    proc = subprocess.run([sys.executable, str(GATE), "--layer", "stop", "--hook"], cwd=root, env=env,
                          input=json.dumps(envelope), capture_output=True, text=True, check=False)
    try:
        return json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        return {"_malformed": proc.stdout + proc.stderr}


def report(root: Path) -> dict[str, Any]:
    return json.loads((root / ".claude/state/gate/last-report.json").read_text())


def open_escalations(root: Path) -> list[dict[str, Any]]:
    path = root / ".claude/state/gate/escalations.json"
    return json.loads(path.read_text()).get("open", []) if path.is_file() else []


def blocked_on(root: Path) -> set[str]:
    return {f["file"] for f in report(root)["findings"] if f["severity"] == "block" and f["file"]}


try:
    # ---------------------------------------------------------------- the incident
    print("the runner's red work, the present session writes no code")
    r = new_repo()
    live_runner(r)
    path = transcript(r, ("Bash", {"command": "git status --short"}), ("Read", {"file_path": str(r / "runner.py")}))
    outs = [stop(r, path) for _ in range(3)]
    check("three turns in a row: no block", all(o.get("decision") is None for o in outs), outs)
    check("and no escalation", not open_escalations(r) and not list((r / "tasks" / "blocked").glob("9*")), open_escalations(r))
    shared = report(r).get("shared_tree", {})
    check("the report names the runner's work as not judged", "runner.py" in shared.get("foreign", []) and shared.get("own") == [], report(r))

    print("the present session writes a coordination file, not code")
    r = new_repo()
    live_runner(r)
    (r / "note.md").write_text("for the inbox\n")
    path = transcript(r, ("Write", {"file_path": str(r / "note.md"), "content": "for the inbox\n"}))
    outs = [stop(r, path) for _ in range(3)]
    check("three turns: no block, no escalation", all(o.get("decision") is None for o in outs) and not open_escalations(r), outs)

    # ---------------------------------------------------------------- the session's own breakage
    print("the present session breaks a file itself")
    r = new_repo()
    live_runner(r)
    (r / "mine.py").write_text("x = 1  # BROKEN\n")
    path = transcript(r, ("Edit", {"file_path": str(r / "mine.py"), "old_string": "x = 1", "new_string": "x = 1  # BROKEN"}))
    first = stop(r, path)
    check("an Edit of its own file: blocked", first.get("decision") == "block", first)
    check("on its own file only; the runner's finding is a log",
          blocked_on(r) == {"mine.py"} and any(f["file"] == "runner.py" and f["severity"] == "log" for f in report(r)["findings"]),
          report(r)["findings"])
    stop(r, path)
    third = stop(r, path)
    escalations = open_escalations(r)
    check("the third block escalates, as before", "GATE ESCALATION" in str(third.get("systemMessage", "")) and len(escalations) == 1, third)
    check("the escalation names only the session's file", escalations and escalations[0]["files"] == ["mine.py"], escalations)
    check("and does not hold the runner's task", escalations and "work" not in escalations[0], escalations)

    print("a file written by Bash is the session's too")
    r = new_repo()
    live_runner(r)
    (r / "mine.py").write_text("x = 1  # BROKEN\n")
    path = transcript(r, ("Bash", {"command": "cd sub/.. && echo 'x = 1  # BROKEN' > mine.py"}))
    out = stop(r, path)
    check("`echo … > mine.py`: blocked on mine.py", out.get("decision") == "block" and blocked_on(r) == {"mine.py"}, report(r)["findings"])
    r = new_repo()
    live_runner(r)
    (r / "mine.py").write_text("x = 1  # BROKEN\n")
    path = transcript(r, ("Bash", {"command": "sed -i 's/x = 1/x = 1  # BROKEN/' mine.py"}))
    check("`sed -i … mine.py`: blocked", stop(r, path).get("decision") == "block")

    print("a subagent's write is the session's")
    r = new_repo()
    live_runner(r)
    (r / "mine.py").write_text("x = 1  # BROKEN\n")
    path = transcript(r, ("Agent", {"subagent_type": "general-purpose", "prompt": "fix"}),
                      agents=[[("Write", {"file_path": str(r / "mine.py"), "content": "x"})]])
    check("Write inside the subagent's transcript: blocked on mine.py",
          stop(r, path).get("decision") == "block" and blocked_on(r) == {"mine.py"}, report(r)["findings"])

    # ---------------------------------------------------------------- what cannot be told: the whole tree
    print("what the transcript does not show: the whole tree, as before")
    r = new_repo()
    live_runner(r)
    path = transcript(r, ("Bash", {"command": 'echo x > "$TARGET"'}))
    check("a write to a path in a variable: the runner's file is judged", stop(r, path).get("decision") == "block"
          and "runner.py" in blocked_on(r), report(r)["findings"])
    r = new_repo()
    live_runner(r)
    path = transcript(r, ("Agent", {"subagent_type": "general-purpose", "prompt": "x"}))
    check("a subagent with no transcript: the whole tree", stop(r, path).get("decision") == "block")
    r = new_repo()
    live_runner(r)
    check("no transcript in the envelope: the whole tree", stop(r, None).get("decision") == "block")

    # ---------------------------------------------------------------- not a shared tree
    print("not a shared tree: nothing changes")
    r = new_repo()
    path = transcript(r)
    check("no runner lock: the red file blocks, as before", stop(r, path).get("decision") == "block")
    r = new_repo()
    dead_runner(r)
    check("a lock whose runner is gone: the red file blocks", stop(r, transcript(r)).get("decision") == "block")
    r = new_repo()
    live_runner(r)
    check("the runner's own session (CLAUDE_UNATTENDED_SESSION=1): its red file blocks",
          stop(r, transcript(r), session="runner", unattended=True).get("decision") == "block")
    for _ in range(2):
        stop(r, transcript(r), session="runner", unattended=True)
    escalations = open_escalations(r)
    check("and its escalation still holds its task", escalations and escalations[0].get("work") == "302-runner-task", escalations)

    # ---------------------------------------------------------------- the paths a command writes
    print("shell_readonly.written_paths")
    env = {"HOME": "/home/u"}

    def written(command: str) -> set[str] | None:
        return shell_readonly.written_paths(command, "/p", env, "/p")

    check("a redirection", written("echo 1 > a.py") == {"/p/a.py"}, written("echo 1 > a.py"))
    check("cp: the last argument", written("cp a.py b.py") == {"/p/b.py"})
    check("sed -i with its script emptied as text", written("sed -i mine.py") == {"/p/mine.py"}, written("sed -i mine.py"))
    check("a temporary place is not the tree", written("cp a.py /tmp/x.py && echo 1 > /dev/null") == set())
    check("git add and git commit change no file", written("git add a.py && git commit -m 'm > n'") == set())
    check("git checkout changes files the text does not list", written("git checkout -- .") is None)
    check("a formatter rewrites what it is given", written("ruff format .") is None)
    check("a path in a variable is unknown", written('echo 1 > "$F"') is None)
    check("bash -c: the inner command", written("bash -c 'echo 1 > c.py'") == {"/p/c.py"}, written("bash -c 'echo 1 > c.py'"))
    check("a script a command starts is not seen (the named limit)", written("python3 gen.py") == set())

    # ---------------------------------------------------------------- the SessionStart notice
    print("env-check.sh: the session learns of the runner on its first turn")

    def session_start(root: Path, unattended: bool = False) -> str:
        env = {k: v for k, v in hook_env(root).items() if k != "CLAUDE_UNATTENDED_SESSION"}
        if unattended:
            env["CLAUDE_UNATTENDED_SESSION"] = "1"
        return subprocess.run(["bash", str(ENV_CHECK)], input="{}", capture_output=True, text=True, env=env, check=False).stdout

    r = new_repo()
    pid = live_runner(r)
    said = session_start(r)
    check("a live runner: the notice, with its pid, its task and a clone command",
          "a board runner works in this tree" in said and str(pid) in said and "302-runner-task" in said and "git clone" in said, said)
    check("the runner's own session: no notice", "board runner works" not in session_start(r, unattended=True))
    r = new_repo()
    dead_runner(r)
    check("a dead lock: no notice", "board runner works" not in session_start(r))
finally:
    for sleeper in SLEEPERS:
        sleeper.kill()
        sleeper.wait()

print()
print(f"PASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
