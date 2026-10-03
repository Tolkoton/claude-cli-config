#!/usr/bin/env python3
"""The task board in files and its one reader, .claude/unattended/board.py (package board, B1).

WHAT IS CHECKED
  - a task file is parsed the way the owner writes one: the seventeen real tasks the owner sent
    (tests/fixtures/board-inbox/, byte copies) give the expected numbers, dependencies, audit
    flags and question counts;
  - the questions section is the text under the heading, not a sentence that mentions it, and
    an HTML comment in it (the template's hint) is not a question;
  - `next` takes the lowest number whose dependencies are all in done/, prints a task that is
    already in doing/ instead, and tells "todo is empty" (3) from "nothing is eligible" (4);
  - `start` moves one task to doing/ and refuses a second one;
  - `import-inbox` moves, replaces in todo/, never touches doing/ and done/, and lets an
    ANSWERED copy replace a blocked task (and only an answered one);
  - `unblock` returns a blocked task to todo/ only when every `Відповідь:` is filled;
  - `audit-allowed` says yes only for exactly one task in doing/ that asks for the audit;
  - the board ships: the template has the owner's sections, tasks/TEMPLATE.md is the seed,
    and a synthetic `engine.py install` seeds tasks/ once and never again.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/unattended/board.py"
INBOX = ROOT / "tests/fixtures/board-inbox"
_spec = importlib.util.spec_from_file_location("board", SCRIPT)
assert _spec is not None and _spec.loader is not None, SCRIPT
board = importlib.util.module_from_spec(_spec)
sys.modules["board"] = board
_spec.loader.exec_module(board)

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          capture_output=True, text=True, check=False)


def new_board() -> Path:
    root = Path(tempfile.mkdtemp(prefix="board-"))
    for name in board.COLUMNS:
        (root / "tasks" / name).mkdir(parents=True)
        (root / "tasks" / name / ".gitkeep").touch()
    return root


def task(deps: str = "—", audit: str = "ні", questions: str = "") -> str:
    return (f"# Задача\n\nЗалежить від: {deps}\nАудит потрібен: {audit}\n\n## Що зробити\n- щось\n\n"
            f"## Готово, коли\n- готово\n\n## Питання до власника\n{questions}")


def put(root: Path, column: str, name: str, text: str) -> Path:
    path = root / "tasks" / column / name
    path.write_text(text, encoding="utf-8")
    return path


def done(root: Path, stem: str) -> None:
    (root / "tasks/done" / stem).mkdir()
    (root / "tasks/done" / stem / "task.md").write_text(task(), encoding="utf-8")
    (root / "tasks/done" / stem / "report.md").write_text("# report\n", encoding="utf-8")


# --- parsing: the owner's seventeen real tasks ---------------------------------------------
print("parsing")
real = {p.name: board.parse(p.read_text(encoding="utf-8")) for p in sorted(INBOX.glob("*.md"))}
check("seventeen real tasks are in the fixtures", len(real) == 17, sorted(real))
check("every real file name is a task name", all(board.number_of(n) is not None for n in real), sorted(real))
check("001 depends on nothing («—»)", real["001-critics-strongest-model.md"].depends == ())
check("007 depends on 001", real["007-release-and-stable.md"].depends == (1,))
check("080 depends on 010, 050, 060, 070", real["080-modes-design.md"].depends == (10, 50, 60, 70))
check("005 and 040 («дошка задач») name no task", real["005-escalation-via-board.md"].depends == ()
      and real["040-lessons-to-rules-owner-only.md"].depends == ())
check("no real task asks for the audit", not any(t.audit for t in real.values()))
check("no real task has a question yet", all(t.answers == () for t in real.values()),
      {n: t.answers for n, t in real.items() if t.answers})
check("015's body sentence about questions is not its questions section",
      "у розділ нижче" not in real["015-overseer-fresh-context.md"].questions)
check("a task with no question is not answered", not real["012-simplifier-gemini-second-opinion.md"].answered)

t = board.parse(task(audit="так"))
check("«Аудит потрібен: так» is read", t.audit is True)
check("«Аудит потрібен: Так.» is read too", board.parse(task(audit="Так.")).audit is True)
check("a missing audit line means no", board.parse("# x\n\n## Що зробити\n").audit is False)
check("an audit line below the header (in the body) does not count",
      board.parse("# x\n\nЗалежить від: —\n\n## Що зробити\nАудит потрібен: так\nЗалежить від: 005\n").audit is False
      and board.parse("# x\n\n## Що зробити\nЗалежить від: 005\n").depends == ())
check("«так» only in the template's choice «так/ні» is not a yes", board.parse(task(audit="так/ні")).audit is False)
check("dependencies «1, 12» are numbers 1 and 12", board.parse(task(deps="1, 12")).depends == (1, 12))

q_open = "1. Застосувати?\n   Відповідь:\n2. Коли?\n   Відповідь: завтра\n"
q_full = "1. Застосувати?\n   Відповідь: так\n2. Коли?\n   Відповідь: завтра\n"
check("two questions, one answered: not answered", board.parse(task(questions=q_open)).answers == ("", "завтра")
      and not board.parse(task(questions=q_open)).answered)
check("two questions, both answered: answered", board.parse(task(questions=q_full)).answered)
check("a bold «**Відповідь:** так» is an answer", board.parse(task(questions="- Чи?\n  **Відповідь:** так\n")).answers == ("так",))
check("an HTML comment (the template's hint) is not a question",
      board.parse(task(questions="<!-- Питання?\nВідповідь: -->\n")).answers == ())
check("«Відповідь:» outside the questions section is not an answer",
      board.parse("# x\n\n## Що зробити\nВідповідь: так\n\n## Питання до власника\n").answers == ())
check("the questions section ends at the next heading",
      board.parse(task(questions="- Чи?\n  Відповідь: так\n\n## Інше\nВідповідь:\n")).answers == ("так",))

# --- next / start / where ---------------------------------------------------------------------
print("next, start, where")
root = new_board()
r = cli(root, "next")
check("empty todo: exit 3, nothing printed", r.returncode == 3 and r.stdout == "", (r.returncode, r.stdout, r.stderr))
put(root, "todo", "010-b.md", task(deps="002"))
put(root, "todo", "002-a.md", task())
put(root, "todo", "100-c.md", task())
(root / "tasks/todo/README.md").write_text("not a task\n", encoding="utf-8")
r = cli(root, "next")
check("the lowest number goes first", r.returncode == 0 and r.stdout.strip() == "tasks/todo/002-a.md", r.stdout + r.stderr)
r = cli(root, "start", "tasks/todo/002-a.md")
check("start moves it to doing/", r.returncode == 0 and (root / "tasks/doing/002-a.md").is_file()
      and not (root / "tasks/todo/002-a.md").exists() and r.stdout.strip() == "tasks/doing/002-a.md", r.stdout + r.stderr)
r = cli(root, "next")
check("a task in doing/ is what `next` prints", r.returncode == 0 and r.stdout.strip() == "tasks/doing/002-a.md", r.stdout)
r = cli(root, "start", "tasks/todo/100-c.md")
check("a second start is refused: one task in doing/ at a time", r.returncode == 2 and (root / "tasks/todo/100-c.md").is_file(), r.stderr)
check("where: doing", cli(root, "where", "002-a").stdout.strip() == "doing")
(root / "tasks/doing/002-a.md").unlink()
put(root, "blocked", "002-a.md", task(questions="- Чи?\n  Відповідь:\n"))
check("where: blocked", cli(root, "where", "002-a").stdout.strip() == "blocked")
r = cli(root, "next")
check("010 waits for 002 (blocked is not done): 100 is next", r.stdout.strip() == "tasks/todo/100-c.md", r.stdout)
(root / "tasks/todo/100-c.md").unlink()
r = cli(root, "next")
check("only a task with an unmet dependency is left: exit 4", r.returncode == 4 and r.stdout == "", (r.returncode, r.stdout))
(root / "tasks/blocked/002-a.md").unlink()
done(root, "002-a")
check("where: done", cli(root, "where", "002-a").stdout.strip() == "done")
check("where: missing", cli(root, "where", "999-x").stdout.strip() == "missing")
r = cli(root, "next")
check("with 002 in done/, 010 is eligible", r.returncode == 0 and r.stdout.strip() == "tasks/todo/010-b.md", r.stdout)
put(root, "doing", "100-c.md", task())
put(root, "doing", "101-d.md", task())
r = cli(root, "next")
check("two tasks in doing/: exit 2, said on stderr", r.returncode == 2 and "doing" in r.stderr, r.stderr)
r = cli(root, "start", "tasks/todo/nope.md")
check("start of a file that is not in todo/: exit 2", r.returncode == 2, r.stderr)

# --- unblock ------------------------------------------------------------------------------------
print("unblock")
root = new_board()
put(root, "blocked", "003-open.md", task(questions=q_open))
put(root, "blocked", "004-full.md", task(questions=q_full))
put(root, "blocked", "005-none.md", task())
r = cli(root, "unblock")
check("only the fully answered task returns to todo/", r.returncode == 0 and r.stdout.split() == ["004-full.md"]
      and (root / "tasks/todo/004-full.md").is_file() and (root / "tasks/blocked/003-open.md").is_file()
      and (root / "tasks/blocked/005-none.md").is_file(), r.stdout + r.stderr)
check("its text is untouched", (root / "tasks/todo/004-full.md").read_text(encoding="utf-8") == task(questions=q_full))

# --- import-inbox -------------------------------------------------------------------------------
print("import-inbox")
root = new_board()
inbox = root / "inbox"
inbox.mkdir()
put(root, "todo", "020-old-name.md", "old\n")
put(root, "doing", "030-busy.md", task())
done(root, "040-finished")
put(root, "blocked", "050-asked.md", task(questions=q_open))
put(root, "blocked", "060-asked.md", task(questions=q_open))
(inbox / "010-new.md").write_text(task(), encoding="utf-8")
(inbox / "020-new-name.md").write_text("new\n", encoding="utf-8")
(inbox / "030-busy.md").write_text("changed\n", encoding="utf-8")
(inbox / "040-finished.md").write_text("changed\n", encoding="utf-8")
(inbox / "050-asked.md").write_text(task(questions=q_full), encoding="utf-8")
(inbox / "060-asked.md").write_text(task(), encoding="utf-8")
(inbox / "notes.txt").write_text("not a task\n", encoding="utf-8")
r = cli(root, "import-inbox", str(inbox))
lines = dict(line.split(" ", 1) for line in r.stdout.splitlines())
check("a new task is imported and leaves the inbox", lines.get("010-new.md", "").startswith("imported")
      and (root / "tasks/todo/010-new.md").read_text(encoding="utf-8") == task() and not (inbox / "010-new.md").exists(), r.stdout + r.stderr)
check("the same number in todo/ is replaced, old name gone", lines.get("020-new-name.md", "").startswith("replaced")
      and (root / "tasks/todo/020-new-name.md").read_text(encoding="utf-8") == "new\n"
      and not (root / "tasks/todo/020-old-name.md").exists(), r.stdout)
check("the same number in doing/ is not touched and stays in the inbox", lines.get("030-busy.md", "").startswith("skipped")
      and (root / "tasks/doing/030-busy.md").read_text(encoding="utf-8") == task() and (inbox / "030-busy.md").is_file()
      and not (root / "tasks/todo/030-busy.md").exists(), r.stdout)
check("the same number in done/ is not touched and stays in the inbox", lines.get("040-finished.md", "").startswith("skipped")
      and (inbox / "040-finished.md").is_file() and not (root / "tasks/todo/040-finished.md").exists(), r.stdout)
check("an answered copy replaces the blocked task", lines.get("050-asked.md", "").startswith("answered")
      and (root / "tasks/blocked/050-asked.md").read_text(encoding="utf-8") == task(questions=q_full)
      and not (inbox / "050-asked.md").exists(), r.stdout)
check("a copy without answers does NOT wipe the blocked task's questions", lines.get("060-asked.md", "").startswith("skipped")
      and (root / "tasks/blocked/060-asked.md").read_text(encoding="utf-8") == task(questions=q_open)
      and (inbox / "060-asked.md").is_file(), r.stdout)
check("a file that is not a task stays where it is, unlisted", (inbox / "notes.txt").is_file() and "notes.txt" not in r.stdout)
r = cli(root, "import-inbox", str(root / "no-such-dir"))
check("no inbox directory: exit 0, nothing printed", r.returncode == 0 and r.stdout == "", r.stderr)

root = new_board()
inbox = root / "inbox"
shutil.copytree(INBOX, inbox)
before = {p.name: p.read_bytes() for p in inbox.glob("*.md")}
r = cli(root, "import-inbox", str(inbox))
after = {p.name: p.read_bytes() for p in (root / "tasks/todo").glob("*.md")}
check("the seventeen real tasks arrive byte-identical and the inbox is empty", after == before and not list(inbox.glob("*.md")), r.stdout[:300])
r = cli(root, "next")
check("the first real task is 001", r.stdout.strip() == "tasks/todo/001-critics-strongest-model.md", r.stdout)

# --- audit-allowed ------------------------------------------------------------------------------
print("audit-allowed")
root = new_board()
r = cli(root, "audit-allowed")
check("no task in doing/: refused, with the reason", r.returncode == 1 and "doing" in r.stdout + r.stderr, r.stdout + r.stderr)
put(root, "doing", "001-a.md", task(audit="ні"))
r = cli(root, "audit-allowed")
check("the task says «ні»: refused, the task is named", r.returncode == 1 and "001-a.md" in r.stdout + r.stderr, r.stdout + r.stderr)
put(root, "doing", "001-a.md", task(audit="так"))
r = cli(root, "audit-allowed")
check("the task says «так»: allowed", r.returncode == 0, r.stdout + r.stderr)
put(root, "todo", "002-b.md", task(audit="так"))
(root / "tasks/doing/001-a.md").unlink()
check("«так» in todo/ allows nothing", cli(root, "audit-allowed").returncode == 1)
r = cli(root, "audit-allowed", "--tasks-dir", str(new_board() / "tasks"))
check("--tasks-dir names another board", r.returncode == 1, r.stdout + r.stderr)

# --- summary ------------------------------------------------------------------------------------
print("summary")
root = new_board()
put(root, "todo", "010-b.md", task(deps="002, 777"))
put(root, "blocked", "002-a.md", task(questions=q_open))
done(root, "001-z")
r = cli(root, "summary")
check("summary counts the columns", "todo: 1" in r.stdout and "blocked: 1" in r.stdout and "done: 1" in r.stdout and "doing: 0" in r.stdout, r.stdout)
check("summary names the open question of a blocked task", "002-a.md" in r.stdout and "Застосувати?" in r.stdout, r.stdout)
check("summary says what 010 waits for, and that 777 exists nowhere", "010-b.md" in r.stdout and "002" in r.stdout
      and "777" in r.stdout and "ніде" in r.stdout, r.stdout)

# --- the board ships ----------------------------------------------------------------------------
print("the board in this repository and in a project")
template = (ROOT / "tasks/TEMPLATE.md").read_text(encoding="utf-8")
check("the template has the owner's sections, in order",
      [h for h in ("# ", "Залежить від:", "Аудит потрібен: ні", "## Що зробити", "## Готово, коли", "## Питання до власника", "Відповідь:")
       if h in template] == ["# ", "Залежить від:", "Аудит потрібен: ні", "## Що зробити", "## Готово, коли", "## Питання до власника", "Відповідь:"]
      and template.index("Залежить від:") < template.index("Аудит потрібен:") < template.index("## Що зробити")
      < template.index("## Готово, коли") < template.index("## Питання до власника") < template.index("Відповідь:"), template)
parsed = board.parse(template)
check("the template itself parses: no dependency, no audit, no open question", parsed.depends == () and not parsed.audit and parsed.answers == (), parsed)
check("tasks/TEMPLATE.md is the seed, byte for byte", template == (ROOT / "templates/project/tasks/TEMPLATE.md").read_text(encoding="utf-8"))
check("the four columns exist here", all((ROOT / "tasks" / c).is_dir() for c in board.COLUMNS))
check("tasks/README.md exists here and as a seed", (ROOT / "tasks/README.md").is_file() and (ROOT / "templates/project/tasks/README.md").is_file())


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


with tempfile.TemporaryDirectory(prefix="board-install-") as tmp:
    where = Path(tmp)
    eng = where / "engine"
    eng.mkdir()
    for rel in (".claude", "templates"):
        shutil.copytree(ROOT / rel, eng / rel, ignore=shutil.ignore_patterns("__pycache__", "state", "settings.local.json"))
    shutil.copy2(ROOT / "engine.py", eng / "engine.py")
    git(eng, "init", "-q", "-b", "main")
    git(eng, "add", "-A")
    git(eng, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "engine")
    git(eng, "tag", "v99.0.0")
    env = {**os.environ, "ENGINE_PROJECTS_FILE": str(where / "projects.txt")}
    proj = where / "fresh"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")

    def engine(command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(eng / "engine.py"), command, str(proj), "--ref", "v99.0.0",
                               *(["--no-register"] if command == "install" else [])],
                              capture_output=True, text=True, env=env, check=False)

    r = engine("install")
    check("install exits 0", r.returncode == 0, r.stdout + r.stderr)
    check("the project gets the four columns", all((proj / "tasks" / c).is_dir() for c in board.COLUMNS), r.stdout)
    check("…the README and the template, from the seeds",
          (proj / "tasks/README.md").is_file() and (proj / "tasks/TEMPLATE.md").is_file()
          and (proj / "tasks/README.md").read_bytes() == (ROOT / "templates/project/tasks/README.md").read_bytes())
    check("…and the board's reader and runner, as engine files", (proj / ".claude/unattended/board.py").is_file())
    r = subprocess.run([sys.executable, str(proj / ".claude/unattended/board.py"), "next"], capture_output=True, text=True, check=False)
    check("board.py finds the project's board without --root", r.returncode == 3, r.stdout + r.stderr)
    (proj / "tasks/README.md").write_text("the project's own words\n", encoding="utf-8")
    (proj / "tasks/TEMPLATE.md").unlink()
    (proj / "tasks/todo/001-mine.md").write_text(task(), encoding="utf-8")
    r = engine("update")
    check("update exits 0", r.returncode == 0, r.stdout + r.stderr)
    check("an update never overwrites the project's README", (proj / "tasks/README.md").read_text(encoding="utf-8") == "the project's own words\n")
    check("…never re-seeds a template the project deleted (seeded once)", not (proj / "tasks/TEMPLATE.md").exists())
    check("…and never touches a task", (proj / "tasks/todo/001-mine.md").read_text(encoding="utf-8") == task())

# --- the rules: every bullet of the owner's items 3 and 4 is written down ---------------------------
print("the rules for the agent")
# whitespace is collapsed: a rule must not go missing because a line was re-wrapped
seed = " ".join((ROOT / "templates/project/tasks/README.md").read_text(encoding="utf-8").split())
here = " ".join((ROOT / "tasks/README.md").read_text(encoding="utf-8").split())
short = (ROOT / ".claude/engine-rules.md").read_text(encoding="utf-8")
short = short[short.index("## The task board and paid runs"):short.index("## Constitution")]
MANUAL = {
    "which task: the first in todo/ with its dependencies in done/": ("першу за номером задачу з `todo/`", "залежності вже в `done/`"),
    "…moved to doing/ in a commit of its own — or already there when the runner started you": ("окремим commit-ом", "вже лежить задача"),
    "…one task in doing/ at a time": ("одночасно лише одна задача",),
    "through the pipeline: big by /feature-architect, small in one slice": ("/feature-architect", "одним зрізом"),
    "small decisions are the agent's, recorded in the report": ("Рішення, які я ухвалив сам",),
    "the owner is needed: a question, blocked/, the next task": ("допиши питання", "`blocked/`", "берись за наступну"),
    "a design-first task ends with a design and questions; building is another task": ("спершу проєкт", "лише окремою задачею"),
    "the report: what changed for the owner, a one-minute demonstration, cost, commits, deferred": (
        "Що змінилось для власника", "демонстрація на хвилину", "витрати", "діапазон commit-ів", "відкладене"),
    "then the task goes to done/NNN-name/ with task.md and report.md": ("`done/NNN-назва/`", "`task.md`", "`report.md`"),
    "paid runs only on the owner's written word": ("Аудит потрібен: так", "лімітом у доларах", "Агент сам таких прогонів не починає"),
    "the audit script refuses by itself; --owner-approved is the owner's": ("він відмовляє", "--owner-approved"),
    "the full suite once, at the end of a task; the fast one after a slice": ("один раз, наприкінці задачі", "лише швидкий набір"),
}
for rule, phrases in MANUAL.items():
    missing = [ph for ph in phrases if ph not in seed]
    check(f"manual: {rule}", not missing, missing)
check("this repository's manual carries every rule of the seed (it may only have grown)",
      all(ph in here for phrases in MANUAL.values() for ph in phrases))
SHORT = ("`tasks/README.md`", "`todo/`", "dependencies in `done/`", "`doing/` in its own commit", "`done/NNN-name/`", "`report.md`",
         "`blocked/`", "question for the owner", "paid run", "audit included", "`Аудит потрібен: так`", "dollar limit", "Full tests once")
check("the engine's standing rules say it briefly", all(ph in short for ph in SHORT), [ph for ph in SHORT if ph not in short])
check("…in at most six lines", len(short.strip().splitlines()) <= 6, len(short.strip().splitlines()))
agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8") + (ROOT / "templates/project/AGENTS.md").read_text(encoding="utf-8")
check("both AGENTS.md files name tasks/ among the key paths", agents.count("| `tasks/` |") == 2)
evals_readme = (ROOT / "evals/README.md").read_text(encoding="utf-8")
check("evals/README.md states the paid-run rule", "--owner-approved" in evals_readme and "Аудит потрібен: так" in evals_readme)
limits = (ROOT / "docs/engine-limits.md").read_text(encoding="utf-8")
check("docs/engine-limits.md says what the gate and the runner do not guarantee", "seat belt, not a lock" in limits and "BOARD_MAX_USD" in limits)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
