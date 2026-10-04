#!/usr/bin/env python3
"""board-runner.sh drives the task board (package board, B2 and B3) — with a fake `claude`.

Every case builds a synthetic repository on the branch `unattended/work` with a bare `origin`,
puts task files on its board and runs the real .claude/unattended/board-runner.sh against it
(CLAUDE_PROJECT_DIR names the repository). The fake `claude` records its argv and environment
and then does what its script for that call says — the things tasks/README.md asks of an agent:

    done            move the task to done/NNN-name/ (task.md, report.md) and commit
    done-nocommit   the same, without the commit
    block           add a question, move the task to blocked/, commit
    work            commit something, leave the task in doing/
    idle            do nothing
    limit           answer with a usage-limit notice
    garbage         print something that is not JSON
    dirty           leave an uncommitted file outside tasks/, commit nothing
    auth            answer only that claude is logged out
    return          move the task back to todo/ and commit — neither done nor a question
    vanish          delete the task file and commit
    tidy            commit everything that is uncommitted (what the runner asks for when a closed
                    task left the tree dirty, board 029)
    <step>-dirty    do <step>, then stage a file outside tasks/ and leave it uncommitted
    refused         claim one unit complete three times; each claim is audited through the REAL
                    overseer hooks (overseer_stop.py, overseer_verdict.py — the Stop, PreToolUse
                    and SubagentStop envelopes a session would send) and answered BLOCK. What the
                    Stop hook printed after the third goes to <home>/hook-said; the fake then ends
                    its session, as claude does on `continue: false` (board 031)

FAKE_STOP_AT=<n> makes call n ask for a soft stop while it runs — through the runner's own
`--stop-after-task`, or (FAKE_STOP_HOW=file) by creating the flag file itself.
    gateq           the Stop gate gave up during the session: a gate question appears in blocked/,
                    uncommitted, and the task stays in doing/

A conversation's reported cost is its running total (1 USD a call unless FAKE_COST says
otherwise); `--resume ID` keeps the id, a call without it opens a new conversation.

THE TRACER (the feature's integration premise, PR-board-06) is the first case: the runner learns
that the agent finished from the working tree and HEAD alone. The fake follows the manual by
construction, so this proves the runner's mechanics — not that a real agent follows the manual;
only the live check does that.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / ".claude/unattended/board-runner.sh"
FAKE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path

home = Path(os.environ["FAKE_HOME"])
argv = sys.argv[1:]
calls = home / "calls.jsonl"
n = len(calls.read_text().splitlines()) if calls.exists() else 0
mode = Path(".claude/state/overseer/mode")
with calls.open("a") as f:
    f.write(json.dumps({"argv": argv, "cwd": os.getcwd(), "unattended": os.environ.get("CLAUDE_UNATTENDED_SESSION", ""),
                        "mode": mode.read_text().strip() if mode.exists() else "(absent)"}, ensure_ascii=False) + "\n")
plan = (home / "plan").read_text().split()
step = plan[n] if n < len(plan) else "done"
if os.environ.get("FAKE_STOP_AT") == str(n):   # the operator asks for a soft stop during this call
    if os.environ.get("FAKE_STOP_HOW") == "file":
        Path(".claude/state/board/stop-after-task").touch()
    else:
        asked = subprocess.run(["bash", os.environ["FAKE_RUNNER"], "--stop-after-task"], capture_output=True, text=True)
        (home / "stop-asked").write_text(f"{asked.returncode}\n{asked.stdout}{asked.stderr}")
session = argv[argv.index("--resume") + 1] if "--resume" in argv else f"s{n + 1}"
costs = json.loads((home / "costs").read_text()) if (home / "costs").exists() else {}
costs[session] = costs.get(session, 0.0) + float(os.environ.get("FAKE_COST", "1"))
(home / "costs").write_text(json.dumps(costs))

def git(*a):
    subprocess.run(["git", *a], check=True, capture_output=True)

doing = sorted(Path("tasks/doing").glob("[0-9]*.md"))
result = "worked"
leave = step.endswith("-dirty")
step = step.removesuffix("-dirty")
if step in ("done", "done-nocommit") and doing:
    task = doing[0]
    target = Path("tasks/done") / task.stem
    target.mkdir(parents=True)
    task.rename(target / "task.md")
    (target / "report.md").write_text("# Звіт\n\n## Що змінилось для власника\n- зроблено\n")
    if step == "done":
        git("add", "-A", "tasks"); git("commit", "-q", "-m", f"{task.stem}: done", "--", "tasks")
elif step == "block" and doing:
    task = doing[0]
    task.write_text(task.read_text() + "1. Застосувати?\n   Відповідь:\n")
    task.rename(Path("tasks/blocked") / task.name)
    git("add", "-A", "tasks"); git("commit", "-q", "-m", f"{task.stem}: blocked", "--", "tasks")
elif step == "work":
    Path(f"work-{n}.txt").write_text("progress\n")
    git("add", f"work-{n}.txt"); git("commit", "-q", "-m", f"work {n}")
elif step == "gateq":
    Path("tasks/blocked/900-gate-escalation-20261003T101500Z.md").write_text(
        "# 900\n\nЗалежить від: —\nАудит потрібен: ні\nЕскалація воріт: 2026-10-03T10:15:00Z\n\n"
        "## Питання до власника\n1. Закрити?\n   Відповідь:\n")
elif step == "dirty":
    Path(f"half-{n}.txt").write_text("half done\n")
elif step == "return" and doing:
    doing[0].rename(Path("tasks/todo") / doing[0].name)
    git("add", "-A", "tasks"); git("commit", "-q", "-m", "back to todo")
elif step == "vanish" and doing:
    doing[0].unlink()
    git("add", "-A", "tasks"); git("commit", "-q", "-m", "gone")
elif step == "tidy":
    git("add", "-A"); git("commit", "-q", "-m", "the leftovers")
elif step == "refused":
    hooks = Path(os.environ["FAKE_HOOKS"])
    state = Path(".claude/state/overseer")

    def hook(script, args, envelope):
        return subprocess.run([sys.executable, str(hooks / script), *args], input=json.dumps(envelope), capture_output=True, text=True).stdout

    def use(i, name, tool_input):
        return [{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": tool_input}]}},
                {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "ok"}]}}]

    said = ""
    for turn in range(1, 5):   # three claims, each audited and refused; the fourth stop hears the third verdict
        records = [{"type": "user", "message": {"role": "user", "content": "do the unit"}}]
        records += use(0, "Agent", {"subagent_type": "overseer", "prompt": "OVERSEER_REQUEST x"}) if turn > 1 else []
        records += use(1, "Edit", {"file_path": os.path.abspath("src/unit.py")}) + use(2, "Bash", {"command": "pytest -q"})
        transcript = home / f"transcript-{n}-{turn}.jsonl"
        transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        said = hook("overseer_stop.py", [], {"hook_event_name": "Stop", "transcript_path": str(transcript),
                                            "last_assistant_message": f"Attempt {turn}.\n\n=== UNIT 1 COMPLETE ==="})
        if turn == 4:
            break
        request = json.loads((state / "pending.json").read_text())["id"]
        hook("overseer_verdict.py", ["guard"], {"hook_event_name": "PreToolUse", "tool_name": "Agent",
                                               "tool_input": {"subagent_type": "overseer", "prompt": f"OVERSEER_REQUEST {request}"}})
        reply = {"verdict": "BLOCK", "check": 4, "reason": f"ПРИЧИНА-{turn}: the assertion passes without the fix",
                 "evidence": ["src/unit.py:1"], "category": "none"}
        hook("overseer_verdict.py", ["record"], {"hook_event_name": "SubagentStop", "agent_type": "overseer", "agent_id": f"a{turn}",
                                                "last_assistant_message": "```json\n" + json.dumps(reply) + "\n```"})
    (home / "hook-said").write_text(said)
elif step == "limit":
    result = "You've hit your session limit · resets 3pm (UTC)"
elif step == "auth":
    result = "Invalid API key · Please run /login"
elif step == "garbage":
    print("Error: something broke before a session existed")
    sys.exit(1)
if leave:
    Path(f"left-{n}.txt").write_text("the task's own file, never committed\n")
    git("add", f"left-{n}.txt")
print(json.dumps({"type": "result", "is_error": step in ("limit", "auth"), "result": result,
                  "session_id": session, "total_cost_usd": costs[session]}))
'''

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def sh(cwd: Path, *cmd: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=ok)


def task(deps: str = "—", questions: str = "") -> str:
    return (f"# Задача\n\nЗалежить від: {deps}\nАудит потрібен: ні\n\n## Що зробити\n- щось\n\n"
            f"## Готово, коли\n- готово\n\n## Питання до власника\n{questions}")


class World:
    """A repository on unattended/work, its bare origin, an inbox, and the fake claude."""

    def __init__(self, plan: str = "", branch: str = "unattended/work", push_first: bool = True) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="board-runner-"))
        self.repo, self.origin, self.inbox, self.home = (self.dir / n for n in ("repo", "origin.git", "inbox", "fake"))
        for d in (self.repo, self.inbox, self.home):
            d.mkdir()
        sh(self.dir, "git", "init", "-q", "--bare", "-b", "main", str(self.origin))
        sh(self.repo, "git", "init", "-q", "-b", "main")
        for key, value in (("user.name", "t"), ("user.email", "t@example.invalid")):
            sh(self.repo, "git", "config", key, value)
        for column in ("todo", "doing", "blocked", "done"):
            (self.repo / "tasks" / column).mkdir(parents=True)
            (self.repo / "tasks" / column / ".gitkeep").touch()
        (self.repo / ".gitignore").write_text(".claude/state/\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-q", "-m", "base")
        sh(self.repo, "git", "remote", "add", "origin", str(self.origin))
        sh(self.repo, "git", "push", "-q", "origin", "main")
        if branch != "main":
            sh(self.repo, "git", "switch", "-q", "-c", branch)
            if push_first:
                sh(self.repo, "git", "push", "-q", "origin", branch)
        self.fake = self.home / "claude"
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        (self.home / "plan").write_text(plan)
        self.state = self.repo / ".claude/state/board"

    def put(self, column: str, name: str, text: str | None = None, commit: bool = True) -> None:
        (self.repo / "tasks" / column / name).write_text(task() if text is None else text, encoding="utf-8")
        if commit:
            sh(self.repo, "git", "add", "-A", "tasks")
            sh(self.repo, "git", "commit", "-q", "-m", f"owner: {name}")

    def run(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        # The real runner exports its own settings (BOARD_MAX_USD…) to the session this suite may
        # run in; none of them may reach the runner under test.
        full = {**{k: v for k, v in os.environ.items() if not k.startswith("BOARD_")},
                "CLAUDE_PROJECT_DIR": str(self.repo), "BOARD_CLAUDE": str(self.fake),
                "BOARD_INBOX": str(self.inbox), "BOARD_PAUSE_SEC": "0", "BOARD_LIMIT_WAIT_SEC": "0",
                "FAKE_HOME": str(self.home), "FAKE_RUNNER": str(RUNNER), "FAKE_HOOKS": str(ROOT / ".claude/hooks")}
        # The suite itself may run inside a Claude Code session; the runner under test is the
        # owner's process unless a case says otherwise (CLAUDECODE="1").
        for name in ("CLAUDE_UNATTENDED_SESSION", "CLAUDECODE"):
            full.pop(name, None)
        full.update(env)
        return subprocess.run(["bash", str(RUNNER), *args], cwd=self.dir, capture_output=True, text=True, env=full, check=False)

    def calls(self) -> list[dict[str, Any]]:
        path = self.home / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def argv(self, n: int) -> list[str]:
        return [str(a) for a in self.calls()[n]["argv"]]

    def status(self) -> str:
        return (self.state / "status").read_text().strip() if (self.state / "status").exists() else ""

    def log(self, *args: str) -> list[str]:
        return sh(self.repo, "git", "log", "--format=%s", *args).stdout.splitlines()

    def head(self, where: str = "HEAD") -> str:
        return sh(self.repo, "git", "rev-parse", where, ok=False).stdout.strip()

    def origin_head(self, branch: str = "unattended/work") -> str:
        return sh(self.origin, "git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", ok=False).stdout.strip()

    def costs(self) -> dict[str, Any]:
        tasks: dict[str, Any] = json.loads((self.state / "costs.json").read_text())["tasks"]
        return tasks

    def has(self, rel: str) -> bool:
        return (self.repo / rel).exists()


# --- the tracer ----------------------------------------------------------------------------------
print("the tracer: todo → doing → done, seen through files and git alone")
w = World("done")
w.put("todo", "001-first.md")
base = w.head()
r = w.run()
check("the runner exits 0", r.returncode == 0, r.stdout + r.stderr)
check("the task is in done/ with task.md and report.md", w.has("tasks/done/001-first/task.md") and w.has("tasks/done/001-first/report.md")
      and not w.has("tasks/doing/001-first.md") and not w.has("tasks/todo/001-first.md"))
check("two commits: the move to doing/, then the agent's", w.log(f"{base}..HEAD") == ["001-first: done", "board: 001-first → doing"], w.log(f"{base}..HEAD"))
moved = sh(w.repo, "git", "show", "--stat", "--format=", "HEAD~1").stdout
check("the commit to doing/ holds the move and nothing else", "tasks/{todo => doing}/001-first.md" in moved and moved.count("|") == 1, moved)
a = w.argv(0)
check("claude was called once, with -p and the three flags the owner named",
      len(w.calls()) == 1 and a[0] == "-p" and "--settings" in a and a[a.index("--settings") + 1] == ".claude/settings.json"
      and a[a.index("--permission-mode") + 1] == "auto" and a[a.index("--output-format") + 1] == "json", a)
check("a fresh conversation: no --resume, no -c", "--resume" not in a and "-c" not in a and "--continue" not in a, a)
check("the prompt names the task file and the manual", "tasks/doing/001-first.md" in a[1] and "tasks/README.md" in a[1], a[1])
check("no budget flag unless a cap is set", "--max-budget-usd" not in a, a)
check("it ran in the repository", w.calls()[0]["cwd"] == str(w.repo))
check("status: idle, todo empty", w.status().startswith("state=idle task=- since=") and "reason=todo-empty" in w.status(), w.status())
check("since= is UTC in ISO form", w.status().split("since=")[1][:20].endswith("Z") and "T" in w.status().split("since=")[1][:20], w.status())
check("the summary is written", "idle" in (w.state / "summary.md").read_text() and "done: 1" in (w.state / "summary.md").read_text())
check("the cost of the task is recorded", w.costs()["001-first"]["cost_usd"] == 1.0 and w.costs()["001-first"]["outcome"] == "done", w.costs())
check("the branch was pushed", w.origin_head() == w.head(), (w.origin_head(), w.head()))
logged = (w.state / "events.log").read_text()
check("events: start, commit, attempt, task-done, pushed, stop", all(word in logged for word in
      (" start ", " commit ", " attempt 001-first 1", " task-done 001-first", " pushed ", " stop idle ")), logged)
check("the lock is released", not (w.state / "lock").exists())

# --- a task already in doing/ ----------------------------------------------------------------------
print("a task already in doing/")
w = World("done")
w.put("doing", "001-first.md")
w.put("todo", "000-earlier.md")
base = w.head()
r = w.run("--once")
check("it is finished first, with no second move to doing/", w.has("tasks/done/001-first/report.md") and w.has("tasks/todo/000-earlier.md")
      and w.log(f"{base}..HEAD") == ["001-first: done"], w.log(f"{base}..HEAD"))
check("--once: one task, exit 0, state=stopped", r.returncode == 0 and len(w.calls()) == 1 and "state=stopped" in w.status()
      and "reason=once" in w.status(), w.status())

# --- order and dependencies; a fresh conversation per task -----------------------------------------
print("order, dependencies, one conversation per task")
w = World("done done done")
w.put("todo", "002-second.md", task(deps="001"))
w.put("todo", "010-third.md")
w.put("todo", "001-first.md")
w.put("todo", "020-waits.md", task(deps="999"))
r = w.run()
order = [str(c["argv"][1]).split("tasks/doing/")[1].split(".md")[0] for c in w.calls()]
check("001, then 002 (it depended on 001), then 010", order == ["001-first", "002-second", "010-third"], order)
check("each task in a fresh conversation", all("--resume" not in w.argv(i) for i in range(3)))
check("a task whose dependency never comes: waiting-owner, exit 0", r.returncode == 0 and "state=waiting-owner" in w.status()
      and w.has("tasks/todo/020-waits.md"), w.status() + r.stdout)
check("the summary names the missing dependency", "999" in (w.state / "summary.md").read_text(), (w.state / "summary.md").read_text())

# --- continuing ------------------------------------------------------------------------------------
print("a session that stopped with the task open is continued")
w = World("work idle done")
w.put("todo", "001-first.md")
r = w.run()
check("three calls; the second and third resume the first conversation", len(w.calls()) == 3 and "--resume" not in w.argv(0)
      and w.argv(1)[w.argv(1).index("--resume") + 1] == "s1" and w.argv(2)[w.argv(2).index("--resume") + 1] == "s1", [c["argv"] for c in w.calls()])
check("the continue prompt names the task", "tasks/doing/001-first.md" in w.argv(1)[1] and w.argv(1)[1].startswith("Continue"))
check("one conversation's running total is counted once: 3 USD, not 1+2+3", w.costs()["001-first"]["cost_usd"] == 3.0, w.costs())
check("every attempt's raw figure is kept", [a["reported_usd"] for a in w.costs()["001-first"]["attempts"]] == [1.0, 2.0, 3.0])

print("output without a session id: the next attempt is a fresh conversation")
w = World("garbage done")
w.put("todo", "001-first.md")
r = w.run()
check("the second call does not resume", len(w.calls()) == 2 and "--resume" not in w.argv(1) and w.has("tasks/done/001-first/report.md"), r.stdout + r.stderr)

# --- three attempts without a commit ----------------------------------------------------------------
print("three attempts in a row without a commit: the task is parked, the board is not stopped")
w = World("idle idle idle idle idle")
w.put("todo", "001-first.md")
r = w.run()
check("after three the runner parks the task in blocked/ and ends as waiting-owner, exit 0", r.returncode == 0 and len(w.calls()) == 3
      and w.has("tasks/blocked/001-first.md") and not w.has("tasks/doing/001-first.md") and "state=waiting-owner" in w.status(), w.status() + r.stdout + r.stderr)
r = w.run()
check("a restart does not touch it: it waits for the owner", r.returncode == 0 and len(w.calls()) == 3 and w.has("tasks/blocked/001-first.md"), len(w.calls()))
(w.home / "plan").write_text("idle idle idle idle done")
parked = w.repo / "tasks/blocked/001-first.md"
parked.write_text(parked.read_text(encoding="utf-8").replace("Відповідь:", "Відповідь: продовжити"), encoding="utf-8")
r = w.run()
check("the owner's answer returns it with a fresh count and a fresh conversation; the task then finishes", r.returncode == 0
      and w.has("tasks/done/001-first/report.md") and len(w.calls()) == 5 and "--resume" not in w.argv(3), r.stdout + r.stderr)

print("a commit resets the count; the count is per task")
w = World("idle idle work idle idle done idle idle done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
r = w.run()
check("idle idle WORK idle idle done, then idle idle done: both finish", r.returncode == 0 and len(w.calls()) == 9
      and w.has("tasks/done/001-first/report.md") and w.has("tasks/done/002-second/report.md"), w.status() + r.stdout)

# --- the usage limit -----------------------------------------------------------------------------------
print("the usage limit")
w = World("limit limit limit limit done")
w.put("todo", "001-first.md")
r = w.run(BOARD_LIMIT_WAIT_SEC="1")
check("four limit notices are not attempts: the task still finishes", r.returncode == 0 and len(w.calls()) == 5 and w.has("tasks/done/001-first/report.md"), w.status())
check("the wait is logged", "usage limit; waiting 1 s" in r.stdout and (w.state / "events.log").read_text().count(" limit") >= 4, r.stdout)
check("the attempts are marked", [a["limit"] for a in w.costs()["001-first"]["attempts"]] == [True, True, True, True, False])
runner_text = RUNNER.read_text(encoding="utf-8")
check("the default wait is 15 minutes, the limit 12 hours, the stall 3 attempts",
      "BOARD_LIMIT_WAIT_SEC:-900}" in runner_text and "BOARD_TASK_MAX_SEC:-43200}" in runner_text and "BOARD_STALL_ATTEMPTS:-3}" in runner_text)

# --- twelve hours ----------------------------------------------------------------------------------------
print("a task older than the limit")
w = World("done")
w.put("doing", "001-first.md")
w.state.mkdir(parents=True)
old = (datetime.now(UTC) - timedelta(hours=13)).strftime("%Y-%m-%dT%H:%M:%SZ")
(w.state / "costs.json").write_text(json.dumps({"tasks": {"001-first": {"started_utc": old, "session_id": "s9", "attempts_without_commit": 0,
                                                                        "cost_usd": 0.0, "attempts": []}}}))
w.put("todo", "002-second.md")
r = w.run()
check("started 13 hours ago: parked without one more call (reason deadline); the next task is done by the one call", r.returncode == 0
      and w.has("tasks/blocked/001-first.md") and "довше за 12 год" in (w.repo / "tasks/blocked/001-first.md").read_text(encoding="utf-8")
      and len(w.calls()) == 1 and w.has("tasks/done/002-second/report.md"), w.status() + r.stdout + r.stderr)
w = World("idle")
w.put("doing", "001-first.md")
w.state.mkdir(parents=True)
(w.state / "costs.json").write_text(json.dumps({"tasks": {"001-first": {"started_utc": (datetime.now(UTC) - timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "session_id": "s9", "attempts_without_commit": 0, "cost_usd": 0.0, "attempts": []}}}))
(w.home / "plan").write_text("done")
r = w.run()
check("started 11 hours ago: it runs, resuming the stored conversation", r.returncode == 0 and w.argv(0)[w.argv(0).index("--resume") + 1] == "s9", w.status())

# --- the budget -------------------------------------------------------------------------------------------
print("the budget of one task")
w = World("work work work work")
w.put("todo", "001-first.md")
r = w.run(BOARD_MAX_USD="3", FAKE_COST="2")
first, second = w.argv(0), w.argv(1)
check("the first call may spend the whole cap", first[first.index("--max-budget-usd") + 1] == "3.00", first)
check("the second call gets what is left", second[second.index("--max-budget-usd") + 1] == "1.00", second)
check("with the cap spent the task is parked (reason budget): exit 0, no third call", r.returncode == 0 and len(w.calls()) == 2
      and w.has("tasks/blocked/001-first.md") and "бюджет: 3 USD" in (w.repo / "tasks/blocked/001-first.md").read_text(encoding="utf-8")
      and " task-parked 001-first budget" in (w.state / "events.log").read_text(), w.status() + r.stdout + r.stderr)
parked = w.repo / "tasks/blocked/001-first.md"
parked.write_text(parked.read_text(encoding="utf-8").replace("Відповідь:", "Відповідь: так, продовжити"), encoding="utf-8")
(w.home / "plan").write_text("x x done")
r = w.run(BOARD_MAX_USD="3", FAKE_COST="2")
third = w.argv(2)
check("the owner's answer gives it one more budget of the same size; the 4 USD already spent stay on its bill", len(w.calls()) == 3
      and third[third.index("--max-budget-usd") + 1] == "3.00" and w.has("tasks/done/001-first/report.md")
      and w.costs()["001-first"]["cost_usd"] == 6.0, (third, w.costs()))

# --- blocked, answered, unblocked ------------------------------------------------------------------------
print("a task that needs the owner")
w = World("block done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
r = w.run()
check("001 went to blocked/ with its question, 002 was done after it", w.has("tasks/blocked/001-first.md") and w.has("tasks/done/002-second/report.md")
      and "Відповідь:" in (w.repo / "tasks/blocked/001-first.md").read_text(), r.stdout)
check("then the runner stops: waiting-owner, exit 0", r.returncode == 0 and "state=waiting-owner" in w.status(), w.status())
check("the summary shows the question", "Застосувати?" in (w.state / "summary.md").read_text())
check("costs: 001 is recorded as blocked", w.costs()["001-first"]["outcome"] == "blocked")
# the owner answers in the branch, from another clone
other = w.dir / "owner"
sh(w.dir, "git", "clone", "-q", "-b", "unattended/work", str(w.origin), str(other))
for key, value in (("user.name", "owner"), ("user.email", "o@example.invalid")):
    sh(other, "git", "config", key, value)
answered = (other / "tasks/blocked/001-first.md").read_text().replace("Відповідь:", "Відповідь: так")
(other / "tasks/blocked/001-first.md").write_text(answered)
(other / "tasks/todo/003-new.md").write_text(task())
sh(other, "git", "add", "-A")
sh(other, "git", "commit", "-q", "-m", "owner: answer 001, add 003")
sh(other, "git", "push", "-q", "origin", "unattended/work")
(w.home / "plan").write_text("x x done done")
r = w.run()
check("the answer and the new task arrive by pull --rebase; both get done", r.returncode == 0 and w.has("tasks/done/001-first/report.md")
      and w.has("tasks/done/003-new/report.md") and "state=idle" in w.status(), w.status() + r.stdout + r.stderr)
check("the answered task returned to todo/ in a commit of its own", any(s.startswith("board: answered, back to todo — 001-first.md") for s in w.log()), w.log()[:8])
check("task.md in done/ carries the answer", "Відповідь: так" in (w.repo / "tasks/done/001-first/task.md").read_text())
check("001 came back before 003", [str(c["argv"][1]).split("tasks/doing/")[1][:3] for c in w.calls()[2:]] == ["001", "003"])

# --- the inbox ---------------------------------------------------------------------------------------------
print("the inbox")
w = World("done done")
w.put("todo", "005-old.md", "old text\n")
w.put("doing", "001-busy.md")
(w.inbox / "005-new.md").write_text(task())
(w.inbox / "001-busy.md").write_text("an edit that must not land\n")
(w.inbox / "007-fresh.md").write_text(task())
base = w.head()
r = w.run()
subjects = w.log(f"{base}..HEAD")
check("the inbox files are taken in one commit, before any task", subjects[-1].startswith("board: from the inbox — 2 file(s) taken"), subjects)
check("005 was replaced, 007 added, both done", w.has("tasks/done/005-new/report.md") and w.has("tasks/done/007-fresh/report.md")
      and not w.has("tasks/todo/005-old.md") and not w.has("tasks/done/005-old"), subjects)
check("the copy of a task in doing/ stayed in the inbox and changed nothing", (w.inbox / "001-busy.md").exists()
      and "must not land" not in (w.repo / "tasks/done/001-busy/task.md").read_text() and not w.has("tasks/todo/001-busy.md"))
check("the inbox is otherwise empty", sorted(p.name for p in w.inbox.iterdir()) == ["001-busy.md"])
w = World("done")
w.put("todo", "001-first.md")
r = w.run(BOARD_INBOX=str(w.dir / "no-such-inbox"))
check("no inbox directory at all is fine", r.returncode == 0 and w.has("tasks/done/001-first/report.md"), r.stdout + r.stderr)

# --- a move the agent did not commit ------------------------------------------------------------------------
print("the agent moved the task and forgot the commit")
w = World("done-nocommit")
w.put("todo", "001-first.md")
(w.repo / "stray.txt").write_text("not the runner's business\n")
r = w.run()
check("the runner commits tasks/ — and only tasks/", r.returncode == 0 and w.log()[0] == "board: 001-first → done (the move was left uncommitted)"
      and sh(w.repo, "git", "status", "--porcelain").stdout.strip() == "?? stray.txt", sh(w.repo, "git", "status", "--porcelain").stdout + r.stdout)
check("what was pushed includes it", w.origin_head() == w.head())

# --- push and no push ------------------------------------------------------------------------------------------
print("--no-push; a remote that does not have the branch yet")
w = World("done")
w.put("todo", "001-first.md")
before = w.origin_head()
r = w.run("--no-push")
check("--no-push: the task is done, origin did not move", r.returncode == 0 and w.has("tasks/done/001-first/report.md") and w.origin_head() == before
      and " pushed " not in (w.state / "events.log").read_text(), w.origin_head())
w = World("done", push_first=False)
w.put("todo", "001-first.md")
r = w.run()
check("the first push creates the branch on origin", r.returncode == 0 and w.origin_head() == w.head() != "", r.stdout + r.stderr)

# --- the branch ---------------------------------------------------------------------------------------------------
print("the branch")
w = World("done", branch="main")
w.put("todo", "001-first.md")
head = w.head()
r = w.run()
check("on main with no work branch anywhere: exit 1, state=error, nothing committed, claude not called",
      r.returncode == 1 and "state=error" in w.status() and "reason=branch" in w.status() and w.head() == head and len(w.calls()) == 0, w.status())
r = w.run(BOARD_BRANCH="main")
check("BOARD_BRANCH=main is refused: commits go to unattended/* only", r.returncode == 1 and "reason=branch" in w.status() and w.head() == head and len(w.calls()) == 0, w.status())
w = World("done")
w.put("todo", "001-first.md")
sh(w.repo, "git", "switch", "-q", "main")
r = w.run()
check("started on main while the work branch exists: it switches and works there", r.returncode == 0
      and sh(w.repo, "git", "branch", "--show-current").stdout.strip() == "unattended/work" and w.has("tasks/done/001-first/report.md")
      and w.head("main") == sh(w.origin, "git", "rev-parse", "refs/heads/main").stdout.strip(), r.stdout + r.stderr)

# --- a pull that does not apply ---------------------------------------------------------------------------------------
print("a pull that conflicts")
w = World("done")
w.put("todo", "001-first.md")
sh(w.repo, "git", "push", "-q", "origin", "unattended/work")
other = w.dir / "owner"
sh(w.dir, "git", "clone", "-q", "-b", "unattended/work", str(w.origin), str(other))
for key, value in (("user.name", "owner"), ("user.email", "o@example.invalid")):
    sh(other, "git", "config", key, value)
(other / "tasks/todo/001-first.md").write_text("the owner's version\n")
sh(other, "git", "commit", "-q", "-am", "owner edit")
sh(other, "git", "push", "-q", "origin", "unattended/work")
w.put("todo", "001-first.md", "the local version\n")
head = w.head()
r = w.run()
check("exit 1, state=error reason=pull-conflict, claude not called", r.returncode == 1 and "state=error" in w.status()
      and "reason=pull-conflict" in w.status() and len(w.calls()) == 0, w.status() + r.stdout)
check("the rebase was aborted: nothing of the work moved, no rebase in progress", w.head("HEAD~1") == head and not (w.repo / ".git/rebase-merge").exists()
      and not (w.repo / ".git/rebase-apply").exists(), w.log()[:3])
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("the one commit on top is the journal entry: the conflict, and that the whole board stopped", w.log()[0].startswith("board: anomaly — the board:")
      and "конфлікт під час pull" in journal and "дошку зупинено (причина `pull-conflict`)" in journal
      and sh(w.repo, "git", "status", "--porcelain").stdout == "", journal)

# --- one runner at a time; the mode file -------------------------------------------------------------------------------
print("the lock and the mode file")
w = World("done")
w.put("todo", "001-first.md")
w.state.mkdir(parents=True)
(w.state / "lock").write_text(str(os.getpid()))
r = w.run()
check("a live lock: the second runner refuses, exit 1, nothing done", r.returncode == 1 and "another runner" in r.stderr and len(w.calls()) == 0
      and w.has("tasks/todo/001-first.md"), r.stderr)
(w.state / "lock").write_text("999999")
r = w.run()
check("a stale lock is reclaimed", r.returncode == 0 and w.has("tasks/done/001-first/report.md"), r.stdout + r.stderr)
check("the session saw mode=unattended and CLAUDE_UNATTENDED_SESSION=1", w.calls()[0]["mode"] == "unattended" and w.calls()[0]["unattended"] == "1", w.calls()[0])
check("afterwards the mode file is absent again, as before", not w.has(".claude/state/overseer/mode") and not (w.state / "mode.before").exists())
w = World("done")
w.put("todo", "001-first.md")
(w.repo / ".claude/state/overseer").mkdir(parents=True)
(w.repo / ".claude/state/overseer/mode").write_text("attended\n")
r = w.run()
check("a mode the owner had set is put back", (w.repo / ".claude/state/overseer/mode").read_text() == "attended\n" and w.calls()[0]["mode"] == "unattended")
w = World("done")
w.put("todo", "001-first.md")
w.state.mkdir(parents=True)
(w.repo / ".claude/state/overseer").mkdir(parents=True)
(w.repo / ".claude/state/overseer/mode").write_text("unattended\n")
(w.state / "mode.before").write_text("(absent)\n")
r = w.run()
check("a runner killed without its trap left mode.before: the next one heals it", not w.has(".claude/state/overseer/mode") and r.returncode == 0, r.stdout)

# --- --status; a TERM ---------------------------------------------------------------------------------------------------
print("--status and a kill")
r = w.run("--status")
check("--status prints the status line and the board, runs nothing", r.returncode == 0 and "state=idle" in r.stdout and "done: 1" in r.stdout and len(w.calls()) == 1, r.stdout)
r = w.run("--bogus")
check("an unknown option: exit 2", r.returncode == 2 and "--bogus" in r.stderr)
w = World("idle")
w.put("todo", "001-first.md")
slow = w.home / "claude"
slow.write_text("#!/usr/bin/env bash\necho $$ > \"$FAKE_HOME/pid\"\nsleep 60\n")
env = {**os.environ, "CLAUDE_PROJECT_DIR": str(w.repo), "BOARD_CLAUDE": str(slow), "BOARD_INBOX": str(w.inbox), "FAKE_HOME": str(w.home)}
proc = subprocess.Popen(["bash", str(RUNNER)], cwd=w.dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(100):
    if (w.home / "pid").exists():
        break
    time.sleep(0.1)
child = int((w.home / "pid").read_text()) if (w.home / "pid").exists() else 0
proc.terminate()
proc.wait(timeout=20)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


check("TERM: the session goes down with the runner", child > 0 and not alive(child), child)
check("…the mode file is restored, the lock released, the status says so", not w.has(".claude/state/overseer/mode") and not (w.state / "lock").exists()
      and "state=error" in w.status() and "reason=killed" in w.status(), w.status())

# --- board 005: the gate's escalation is closed through the board ----------------------------------
GATE = ROOT / ".claude/hooks/gate.py"


def escalate(w: World) -> tuple[str, str]:
    """The REAL gate gives up on its first block in w.repo: (stamp, the question's file name)."""
    (w.repo / ".claude").mkdir(exist_ok=True)
    (w.repo / ".claude/project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="false"\nGATE_MAX_BLOCKS="1"\n')
    (w.repo / "mod.py").write_text("x = 1\n")
    sh(w.repo, "git", "add", "mod.py", ".claude/project.env")
    sh(w.repo, "git", "commit", "-q", "-m", "code")
    (w.repo / "mod.py").write_text("x = 1\nq = 9\n")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(w.repo)}
    subprocess.run([sys.executable, str(GATE), "--layer", "stop", "--hook"], cwd=w.repo, env=env, text=True,
                   input=json.dumps({"session_id": "s1"}), capture_output=True, check=True)
    names = sorted(p.name for p in (w.repo / "tasks/blocked").glob("9*-gate-escalation-*.md"))
    return str(escalations(w)["open"][-1]["stamp"]), names[0] if names else ""


def escalations(w: World) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((w.repo / ".claude/state/gate/escalations.json").read_text())
    return data


def write_answer(path: Path, text: str) -> None:
    head, _, rest = path.read_text(encoding="utf-8").rpartition("Відповідь:")
    path.write_text(f"{head}Відповідь: {text}{rest}", encoding="utf-8")


def owner_answers(w: World, name: str, text: str = "закрити") -> None:
    """The owner answers where they work: in the branch, from another checkout, and pushes."""
    clone = Path(tempfile.mkdtemp(prefix="owner-", dir=w.dir))
    sh(w.dir, "git", "clone", "-q", "-b", "unattended/work", str(w.origin), str(clone))
    for key, value in (("user.name", "owner"), ("user.email", "owner@example.invalid")):
        sh(clone, "git", "config", key, value)
    write_answer(clone / "tasks/blocked" / name, text)
    sh(clone, "git", "commit", "-q", "-am", "owner: answer")
    sh(clone, "git", "push", "-q", "origin", "unattended/work")


def events(w: World) -> str:
    return (w.state / "events.log").read_text()


print("board 005, the demonstration: escalation → a task in blocked/ → the owner's answer → closed")
w = World("")
stamp, name = escalate(w)
stem = name.removesuffix(".md")
check("the gate's escalation is a question in tasks/blocked/, not yet committed",
      name.startswith("900-gate-escalation-") and name in sh(w.repo, "git", "status", "--porcelain", "-uall").stdout, name)
r = w.run()
check("the runner commits the question by itself and pushes it", w.log("-1") == ["board: the gate asks the owner — 1 question(s) in blocked/"]
      and w.origin_head() == w.head() and sh(w.repo, "git", "show", "--stat", "--format=", "HEAD").stdout.count("|") == 1, w.log("-3"))
check("unanswered: the escalation stays open, the runner waits for the owner", len(escalations(w)["open"]) == 1
      and r.returncode == 0 and "state=waiting-owner" in w.status() and w.has(f"tasks/blocked/{name}"), w.status())
check("the summary shows the question to the owner", name in (w.state / "summary.md").read_text(), (w.state / "summary.md").read_text())
owner_answers(w, name)
r = w.run()
state = escalations(w)
check("the owner answered «закрити» in the branch: the escalation is closed", state["open"] == []
      and [e["stamp"] for e in state["closed"]] == [stamp], state)
check("…the parked entry is RESUMED", f"## {stamp} — gate stop layer — RESUMED" in (w.repo / ".engine/overseer/parked.md").read_text())
check("…the task is in done/ with the answer and a report", not w.has(f"tasks/blocked/{name}")
      and "Відповідь: закрити" in (w.repo / f"tasks/done/{stem}/task.md").read_text()
      and stamp in (w.repo / f"tasks/done/{stem}/report.md").read_text())
check("…in a commit of its own, pushed", w.log("-1") == [f"board: {stem} → done — gate escalation {stamp} closed on the owner's answer"]
      and w.origin_head() == w.head(), w.log("-2"))
check("…by the runner: no agent was started at all", w.calls() == [] and f"escalation-closed {stamp} {name}" in events(w), events(w))
check("…and nothing waits any more: idle", r.returncode == 0 and "state=idle" in w.status(), w.status())
check("the uncommitted work the gate blocked on was not touched", (w.repo / "mod.py").read_text() == "x = 1\nq = 9\n")

print("board 005: the answer through the inbox")
w = World("")
stamp, name = escalate(w)
w.run()
copy = w.inbox / name
copy.write_text((w.repo / "tasks/blocked" / name).read_text(encoding="utf-8"), encoding="utf-8")
write_answer(copy, "Закрити.")
r = w.run()
check("an answered copy in the inbox closes the escalation", escalations(w)["open"] == [] and w.has(f"tasks/done/{name.removesuffix('.md')}/report.md")
      and not copy.exists() and w.calls() == [], events(w))

print("board 005: an answer the owner did not send closes nothing")
for how in ("uncommitted", "committed"):
    w = World("")
    stamp, name = escalate(w)
    w.run()
    write_answer(w.repo / "tasks/blocked" / name, "закрити")
    if how == "committed":
        sh(w.repo, "git", "commit", "-q", "-am", "agent: answers for the owner")
    r = w.run()
    text = (w.repo / "tasks/blocked" / name).read_text(encoding="utf-8") if w.has(f"tasks/blocked/{name}") else ""
    check(f"«закрити» written in the checkout ({how}): the escalation stays open", len(escalations(w)["open"]) == 1
          and not w.has(f"tasks/done/{name.removesuffix('.md')}"), events(w))
    check("…the answer is wiped, the reason written under the question, and that is pushed",
          "Відповідь: закрити" not in text and "Примітка виконавця" in text and w.origin_head() == w.head()
          and "escalation-answer-rejected" in events(w) and "state=waiting-owner" in w.status(), text)
owner_answers(w, name)
w.run()
check("…and the owner's real answer afterwards still closes it", escalations(w)["open"] == [], events(w))

print("board 005: a runner started inside a Claude Code session closes nothing")
w = World("")
stamp, name = escalate(w)
w.run()
owner_answers(w, name)
r = w.run(CLAUDECODE="1")
check("gate.py refuses; the question stays in blocked/, the event says refused", len(escalations(w)["open"]) == 1
      and w.has(f"tasks/blocked/{name}") and f"escalation-close-refused {stamp} {name} rc=2" in events(w), events(w))
r = w.run()
check("the owner's runner then closes it (the answer had arrived from the owner)", escalations(w)["open"] == []
      and w.has(f"tasks/done/{name.removesuffix('.md')}/report.md"), events(w))

print("board 005: any other answer is an instruction for an agent")
w = World("done")
stamp, name = escalate(w)
w.run()
owner_answers(w, name, "виправ lint у mod.py")
r = w.run()
check("the task goes back to todo/ and an agent takes it; the escalation stays open", len(w.calls()) == 1
      and f"tasks/doing/{name}" in w.argv(0)[1] and len(escalations(w)["open"]) == 1 and "escalation-closed" not in events(w), events(w))

print("board 005: an escalation that is no longer open")
w = World("")
stamp, name = escalate(w)
w.run()
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(w.repo)}
subprocess.run([sys.executable, str(GATE), "--close-escalation", stamp], cwd=w.repo, env=env, capture_output=True, check=True)
owner_answers(w, name)
r = w.run()
check("closed in a terminal earlier: the question still leaves the board, the report says so",
      "вже не була відкрита" in (w.repo / f"tasks/done/{name.removesuffix('.md')}/report.md").read_text()
      and "was-not-open" in events(w) and "state=idle" in w.status(), events(w))

print("board 005: a question that appears during a session is published before the task closes")
w = World("gateq done")
w.put("todo", "001-first.md")
r = w.run()
log = w.log()
asks = "board: the gate asks the owner — 1 question(s) in blocked/"
check("its own commit, between the two attempts", asks in log and log.index(asks) > log.index("001-first: done"), log)
lines = events(w).splitlines()
ask_at = next((i for i, line in enumerate(lines) if " gate-question " in line), -1)
check("…pushed at once, while the task was still open", ask_at >= 0 and " pushed " in lines[ask_at + 1]
      and any(" attempt 001-first 2" in line for line in lines[ask_at:]), lines)
check("…the commit holds the question and nothing else",
      sh(w.repo, "git", "show", "--stat", "--format=", f"HEAD~{log.index(asks)}").stdout.count("|") == 1)
check("the task finished; the run ends waiting for the owner", w.has("tasks/done/001-first/report.md") and "state=waiting-owner" in w.status(), w.status())

# --- board 008: an action the owner approved with «так» is taken by the runner ----------------------
OLD_SETTINGS, NEW_SETTINGS = '{"hooks": {}}\n', '{"hooks": {"PostToolUse": []}}\n'
# The stand-in for tests/test_settings_proposal.py: red only when the applied file says "red".
STUB_TEST = 'import sys\nfrom pathlib import Path\nsys.exit(1 if "red" in Path(".claude/settings.json").read_text() else 0)\n'


def proposal_world(plan: str = "done", proposal: str = NEW_SETTINGS) -> tuple[World, str]:
    """A repository with a live settings file, a proposal and its test; 008 waits in blocked/ with
    the question and the offer an agent wrote (board.py action-line). Returns the world and the offer."""
    w = World(plan)
    for rel, text in ((".claude/settings.json", OLD_SETTINGS), ("docs/tasks/settings.json", proposal),
                      ("tests/test_settings_proposal.py", STUB_TEST)):
        (w.repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (w.repo / rel).write_text(text)
    sh(w.repo, "git", "add", ".claude/settings.json", "docs", "tests")
    sh(w.repo, "git", "commit", "-q", "-m", "settings and the proposal")
    offer = sh(w.repo, sys.executable, str(ROOT / ".claude/unattended/board.py"), "--root", str(w.repo), "action-line", "apply-settings").stdout.strip()
    w.put("blocked", "008-wiring.md", task(questions=f"1. Застосувати пропозицію налаштувань?\n   {offer}\n   Відповідь:\n"))
    sh(w.repo, "git", "push", "-q", "origin", "unattended/work")
    return w, offer


def live_settings(w: World) -> str:
    return (w.repo / ".claude/settings.json").read_text()


def blocked_text(w: World) -> str:
    path = w.repo / "tasks/blocked/008-wiring.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


print("board 008, the demonstration: the question with an offer → the owner's «так» → the runner applies")
w, offer = proposal_world()
r = w.run()
check("unanswered: nothing is applied, no agent starts, the runner waits for the owner", live_settings(w) == OLD_SETTINGS and w.calls() == []
      and "state=waiting-owner" in w.status() and "Застосувати пропозицію налаштувань?" in (w.state / "summary.md").read_text(), w.status())
owner_answers(w, "008-wiring.md", "так")
r = w.run()
done = (w.repo / "tasks/done/008-wiring/task.md").read_text(encoding="utf-8") if w.has("tasks/done/008-wiring/task.md") else ""
check("the owner answered «так»: the live file is the proposal", live_settings(w) == NEW_SETTINGS, events(w))
check("…applied by the runner, before any agent was started", "action-applied apply-settings 008-wiring.md" in events(w)
      and events(w).index("action-applied") < events(w).index(" attempt 008-wiring 1"), events(w))
check("…committed by itself: the settings file and nothing else", "settings: the proposal docs/tasks/settings.json applied on the owner's answer (008-wiring)" in w.log()
      and sh(w.repo, "git", "show", "--stat", "--format=", "HEAD~" + str(w.log().index("settings: the proposal docs/tasks/settings.json applied on the owner's answer (008-wiring)"))).stdout.count("|") == 1, w.log()[:6])
check("…the offer is replaced by the outcome; the answer stays", "Дію виконано" in done and "Дія виконавця:" not in done and "Відповідь: так" in done, done)
check("…then the task went back to todo/ and the agent closed it with a report", len(w.calls()) == 1 and "tasks/doing/008-wiring.md" in w.argv(0)[1]
      and w.has("tasks/done/008-wiring/report.md"), events(w))
check("…everything pushed, the tree clean, idle", w.origin_head() == w.head() and "state=idle" in w.status()
      and sh(w.repo, "git", "status", "--porcelain").stdout == "", w.status())
r = w.run()
check("a second run applies nothing again", events(w).count("action-applied") == 1 and len(w.calls()) == 1)

print("board 008: «так» the owner did not send applies nothing")
for how in ("uncommitted", "committed"):
    w, offer = proposal_world()
    w.run()
    write_answer(w.repo / "tasks/blocked/008-wiring.md", "так")
    if how == "committed":
        sh(w.repo, "git", "commit", "-q", "-am", "agent: answers for the owner")
    r = w.run()
    check(f"«так» written in the checkout ({how}): the live file is untouched, no agent starts", live_settings(w) == OLD_SETTINGS and w.calls() == []
          and "action-applied" not in events(w), events(w))
    check("…the answer is wiped, the reason written under the question, the offer kept, and that is pushed",
          "Відповідь: так" not in blocked_text(w) and "Примітка виконавця" in blocked_text(w) and offer in blocked_text(w)
          and "action-answer-rejected apply-settings 008-wiring.md" in events(w) and w.origin_head() == w.head(), blocked_text(w))
owner_answers(w, "008-wiring.md", "Так.")
w.run()
check("…and the owner's real answer afterwards is acted on", live_settings(w) == NEW_SETTINGS, events(w))

print("board 008: the answer through the inbox")
w, offer = proposal_world()
w.run()
copy = w.inbox / "008-wiring.md"
copy.write_text(blocked_text(w), encoding="utf-8")
write_answer(copy, "так")
w.run()
check("an answered copy in the inbox is the owner's: applied", live_settings(w) == NEW_SETTINGS and not copy.exists(), events(w))

print("board 008: a runner started inside a Claude Code session applies nothing")
w, offer = proposal_world()
w.run()
owner_answers(w, "008-wiring.md", "так")
r = w.run(CLAUDECODE="1")
check("owner_action.py refuses; the question stays in blocked/ with its offer, no agent starts", live_settings(w) == OLD_SETTINGS and offer in blocked_text(w)
      and "action-refused apply-settings 008-wiring.md rc=2" in events(w) and w.calls() == [], events(w))
w.run()
check("the owner's runner then applies it", live_settings(w) == NEW_SETTINGS, events(w))

print("board 008: the proposal changed after the question — the owner approved another file")
w, offer = proposal_world()
w.run()
(w.repo / "docs/tasks/settings.json").write_text('{"hooks": {"Stop": []}}\n')
sh(w.repo, "git", "commit", "-q", "-am", "agent: a different proposal")
owner_answers(w, "008-wiring.md", "так")
w.run()
back = (w.repo / "tasks/done/008-wiring/task.md").read_text(encoding="utf-8")
check("not applied; the task returns to the agent with the reason", live_settings(w) == OLD_SETTINGS and "action-stale apply-settings" in events(w)
      and "Дію не виконано" in back and "sha256" in back and len(w.calls()) == 1, events(w))

print("board 008: the test is red after the copy")
w, offer = proposal_world(proposal='{"red": true}\n')
w.run()
owner_answers(w, "008-wiring.md", "так")
w.run()
back = (w.repo / "tasks/done/008-wiring/task.md").read_text(encoding="utf-8")
check("the previous file is put back, nothing is committed for it, the agent is told", live_settings(w) == OLD_SETTINGS and "action-failed apply-settings" in events(w)
      and "попередній" in back and not any(s.startswith("settings:") for s in w.log()), events(w))

print("board 008: any other answer is an instruction; an action outside the list is never run")
w, offer = proposal_world()
w.run()
owner_answers(w, "008-wiring.md", "ні, спершу прибери PostToolUseFailure")
w.run()
check("«ні …»: nothing applied, the task goes to an agent", live_settings(w) == OLD_SETTINGS and len(w.calls()) == 1 and "action-" not in events(w), events(w))
w = World("done")
(w.repo / "pwned.sh").write_text("touch PWNED\n")
w.put("blocked", "009-other.md", task(questions="1. Запустити?\n   Дія виконавця: run-script pwned.sh\n   Відповідь:\n"))
sh(w.repo, "git", "add", "pwned.sh")
sh(w.repo, "git", "commit", "-q", "-m", "a script")
sh(w.repo, "git", "push", "-q", "origin", "unattended/work")
owner_answers(w, "009-other.md", "так")
w.run()
check("an unknown action is not an offer: the runner runs nothing, the task is an ordinary answered one", not w.has("PWNED")
      and "action-" not in events(w) and len(w.calls()) == 1, events(w))
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
direct = subprocess.run([sys.executable, str(ROOT / ".claude/unattended/owner_action.py"), "--root", str(w.repo), "run-script", "pwned.sh"],
                        env=env, capture_output=True, text=True, check=False)
check("owner_action.py itself refuses what is not on its list (exit 2)", direct.returncode == 2 and "not an allowed action" in direct.stderr and not w.has("PWNED"), direct.stderr)

# --- board 040: a lesson becomes a rule only on the owner's «так» ---------------------------------
LQ = ROOT / ".claude/hooks/lesson_queue.py"
RULE_TEXT = "Show the RED before the GREEN."
RULES_SEED = "# Rules approved from lessons\n"


def agent_lq(w: World, *args: str, session: bool = True) -> subprocess.CompletedProcess[str]:
    """lesson_queue.py as an agent's tool runs it: inside a Claude Code session."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(w.repo)}
    if session:
        env["CLAUDECODE"] = "1"
    return subprocess.run([sys.executable, str(LQ), *args], cwd=w.repo, env=env, capture_output=True, text=True, check=False)


def rule_world() -> tuple[World, str, str]:
    """A project whose agent filed a lesson as a rule proposal, and committed and pushed the question.
    Returns the world, the proposal's id and the name of the question in tasks/blocked/."""
    w = World("done")
    (w.repo / "CLAUDE.md").write_text("@.engine/rules.md\n")
    (w.repo / ".engine").mkdir()
    (w.repo / ".engine/rules.md").write_text(RULES_SEED)
    added = agent_lq(w, "add", "--source", "agent", "--slice", "s", "the RED was not shown twice")
    ident = added.stdout.split()[0].lstrip("#")
    filed = agent_lq(w, "resolve", ident, "--to", "rule", "--text", RULE_TEXT, "--why", "audit 06 caught it twice", "--recommend", "так: двічі зловлено")
    assert filed.returncode == 0, filed.stderr
    name = f"800-rule-proposal-{ident}.md"
    sh(w.repo, "git", "add", "-A", "CLAUDE.md", ".engine", "tasks")
    sh(w.repo, "git", "commit", "-q", "-m", "agent: a lesson, proposed as a rule")
    sh(w.repo, "git", "push", "-q", "origin", "unattended/work")
    return w, ident, name


def rules_file(w: World) -> str:
    return (w.repo / ".engine/rules.md").read_text(encoding="utf-8")


def proposals_file(w: World) -> str:
    return (w.repo / ".engine/rule-proposals.md").read_text(encoding="utf-8")


print("board 040, the demonstration: a lesson → a question in blocked/ → the owner's «так» → the runner makes it a rule")
w, ident, name = rule_world()
stem = name.removesuffix(".md")
asked = (w.repo / "tasks/blocked" / name).read_text(encoding="utf-8")
check("the lesson filed as a rule is a question to the owner with the exact text and the overseer's recommendation",
      "Зробити це правилом?" in asked and f"  > {RULE_TEXT}\n" in asked and "Рекомендація наглядача: так: двічі зловлено" in asked
      and "Дія виконавця: promote-rule " in asked, asked)
check("nothing is a rule yet", rules_file(w) == RULES_SEED and f"## RP-{ident} —" in proposals_file(w) and "— PROPOSED" in proposals_file(w))
refused = agent_lq(w, "promote", ident)
check("the agent's own promote is refused: the owner has not answered", refused.returncode == 1 and "owner" in refused.stderr and rules_file(w) == RULES_SEED, refused.stderr)
r = w.run()
check("unanswered: the runner promotes nothing, starts no agent and waits for the owner", rules_file(w) == RULES_SEED and w.calls() == []
      and "state=waiting-owner" in w.status() and "Зробити це правилом?" in (w.state / "summary.md").read_text(), w.status())
owner_answers(w, name, "так")
r = w.run()
check("the owner answered «так»: the rule is in .engine/rules.md, word for word", f"- {RULE_TEXT} (RP-{ident}, " in rules_file(w), events(w) + rules_file(w))
check("…the proposal is APPROVED", f"## RP-{ident} — " in proposals_file(w) and "— APPROVED" in proposals_file(w), proposals_file(w))
check("…done by the runner, with no agent", f"action-applied promote-rule {name}" in events(w) and w.calls() == [], events(w))
rule_commit = f"rules: promote-rule on the owner's answer ({stem})"
shown = sh(w.repo, "git", "show", "--stat", "--format=", "HEAD~" + str(w.log().index(rule_commit))).stdout if rule_commit in w.log() else ""
check("…committed by itself: the rules and the proposals, nothing else", ".engine/rules.md" in shown and ".engine/rule-proposals.md" in shown and shown.count("|") == 2, w.log()[:5])
closed = (w.repo / "tasks/done" / stem / "task.md").read_text(encoding="utf-8") if w.has(f"tasks/done/{stem}/task.md") else ""
check("…the question is in done/ with the answer, the outcome and the runner's report", "Відповідь: так" in closed and "правило додано" in closed
      and "Дія виконавця:" not in closed and "став правилом" in (w.repo / "tasks/done" / stem / "report.md").read_text(encoding="utf-8"), closed)
check("…everything pushed, the tree clean, idle", w.origin_head() == w.head() and "state=idle" in w.status()
      and sh(w.repo, "git", "status", "--porcelain").stdout == "", w.status())
before = rules_file(w)
w.run()
check("a second run adds nothing", rules_file(w) == before and events(w).count("action-applied") == 1)

print("board 040: «так» the owner did not send makes no rule")
for how in ("uncommitted", "committed"):
    w, ident, name = rule_world()
    w.run()
    write_answer(w.repo / "tasks/blocked" / name, "так")
    direct = agent_lq(w, "promote", ident)
    check(f"an agent writes «так» itself ({how}) and runs promote: refused inside its session", direct.returncode == 1 and "CLAUDECODE" in direct.stderr
          and rules_file(w) == RULES_SEED, direct.stderr)
    if how == "committed":
        sh(w.repo, "git", "commit", "-q", "-am", "agent: answers for the owner")
    w.run()
    left = (w.repo / "tasks/blocked" / name).read_text(encoding="utf-8")
    check("…and the runner wipes that answer, says why, keeps the offer and promotes nothing", rules_file(w) == RULES_SEED and "Відповідь: так" not in left
          and "Примітка виконавця" in left and "Дія виконавця: promote-rule" in left and f"action-answer-rejected promote-rule {name}" in events(w)
          and w.calls() == [] and w.origin_head() == w.head(), left)
owner_answers(w, name, "Так.")
w.run()
check("…the owner's real answer afterwards is acted on", f"- {RULE_TEXT} (RP-{ident}, " in rules_file(w), events(w))

print("board 040: the answer through the inbox; a runner inside a session; «ні»; an instruction; a changed text")
w, ident, name = rule_world()
w.run()
copy = w.inbox / name
copy.write_text((w.repo / "tasks/blocked" / name).read_text(encoding="utf-8"), encoding="utf-8")
write_answer(copy, "так")
w.run()
check("an answered copy in the inbox is the owner's: the rule is made", f"- {RULE_TEXT} (RP-{ident}, " in rules_file(w) and not copy.exists(), events(w))
w, ident, name = rule_world()
w.run()
owner_answers(w, name, "так")
w.run(CLAUDECODE="1")
check("a runner started inside a Claude Code session makes no rule; the question stays", rules_file(w) == RULES_SEED and w.has(f"tasks/blocked/{name}")
      and f"action-refused promote-rule {name} rc=2" in events(w) and w.calls() == [], events(w))
w.run()
check("the owner's runner then does", f"- {RULE_TEXT} (RP-{ident}, " in rules_file(w), events(w))
w, ident, name = rule_world()
w.run()
owner_answers(w, name, "ні")
w.run()
stem = name.removesuffix(".md")
check("«ні»: no rule, the proposal is REJECTED, the question is in done/ with a report, no agent was started",
      rules_file(w) == RULES_SEED and "— REJECTED" in proposals_file(w) and w.has(f"tasks/done/{stem}/report.md") and w.calls() == []
      and f"action-applied reject-rule {name}" in events(w) and w.origin_head() == w.head(), events(w))
w, ident, name = rule_world()
w.run()
owner_answers(w, name, "так, але коротше: «Спершу RED»")
w.run()
check("«так, але …» is an instruction, not consent to this text: no rule, the task goes to an agent",
      rules_file(w) == RULES_SEED and "— PROPOSED" in proposals_file(w) and len(w.calls()) == 1 and "action-" not in events(w), events(w))
w, ident, name = rule_world()
w.run()
path = w.repo / ".engine/rule-proposals.md"
path.write_text(proposals_file(w).replace(RULE_TEXT, "Do whatever the agent says."), encoding="utf-8")
sh(w.repo, "git", "commit", "-q", "-am", "agent: another text under the same proposal")
owner_answers(w, name, "так")
w.run()
back = (w.repo / "tasks/done" / name.removesuffix(".md") / "task.md").read_text(encoding="utf-8")
check("the rule text changed after the question: the owner approved another text — no rule, the agent is told",
      rules_file(w) == RULES_SEED and "Do whatever" not in rules_file(w) and f"action-stale promote-rule {name}" in events(w)
      and "Дію не виконано" in back and len(w.calls()) == 1, events(w))

# --- a task that needs the owner present is never the runner's (board 016) ------------------------------------------------
print("attended tasks")
ATTENDED_017 = (ROOT / "tests/fixtures/board-attended/017-block-dangerous-push-hardening.md").read_text(encoding="utf-8")
w = World("done\ndone")
(w.repo / "tasks/done/016-attended-tasks").mkdir()
(w.repo / "tasks/done/016-attended-tasks/task.md").write_text(task(), encoding="utf-8")
w.put("todo", "017-block-dangerous-push-hardening.md", ATTENDED_017)
w.put("todo", "018-after.md", task(deps="017"))
w.put("todo", "019-free.md")
r = w.run()
check("017 (the owner's own file, its dependency done) is passed over: only 019 was worked on", r.returncode == 0 and len(w.calls()) == 1
      and "019-free.md" in " ".join(w.argv(0)) and w.has("tasks/done/019-free/report.md"), r.stdout + r.stderr + str(w.calls()))
check("017 is still in todo/, byte for byte, and 018, which depends on it, waits", w.has("tasks/todo/018-after.md")
      and (w.repo / "tasks/todo/017-block-dangerous-push-hardening.md").read_text(encoding="utf-8") == ATTENDED_017)
check("the runner stops saying it waits for the owner — presence named", "state=waiting-owner" in w.status()
      and "presence" in (w.state / "summary.md").read_text(encoding="utf-8"), w.status())
check("no commit of the runner ever moved 017", not any("017-block" in line for line in w.log() if not line.startswith("owner: ")), w.log())
w = World("done")
w.put("todo", "017-block-dangerous-push-hardening.md", ATTENDED_017.replace("Залежить від: 016", "Залежить від: —"))
r = w.run("--once")
check("017 alone, nothing to wait for, even with --once: claude is not called, the task does not move", r.returncode == 0
      and len(w.calls()) == 0 and w.has("tasks/todo/017-block-dangerous-push-hardening.md") and "state=waiting-owner" in w.status(), w.status() + r.stderr)
w = World("done")
w.put("doing", "017-block-dangerous-push-hardening.md", ATTENDED_017)
w.put("todo", "019-free.md")
r = w.run()
check("017 left in doing/ by the owner's session: the runner does not continue it — claude not called, reason=attended", r.returncode == 0
      and len(w.calls()) == 0 and w.has("tasks/doing/017-block-dangerous-push-hardening.md") and "state=waiting-owner" in w.status()
      and "reason=attended" in w.status(), w.status() + r.stdout + r.stderr)
r = w.run("--retry")
check("…nor with --retry", len(w.calls()) == 0 and w.has("tasks/doing/017-block-dangerous-push-hardening.md"), w.status())
w = World("done")
w.put("todo", "017-ordinary.md", ATTENDED_017.replace("Потрібна присутність власника: так", "Потрібна присутність власника: ні").replace("Залежить від: 016", "Залежить від: —"))
r = w.run()
check("the negative case: the same task with «ні» IS taken", len(w.calls()) == 1 and w.has("tasks/done/017-ordinary/report.md"), w.status() + r.stderr)

# --- the soft stop (board 019) ---------------------------------------------------------------------------------------------
print("the soft stop: --stop-after-task")
w = World("done done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
flag = w.state / "stop-after-task"
r = w.run(FAKE_STOP_AT="0")
asked = (w.home / "stop-asked").read_text(encoding="utf-8")
check("the command, given while a task is running, exits 0 and says the runner will stop", asked.startswith("0\n") and "001-first" in asked, asked)
check("the current task is finished, the next one is not started", r.returncode == 0 and len(w.calls()) == 1
      and w.has("tasks/done/001-first/report.md") and w.has("tasks/todo/002-second.md"), r.stdout + r.stderr)
check("state=stopped, the task named, reason=stop-after-task", "state=stopped task=001-first" in w.status()
      and "reason=stop-after-task" in w.status(), w.status())
check("the flag is removed", not flag.exists())
check("the finished task was pushed, the lock released, the stop is in the events and the summary", w.origin_head() == w.head()
      and not (w.state / "lock").exists() and " stop stopped stop-after-task 001-first" in events(w)
      and " stop-requested " in events(w) and "stopped" in (w.state / "summary.md").read_text(encoding="utf-8"), events(w))
r = w.run()
check("the next start is an ordinary one: the second task is done", r.returncode == 0 and len(w.calls()) == 2
      and w.has("tasks/done/002-second/report.md") and "state=idle" in w.status(), w.status() + r.stdout + r.stderr)

w = World("work idle done done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
r = w.run(FAKE_STOP_AT="0", FAKE_STOP_HOW="file")
check("the flag file alone is enough, and a task still open is continued to its end: three calls, then stopped",
      r.returncode == 0 and len(w.calls()) == 3 and w.has("tasks/done/001-first/report.md") and w.has("tasks/todo/002-second.md")
      and "state=stopped task=001-first" in w.status() and not (w.state / "stop-after-task").exists(), w.status() + r.stdout + r.stderr)
check("the work of the task is all committed: nothing is lost", sh(w.repo, "git", "status", "--porcelain").stdout == ""
      and "work 0" in w.log(), sh(w.repo, "git", "status", "--porcelain").stdout)

w = World("block done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
r = w.run(FAKE_STOP_AT="0")
check("a task that ends in blocked/ is a finished task too: stopped, the next one not started", r.returncode == 0 and len(w.calls()) == 1
      and w.has("tasks/blocked/001-first.md") and w.has("tasks/todo/002-second.md") and "state=stopped task=001-first" in w.status(), w.status())

w = World("done done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
r = w.run()
check("the negative case: no flag — both tasks are done, state=idle", r.returncode == 0 and len(w.calls()) == 2 and "state=idle" in w.status(), w.status())

w = World("done")
w.put("todo", "001-first.md")
r = w.run("--stop-after-task")
check("no runner is working: the command refuses (exit 1), says so, and leaves no flag", r.returncode == 1
      and "no runner" in r.stderr and not (w.state / "stop-after-task").exists() and len(w.calls()) == 0, r.stdout + r.stderr)
w.state.mkdir(parents=True, exist_ok=True)
dead = subprocess.Popen(["true"])
dead.wait()
(w.state / "lock").write_text(f"{dead.pid}\n")
r = w.run("--stop-after-task")
check("…the same with the lock of a runner that died", r.returncode == 1 and not (w.state / "stop-after-task").exists(), r.stdout + r.stderr)
(w.state / "stop-after-task").touch()
r = w.run()
check("a flag left over from a runner that died does not stop the new one: removed at the start, the task is done",
      r.returncode == 0 and len(w.calls()) == 1 and w.has("tasks/done/001-first/report.md") and "state=idle" in w.status()
      and not (w.state / "stop-after-task").exists() and " stop-flag-stale" in events(w), w.status() + events(w))

# --- one task never stops the board (board 021) ---------------------------------------------------------------------------
print("one task never stops the board: a stuck task is parked with its reason, the next one goes")
w = World("dirty idle idle done")
w.put("todo", "001-stuck.md")
w.put("todo", "002-next.md")
base = w.head()
r = w.run()
text = (w.repo / "tasks/blocked/001-stuck.md").read_text(encoding="utf-8") if w.has("tasks/blocked/001-stuck.md") else ""
check("the stuck task is in blocked/, the next task is done, the runner exits 0", r.returncode == 0 and len(w.calls()) == 4 and text != ""
      and not w.has("tasks/doing/001-stuck.md") and w.has("tasks/done/002-next/report.md") and "state=waiting-owner" in w.status(), w.status() + r.stdout + r.stderr)
why, _, asked = text.partition("## Питання до власника")
check("the task file says why it stopped, in a section of its own before the questions", "## Чому зупинилась" in why
      and "3 спроб(и) поспіль не дали жодного commit-а" in why and "Що зробити" in why.split("## Чому зупинилась")[0], text)
check("…and asks the owner, with an empty answer line", "1. Задача застрягла" in asked and asked.rstrip().endswith("Відповідь:"), asked)
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
entry = journal.split("\n## ")[-1]
check("the anomaly journal has the entry: UTC time, the task, what happened, what was done", journal.startswith("# Журнал аномалій дошки")
      and entry.split(" — ")[0].endswith("Z") and "T" in entry.split(" — ")[0] and entry.splitlines()[0].endswith("— 001-stuck")
      and "- Що сталося: 3 спроб(и)" in entry and "- Що зроблено: задачу перенесено в `blocked/`" in entry, journal)
subjects = w.log(f"{base}..HEAD")
check("one commit holds the move and the journal, and it is pushed", "board: 001-stuck → blocked — the runner parked it (no-commit); the board goes on" in subjects
      and set(sh(w.repo, "git", "show", "--name-only", "--format=", f"HEAD~{subjects.index('board: 001-stuck → blocked — the runner parked it (no-commit); the board goes on')}").stdout.split())
      == {"tasks/ANOMALIES.md", "tasks/blocked/001-stuck.md", "tasks/doing/001-stuck.md"} and w.origin_head() == w.head(), subjects)
stash = sh(w.repo, "git", "rev-parse", "-q", "--verify", "refs/stash", ok=False).stdout.strip()
check("the uncommitted work of the stuck task is in a stash the task file names; the next task began on a clean tree", stash != ""
      and f"git stash apply {stash}" in why and "half-0.txt" in sh(w.repo, "git", "show", "--name-only", "--format=", f"{stash}^3", ok=False).stdout
      and not w.has("half-0.txt") and sh(w.repo, "git", "status", "--porcelain").stdout == "", sh(w.repo, "git", "status", "--porcelain").stdout + why)
check("events and costs: the task is recorded as parked and blocked", " task-parked 001-stuck no-commit stash=" in events(w)
      and w.costs()["001-stuck"]["outcome"] == "blocked" and "001-stuck" in (w.state / "summary.md").read_text(encoding="utf-8"), events(w))
check("the next task had a conversation of its own", "--resume" not in w.argv(3) and "tasks/doing/002-next.md" in w.argv(3)[1], w.argv(3))

w = World("idle idle idle idle idle idle done")
w.put("todo", "001-stuck.md")
w.put("todo", "002-stuck-too.md")
w.put("todo", "003-fine.md")
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("two stuck tasks in a row: both parked, the third done, two journal entries in order", r.returncode == 0 and len(w.calls()) == 7
      and w.has("tasks/blocked/001-stuck.md") and w.has("tasks/blocked/002-stuck-too.md") and w.has("tasks/done/003-fine/report.md")
      and journal.count("\n## ") == 2 and journal.index("— 001-stuck") < journal.index("— 002-stuck-too"), journal + w.status())

w = World("idle idle idle x idle idle idle")
w.put("todo", "001-stuck.md")
w.run()
parked = w.repo / "tasks/blocked/001-stuck.md"
parked.write_text(parked.read_text(encoding="utf-8").replace("Відповідь:", "Відповідь: ще раз"), encoding="utf-8")
(w.home / "plan").write_text("x x x idle idle idle")
r = w.run()
text = parked.read_text(encoding="utf-8")
check("parked a second time: one section with two dated lines, a second question, the first answer kept", r.returncode == 0
      and text.count("## Чому зупинилась") == 1 and text.count("спроб(и) поспіль") == 2 and "Відповідь: ще раз" in text
      and "2. Задача застрягла" in text and text.rstrip().endswith("Відповідь:"), text)

w = World("return done")
w.put("todo", "001-odd.md")
w.put("todo", "002-next.md")
r = w.run()
text = (w.repo / "tasks/blocked/001-odd.md").read_text(encoding="utf-8") if w.has("tasks/blocked/001-odd.md") else ""
check("the agent put its task back into todo/: parked with that reason instead of being taken again for ever", r.returncode == 0
      and len(w.calls()) == 2 and "агент повернув задачу" in text and w.has("tasks/done/002-next/report.md"), w.status() + r.stdout + r.stderr)

w = World("vanish done")
w.put("todo", "001-gone.md")
w.put("todo", "002-next.md")
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("a task that vanished from the board: written into the journal, the next task is done, exit 0", r.returncode == 0 and len(w.calls()) == 2
      and "— 001-gone" in journal and "задача зникла з дошки" in journal and w.has("tasks/done/002-next/report.md") and "state=idle" in w.status()
      and sh(w.repo, "git", "status", "--porcelain").stdout == "" and w.origin_head() == w.head(), w.status() + journal + r.stderr)

# --- a task closes with a clean tree only (board 029) ----------------------------------------------------------------------
print("board 029: a closed task that left uncommitted files gets one turn to commit or remove them")


def porcelain(w: World) -> str:
    return sh(w.repo, "git", "status", "--porcelain").stdout


w = World("done-dirty tidy done")
w.put("todo", "001-first.md")
w.put("todo", "002-next.md")
r = w.run()
check("the agent is given the turn back once, and the next task follows", r.returncode == 0 and len(w.calls()) == 3
      and w.has("tasks/done/001-first/report.md") and w.has("tasks/done/002-next/report.md"), w.status() + r.stdout + r.stderr)
a = w.argv(1) if len(w.calls()) > 1 else ["", ""]
check("the turn continues the task's conversation and asks one thing: commit what is the task's or remove the rest",
      "--resume" in a and a[a.index("--resume") + 1] == "s1" and "left-0.txt" in a[1] and "001-first" in a[1]
      and "commit" in a[1].lower() and "remove" in a[1].lower() and "commit_checkpoint.sh" in a[1], a)
check("the tree is clean, nothing is in the journal, the cleaning is an event", porcelain(w) == "" and not w.has("tasks/ANOMALIES.md")
      and " dirty-tree 001-first " in events(w) and " dirty-tree-cleaned 001-first" in events(w), porcelain(w) + events(w))
check("the turn is booked on the task: two attempts, its cost", len(w.costs()["001-first"]["attempts"]) == 2
      and w.costs()["001-first"]["cost_usd"] == 2.0 and w.costs()["001-first"]["outcome"] == "done", w.costs())
check("the second task had a conversation of its own and was asked nothing more", "--resume" not in w.argv(2) and "tasks/doing/002-next.md" in w.argv(2)[1], w.argv(2))

w = World("done-dirty idle done")
w.put("todo", "001-first.md")
w.put("todo", "002-next.md")
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("still dirty after the one turn: no second request, the next task is done, exit 0", r.returncode == 0 and len(w.calls()) == 3
      and w.has("tasks/done/002-next/report.md") and "state=idle" in w.status(), w.status() + r.stdout + r.stderr)
check("the journal has one entry, for that task, with the list of files", journal.count("\n## ") == 1 and "— 001-first" in journal
      and "незакомічені файли" in journal and "`left-0.txt`" in journal, journal)
check("nothing was deleted, stashed or committed by the runner: the file is where the agent left it, still staged",
      porcelain(w) == "A  left-0.txt\n" and sh(w.repo, "git", "rev-parse", "-q", "--verify", "refs/stash", ok=False).stdout.strip() == "", porcelain(w))
check("the journal entry is committed and pushed", w.origin_head() == w.head()
      and any(s.startswith("board: anomaly — 001-first:") for s in w.log()), w.log())
check("the next task is not blamed for files that were there before it began", "— 002-next" not in journal and " dirty-tree 002-next" not in events(w), events(w))

w = World("block-dirty idle")
w.put("todo", "001-ask.md")
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("a task the agent moved to blocked/ is held to the same rule", r.returncode == 0 and len(w.calls()) == 2 and "--resume" in w.argv(1)
      and w.has("tasks/blocked/001-ask.md") and "`left-0.txt`" in journal and "state=waiting-owner" in w.status(), w.status() + journal + r.stderr)

w = World("done-dirty limit tidy")
w.put("todo", "001-first.md")
r = w.run()
check("a usage-limit notice is not the one turn: it is waited out and asked again", r.returncode == 0 and len(w.calls()) == 3
      and porcelain(w) == "" and not w.has("tasks/ANOMALIES.md"), porcelain(w) + w.status() + r.stderr)

w = World("done-dirty tidy")
w.put("todo", "001-first.md")
r = w.run(BOARD_MAX_USD="1")
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("the task's budget is spent: no turn is bought, the journal gets the entry at once", r.returncode == 0 and len(w.calls()) == 1
      and "`left-0.txt`" in journal and "бюджет" in journal and porcelain(w) == "A  left-0.txt\n", journal + r.stderr)

w = World("done-nocommit")
w.put("todo", "001-first.md")
(w.repo / "stray.txt").write_text("was here before the task\n")
r = w.run()
check("a move left uncommitted under tasks/ is the runner's to commit, and a file that was there before the task is not the task's: no turn, no entry",
      r.returncode == 0 and len(w.calls()) == 1 and porcelain(w) == "?? stray.txt\n" and not w.has("tasks/ANOMALIES.md"), porcelain(w) + r.stderr)

w = World("dirty idle idle done")
w.put("todo", "001-stuck.md")
r = w.run()
check("a task the runner parked is not asked: its work is already in the stash", r.returncode == 0 and len(w.calls()) == 3
      and " dirty-tree " not in events(w) and porcelain(w) == "", events(w))

w = World("done-dirty idle")
w.put("todo", "001-first.md")
for n in range(60):
    (w.repo / f"gen-{n:02d}.txt").write_text("x\n")
w.fake.write_text(FAKE.replace("if leave:", 'if leave:\n    [Path(f"many-{i:02d}.txt").write_text("x\\n") for i in range(60)]'))
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
ask = w.argv(1)[1] if len(w.calls()) > 1 else ""
check("many files: the journal names every one of the task's, none of those that were there before; the request stays short",
      r.returncode == 0 and all(f"`many-{i:02d}.txt`" in journal for i in range(60)) and "gen-" not in journal
      and "many-00.txt" in ask and "many-59.txt" not in ask and "21 more" in ask and "gen-" not in ask, journal + ask)

print("…and what does stop the whole board")
w = World("auth done done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("claude is logged out: the whole board stops — exit 1, state=error reason=logged-out, one call, the next task not started", r.returncode == 1
      and len(w.calls()) == 1 and "state=error task=001-first" in w.status() and "reason=logged-out" in w.status() and w.has("tasks/todo/002-second.md"), w.status() + r.stdout)
check("…the task stays in doing/ (it is not its fault), the journal says so and is pushed", w.has("tasks/doing/001-first.md")
      and "claude розлогінився" in journal and "дошку зупинено (причина `logged-out`)" in journal and w.origin_head() == w.head()
      and sh(w.repo, "git", "status", "--porcelain").stdout == "", journal)
r = w.run()
check("after the login the next start goes on: the logged-out call was no attempt, both tasks are done", r.returncode == 0 and len(w.calls()) == 3
      and w.has("tasks/done/001-first/report.md") and w.has("tasks/done/002-second/report.md")
      and w.costs()["001-first"]["attempts"][0]["auth"] is True and w.costs()["001-first"]["attempts_without_commit"] == 0, w.status() + str(w.costs()))
w = World("idle idle idle done")
w.put("todo", "001-stuck.md")
w.put("todo", "002-next.md")
r = w.run(FAKE_STOP_AT="0", FAKE_STOP_HOW="file")
check("the soft stop holds after a parked task too: parked, stopped, the next one not started", r.returncode == 0 and len(w.calls()) == 3
      and w.has("tasks/blocked/001-stuck.md") and w.has("tasks/todo/002-next.md") and "state=stopped task=001-stuck" in w.status()
      and "reason=stop-after-task" in w.status(), w.status() + r.stdout)
w = World("done done")
w.put("todo", "001-first.md")
w.put("todo", "002-second.md")
os.rename(w.origin, w.dir / "origin-away.git")
r = w.run()
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("origin out of reach is not critical: both tasks are done, each failed push is in the journal", r.returncode == 0 and len(w.calls()) == 2
      and w.has("tasks/done/002-second/report.md") and journal.count("гілку не вдалося надіслати") >= 2
      and sh(w.repo, "git", "status", "--porcelain").stdout == "", journal + r.stdout)
w = World("done")
w.put("todo", "001-first.md")
r = w.run()
check("the negative case: nothing odd happened — no journal is made", r.returncode == 0 and not w.has("tasks/ANOMALIES.md"))
# --- three BLOCKs park the task, and the runner does it (board 031) -----------------------------------
print("three BLOCKs in a row on one unit: the hook stops the session, the runner parks the task and takes the next")
WIRED = json.dumps({"hooks": {"SubagentStop": [{"matcher": "overseer", "hooks": [
    {"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" record'}]}]}})


def audited_world(plan: str) -> World:
    """A world whose settings wire the overseer as a separate agent, with a code file to claim a unit on."""
    world = World(plan)
    (world.repo / ".claude").mkdir(exist_ok=True)
    (world.repo / ".claude/settings.json").write_text(WIRED)
    (world.repo / "src").mkdir()
    (world.repo / "src/unit.py").write_text("def unit():\n    return 1\n")
    sh(world.repo, "git", "add", "-A")
    sh(world.repo, "git", "commit", "-q", "-m", "the project")
    return world


w = audited_world("refused done")
w.put("todo", "001-refused.md")
w.put("todo", "002-next.md")
r = w.run()
said = json.loads((w.home / "hook-said").read_text() or "{}") if (w.home / "hook-said").exists() else {}
check("the hook, under the runner, stopped the session and asked nothing of the agent", said.get("continue") is False and "decision" not in said
      and "001-refused" in said.get("stopReason", ""), said)
text = (w.repo / "tasks/blocked/001-refused.md").read_text(encoding="utf-8") if w.has("tasks/blocked/001-refused.md") else ""
why = text.split("## Чому зупинилась")[-1].split("## Питання до власника")[0]
check("the runner moved the task to blocked/ after ONE session — the fake never touched the task file", r.returncode == 0
      and bool(text) and not w.has("tasks/doing/001-refused.md") and " attempt 001-refused 2" not in events(w), r.stdout + r.stderr + events(w))
check("«Чому зупинилась» carries the unit and the three overseers' verdicts", "наглядач тричі поспіль відхилив один юніт (-|001-refused|unit 1)" in why
      and all(f"BLOCK {k} (" in why and f"перевірка #4): ПРИЧИНА-{k}:" in why for k in (1, 2, 3)), text)
check("…and one question to the owner, unanswered", "1. Три наглядачі поспіль" in text and text.rstrip().endswith("Відповідь:"), text)
journal = (w.repo / "tasks/ANOMALIES.md").read_text(encoding="utf-8") if w.has("tasks/ANOMALIES.md") else ""
check("the event is in the anomaly journal", "— 001-refused\n- Що сталося: наглядач тричі поспіль відхилив один юніт" in journal, journal)
check("the runner took the next task: it is done by the second call", len(w.calls()) == 2 and w.has("tasks/done/002-next/report.md")
      and "state=waiting-owner" in w.status(), w.status() + r.stdout)
check("one commit holds the move and the journal; the event is logged; the marker is gone",
      "board: 001-refused → blocked — the runner parked it (three-blocks); the board goes on" in w.log()
      and " task-parked 001-refused three-blocks" in events(w) and not list(w.state.glob("three-blocks-*")), events(w))
check("the ledger the audits wrote is kept in the stash the task names, and the tree is clean", "git stash apply " in why
      and sh(w.repo, "git", "status", "--porcelain").stdout == "", why)
review = sh(w.repo, "python3", str(ROOT / ".claude/unattended/board.py"), "--root", str(w.repo), "review", "--since", "main", ok=False)
check("the review shows it among the anomalies", "наглядач тричі поспіль" in review.stdout.split("Аномалії")[-1], review.stdout[-1500:] + review.stderr)
parked = w.repo / "tasks/blocked/001-refused.md"
parked.write_text(text.replace("Відповідь:", "Відповідь: спробуй інакше"), encoding="utf-8")
sh(w.repo, "git", "commit", "-q", "-am", "owner: answer")
sh(w.repo, "git", "push", "-q", "origin", "unattended/work")
(w.home / "plan").write_text("refused done done")
r = w.run()
check("after the owner's answer the task is taken again and finished: the old BLOCKs do not park it a second time", r.returncode == 0
      and w.has("tasks/done/001-refused/report.md") and events(w).count(" task-parked 001-refused") == 1, r.stdout + r.stderr + events(w))
w = audited_world("idle done")
w.put("todo", "001-quiet.md")
r = w.run()
check("the negative case: a session without three BLOCKs is simply continued — nothing is parked", r.returncode == 0 and len(w.calls()) == 2
      and w.has("tasks/done/001-quiet/report.md") and "task-parked" not in events(w) and not w.has("tasks/ANOMALIES.md"), events(w))
w = audited_world("done")
w.put("doing", "001-left.md")
w.put("todo", "002-next.md")
w.state.mkdir(parents=True, exist_ok=True)
(w.state / "three-blocks-001-left.json").write_text(json.dumps({"task": "001-left", "unit": "-|001-left|unit 1", "blocks": [
    {"utc": "2026-10-04T10:00:00Z", "request": "r1", "check": 4, "reason": "ЗАЛИШЕНА-ПРИЧИНА"}]}, ensure_ascii=False))
r = w.run()
text = (w.repo / "tasks/blocked/001-left.md").read_text(encoding="utf-8") if w.has("tasks/blocked/001-left.md") else ""
check("a marker left by a runner that died before parking: the next runner parks the task first, with no session for it",
      r.returncode == 0 and "ЗАЛИШЕНА-ПРИЧИНА" in text and len(w.calls()) == 1 and "tasks/doing/002-next.md" in w.argv(0)[1]
      and w.has("tasks/done/002-next/report.md") and not list(w.state.glob("three-blocks-*")), text + r.stdout + r.stderr)
check("the runner's head and both manuals say who parks a task after three BLOCKs",
      "THREE BLOCKS PARK THE TASK" in runner_text.split("set -uo pipefail")[0]
      and all("три вердикти наглядача" in " ".join((ROOT / m).read_text(encoding="utf-8").split()) for m in ("tasks/README.md", "templates/project/tasks/README.md")))

head_text = runner_text.split("set -uo pipefail")[0]
check("the runner's head no longer lists stalled or deadline among its states and names what stops the board",
      "stalled|deadline" not in head_text and "ONE TASK NEVER STOPS THE BOARD" in head_text and "logged-out" in head_text and "pull-conflict" in head_text)

for manual in ("tasks/README.md", "templates/project/tasks/README.md"):
    words = " ".join((ROOT / manual).read_text(encoding="utf-8").split())
    check(f"{manual} tells the owner where a stuck task goes, where the journal is and what stops the whole board",
          "tasks/ANOMALIES.md" in words and "Чому зупинилась" in words and "Одна задача не зупиняє дошку" in words and "розлогінився" in words)
    check(f"{manual} tells the operator to stop the runner this way only, and not to kill it",
          "як зупинити виконавця" in words and "Лише так" in words and "board-runner.sh --stop-after-task" in words
          and "не вбивайте" in words and ".claude/state/board/stop-after-task" in words)
    check(f"{manual} tells the owner that a task closes with a clean tree: one turn back, then the journal, nothing deleted",
          "Задача закривається з чистим робочим деревом" in words and "один раз отримує хід назад" in words and "нічого не видаляє" in words)
check("the runner's own head and the unattended README name the option",
      "--stop-after-task" in runner_text.split("set -uo pipefail")[0] and "--stop-after-task" in (ROOT / ".claude/unattended/README.md").read_text(encoding="utf-8"))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
