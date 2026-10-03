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
session = argv[argv.index("--resume") + 1] if "--resume" in argv else f"s{n + 1}"
costs = json.loads((home / "costs").read_text()) if (home / "costs").exists() else {}
costs[session] = costs.get(session, 0.0) + float(os.environ.get("FAKE_COST", "1"))
(home / "costs").write_text(json.dumps(costs))

def git(*a):
    subprocess.run(["git", *a], check=True, capture_output=True)

doing = sorted(Path("tasks/doing").glob("[0-9]*.md"))
result = "worked"
if step in ("done", "done-nocommit") and doing:
    task = doing[0]
    target = Path("tasks/done") / task.stem
    target.mkdir(parents=True)
    task.rename(target / "task.md")
    (target / "report.md").write_text("# Звіт\n\n## Що змінилось для власника\n- зроблено\n")
    if step == "done":
        git("add", "-A", "tasks"); git("commit", "-q", "-m", f"{task.stem}: done")
elif step == "block" and doing:
    task = doing[0]
    task.write_text(task.read_text() + "1. Застосувати?\n   Відповідь:\n")
    task.rename(Path("tasks/blocked") / task.name)
    git("add", "-A", "tasks"); git("commit", "-q", "-m", f"{task.stem}: blocked")
elif step == "work":
    Path(f"work-{n}.txt").write_text("progress\n")
    git("add", f"work-{n}.txt"); git("commit", "-q", "-m", f"work {n}")
elif step == "gateq":
    Path("tasks/blocked/900-gate-escalation-20261003T101500Z.md").write_text(
        "# 900\n\nЗалежить від: —\nАудит потрібен: ні\nЕскалація воріт: 2026-10-03T10:15:00Z\n\n"
        "## Питання до власника\n1. Закрити?\n   Відповідь:\n")
elif step == "limit":
    result = "You've hit your session limit · resets 3pm (UTC)"
elif step == "garbage":
    print("Error: something broke before a session existed")
    sys.exit(1)
print(json.dumps({"type": "result", "is_error": step == "limit", "result": result,
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
        full = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.repo), "BOARD_CLAUDE": str(self.fake),
                "BOARD_INBOX": str(self.inbox), "BOARD_PAUSE_SEC": "0", "BOARD_LIMIT_WAIT_SEC": "0",
                "FAKE_HOME": str(self.home)}
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
events = (w.state / "events.log").read_text()
check("events: start, commit, attempt, task-done, pushed, stop", all(word in events for word in
      (" start ", " commit ", " attempt 001-first 1", " task-done 001-first", " pushed ", " stop idle ")), events)
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
print("three attempts in a row without a commit")
w = World("idle idle idle idle idle")
w.put("todo", "001-first.md")
r = w.run()
check("the runner stops after three: exit 1, state=stalled", r.returncode == 1 and len(w.calls()) == 3 and "state=stalled task=001-first" in w.status()
      and "reason=no-commit" in w.status(), w.status())
check("the task stays in doing/", w.has("tasks/doing/001-first.md"))
r = w.run()
check("a restart does not get three more: the count is the task's", r.returncode == 1 and len(w.calls()) == 3, len(w.calls()))
(w.home / "plan").write_text("idle idle idle idle done")
r = w.run("--retry")
check("--retry gives a fresh count; the task then finishes", r.returncode == 0 and w.has("tasks/done/001-first/report.md") and len(w.calls()) == 5, r.stdout + r.stderr)

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
w = World("idle")
w.put("doing", "001-first.md")
w.state.mkdir(parents=True)
old = (datetime.now(UTC) - timedelta(hours=13)).strftime("%Y-%m-%dT%H:%M:%SZ")
(w.state / "costs.json").write_text(json.dumps({"tasks": {"001-first": {"started_utc": old, "session_id": "s9", "attempts_without_commit": 0,
                                                                        "cost_usd": 0.0, "attempts": []}}}))
r = w.run()
check("started 13 hours ago: state=deadline, exit 1, claude not called", r.returncode == 1 and "state=deadline task=001-first" in w.status()
      and len(w.calls()) == 0, w.status() + r.stdout + r.stderr)
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
check("with the cap spent the runner stops: state=stalled reason=budget, exit 1, no third call",
      r.returncode == 1 and len(w.calls()) == 2 and "state=stalled task=001-first" in w.status() and "reason=budget" in w.status(), w.status())

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
check("the rebase was aborted: HEAD where it was, no rebase in progress", w.head() == head and not (w.repo / ".git/rebase-merge").exists()
      and not (w.repo / ".git/rebase-apply").exists())

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

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
