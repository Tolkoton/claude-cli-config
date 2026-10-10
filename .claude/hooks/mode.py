#!/usr/bin/env python3
"""mode.py — the one reader of a task's mode (board 097; the approved design is board 080).

    python3 .claude/hooks/mode.py show [--task FILE]      one line: the mode, the accompaniment,
                                                         «without supervision», the work type —
                                                         each with where it was read; writes nothing
    python3 .claude/hooks/mode.py raise <mode> --why "…"  the agent raises the mode of its task in doing/
    python3 .claude/hooks/mode.py unattended              `unattended env|mode-file` (exit 0) or `attended` (exit 1)

THREE MODES, a property of the TASK: ескіз (an answer to one question, code only in quarantine),
соло (one builder, the gates, the overseer), конвеєр (a feature architect, a sealed slice contract
on every slice). The owner writes the line `Режим: ескіз|соло|конвеєр` under the task's title; a
task without it is соло. A value that names no mode (or two such lines) is nobody's clear word:
the board does not take that task (board.py) and says why.

RAISING. The agent goes up by itself and never down: a lighter mode lifts checks, and nobody lifts
checks for themselves (the constitution, article 3). `raise` appends to the session's task in
doing/ the section `## Режим піднято`, one line per raise — when, from which mode to which, why.
The mode in force is the higher of the owner's line and the last raise. There is no state file:
the raise lives in the task file and moves to done/ with it, so the next task starts from its own
line or from соло. Only the owner undoes a raise, by deleting that section from the task file.

WHAT A MODE FORBIDS (`refusal`). A fix is never made in quarantine: /hotfix and /bugfix are
refused in ескіз. An urgent fix is small by definition: /hotfix is refused in конвеєр. hotfix.py
start and bugfix.py prove ask here.

«WITHOUT SUPERVISION» is a property of the SESSION: the runner's variable
CLAUDE_UNATTENDED_SESSION=1, or `.claude/state/overseer/mode` saying `unattended`. It was computed
in five places, each its own way (board.py, env-probe.sh, goals.py, hotfix.py, park-ask-gated.py);
they all ask `unattended` here.

THE ACCOMPANIMENT is a fact about the project: it has the snapshot `.engine/baseline.json` and the
profile `.engine/onboard/profile.md`. THE WORK TYPE belongs to the card: `type:` of the bug record
that `.engine/PROGRESS.md` marks IN PROGRESS.

A mode says which roles run and how strictly; it never says who runs them, and nothing here
names one (tests/test_model_roles.py). Standard library only. Exit: 0 done; 1 attended
(`unattended` only); 2 refused.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MODES = ("ескіз", "соло", "конвеєр")  # in the order of their ceremony: a raise goes rightwards only
DEFAULT = "соло"
LINE = re.compile(r"^Режим:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
RAISED = "## Режим піднято"
RAISED_HEADING = re.compile(r"^##\s+Режим піднято\s*$", re.MULTILINE)
RAISE_LINE = re.compile(r"^- (\S+) — (\S+) → (\S+): (.+)$", re.MULTILINE)
QUESTIONS = re.compile(r"^##\s+Питання до власника\s*$", re.MULTILINE)
HEADING = re.compile(r"^##\s", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
ENV = "CLAUDE_UNATTENDED_SESSION"
MODE_FILE = ".claude/state/overseer/mode"
SOURCES = {"env": f"змінна runner-а {ENV}=1", "mode-file": f"файл {MODE_FILE}"}
BASELINE, PROFILE = ".engine/baseline.json", ".engine/onboard/profile.md"
TYPE_LINE = re.compile(r"^type:[ \t]*(\S+)", re.MULTILINE)
FORBIDDEN = {
    ("ескіз", "hotfix"): "a fix is never made in quarantine: /hotfix is refused in the mode «ескіз»",
    ("ескіз", "bugfix"): "a fix is never made in quarantine: /bugfix is refused in the mode «ескіз»",
    ("конвеєр", "hotfix"): "an urgent fix is small by definition: /hotfix is refused in the mode «конвеєр»",
}
EXIT_OK, EXIT_ATTENDED, EXIT_REFUSED = 0, 1, 2


@dataclass(frozen=True)
class Raise:
    utc: str
    before: str
    after: str
    why: str


@dataclass(frozen=True)
class Mode:
    """What a task file says about its mode: the owner's line and the raises."""

    line: str | None  # the owner's value as written; None when the task has no `Режим:` line
    raises: tuple[Raise, ...] = ()
    error: str = ""  # why the line names no mode; "" when it does or is absent

    @property
    def owner(self) -> str:
        """The owner's mode: the line, else соло."""
        return _normal(self.line) if self.line is not None and not self.error else DEFAULT

    @property
    def current(self) -> str:
        """The mode in force: the higher of the owner's line and the last raise."""
        if self.error:
            return ""
        last = self.raises[-1].after if self.raises else self.owner
        return max(self.owner, last, key=MODES.index)

    def shown(self) -> str:
        """The mode with where it was read, for a person: `соло (рядка «Режим:» немає → соло)`."""
        if self.error:
            return f"невідомий ({self.error}; task board таку задачу не бере)"
        said = f"рядок «Режим: {self.line}»" if self.line is not None else f"рядка «Режим:» немає → {DEFAULT}"
        raised = "; ".join(f"піднято {r.utc} з {r.before} на {r.after} — {r.why}" for r in self.raises)
        return f"{self.current} ({said}" + (f"; {raised}" if raised else "") + ")"


def _normal(value: str) -> str:
    return value.strip().strip("*_.!").strip().lower()


def parse(text: str) -> Mode:
    """The mode of a task file. The line is read in the header only (above the first `## `)."""
    text = COMMENT.sub("", text)
    first = HEADING.search(text)
    lines = LINE.findall(text[: first.start()] if first else text)
    raises = tuple(Raise(*m.groups()) for m in RAISE_LINE.finditer(_raised_section(text))
                   if m.group(2) in MODES and m.group(3) in MODES)
    if not lines:
        return Mode(None, raises)
    if len(lines) > 1:
        return Mode(lines[0], raises, "рядків «Режим:» два або більше — незрозуміло, котрий чинний")
    if _normal(lines[0]) not in MODES:
        return Mode(lines[0], raises, f"«Режим: {lines[0]}» — такого режиму немає: {', '.join(MODES)}")
    return Mode(lines[0], raises)


def _raised_section(text: str) -> str:
    found = RAISED_HEADING.search(text)
    if not found:
        return ""
    rest = text[found.end():]
    following = HEADING.search(rest)
    return rest[: following.start()] if following else rest


# ------------------------------------------------------------------ the session


def unattended(root: Path) -> tuple[bool, str]:
    """(nobody is watching, where that was read: `env` or `mode-file`; "" when attended)."""
    if os.environ.get(ENV) == "1":
        return True, "env"
    try:
        said = (root / MODE_FILE).read_text(encoding="utf-8")
    except (OSError, ValueError):
        said = ""
    return (True, "mode-file") if _normal(said) == "unattended" else (False, "")


def _board() -> Any:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unattended"))
    import board  # here, not at the top: board.py imports this module

    return board


def own_task(root: Path) -> list[Path]:
    """The session's tasks in doing/ (board.py `own`): one, or none when there is no board task."""
    tasks = root / "tasks"
    return list(_board().own(tasks)) if (tasks / "doing").is_dir() else []


def accompaniment(root: Path) -> tuple[bool, str]:
    missing = [p for p in (BASELINE, PROFILE) if not (root / p).is_file()]
    return (False, "немає " + " і ".join(missing)) if missing else (True, f"{BASELINE} і {PROFILE}")


def work_type(root: Path) -> tuple[str, str]:
    """(`type:` of the card IN PROGRESS, where it was read) — `—` when there is no such card."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import complexity_budget

        card = complexity_budget.active_contract(root)
    except (ImportError, OSError, ValueError):
        card = None
    if card is None:
        return "—", "у .engine/PROGRESS.md немає картки IN PROGRESS"
    found = TYPE_LINE.search(card.read_text(encoding="utf-8"))
    shown = card.relative_to(root).as_posix() if card.is_relative_to(root) else str(card)
    return (found.group(1), shown) if found else ("—", f"{shown} без рядка type:")


def show_line(root: Path, task: Path | None = None) -> str:
    """The one line `show` prints: the task given, else the session's task in doing/."""
    if task is None:
        mine = own_task(root)
        task = mine[0] if len(mine) == 1 else None
    if task is None:
        mode = "— (у tasks/doing/ немає задачі цієї сесії: без задачі task board режим задає команда власника)"
    else:
        name = task.parent.name if task.name == "task.md" else task.stem
        mode = f"{parse(task.read_text(encoding='utf-8')).shown()}, задача {name}"
    with_owner, said = accompaniment(root)
    alone, where = unattended(root)
    kind, card = work_type(root)
    return (f"режим: {mode} · супровід: {'так' if with_owner else 'ні'} ({said}) · "
            f"без нагляду: {'так (' + SOURCES[where] + ')' if alone else 'ні (ні змінної runner-а, ні файла режиму)'} · "
            f"тип роботи: {kind} ({card})")


def refusal(root: Path, command: str, task: Path | None = None) -> str | None:
    """Why `command` (hotfix, bugfix) may not run in the mode of `task` — the task file given, else
    the session's task in doing/. None when it may, or when there is no board task."""
    if task is None:
        mine = own_task(root)
        task = mine[0] if len(mine) == 1 else None
    try:
        text = task.read_text(encoding="utf-8") if task else ""
    except OSError:
        text = ""
    current = parse(text).current if text else ""
    reason = FORBIDDEN.get((current, command))
    return f"{reason} (task {task.name if task else '-'}, python3 .claude/hooks/mode.py show)" if reason else None


# ------------------------------------------------------------------ raise


def raise_mode(path: Path, target: str, why: str, now: str) -> str | None:
    """Append the raise to the task file; the reason it is refused, or None when it is written."""
    text = path.read_text(encoding="utf-8")
    mode = parse(text)
    why = " ".join(why.replace("<!--", "<! --").split())
    if mode.error:
        return f"the task's own line names no mode ({mode.error}); only the owner can say which one is meant"
    if target not in MODES:
        return f"«{target}» is no mode: {', '.join(MODES)}"
    if MODES.index(target) <= MODES.index(mode.current):
        return (f"the task is in «{mode.current}» already; a raise goes up only ({' → '.join(MODES)}) — "
                "a lighter mode is set by the owner alone, in the task's line")
    if not why:
        return "--why is empty: a raise says why"
    line = f"- {now} — {mode.current} → {target}: {why}"
    path.write_text(_with_line(text, line), encoding="utf-8")
    return None


def _with_line(text: str, line: str) -> str:
    """`text` with `line` at the end of the section `## Режим піднято`, made before the questions
    (or at the end) the first time."""
    text = text.rstrip("\n") + "\n"
    found = RAISED_HEADING.search(text)
    if found:
        rest = text[found.end():]
        following = HEADING.search(rest)
        cut = found.end() + (following.start() if following else len(rest))
        return text[:cut].rstrip("\n") + f"\n{line}\n" + ("\n" if following else "") + text[cut:]
    questions = QUESTIONS.search(text)
    if questions:
        head, tail = text[: questions.start()], text[questions.start():]
        return head.rstrip("\n") + f"\n\n{RAISED}\n{line}\n\n" + tail
    return text + f"\n{RAISED}\n{line}\n"


def cmd_raise(root: Path, target: str, why: str) -> int:
    mine = own_task(root)
    if len(mine) != 1:
        print(f"REFUSED: tasks/doing/ holds {len(mine)} tasks of this session, not one: a raise is written into the task in hand",
              file=sys.stderr)
        return EXIT_REFUSED
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    reason = raise_mode(mine[0], target, why, now)
    if reason:
        print(f"REFUSED: {reason}", file=sys.stderr)
        return EXIT_REFUSED
    print(f"RAISED: {mine[0].relative_to(root).as_posix()} — {parse(mine[0].read_text(encoding='utf-8')).shown()}")
    return EXIT_OK


# ------------------------------------------------------------------ entry


def project_root() -> Path:
    given = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if given and Path(given).is_dir():
        return Path(given)
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    return Path(top.stdout.strip()) if top.returncode == 0 and top.stdout.strip() else Path.cwd()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=None, help="the project (default: CLAUDE_PROJECT_DIR, else the git repository here)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("show").add_argument("--task", type=Path, default=None, help="a task file (default: the session's task in doing/)")
    raising = commands.add_parser("raise")
    raising.add_argument("mode", help=" | ".join(MODES))
    raising.add_argument("--why", required=True)
    commands.add_parser("unattended")
    args = parser.parse_args(argv)
    root = (args.root or project_root()).resolve()
    if args.command == "raise":
        return cmd_raise(root, args.mode, args.why)
    if args.command == "unattended":
        alone, where = unattended(root)
        print(f"unattended {where}" if alone else "attended")
        return EXIT_OK if alone else EXIT_ATTENDED
    task = args.task if args.task is None or args.task.is_absolute() else root / args.task
    if task is not None and not task.is_file():
        print(f"REFUSED: {args.task} is not a file", file=sys.stderr)
        return EXIT_REFUSED
    print(show_line(root, task))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
