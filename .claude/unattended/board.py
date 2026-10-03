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
It never runs git: staging and committing belong to the runner and to the agent. The one
exception reads only: `review` takes the board from the work branch in origin (board_review.py).

    board.py next                    the task to work on: the one in doing/, else the first in
                                     todo/ whose dependencies are all in done/.
                                     exit 3: todo/ is empty; exit 4: tasks wait, none is eligible
    board.py start <todo file>       move it to doing/ (refused while doing/ holds a task)
    board.py where <NNN-name>        todo | doing | blocked | done | missing
    board.py import-inbox <dir>      take new task files in (see `import_inbox`)
    board.py unblock                 blocked/ tasks whose every answer is filled go back to todo/
    board.py audit-allowed           exit 0 only when the one task in doing/ asks for the audit
    board.py gate-answers            the gate's questions in blocked/ that the owner answered
                                     «закрити»: one `name<TAB>stamp<TAB>sha256` line each
    board.py gate-done <name> <closed|absent>   such a task goes to done/ with its report
    board.py gate-reject <name>      its answer is wiped and the question asked again
    board.py owner-actions           blocked/ tasks that carry an allowed action the owner answered
                                     «так» (a rule proposal: also «ні»): one
                                     `name<TAB>action<TAB>argument<TAB>sha256` line each
    board.py action-line <action>    the line an agent writes under its question to offer the action
    board.py action-done <name> <applied|failed|stale>   the offer is replaced by what happened
    board.py action-reject <name>    its answer is wiped and the question asked again
    board.py summary                 the board in a dozen lines, for the owner
    board.py review [--since <commit|date>] [--offline]
                                     the owner's review: one markdown document about the work
                                     branch in origin; changes nothing (board_review.py)

A GATE QUESTION (board 005) is a task the Stop gate writes itself when it gives up after N
blocks in a row (`gate_question`, called by .claude/hooks/gate.py): tasks/blocked/9NN-gate-
escalation-<stamp>.md, with the line `Ескалація воріт: <stamp>` under its title. The owner's
answer «закрити» is acted on by board-runner.sh, which runs `gate.py --close-escalation` — never
by an agent, so `unblock` leaves such a task where it is. Any other answer is an instruction:
the task goes back to todo/ like every answered task.

AN OWNER ACTION (board 008) is something only the owner may decide and no agent may do — today
one thing: applying the settings proposal. The agent asks its question and writes under it the
line `Дія виконавця: apply-settings <sha256 of the proposal>` (`action-line` prints it). The
owner's answer «так» is acted on by board-runner.sh through owner_action.py, never by an agent;
`unblock` leaves such a task where it is until the runner has replaced the offer with the
outcome, and then the task returns to todo/ for the agent to check and report. The list of what
the runner may do on the owner's word is OWNER_ACTIONS and nothing outside it is ever run from a
task file. Any other answer is an instruction for the agent, as everywhere.

A RULE QUESTION (board 040) is how a lesson becomes a rule: never by itself, only on the owner's
word. `rule_question` (called by .claude/hooks/lesson_queue.py when a lesson is filed as a rule
proposal) writes tasks/blocked/8NN-rule-proposal-<id>.md: the exact text of the rule, the
overseer's recommendation when there is one, the question «Зробити це правилом?» and the offer
`Дія виконавця: promote-rule <sha256 of the id and the text>`. «так» is the runner's to act on
(owner_action.py promote-rule → lesson_queue.promote), «ні» too (reject-rule: the proposal is
closed); either way the runner moves the task to done/ with a short report and no agent is
started. Any other answer is an instruction for the agent.

`--root DIR` names the repository (default: the one this file is installed in).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
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
GATE = re.compile(r"^Ескалація воріт:\s*(\S+)", re.MULTILINE)
GATE_FIRST = 900  # the gate's questions are numbered from here, past the owner's own tasks
GATE_CLOSE = "закрити"
# What the runner may do on the owner's word, and the answer that asks for it. `close-escalation`
# is offered by the gate's own question (the `Ескалація воріт:` line), the rest by an action line.
OWNER_ACTIONS = {"apply-settings": "так", "promote-rule": "так", "close-escalation": GATE_CLOSE}
RULE_ACTION, RULE_DECLINE, RULE_NO = "promote-rule", "reject-rule", "ні"  # «ні» under a rule question closes the proposal
RULE = re.compile(r"^Пропозиція правила:\s*RP-(\w+)", re.MULTILINE)
RULE_FIRST = 800  # rule questions are numbered from here; the gate's from GATE_FIRST
ACTION = re.compile(r"^[\s>*_-]*Дія виконавця:[ \t]*`?([a-z][a-z-]*)(?:[ \t]+([0-9a-f]{64}))?`?[ \t]*$", re.MULTILINE)
ACTION_FILES = {"apply-settings": "docs/tasks/settings.json"}  # the file whose sha256 the offer names
OFFERS = {*ACTION_FILES, RULE_ACTION}  # what an action line may offer; the rule's sha256 is of its id and text
EXIT_REFUSED, EXIT_TODO_EMPTY, EXIT_NONE_ELIGIBLE = 2, 3, 4


@dataclass(frozen=True)
class Task:
    depends: tuple[int, ...]
    audit: bool
    questions: str
    answers: tuple[str, ...]
    gate: str = ""
    action: str = ""
    action_arg: str = ""
    rule: str = ""

    @property
    def answered(self) -> bool:
        """Every question has its answer — and there is at least one: a task that asks nothing
        was answered by nobody."""
        return bool(self.answers) and all(self.answers)

    @property
    def closes(self) -> bool:
        """A gate question whose last answer is the one word «закрити»: the runner's to act on."""
        return bool(self.gate) and self.says(GATE_CLOSE)

    @property
    def approves(self) -> bool:
        """An offered action whose last answer is the one word «так»: the runner's to act on."""
        return bool(self.action) and not self.gate and self.says(OWNER_ACTIONS[self.action], alone=self.action == RULE_ACTION)

    @property
    def declines(self) -> bool:
        """A rule question whose last answer is the one word «ні»: the runner closes the proposal."""
        return self.action == RULE_ACTION and not self.gate and self.says(RULE_NO, alone=True)

    @property
    def decided(self) -> str:
        """The action the runner is to take on the owner's answer, or ""."""
        return self.action if self.approves else RULE_DECLINE if self.declines else ""

    def says(self, word: str, alone: bool = False) -> bool:
        """The last answer begins with `word`; alone=True (a rule question): it is nothing but that
        word — «так, але інакше» is an instruction, not consent to this text."""
        if not self.answered:
            return False
        words = self.answers[-1].lower().split()
        return bool(words) and words[0].strip("«»\"'`*_.,;:!") == word and (not alone or len(words) == 1)


def parse(text: str) -> Task:
    text = COMMENT.sub("", text)
    first_heading = HEADING.search(text)
    header = text[: first_heading.start()] if first_heading else text
    depends = DEPENDS.search(header)
    audit = AUDIT.search(header)
    gate = GATE.search(header)
    section = QUESTIONS.search(text)
    questions = ""
    if section:
        rest = text[section.end():]
        following = HEADING.search(rest)
        questions = rest[: following.start()] if following else rest
    rule = RULE.search(header)
    offers = [m for m in ACTION.finditer(questions) if m.group(1) in OFFERS]
    return Task(
        action=offers[-1].group(1) if offers else "",
        action_arg=(offers[-1].group(2) or "") if offers else "",
        depends=tuple(int(n) for n in re.findall(r"\d+", depends.group(1))) if depends else (),
        audit=audit is not None and audit.group(1).strip(".,;*_").lower() == "так",
        questions=questions.strip(),
        answers=tuple(a.strip() for a in ANSWER.findall(questions)),
        gate=gate.group(1) if gate else "",
        rule=rule.group(1) if rule else "",
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
        task = read(path)
        # A gate question answered «закрити» is closed by the runner, not handed to an agent;
        # an offered action answered «так» waits for the runner to act on it first.
        if task.answered and not task.closes and not task.decided:
            target = board.tasks / "todo" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            path.rename(target)
            moved.append(path.name)
    return moved


def gate_question(board: Board, stamp: str, blocks: int, slice_name: str, files: list[str],
                  reasons: list[str], report: str) -> Path | None:
    """The Stop gate's escalation as a question in blocked/. None when the project has no board;
    the task already written for this stamp when there is one."""
    if not board.tasks.is_dir():
        return None
    for path in [*(p for c in ("todo", "doing", "blocked") for p in board.files(c)), *(d / "task.md" for d in board.done())]:
        if path.is_file() and read(path).gate == stamp:
            return path
    taken = {n for column in COLUMNS for n in board.numbers(column)}
    number = next(n for n in range(GATE_FIRST, GATE_FIRST + len(taken) + 1) if n not in taken)

    def shown(lines: list[str], empty: str) -> str:
        return "\n".join(f"  - {line.replace('<!--', '<! --').strip()}" for line in lines) or f"  - {empty}"

    text = f"""# {number} — Ворота зупинили роботу: потрібне ваше рішення

Залежить від: —
Аудит потрібен: ні
Ескалація воріт: {stamp}

## Що сталося
Перевірки наприкінці ходу (ворота) не пройшли {blocks} раз(и) поспіль, і агент не зміг цього
виправити. Хід завершено; зроблене лежить на диску. Поки це питання відкрите, наглядач не
приймає роботу, яка зачіпає ці файли.

- Зріз: {slice_name}
- Файли:
{shown(files, "(ворота не назвали файлів)")}
- На чому зупинилося:
{shown(reasons, "(причину не записано)")}
- Повний звіт (на сервері): `{report}`

## Що зробити
Це питання поставили ворота, а не агент. Агент на нього не відповідає і сам ескалацію не
закриває: відповідь «закрити» виконує виконавець дошки. Якщо власник відповів інакше — це
вказівка агентові: виконай її, допиши внизу нове питання «Тепер закрити ескалацію?» з порожнім
рядком відповіді й поверни задачу в `tasks/blocked/`.

## Готово, коли
Власник відповів «закрити», і виконавець закрив ескалацію.

## Питання до власника
Варіанти відповіді:
- `закрити` — зауваження воріт прийнято або вже виправлено; роботу з цими файлами можна приймати далі.
- будь-який інший текст — вказівка агентові, що саме виправити; ескалація лишається відкритою.

1. Що робити з цією зупинкою воріт — закрити чи виправляти (тоді напишіть, що саме)?
   Відповідь:
"""
    target = board.tasks / "blocked" / f"{number}-gate-escalation-{re.sub(r'[^0-9A-Za-z]', '', stamp)}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def rule_question(board: Board, ident: str, rule: str, why: str, origin: str, advice: str, sha: str) -> Path | None:
    """A rule proposal as a question in blocked/ (board 040). None when the project has no board;
    the task already written for this proposal when there is one."""
    if not board.tasks.is_dir():
        return None
    for path in [*(p for c in ("todo", "doing", "blocked") for p in board.files(c)), *(d / "task.md" for d in board.done())]:
        if path.is_file() and read(path).rule == ident:
            return path
    taken = {n for column in COLUMNS for n in board.numbers(column)}
    number = next(n for n in range(RULE_FIRST, RULE_FIRST + len(taken) + 1) if n not in taken)

    def shown(text: str, empty: str) -> str:
        return " ".join(text.replace("<!--", "<! --").split()) or empty

    text = f"""# {number} — Зробити урок правилом? Пропозиція RP-{ident}

Залежить від: —
Аудит потрібен: ні
Пропозиція правила: RP-{ident}

## Що сталося
Із роботи над проєктом винесено урок, схожий на постійне правило. Уроки не стають правилами
самі: це правило з'явиться лише з вашої згоди. Наглядач може радити, але не вирішує.

- Текст правила — саме так, слово в слово, він потрапить у `.engine/rules.md`, який читає кожна розмова:

  > {shown(rule, "(тексту немає)")}

- Чому: {shown(why, "(не записано)")}
- Звідки урок: {shown(origin, "(не записано)")}
- Рекомендація наглядача: {shown(advice, "немає")}

## Що зробити
Це питання до власника, не робота для агента. Відповіді «так» і «ні» виконує виконавець дошки.
Якщо власник відповів інакше — це вказівка агентові: виконай її (щоб змінити текст правила,
закрий цю пропозицію — `python3 .claude/hooks/lesson_queue.py reject {ident} --why "<слова власника>"` —
і подай нову), запиши у звіт і закрий задачу. Сам `promote` не запускай і `Відповідь:` не заповнюй.

## Готово, коли
Власник відповів, і виконавець записав правило або закрив пропозицію.

## Питання до власника
Варіанти відповіді:
- `так` — урок стає правилом: рядок вище буде додано до `.engine/rules.md`.
- `ні` — правилом не стає; пропозицію закрито.
- будь-який інший текст — вказівка агентові (наприклад, як переписати правило).

1. Зробити це правилом?
   Дія виконавця: {RULE_ACTION} {sha}
   Відповідь:
"""
    target = board.tasks / "blocked" / f"{number}-rule-proposal-{ident}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def gate_answers(board: Board) -> list[str]:
    lines: list[str] = []
    for path in board.files("blocked"):
        task = read(path)
        if task.closes:
            lines.append(f"{path.name}\t{task.gate}\t{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return lines


def gate_task(board: Board, name: str) -> Path | None:
    path = board.tasks / "blocked" / Path(name).name
    return path if path.is_file() and TASK_NAME.match(path.name) and read(path).gate else None


def gate_done(board: Board, path: Path, outcome: str) -> Path:
    """A gate question the runner has acted on: done/NNN-name/ with task.md and a report.md."""
    stamp = read(path).gate
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if outcome == "closed":
        changed = (f"Ескалацію воріт {stamp} закрито за вашою відповіддю «закрити» ({now}, виконавець дошки). "
                   "Наглядач знову приймає роботу з цими файлами.")
    else:
        changed = (f"Ескалація воріт {stamp} на момент вашої відповіді вже не була відкрита (її закрито раніше "
                   f"або запису про неї немає). Питання прибрано з дошки ({now}, виконавець дошки).")
    target = board.tasks / "done" / path.stem
    target.mkdir(parents=True, exist_ok=True)
    path.rename(target / "task.md")
    (target / "report.md").write_text(
        f"# Звіт: {path.stem}\n\n## Що змінилось для власника\n- {changed}\n\n"
        "Цей звіт написав виконавець дошки, не агент: жодної роботи тут не було, лише ваша відповідь.\n",
        encoding="utf-8")
    return target


def owner_actions(board: Board) -> list[str]:
    lines: list[str] = []
    for path in board.files("blocked"):
        task = read(path)
        if task.decided:
            lines.append(f"{path.name}\t{task.decided}\t{task.action_arg or '-'}\t{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return lines


def action_line(root: Path, action: str) -> str:
    """The offer an agent writes under its question: the action and the sha256 of what it applies."""
    return f"Дія виконавця: {action} {hashlib.sha256((root / ACTION_FILES[action]).read_bytes()).hexdigest()}"


def action_task(board: Board, name: str) -> Path | None:
    path = board.tasks / "blocked" / Path(name).name
    return path if path.is_file() and TASK_NAME.match(path.name) and read(path).action else None


STALE = ("Дію не виконано ({now}, виконавець дошки): {action} — те, що застосовується, змінилося після запитання "
         "(інший sha256) або його немає; власник схвалював не це. Агентові: спитай знову з новим рядком дії.")
ACTION_OUTCOMES = {
    "applied": "Дію виконано ({now}, виконавець дошки): {action} — застосовано за відповіддю власника «так», "
               "перевірка після застосування зелена. Агентові: переконайся і закрий задачу звітом.",
    "failed": "Дію не виконано ({now}, виконавець дошки): {action} — перевірка після застосування червона, попередній "
              "файл повернуто (журнал на сервері: .claude/state/board/logs/owner-action.log). Агентові: виправ і спитай знову.",
    "stale": STALE,
}
RULE_OUTCOMES = {
    (RULE_ACTION, "applied"): "Дію виконано ({now}, виконавець дошки): {action} — за відповіддю власника «так» правило додано до `.engine/rules.md`.",
    (RULE_ACTION, "failed"): "Дію не виконано ({now}, виконавець дошки): {action} — правило не додано: постійний контекст перевищив би "
                             "200 рядків (журнал на сервері: .claude/state/board/logs/owner-action.log). Агентові: скороти "
                             "`.engine/rules.md` і спитай знову (`lesson_queue.py ask <id>`).",
    (RULE_DECLINE, "applied"): "Дію виконано ({now}, виконавець дошки): {action} — за відповіддю власника «ні» пропозицію закрито; правилом вона не стала.",
}
RULE_REPORTS = {
    RULE_ACTION: "Урок став правилом за вашою відповіддю «так»: рядок додано до `.engine/rules.md` ({now}, виконавець дошки).",
    RULE_DECLINE: "Пропозицію правила закрито за вашою відповіддю «ні»: правилом вона не стала ({now}, виконавець дошки).",
}


def action_done(board: Board, path: Path, outcome: str) -> Path:
    """Replace the offer by what happened: the task is then an ordinary answered one (`unblock`)
    and the same answer can never run the action twice. A rule question the runner has acted on
    needs no agent: it goes to done/ with a report. Returns where the task is now."""
    task = read(path)
    action = task.decided or task.action
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    note = RULE_OUTCOMES.get((action, outcome), ACTION_OUTCOMES[outcome]).format(now=now, action=action)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [note if ACTION.match(line) else line for line in lines]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if action not in RULE_REPORTS or outcome != "applied":
        return path
    target = board.tasks / "done" / path.stem
    target.mkdir(parents=True, exist_ok=True)
    path.rename(target / "task.md")
    (target / "report.md").write_text(
        f"# Звіт: {path.stem}\n\n## Що змінилось для власника\n- {RULE_REPORTS[action].format(now=now)}\n\n"
        "Цей звіт написав виконавець дошки, не агент: жодної роботи тут не було, лише ваша відповідь.\n",
        encoding="utf-8")
    return target


def gate_reject(path: Path, word: str = GATE_CLOSE) -> None:
    """Wipe an answer that did not come from the owner and say so under the question."""
    lines = path.read_text(encoding="utf-8").splitlines()
    last = max(i for i, line in enumerate(lines) if ANSWER.match(line))
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines[last] = lines[last][: lines[last].index("Відповідь:")] + "Відповідь:"
    lines.insert(last, f"Примітка виконавця ({now}): відповідь «{word}» з'явилася на сервері, а не прийшла "
                       "через гілку чи теку вхідних задач, тому її не прийнято. Дайте відповідь ще раз.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
            asked = [text.strip() for text in lines[:index] if text.strip() and not ANSWER.match(text) and not ACTION.match(text)]
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


def cmd_review(root: Path, args: argparse.Namespace) -> int:
    import board_review  # here, not at the top: board_review reads this module's parser

    try:
        document = board_review.review(root, args.state_dir or root / ".claude/state", args.remote, args.branch,
                                       args.since, args.offline, datetime.now(UTC))
    except board_review.ReviewError as refusal:
        print(f"board: review: {refusal}", file=sys.stderr)
        return EXIT_REFUSED
    sys.stdout.write(document)
    return 0


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
    commands.add_parser("gate-answers")
    gate_done_parser = commands.add_parser("gate-done")
    gate_done_parser.add_argument("name")
    gate_done_parser.add_argument("outcome", choices=("closed", "absent"))
    commands.add_parser("gate-reject").add_argument("name")
    commands.add_parser("owner-actions")
    commands.add_parser("action-line").add_argument("action", choices=sorted(ACTION_FILES))
    action_done_parser = commands.add_parser("action-done")
    action_done_parser.add_argument("name")
    action_done_parser.add_argument("outcome", choices=sorted(ACTION_OUTCOMES))
    commands.add_parser("action-reject").add_argument("name")
    commands.add_parser("summary")
    review_parser = commands.add_parser("review")
    review_parser.add_argument("--since", default=None, help="a commit or a date; default: the newest version tag")
    review_parser.add_argument("--offline", action="store_true", help="do not ask origin; show the state this clone saw last")
    review_parser.add_argument("--remote", default=os.environ.get("BOARD_REMOTE", "origin"))
    review_parser.add_argument("--branch", default=os.environ.get("BOARD_BRANCH", "unattended/work"))
    review_parser.add_argument("--state-dir", type=Path, default=None, help="the runner's state (default: .claude/state)")
    args = parser.parse_args()
    root: Path = args.root.resolve()
    if args.command == "review":
        return cmd_review(root, args)
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
    if args.command == "gate-answers":
        for line in gate_answers(board):
            print(line)
        return 0
    if args.command in ("gate-done", "gate-reject"):
        path = gate_task(board, args.name)
        if path is None:
            print(f"board: {args.name} is not a gate question in tasks/blocked/", file=sys.stderr)
            return EXIT_REFUSED
        if args.command == "gate-done":
            print(board.shown(gate_done(board, path, args.outcome)))
        else:
            gate_reject(path)
        return 0
    if args.command == "owner-actions":
        for line in owner_actions(board):
            print(line)
        return 0
    if args.command == "action-line":
        print(action_line(root, args.action))
        return 0
    if args.command in ("action-done", "action-reject"):
        path = action_task(board, args.name)
        if path is None:
            print(f"board: {args.name} offers no action in tasks/blocked/", file=sys.stderr)
            return EXIT_REFUSED
        if args.command == "action-done":
            print(board.shown(action_done(board, path, args.outcome)))
        else:
            gate_reject(path, RULE_NO if read(path).declines else OWNER_ACTIONS[read(path).action])
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
