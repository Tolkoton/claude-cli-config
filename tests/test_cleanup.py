#!/usr/bin/env python3
"""The cleanup task (board 045): when the board runner has nothing to take, it puts a cleanup
task on the board itself — not more than once a day — and takes it.

Deterministic: every scene runs the real board.py and the real board-runner.sh on a synthetic
project with a bare origin. The agent is a fake claude that does what the task in doing/ says as
far as a script can: for a cleanup task it runs the command the task names — a stub
`.claude/hooks/simplifier.py` that records the call — and closes the task with a report.

  - `board.py cleanup-task`: placed only when nothing can be taken (todo/ empty, or all that is
    left is attended, waits for a dependency or lies in blocked/); never while a task can start
    or one is in doing/; never while a cleanup task is open; once a day (CLEANUP_EVERY_DAYS: `0`
    never, `3` every third day); never in a project without the simplifier;
  - the number: after the owner's tasks, under the open items (700+) — the weekly task's too;
  - the runner: an idle board -> the task appears in one commit with its entry in the anomaly
    journal -> an agent does it (the nightly command ran) -> the runner stops as it did before;
    the same day's next run places nothing, the next day's places one; a board that waits for the
    owner is cleaned too and still ends `waiting-owner`;
  - the review shows the entry in «Аномалії»;
  - the prose: the manuals, the settings.

Run:   python3 tests/test_cleanup.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / ".claude/unattended/board.py"
RUNNER = ROOT / ".claude/unattended/board-runner.sh"
RUNNER_LIMIT_S = 120
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=False)


def out(r: subprocess.CompletedProcess[str]) -> str:
    return f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"


# The project's simplifier: records that the nightly mode ran and answers like the real one.
SIMPLIFIER = """import os, sys
with open(os.environ["FAKE_HOME"] + "/nightly", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
print("0 signal(s) in .claude/state/simplify/signals-full.json")
print("no sharp growth: the nightly cleanup reviews the signals only")
"""
# The agent: one call a line (the task it was given), the task's own command for a cleanup task, then done/.
FAKE = r'''#!/usr/bin/env python3
import os, re, subprocess, sys
from pathlib import Path
doing = sorted(Path("tasks/doing").glob("[0-9]*.md"))
with open(os.environ["FAKE_HOME"] + "/calls", "a") as f:
    f.write((doing[0].name if doing else "-") + " | " + sys.argv[2].split(". ")[1] + "\n")
if doing:
    text, said = doing[0].read_text(encoding="utf-8"), ""
    command = re.search(r"`(python3 \S*simplifier\.py nightly)`", text)
    if "-cleanup-" in doing[0].name and command:
        said = subprocess.run(command.group(1).split(), capture_output=True, text=True, check=True).stdout
    target = Path("tasks/done") / doing[0].stem
    target.mkdir(parents=True)
    doing[0].rename(target / "task.md")
    (target / "report.md").write_text("# report\n" + said)
    subprocess.run(["git", "add", "-A", "tasks"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"{doing[0].stem}: done", "--", "tasks"], check=True)
print('{"type":"result","subtype":"success","is_error":false,"result":"ok","session_id":"s1","total_cost_usd":0.1}')
'''
TASK = "# {n} — Задача\n\nЗалежить від: {dep}\n{more}Аудит потрібен: ні\n\n## Що зробити\n- щось\n\n## Питання до власника\n{ask}"
worlds: list[Path] = []


class World:
    """A project on unattended/work with a bare origin, a stub simplifier and the fake claude."""

    def __init__(self, env: str = "", simplifier: bool = True, weekly: bool = False) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="cleanup-"))
        worlds.append(self.dir)
        self.repo, self.origin, self.home = self.dir / "repo", self.dir / "origin.git", self.dir / "fake"
        self.repo.mkdir()
        self.home.mkdir()
        files = {".claude/project.env": env, ".gitignore": ".claude/state/\n",
                 **{f"tasks/{c}/.gitkeep": "" for c in ("todo", "doing", "blocked", "done")}}
        if simplifier:
            files[".claude/hooks/simplifier.py"] = SIMPLIFIER
        if weekly:   # the project has /maintain: the runner places the weekly task as well
            files[".claude/commands/maintain.md"] = "the command\n"
        for rel, body in files.items():
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(body, encoding="utf-8")
        sh(self.dir, "git", "init", "-q", "--bare", "-b", "main", str(self.origin))
        sh(self.repo, "git", "init", "-q", "-b", "unattended/work")
        for key, value in (("user.name", "t"), ("user.email", "t@example.invalid")):
            sh(self.repo, "git", "config", key, value)
        sh(self.repo, "git", "remote", "add", "origin", str(self.origin))
        self.commit("base")
        fake = self.home / "claude"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    def env(self, **more: str) -> dict[str, str]:
        full = {k: v for k, v in os.environ.items() if not k.startswith("BOARD_") and k not in ("CLAUDE_UNATTENDED_SESSION", "CLAUDECODE")}
        return {**full, "CLAUDE_PROJECT_DIR": str(self.repo), "FAKE_HOME": str(self.home), "BOARD_CLAUDE": str(self.home / "claude"),
                "BOARD_INBOX": str(self.dir / "inbox"), "BOARD_PAUSE_SEC": "0", **more}

    def board(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(BOARD), "--root", str(self.repo), *args], cwd=self.repo, capture_output=True, text=True, check=False, env=self.env())

    def cleanup(self, today: str) -> str:
        r = self.board("cleanup-task", "--today", today)
        assert r.returncode == 0, out(r)
        return r.stdout.strip()

    def runner(self, today: str, *args: str) -> subprocess.CompletedProcess[str]:
        # The limit turns a runner that never stops (a broken daily guard places a task on every pass) into a red check.
        try:
            return subprocess.run(["bash", str(RUNNER), *args], cwd=self.dir, capture_output=True, text=True, check=False, env=self.env(BOARD_TODAY=today), timeout=RUNNER_LIMIT_S)
        except subprocess.TimeoutExpired:
            (self.repo / ".claude/state/board/stop-after-task").touch()   # whatever is left of it stops at its next pass
            return subprocess.CompletedProcess(["board-runner"], 124, "", f"the runner did not stop in {RUNNER_LIMIT_S} s")

    def commit(self, message: str) -> None:
        sh(self.repo, "git", "add", "-A")
        done = sh(self.repo, "git", "commit", "-q", "-m", message)
        assert done.returncode == 0, done.stderr
        sh(self.repo, "git", "push", "-q", "origin", "unattended/work")

    def task(self, column: str, name: str, dep: str = "—", more: str = "", ask: str = "") -> "World":
        number = name.split("-")[0]
        if column == "done":
            (self.repo / "tasks/done" / name).mkdir(parents=True)
            (self.repo / "tasks/done" / name / "task.md").write_text(TASK.format(n=number, dep=dep, more=more, ask=ask), encoding="utf-8")
        else:
            (self.repo / "tasks" / column / f"{name}.md").write_text(TASK.format(n=number, dep=dep, more=more, ask=ask), encoding="utf-8")
        return self

    def move(self, name: str, source: str, target: str) -> None:
        if target == "done":
            (self.repo / "tasks/done" / name).mkdir(parents=True)
            (self.repo / "tasks" / source / f"{name}.md").rename(self.repo / "tasks/done" / name / "task.md")
        else:
            (self.repo / "tasks" / source / f"{name}.md").rename(self.repo / "tasks" / target / f"{name}.md")

    def text(self, rel: str) -> str:
        path = self.repo / rel
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def said(self, name: str) -> list[str]:
        path = self.home / name
        return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []

    def subjects(self) -> list[str]:
        return sh(self.repo, "git", "log", "--format=%s").stdout.splitlines()

    def tasks(self, column: str) -> list[str]:
        return sorted(p.name for p in (self.repo / "tasks" / column).glob("[0-9]*"))

    def status(self) -> str:
        return self.text(".claude/state/board/status")

    def dirty(self) -> str:
        return sh(self.repo, "git", "status", "--porcelain", "--untracked-files=all").stdout.strip()


ATTENDED = "Потрібна присутність власника: так\n"
PLACED = "the cleanup task"   # in the subject of the runner's commit

try:
    # --- when it is placed ----------------------------------------------------------------------------
    print("board.py cleanup-task: only when nothing can be taken")
    check("NEGATIVE: a project without the simplifier gets no task", World(simplifier=False).cleanup("2026-10-05") == "")
    w = World()
    first, second = w.cleanup("2026-10-05"), w.cleanup("2026-10-05")
    check("todo/ is empty: the first call places it, the second does not", first == "tasks/todo/001-cleanup-2026-10-05.md" and second == "" and w.tasks("todo") == ["001-cleanup-2026-10-05.md"], first + "|" + second)
    placed = w.text("tasks/todo/001-cleanup-2026-10-05.md")
    check("the task names the nightly command and the simplifier's rules, needs no owner present and no paid audit, and can start",
          all(s in placed for s in ("`python3 .claude/hooks/simplifier.py nightly`", ".claude/references/simplifier.md", "SIMPLIFIER CALL:", "Simplifier-Finding: <id>", ".engine/simplifier/report.md",
                                    "Потрібна присутність власника: ні", "Аудит потрібен: ні", "раз на добу"))
          and w.board("next").stdout.strip() == "tasks/todo/001-cleanup-2026-10-05.md", placed)
    w.move("001-cleanup-2026-10-05", "todo", "blocked")
    check("while one waits in blocked/ — weeks later too — no second one", w.cleanup("2026-11-20") == "" and w.tasks("todo") == [])
    w.move("001-cleanup-2026-10-05", "blocked", "done")
    check("NEGATIVE: done today — not again today", w.cleanup("2026-10-05") == "" and w.tasks("todo") == [])
    check("the next day: the next one, with the next number", w.cleanup("2026-10-06") == "tasks/todo/002-cleanup-2026-10-06.md")

    check("NEGATIVE: a task that can start is in todo/ — the runner has work, no cleanup", World().task("todo", "010-work").cleanup("2026-10-05") == "")
    check("NEGATIVE: a task is in doing/ — no cleanup", World().task("doing", "010-work").cleanup("2026-10-05") == "")
    waits = World().task("todo", "010-with-owner", more=ATTENDED).task("todo", "020-after", dep="010").task("blocked", "030-asked", ask="1. Що?\n   Відповідь:\n")
    check("all that is left waits for the owner — present, a dependency, an answer: the cleanup is placed after them",
          waits.cleanup("2026-10-05") == "tasks/todo/031-cleanup-2026-10-05.md" and waits.board("next").stdout.strip() == "tasks/todo/031-cleanup-2026-10-05.md")

    check("CLEANUP_EVERY_DAYS=0: never", World(env='CLEANUP_EVERY_DAYS="0"\n').cleanup("2026-10-05") == "")
    rare = World(env='CLEANUP_EVERY_DAYS="3"\n').task("done", "001-cleanup-2026-10-05")
    late = [rare.cleanup("2026-10-07"), rare.cleanup("2026-10-08")]
    check("CLEANUP_EVERY_DAYS=3: not on the second day, on the third", late == ["", "tasks/todo/002-cleanup-2026-10-08.md"] and "раз на 3 діб" in rare.text(late[1]), late)

    print("the number of a task the runner places: after the owner's tasks, under the open items")
    high = World(weekly=True).task("done", "040-old").task("blocked", "705-open-item-x", ask="1. Що?\n   Відповідь:\n").task("blocked", "800-rule-proposal-y", ask="1. Що?\n   Відповідь:\n")
    check("an open item (700+) and a rule question (800+) do not pull the cleanup task's number up", high.cleanup("2026-10-05") == "tasks/todo/041-cleanup-2026-10-05.md")
    weekly = high.board("maintain-task", "--today", "2026-10-05").stdout.strip()
    check("nor the weekly maintenance task's", weekly == "tasks/todo/042-maintain-2026-10-05.md", weekly)

    # --- the runner -----------------------------------------------------------------------------------
    print("the runner: the board is idle -> the cleanup task appears -> it is done")
    w = World().task("todo", "010-work")
    w.commit("the owner's task")
    r = w.runner("2026-10-05")
    name = "011-cleanup-2026-10-05"
    check("the owner's task first, then the cleanup task the runner placed itself; both done, the runner stops idle as before",
          r.returncode == 0 and w.tasks("done") == ["010-work", name] and w.tasks("todo") == [] and "state=idle" in w.status() and "reason=todo-empty" in w.status(), out(r) + str(w.subjects()))
    check("the agent was started for each, with the cleanup task as its task", w.said("calls") == [f"010-work.md | Your task is the file tasks/doing/010-work.md", f"{name}.md | Your task is the file tasks/doing/{name}.md"], w.said("calls"))
    check("the cleanup ran the simplifier's nightly mode, once, and its answer is in the report",
          w.said("nightly") == ["nightly"] and "no sharp growth" in w.text(f"tasks/done/{name}/report.md"), w.said("nightly"))
    journal = w.text("tasks/ANOMALIES.md")
    check("the event is in the anomaly journal: under the task, what happened, what was done, by the runner",
          journal.count(f"— {name}\n") == 1 and "task board вільна" in journal and f"`tasks/todo/{name}.md`" in journal and "Хто записав: runner" in journal, journal)
    check("placed in one commit — the task and its journal entry together — and nothing is left uncommitted",
          sum(PLACED in s for s in w.subjects()) == 1 and w.dirty() == ""
          and sorted(sh(w.repo, "git", "show", "--name-only", "--format=", "HEAD~2").stdout.split()) == ["tasks/ANOMALIES.md", f"tasks/todo/{name}.md"], str(w.subjects()) + w.dirty())
    check("origin has it all", sh(w.repo, "git", "rev-parse", "HEAD").stdout == sh(w.repo, "git", "rev-parse", "origin/unattended/work").stdout)
    doc = w.board("review", "--offline", "--state-dir", str(w.repo / ".claude/state"))
    odd = doc.stdout.split("\n## Аномалії")[1].split("\n## ")[0] if "\n## Аномалії" in doc.stdout else ""
    check("the review shows it in «Аномалії»", name in odd and "task board вільна" in odd, out(doc)[:900])

    check("board 723: NEGATIVE — with a journal that can be written, no anomaly-failed event", "anomaly-failed" not in w.text(".claude/state/board/events.log"),
          w.text(".claude/state/board/events.log"))
    r = w.runner("2026-10-05")
    check("NEGATIVE: the same day's next run places nothing and starts no agent", r.returncode == 0 and len(w.said("calls")) == 2 and sum(PLACED in s for s in w.subjects()) == 1 and "state=idle" in w.status(), out(r))
    r = w.runner("2026-10-06")
    check("the next day: once more, and once", w.tasks("done") == ["010-work", name, "012-cleanup-2026-10-06"] and len(w.said("calls")) == 3 and w.said("nightly") == ["nightly"] * 2, out(r) + str(w.subjects()))

    w = World().task("todo", "010-work")
    (w.repo / "tasks/ANOMALIES.md").mkdir()   # board 723: the journal cannot be written — a directory stands where the file goes
    w.commit("the owner's task")
    r = w.runner("2026-10-05")
    name = "011-cleanup-2026-10-05"
    log = w.text(".claude/state/board/events.log")
    check("board 723: NEGATIVE — the journal cannot be written: events.log says so for the cleanup task it placed",
          f"anomaly-failed cleanup-task tasks/todo/{name}.md" in log, log)
    check("…the cleanup task is placed and committed all the same, and done; the board did not stop",
          r.returncode == 0 and w.tasks("done") == ["010-work", name] and sum(PLACED in s for s in w.subjects()) == 1
          and w.said("nightly") == ["nightly"] and "state=idle" in w.status() and "reason=todo-empty" in w.status(), out(r) + log)
    check("…and it says nothing else: the journal stands where it stood, nothing is left uncommitted",
          (w.repo / "tasks/ANOMALIES.md").is_dir() and w.dirty() == "", w.dirty())

    w = World().task("blocked", "030-asked", ask="1. Що?\n   Відповідь:\n")
    w.commit("a question waits")
    r = w.runner("2026-10-05")
    check("a board that waits for the owner is cleaned too, and still ends waiting-owner",
          r.returncode == 0 and w.tasks("done") == ["031-cleanup-2026-10-05"] and w.tasks("blocked") == ["030-asked.md"] and "state=waiting-owner" in w.status(), out(r))

    # `board.py next` answers 4 here, not 3: todo/ holds tasks, and none of them can start.
    w = World().task("todo", "010-with-owner", more=ATTENDED).task("todo", "020-after", dep="010")
    w.commit("tasks that wait for the owner's presence")
    r = w.runner("2026-10-05")
    check("todo/ holds only tasks that wait for the owner's presence: cleaned too, they stay where they were, the run ends waiting-owner",
          r.returncode == 0 and w.tasks("done") == ["021-cleanup-2026-10-05"] and w.tasks("todo") == ["010-with-owner.md", "020-after.md"]
          and w.said("nightly") == ["nightly"] and "state=waiting-owner" in w.status(), out(r))

    w = World(env='CLEANUP_EVERY_DAYS="0"\n')
    r = w.runner("2026-10-05")
    check("NEGATIVE: switched off — the runner stops idle at once, no task, no agent, no journal", r.returncode == 0 and w.tasks("done") == [] and w.said("calls") == [] and w.text("tasks/ANOMALIES.md") == "" and "state=idle" in w.status(), out(r))

    w = World(weekly=True)
    r = w.runner("2026-10-05")
    check("with the weekly task due as well: that one first (it is work to take), then the cleanup, each once",
          r.returncode == 0 and w.tasks("done") == ["001-maintain-2026-10-05", "002-cleanup-2026-10-05"] and w.said("nightly") == ["nightly"], out(r))

    w = World().task("todo", "010-work")
    w.commit("the owner's task")
    r = w.runner("2026-10-05", "--once")
    check("NEGATIVE: --once ends after the owner's task; no cleanup is placed behind it", r.returncode == 0 and w.tasks("done") == ["010-work"] and w.tasks("todo") == [] and "reason=once" in w.status(), out(r))

    # --- the prose ------------------------------------------------------------------------------------
    print("the manuals and the settings")
    for manual in ("tasks/README.md", "templates/project/tasks/README.md", ".claude/unattended/README.md", ".claude/references/simplifier.md"):
        words = " ".join((ROOT / manual).read_text(encoding="utf-8").split())
        check(f"{manual} names the cleanup task and its setting", "cleanup-task" in words and "CLEANUP_EVERY_DAYS" in words, manual)
    for env_file in (".claude/project.env", "templates/project/.claude/project.env"):
        check(f"{env_file} documents CLEANUP_EVERY_DAYS, empty by default", '\nCLEANUP_EVERY_DAYS=""\n' in (ROOT / env_file).read_text(encoding="utf-8"), env_file)
    check("board.py lists the command", "board.py cleanup-task" in BOARD.read_text(encoding="utf-8").split('"""')[1])
finally:
    for d in worlds:
        shutil.rmtree(d, ignore_errors=True)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
