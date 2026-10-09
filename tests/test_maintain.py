#!/usr/bin/env python3
"""/maintain — regular care (board 076): the report, the owner's «так» on the list, the weekly task.

WHY. Changing packages is the owner's act: the agent reports and asks, the board runner updates —
only what the owner saw, only patches and minor versions, one at a time, each checked by the full
gate and committed or rolled back. A major version never rides along. And the care comes back by
itself once a week, once.

Deterministic: every scene runs the real maintain.py, board.py, owner_action.py and
board-runner.sh on a synthetic repository (branch unattended/work, a bare origin, a fake
`claude`). NO PACKAGE IS TOUCHED: the project's `DEPS_UPDATE_CMD` is a stub that records its
arguments and rewrites a pin in `requirements.txt`; the project's test goes red on one pin.
The refusals come first: the action is shown NOT to run before it is shown to run.

SCENES
  - the class of an update is computed from the two versions; a major (and a 0.x minor, and a
    version that is not numbers) never enters updates.json, and becomes a task proposal;
  - with no DEPS_OUTDATED_CMD the step is not there: no list, no question;
  - the report's other parts by their VALUES, not their headings: the hot file is the one that
    both changes often and is complex (not the busy simple one, not the quiet complex one); the
    snapshot's counts and what went since the previous report; the open and the overdue debt;
    the lesson queue, the waiting rule proposals (the PROPOSED ones only) and whether memory is due
    a clean-up (board 743: each by its value, with its negative case); a task proposal for each;
  - an answer that is not «так» — the command is not called; inside a session — refused;
  - the list changed after the question — not called;
  - «так» — the command is called with exactly the list the owner saw: the patches as one group,
    each minor alone, a commit for each;
  - an update that broke the tests is rolled back and written down with the output; the rest stays;
  - a major version put into the list by hand is skipped even under «так»;
  - checks red before any update, a dirty tree, no command — nothing is touched;
  - a week later the maintenance task appears on the board once, not twice.
The command is prose a model follows; what is free to check is its structure.

Run:   python3 tests/test_maintain.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
MAINTAIN = HOOKS / "maintain.py"
BOARD = ROOT / ".claude/unattended/board.py"
ACTION = ROOT / ".claude/unattended/owner_action.py"
RUNNER = ROOT / ".claude/unattended/board-runner.sh"
RUNNER_LIMIT_S = 120
PASS = FAIL = 0
# The simplifier's outside tools (vulture, pylint through uvx) are not what is tested here.
PATH = os.pathsep.join(d for d in os.environ.get("PATH", "").split(os.pathsep) if d and not any((Path(d) / t).exists() for t in ("uvx", "vulture", "pylint")))

sys.path.insert(0, str(HOOKS))
spec = importlib.util.spec_from_file_location("maintain", MAINTAIN)
assert spec is not None and spec.loader is not None
maintain = importlib.util.module_from_spec(spec)
sys.modules["maintain"] = maintain
spec.loader.exec_module(maintain)


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=False)


def out(r: subprocess.CompletedProcess[str]) -> str:
    return f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"


# What the project's stub commands see. `left-pad` is the patch that breaks the test.
OUTDATED = """Package    Version  Latest   Type
---------- -------- -------- -----
requests   2.31.0   2.31.4   wheel
left-pad   1.0.0    1.0.1    wheel
attrs      23.1.0   23.2.0   wheel
django     4.2.1    5.0.0    wheel
tinylib    0.3.1    0.4.0    wheel
nightly    1.0.0rc1 1.0.0rc2 wheel
"""
PINS = "requests==2.31.0\nleft-pad==1.0.0\nattrs==23.1.0\ndjango==4.2.1\n"
# The stub: records its arguments, one call a line, and rewrites the pins it was given.
UPDATE_STUB = """import json, os, sys
from pathlib import Path
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
pins = dict(line.split("==") for line in Path("requirements.txt").read_text().split())
for arg in sys.argv[1:]:
    name, version = arg.split("==")
    pins[name] = version
Path("requirements.txt").write_text("".join(f"{n}=={v}\\n" for n, v in pins.items()))
Path("installed.lock").write_text("the update command left a new file\\n")
"""
PROJECT_TEST = 'import sys\nfrom pathlib import Path\nbad = "left-pad==1.0.1" in Path("requirements.txt").read_text()\nprint("FAILED test_pad: left-pad 1.0.1 pads on the right" if bad else "1 passed")\nsys.exit(1 if bad else 0)\n'
ENV = ('SOURCE_DIRS="app"\nCODE_EXTENSIONS="py"\nTEST_CMD="python3 tests/check.py"\nDEPS_OUTDATED_CMD="cat outdated.txt"\n'
       'DEPS_AUDIT_CMD="echo no known vulnerabilities"\nDEPS_UPDATE_CMD="python3 tools/update.py"\nDEPS_RESTORE_CMD="touch restored.flag"\n')
FAKE = r'''#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
with open(os.environ["FAKE_HOME"] + "/calls", "a") as f:
    f.write("call\n")
doing = sorted(Path("tasks/doing").glob("[0-9]*.md"))
if doing:
    target = Path("tasks/done") / doing[0].stem
    target.mkdir(parents=True)
    doing[0].rename(target / "task.md")
    (target / "report.md").write_text("# report\n")
    subprocess.run(["git", "add", "-A", "tasks"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"{doing[0].stem}: done", "--", "tasks"], check=True)
print('{"type":"result","subtype":"success","is_error":false,"result":"ok","session_id":"s1","total_cost_usd":0.1}')
'''
worlds: list[Path] = []


class World:
    """A project on unattended/work with a bare origin, the stub commands and the fake claude."""

    def __init__(self, env: str = ENV, command: bool = False) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="maintain-"))
        worlds.append(self.dir)
        self.repo, self.origin, self.home = self.dir / "repo", self.dir / "origin.git", self.dir / "fake"
        self.repo.mkdir()
        self.home.mkdir()
        self.log = self.dir / "update-calls.jsonl"
        files = {"app/calc.py": "def add(a, b):\n    return a + b\n", "tests/check.py": PROJECT_TEST, "tools/update.py": UPDATE_STUB,
                 "outdated.txt": OUTDATED, "requirements.txt": PINS, ".claude/project.env": env,
                 ".gitignore": ".claude/state/\nrestored.flag\n", **{f"tasks/{c}/.gitkeep": "" for c in ("todo", "doing", "blocked", "done")}}
        if command:
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
        return {**full, "PATH": PATH, "CLAUDE_PROJECT_DIR": str(self.repo), "STUB_LOG": str(self.log), "FAKE_HOME": str(self.home),
                "BOARD_CLAUDE": str(self.home / "claude"), "BOARD_INBOX": str(self.dir / "inbox"), "BOARD_PAUSE_SEC": "0", **more}

    def py(self, script: Path, *args: str, **more: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(script), *args], cwd=self.repo, capture_output=True, text=True, check=False, env=self.env(**more))

    def board(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.py(BOARD, "--root", str(self.repo), *args)

    def action(self, sha: str, **more: str) -> subprocess.CompletedProcess[str]:
        return self.py(ACTION, "--root", str(self.repo), "update-deps", sha, **more)

    def runner(self, *args: str, **more: str) -> subprocess.CompletedProcess[str]:
        # The limit turns a runner that never stops (a broken weekly guard places a task on every pass) into a red check.
        try:
            return subprocess.run(["bash", str(RUNNER), *args], cwd=self.dir, capture_output=True, text=True, check=False, env=self.env(**more), timeout=RUNNER_LIMIT_S)
        except subprocess.TimeoutExpired:
            (self.repo / ".claude/state/board/stop-after-task").touch()   # whatever is left of it stops at its next pass
            return subprocess.CompletedProcess(["board-runner"], 124, "", f"the runner did not stop in {RUNNER_LIMIT_S} s")

    def commit(self, message: str) -> None:
        sh(self.repo, "git", "add", "-A")
        done = sh(self.repo, "git", "commit", "-q", "-m", message)
        assert done.returncode == 0, done.stderr
        sh(self.repo, "git", "push", "-q", "origin", "unattended/work")

    def text(self, rel: str) -> str:
        path = self.repo / rel
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def subjects(self) -> list[str]:
        return sh(self.repo, "git", "log", "--format=%s").stdout.splitlines()

    def sha(self) -> str:
        return hashlib.sha256((self.repo / maintain.UPDATES_REL).read_bytes()).hexdigest()

    def tasks(self, column: str) -> list[str]:
        return sorted(p.name for p in (self.repo / "tasks" / column).glob("[0-9]*"))

    def dirty(self) -> str:
        return sh(self.repo, "git", "status", "--porcelain", "--untracked-files=all").stdout.strip()

    def reported(self, date: str = "2026-10-04") -> "World":
        """The agent's half is done: the report and the list are written and committed."""
        r = self.py(MAINTAIN, "report", "--date", date)
        assert r.returncode == 0, out(r)
        self.commit("maintain: the report")
        return self

    def asked(self, answer: str = "") -> str:
        """The task waits in blocked/ with the question maintain.py printed; `answer` is the owner's, pushed from elsewhere."""
        question = self.py(MAINTAIN, "question")
        assert question.returncode == 0, out(question)
        name = "020-maintain-2026-10-04.md"
        body = "# 020 — Догляд\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Що зробити\n- /maintain\n\n## Питання до власника\n1. " + question.stdout
        (self.repo / "tasks/blocked" / name).write_text(body, encoding="utf-8")
        self.commit("020: the question")
        if answer:   # the owner answers in another clone and pushes: the answer ARRIVES by the pull
            clone = self.dir / "owner"
            sh(self.dir, "git", "clone", "-q", "-b", "unattended/work", str(self.origin), str(clone))
            path = clone / "tasks/blocked" / name
            path.write_text(path.read_text(encoding="utf-8").replace("   Відповідь:", f"   Відповідь: {answer}"), encoding="utf-8")
            sh(clone, "git", "-c", "user.name=o", "-c", "user.email=o@example.invalid", "commit", "-q", "-am", "owner: the answer")
            sh(clone, "git", "push", "-q", "origin", "unattended/work")
        return question.stdout


try:
    # --- the class of an update ---------------------------------------------------------------------
    print("the class of an update is computed, never taken on trust")
    kinds = {(a, b): maintain.kind_of(a, b) for a, b in (("1.2.3", "1.2.9"), ("1.2.3", "1.4.0"), ("1.2.3", "2.0.0"), ("0.3.1", "0.4.0"),
                                                         ("0.3.1", "0.3.2"), ("2024a", "2024b"), ("1.2.3", "1.2.3"), ("1.5.0", "1.4.9"), ("v1.2", "v1.3"))}
    check("patch, minor, major; a 0.x minor is a major; not numbers is unknown; not newer is nothing",
          list(kinds.values()) == ["patch", "minor", "major", "major", "patch", "unknown", "", "", "minor"], kinds)
    as_json = maintain.parse_outdated(json.dumps([{"name": "a", "version": "1.0.0", "latest_version": "1.0.1"}, {"name": "b", "version": "1.0.0", "latest_version": "3.0.0"}]))
    as_npm = maintain.parse_outdated(json.dumps({"c": {"current": "2.1.0", "wanted": "2.1.0", "latest": "2.2.0"}}))
    check("pip's JSON list and npm's JSON object are read like the text table",
          [(d["name"], d["kind"]) for d in as_json + as_npm] == [("a", "patch"), ("b", "major"), ("c", "minor")], as_json + as_npm)

    # --- the report -----------------------------------------------------------------------------------
    print("the report: read-only, and a major version never enters the list")
    w = World().reported()
    report = w.text(".engine/maintain/2026-10-04.md")
    listed = json.loads(w.text(".engine/maintain/updates.json"))["updates"]
    check("updates.json holds the patches and the minor version, in one order",
          [(d["name"], d["kind"]) for d in listed] == [("left-pad", "patch"), ("requests", "patch"), ("attrs", "minor")], listed)
    check("NEGATIVE: the major version, the 0.x minor and the unreadable version are not in the list",
          not {"django", "tinylib", "nightly"} & {d["name"] for d in listed}, listed)
    check("…each of them is a task proposal in the report instead", all(f"Оновити `{name}`" in report for name in ("django", "tinylib", "nightly"))
          and "окрема задача" in report, report)
    check("the report has every section the design names",
          all(f"## {h}" in report for h in ("Залежності", "Складність проти минулого звіту", "Гарячі місця", "Знімок «як було»",
                                           "Борги термінових виправлень", "Черга уроків", "Пропозиції задач", "Питання до власника")), report)
    check("…with the audit command's output and the first-report note", "no known vulnerabilities" in report and "перший звіт" in report, report)
    check("the report run called no update and changed no pin", w.calls() == [] and w.text("requirements.txt") == PINS, w.calls())
    (w.repo / "app/more.py").write_text("def twice(a):\n    return a * 2\n")
    w.commit("more code")
    again = w.reported("2026-10-11").text(".engine/maintain/2026-10-11.md")
    check("the next report compares with the previous one", "минулим звітом від 2026-10-04" in again and "файлів робочого коду: 2 (було 1, +1)" in again, again)

    question = w.asked()
    check("the question names the count, lists what the owner approves, and offers the sha256 of the list",
          "Оновити ці 3 залежностей?" in question and all(f"`{n}`" in question for n in ("left-pad", "requests", "attrs"))
          and f"Дія runner-а: update-deps {w.sha()}" in question and question.rstrip().endswith("Відповідь:") and "django" not in question, question)

    bare = World(env='SOURCE_DIRS="app"\nTEST_CMD="python3 tests/check.py"\n').reported()
    none = bare.py(MAINTAIN, "question")
    check("no DEPS_OUTDATED_CMD: the step is not there — the report says so, no list, no question (exit 3)",
          "Кроку немає" in bare.text(".engine/maintain/2026-10-04.md") and not (bare.repo / maintain.UPDATES_REL).exists()
          and none.returncode == 3 and not none.stdout.strip(), out(none))
    check("…and the board offers no action without the list", bare.board("action-line", "update-deps").returncode == 2)

    # --- the report's other parts, by value -----------------------------------------------------------
    print("the report's other parts: values, not headings")
    branchy = "def tangled(a):\n    n = 0\n" + "".join(f"    if a == {i}:\n        n += {i}\n" for i in range(12)) + "    return n\n"
    w = World()
    for rel, body in (("app/hot.py", branchy), ("app/quiet.py", branchy.replace("tangled", "knotted")), ("app/busy.py", "def one():\n    return 1\n"),
                      (".engine/baseline.json", json.dumps({"schema": 1, "tests": ["tests/t.py::a", "tests/t.py::b"], "lint": {"app/hot.py": {"E501": 3}}, "types": {"app/hot.py": {"arg-type": 1}}})),
                      (".engine/debt.md", "# Debts of urgent fixes\n\n"
                       "- 001-login | open | recorded 2026-09-24 | due 2026-10-01 | commit abc1234 | deferred: the test | follow-up: tasks/todo/011-followup.md\n"
                       "- 002-cart | open | recorded 2026-10-02 | due 2026-10-09 | commit def5678 | deferred: the test | follow-up: tasks/todo/012-followup.md\n"
                       "- 003-old | closed 2026-09-20 by 004 | recorded 2026-09-10 | due 2026-09-17 | commit 0a0a0a0 | deferred: the test | follow-up: tasks/done/009\n"),
                      (".engine/lesson-queue.md", "# queue\n- 2026-09-28 | gate | s1 | the first lesson #0000aaaa\n- 2026-10-01 | agent | s1 | the second lesson #0000bbbb\n"),
                      (".engine/rule-proposals.md", "# Rule proposals\n\n## RP-0000cccc — 2026-10-02 — PROPOSED\n- Rule: чекає\n\n"
                       "## RP-0000ffff — 2026-10-03 — PROPOSED\n- Rule: теж чекає\n\n"
                       # the states lesson_queue.py closes a proposal with: APPROVED (promote) and REJECTED (reject)
                       "## RP-0000dddd — 2026-09-20 — APPROVED\n- Rule: уже правило\n\n## RP-0000eeee — 2026-09-21 — REJECTED\n- Rule: відхилено\n")):
        (w.repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (w.repo / rel).write_text(body, encoding="utf-8")
    w.commit("the project has a history")
    for i in range(3):   # two files change often; only one of them is complex
        for rel in ("app/hot.py", "app/busy.py"):
            (w.repo / rel).write_text((w.repo / rel).read_text() + f"# change {i}\n")
        w.commit(f"change {i}")
    rich = w.reported().text(".engine/maintain/2026-10-04.md")

    def part(doc: str, heading: str) -> str:
        return doc.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]

    hot, tasks_part = part(rich, "Гарячі місця"), part(rich, "Пропозиції задач")
    check("hot places: the file that changes often AND holds a function over the limit, with both numbers",
          "- `app/hot.py`: змін 4, найскладніша функція 13" in hot, hot)
    check("NEGATIVE: the busy simple file and the quiet complex file are not hot", "busy.py" not in hot and "quiet.py" not in hot and "- немає" not in hot, hot)
    check("…and it is a task proposal", "Спростити `app/hot.py`: змінювався 4 разів за 90 днів, найскладніша функція — 13." in tasks_part, tasks_part)
    snap = part(rich, "Знімок «як було»")
    check("the snapshot: what is left, by kind", all(line in snap for line in ("- старих падінь тестів: 2", "- зауважень лінтера: 3", "- зауважень типів: 1"))
          and "прибрано" not in snap, snap)
    check("…and the old failures are a task proposal", "Полагодити старі падіння тестів зі знімка «як було» (2)" in tasks_part, tasks_part)
    debt = part(rich, "Борги термінових виправлень")
    check("the debts: two open of three, one overdue and marked, the closed one not shown",
          "Відкрито: 2 з 3; прострочено: 1." in debt and "- ПРОСТРОЧЕНО — `001-login`: строк 2026-10-01, commit abc1234" in debt
          and "- `002-cart`: строк 2026-10-09" in debt and "003-old" not in debt, debt)
    check("…the overdue one is a task proposal, the one in time is not",
          "Закрити прострочений борг термінового виправлення `001-login` (строк 2026-10-01): tasks/todo/011-followup.md." in tasks_part and "002-cart" not in tasks_part, tasks_part)
    queue = part(rich, "Черга уроків")
    check("the lesson queue: how many and since when", "- кандидатів у черзі: 2, найстаріший від 2026-09-28" in queue, queue)
    check("board 743: the rule proposals that wait for the owner — the two PROPOSED; NEGATIVE: the approved (promoted) and the rejected are not counted",
          "- пропозицій правил, що чекають вашої відповіді: 2" in queue, queue)
    check("board 743: NEGATIVE — two candidates and a clean-up clock that has just started: memory is not due, and no task is proposed for it",
          "- прибирання пам'яті: ще не час" in queue and "Прибрати пам'ять" not in tasks_part, queue + tasks_part)
    (w.repo / ".engine/baseline.json").write_text(json.dumps({"schema": 1, "tests": ["tests/t.py::a"], "lint": {"app/hot.py": {"E501": 1}}, "types": {}}))
    (w.repo / ".engine/debt.md").write_text(w.text(".engine/debt.md").replace("- 001-login | open |", "- 001-login | closed 2026-10-08 by 013 |"))
    w.commit("a week of repairs")
    later = w.reported("2026-10-11")
    snap, debt, tasks_part = (part(later.text(".engine/maintain/2026-10-11.md"), h) for h in ("Знімок «як було»", "Борги термінових виправлень", "Пропозиції задач"))
    check("a week later the snapshot says what went: each count against the previous report, and the sum removed",
          all(line in snap for line in ("- старих падінь тестів: 1 (було 2, -1)", "- зауважень лінтера: 1 (було 3, -2)", "- зауважень типів: 0 (було 1, -1)",
                                        "- прибрано з минулого звіту: 4")), snap)
    check("…and the debt that was closed is gone while the other, now past its term, is overdue",
          "Відкрито: 1 з 3; прострочено: 1." in debt and "001-login" not in debt + tasks_part and "ПРОСТРОЧЕНО — `002-cart`" in debt and "`002-cart`" in tasks_part, debt + tasks_part)
    crowded = World()
    (crowded.repo / ".engine").mkdir(exist_ok=True)
    (crowded.repo / ".engine/lesson-queue.md").write_text("# queue\n" + "".join(f"- 2026-09-{10 + i:02d} | gate | s1 | lesson {i} #{i:08x}\n" for i in range(31)),
                                                           encoding="utf-8")
    crowded.commit("a long queue")
    report = crowded.reported().text(".engine/maintain/2026-10-04.md")
    queue, tasks_part = part(report, "Черга уроків"), part(report, "Пропозиції задач")
    check("board 743: 31 candidates — memory is due, and the reason is said; no rule proposal waits (no file): 0",
          "- прибирання пам'яті: час — 31 candidates in the queue (over 30)" in queue and "- пропозицій правил, що чекають вашої відповіді: 0" in queue, queue)
    check("…and the clean-up is a task proposal, with the same reason", "Прибрати пам'ять і розібрати чергу уроків (31 candidates in the queue (over 30))." in tasks_part, tasks_part)
    empty = part(World().reported().text(".engine/maintain/2026-10-04.md"), "Гарячі місця")
    check("a project with none of this says so instead of inventing it", "- немає" in empty, empty)

    # --- the refusals, before the action is shown to run --------------------------------------------
    print("not «так»: the command is not called")
    w = World().reported()
    w.asked("так, але без attrs")
    r = w.runner()
    check("«так, але…» is an instruction: no update, no pin changed, the task goes back to the agent",
          w.calls() == [] and w.text("requirements.txt") == PINS and not any(s.startswith("deps:") for s in w.subjects())
          and w.tasks("done") == ["020-maintain-2026-10-04"], out(r) + str(w.subjects()))

    w = World().reported()
    w.asked()
    r = w.runner()
    check("no answer: nothing is updated and the runner waits for the owner", w.calls() == [] and "state=waiting-owner" in w.text(".claude/state/board/status"), out(r))
    sha = w.sha()
    r = w.action(sha, CLAUDECODE="1")
    check("inside a Claude Code session the action is refused (exit 2): an agent cannot take it", r.returncode == 2 and w.calls() == [], out(r))

    print("the list changed after the question: not the one the owner saw")
    w = World().reported()
    w.asked("так")
    (w.repo / "outdated.txt").write_text(OUTDATED + "newcomer   1.0.0    1.0.1    wheel\n")
    w.commit("the world moved on")
    w.reported("2026-10-05")
    r = w.runner()
    check("stale: the command is not called, the task returns to the agent with the reason",
          w.calls() == [] and w.text("requirements.txt") == PINS and "action-stale update-deps" in w.text(".claude/state/board/events.log")
          and "інший sha256" in w.text("tasks/done/020-maintain-2026-10-04/task.md"), out(r) + w.text(".claude/state/board/events.log"))

    # --- «так» ----------------------------------------------------------------------------------------
    print("«так»: the runner updates exactly the list the owner saw")
    w = World().reported()
    question = w.asked("так")
    r = w.runner()
    result = w.text(".engine/maintain/update-result.md")
    check("the command got the patches as one group, then — the group having broken the test — each patch alone, then the minor alone",
          w.calls() == [["left-pad==1.0.1", "requests==2.31.4"], ["left-pad==1.0.1"], ["requests==2.31.4"], ["attrs==23.2.0"]], w.calls())
    asked_for = {f"{d['name']}=={d['latest']}" for d in json.loads(w.text(".engine/maintain/updates.json"))["updates"]}
    check("…and nothing outside the list the owner saw", {a for call in w.calls() for a in call} == asked_for and all(a.split("==")[0] in question for a in asked_for), w.calls())
    check("the update that broke the test is rolled back: its pin is the old one, the file the command created is gone",
          "left-pad==1.0.0" in w.text("requirements.txt") and not w.dirty() and (w.repo / "restored.flag").exists(), w.text("requirements.txt") + w.dirty())
    check("…and written down with the output that shows why", "СКАСОВАНО" in result and "left-pad 1.0.1 pads on the right" in result, result)
    check("the others are updated, each in a commit of its own",
          "requests==2.31.4" in w.text("requirements.txt") and "attrs==23.2.0" in w.text("requirements.txt")
          and [s.split(" — ")[0] for s in w.subjects() if s.startswith("deps:")] == ["deps: attrs 23.1.0 → 23.2.0", "deps: requests 2.31.0 → 2.31.4"], w.subjects())
    check("the result says two of three; the offer is replaced by the outcome and the agent closes the task",
          "Оновлено 2 з 3" in result and "action-applied update-deps" in w.text(".claude/state/board/events.log")
          and "Дію виконано" in w.text("tasks/done/020-maintain-2026-10-04/task.md") and "Дія runner-а:" not in w.text("tasks/done/020-maintain-2026-10-04/task.md"), out(r))
    check("everything is pushed and the tree is clean", not w.dirty() and sh(w.repo, "git", "rev-parse", "HEAD").stdout == sh(w.origin, "git", "rev-parse", "unattended/work").stdout, w.dirty())
    before = len(w.calls())
    r = w.runner()
    check("the same answer never runs the action twice", len(w.calls()) == before, w.calls())

    print("a major version put into the list by hand does not ride along")
    w = World().reported()
    forged = json.loads(w.text(".engine/maintain/updates.json"))
    forged["updates"] = [{"name": "django", "current": "4.2.1", "latest": "5.0.0", "kind": "patch"}, {"name": "requests", "current": "2.31.0", "latest": "2.31.4", "kind": "patch"}]
    (w.repo / maintain.UPDATES_REL).write_text(json.dumps(forged))
    w.commit("a list edited by hand")
    r = w.action(w.sha())
    check("NEGATIVE: the command never sees it, whatever class the file claims; the report says why",
          r.returncode == 0 and w.calls() == [["requests==2.31.4"]] and "django==4.2.1" in w.text("requirements.txt")
          and "НЕ ОНОВЛЮВАЛОСЬ" in w.text(".engine/maintain/update-result.md"), out(r) + str(w.calls()))

    print("nothing is touched when an update could not be checked or undone")
    w = World().reported()
    (w.repo / "requirements.txt").write_text(PINS.replace("left-pad==1.0.0", "left-pad==1.0.1"))
    w.commit("red before")
    r = w.action(w.sha())
    check("checks red before any update: exit 1, the command is not called", r.returncode == 1 and w.calls() == []
          and "ще до оновлень" in w.text(".engine/maintain/update-result.md"), out(r))
    w = World().reported()
    (w.repo / "half.txt").write_text("somebody's work\n")
    r = w.action(w.sha())
    check("a dirty tree: exit 1, the command is not called, the stranger's file is left alone", r.returncode == 1 and w.calls() == [] and (w.repo / "half.txt").exists(), out(r))
    w = World(env=ENV.replace('DEPS_UPDATE_CMD="python3 tools/update.py"', 'DEPS_UPDATE_CMD=""')).reported()
    r = w.action(w.sha())
    check("no DEPS_UPDATE_CMD: exit 1, nothing is guessed", r.returncode == 1 and w.calls() == [] and "DEPS_UPDATE_CMD" in w.text(".engine/maintain/update-result.md"), out(r))
    w = World(env=ENV.replace('TEST_CMD="python3 tests/check.py"\n', 'LINT_CMD="true"\n')).reported()
    r = w.action(w.sha())
    check("a project whose gate runs no tests: exit 1 — an update nothing can check is not made", r.returncode == 1 and w.calls() == [], out(r))
    w = World().reported()
    sh(w.repo, "git", "switch", "-q", "-c", "feature/x")
    r = w.action(w.sha())
    check("not on an unattended/* branch: refused (exit 2), no commit is made from a script elsewhere", r.returncode == 2 and w.calls() == [], out(r))
    r = w.action("0" * 64)
    check("another sha256: stale (exit 3)", r.returncode == 3 and w.calls() == [], out(r))

    # --- the weekly task ------------------------------------------------------------------------------
    print("once a week the maintenance task appears on the board — once")
    w = World()
    check("NEGATIVE: a project without the /maintain command gets no task", w.board("maintain-task", "--today", "2026-10-04").stdout == "" and w.tasks("todo") == [])
    w = World(command=True)
    first = w.board("maintain-task", "--today", "2026-10-04")
    second = w.board("maintain-task", "--today", "2026-10-04")
    check("the first call places it, the second does not: one task in todo/",
          first.stdout.strip() == "tasks/todo/001-maintain-2026-10-04.md" and second.stdout == "" and w.tasks("todo") == ["001-maintain-2026-10-04.md"], out(first) + out(second))
    placed = w.text("tasks/todo/001-maintain-2026-10-04.md")
    check("the task asks for /maintain, needs no owner present and no paid audit, and the board reads it as eligible",
          "`/maintain`" in placed and "Потрібна присутність власника: ні" in placed and "Аудит потрібен: ні" in placed
          and w.board("next").stdout.strip() == "tasks/todo/001-maintain-2026-10-04.md", placed)
    (w.repo / "tasks/todo/001-maintain-2026-10-04.md").rename(w.repo / "tasks/blocked/001-maintain-2026-10-04.md")
    check("while it waits in blocked/ — weeks later too — no second one", w.board("maintain-task", "--today", "2026-11-20").stdout == "" and w.tasks("todo") == [])
    (w.repo / "tasks/done/001-maintain-2026-10-04").mkdir()
    (w.repo / "tasks/blocked/001-maintain-2026-10-04.md").rename(w.repo / "tasks/done/001-maintain-2026-10-04/task.md")
    check("done six days ago: not yet", w.board("maintain-task", "--today", "2026-10-10").stdout == "" and w.tasks("todo") == [])
    week = w.board("maintain-task", "--today", "2026-10-11")
    check("done seven days ago: the next one, with the next number", week.stdout.strip() == "tasks/todo/002-maintain-2026-10-11.md", out(week))
    off = World(env=ENV + 'MAINTAIN_EVERY_DAYS="0"\n', command=True)
    check("MAINTAIN_EVERY_DAYS=0: never", off.board("maintain-task", "--today", "2026-10-04").stdout == "" and off.tasks("todo") == [])

    w = World(command=True)
    r = w.runner(BOARD_TODAY="2026-10-04")
    r2 = w.runner(BOARD_TODAY="2026-10-05")
    check("the runner places it itself, in one commit, an agent does it, and the next day's run places nothing",
          w.tasks("done") == ["001-maintain-2026-10-04"] and w.tasks("todo") == [] and sum("the weekly maintenance task" in s for s in w.subjects()) == 1
          and len(w.text("../fake/calls").splitlines()) == 1, out(r) + out(r2) + str(w.subjects()))
    r3 = w.runner(BOARD_TODAY="2026-10-11")
    check("a week later: once more, and once", w.tasks("done") == ["001-maintain-2026-10-04", "002-maintain-2026-10-11"]
          and sum("the weekly maintenance task" in s for s in w.subjects()) == 2, out(r3) + str(w.subjects()))

    # --- the prose ------------------------------------------------------------------------------------
    print("the command, the manuals, the lists")
    command = " ".join((ROOT / ".claude/commands/maintain.md").read_text(encoding="utf-8").split())
    check("the command: the report script, the question script, never the update itself, a major is a separate task, nothing removed",
          all(s in command for s in ("maintain.py report", "maintain.py question", "never run `owner_action.py` yourself", "A major or an unknown version never enters the list",
                                     "does not delete code", "DEPS_OUTDATED_CMD", "update-result.md")), command)
    for manual in ("tasks/README.md", "templates/project/tasks/README.md", ".claude/unattended/README.md"):
        words = " ".join((ROOT / manual).read_text(encoding="utf-8").split())
        check(f"{manual} names the action update-deps and the weekly task", "update-deps" in words and "maintain-task" in words, manual)
    for env_file in (".claude/project.env", "templates/project/.claude/project.env"):
        keys = (ROOT / env_file).read_text(encoding="utf-8")
        check(f"{env_file} documents the settings, all empty by default",
              all(f'\n{k}=""\n' in keys for k in ("DEPS_OUTDATED_CMD", "DEPS_AUDIT_CMD", "DEPS_UPDATE_CMD", "DEPS_UPDATE_SPEC", "DEPS_RESTORE_CMD", "MAINTAIN_EVERY_DAYS")), env_file)
    board_text = BOARD.read_text(encoding="utf-8")
    check("update-deps is on the short list of what the runner may do on the owner's word, in both scripts",
          '"update-deps": update_deps' in ACTION.read_text(encoding="utf-8") and '"update-deps"' in board_text.split("OWNER_ACTIONS = ")[1].split("\n")[0])
finally:
    for d in worlds:
        shutil.rmtree(d, ignore_errors=True)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
