#!/usr/bin/env python3
"""The mode of a task and its one reader, .claude/hooks/mode.py (board 097; design: board 080).

WHAT IS CHECKED, the negative cases first
  - `Режим: абищо` (and two `Режим:` lines) is not taken from the inbox: the file stays there, the
    journal says why once, and such a task already in todo/ is passed over by `next`;
  - `mode.py raise` refuses to go down or sideways (соло on a task in конвеєр), without a task of
    the session in doing/, on a line that names no mode, and without a reason;
  - /hotfix is refused with `Режим: ескіз` and with `Режим: конвеєр`, /bugfix (`bugfix.py prove`)
    with `Режим: ескіз`; соло lets both through;
  - a raise is written into the task file itself and lasts until the task is closed: the next task,
    without a line, is соло again — there is no state file to inherit from;
  - every task file of this board reads as before: no line is соло, and nothing on the board is
    refused for its mode;
  - «nobody is watching» has one reader: board.py, goals.py, hotfix.py, park-ask-gated.py and
    env-probe.sh answer as mode.py does for the runner's variable, the mode file and neither, and
    none of them reads the variable or the file itself any more;
  - the overseer's request carries the mode line.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
MODE = HOOKS / "mode.py"
BOARD = ROOT / ".claude/unattended/board.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(HOOKS))
mode = load("mode", MODE)
board = load("board", BOARD)

TASK = "# {n} — Задача\n\nЗалежить від: —\n{line}Аудит потрібен: ні\n\n## Що зробити\n- щось\n\n## Готово, коли\n- готово\n\n## Питання до власника\n"
roots: list[Path] = []


def task(n: str = "010", line: str = "") -> str:
    return TASK.format(n=n, line=f"{line}\n" if line else "")


def project(git: bool = False) -> Path:
    root = Path(tempfile.mkdtemp(prefix="mode-"))
    roots.append(root)
    for column in board.COLUMNS:
        (root / "tasks" / column).mkdir(parents=True)
    if git:
        for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t"), ("config", "user.name", "t")):
            subprocess.run(["git", *args], cwd=root, check=True)
        (root / ".gitignore").write_text(".claude/state/\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "base", "--allow-empty"], cwd=root, check=True)
    return root


def put(root: Path, column: str, name: str, text: str) -> Path:
    path = root / "tasks" / column / name
    path.write_text(text, encoding="utf-8")
    return path


def run(script: Path, root: Path, *args: str, unattended: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, check=False,
                          env=hook_env(root, CLAUDE_UNATTENDED_SESSION=unattended))


def said(r: subprocess.CompletedProcess[str]) -> str:
    return f"exit {r.returncode}: {r.stdout} {r.stderr}"


# ------------------------------------------------------------------ an unknown mode is not taken
print("a line that names no mode is nobody's clear word")
root = project()
inbox = root / "inbox"
inbox.mkdir()
(inbox / "020-bad.md").write_text(task("020", "Режим: абищо"), encoding="utf-8")
(inbox / "021-two.md").write_text(task("021", "Режим: соло\nРежим: конвеєр"), encoding="utf-8")
(inbox / "022-good.md").write_text(task("022", "Режим: Конвеєр"), encoding="utf-8")
r = run(BOARD, root, "--root", str(root), "import-inbox", str(inbox))
check("negative — «Режим: абищо» is not taken from the inbox and the line says why",
      "020-bad.md skipped: «Режим: абищо» — такого режиму немає" in r.stdout and (inbox / "020-bad.md").is_file()
      and not (root / "tasks/todo/020-bad.md").exists(), said(r))
check("negative — two «Режим:» lines are not taken either", "021-two.md skipped: рядків «Режим:» два" in r.stdout and (inbox / "021-two.md").is_file(), said(r))
check("…a good line in another case is taken", "022-good.md imported" in r.stdout and (root / "tasks/todo/022-good.md").is_file(), said(r))
journal = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("…the journal says why, once per file", journal.count("020-bad.md") == 1 and journal.count("021-two.md") == 1
      and "Режим: ескіз|соло|конвеєр" in journal, journal)
run(BOARD, root, "--root", str(root), "import-inbox", str(inbox))
check("…and a second import writes no second entry", (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8") == journal)
put(root, "todo", "005-bad-in-todo.md", task("005", "Режим: абищо"))
r = run(BOARD, root, "--root", str(root), "next")
check("negative — such a task already in todo/ is passed over by next", r.stdout.strip() == "tasks/todo/022-good.md", said(r))
r = run(BOARD, root, "--root", str(root), "summary")
check("…and summary says why", "не береться: 005-bad-in-todo.md — «Режим: абищо» — такого режиму немає" in r.stdout, said(r))
check("a line under a heading is text, not the mode", mode.parse(task() + "Режим: абищо\n").error == ""
      and mode.parse(task() + "Режим: абищо\n").current == "соло")
check("a line in a comment is not read", mode.parse(task("010", "<!-- Режим: конвеєр -->")).current == "соло")
check("**конвеєр** and «Соло.» are read as the mode", mode.parse(task("010", "Режим: **конвеєр**")).current == "конвеєр"
      and mode.parse(task("010", "Режим: Соло.")).current == "соло")
check("a model written into the line is no mode: the line names roles, never who runs them",
      mode.parse(task("010", "Режим: конвеєр, opus")).error != "")

# ------------------------------------------------------------------ raise: up only
print("raise: up only, by the script, into the task file")
root = project()
pipeline = put(root, "doing", "030-pipeline.md", task("030", "Режим: конвеєр"))
before = pipeline.read_text(encoding="utf-8")
r = run(MODE, root, "--root", str(root), "raise", "соло", "--why", "менше роботи")
check("negative — raise соло on a task in конвеєр is refused and the file is untouched",
      r.returncode == 2 and "a raise goes up only" in r.stderr and pipeline.read_text(encoding="utf-8") == before, said(r))
r = run(MODE, root, "--root", str(root), "raise", "конвеєр", "--why", "те саме")
check("negative — a raise to the mode in force is refused too", r.returncode == 2 and pipeline.read_text(encoding="utf-8") == before, said(r))
pipeline.rename(root / "tasks/todo" / pipeline.name)
r = run(MODE, root, "--root", str(root), "raise", "конвеєр", "--why", "великий обсяг")
check("negative — no task of the session in doing/: refused", r.returncode == 2 and "holds 0 tasks" in r.stderr, said(r))
solo = put(root, "doing", "031-solo.md", task("031"))
r = run(MODE, root, "--root", str(root), "raise", "конвеєр", "--why", "   ")
check("negative — a raise without a reason is refused", r.returncode == 2 and "--why is empty" in r.stderr and "Режим піднято" not in solo.read_text(encoding="utf-8"), said(r))
r = run(MODE, root, "--root", str(root), "raise", "ескіз", "--why", "лише питання")
check("negative — соло → ескіз is down, refused", r.returncode == 2 and "Режим піднято" not in solo.read_text(encoding="utf-8"), said(r))
r = run(MODE, root, "--root", str(root), "raise", "абищо", "--why", "x")
check("negative — a raise to no mode is refused", r.returncode == 2 and "is no mode" in r.stderr, said(r))
r = run(MODE, root, "--root", str(root), "raise", "конвеєр", "--why", "slice-planner critic: не той обсяг")
text = solo.read_text(encoding="utf-8")
check("соло → конвеєр is written: the section stands before the questions, one dated line",
      r.returncode == 0 and re.search(r"\n## Режим піднято\n- \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ — соло → конвеєр: slice-planner critic: не той обсяг\n\n## Питання до власника\n", text)
      is not None, said(r) + text)
check("…the task's own line is not touched (there is none) and the mode in force is конвеєр",
      "Режим:" not in text.split("\n## ", 1)[0] and mode.parse(text).current == "конвеєр")
raised_sketch = put(root, "todo", "038-raised-sketch.md", task("038", "Режим: ескіз"))
mode.raise_mode(raised_sketch, "конвеєр", "кілька модулів", "2026-10-09T06:00:00Z")
before_down = raised_sketch.read_text(encoding="utf-8")
down = mode.raise_mode(raised_sketch, "соло", "менше роботи", "2026-10-09T06:00:01Z")
check("negative — down from a mode that was itself raised: ескіз raised to конвеєр, then «raise соло» — refused, the file untouched",
      "a raise goes up only" in (down or "") and raised_sketch.read_text(encoding="utf-8") == before_down
      and mode.parse(before_down).current == "конвеєр", down)
cli = project()
cli_sketch = put(cli, "doing", "039-cli-sketch.md", task("039", "Режим: ескіз"))
up = run(MODE, cli, "--root", str(cli), "raise", "конвеєр", "--why", "кілька модулів")
cli_before = cli_sketch.read_text(encoding="utf-8")
back = run(MODE, cli, "--root", str(cli), "raise", "соло", "--why", "менше роботи")
check("negative — the same through the command: «Режим: ескіз», `mode.py raise конвеєр`, then `mode.py raise соло` — exit 2, the file untouched",
      up.returncode == 0 and back.returncode == 2 and "a raise goes up only" in back.stderr and cli_sketch.read_text(encoding="utf-8") == cli_before
      and mode.parse(cli_before).current == "конвеєр", said(up) + " | " + said(back))
r = run(MODE, root, "--root", str(root), "show")
check("show says конвеєр, with the line's absence and the raise as its sources",
      r.returncode == 0 and r.stdout.startswith("режим: конвеєр (рядка «Режим:» немає → соло; піднято ") and "slice-planner critic" in r.stdout
      and "задача 031-solo" in r.stdout, said(r))
sketch = put(root, "todo", "032-sketch.md", task("032", "Режим: ескіз"))
text = sketch.read_text(encoding="utf-8")
one = mode.raise_mode(sketch, "соло", "потрібен робочий код", "2026-10-09T01:00:00Z")
two = mode.raise_mode(sketch, "конвеєр", "кілька модулів", "2026-10-09T02:00:00Z")
raised = mode.parse(sketch.read_text(encoding="utf-8"))
check("two raises: two lines in one section, the last one in force", one is None and two is None and raised.current == "конвеєр"
      and [r.after for r in raised.raises] == ["соло", "конвеєр"] and sketch.read_text(encoding="utf-8").count("## Режим піднято") == 1)
check("the owner deletes the section: the owner's line is in force again",
      mode.parse(text).current == "ескіз" and mode.parse(sketch.read_text(encoding="utf-8").replace("## Режим піднято", "## Інше")).current == "ескіз")
check("…written as one list: the second line right under the first, a blank line before the next heading",
      "\n\n## Режим піднято\n- 2026-10-09T01:00:00Z — ескіз → соло: потрібен робочий код\n"
      "- 2026-10-09T02:00:00Z — соло → конвеєр: кілька модулів\n\n## Питання до власника\n" in sketch.read_text(encoding="utf-8"),
      sketch.read_text(encoding="utf-8"))
check("…and the second line starts from the mode in force, not from the owner's line",
      "— соло → конвеєр: кілька модулів" in sketch.read_text(encoding="utf-8"), sketch.read_text(encoding="utf-8"))
later = task("035", "Режим: конвеєр") + "\n## Режим піднято\n- 2026-10-09T00:00:00Z — ескіз → соло: давно\n"
check("the owner's line written above an older raise is in force: the higher of the two, not the last raise",
      mode.parse(later).current == "конвеєр" and mode.parse(later.replace("Режим: конвеєр", "Режим: ескіз")).current == "соло")
odd = task("036") + "\n## Режим піднято\n- 2026-10-09T00:00:00Z — соло → абищо: x\n- 2026-10-09T00:00:01Z — абищо → конвеєр: y\n"
check("negative — a raise line that names no mode counts for nothing", mode.parse(odd).current == "соло" and mode.parse(odd).raises == ())
twolines = put(root, "todo", "037-why.md", task("037"))
mode.raise_mode(twolines, "конвеєр", "перший рядок\nдругий   рядок", "2026-10-09T03:00:00Z")
section = twolines.read_text(encoding="utf-8").split("## Режим піднято\n", 1)[1].split("\n\n", 1)[0]
check("a reason over several lines is written as one line: the section stays one line per raise",
      section == "- 2026-10-09T03:00:00Z — соло → конвеєр: перший рядок другий рядок", section)
check("a raise line written into a comment counts for nothing",
      mode.parse(task("033") + "\n<!--\n## Режим піднято\n- 2026-10-09T00:00:00Z — соло → конвеєр: x\n-->\n").current == "соло")
bad = put(root, "todo", "034-bad.md", task("034", "Режим: абищо"))
check("negative — a task whose line names no mode cannot be raised", "names no mode" in (mode.raise_mode(bad, "конвеєр", "x", "t") or ""))

# ------------------------------------------------------------------ the raise lasts until the task is closed
print("a raise lasts until the end of its task")
folder = root / "tasks/done/031-solo"
folder.mkdir()
solo.rename(folder / "task.md")
(folder / "report.md").write_text("# звіт\n", encoding="utf-8")
put(root, "doing", "040-next.md", task("040"))
r = run(MODE, root, "--root", str(root), "show")
check("the raised task is closed; the next one without a line is соло", r.returncode == 0 and r.stdout.startswith("режим: соло (рядка «Режим:» немає → соло), задача 040-next"), said(r))
check("…the closed task still says конвеєр, in done/", mode.parse((folder / "task.md").read_text(encoding="utf-8")).current == "конвеєр")
check("…and nothing but the task files was written: no state of the mode to inherit", not (root / ".claude").exists(),
      sorted(str(p) for p in (root / ".claude").rglob("*")) if (root / ".claude").exists() else "")
r = run(MODE, root, "--root", str(root), "show", "--task", "tasks/done/031-solo/task.md")
check("show --task reads a task anywhere on the board", "режим: конвеєр" in r.stdout and "задача 031-solo" in r.stdout, said(r))
beside = project()
put(beside, "doing", "060-with-owner.md", task("060", "Режим: ескіз").replace("Аудит потрібен:", "Потрібна присутність власника: так\nАудит потрібен:"))
put(beside, "doing", "061-runner.md", task("061"))
r = run(MODE, beside, "--root", str(beside), "show", unattended="1")
check("the owner's attended task beside the runner's: an unattended session reads its own task, not the owner's",
      r.stdout.startswith("режим: соло (рядка «Режим:» немає → соло), задача 061-runner"), said(r))
two = project()
first_two = put(two, "doing", "062-a.md", task("062"))
put(two, "doing", "063-b.md", task("063"))
r = run(MODE, two, "--root", str(two), "raise", "конвеєр", "--why", "x")
check("negative — two tasks of the session in doing/: a raise is refused, nothing is written",
      r.returncode == 2 and "holds 2 tasks" in r.stderr and "Режим піднято" not in first_two.read_text(encoding="utf-8"), said(r))
hidden = put(two, "todo", "064-comment.md", task("064"))
mode.raise_mode(hidden, "конвеєр", "причина <!-- а далі нічого не видно", "2026-10-09T04:00:00Z")
check("a reason that opens an HTML comment cannot hide the raise or the rest of the file",
      mode.parse(hidden.read_text(encoding="utf-8")).current == "конвеєр" and "<!--" not in hidden.read_text(encoding="utf-8")
      and board.parse(hidden.read_text(encoding="utf-8")).questions == "", hidden.read_text(encoding="utf-8"))
first_raise = mode.raise_mode(put(two, "todo", "066-sketch.md", "# 066\n\nРежим: ескіз\n\n## Що зробити\n- щось\n"), "соло", "перше", "2026-10-09T05:00:00Z")
second_raise = mode.raise_mode(two / "tasks/todo/066-sketch.md", "конвеєр", "друге", "2026-10-09T05:00:01Z")
tail = (two / "tasks/todo/066-sketch.md").read_text(encoding="utf-8")
check("a task without a questions section: the section is made at the end, and the next raise joins it",
      first_raise is None and second_raise is None and tail.endswith("- щось\n\n## Режим піднято\n- 2026-10-09T05:00:00Z — ескіз → соло: перше\n"
                                                                      "- 2026-10-09T05:00:01Z — соло → конвеєр: друге\n") and mode.parse(tail).current == "конвеєр", tail)
r = run(MODE, two, "--root", str(two), "show", "--task", "tasks/todo/999-none.md")
check("negative — show --task with no such file: refused, exit 2", r.returncode == 2 and "is not a file" in r.stderr, said(r))
(two / ".engine").mkdir()
(two / ".engine/baseline.json").write_text("{}\n", encoding="utf-8")
half = mode.accompaniment(two)
(two / ".engine/onboard").mkdir()
(two / ".engine/onboard/profile.md").write_text("# profile\n", encoding="utf-8")
check("the accompaniment needs both the snapshot and the profile: one of them is no accompaniment",
      half == (False, "немає .engine/onboard/profile.md") and mode.accompaniment(two)[0] is True, (half, mode.accompaniment(two)))
empty = project()
r = run(MODE, empty, "--root", str(empty), "show")
check("no task in doing/: show says so and exits 0", r.returncode == 0 and r.stdout.startswith("режим: — (у tasks/doing/ немає задачі цієї сесії"), said(r))

# ------------------------------------------------------------------ the tasks there are
print("the tasks there are read as before")
real = [p for c in ("todo", "doing", "blocked") for p in (ROOT / "tasks" / c).glob("[0-9]*.md")] + list((ROOT / "tasks/done").glob("*/task.md"))
refused = [p.name for p in real if board.read(p).mode_error]
check(f"{len(real)} task files of this board: none is refused for its mode", len(real) > 50 and not refused, refused)
check("…a task without the line is соло", all(mode.parse(p.read_text(encoding="utf-8")).current == "соло"
                                            for p in real if "Режим:" not in p.read_text(encoding="utf-8")))
template = (ROOT / "tasks/TEMPLATE.md").read_text(encoding="utf-8")
check("the template carries the line, and it reads as соло", "Режим: соло" in template and mode.parse(template).current == "соло" and not board.parse(template).mode_error)

# ------------------------------------------------------------------ what a mode forbids
print("what a mode forbids: /hotfix and /bugfix")
URGENT = "# 010 — Вхід падає\n\nЗалежить від: —\n{line}Аудит потрібен: ні\n\n## Що зробити\nЦе термінове виправлення: `/hotfix`.\n\n## Питання до власника\n"


def urgent(line: str) -> Path:
    root = project(git=True)
    (root / ".claude").mkdir()
    (root / ".claude/project.env").write_text('SOURCE_DIRS="app"\n', encoding="utf-8")
    put(root, "doing", "010-urgent.md", URGENT.format(line=f"{line}\n" if line else ""))
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "task"], cwd=root, check=True)
    return root


for line, refused_ in (("Режим: ескіз", True), ("Режим: конвеєр", True), ("", False)):
    root = urgent(line)
    r = run(HOOKS / "hotfix.py", root, "start", "--name", "login-500", "--task", "tasks/doing/010-urgent.md")
    cards = list((root / ".engine/bugs").glob("*.md")) if (root / ".engine/bugs").is_dir() else []
    if refused_:
        check(f"negative — /hotfix with «{line}» is refused and writes no card",
              r.returncode == 2 and "is refused in the mode" in r.stdout and not cards, said(r))
    else:
        check("/hotfix in соло (no line) starts: the card is written", r.returncode == 0 and len(cards) == 1, said(r))
        shown = run(MODE, root, "--root", str(root), "show").stdout
        check("…and show names the work type from the card IN PROGRESS", "тип роботи: hotfix (.engine/bugs/001-login-500.md)" in shown, shown)
root = urgent("Режим: ескіз")
(root / "tasks/doing/010-urgent.md").rename(root / "tasks/todo/010-urgent.md")
r = run(HOOKS / "hotfix.py", root, "start", "--name", "login-500", "--task", "tasks/todo/010-urgent.md")
check("negative — the task named by --task decides, wherever it lies: ескіз in todo/, doing/ empty — refused",
      r.returncode == 2 and "is refused in the mode «ескіз»" in r.stdout, said(r))
(root / "tasks/todo/010-urgent.md").rename(root / "tasks/doing/010-urgent.md")
r = run(HOOKS / "bugfix.py", root, "prove", "--test", "tests/test_x.py", "--cmd", "true")
check("negative — /bugfix (bugfix.py prove) in ескіз is refused before anything runs",
      r.returncode == 1 and "/bugfix is refused in the mode «ескіз»" in r.stdout, said(r))
root = urgent("")
r = run(MODE, root, "--root", str(root), "raise", "конвеєр", "--why", "кілька модулів")
r = run(HOOKS / "hotfix.py", root, "start", "--name", "login-500", "--task", "tasks/doing/010-urgent.md")
check("negative — the mode in force decides, not the owner's line: no line, raised to конвеєр — /hotfix refused, no card",
      r.returncode == 2 and "is refused in the mode «конвеєр»" in r.stdout and not (root / ".engine/bugs").exists(), said(r))
root = urgent("Режим: ескіз")
run(MODE, root, "--root", str(root), "raise", "соло", "--why", "потрібне виправлення")
r = run(HOOKS / "bugfix.py", root, "prove", "--test", "tests/test_x.py", "--cmd", "true")
check("…and the other way: ескіз raised to соло — bugfix.py prove is not refused for its mode (it goes on to its own checks)",
      "refused in the mode" not in r.stdout and "is not a file of this project" in r.stderr, said(r))
check("…in соло and in конвеєр bugfix is allowed", mode.FORBIDDEN.get(("соло", "bugfix")) is None and mode.FORBIDDEN.get(("конвеєр", "bugfix")) is None)

# ------------------------------------------------------------------ «nobody is watching»: one reader
print("«nobody is watching» has one reader")
root = project(git=True)
probe = ROOT / ".claude/unattended/env-probe.sh"
gated = HOOKS / "park-ask-gated.py"
push = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push origin work"}})
goals = load("goals_for_mode", HOOKS / "goals.py")
hotfix = load("hotfix_for_mode", HOOKS / "hotfix.py")
for label, env_value, file_text, expected, where, kind in (
        ("the runner's variable", "1", None, True, "env", "unattended-supervised"),
        ("the mode file", "", "unattended\n", True, "mode-file", "unattended-mode-file"),
        ("neither", "", None, False, "", "attended-local"),
        ("negative — the variable is 0, the file says attended", "0", "attended\n", False, "", "attended-local")):
    state = root / ".claude/state/overseer/mode"
    if file_text is None:
        state.unlink(missing_ok=True)
    else:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(file_text, encoding="utf-8")
    saved = dict(os.environ)
    os.environ["CLAUDE_UNATTENDED_SESSION"] = env_value
    try:
        answers = {"mode.py": mode.unattended(root), "board.py": board.unattended_session(root), "goals.py": goals.unattended(root),
                   "hotfix.py": hotfix.unattended(root)}
    finally:
        os.environ.clear()
        os.environ.update(saved)
    parked = subprocess.run([sys.executable, str(gated)], input=push, capture_output=True, text=True, check=False,
                            env=hook_env(root, CLAUDE_UNATTENDED_SESSION=env_value)).stdout
    kind_said = subprocess.run(["bash", str(probe)], capture_output=True, text=True, check=False,
                               env=hook_env(root, CLAUDE_UNATTENDED_SESSION=env_value, CLAUDE_CODE_REMOTE="")).stdout
    cli = run(MODE, root, "--root", str(root), "unattended", unattended=env_value)
    check(f"{label}: all five places answer as the reader ({expected}, {where or 'attended'})",
          answers["mode.py"] == (expected, where) and answers["board.py"] == expected and answers["goals.py"] == expected
          and answers["hotfix.py"] == expected and ('"deny"' in parked) == expected and f"session_kind={kind}\n" in kind_said
          and cli.returncode == (0 if expected else 1), (answers, parked[:80], [line for line in kind_said.splitlines() if "session_kind" in line], said(cli)))
alone = project()
(alone / ".claude/hooks").mkdir(parents=True)
(alone / ".claude/unattended").mkdir(parents=True)
shutil.copy2(gated, alone / ".claude/hooks/park-ask-gated.py")
shutil.copy2(probe, alone / ".claude/unattended/env-probe.sh")
(alone / ".claude/state/overseer").mkdir(parents=True)
(alone / ".claude/state/overseer/mode").write_text("unattended\n", encoding="utf-8")
lone_hook = subprocess.run([sys.executable, str(alone / ".claude/hooks/park-ask-gated.py")], input=push, capture_output=True, text=True,
                           check=False, env=hook_env(alone, CLAUDE_UNATTENDED_SESSION="")).stdout
lone_probe = subprocess.run(["bash", str(alone / ".claude/unattended/env-probe.sh")], capture_output=True, text=True, check=False,
                            env=hook_env(alone, CLAUDE_UNATTENDED_SESSION="", CLAUDE_CODE_REMOTE="")).stdout
check("negative — the reader missing: the park hook falls back to «attended» (the normal prompt: since board 603 the hook asks itself), the probe says it cannot tell",
      '"permissionDecision": "ask"' in lone_hook and '"deny"' not in lone_hook and "session_kind=unknown (no python3 or no " in lone_probe,
      (lone_hook[:80], [line for line in lone_probe.splitlines() if "session_kind" in line]))
# The ways the five decided it themselves; env-probe.sh still PRINTS the file's content as a fact, which decides nothing.
for text, expected in (("not unattended\n", False), ("unattended later\n", False), ("Unattended\n", True), ("**unattended**\n", True)):
    (root / ".claude/state/overseer/mode").write_text(text, encoding="utf-8")
    check(f"the mode file says {text.strip()!r}: {'unattended' if expected else 'attended'} — the word itself, not a word inside a sentence",
          mode.unattended(root)[0] == expected)
own_reading = re.compile(r'environ\.get\("CLAUDE_UNATTENDED_SESSION"\)|"overseer" / "mode"|MODE_REL|CLAUDE_UNATTENDED_SESSION:-|grep -qx .unattended|== "unattended"|"unattended" in ')
places = (".claude/unattended/board.py", ".claude/unattended/env-probe.sh", ".claude/hooks/goals.py", ".claude/hooks/hotfix.py", ".claude/hooks/park-ask-gated.py")
readers = {rel: [line.strip() for line in (ROOT / rel).read_text(encoding="utf-8").splitlines() if own_reading.search(line)] for rel in places}
check("none of the five reads the variable or the mode file itself any more", not any(readers.values()), readers)

# ------------------------------------------------------------------ the overseer's request
print("the overseer's request carries the mode")
root = project(git=True)
put(root, "doing", "050-x.md", task("050", "Режим: конвеєр"))
verdict = load("overseer_verdict_for_mode", HOOKS / "overseer_verdict.py")
request = verdict.make_request(root, "=== UNIT 1 COMPLETE ===", origin="test")
check("request.json says the task's mode, as mode.py show prints it", request.get("mode", "").startswith("режим: конвеєр (рядок «Режим: конвеєр»)")
      and json.loads((root / f".claude/state/overseer/requests/{request['id']}/request.json").read_text(encoding="utf-8"))["mode"] == request["mode"], request.get("mode"))
check("the overseer's definition says what the field means", "`mode`" in (ROOT / ".claude/agents/overseer.md").read_text(encoding="utf-8")
      and "«конвеєр»" in (ROOT / ".claude/agents/overseer.md").read_text(encoding="utf-8"))

for path in roots:
    shutil.rmtree(path, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
