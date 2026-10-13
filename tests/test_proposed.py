#!/usr/bin/env python3
"""New work only through the owner: the column tasks/proposed/ (board 111).

WHAT IS CHECKED, the negative cases first
  - `open-item --to todo` and the overseer's test gap (`overseer_verdict.open_test_gaps`) leave NO file
    in todo/: the item lies in proposed/; so does the follow-up of an urgent fix (`hotfix.py debt`)
    and what `--to proposed` names outright;
  - a board that holds proposals only gives the runner nothing: `next` exits 3 and prints nothing,
    `start` refuses a file of proposed/;
  - a number of proposed/ is taken: the next item, and an inbox file without a number, get another;
  - `check` sees one number in proposed/ and todo/, and one number twice inside proposed/;
  - the owner puts a proposal to work through the inbox: a file with the proposal's number moves it to
    todo/ with the inbox text, and only then `next` offers it;
  - a question for the owner (`--to blocked`) lies where it lay;
  - `summary` (the runner's summary.md prints it) counts proposed/ and names its items; the same key
    returns the proposal still open; `where` says `proposed`;
  - with the engine's own project.env an idle board gets no cleanup task (CLEANUP_EVERY_DAYS="0"); with the
    template's it does, as before.
The review's part is in test_board_review.py, the real runner's in test_board_runner.py.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from hook_env import hook_env, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/unattended/board.py"


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


board = load("board", SCRIPT)
sys.path.insert(0, str(ROOT / ".claude/hooks"))
verdict = load("overseer_verdict", ROOT / ".claude/hooks/overseer_verdict.py")

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in hook_env(root).items() if k != "CLAUDE_UNATTENDED_SESSION"}
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], capture_output=True, text=True, check=False, env=env)


def new_board() -> Path:
    """A board as a project installed before this column has it: four columns, no proposed/."""
    root = Path(sandbox_dir("proposed-"))
    for name in ("todo", "doing", "blocked", "done"):
        (root / "tasks" / name).mkdir(parents=True)
    return root


def names(root: Path, column: str) -> list[str]:
    return sorted(p.name for p in (root / "tasks" / column).glob("[0-9]*"))


def task(title: str = "Задача", body: str = "- щось") -> str:
    return f"# {title}\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Що зробити\n{body}\n\n## Готово, коли\n- готово\n\n## Питання до власника\n"


print("work an agent, a hook or the overseer found is a proposal, never a task of todo/")
root = new_board()
r = cli(root, "open-item", "--to", "todo", "--key", "found-one", "--title", "Знахідка агента", "--what", "щось не так", "--do", "ЗРОБИТИ-ОДИН")
check("`open-item --to todo` leaves nothing in todo/", names(root, "todo") == [], names(root, "todo"))
check("…the item lies in proposed/, and that is the path printed", r.stdout.strip() == "tasks/proposed/701-open-item-found-one.md"
      and names(root, "proposed") == ["701-open-item-found-one.md"], r.stdout + r.stderr)
row = {"verdict": "PASS", "unit_key": "111/1", "slice": "111", "request": "20261013T000000Z-aaaaaa"}
opened = verdict.open_test_gaps(root, row, [{"check": "a check that the gap is seen", "misses": "nothing fails when it is gone", "where": "tests/x.py"}])
check("the overseer's test gap leaves nothing in todo/", names(root, "todo") == [], names(root, "todo"))
check("…it lies in proposed/, and the ledger row names that path", len(names(root, "proposed")) == 2
      and str(opened[0].get("task", "")).startswith("tasks/proposed/702-open-item-test-gap-"), (names(root, "proposed"), opened))
r = cli(root, "open-item", "--to", "proposed", "--title", "Названо прямо", "--what", "x")
check("`--to proposed` is the same column by its own name", r.returncode == 0 and r.stdout.startswith("tasks/proposed/703-open-item-")
      and names(root, "todo") == [], r.stdout + r.stderr)

print("the runner takes nothing from proposed/")
r = cli(root, "next")
check("a board with proposals only: `next` exits 3 and prints nothing", r.returncode == 3 and r.stdout == "", (r.returncode, r.stdout, r.stderr))
r = cli(root, "start", "tasks/proposed/701-open-item-found-one.md")
check("`start` refuses a file of proposed/, and it stays there", r.returncode == 2 and names(root, "doing") == []
      and "701-open-item-found-one.md" in names(root, "proposed"), (r.returncode, r.stderr))

print("a number of proposed/ is taken")
r = cli(root, "open-item", "--to", "blocked", "--title", "Питання", "--what", "x", "--question", "Так чи ні?")
check("a question for the owner lies in blocked/ as before — with the number after the proposals'", r.stdout.strip().startswith("tasks/blocked/704-open-item-")
      and len(names(root, "blocked")) == 1, r.stdout + r.stderr)
inbox = root / "inbox"
inbox.mkdir()
(inbox / "owner-idea.md").write_text(task("NNN — Ідея власника").replace("Залежить від: —", "Клас: 7\nЗалежить від: —"), encoding="utf-8")
(root / "tasks/CLASSES.md").write_text((ROOT / "tasks/CLASSES.md").read_text(encoding="utf-8"), encoding="utf-8")
r = cli(root, "import-inbox", str(inbox))
check("an inbox file without a number gets one no proposal carries", names(root, "todo") == ["705-owner-idea.md"], r.stdout + r.stderr)
r = cli(root, "open-item", "--to", "todo", "--key", "found-one", "--title", "Те саме вдруге", "--what", "x")
check("the same key while the proposal waits: that proposal, not a second one", r.stdout.strip() == "tasks/proposed/701-open-item-found-one.md"
      and len(names(root, "proposed")) == 3, r.stdout)
check("`where` says proposed", cli(root, "where", "701-open-item-found-one").stdout.strip() == "proposed")

print("`check` sees a collision with proposed/")
clash = new_board()
(clash / "tasks/proposed").mkdir()
(clash / "tasks/proposed/701-open-item-a.md").write_text(task(), encoding="utf-8")
check("no collision: `check` is silent", cli(clash, "check").returncode == 0, cli(clash, "check").stdout)
(clash / "tasks/todo/701-other.md").write_text(task(), encoding="utf-8")
r = cli(clash, "check")
check("one number in proposed/ and in todo/ is an error that names both files", r.returncode == 1 and "ПОМИЛКА" in r.stdout and "701" in r.stdout
      and "proposed/701-open-item-a.md" in r.stdout and "todo/701-other.md" in r.stdout, r.stdout)
check("…and `summary` shows it", "ПОМИЛКА" in cli(clash, "summary").stdout)
(clash / "tasks/todo/701-other.md").unlink()
(clash / "tasks/proposed/701-open-item-b.md").write_text(task(), encoding="utf-8")
r = cli(clash, "check")
check("one number twice inside proposed/ is an error too", r.returncode == 1 and "у proposed/" in r.stdout and "701-open-item-b.md" in r.stdout, r.stdout)

print("the owner puts a proposal to work through the inbox")
before = (root / "tasks/proposed/701-open-item-found-one.md").read_text(encoding="utf-8")
(inbox / "701-do-it.md").write_text(task("701 — Власник поставив у роботу", "- СЛОВО-ВЛАСНИКА"), encoding="utf-8")
r = cli(root, "import-inbox", str(inbox))
check("the inbox file with the proposal's number: the proposal leaves proposed/", "701-open-item-found-one.md" not in names(root, "proposed")
      and len(names(root, "proposed")) == 2, (names(root, "proposed"), r.stdout))
check("…and is a task of todo/ with the inbox text, under the inbox name", "701-do-it.md" in names(root, "todo")
      and "СЛОВО-ВЛАСНИКА" in (root / "tasks/todo/701-do-it.md").read_text(encoding="utf-8") and "ЗРОБИТИ-ОДИН" in before, (names(root, "todo"), r.stdout))
check("…the inbox is empty, and the line says where it went", not list(inbox.glob("*.md")) and "tasks/todo/701-do-it.md" in r.stdout and "proposed" in r.stdout, r.stdout)
check("only now `next` offers it", cli(root, "next").stdout.strip() == "tasks/todo/701-do-it.md", cli(root, "next").stdout)
check("the other proposals stay where they were", all(n.startswith(("702-", "703-")) for n in names(root, "proposed")), names(root, "proposed"))

print("the summary counts proposed/ and names its items")
out = cli(root, "summary").stdout
check("the count stands on the first line beside the other columns", "proposed: 2" in out.splitlines()[0], out)
check("every proposal is named with its title", "пропозиція" in out and "703-open-item-" in out and "Названо прямо" in out and "Брак тесту (overseer)" in out, out)
check("the summary says who puts them to work", "inbox" in out and "власник" in out, out)
empty = new_board()
check("a board without proposals says nothing about them beyond the count", "пропозиція" not in cli(empty, "summary").stdout
      and "proposed: 0" in cli(empty, "summary").stdout, cli(empty, "summary").stdout)

print("the engine's own runner places no work")
own, template = ((ROOT / rel).read_text(encoding="utf-8") for rel in (".claude/project.env", "templates/project/.claude/project.env"))
check("the engine's project.env: CLEANUP_EVERY_DAYS is 0", '\nCLEANUP_EVERY_DAYS="0"\n' in own, [line for line in own.splitlines() if line.startswith("CLEANUP")])
check("the template's project.env: as it was, empty", '\nCLEANUP_EVERY_DAYS=""\n' in template)
placed = {}
for name, env_text in (("engine", own), ("template", template)):
    idle = new_board()
    (idle / ".claude/hooks").mkdir(parents=True)
    (idle / ".claude/hooks/simplifier.py").write_text("", encoding="utf-8")
    (idle / ".claude/project.env").write_text(env_text, encoding="utf-8")
    placed[name] = cli(idle, "cleanup-task", "--today", "2030-01-01").stdout.strip()
check("NEGATIVE — an idle board with the engine's own project.env: `cleanup-task` places nothing", placed["engine"] == "", placed)
check("…and with the template's it places the task, as before", placed["template"] == "tasks/todo/401-cleanup-2030-01-01.md", placed)

print("the column ships")
check("the engine's board and the template have proposed/", (ROOT / "tasks/proposed").is_dir() and (ROOT / "templates/project/tasks/proposed/.gitkeep").is_file())
for manual in ("tasks/README.md", "templates/project/tasks/README.md"):
    words = (ROOT / manual).read_text(encoding="utf-8")
    check(f"{manual} names the column and how a proposal goes to work", "`proposed/`" in words and "inbox" in words and "пропозиці" in words, manual)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
