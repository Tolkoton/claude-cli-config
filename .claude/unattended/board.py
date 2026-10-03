#!/usr/bin/env python3
"""The task board in files: the one reader of tasks/ (package board).

The board is four directories under tasks/ — todo/, doing/, blocked/, done/. A task is one
file `NNN-name.md`; the number is its place in the queue. Under the title it carries two plain
lines, `Залежить від:` (task numbers) and `Аудит потрібен: так|ні`, and its last section,
`## Питання до власника`, holds questions, each with an `Відповідь:` line. A finished task is
a directory done/NNN-name/ with task.md and report.md. tasks/README.md is the manual.

This module parses a task and makes every move that needs a decision, so that "which task is
next", "is it answered" and "does it ask for the paid audit" are decided in one place for the
runner (board-runner.sh), for the audit runner (evals/run_audit_scenarios.py) and for a person.
It never runs git: staging and committing belong to the runner and to the agent.

    board.py next                    the task to work on: the one in doing/, else the first in
                                     todo/ whose dependencies are all in done/.
                                     exit 3: todo/ is empty; exit 4: tasks wait, none is eligible
    board.py start <todo file>       move it to doing/ (refused while doing/ holds a task)
    board.py where <NNN-name>        todo | doing | blocked | done | missing
    board.py import-inbox <dir>      take new task files in (see `import_inbox`)
    board.py unblock                 blocked/ tasks whose every answer is filled go back to todo/
    board.py audit-allowed           exit 0 only when the one task in doing/ asks for the audit
    board.py summary                 the board in a dozen lines, for the owner

`--root DIR` names the repository (default: the one this file is installed in).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ("todo", "doing", "blocked", "done")
TASK_NAME = re.compile(r"^(\d{3,})-.+\.md$")
DONE_NAME = re.compile(r"^(\d{3,})-.+$")
DEPENDS = re.compile(r"^Залежить від:(.*)$", re.MULTILINE)
AUDIT = re.compile(r"^Аудит потрібен:\s*(\S+)", re.MULTILINE)
QUESTIONS = re.compile(r"^##\s+Питання до власника\s*$", re.MULTILINE)
HEADING = re.compile(r"^##\s", re.MULTILINE)
ANSWER = re.compile(r"^[\s>*_-]*Відповідь:[*_]*[ \t]*(.*)$", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
EXIT_REFUSED, EXIT_TODO_EMPTY, EXIT_NONE_ELIGIBLE = 2, 3, 4


@dataclass(frozen=True)
class Task:
    depends: tuple[int, ...]
    audit: bool
    questions: str
    answers: tuple[str, ...]

    @property
    def answered(self) -> bool:
        """Every question has its answer — and there is at least one: a task that asks nothing
        was answered by nobody."""
        return bool(self.answers) and all(self.answers)


def parse(text: str) -> Task:
    text = COMMENT.sub("", text)
    first_heading = HEADING.search(text)
    header = text[: first_heading.start()] if first_heading else text
    depends = DEPENDS.search(header)
    audit = AUDIT.search(header)
    section = QUESTIONS.search(text)
    questions = ""
    if section:
        rest = text[section.end():]
        following = HEADING.search(rest)
        questions = rest[: following.start()] if following else rest
    return Task(
        depends=tuple(int(n) for n in re.findall(r"\d+", depends.group(1))) if depends else (),
        audit=audit is not None and audit.group(1).strip(".,;*_").lower() == "так",
        questions=questions.strip(),
        answers=tuple(a.strip() for a in ANSWER.findall(questions)),
    )


def number_of(name: str) -> int | None:
    match = TASK_NAME.match(name) or DONE_NAME.match(name)
    return int(match.group(1)) if match else None


def read(path: Path) -> Task:
    return parse(path.read_text(encoding="utf-8"))


class Board:
    def __init__(self, tasks: Path) -> None:
        self.tasks = tasks

    def files(self, column: str) -> list[Path]:
        """The task files of todo/, doing/ or blocked/, lowest number first."""
        found = [p for p in (self.tasks / column).glob("*.md") if p.is_file() and TASK_NAME.match(p.name)]
        return sorted(found, key=lambda p: (number_of(p.name) or 0, p.name))

    def done(self) -> list[Path]:
        folder = self.tasks / "done"
        found = [p for p in folder.iterdir() if p.is_dir() and DONE_NAME.match(p.name)] if folder.is_dir() else []
        return sorted(found, key=lambda p: (number_of(p.name) or 0, p.name))

    def numbers(self, column: str) -> set[int]:
        paths = self.done() if column == "done" else self.files(column)
        return {n for p in paths if (n := number_of(p.name)) is not None}

    def unmet(self, task: Task) -> list[int]:
        finished = self.numbers("done")
        return [n for n in task.depends if n not in finished]

    def eligible(self) -> Path | None:
        return next((p for p in self.files("todo") if not self.unmet(read(p))), None)

    def shown(self, path: Path) -> str:
        return path.relative_to(self.tasks.parent).as_posix()

    def with_number(self, column: str, number: int) -> list[Path]:
        return [p for p in self.files(column) if number_of(p.name) == number]


def cmd_next(board: Board) -> int:
    doing = board.files("doing")
    if len(doing) > 1:
        print("board: tasks/doing/ holds more than one task (" + ", ".join(p.name for p in doing)
              + ") — one at a time; move the extra ones back to tasks/todo/", file=sys.stderr)
        return EXIT_REFUSED
    if doing:
        print(board.shown(doing[0]))
        return 0
    task = board.eligible()
    if task is None:
        return EXIT_NONE_ELIGIBLE if board.files("todo") else EXIT_TODO_EMPTY
    print(board.shown(task))
    return 0


def cmd_start(board: Board, root: Path, given: str) -> int:
    source = (root / given).resolve() if not Path(given).is_absolute() else Path(given).resolve()
    if source.parent != (board.tasks / "todo").resolve() or not source.is_file() or not TASK_NAME.match(source.name):
        print(f"board: {given} is not a task file in tasks/todo/", file=sys.stderr)
        return EXIT_REFUSED
    doing = board.files("doing")
    if doing:
        print(f"board: tasks/doing/ already holds {doing[0].name} — one task at a time", file=sys.stderr)
        return EXIT_REFUSED
    target = board.tasks / "doing" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    print(board.shown(target))
    return 0


def cmd_where(board: Board, stem: str) -> int:
    stem = stem.removesuffix(".md")
    for column in ("todo", "doing", "blocked"):
        if (board.tasks / column / f"{stem}.md").is_file():
            print(column)
            return 0
    print("done" if (board.tasks / "done" / stem).is_dir() else "missing")
    return 0


def import_inbox(board: Board, inbox: Path) -> list[str]:
    """Move the task files of `inbox` onto the board. One line per file:

    imported  a new number: into todo/
    replaced  the number is in todo/: the inbox file takes its place (the owner's newer text)
    answered  the number is in blocked/ and the inbox copy has every answer filled: it replaces
              the blocked file — this is how an answer arrives without git; `unblock` then moves it
    skipped   the number is in doing/ or done/ (nothing there is ever touched), or in blocked/
              while the copy is not fully answered (it would wipe the questions). The file stays
              in the inbox.
    A file taken is REMOVED from the inbox: a copy left behind would come back as a new task
    after the real one reached done/.
    """
    lines: list[str] = []
    if not inbox.is_dir():
        return lines
    for source in sorted(inbox.glob("*.md"), key=lambda p: (number_of(p.name) or 0, p.name)):
        number = number_of(source.name) if TASK_NAME.match(source.name) else None
        if number is None or not source.is_file():
            continue
        content = source.read_bytes()
        busy = next((c for c in ("doing", "done") if number in board.numbers(c)), None)
        blocked = board.with_number("blocked", number)
        if busy:
            lines.append(f"{source.name} skipped: {number:03d} is in {busy}/")
            continue
        if blocked:
            if not parse(content.decode("utf-8", "replace")).answered:
                lines.append(f"{source.name} skipped: {number:03d} is in blocked/ and this copy does not answer every question")
                continue
            column, verb, old = "blocked", "answered", blocked
        else:
            old = board.with_number("todo", number)
            column, verb = "todo", "replaced" if old else "imported"
        for path in old:
            path.unlink()
        target = board.tasks / column / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        source.unlink()
        lines.append(f"{source.name} {verb}: tasks/{column}/{source.name}")
    return lines


def unblock(board: Board) -> list[str]:
    moved: list[str] = []
    for path in board.files("blocked"):
        if read(path).answered:
            target = board.tasks / "todo" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            path.rename(target)
            moved.append(path.name)
    return moved


def audit_refusal(tasks: Path) -> str | None:
    """Why a paid audit may NOT start for the work in hand; None when the task in doing/ asks for it."""
    doing = Board(tasks).files("doing")
    if not doing:
        return f"no task is in {tasks}/doing/"
    if len(doing) > 1:
        return f"{tasks}/doing/ holds more than one task: " + ", ".join(p.name for p in doing)
    if not read(doing[0]).audit:
        return f"the task in doing/, {doing[0].name}, does not say «Аудит потрібен: так»"
    return None


def first_open_question(task: Task) -> str:
    """The text of the first question whose answer is empty, for the summary."""
    lines = task.questions.splitlines()
    for index, line in enumerate(lines):
        answer = ANSWER.match(line)
        if answer and not answer.group(1).strip():
            asked = [text.strip() for text in lines[:index] if text.strip() and not ANSWER.match(text)]
            return asked[-1] if asked else "(питання без тексту)"
    return "(питань не записано)"


def summary(board: Board) -> list[str]:
    todo, doing, blocked, done = board.files("todo"), board.files("doing"), board.files("blocked"), board.done()
    known = {n for column in COLUMNS for n in board.numbers(column)}
    lines = [f"todo: {len(todo)}   doing: {len(doing)}   blocked: {len(blocked)}   done: {len(done)}"]
    lines += [f"в роботі: {p.name}" for p in doing]
    for path in blocked:
        lines.append(f"чекає відповіді власника: {path.name} — {first_open_question(read(path))}")
    for path in todo:
        unmet = board.unmet(read(path))
        if unmet:
            waits = ", ".join(f"{n:03d}" + ("" if n in known else " (такої задачі ніде немає)") for n in unmet)
            lines.append(f"чекає на залежності: {path.name} — {waits}")
    task = board.eligible() if not doing else None
    if task:
        lines.append(f"наступна: {task.name}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="The task board in files (tasks/README.md).")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="the repository that holds tasks/ (default: the one this file is in)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("next")
    commands.add_parser("start").add_argument("task")
    commands.add_parser("where").add_argument("name")
    commands.add_parser("import-inbox").add_argument("inbox", type=Path)
    commands.add_parser("unblock")
    commands.add_parser("audit-allowed").add_argument("--tasks-dir", type=Path, default=None)
    commands.add_parser("summary")
    args = parser.parse_args()
    root: Path = args.root.resolve()
    board = Board(root / "tasks")
    if args.command == "next":
        return cmd_next(board)
    if args.command == "start":
        return cmd_start(board, root, args.task)
    if args.command == "where":
        return cmd_where(board, args.name)
    if args.command == "import-inbox":
        for line in import_inbox(board, args.inbox):
            print(line)
        return 0
    if args.command == "unblock":
        for name in unblock(board):
            print(name)
        return 0
    if args.command == "audit-allowed":
        refusal = audit_refusal(args.tasks_dir.resolve() if args.tasks_dir else board.tasks)
        if refusal:
            print(f"paid audit not allowed: {refusal}")
            return 1
        return 0
    print("\n".join(summary(board)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
