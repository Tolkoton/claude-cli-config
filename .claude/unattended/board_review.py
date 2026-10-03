"""The owner's review of the task board: one markdown document, and nothing is changed (board 009).

    board.py review [--since <commit|date>] [--offline] [--remote origin] [--branch unattended/work]

The owner reviews when there is time for it, not when a task ends. So the review may run at any
moment, next to a runner in the middle of a task, and from any clone. Two things make that safe:

WHAT IT READS. The board as the work branch has it IN ORIGIN — never the checkout it is run
from, which on the runner's machine is half-way through something. `git ls-remote` names the
commit; when this clone lacks it, the commit is fetched as objects only (`--refmap=`,
`--no-write-fetch-head`): no ref, no index and no file of the working tree is written, so a
runner pulling at the same moment meets no lock of ours. With origin out of reach the last
state this clone knows (its remote-tracking ref) is shown, and the document says so.
The runner's own state — `.claude/state/board/` — is not in git; it is read when the review runs
on the runner's machine and replaced by what git shows when it does not.

WHAT IT SHOWS, in six sections: the state now; what was done since `--since` (default: the
newest version tag), each finished task with the owner's parts of its report; everything that
waits for the owner — every unfilled `Відповідь:` in blocked/ with the text above it, the
settings proposals, the open escalations, the parked items, the rule proposals; the plan; the
candidates for new tasks; the health. `--since` narrows what was DONE (and the candidates and the
costs that come from it); what waits and what is planned is always shown whole. The last line is
the command for the next review.

Exit 0: the document is on stdout. Exit 2: no document — the branch is known neither to origin
nor to this clone, or `--since` is neither a commit nor a date.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import board
import board_state

EXIT_REFUSED = 2
CONTEXT_BUDGET = 200
MAX_HOPS = 4  # how deep Claude Code follows `@path` imports (tests/test_context_budget.py)
IMPORT_RE = re.compile(r"(?:(?<=\s)|^)@([^\s`]+)", re.MULTILINE)
FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
SPAN_RE = re.compile(r"`[^`\n]*`")
STATUS = re.compile(r"^state=(\S+) task=(\S+) since=(\S+)(?: reason=(.*))?$")
ENTRY = re.compile(r"(?=^## \d{4}-\d\d-\d\d)", re.MULTILINE)
PARKED = re.compile(r"^## (\S+) — (.+) — (PARKED|RESUMED|SURFACED)[ \t]*$", re.MULTILINE)
PROPOSAL = re.compile(r"^## (RP-\w+) — \S+ — PROPOSED[ \t]*$", re.MULTILINE)
GOLDEN = re.compile(r"^evals/baseline/[^/]+/results-[^/]+\.json$")
FINDING_MAX = 260
# The runner's states (board-runner.sh), as the owner reads them.
STATES = {
    "running": "працює",
    "waiting-limit": "чекає, поки відновиться ліміт використання",
    "idle": "зупинився: у todo/ нічого немає",
    "waiting-owner": "зупинився: усе, що лишилося, чекає власника",
    "stopped": "зупинився після однієї задачі, як і просили",
    "stalled": "зупинився: кілька спроб поспіль без жодного commit-а",
    "deadline": "зупинився: задача триває довше дозволеного або вичерпала свій бюджет",
    "error": "зупинився через помилку",
}
# The parts of a report the review quotes, by the start of the heading (reports word them freely).
OWNER_PARTS = (("що змінилось для власника",), ("демонстрація",), ("рішення, які я ухвалив сам",), ("витрати",), ("commit", "діапазон commit"))
CANDIDATE_PARTS = (("відкладене",), ("чого мені бракувало",))


class ReviewError(Exception):
    """No document can be made; the text is the reason."""


def git(root: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    """Git that only reads, and never stops to ask for a password: a remote that wants one is out of reach."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    command = ["git", "-C", str(root), "-c", "core.quotepath=false", *args]
    try:
        return subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", check=False, env=env,
                              stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(command, 124, "", "timed out")


class Source:
    """One commit of the work branch, read through git."""

    def __init__(self, root: Path, sha: str, name: str, note: str) -> None:
        self.root, self.sha, self.name, self.note = root, sha, name, note
        listed = git(root, "ls-tree", "-r", "-z", "--name-only", sha).stdout
        self.files = frozenset(p for p in listed.split("\0") if p)

    def show(self, path: str) -> str:
        return git(self.root, "show", f"{self.sha}:{path}").stdout if path in self.files else ""

    def column(self, name: str) -> list[str]:
        """The task files of todo/, doing/ or blocked/, lowest number first — as board.Board.files."""
        prefix = f"tasks/{name}/"
        found = [p for p in self.files if p.startswith(prefix) and board.TASK_NAME.match(p[len(prefix):])]
        return sorted(found, key=lambda p: (board.number_of(posixpath.basename(p)) or 0, p))

    def done(self) -> list[str]:
        stems = {p.split("/")[2] for p in self.files if p.startswith("tasks/done/") and p.count("/") >= 3}
        return sorted((s for s in stems if board.DONE_NAME.match(s)), key=lambda s: (board.number_of(s) or 0, s))

    def log(self, *args: str) -> str:
        return git(self.root, "log", *args).stdout.strip()


def has_commit(root: Path, sha: str) -> bool:
    return git(root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def source(root: Path, remote: str, branch: str, offline: bool) -> Source:
    name = f"{remote}/{branch}"
    note = "без звернення до origin (--offline): стан, який цей клон бачив востаннє"
    if not offline:
        asked = git(root, "ls-remote", remote, f"refs/heads/{branch}", timeout=30)
        sha = asked.stdout.split()[0] if asked.returncode == 0 and asked.stdout.split() else ""
        if sha and not has_commit(root, sha):
            # Objects only: no ref and no FETCH_HEAD, so nothing a runner's pull could trip over.
            git(root, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "--refmap=", remote, f"refs/heads/{branch}", timeout=120)
        if sha and has_commit(root, sha):
            return Source(root, sha, name, "")
        if asked.returncode == 0 and not sha:
            raise ReviewError(f"{remote} has no branch {branch}: nothing to review (the work branch is named by --branch or BOARD_BRANCH)")
        note = f"{remote} недосяжний: показано стан, який цей клон бачив востаннє"
    known = git(root, "rev-parse", "--verify", "--quiet", f"refs/remotes/{name}^{{commit}}").stdout.strip()
    if not known:
        raise ReviewError(f"the branch {branch} of {remote} cannot be reached and this clone has never seen it: nothing to review")
    return Source(root, known, name, note)


@dataclass(frozen=True)
class Since:
    shown: str
    revisions: tuple[str, ...]  # what `git log` takes to list the period
    utc: datetime | None        # the same moment for the runner's records; None: from the start


def as_utc(text: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(text.strip())
    except ValueError:
        return None
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def since(src: Source, given: str | None) -> Since:
    label = given
    if given is None:
        label = git(src.root, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", src.sha).stdout.strip()
        if not label:
            return Since("від початку (міток версій у гілці немає)", (src.sha,), None)
    assert label is not None
    commit = git(src.root, "rev-parse", "--verify", "--quiet", f"{label}^{{commit}}").stdout.strip()
    if commit:
        moment = as_utc(git(src.root, "log", "-1", "--format=%cI", commit).stdout)
        what = f"мітки версії `{label}`" if given is None else f"commit-а `{label}`"
        return Since(f"від {what} ({commit[:7]}, {stamp(moment)})", (f"{commit}..{src.sha}",), moment)
    moment = as_utc(label)
    if moment is None:
        raise ReviewError(f"--since {label}: neither a commit of this repository nor a date (2026-10-03 or 2026-10-03T14:00:00Z)")
    return Since(f"від {stamp(moment)}", (f"--since={moment.isoformat()}", src.sha), moment)


def stamp(moment: datetime | None) -> str:
    return moment.strftime("%Y-%m-%d %H:%M UTC") if moment else "час невідомий"


def elapsed(start: datetime, end: datetime) -> str:
    minutes = max(0, int((end - start).total_seconds()) // 60)
    days, hours, rest = minutes // 1440, minutes % 1440 // 60, minutes % 60
    parts = [f"{days} дн" if days else "", f"{hours} год" if days or hours else "", f"{rest} хв"]
    return " ".join(p for p in parts if p)


def title_of(text: str, fallback: str) -> str:
    first = next((line for line in text.splitlines() if line.startswith("# ")), "")
    return first[2:].strip() or fallback


# ------------------------------------------------------------------ reports


def sections(text: str) -> list[tuple[str, str]]:
    """The `## ` sections of a report: (heading, body). A `## ` line inside a code block is text."""
    found: list[tuple[str, str]] = []
    heading: str | None = None
    body: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            if heading is not None:
                found.append((heading, "\n".join(body).strip()))
            heading, body = line[3:].strip(), []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        found.append((heading, "\n".join(body).strip()))
    return found


def pick(found: list[tuple[str, str]], prefixes: tuple[str, ...]) -> tuple[str, str] | None:
    return next(((h, b) for h, b in found if b and h.lower().startswith(prefixes)), None)


def quoted(heading: str, body: str) -> list[str]:
    """A report's section inside the review: its heading in bold, its own headings pushed down."""
    lines = [f"**{heading}**", ""]
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        lines.append("##" + line if not fenced and line.startswith("#") else line)
    return [*lines, ""]


# ------------------------------------------------------------------ the runner's state


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def task_costs(state: Path) -> dict[str, dict[str, Any]]:
    tasks = load_json(state / "board/costs.json").get("tasks")
    return {str(k): v for k, v in tasks.items() if isinstance(v, dict)} if isinstance(tasks, dict) else {}


def runner_alive(state: Path) -> bool | None:
    """Whether the process named in the runner's lock exists. None: no lock to judge by."""
    try:
        pid = int((state / "board/lock").read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def task_line(name: str, entry: dict[str, Any] | None, now: datetime) -> str:
    line = f"- Задача у виконавця: `{name}`"
    if entry:
        begun = as_utc(str(entry.get("started_utc", "")))
        line += f", триває {elapsed(begun, now)}" if begun and "outcome" not in entry else ""
        line += f"; витрачено ${float(entry.get('cost_usd', 0.0)):.2f} за {len(entry.get('attempts') or [])} завершених спроб"
        idle = int(entry.get("attempts_without_commit", 0) or 0)
        line += f", із них поспіль без commit-а: {idle}" if idle else ""
    return line + "."


def runner_lines(src: Source, state: Path, status: re.Match[str], now: datetime) -> list[str]:
    word, name, started, reason = status.group(1), status.group(2), as_utc(status.group(3)), status.group(4)
    working = word in ("running", "waiting-limit")
    lines = [f"За файлами стану виконавця (`{os.path.relpath(state / 'board', src.root)}/`, ця машина):",
             f"- Виконавець: **{STATES.get(word, word)}** (`{word}`), у цьому стані від {stamp(started)}"
             + (f" — {elapsed(started, now)}" if started else "") + (f"; причина: `{reason}`" if reason else "") + "."]
    if working and runner_alive(state) is False:
        lines.append("- Увага: процесу виконавця з файла `lock` на цій машині немає — запис стану міг застаріти.")
    if name != "-":
        lines.append(task_line(name, task_costs(state).get(name), now))
    summary = state / "board/summary.md"
    if not working and summary.is_file():
        lines += [f"- Підсумок останнього запуску: {said[2:]}" for said in summary.read_text(encoding="utf-8").splitlines() if said.startswith("- Стан:")]
    return lines


def now_section(src: Source, state: Path, now: datetime) -> list[str]:
    try:
        status = STATUS.match((state / "board/status").read_text(encoding="utf-8").strip())
    except OSError:
        status = None
    if status:
        lines = runner_lines(src, state, status, now)
    else:
        lines = [("Файлів стану виконавця тут немає (вони лише на його машині), тож стан — із git; "
                  "витрат і того, чи виконавець зараз працює або чекає ліміту, з git не видно.")]
    doing = src.column("doing")
    for path in doing:
        moved = as_utc(src.log("-1", "--diff-filter=AR", "--format=%cI", src.sha, "--", path))
        lines.append(f"- У гілці в `doing/`: `{posixpath.basename(path)}` — {title_of(src.show(path), 'без назви')}; "
                     f"узято в роботу {stamp(moved)}" + (f", {elapsed(moved, now)} тому" if moved else "") + ".")
    if not doing:
        unpushed = status is not None and status.group(2) != "-"
        lines.append("- У гілці в `doing/` зараз порожньо" + (" (commit, яким задачу взято в роботу, ще не надіслано)." if unpushed else "."))
    counts = "   ".join(f"{c}: {len(src.done() if c == 'done' else src.column(c))}" for c in board.COLUMNS)
    lines.append(f"- Дошка: {counts}")
    return lines


# ------------------------------------------------------------------ done


def new_done(src: Source, period: Since) -> list[str]:
    """The stems under tasks/done/ that gained a file in the period — a task that was finished in it."""
    added = src.log("--format=", "--name-only", "--diff-filter=AR", *period.revisions, "--", "tasks/done")
    stems = {p.split("/")[2] for p in added.splitlines() if p.startswith("tasks/done/") and p.count("/") >= 3}
    return [s for s in src.done() if s in stems]


def done_section(src: Source, stems: list[str], costs: dict[str, dict[str, Any]]) -> list[str]:
    if not stems:
        return ["За цей період нових готових задач немає."]
    lines: list[str] = []
    for stem in stems:
        folder = f"tasks/done/{stem}"
        report = src.show(f"{folder}/report.md")
        lines += [f"### {stem} — {title_of(src.show(f'{folder}/task.md'), stem)}", ""]
        closed = src.log("-1", "--diff-filter=AR", "--format=%h%x09%cI%x09%s", src.sha, "--", f"{folder}/report.md", f"{folder}/task.md").split("\t")
        if len(closed) == 3:
            lines.append(f"Закрито {stamp(as_utc(closed[1]))}, commit `{closed[0]}` — {closed[2]}")
        if stem in costs:
            lines.append(f"За записами виконавця: ${float(costs[stem].get('cost_usd', 0.0)):.2f}, спроб: {len(costs[stem].get('attempts') or [])}.")
        lines.append("")
        found = sections(report)
        if not report:
            lines += ["Звіту `report.md` у теці немає.", ""]
        for prefixes in OWNER_PARTS:
            part = pick(found, prefixes)
            if part:
                lines += quoted(*part)
        lines += [f"Повний звіт: `{folder}/report.md`", ""]
    return lines


# ------------------------------------------------------------------ what waits for the owner


def open_questions(questions: str) -> list[str]:
    """One block per `Відповідь:` line that is empty: everything written above it since the
    previous answer — the question, its context, the options, an offered action."""
    blocks: list[str] = []
    current: list[str] = []
    for line in questions.splitlines():
        answer = board.ANSWER.match(line)
        if answer is None:
            current.append(line)
            continue
        if not answer.group(1).strip():
            blocks.append(textwrap.dedent("\n".join(current)).strip() or "(питання без тексту)")
        current = []
    return blocks


def undecided(text: str) -> list[str]:
    """Entries of the escalations log nobody closed: no `Status: CLOSED`, no filled `Human chose:`."""
    found = []
    for block in ENTRY.split(text)[1:]:
        chose = re.search(r"^- Human chose:[ \t]*(\S.*)$", block, re.MULTILINE)
        if "Status: CLOSED" not in block and not chose:
            found.append(block.splitlines()[0][3:].strip())
    return found


def still_parked(text: str) -> list[str]:
    """Items of the parked queue whose latest entry is not RESUMED, each with what it waits for."""
    latest: dict[str, tuple[str, str, str]] = {}
    entries = list(PARKED.finditer(text))
    for index, entry in enumerate(entries):
        body = text[entry.end(): entries[index + 1].start() if index + 1 < len(entries) else len(text)]
        needs = re.search(r"^- Blocked on:[ \t]*(.*)$", body, re.MULTILINE)
        when, item, status = entry.group(1), entry.group(2).strip(), entry.group(3)
        if item not in latest or when >= latest[item][0]:
            latest[item] = (when, status, needs.group(1).strip() if needs else "")
    return [f"{item} (від {when[:10]}) — чекає: {needs or 'не записано'}" for item, (when, status, needs) in latest.items() if status != "RESUMED"]


Asked = tuple[str, str, board.Task]  # a blocked task: its path, its text, what board.py reads in it


def question_lines(src: Source, asked: list[Asked]) -> list[str]:
    lines: list[str] = []
    for path, text, task in asked:
        blocks = open_questions(task.questions)
        if not blocks:
            continue
        name = posixpath.basename(path)
        lines.append(f"### {name} — {title_of(text, name)}")
        draft = f"tasks/blocked/report-{name}"
        if draft in src.files:
            lines.append(f"Що зроблено і чому питання — у чернетці звіту `{draft}`.")
        if task.gate:
            lines.append(f"Це питання поставили ворота (ескалація `{task.gate}`): відповідь `закрити` закриє її, інший текст — вказівка агентові.")
        if task.action:
            lines.append(f"Тут є дія виконавця `{task.action}`: відповідь `так` під тим питанням виконає її; інший текст — вказівка агентові.")
        for block in blocks:
            lines += ["", *(f"> {line}".rstrip() for line in block.splitlines()), "> **Відповідь:** _порожньо_"]
        lines.append("")
    return lines


def settings_lines(src: Source, asked: list[Asked]) -> list[str]:
    lines = [f"- `{posixpath.basename(path)}` чекає «так»: дію `apply-settings` виконає виконавець, не агент."
             for path, _, task in asked if task.action and not task.answered]
    proposal = src.show("docs/tasks/settings.json")
    if proposal and proposal != src.show(".claude/settings.json"):
        lines.append("- `docs/tasks/settings.json` відрізняється від живого `.claude/settings.json`: пропозицію не застосовано.")
    return lines or ["- Немає: жодна задача не чекає «так», пропозиція збігається з живим файлом або її немає."]


def escalation_lines(src: Source, state: Path, asked: list[Asked]) -> list[str]:
    lines = [f"- Ворота, на дошці: `{posixpath.basename(path)}` (ескалація `{task.gate}`)." for path, _, task in asked if task.gate]
    lines += [f"- Ворота, на цій машині: `{entry.get('stamp')}` — зріз {entry.get('slice') or 'не названо'}."
              for entry in load_json(state / "gate/escalations.json").get("open") or [] if isinstance(entry, dict)]
    lines += [f"- Журнал наглядача (`.engine/overseer/escalations.md`), без рішення: {entry}" for entry in undecided(src.show(".engine/overseer/escalations.md"))]
    lines += [f"- Відкладене (`.engine/overseer/parked.md`): {entry}" for entry in still_parked(src.show(".engine/overseer/parked.md"))]
    return lines or ["- Немає."]


def rule_lines(src: Source) -> list[str]:
    proposals = src.show(".engine/rule-proposals.md")
    lines = []
    for match in PROPOSAL.finditer(proposals):
        rule = re.search(r"^- Rule:[ \t]*(.*)$", proposals[match.end():].split("\n## ", 1)[0], re.MULTILINE)
        lines.append(f"- `{match.group(1)}`: {rule.group(1).strip() if rule else '(тексту правила немає)'}")
    return lines or ["- Немає (`.engine/rule-proposals.md`)."]


def waiting_section(src: Source, state: Path) -> list[str]:
    asked: list[Asked] = [(path, text, board.parse(text)) for path in src.column("blocked") for text in [src.show(path)]]
    total = sum(task.answers.count("") for _, _, task in asked)
    return [(f"Незаповнених відповідей: {total}, у задачах: {sum(1 for _, _, task in asked if '' in task.answers)} (тека `tasks/blocked/`). Відповідь пишеться в "
             "рядок «Відповідь:» файла задачі — у гілці або копією файла в теку вхідних задач; задача повертається в роботу, коли заповнено всі."), "",
            *question_lines(src, asked),
            "### Пропозиції налаштувань", "", *settings_lines(src, asked), "",
            "### Відкриті ескалації", "", *escalation_lines(src, state, asked), "",
            "### Пропозиції правил", "", *rule_lines(src)]


# ------------------------------------------------------------------ plan, candidates, health


def plan_section(src: Source) -> list[str]:
    todo = src.column("todo")
    if not todo:
        return ["У `todo/` порожньо."]
    place = {board.number_of(posixpath.basename(p)): c for c in ("todo", "doing", "blocked") for p in src.column(c)}
    place.update({board.number_of(s): "done" for s in src.done()})
    lines = []
    first_free = not src.column("doing")
    for index, path in enumerate(todo, 1):
        text = src.show(path)
        depends = board.parse(text).depends
        unmet = [n for n in depends if place.get(n) != "done"]
        line = f"{index}. `{posixpath.basename(path)}` — {title_of(text, 'без назви')}"
        if unmet:
            line += "; **стоїть**, чекає на: " + ", ".join(f"{n:03d} ({place.get(n) or 'такої задачі ніде немає'})" for n in unmet)
        else:
            line += f"; залежності: {', '.join(f'{n:03d}' for n in depends) + ' — готові' if depends else 'немає'}"
            line += " — **наступна**" if first_free else ""
            first_free = False
        lines.append(line)
    return lines


def candidates_section(src: Source, stems: list[str], period: Since) -> list[str]:
    lines: list[str] = []
    for stem in stems:
        found = sections(src.show(f"tasks/done/{stem}/report.md"))
        parts = [part for prefixes in CANDIDATE_PARTS if (part := pick(found, prefixes))]
        if parts:
            lines += [f"### Зі звіту {stem}", ""]
            for part in parts:
                lines += quoted(*part)
    passes = []
    for heading, body in sections(src.show(".engine/simplifier/report.md")):
        moment = as_utc(heading.split(" ", 1)[0].replace("Z", "+00:00"))
        if period.utc and moment and moment < period.utc:
            continue
        findings = [line[2:] for line in body.splitlines() if line.startswith("- `F-")]
        passes += [f"**{heading}** — знахідок: {len(findings)}", ""]
        passes += [f"- {f if len(f) <= FINDING_MAX else f[:FINDING_MAX].rstrip() + '…'}" for f in findings] + [""]
    if passes:
        lines += ["### Знахідки спрощувача для розбору (`.engine/simplifier/report.md`)", "", *passes]
    return lines or ["За цей період кандидатів немає: у нових звітах немає розділів «Відкладене» чи «Чого мені бракувало», знахідок спрощувача немає."]


def context_lines(src: Source) -> tuple[int, int] | None:
    """Lines and files of the persistent context: CLAUDE.md and everything it imports."""
    if "CLAUDE.md" not in src.files:
        return None
    seen: dict[str, int] = {}

    def walk(path: str, hops: int) -> None:
        if path in seen or path not in src.files:
            return
        text = src.show(path)
        seen[path] = len(text.splitlines())
        if hops >= MAX_HOPS:
            return
        for token in IMPORT_RE.findall(SPAN_RE.sub("", FENCE_RE.sub("", text))):
            walk(posixpath.normpath(posixpath.join(posixpath.dirname(path), token.rstrip(".,;:)"))), hops + 1)

    walk("CLAUDE.md", 0)
    return sum(seen.values()), len(seen)


def period_costs(costs: dict[str, dict[str, Any]], period: Since) -> list[tuple[str, float]]:
    spent = []
    for name, entry in sorted(costs.items()):
        attempts = [a for a in entry.get("attempts") or [] if isinstance(a, dict)
                    and (period.utc is None or ((when := as_utc(str(a.get("utc", "")))) is not None and when >= period.utc))]
        if attempts:
            spent.append((name, board_state.cost_of(attempts)))
    return spent


def test_run_line(src: Source) -> str:
    runs = [b for b in src.show(".engine/overseer/ledger.md").split("\n## ") if "run_all.sh" in b]
    if not runs:
        return "- Повний прогін тестів: запису в `.engine/overseer/ledger.md` немає."
    evidence = " ".join(line.strip().removeprefix("- ") for line in runs[-1].splitlines()[1:] if "run_all.sh" in line)
    return f"- Останній повний прогін тестів, за записом у ledger («{runs[-1].splitlines()[0].strip()}»): {evidence[:600]}"


def golden_line(src: Source) -> str:
    """The newest recorded run of the golden set, by the time written in the file itself."""
    newest: tuple[str, str, list[Any]] | None = None
    for path in sorted(p for p in src.files if GOLDEN.match(p)):
        try:
            data = json.loads(src.show(path))
        except ValueError:
            continue
        results = data.get("results") if isinstance(data, dict) else None
        recorded = str(data.get("recorded_utc", "")) if isinstance(data, dict) else ""
        if isinstance(results, list) and (newest is None or recorded > newest[0]):
            newest = (recorded, path, results)
    if newest is None:
        return "- Золотий набір: записаних результатів (`evals/baseline/*/results-*.json`) немає."
    met = sum(1 for r in newest[2] if isinstance(r, dict) and r.get("pass"))
    return f"- Золотий набір, найновіший запис `{newest[1]}` ({newest[0] or 'час не записано'}): {met} із {len(newest[2])} сценаріїв відповідають очікуванням."


def health_section(src: Source, costs: dict[str, dict[str, Any]], period: Since) -> list[str]:
    lines = [test_run_line(src), golden_line(src)]
    context = context_lines(src)
    if context:
        lines.append(f"- Постійний контекст (CLAUDE.md і все, що він імпортує): {context[0]} із {CONTEXT_BUDGET} рядків, файлів: {context[1]}.")
    if costs:
        spent = period_costs(costs, period)
        lines.append(f"- Витрати за період, за записами виконавця: ${sum(c for _, c in spent):.2f}"
                     + (" — " + ", ".join(f"{name} ${cost:.2f}" for name, cost in spent) if spent else "") + ".")
    else:
        lines.append("- Витрати за період: записів виконавця (`costs.json`) тут немає; суми по задачах — у розділах «Витрати» їхніх звітів.")
    return lines


# ------------------------------------------------------------------ the document


def review(root: Path, state: Path, remote: str, branch: str, given: str | None, offline: bool, now: datetime) -> str:
    src = source(root, remote, branch, offline)
    period = since(src, given)
    costs = task_costs(state)
    stems = new_done(src, period)
    head = src.log("-1", "--format=%cI%x09%s", src.sha).split("\t")
    lines = [f"# Огляд дошки — {stamp(now)}", "",
             f"Джерело: гілка `{src.name}`, commit `{src.sha[:7]}`" + (f" від {stamp(as_utc(head[0]))} — {head[1]}" if len(head) == 2 else "") + ".",
             *([f"Увага: {src.note}."] if src.note else []),
             f"Період для «Зроблено», кандидатів і витрат: {period.shown}. Огляд нічого не змінює.", ""]
    for title, body in (("Стан зараз", now_section(src, state, now)),
                        ("Зроблено", done_section(src, stems, costs)),
                        ("Чекає на власника", waiting_section(src, state)),
                        ("План", plan_section(src)),
                        ("Кандидати в нові задачі", candidates_section(src, stems, period)),
                        ("Здоров'я", health_section(src, costs, period))):
        lines += [f"## {title}", "", *body, ""]
    lines += ["---", f"Наступний огляд — лише нове після цього: `python3 .claude/unattended/board.py review --since {src.sha[:12]}`"]
    return "\n".join(lines) + "\n"
