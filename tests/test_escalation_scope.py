#!/usr/bin/env python3
"""An open gate escalation holds only the work that touches its files (board 301).

On 2026-10-12 the Stop gate gave up on one file of task 401. Until the owner closed the
escalation, no PASS was accepted in ANY task: the file stayed in the range "changed since the last
accepted PASS", that range is one for the whole branch, and no PASS could move it. Eleven tasks
did their work and went to blocked/ with the same question.

Deterministic: throwaway repositories with a task board, the real gate.py, overseer_stop.py,
overseer_verdict.py, gate_allows.py and board.py (the overseer agent's answer is fed to the verdict
script as its SubagentStop envelope), no model, no network.

  1. the escalation is on a file of task A; a unit of task B that changes other files passes;
  2. a unit of task B that changes the escalated file is refused, as before;
  3. task B's accepted PASS accepts nothing of task A's change: A's unit is refused while the
     escalation is open, and after it is closed the file is in the range of the next audit;
  4. …nor does it mark A's gate exemption in that file judged: the audit after the close shows it;
  5. the board does not offer a task whose verdict the escalation would refuse — the task whose
     unit opened it, a task whose own commits changed its files, every task when the escalation
     names no file — and says why.

Run:   python3 tests/test_escalation_scope.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           check=True).stdout.strip())
HOOKS = ROOT / ".claude" / "hooks"
COLLECTOR = HOOKS / "gate_allows.py"
GATE = HOOKS / "gate.py"
OVERSEER = HOOKS / "overseer_stop.py"
VERDICT_SCRIPT = HOOKS / "overseer_verdict.py"
BOARD = ROOT / ".claude" / "unattended" / "board.py"
WIRED = json.dumps({"hooks": {
    "PreToolUse": [{"matcher": "Agent|Task", "hooks": [{"type": "command", "command": "python3 .claude/hooks/overseer_verdict.py guard"}]}],
    "SubagentStop": [{"matcher": "overseer", "hooks": [{"type": "command", "command": "python3 .claude/hooks/overseer_verdict.py record"}]}]}}) + "\n"
PASS = 0
FAIL = 0
# Built, never written as one literal: this file must stay clean under the guard it tests.
NQ = "# no" + "qa"
GA = "gate" + "-allow:"
REASON = "the generated table keeps its long lines"
TASK = "# Задача\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Що зробити\n- щось\n\n## Готово, коли\n- готово\n"
STATE = ".claude/state/gate/escalations.json"
JUDGED = ".claude/state/overseer/gate-allows-judged.json"


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:900]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str = "c") -> str:
    sh(root, "git", "add", "-A")
    sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message, "--allow-empty")
    return sh(root, "git", "rev-parse", "HEAD").stdout.strip()


def new_repo() -> Path:
    """A project with a task board on unattended/x; the gate's checks find nothing."""
    root = Path(tempfile.mkdtemp(prefix="escalation-scope-"))
    sh(root, "git", "init", "-q", "-b", "main")
    (root / ".claude").mkdir()
    (root / ".claude" / "project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="true"\nTYPECHECK_CMD="true"\nTEST_CMD="true"\n')
    (root / ".claude" / "settings.json").write_text(WIRED)
    (root / ".gitignore").write_text(".claude/state/\n_transcript.jsonl\n")
    (root / ".engine" / "overseer").mkdir(parents=True)
    for column in ("todo", "doing", "blocked", "done"):
        (root / "tasks" / column).mkdir(parents=True)
        (root / "tasks" / column / ".gitkeep").touch()
    (root / "a.py").write_text("x = 1\n")
    commit(root, "init")
    sh(root, "git", "switch", "-q", "-c", "unattended/x")
    return root


def run(script: Path, root: Path, *args: str, stdin: Any = None, **extra: str) -> subprocess.CompletedProcess[str]:
    env = hook_env(root, **extra)
    for name in ("CLAUDE_UNATTENDED_SESSION", "CLAUDECODE"):
        if name not in extra:
            env.pop(name, None)
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True,
                          env=env, input=json.dumps(stdin) if stdin is not None else "", check=False)


def move(root: Path, name: str, source: str, target: str) -> None:
    """A task changes its column in a commit of its own, as the runner and the agent do it."""
    if source:
        sh(root, "git", "mv", f"tasks/{source}/{name}.md", f"tasks/{target}/{name}.md")
    else:
        (root / "tasks" / target / f"{name}.md").write_text(TASK, encoding="utf-8")
    commit(root, f"board: {name} → {target}")


def escalations(root: Path) -> dict[str, Any]:
    return dict(json.loads((root / STATE).read_text()))


def open_escalation(root: Path, stamp: str, files: list[str], work: str = "") -> None:
    (root / STATE).parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {"stamp": stamp, "slice": "(none)", "files": files}
    (root / STATE).write_text(json.dumps({"open": [entry | ({"work": work} if work else {})], "closed": [], "refusals": []}))


def close(root: Path, stamp: str) -> int:
    return run(GATE, root, "--close-escalation", stamp).returncode


def transcript(root: Path, edited: str) -> Path:
    records = [
        {"type": "user", "message": {"role": "user", "content": "finish unit 1"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t0", "name": "Edit",
             "input": {"file_path": str(root / edited), "old_string": "a", "new_string": "b"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "uv run pytest -q"}}]}},
    ]
    path = root / "_transcript.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in records) + "\n")
    return path


def overseer(root: Path, message: str, edited: str = "a.py") -> str:
    proc = run(OVERSEER, root, stdin={"hook_event_name": "Stop", "last_assistant_message": message,
                                      "transcript_path": str(transcript(root, edited))})
    return str(json.loads(proc.stdout).get("reason", "")) if proc.stdout.strip() else ""


CLAIMS = 0
GOOD = {"verdict": "PASS", "check": None, "reason": "every claim has its evidence", "evidence": ["a.py:1"], "category": "none"}


def claim(root: Path, edited: str = "a.py") -> str:
    """A unit-completion claim: what the builder is told, then what the request shows the overseer about the gate."""
    global CLAIMS
    CLAIMS += 1
    said = overseer(root, f"Did the work, claim {CLAIMS}.\n\n=== UNIT 1 COMPLETE ===\n", edited)
    try:
        rid = json.loads((root / ".claude/state/overseer/pending.json").read_text())["id"]
        request = json.loads((root / ".claude/state/overseer/requests" / rid / "request.json").read_text())
    except (OSError, ValueError, KeyError):
        return said
    return "\n\n".join(x for x in (said, str(request.get("gate_allows", "")), str(request.get("gate_escalation", ""))) if x)


def answer(root: Path) -> str:
    """The overseer agent is launched for the pending request and answers PASS; what the Stop hook then says."""
    rid = json.loads((root / ".claude/state/overseer/pending.json").read_text())["id"]
    run(VERDICT_SCRIPT, root, "guard", stdin={"hook_event_name": "PreToolUse", "tool_name": "Agent",
                                              "tool_input": {"subagent_type": "overseer", "prompt": f"OVERSEER_REQUEST {rid}"}})
    run(VERDICT_SCRIPT, root, "record", stdin={"hook_event_name": "SubagentStop", "agent_type": "overseer", "agent_id": "a1",
                                               "last_assistant_message": "```json\n" + json.dumps(GOOD) + "\n```"})
    return overseer(root, f"The overseer answered request {rid}.")


def audited(root: Path, edited: str = "a.py") -> tuple[str, str]:
    """A claim the overseer answers with PASS: (the request as the overseer reads it, what the Stop hook says after the verdict)."""
    asked = claim(root, edited)
    return asked, answer(root)


def passed(said: str) -> bool:
    return said.startswith("OVERSEER_PASS recorded")


def last_verdict(root: Path) -> dict[str, Any]:
    lines = (root / ".claude/state/overseer/verdicts.jsonl").read_text().splitlines()
    return dict(json.loads(lines[-1]))


def locked(said: str, root: Path) -> bool:
    """The overseer's PASS was recorded as a BLOCK because the gate's escalation is open."""
    row = last_verdict(root)
    return said.startswith("OVERSEER_BLOCK") and "gate escalation" in said and row["verdict"] == "BLOCK" and "gate escalation" in str(row["reason"])


def judged(root: Path) -> dict[str, Any]:
    try:
        return dict(json.loads((root / JUDGED).read_text()))
    except (OSError, ValueError):
        return {}


def exemptions(root: Path, *args: str) -> list[tuple[str, int]]:
    data = json.loads(run(COLLECTOR, root, "--json", *args).stdout or "{}")
    return [(str(i["file"]), int(i["line"])) for i in data.get("allows", [])]


def board(root: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    return run(BOARD, root, "--root", str(root), *args, **extra)


def task_a_escalated() -> tuple[Path, str]:
    """Task 401-a changed a.py — with a gate exemption — and committed it; the gate gave up on a.py (as on
    2026-10-12: an exemption the gate did not take); the task went to blocked/ with its question."""
    root = new_repo()
    move(root, "401-a", "", "doing")
    (root / "a.py").write_text(f"x = 1\ntable = 2  {NQ}: E501  # {GA} {REASON}\n")
    commit(root, "board 401: built and not yet audited")
    open_escalation(root, "2026-10-12T01:56:46Z", ["a.py"], "401-a")
    return root, "2026-10-12T01:56:46Z"


# ---------------------------------------------------------------- 0. what the gate records
print("the gate records whose work it gave up on")
r = new_repo()
move(r, "401-a", "", "doing")
(r / ".claude" / "project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="false"\nGATE_MAX_BLOCKS="1"\n')
commit(r, "env")
(r / "a.py").write_text("x = 1\nq = 9\n")
run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
entry = (escalations(r)["open"] or [{}])[-1]
check("an escalation opened while a board task is in doing/ names that task (`work`) beside its files",
      entry.get("files") == ["a.py"] and entry.get("work") == "401-a", entry)
said = audited(r)[1]
check("negative, as before — the unit of the task that opened it is refused while it is open", locked(said, r) and "a.py" in said, said)

# ---------------------------------------------------------------- 1. the scene of 2026-10-12
print("the scene of 2026-10-12: the escalation is on task A's file, task B changes other files")
r, stamp = task_a_escalated()
said = audited(r)[1]
check("negative — task A's own unit: the PASS is recorded as BLOCK, naming the escalation and the file",
      locked(said, r) and stamp in said and "a.py" in said, (said, last_verdict(r)))
move(r, "401-a", "doing", "blocked")
move(r, "402-b", "", "doing")
(r / "b.py").write_text("k = 1\n")
asked, said = audited(r, "b.py")
b_passed = passed(said)
check("task B's unit changes only b.py: the request does not say a PASS will be refused",
      asked.startswith("OVERSEER_REQUEST") and "OVERSEER_PASS will not be accepted" not in asked, asked)
check("…and its PASS is accepted", b_passed and last_verdict(r)["verdict"] == "PASS", (said, last_verdict(r)))
check("…the request tells the overseer the escalated file is set aside, not part of this audit",
      "SET ASIDE" in asked and "a.py" in asked.split("SET ASIDE")[-1], asked)
check("…and does not ask it to judge task A's exemption there", "a.py:2" not in asked and "GATE-ALLOW REVIEW" not in asked, asked)

print("what task B's accepted PASS did NOT accept")
state = judged(r)
check("the base moved to the commit of B's PASS, and a.py is recorded as held from the base before it",
      b_passed and state.get("commit") == sh(r, "git", "rev-parse", "HEAD").stdout.strip()
      and list(state.get("held", {})) == ["a.py"] and state["held"]["a.py"] == sh(r, "git", "rev-parse", "main").stdout.strip(), state)
check("task A's exemption in a.py is not marked judged", b_passed and state.get("judged") == [], state)
check("the collector run by hand in task B's session sets it aside too; against a named base it is there",
      b_passed and exemptions(r) == [] and exemptions(r, "--base", "main") == [("a.py", 2)], (exemptions(r), exemptions(r, "--base", "main")))
commit(r, "board 402: unit 1, overseer PASS")

print("task B changes the escalated file")
(r / "a.py").write_text((r / "a.py").read_text() + "more = 3\n")
asked, said = audited(r, "a.py")
check("negative — a unit of task B that changes a.py (uncommitted): refused, as before",
      b_passed and "OVERSEER_PASS will not be accepted" in asked and locked(said, r) and "a.py" in said, (asked, said))
commit(r, "board 402: a change of a.py")
check("negative — …and after B committed that change", b_passed and locked(audited(r, "a.py")[1], r), last_verdict(r))
sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "revert", "--no-edit", "HEAD")

print("a third task, then task A again")
r, stamp = task_a_escalated()
move(r, "401-a", "doing", "blocked")
move(r, "402-b", "", "doing")
(r / "b.py").write_text("k = 1\n")
b_passed = passed(audited(r, "b.py")[1])
commit(r, "board 402: unit 1, overseer PASS")
move(r, "402-b", "doing", "blocked")
move(r, "403-c", "", "doing")
(r / "c.py").write_text("m = 1\n")
c_passed = passed(audited(r, "c.py")[1])
commit(r, "board 403: unit 1, overseer PASS")
check("a second other task passes too, and a.py is still held from the same base",
      b_passed and c_passed and judged(r).get("held") == {"a.py": sh(r, "git", "rev-parse", "main").stdout.strip()}
      and judged(r).get("judged") == [], (b_passed, c_passed, judged(r)))
move(r, "403-c", "doing", "blocked")
move(r, "401-a", "blocked", "doing")
(r / "a2.py").write_text("n = 1\n")
asked, said = audited(r, "a2.py")
check("negative — task A is back and the escalation is open: its unit is refused, though other tasks' PASSes moved the base",
      b_passed and c_passed and "OVERSEER_PASS will not be accepted" in asked and locked(said, r) and "a.py" in said, (asked, said, last_verdict(r)))
check("…and that refusal judged nothing", judged(r).get("judged") == [] and list(judged(r).get("held", {})) == ["a.py"], judged(r))

print("the owner closes the escalation")
check("closed by the owner's command", close(r, stamp) == 0 and escalations(r)["open"] == [], escalations(r))
unit = run(COLLECTOR, r, "--json").stdout
asked, said = audited(r, "a2.py")
check("a.py is in the range of the next audit: the request names it and where its change is counted from",
      b_passed and "BACK IN THIS AUDIT" in asked and "a.py" in asked.split("BACK IN THIS AUDIT")[-1]
      and sh(r, "git", "rev-parse", "main").stdout.strip()[:12] in asked, asked)
check("task A's exemption is shown to the overseer — file, line and reason",
      b_passed and "GATE-ALLOW REVIEW" in asked and "a.py:2" in asked and REASON in asked, (asked, unit))
check("the PASS is accepted now", b_passed and passed(said), (said, last_verdict(r)))
check("…and only this PASS marks the exemption judged and lets the file go",
      b_passed and len(judged(r).get("judged", [])) == 1 and judged(r).get("held") == {}, judged(r))

print("an escalation that names no file covers all work")
r = new_repo()
move(r, "402-b", "", "doing")
(r / "b.py").write_text("k = 1\n")
open_escalation(r, "S-ALL", [])
asked, said = audited(r, "b.py")
check("negative — every unit is refused while it is open", "covers all work" in asked and locked(said, r), (asked, said))

# ---------------------------------------------------------------- 2. the board
print("the board does not offer a task the escalation would refuse")
r, stamp = task_a_escalated()
move(r, "401-a", "doing", "todo")
move(r, "402-b", "", "todo")
offered = board(r, "next")
check("the task whose unit opened the escalation is passed over; the next one is offered",
      offered.returncode == 0 and offered.stdout.strip() == "tasks/todo/402-b.md", (offered.returncode, offered.stdout, offered.stderr))
refused = board(r, "start", "tasks/todo/401-a.md")
check("negative — `start` refuses it and names the escalation", refused.returncode != 0 and stamp in refused.stderr
      and (r / "tasks/todo/401-a.md").is_file(), (refused.returncode, refused.stderr))
said = board(r, "summary").stdout
check("the summary says what it waits for", f"чекає, поки власник закриє ескалацію gates {stamp}: 401-a.md" in said, said)
sh(r, "git", "rm", "-q", "tasks/todo/402-b.md")
commit(r, "402 gone")
alone = board(r, "next")
check("with nothing else in todo/: nothing can start (exit 4 — it waits for the owner)", alone.returncode == 4 and alone.stdout == "", (alone.returncode, alone.stdout))
check("closed: the task is offered again", close(r, stamp) == 0 and board(r, "next").stdout.strip() == "tasks/todo/401-a.md", board(r, "next").stdout)

r, stamp = task_a_escalated()
(r / STATE).write_text(json.dumps({"open": [{"stamp": stamp, "slice": "(none)", "files": ["a.py"]}]}))   # written before `work` existed
move(r, "401-a", "doing", "todo")
move(r, "402-b", "", "todo")
check("an escalation with no `work`: the task whose own commits changed its file is passed over all the same",
      board(r, "next").stdout.strip() == "tasks/todo/402-b.md", board(r, "next").stdout)

r = new_repo()
move(r, "402-b", "", "todo")
check("no escalation: the task is offered", board(r, "next").stdout.strip() == "tasks/todo/402-b.md", board(r, "next").stdout)
open_escalation(r, "S-ALL", [])
none = board(r, "next")
check("negative — an escalation that covers all work: no task is offered (exit 4)", none.returncode == 4 and none.stdout == "", (none.returncode, none.stdout))
refused = board(r, "start", "tasks/todo/402-b.md")
check("negative — …and `start` refuses", refused.returncode != 0 and "S-ALL" in refused.stderr and (r / "tasks/todo/402-b.md").is_file(), refused.stderr)
said = board(r, "summary").stdout
check("the summary says the board waits for the owner and why",
      "ескалація gates S-ALL накриває всю роботу" in said and "наступна:" not in said, said)
held = board(r, "gate-hold")
check("`gate-hold` prints the stamp for the runner", held.returncode == 0 and held.stdout.strip() == "S-ALL", (held.returncode, held.stdout, held.stderr))
r = new_repo()
(r / ".claude/hooks").mkdir(parents=True)
(r / ".claude/hooks/simplifier.py").write_text("")
open_escalation(r, "S-ALL", [])
placed = board(r, "cleanup-task", "--today", date.today().isoformat())
check("negative — no cleanup task is placed while it is open (its units would be refused too)",
      placed.stdout.strip() == "" and not list((r / "tasks/todo").glob("*cleanup*")), (placed.stdout, placed.stderr))
check("closed: `gate-hold` prints nothing", close(r, "S-ALL") == 0 and board(r, "gate-hold").stdout.strip() == "", board(r, "gate-hold").stdout)
placed = board(r, "cleanup-task", "--today", date.today().isoformat())
check("…and the cleanup task is placed as usual", "cleanup" in placed.stdout and len(list((r / "tasks/todo").glob("*cleanup*"))) == 1, (placed.stdout, placed.stderr))

print()
print(f"{'PASS' if FAIL == 0 else 'FAIL'}: {PASS}/{PASS + FAIL}")
sys.exit(0 if FAIL == 0 else 1)
