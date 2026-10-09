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
  - a task that says «Потрібна присутність власника: так» (board 016) is never offered by `next`
    and never moved by `start`; with `--attended` it is, and `--attended` is refused in an
    unattended session; left in doing/ it is passed over — the board goes on (board 049); the owner's own task 017 is one;
  - the board ships: the template has the owner's sections, tasks/TEMPLATE.md is the seed,
    and a synthetic `engine.py install` seeds tasks/ once and never again.
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


def cli(root: Path, *args: str, unattended: bool = False) -> subprocess.CompletedProcess[str]:
    # The suite itself may run inside an unattended session; a case says which kind it means.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_UNATTENDED_SESSION"}
    if unattended:
        env["CLAUDE_UNATTENDED_SESSION"] = "1"
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          capture_output=True, text=True, check=False, env=env)


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
check("005 and 040 («task board») name no task", real["005-escalation-via-board.md"].depends == ()
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
(root / "tasks/todo/005-loop.md").symlink_to("005-loop.md")  # a link to itself
for given in ("tasks/todo/005-loop.md", str(root / "tasks/todo/005-loop.md")):
    r = cli(root, "start", given)
    check(f"start of a symlink loop ({'absolute' if given.startswith('/') else 'relative'}) is refused, not a traceback (board 718)",
          r.returncode == 2 and "is not a task file in tasks/todo/" in r.stderr and "Traceback" not in r.stderr, r.stderr[-300:])
(root / "tasks/todo/005-loop.md").unlink()

# --- a task that needs the owner present (board 016) ------------------------------------------
print("attended tasks")
ATTENDED_LINE = "Потрібна присутність власника"


def attended_task(value: str = "так", deps: str = "—") -> str:
    return task(deps=deps).replace("Аудит потрібен:", f"{ATTENDED_LINE}: {value}\nАудит потрібен:")


check("«Потрібна присутність власника: так» is read", board.parse(attended_task()).attended is True)
check("…«Так.» too", board.parse(attended_task("Так.")).attended is True)
check("«ні», the template's «так/ні» and a missing line all mean no", not board.parse(attended_task("ні")).attended
      and not board.parse(attended_task("так/ні")).attended and not board.parse(task()).attended)
check("the line below the header (in the body) does not count",
      not board.parse(f"# x\n\nЗалежить від: —\n\n## Що зробити\n{ATTENDED_LINE}: так\n").attended)
check("the other header lines are still read beside it", board.parse(attended_task(deps="3")).depends == (3,)
      and board.parse(attended_task().replace("Аудит потрібен: ні", "Аудит потрібен: так")).audit)
real_017 = (ROOT / "tests/fixtures/board-attended/017-block-dangerous-push-hardening.md").read_text(encoding="utf-8")
check("the owner's task 017 is an attended task that depends on 016", board.parse(real_017).attended and board.parse(real_017).depends == (16,))

root = new_board()
put(root, "todo", "017-guards.md", real_017)
done(root, "016-attended-tasks")
r = cli(root, "next")
check("017 alone in todo/, its dependency done: `next` offers nothing, exit 4", r.returncode == 4 and r.stdout == "", (r.returncode, r.stdout, r.stderr))
put(root, "todo", "018-after.md", task(deps="017"))
put(root, "todo", "019-free.md", task())
r = cli(root, "next")
check("`next` passes over 017 and over what depends on it: 019", r.returncode == 0 and r.stdout.strip() == "tasks/todo/019-free.md", r.stdout + r.stderr)
r = cli(root, "start", "tasks/todo/017-guards.md")
check("`start` refuses 017 and says why; the file stays in todo/", r.returncode == 2 and ATTENDED_LINE in r.stderr and "--attended" in r.stderr
      and (root / "tasks/todo/017-guards.md").is_file() and not (root / "tasks/doing/017-guards.md").exists(), r.stderr)
r = cli(root, "summary")
check("summary names 017 as waiting for the owner's presence, and 019 as next", "чекає на присутність власника: 017-guards.md" in r.stdout
      and "наступна: 019-free.md" in r.stdout, r.stdout)
for command in (("next", "--attended"), ("start", "--attended", "tasks/todo/017-guards.md")):
    r = cli(root, *command, unattended=True)
    check(f"`{command[0]} --attended` is refused in an unattended session (the environment)", r.returncode == 2 and r.stdout == ""
          and "unattended" in r.stderr and (root / "tasks/todo/017-guards.md").is_file(), (r.returncode, r.stdout, r.stderr))
(root / ".claude/state/overseer").mkdir(parents=True)
(root / ".claude/state/overseer/mode").write_text("unattended\n", encoding="utf-8")
r = cli(root, "start", "--attended", "tasks/todo/017-guards.md")
check("…and while the mode file says unattended (a runner is at work)", r.returncode == 2 and (root / "tasks/todo/017-guards.md").is_file(), r.stderr)
r = cli(root, "next", unattended=True)
check("…a plain `next` still works there", r.returncode == 0 and r.stdout.strip() == "tasks/todo/019-free.md", r.stderr)
(root / ".claude/state/overseer/mode").write_text("attended\n", encoding="utf-8")
r = cli(root, "next", "--attended")
check("with the owner present, `next --attended` offers 017 — not the free 019", r.returncode == 0 and r.stdout.strip() == "tasks/todo/017-guards.md", r.stdout + r.stderr)
r = cli(root, "start", "--attended", "tasks/todo/017-guards.md")
check("…and `start --attended` moves it to doing/", r.returncode == 0 and (root / "tasks/doing/017-guards.md").is_file(), r.stderr)
r = cli(root, "next")
check("017 in doing/ does not stop the board (board 049): a plain `next` passes over it and offers 019", r.returncode == 0
      and r.stdout.strip() == "tasks/todo/019-free.md" and r.stderr == "", (r.returncode, r.stdout, r.stderr))
r = cli(root, "summary")
check("…summary names 017 as worked on with the owner, and 019 as next", "в роботі з власником: 017-guards.md" in r.stdout
      and "в роботі: 017" not in r.stdout and "наступна: 019-free.md" in r.stdout, r.stdout)
put(root, "todo", "021-ordinary.md", task())
put(root, "todo", "020-second-attended.md", attended_task())
r = cli(root, "start", "--attended", "tasks/todo/020-second-attended.md")
check("…a second attended task is not started beside it: one at a time for the owner's session too", r.returncode == 2
      and (root / "tasks/todo/020-second-attended.md").is_file(), r.stderr)
(root / "tasks/todo/020-second-attended.md").unlink()
r = cli(root, "start", "tasks/todo/019-free.md", unattended=True)
check("…`start` moves 019 into doing/ beside 017", r.returncode == 0 and (root / "tasks/doing/019-free.md").is_file()
      and (root / "tasks/doing/017-guards.md").is_file(), r.stderr)
r = cli(root, "next", unattended=True)
check("…and `next` then prints 019, the runner's own task — not 017, not exit 2", r.returncode == 0 and r.stdout.strip() == "tasks/doing/019-free.md", (r.returncode, r.stdout, r.stderr))
r = cli(root, "start", "tasks/todo/021-ordinary.md")
check("…the negative case: a second ORDINARY task is still refused — one at a time", r.returncode == 2 and "019-free.md" in r.stderr
      and (root / "tasks/todo/021-ordinary.md").is_file(), r.stderr)
r = cli(root, "summary")
check("…summary shows both, each as what it is", "в роботі: 019-free.md" in r.stdout and "в роботі з власником: 017-guards.md" in r.stdout, r.stdout)
put(root, "doing", "022-extra.md", task())
r = cli(root, "next")
check("…two ordinary tasks in doing/ are still refused (exit 2), whatever the owner's session holds", r.returncode == 2 and "022-extra.md" in r.stderr, (r.returncode, r.stderr))
for name in ("019-free.md", "022-extra.md"):
    (root / "tasks/doing" / name).unlink()
(root / "tasks/todo/021-ordinary.md").unlink()
r = cli(root, "next", "--attended")
check("…`next --attended` prints it", r.returncode == 0 and r.stdout.strip() == "tasks/doing/017-guards.md", r.stdout + r.stderr)
(root / "tasks/doing/017-guards.md").unlink()
r = cli(root, "next", "--attended")
check("no attended task in todo/: `next --attended` exits 4 and does not offer an ordinary one", r.returncode == 4 and r.stdout == "", (r.returncode, r.stdout))
put(root, "todo", "020-attended-waits.md", attended_task(deps="018"))
r = cli(root, "next", "--attended")
check("an attended task waits for its dependencies like any other", r.returncode == 4 and r.stdout == "", (r.returncode, r.stdout))
shutil.rmtree(root, ignore_errors=True)

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

# --- the owner's answers first (board 049) --------------------------------------------------------
print("the owner's answers first")
FIRST = root / "tasks/.first"
check("unblock writes the answered task into tasks/.first", FIRST.read_text(encoding="utf-8").split() == ["004-full.md"], FIRST.read_text(encoding="utf-8") if FIRST.exists() else "(absent)")
shutil.rmtree(root, ignore_errors=True)
root = new_board()
done(root, "001-base")
FIRST = root / "tasks/.first"
put(root, "todo", "010-queued.md", task())
put(root, "todo", "020-queued.md", task())
put(root, "blocked", "900-gate-escalation-20261003T101500Z.md", task(questions="1. Закрити ескалацію?\n   Відповідь: спершу виправ тест\n").replace(
    "Аудит потрібен: ні", "Аудит потрібен: ні\nЕскалація gates: 2026-10-03T10:15:00Z"))
put(root, "blocked", "050-parked.md", task(questions="1. Що далі?\n   Відповідь: роби далі\n"))
put(root, "blocked", "060-waits.md", task(deps="999", questions="1. Що далі?\n   Відповідь: так\n"))
put(root, "blocked", "070-with-owner.md", attended_task().replace("## Питання до власника\n", "## Питання до власника\n1. Що?\n   Відповідь: разом\n"))
check("the negative case first: before any answer returns, the queue is by number", cli(root, "next").stdout.strip() == "tasks/todo/010-queued.md")
r = cli(root, "unblock")
check("four answered tasks return to todo/ — a gate question with an instruction among them", r.stdout.split() ==
      ["050-parked.md", "060-waits.md", "070-with-owner.md", "900-gate-escalation-20261003T101500Z.md"], r.stdout + r.stderr)
check("tasks/.first lists them in the order answered", FIRST.read_text(encoding="utf-8").split() == r.stdout.split(), FIRST.read_text(encoding="utf-8"))
r = cli(root, "next")
check("`next` offers the answered 050 before 010, whatever the number", r.returncode == 0 and r.stdout.strip() == "tasks/todo/050-parked.md", r.stdout + r.stderr)
r = cli(root, "summary")
check("summary says which tasks go first and why, and names 050 as next", "першою, бо власник відповів: 050-parked.md" in r.stdout
      and "першою, бо власник відповів: 900-gate-escalation-20261003T101500Z.md" in r.stdout and "наступна: 050-parked.md" in r.stdout
      and "першою, бо власник відповів: 010" not in r.stdout, r.stdout)
r = cli(root, "start", "tasks/todo/050-parked.md")
check("started, a task leaves tasks/.first", r.returncode == 0 and "050-parked.md" not in FIRST.read_text(encoding="utf-8").split()
      and "900-gate-escalation-20261003T101500Z.md" in FIRST.read_text(encoding="utf-8").split(), FIRST.read_text(encoding="utf-8"))
shutil.rmtree(root / "tasks/doing")
(root / "tasks/doing").mkdir()
r = cli(root, "next")
check("then the gate question numbered 900 — still before 010 and 020; 060 waits for its dependency, 070 for the owner's presence",
      r.returncode == 0 and r.stdout.strip() == "tasks/todo/900-gate-escalation-20261003T101500Z.md", r.stdout + r.stderr)
check("…with the owner present, the answered attended task is the one offered", cli(root, "next", "--attended").stdout.strip() == "tasks/todo/070-with-owner.md")
cli(root, "start", "tasks/todo/900-gate-escalation-20261003T101500Z.md")
(root / "tasks/doing/900-gate-escalation-20261003T101500Z.md").unlink()
check("the answers taken, the queue is by number again: 010", cli(root, "next").stdout.strip() == "tasks/todo/010-queued.md")
check("…and the answered task that cannot start yet keeps its place for when it can", FIRST.read_text(encoding="utf-8").split() == ["060-waits.md", "070-with-owner.md"], FIRST.read_text(encoding="utf-8"))
done(root, "999-arrived")
check("…its dependency done, 060 goes before 010", cli(root, "next").stdout.strip() == "tasks/todo/060-waits.md")
(root / "tasks/todo/060-waits.md").rename(root / "tasks/blocked/060-waits.md")
FIRST.write_text("060-waits.md\n020-queued.md\nno-such-task.md\n", encoding="utf-8")
check("a name in tasks/.first that is not in todo/ changes nothing; one that is goes first", cli(root, "next").stdout.strip() == "tasks/todo/020-queued.md")
FIRST.unlink()
check("no tasks/.first at all: by number", cli(root, "next").stdout.strip() == "tasks/todo/010-queued.md")

# --- park and the anomaly journal (board 021) ----------------------------------------------------
print("park: the runner gives up on a task, not on the board")
root = new_board()
put(root, "doing", "007-stuck.md", task())
put(root, "todo", "008-next.md", task())
r = cli(root, "park", "007-stuck", "no-commit", "--detail", "3", "--stash", "abc123")
parked = root / "tasks/blocked/007-stuck.md"
text = parked.read_text(encoding="utf-8") if parked.is_file() else ""
check("the task moves from doing/ to blocked/", r.returncode == 0 and r.stdout.strip() == "tasks/blocked/007-stuck.md"
      and not (root / "tasks/doing/007-stuck.md").exists(), r.stdout + r.stderr)
check("«Чому зупинилась» stands before the questions, dated in UTC, with the reason and the stash", text.index("## Чому зупинилась") < text.index("## Питання до власника")
      and re.search(r"^- \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ — 3 спроб\(и\) поспіль не дали жодного commit-а", text, re.MULTILINE) is not None
      and "git stash apply abc123" in text, text)
check("the task's own text is kept as it was", text.startswith(task().rstrip("\n").split("## Питання до власника")[0].rstrip("\n")), text)
check("the questions stay the last section and the new one waits for an answer", board.read(parked).answers == ("",)
      and "1. Задача застрягла" in board.read(parked).questions and cli(root, "unblock").stdout == "", board.read(parked))
journal = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("the journal is made with its heading and one entry: time, task, what happened, what was done", journal.startswith("# Журнал аномалій task board\n")
      and re.search(r"\n## \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ — 007-stuck\n- Що сталося: 3 спроб\(и\).*\n- Що зроблено: задачу перенесено в `blocked/`", journal) is not None, journal)
check("the board goes on: the next task is offered", cli(root, "next").stdout.strip() == "tasks/todo/008-next.md")
parked.write_text(text.replace("Відповідь:", "Відповідь: продовжити"), encoding="utf-8")
check("any answer returns the parked task to todo/", cli(root, "unblock").stdout.split() == ["007-stuck.md"] and (root / "tasks/todo/007-stuck.md").is_file())
r = cli(root, "park", "007-stuck", "returned")
text = parked.read_text(encoding="utf-8")
check("a task in todo/ can be parked too; a second stop adds a line to the one section and a second question", r.returncode == 0
      and text.count("## Чому зупинилась") == 1 and text.count("\n- 20") == 2 and "агент повернув задачу" in text
      and board.read(parked).answers == ("продовжити", "") and "\n2. Агент не закінчив" in text, text)
check("…and a second journal entry under the first", (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8").count("\n## ") == 2)
for reason, words in (("deadline", "довше за 12 год"), ("budget", "`BOARD_MAX_USD`): задача витратила 12 USD")):
    put(root, "doing", "009-other.md", "# Без розділу питань\n\nЗалежить від: —\n")
    r = cli(root, "park", "009-other", reason, "--detail", "12")
    text = (root / "tasks/blocked/009-other.md").read_text(encoding="utf-8")
    check(f"{reason}: the reason is worded, and a task without a questions section gets one", r.returncode == 0 and words in text
          and board.read(root / "tasks/blocked/009-other.md").answers == ("",) and "git stash" not in text, text)
    (root / "tasks/blocked/009-other.md").unlink()
# three BLOCKs in a row (board 031): the verdicts the Stop hook left go into the task
put(root, "doing", "010-refused.md", task())
marker = root / "marker.json"
marker.write_text(json.dumps({"task": "010-refused", "unit": "-|010-refused|unit 2", "blocks": [
    {"utc": "2026-10-04T10:00:00Z", "request": "r1", "check": 4, "reason": "masked  test gap"},
    {"utc": "2026-10-04T10:05:00Z", "request": "r2", "check": None, "reason": "ДРУГА-ПРИЧИНА"},
    {"utc": "2026-10-04T10:09:00Z", "request": "r3", "check": 1, "reason": "false DONE"}]}, ensure_ascii=False), encoding="utf-8")
r = cli(root, "park", "010-refused", "three-blocks", "--verdicts", str(marker))
refused = root / "tasks/blocked/010-refused.md"
text = refused.read_text(encoding="utf-8") if refused.is_file() else ""
why = text.split("## Чому зупинилась")[-1].split("## Питання до власника")[0]
check("three-blocks: the reason names the unit and the three verdicts stand under it, in order, before the questions", r.returncode == 0
      and "overseer тричі поспіль відхилив один юніт (-|010-refused|unit 2)" in why
      and why.index("BLOCK 1 (2026-10-04T10:00:00Z, запит `r1`, перевірка #4): masked test gap") < why.index("BLOCK 2 (2026-10-04T10:05:00Z, запит `r2`): ДРУГА-ПРИЧИНА")
      < why.index("BLOCK 3 (2026-10-04T10:09:00Z, запит `r3`, перевірка #1): false DONE"), r.stderr + text)
check("…with one question that waits for the owner, and a journal entry", board.read(refused).answers == ("",) and "1. Три overseer-и поспіль" in text
      and "— 010-refused\n- Що сталося: overseer тричі поспіль" in (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8"), text)
put(root, "doing", "011-bare.md", task())
r = cli(root, "park", "011-bare", "three-blocks", "--verdicts", str(root / "no-such-marker.json"))
text = (root / "tasks/blocked/011-bare.md").read_text(encoding="utf-8")
check("the negative case: without a readable marker the task is still parked, with no verdict lines invented", r.returncode == 0
      and "overseer тричі поспіль" in text and "BLOCK 1" not in text, r.stderr + text)
r = cli(root, "park", "999-nowhere", "no-commit")
check("the negative cases: a task that is in neither doing/ nor todo/ is refused, and so is an unknown reason", r.returncode == 2
      and "neither" in r.stderr and cli(root, "park", "008-next", "because").returncode == 2 and (root / "tasks/todo/008-next.md").is_file(), r.stderr)
before = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
r = cli(root, "anomaly", "-", "ЩОСЬ-ДИВНЕ", "ПІШОВ-ДАЛІ")
after = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("anomaly: one more entry at the end, for the board as a whole, nothing above it changed", r.returncode == 0 and after.startswith(before)
      and re.search(r"\n## \S+Z — task board\n- Що сталося: ЩОСЬ-ДИВНЕ\n- Що зроблено: ПІШОВ-ДАЛІ\n- Хто записав: runner\n$", after) is not None, after)
# board 035: one journal for everything odd — the entry says who wrote it
r = cli(root, "anomaly", "008-next", "АГЕНТ-ПОБАЧИВ", "АГЕНТ-ЗРОБИВ", "--source", "агент")
after = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("anomaly --source: the agent's entry says the agent wrote it", r.returncode == 0
      and after.endswith("— 008-next\n- Що сталося: АГЕНТ-ПОБАЧИВ\n- Що зроблено: АГЕНТ-ЗРОБИВ\n- Хто записав: агент\n"), after)
put(root, "doing", "012-in-hand.md", task())
noted = board.note(root, "gates (gate.py)", "Gates-ЗДАЛИСЯ\nдругий рядок", "ХІД-ЗАКІНЧЕНО")
after = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("note (a hook, the gate): filed under the task in doing/, on one line, with its writer", noted == root / "tasks/ANOMALIES.md"
      and after.endswith("— 012-in-hand\n- Що сталося: Gates-ЗДАЛИСЯ другий рядок\n- Що зроблено: ХІД-ЗАКІНЧЕНО\n- Хто записав: gates (gate.py)\n"), after)
# board 712: the owner's session's task beside the runner's — the entry goes under the writer's own
put(root, "doing", "011-with-owner.md", attended_task())
kept_session = os.environ.pop("CLAUDE_UNATTENDED_SESSION", None)
os.environ["CLAUDE_UNATTENDED_SESSION"] = "1"
board.note(root, "hook x", "ДВІ-СТОРОНИ", "ДАЛІ")
check("note, two sides in doing/, the agent alone: filed under the agent's task, not under the board",
      "— 012-in-hand\n- Що сталося: ДВІ-СТОРОНИ" in (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8"), (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")[-300:])
check("…and audit_refusal there speaks of the agent's task only", "012-in-hand.md" in str(board.audit_refusal(root / "tasks")), board.audit_refusal(root / "tasks"))
del os.environ["CLAUDE_UNATTENDED_SESSION"]
board.note(root, "hook x", "З-ВЛАСНИКОМ", "ДАЛІ")
check("…in the owner's session: under the task the owner is working on",
      "— 011-with-owner\n- Що сталося: З-ВЛАСНИКОМ" in (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8"))
os.environ["CLAUDE_UNATTENDED_SESSION"] = "1"
(root / "tasks/doing/012-in-hand.md").unlink()
board.note(root, "hook x", "ЛИШЕ-ЗАДАЧА-ВЛАСНИКА", "ДАЛІ")
check("negative — the agent alone and only the owner's session's task in doing/: under the board, not under that task",
      "— task board\n- Що сталося: ЛИШЕ-ЗАДАЧА-ВЛАСНИКА" in (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8"))
del os.environ["CLAUDE_UNATTENDED_SESSION"]
if kept_session is not None:
    os.environ["CLAUDE_UNATTENDED_SESSION"] = kept_session
(root / "tasks/doing/011-with-owner.md").unlink()
board.note(root, "hook x", "БЕЗ-ЗАДАЧІ", "ДАЛІ")
check("…and under the board when no task is in doing/", "— task board\n- Що сталося: БЕЗ-ЗАДАЧІ" in (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8"))
nowhere = Path(tempfile.mkdtemp(prefix="board-none-"))
check("the negative case: a project without a board gets no journal and no tasks/ directory",
      board.note(nowhere, "hook x", "a", "b") is None and not (nowhere / "tasks").exists())
# board 035: the uncommitted work of a parked task is on a branch in origin, not only in a stash
put(root, "doing", "013-wip.md", task())
r = cli(root, "park", "013-wip", "no-commit", "--detail", "3", "--stash", "abc123", "--wip", "wip/013-wip/20261004T110524Z", "--wip-remote", "origin")
text = (root / "tasks/blocked/013-wip.md").read_text(encoding="utf-8")
journal = (root / "tasks/ANOMALIES.md").read_text(encoding="utf-8")
check("park --wip --wip-remote: the task file names the branch in origin, how to bring the work back, and the stash", r.returncode == 0
      and "у гілці `wip/013-wip/20261004T110524Z` в origin" in text and "git fetch origin wip/013-wip/20261004T110524Z && git cherry-pick -n FETCH_HEAD" in text
      and "git stash apply abc123" in text, text)
check("…and so does the journal", "у гілці `wip/013-wip/20261004T110524Z` в origin" in journal.split("\n## ")[-1], journal.split("\n## ")[-1])
put(root, "doing", "014-wip-local.md", task())
cli(root, "park", "014-wip-local", "no-commit", "--detail", "3", "--wip", "wip/014-wip-local/20261004T110524Z")
text = (root / "tasks/blocked/014-wip-local.md").read_text(encoding="utf-8")
check("the negative case: a branch that was not pushed is never said to be in origin", "лише на сервері runner-а" in text
      and "в origin (" not in text and "git push origin wip/014-wip-local/20261004T110524Z" in text, text)
check("the journal is not a task: next, summary and unblock do not see it", "ANOMALIES" not in cli(root, "summary").stdout + cli(root, "next").stdout)

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
(root / "loop").symlink_to("loop")  # a link to itself
r = cli(root, "audit-allowed", "--tasks-dir", str(root / "loop"))
check("--tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 718)",
      r.returncode == 1 and "paid audit not allowed: no task of this session is in" in r.stdout and "Traceback" not in r.stderr, r.stdout + r.stderr[-300:])
(root / "loop").unlink()

# --- an open item (board 037) ---------------------------------------------------------------------
print("an open item is a task of the board (board 037)")
root = new_board()
r = cli(root, "open-item", "--to", "blocked", "--key", "S9 cloud-probe", "--title", "Проба в хмарі", "--what", "потрібна хмарна сесія",
        "--question", "Запустити пробу?", "--source", "hook park-ask-gated.py")
item = root / r.stdout.strip()
text = item.read_text(encoding="utf-8") if r.returncode == 0 and item.is_file() else ""
check("--to blocked: 700-open-item-<key>.md in blocked/, with the question and an empty answer",
      r.stdout.strip() == "tasks/blocked/700-open-item-s9-cloud-probe.md" and board.read(item).answers == ("",)
      and "1. Запустити пробу?" in text and "Відкритий пункт: S9 cloud-probe\n" in text and "hook park-ask-gated.py" in text, r.stdout + r.stderr + text)
check("the summary shows it waiting for the owner", "чекає відповіді власника: 700-open-item-s9-cloud-probe.md — 1. Запустити пробу?" in cli(root, "summary").stdout)
r = cli(root, "open-item", "--to", "blocked", "--key", "S9 cloud-probe", "--title", "Ще раз", "--what", "те саме", "--question", "Інше питання?")
check("the same key while the task is open: that task, not a second one", r.stdout.strip() == "tasks/blocked/700-open-item-s9-cloud-probe.md"
      and len(list((root / "tasks/blocked").glob("*.md"))) == 1 and item.read_text(encoding="utf-8") == text, r.stdout)
r = cli(root, "open-item", "--to", "blocked", "--title", "Без питання", "--what", "щось")
check("negative — --to blocked without a question writes nothing and exits 1", r.returncode == 1 and len(list((root / "tasks/blocked").glob("*.md"))) == 1, r.stdout + r.stderr)
item.write_text(text.replace("Відповідь:", "Відповідь: запустити"), encoding="utf-8")
check("an answered item goes back to todo/ like every answered task", cli(root, "unblock").stdout.strip() == item.name and (root / "tasks/todo" / item.name).is_file())
r = cli(root, "open-item", "--to", "todo", "--title", "Вердикт не записано", "--what", "hook не побачив відповіді", "--do", "знайти причину")
work = root / r.stdout.strip()
check("--to todo: the next free number, no question, what to do in the task; `next` offers the lower number first",
      re.fullmatch(r"tasks/todo/701-open-item-\d{14}\.md", r.stdout.strip()) is not None
      and board.read(work).answers == () and "знайти причину" in work.read_text(encoding="utf-8") and cli(root, "next").stdout.strip().endswith(item.name), r.stdout + r.stderr)
r = cli(root, "open-item", "--to", "done", "--key", "C8b", "--title", "Прогін після переміщення", "--what", "чекав грошей", "--do", "закрито рішенням власника")
closed = root / r.stdout.strip()
check("--to done: a directory with task.md and report.md, and the reason in the report",
      r.stdout.strip() == "tasks/done/702-open-item-c8b/task.md" and "закрито рішенням власника" in (closed.parent / "report.md").read_text(encoding="utf-8")
      and 702 in board.Board(root / "tasks").numbers("done"), r.stdout + r.stderr)
r = cli(root, "open-item", "--to", "blocked", "--key", "C8b", "--title", "Знову", "--what", "відкрито знову", "--question", "Так?")
check("a key that only a done/ task carries opens a new item", r.stdout.strip() == "tasks/blocked/703-open-item-c8b.md", r.stdout)


def ask_gated(project: Path, command: str) -> str:
    """What the hook that parks an ask-gated command prints for `command` in `project`."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_UNATTENDED_SESSION"} | {"CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run([sys.executable, str(ROOT / ".claude/hooks/park-ask-gated.py")], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                          capture_output=True, text=True, check=False, env=env).stdout


# A push is not the example any more: since board 603 it is the hook's own rule, by environment
# (it asks attended, and the runner pushes itself) — tests/test_push_by_environment.py.
(root / ".claude/state/overseer").mkdir(parents=True)
check("negative — attended, the hook that parks an ask-gated command says nothing", ask_gated(root, "git rebase main") == "")
(root / ".claude/state/overseer/mode").write_text("unattended\n", encoding="utf-8")
said = json.loads(ask_gated(root, "git rebase main") or "{}").get("hookSpecificOutput", {})
check("unattended it still denies the command, and now sends the agent to the board, not to a line in parked.md",
      said.get("permissionDecision") == "deny" and "board.py open-item --to blocked" in said.get("permissionDecisionReason", "")
      and "Append a PARKED entry" not in said.get("permissionDecisionReason", ""), said)
check("…and a command outside the ask list is still not its business", ask_gated(root, "git status") == "")
bare = Path(tempfile.mkdtemp(prefix="board-none-"))
r = cli(bare, "open-item", "--to", "blocked", "--title", "Немає task board", "--what", "x", "--question", "Так?")
check("negative — a project without tasks/: exit 1, nothing is created", r.returncode == 1 and not (bare / "tasks").exists(), r.stdout + r.stderr)

# --- board 065: two files with one number in a column ------------------------------------------
print("two files with one number (board 065)")
root = new_board()
b = board.Board(root / "tasks")
inbox = root / "inbox"
inbox.mkdir()
GATE_Q = "Ескалація gates: {}\n\n## Питання до власника\n1. Закрити ескалацію?\n   Відповідь:{}\n"
first = put(root, "blocked", "900-gate-escalation-20261006T212543Z.md", GATE_Q.format("2026-10-06T21:25:43Z", ""))
second = put(root, "blocked", "900-gate-escalation-20261007T074013Z.md", GATE_Q.format("2026-10-07T07:40:13Z", ""))
kept = second.read_text(encoding="utf-8")
(inbox / first.name).write_text(GATE_Q.format("2026-10-06T21:25:43Z", " так"), encoding="utf-8")
r = cli(root, "import-inbox", str(inbox))
check("an answer to one of two same-numbered questions replaces that file only", f"{first.name} answered" in r.stdout
      and "Відповідь: так" in first.read_text(encoding="utf-8") and not (inbox / first.name).exists(), r.stdout + r.stderr)
check("…the other question with the same number is still there, untouched", second.is_file() and second.read_text(encoding="utf-8") == kept)
stray = inbox / "900-gate-escalation.md"
stray.write_text(GATE_Q.format("2026-10-07T07:40:13Z", " так"), encoding="utf-8")
before = {q.name: q.read_text(encoding="utf-8") for q in b.files("blocked")}
r = cli(root, "import-inbox", str(inbox))
journal = (root / "tasks" / board.ANOMALIES).read_text(encoding="utf-8") if (root / "tasks" / board.ANOMALIES).is_file() else ""
check("no exact name among two same-numbered files: nothing is deleted, the file stays in the inbox",
      f"{stray.name} skipped" in r.stdout and stray.is_file() and {q.name: q.read_text(encoding="utf-8") for q in b.files("blocked")} == before, r.stdout + r.stderr)
check("…and the anomaly journal names the file and both candidates", stray.name in journal and first.name in journal and second.name in journal
      and "Хто записав: task board (import-inbox)" in journal, journal)
cli(root, "import-inbox", str(inbox))
check("…the same file left in the inbox is written to the journal once, not at every intake",
      bool(journal) and (root / "tasks" / board.ANOMALIES).read_text(encoding="utf-8") == journal)
stray.unlink()
put(root, "todo", "020-one.md", "one\n")
put(root, "todo", "020-two.md", "two\n")
(inbox / "020-two.md").write_text("two, newer\n", encoding="utf-8")
(inbox / "020-three.md").write_text("three\n", encoding="utf-8")
r = cli(root, "import-inbox", str(inbox))
check("todo/ with two files of one number: the exact name is replaced, another name replaces nothing",
      (root / "tasks/todo/020-one.md").read_text(encoding="utf-8") == "one\n" and (root / "tasks/todo/020-two.md").read_text(encoding="utf-8") == "two, newer\n"
      and not (root / "tasks/todo/020-three.md").exists() and (inbox / "020-three.md").is_file() and "020-three.md skipped" in r.stdout, r.stdout + r.stderr)
r = cli(root, "summary")
check("summary shows both duplicates as an error, with the column and the names",
      f"ПОМИЛКА: один номер 900 у двох файлах у blocked/: {first.name}, {second.name}" in r.stdout
      and "ПОМИЛКА: один номер 020 у двох файлах у todo/: 020-one.md, 020-two.md" in r.stdout, r.stdout)
r = cli(root, "check")
check("check exits 1 and prints the same errors", r.returncode == 1 and r.stdout.count("ПОМИЛКА") == 2, r.stdout + r.stderr)
root = new_board()
put(root, "todo", "020-one.md", task())
put(root, "blocked", "020-one.md", task(questions=q_open))
done(root, "020-one")
done(root, "021-two")
r = cli(root, "check")
check("negative — one number in different columns is not this error: check exits 0, summary has no error line",
      r.returncode == 0 and r.stdout == "" and "ПОМИЛКА" not in cli(root, "summary").stdout, r.stdout + r.stderr)
done(root, "021-twin")
r = cli(root, "check")
check("done/ is a column too: two folders with one number", r.returncode == 1 and "у done/: 021-twin, 021-two" in r.stdout, r.stdout)

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
      [h for h in ("# ", "Залежить від:", "Потрібна присутність власника: ні", "Аудит потрібен: ні", "## Що зробити", "## Готово, коли", "## Питання до власника", "Відповідь:")
       if h in template] == ["# ", "Залежить від:", "Потрібна присутність власника: ні", "Аудит потрібен: ні", "## Що зробити", "## Готово, коли", "## Питання до власника", "Відповідь:"]
      and template.index("Залежить від:") < template.index("Потрібна присутність власника:") < template.index("Аудит потрібен:") < template.index("## Що зробити")
      < template.index("## Готово, коли") < template.index("## Питання до власника") < template.index("Відповідь:"), template)
parsed = board.parse(template)
check("the template itself parses: no dependency, no audit, not attended, no open question",
      parsed.depends == () and not parsed.audit and not parsed.attended and parsed.answers == (), parsed)
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
short = short[short.index("## The task board and extra sessions"):short.index("## Constitution")]
MANUAL = {
    "which task: the first in todo/ with its dependencies in done/": ("першу в черзі задачу з `todo/`", "залежності вже в `done/`"),
    "…moved to doing/ in a commit of its own — or already there when the runner started you": ("окремим commit-ом", "вже лежить задача"),
    "…one task in doing/ at a time": ("одночасно лише одна твоя задача",),
    "through the pipeline: big by /feature-architect, small in one slice": ("/feature-architect", "одним slice-ом"),
    "small decisions are the agent's, recorded in the report": ("Рішення, які я ухвалив сам",),
    "the owner is needed: a question, blocked/, the next task": ("допиши питання", "`blocked/`", "берись за наступну"),
    "a design-first task ends with a design and questions; building is another task": ("спершу проєкт", "лише окремою задачею"),
    "the report: what changed for the owner, a one-minute demonstration, cost, commits, deferred": (
        "Що змінилось для власника", "демонстрація на хвилину", "витрати", "діапазон commit-ів", "відкладене"),
    "then the task goes to done/NNN-name/ with task.md and report.md": ("`done/NNN-назва/`", "`task.md`", "`report.md`"),
    "a gate question is the owner's to answer and the runner's to close (board 005)": (
        "9NN-gate-escalation", "не заповнюй", "закриття ескалації не запускай", "Номери від 900"),
    "an action the owner approves is the runner's to take, from a short list (board 008)": (
        "action-line apply-settings", "Відповідь «так» виконує runner", "Сам команду не запускай",
        "застосувати пропозицію налаштувань, зробити урок правилом, закрити ескалацію gates"),
    "consent has one form: exactly the one word «так»; anything else is an instruction (board 036)": (
        "## Одна форма згоди", "рівно одне слово `так`", "регістр і розділові знаки не важать", "«так, але…»",
        "застосовується, задача йде агентові", "«Закрити ескалацію?»", "рівно одне слово «так»; будь-яка інша відповідь", "`/owner-review`"),
    "a lesson becomes a rule only on the owner's answer (board 040)": (
        "Урок робить правилом лише власник", "`lesson_queue.py promote` не запускай", "8NN-rule-proposal", "Номери від 800",
        "зробити урок правилом"),
    "a task that needs the owner present is never the runner's; how to do one with the owner (board 016)": (
        "Потрібна присутність власника: так", "Runner її не бере ніколи", "next --attended", "start --attended",
        "Задачу з присутнім власником сам не бери"),
    "the owner's answers go first; an attended task in doing/ does not stop the runner (board 049)": (
        "## Відповіді власника — першими", "першою після поточної", "`tasks/.first`", "у роботі з власником", "бере наступні задачі"),
    "board 078: extra sessions are ordinary work, booked per task; the audit run stays the owner's": (
        "## Додаткові сесії Claude", "Окремої згоди на них не треба", "extra-sessions.jsonl", "Аудит потрібен: так", "--owner-approved"),
    "the full suite once, at the end of a task; the fast one after a slice": ("один раз, наприкінці задачі", "лише швидкий набір"),
}
for rule, phrases in MANUAL.items():
    missing = [ph for ph in phrases if ph not in seed]
    check(f"manual: {rule}", not missing, missing)
check("this repository's manual carries every rule of the seed (it may only have grown)",
      all(ph in here for phrases in MANUAL.values() for ph in phrases))
SHORT = ("`tasks/README.md`", "`todo/`", "dependencies in `done/`", "`doing/` in its own commit", "`done/NNN-name/`", "`report.md`",
         "`blocked/`", "question for the owner", "Extra Claude sessions", "ordinary work", "`Аудит потрібен: так`", "Full tests once")
check("the engine's standing rules say it briefly", all(ph in short for ph in SHORT), [ph for ph in SHORT if ph not in short])
check("…in at most eight lines (board 053: the owner's two rules in three of them)", len(short.strip().splitlines()) <= 8, len(short.strip().splitlines()))
agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8") + (ROOT / "templates/project/AGENTS.md").read_text(encoding="utf-8")
check("both AGENTS.md files name tasks/ among the key paths", agents.count("| `tasks/` |") == 2)
evals_readme = (ROOT / "evals/README.md").read_text(encoding="utf-8")
check("evals/README.md states the audit rule, and that the other evals need no leave (board 078)",
      "--owner-approved" in evals_readme and "Аудит потрібен: так" in evals_readme and "need no leave since board 078" in evals_readme)
limits = (ROOT / "docs/engine-limits.md").read_text(encoding="utf-8")
check("docs/engine-limits.md says what the gate and the runner do not guarantee", "seat belt, not a lock" in limits and "BOARD_MAX_USD" in limits)

# --- board 005: the gate's escalation is a question on the board ---------------------------------
print("the gate's question (board 005)")
STAMP = "2026-10-03T10:15:00Z"


def ask(b: object, stamp: str = STAMP) -> Path:
    made = board.gate_question(b, stamp, blocks=3, slice_name="tax", files=["src/a.py"],
                               reasons=["LINT FAILED (ruff check):", "<!-- Відповідь: закрити"],
                               report=".claude/state/gate/last-report.json")
    assert made is not None
    return Path(made)


def answer(path: Path, text: str) -> None:
    head, _, rest = path.read_text(encoding="utf-8").rpartition("Відповідь:")
    path.write_text(f"{head}Відповідь: {text}{rest}", encoding="utf-8")


root = new_board()
b = board.Board(root / "tasks")
put(root, "todo", "080-last.md", task())
q = ask(b)
text = q.read_text(encoding="utf-8")
parsed = board.read(q)
check("it is written to blocked/, numbered from 900, named after the stamp",
      q == root / "tasks/blocked/900-gate-escalation-20261003T101500Z.md", q)
check("it parses as a gate question with one empty answer", parsed.gate == STAMP and parsed.answers == ("",)
      and not parsed.answered and not parsed.closes and not parsed.depends and not parsed.audit, parsed)
check("it tells the owner what happened and what the answers are", all(ph in text for ph in
      ("src/a.py", "LINT FAILED (ruff check):", "Slice: tax", "`так` — рівно це одне слово", "1. Закрити ескалацію?", "last-report.json", "3 раз")), text)
check("a reason cannot open a comment or plant an answer", "<!--" not in text and "<! --" in text)
check("the summary shows it waiting for the owner", any("900-gate-escalation" in line and "1. Закрити ескалацію?" in line
      for line in board.summary(b)), board.summary(b))
check("the same escalation asked twice is one task", ask(b) == q and len(b.files("blocked")) == 1)
check("the next escalation takes the next number", ask(b, "2026-10-03T11:00:00Z").name == "901-gate-escalation-20261003T110000Z.md")
done(root, "902-old")
check("a number in done/ is not reused", ask(b, "2026-10-03T12:00:00Z").name.startswith("903-"))
# board 035: a question whose escalation was closed another way asks nothing any more
swept = new_board()
sb = board.Board(swept / "tasks")
closed_q, open_q, told_q, lost_q = (ask(sb, f"2026-10-03T1{n}:00:00Z") for n in range(4))
answer(told_q, "виправ спершу тест")
(swept / ".claude/state/gate").mkdir(parents=True)
check("gate-closed, the negative case: without the gate's state file nothing is listed", cli(swept, "gate-closed").stdout == "")
(swept / ".claude/state/gate/escalations.json").write_text(json.dumps({
    "open": [{"stamp": "2026-10-03T11:00:00Z"}],
    "closed": [{"stamp": "2026-10-03T10:00:00Z"}, {"stamp": "2026-10-03T12:00:00Z"}]}), encoding="utf-8")
check("gate-closed: only the unanswered question whose escalation is recorded as closed — not the open one, not the one "
      "with the owner's instruction, not the one the state does not know",
      cli(swept, "gate-closed").stdout == f"{closed_q.name}\t2026-10-03T10:00:00Z\n", cli(swept, "gate-closed").stdout)
r = cli(swept, "gate-done", closed_q.name, "elsewhere")
report = (swept / "tasks/done" / closed_q.stem / "report.md").read_text(encoding="utf-8") if r.returncode == 0 else ""
check("gate-done elsewhere: the question goes to done/ with a report that says it was closed another way, not on an answer",
      not closed_q.exists() and (swept / "tasks/done" / closed_q.stem / "task.md").is_file() and "закрито іншим шляхом" in report
      and "2026-10-03T10:00:00Z" in report and "ваша відповідь" not in report, r.stderr + report)
bare = Path(tempfile.mkdtemp(prefix="board-none-"))
check("a project without a board gets no task and no tasks/ directory",
      board.gate_question(board.Board(bare / "tasks"), STAMP, 3, "(none)", [], [], "r") is None and not (bare / "tasks").exists())

# Board 036: one form of consent — exactly the one word «так», whatever its case and punctuation.
for given, closes in (("так", True), ("Так.", True), ("«ТАК»!", True), ("`так`", True), ("  **так**  ", True),
                      ("так, але спершу виправ", False), ("так — виправлено", False), ("так так", False), ("закрити", False),
                      ("Закрити.", False), ("не закривати", False), ("такий", False), ("yes", False), ("", False)):
    root = new_board()
    b = board.Board(root / "tasks")
    q = ask(b)
    answer(q, given)
    check(f"answer «{given}»: closes={closes}", board.read(q).closes is closes, board.read(q))
plain = put(root, "blocked", "005-plain.md", task(questions="1. Так?\n   Відповідь: так\n"))
check("«так» under an ordinary task closes nothing and approves nothing: it is an answer like any other", not board.read(plain).approves and not board.read(plain).decided
      and board.read(plain).answered)
check("«так» under an ordinary task closes nothing", not board.read(plain).closes)

root = new_board()
b = board.Board(root / "tasks")
q, other = ask(b), ask(b, "2026-10-03T11:00:00Z")
answer(q, "так")
answer(other, "виправ тест test_a і спитай ще раз")
out = cli(root, "gate-answers").stdout.splitlines()
check("gate-answers lists the «так» one: name, stamp, sha256",
      len(out) == 1 and out[0].split("\t")[:2] == [q.name, STAMP] and len(out[0].split("\t")[2]) == 64, out)
moved = board.unblock(b)
check("unblock leaves «так» to the runner and sends an instruction back to todo/",
      moved == [other.name] and q.is_file() and (root / "tasks/todo" / other.name).is_file(), moved)
again = root / "tasks/blocked" / other.name
(root / "tasks/todo" / other.name).rename(again)
again.write_text(again.read_text(encoding="utf-8") + "Тепер закрити ескалацію?\nВідповідь: Так.\n", encoding="utf-8")
check("an instruction first, «так» to the second question: it closes", board.read(again).closes, board.read(again))

r = cli(root, "gate-reject", q.name)
rejected = board.read(q)
check("gate-reject wipes the answer and says why under the question", r.returncode == 0 and rejected.answers == ("",)
      and not rejected.closes and "Примітка runner-а" in q.read_text(encoding="utf-8"), q.read_text(encoding="utf-8"))
check("...and the question is open again in the summary", any(q.name in line and "чекає відповіді" in line for line in board.summary(b)))
answer(q, "так")
r = cli(root, "gate-done", q.name, "closed")
target = root / "tasks/done" / q.stem
check("gate-done: done/NNN-name/ with task.md (the answer in it) and report.md", r.returncode == 0 and not q.exists()
      and "Відповідь: так" in (target / "task.md").read_text(encoding="utf-8")
      and STAMP in (target / "report.md").read_text(encoding="utf-8")
      and "Що змінилось для власника" in (target / "report.md").read_text(encoding="utf-8"), r.stdout + r.stderr)
r = cli(root, "gate-done", again.name, "absent")
check("gate-done absent: the report says it was not open", r.returncode == 0
      and "вже не була відкрита" in (root / "tasks/done" / again.stem / "report.md").read_text(encoding="utf-8"), r.stderr)
check("gate-done and gate-reject refuse a task that is not a gate question", cli(root, "gate-done", "005-plain.md", "closed").returncode == 2
      and cli(root, "gate-reject", "../todo/x.md").returncode == 2)

# --- board 008: an action offered under a question, approved with «так» --------------------------
print("the owner's action (board 008)")
root = new_board()
b = board.Board(root / "tasks")
(root / "docs/tasks").mkdir(parents=True)
(root / "docs/tasks/settings.json").write_text("{}\n")
SHA = "44136fa355b3678a1138e166b3d48e7b6f1d7a3b1a7d7e6c0f2e5d1d9a6d3c1e"  # any 64 hex digits
offer = cli(root, "action-line", "apply-settings").stdout.strip()
check("action-line prints the offer with the sha256 of the proposal as it is now",
      offer == "Дія runner-а: apply-settings ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356", offer)


def offered(name: str, line: str, reply: str = "") -> Path:
    return put(root, "blocked", name, task(questions=f"1. Застосувати пропозицію налаштувань?\n   {line}\n   Відповідь:{' ' + reply if reply else ''}\n"))


t = board.read(offered("008-wiring.md", offer))
check("the offer is parsed: the action and its sha256; unanswered, it approves nothing",
      t.action == "apply-settings" and t.action_arg == offer.split()[-1] and not t.approves and not t.answered, t)
check("the summary shows the question, not the offer line", any("008-wiring.md — 1. Застосувати пропозицію налаштувань?" in line for line in board.summary(b)), board.summary(b))
check("unanswered: owner-actions lists nothing", cli(root, "owner-actions").stdout == "")
for reply, yes in (("так", True), ("Так.", True), ("«так»", True), ("ТАК!", True), ("так, застосуй", False), ("так, але не все", False), ("ні", False), ("закрити", False),
                   ("такий варіант не годиться", False)):
    check(f"the answer {reply!r} {'approves' if yes else 'does not approve'}", board.read(offered("008-wiring.md", offer, reply)).approves is yes)
for line, why in ((f"Дія runner-а: run-script {SHA}", "an action that is not on the list"), ("Дія runner-а: close-escalation", "the gate's action offered by hand"),
                  ("Дія: apply-settings", "another wording")):
    t = board.read(offered("008-wiring.md", line, "так"))
    check(f"{why} is no offer: an ordinary answered task", t.action == "" and not t.approves and t.answered, t)
header = put(root, "blocked", "007-header.md", task().replace("Аудит потрібен: ні", f"Аудит потрібен: ні\n{offer}") + "1. Так?\n   Відповідь: так\n")
check("an offer outside the questions section is not one", board.read(header).action == "")
header.unlink()
q = offered("008-wiring.md", offer, "так")
out = cli(root, "owner-actions").stdout.splitlines()
check("owner-actions lists it: name, action, sha256 of the proposal, sha256 of the task",
      len(out) == 1 and out[0].split("\t")[:3] == [q.name, "apply-settings", offer.split()[-1]] and len(out[0].split("\t")[3]) == 64, out)
check("gate-answers does not list it, and it is no gate question", cli(root, "gate-answers").stdout == "" and cli(root, "gate-done", q.name, "closed").returncode == 2)
check("unblock leaves «так» to the runner", board.unblock(b) == [] and q.is_file())
r = cli(root, "action-reject", q.name)
text = q.read_text(encoding="utf-8")
check("action-reject wipes the answer, says why, keeps the offer", r.returncode == 0 and board.read(q).answers == ("",) and board.read(q).action == "apply-settings"
      and "відповідь «так» з'явилася на сервері" in text, text)
answer(q, "так")
for outcome, said in (("stale", "sha256"), ("failed", "попередній"), ("applied", "Дію виконано")):
    q = offered("008-wiring.md", offer, "так")
    r = cli(root, "action-done", q.name, outcome)
    t, text = board.read(q), q.read_text(encoding="utf-8")
    check(f"action-done {outcome}: the offer is replaced by the outcome, the answer stays", r.returncode == 0 and t.action == "" and not t.approves
          and t.answers == ("так",) and said in text and "Дія runner-а:" not in text, text)
check("…so the same «так» cannot run the action twice, and the task returns to todo/", cli(root, "owner-actions").stdout == ""
      and board.unblock(b) == [q.name] and (root / "tasks/todo" / q.name).is_file())
plain = put(root, "blocked", "005-plain.md", task(questions="1. Так?\n   Відповідь: так\n"))
check("action-done and action-reject refuse a task that offers no action", cli(root, "action-done", plain.name, "applied").returncode == 2
      and cli(root, "action-reject", plain.name).returncode == 2 and cli(root, "action-done", "../todo/008-wiring.md", "applied").returncode == 2)
check("action-line refuses an action that is not on the list", cli(root, "action-line", "run-script").returncode == 2)

# --- board 040: a lesson becomes a rule only on the owner's word ----------------------------------
print("the rule question (board 040)")
root = new_board()
b = board.Board(root / "tasks")
RULE_SHA = "a" * 64
q = board.rule_question(b, "ab12cd34", "Show the RED before the GREEN. <!-- x -->", "audit 06\ncaught it twice", "lesson #ab12cd34", "", RULE_SHA)
text = q.read_text(encoding="utf-8")
t = board.read(q)
check("rule_question writes tasks/blocked/800-rule-proposal-<id>.md", q == root / "tasks/blocked/800-rule-proposal-ab12cd34.md", q)
check("…the exact rule on one line, the reason, «немає» where the overseer said nothing",
      "  > Show the RED before the GREEN. <! -- x -->\n" in text and "- Чому: audit 06 caught it twice\n" in text and "- Рекомендація overseer-а: немає\n" in text, text)
check("…parsed: the proposal, the offer and its sha256, one empty answer; it asks for no paid audit",
      t.rule == "ab12cd34" and t.action == "promote-rule" and t.action_arg == RULE_SHA and t.answers == ("",) and not t.audit and not t.decided, t)
check("the summary shows the question to the owner", any("800-rule-proposal-ab12cd34.md — 1. Зробити це правилом?" in line for line in board.summary(b)), board.summary(b))
check("a second call for the same proposal writes nothing new", board.rule_question(b, "ab12cd34", "Other text.", "w", "o", "", "b" * 64) == q
      and q.read_text(encoding="utf-8") == text)
second = board.rule_question(b, "ffff0000", "Another rule.", "w", "o", "так: варто", "c" * 64)
check("the next proposal takes the next free number; the overseer's recommendation is shown",
      second.name == "801-rule-proposal-ffff0000.md" and "- Рекомендація overseer-а: так: варто\n" in second.read_text(encoding="utf-8"), second.name)
bare = Path(tempfile.mkdtemp(prefix="board-none-"))
check("a project without a board gets no question", board.rule_question(board.Board(bare / "tasks"), "ab12cd34", "r", "w", "o", "", RULE_SHA) is None and not (bare / "tasks").exists())
check("unanswered: owner-actions lists nothing, unblock moves nothing", cli(root, "owner-actions").stdout == "" and board.unblock(b) == [])
for reply, decided in (("так", "promote-rule"), ("Так.", "promote-rule"), ("«так»", "promote-rule"), ("ні", "reject-rule"), ("Ні.", "reject-rule"),
                       ("так, але коротше", ""), ("ні, перепиши", ""), ("такий текст не годиться", ""), ("закрити", "")):
    q.write_text(text, encoding="utf-8")
    answer(q, reply)
    check(f"the answer {reply!r}: {decided or 'an instruction for the agent, nothing for the runner'}", board.read(q).decided == decided, board.read(q))
check("an answer that is an instruction goes back to todo/ like any answered task", board.unblock(b) == [q.name])
(root / "tasks/todo" / q.name).rename(q)
for reply, action, said in (("так", "promote-rule", "правило додано"), ("ні", "reject-rule", "пропозицію закрито")):
    q.write_text(text, encoding="utf-8")
    answer(q, reply)
    out = cli(root, "owner-actions").stdout.splitlines()
    check(f"«{reply}»: owner-actions lists {action} with the sha256 of the rule; unblock leaves it to the runner",
          len(out) == 1 and out[0].split("\t")[:3] == [q.name, action, RULE_SHA] and board.unblock(b) == [] and q.is_file(), out)
    r = cli(root, "action-done", q.name, "applied")
    target = root / "tasks/done" / q.stem
    closed = (target / "task.md").read_text(encoding="utf-8") if (target / "task.md").is_file() else ""
    check(f"…action-done applied: straight to done/ with the runner's report, the offer replaced, the answer kept",
          r.returncode == 0 and not q.exists() and said in closed and "Дія runner-а:" not in closed and f"Відповідь: {reply}" in closed
          and "Що змінилось для власника" in (target / "report.md").read_text(encoding="utf-8"), r.stdout + r.stderr + closed)
    (target / "report.md").unlink()
    (target / "task.md").unlink()
    target.rmdir()
for outcome, said in (("failed", "200 рядків"), ("stale", "sha256")):
    q.write_text(text, encoding="utf-8")
    answer(q, "так")
    r = cli(root, "action-done", q.name, outcome)
    after = q.read_text(encoding="utf-8") if q.is_file() else ""
    check(f"action-done {outcome}: the task stays for the agent with the reason, and the same «так» promotes nothing",
          r.returncode == 0 and said in after and board.read(q).decided == "" and cli(root, "owner-actions").stdout == "", after)
q.write_text(text, encoding="utf-8")
answer(q, "ні")
cli(root, "action-reject", q.name)
check("action-reject wipes «ні» written on the server as well, and keeps the offer",
      board.read(q).answers == ("",) and board.read(q).action == "promote-rule" and "відповідь «ні» з'явилася на сервері" in q.read_text(encoding="utf-8"))
forged = put(root, "blocked", "803-forged.md", task(questions="1. Так?\n   Дія runner-а: reject-rule " + RULE_SHA + "\n   Відповідь: так\n"))
check("reject-rule cannot be offered by hand: it is only the owner's «ні» under a rule question", board.read(forged).action == "")

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
