#!/usr/bin/env python3
"""The owner's review, `board.py review` (.claude/unattended/board_review.py, board 009).

Everything runs on a synthetic repository: a work checkout (where the runner would be), a bare
`origin`, and a second clone (where the owner or the operator would be). Commit dates are fixed,
so `--since <date>` is deterministic.

WHAT IS CHECKED
  - the review changes no file: every byte under the clone — `.git` included — is the same after
    it, with and without the runner's state files; when the commit has to be fetched first, only
    objects are added: no ref, no index, no HEAD, nothing in the working tree changes;
  - the state is the branch in origin, not the checkout it is run from: a clone that never saw
    the newest commit shows it, and the runner's checkout in the middle of a task (a dirty tree,
    a half-moved task, an unpushed commit) shows what was pushed and stays as it was;
  - `--since` (a commit, a date) shows only what is new; without it the newest version tag is the
    start; the document ends with the command for the next review, and that command shows nothing
    done twice;
  - every unfilled `Відповідь:` in blocked/ is found, in each way an owner's file may write the
    line — and a filled one, and the template's hint in a comment, are not;
  - the seven sections are there, in order, each with what the task asks of it; the anomaly
    journal's new entries are a section of their own (board 021);
  - origin out of reach: the last known state with a note; nothing known at all: exit 2;
  - the session command and the operator's instruction exist and name the same command.
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
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
UNATTENDED = ROOT / ".claude/unattended"
SCRIPT = UNATTENDED / "board.py"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, UNATTENDED / f"{name}.py")
    assert spec is not None and spec.loader is not None, name
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


board = load("board")
board_state = load("board_state")
review = load("board_review")

PASS = FAIL = 0
BRANCH = "unattended/work"


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def git(cwd: Path, *args: str, date: str = "2026-01-01T00:00:00Z") -> str:
    env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False, env=env)
    assert done.returncode == 0, (args, done.stderr)
    return done.stdout.strip()


def cli(root: Path, *args: str, state: Path | None = None) -> subprocess.CompletedProcess[str]:
    """The real command, in `root`. The state directory is named every time, so a test never
    reads this repository's own."""
    command = [sys.executable, str(SCRIPT), "--root", str(root), "review", "--state-dir", str(state or root / "no-state"), *args]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def snapshot(root: Path, skip: tuple[str, ...] = ()) -> dict[str, str]:
    found = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not any(rel.startswith(prefix) for prefix in skip):
            found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


TITLES = ["Стан зараз", "Зроблено", "Чекає на власника", "Аномалії", "План", "Кандидати в нові задачі", "Здоров'я"]


def section(document: str, title: str) -> str:
    """The text of one `## ` section of the review."""
    start = document.index(f"\n## {title}\n")
    ends = [at for other in TITLES if (at := document.find(f"\n## {other}\n", start + 1)) != -1]
    return document[start: min(ends, default=len(document))]


def task(title: str, deps: str = "—", questions: str = "") -> str:
    return (f"# {title}\n\nЗалежить від: {deps}\nАудит потрібен: ні\n\n## Що зробити\n- щось\n\n"
            f"## Готово, коли\n- готово\n\n## Питання до власника\n{questions}")


def report(stem: str, extra: str = "") -> str:
    return (f"# {stem}: звіт\n\n## Що змінилось для власника\n- ЗМІНА-{stem}\n\n## Демонстрація на хвилину\n```text\n$ demo-{stem}\n## not a heading\n```\n\n"
            f"## Витрати\n- ВИТРАТИ-{stem}\n\n## Діапазон commit-ів\n- COMMITS-{stem}\n\n## Відкладене\n- ВІДКЛАДЕНЕ-{stem}\n\n{extra}"
            f"## Рішення, які я ухвалив сам\n- РІШЕННЯ-{stem}\n")


SHA = "a" * 64
QUESTIONS = f"""<!-- Приклад:
1. Питання-з-коментаря?
   Відповідь:
-->
Варіанти: ВАРІАНТ-А або ВАРІАНТ-Б.

1. ПИТАННЯ-ОДИН — звичайний рядок?
   Відповідь:
2. ПИТАННЯ-ДВА — уже з відповіддю?
   Відповідь: так, роби
3. ПИТАННЯ-ТРИ — у цитаті?
   > Відповідь:
4. ПИТАННЯ-ЧОТИРИ — жирним?
   **Відповідь:**
5. ПИТАННЯ-П'ЯТЬ — застосувати пропозицію налаштувань?
   Дія виконавця: apply-settings {SHA}
   Відповідь:
"""
GATE = ("# 900 — Ворота зупинили роботу\n\nЗалежить від: —\nАудит потрібен: ні\nЕскалація воріт: 20260101T000000Z\n\n"
        "## Питання до власника\n1. ПИТАННЯ-ВОРІТ — закрити чи виправляти?\n   Відповідь:\n")


def build() -> tuple[Path, Path, Path, dict[str, str]]:
    """work (the runner's checkout), origin (bare), clone (the owner's), and the commits by name."""
    top = Path(tempfile.mkdtemp(prefix="board-review-"))
    work, origin, clone = top / "work", top / "origin.git", top / "clone"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    for column in board.COLUMNS:
        write(work, f"tasks/{column}/.gitkeep", "")
    write(work, "CLAUDE.md", "@AGENTS.md\n\n# project\nline\n")
    write(work, "AGENTS.md", "# agents\none\ntwo\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "base", date="2025-12-01T00:00:00Z")
    git(work, "tag", "v0.1.0")
    git(work, "switch", "-q", "-c", BRANCH)
    commits = {}

    write(work, "tasks/done/001-first/task.md", task("001 — Перша"))
    write(work, "tasks/done/001-first/report.md", report("001-first"))
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "board: 001-first → done", date="2026-01-01T00:00:00Z")
    commits["first"] = git(work, "rev-parse", "HEAD")

    write(work, "tasks/done/002-second/task.md", task("002 — Друга"))
    write(work, "tasks/done/002-second/report.md", report("002-second", "## Чого мені бракувало\n- БРАКУВАЛО-002-second\n\n"))
    write(work, "tasks/blocked/008-asks.md", task("008 — Питає", questions=QUESTIONS))
    write(work, "tasks/blocked/report-008-asks.md", "# чернетка звіту\n")
    write(work, "tasks/blocked/900-gate-escalation-20260101T000000Z.md", GATE)
    write(work, "tasks/doing/009-in-work.md", task("009 — У роботі"))
    write(work, "tasks/todo/020-free.md", task("020 — Вільна", deps="001"))
    write(work, "tasks/todo/030-stands.md", task("030 — Стоїть", deps="008, 020"))
    write(work, "tasks/todo/040-attended.md", task("040 — ЗАДАЧА-З-ВЛАСНИКОМ").replace("Аудит потрібен:", "Потрібна присутність власника: так\nАудит потрібен:"))
    write(work, "docs/tasks/settings.json", '{"proposal": true}\n')
    write(work, ".claude/settings.json", '{"proposal": false}\n')
    write(work, ".engine/rule-proposals.md", "# Rule proposals\n\n## RP-ab12 — 2026-01-02 — PROPOSED\n- Rule: ПРАВИЛО-ПРОПОЗИЦІЯ\n- Why: бо\n\n"
                                             "## RP-cd34 — 2026-01-02 — PROMOTED\n- Rule: ПРАВИЛО-ВЖЕ-ПРИЙНЯТЕ\n")
    write(work, ".engine/overseer/escalations.md", "# log\n\n## 2026-01-02T00:00:00Z — DESIGN_FORK — ЕСКАЛАЦІЯ-ВІДКРИТА\n- Question: що обрати?\n- Human chose:\n\n"
                                                   "## 2026-01-02T01:00:00Z — AUTONOMOUS — ЕСКАЛАЦІЯ-ЗАКРИТА\n- Decision: так\n- Status: CLOSED\n\n"
                                                   "## 2026-01-02T02:00:00Z — DESIGN_FORK — ЕСКАЛАЦІЯ-ВИРІШЕНА\n- Human chose: друге\n")
    write(work, ".engine/overseer/parked.md", "# parked\n\n## 2026-01-02T00:00:00Z — ВІДКЛАДЕНЕ-ЧЕКАЄ — PARKED\n- Blocked on: ключ від сервісу\n\n"
                                              "## 2026-01-02T00:00:00Z — ВІДКЛАДЕНЕ-ПОВЕРНУТЕ — PARKED\n- Blocked on: щось\n\n"
                                              "## 2026-01-03T00:00:00Z — ВІДКЛАДЕНЕ-ПОВЕРНУТЕ — RESUMED\n- Blocked on: —\n")
    write(work, ".engine/overseer/ledger.md", "# ledger\n\n## 2026-01-02T00:00:00Z — task — BUILT\n- Evidence: `bash tests/run_all.sh` 12 suites green; ПРОГІН-ТЕСТІВ\n")
    write(work, ".engine/simplifier/report.md", "# Simplifier\n\n## 2026-02-01T00:00:00Z — pass\n\n### confirm (1)\n- `F-11111111` **a.py:1** — dead_code: ЗНАХІДКА-СПРОЩУВАЧА\n  - evidence: read\n")
    write(work, "tasks/ANOMALIES.md", "# Журнал аномалій дошки\n\nПише виконавець.\n\n"
                                      "## 2026-01-01T00:00:00Z — 001-first\n- Що сталося: АНОМАЛІЯ-СТАРА\n- Що зроблено: ЗРОБЛЕНО-СТАРЕ\n\n"
                                      "## 2026-02-01T00:00:00Z — дошка\n- Що сталося: АНОМАЛІЯ-НОВА\n- Що зроблено: ЗРОБЛЕНО-НОВЕ\n")
    write(work, "evals/baseline/box/results-a.json", json.dumps({"recorded_utc": "2026-01-01T00:00:00Z", "results": [{"pass": True}]}))
    write(work, "evals/baseline/box/results-b.json", json.dumps({"recorded_utc": "2026-02-01T00:00:00Z", "results": [{"pass": True}, {"pass": True}, {"pass": False}]}))
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "board: 002-second → done", date="2026-02-01T00:00:00Z")
    commits["second"] = git(work, "rev-parse", "HEAD")

    git(top, "init", "-q", "--bare", "-b", "main", str(origin))
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "origin", "main", BRANCH, "--tags")
    git(top, "clone", "-q", str(origin), str(clone))
    return work, origin, clone, commits


def state_files(top: Path, status: str) -> Path:
    state = top / "state"
    write(state, "board/status", status + "\n")
    write(state, "board/costs.json", json.dumps({"tasks": {
        "001-first": {"cost_usd": 1.5, "outcome": "done", "attempts": [{"utc": "2026-01-01T00:00:00Z", "session_id": "a", "reported_usd": 1.5}]},
        "002-second": {"cost_usd": 2.25, "outcome": "done", "attempts": [{"utc": "2026-02-01T00:00:00Z", "session_id": "b", "reported_usd": 2.25}]},
        "009-in-work": {"cost_usd": 0.5, "started_utc": "2026-02-01T00:00:00Z", "attempts": [{"utc": "2026-02-02T00:00:00Z", "session_id": "c", "reported_usd": 0.5}]},
    }}))
    write(state, "gate/escalations.json", json.dumps({"open": [{"stamp": "ШТАМП-ВОРІТ", "slice": "зріз"}], "closed": []}))
    return state


work, origin, clone, commits = build()
top = work.parent

# --- the document ---------------------------------------------------------------------------
print("the document")
r = cli(clone)
doc = r.stdout
check("the review runs in a clone that never checked the work branch out", r.returncode == 0 and doc.startswith("# "), r.stderr)
places = [doc.find(f"\n## {title}") for title in TITLES]
check("the seven sections are there, in the task's order", all(p != -1 for p in places) and places == sorted(places), places)
check("it says which commit of origin it read", commits["second"][:7] in doc.split("\n## ")[0] and f"origin/{BRANCH}" in doc, doc[:400])
done_part = section(doc, "Зроблено")
check("without --since the newest version tag is the start: both finished tasks", "v0.1.0" in doc.split("\n## ")[0]
      and "ЗМІНА-001-first" in done_part and "ЗМІНА-002-second" in done_part, done_part)
check("a finished task shows what changed, the demo, the decisions, the cost, the commits", all(
    f"{word}-002-second" in done_part for word in ("ЗМІНА", "$ demo", "РІШЕННЯ", "ВИТРАТИ", "COMMITS")) and commits["second"][:7] in done_part, done_part)
check("a `## ` line inside a code block of a report is not taken for a heading", "## not a heading\n```" in done_part, done_part)

# --- nothing is changed ---------------------------------------------------------------------
print("read-only")
before = snapshot(clone)
r = cli(clone)
check("the review changes no file — the working tree and .git byte for byte", r.returncode == 0 and snapshot(clone) == before,
      sorted(set(snapshot(clone).items()) ^ set(before.items()))[:6])
state = state_files(top, "state=running task=009-in-work since=2026-02-01T00:00:00Z")
state_before = snapshot(state)
r = cli(clone, state=state)
check("…nor with the runner's state files, which are left as they were", r.returncode == 0 and snapshot(clone) == before and snapshot(state) == state_before)
check("it writes nothing into the directory it is run from either", not (clone / "no-state").exists())

# --- --since ----------------------------------------------------------------------------------
print("--since")
done_part = section(cli(clone, "--since", commits["first"]).stdout, "Зроблено")
check("--since <commit>: only the task finished after it", "ЗМІНА-002-second" in done_part and "001-first" not in done_part, done_part)
done_part = section(cli(clone, "--since", "2026-01-15").stdout, "Зроблено")
check("--since <date>: the same", "ЗМІНА-002-second" in done_part and "001-first" not in done_part, done_part)
both = section(cli(clone, "--since", "2025-12-15").stdout, "Зроблено")
check("--since an earlier date: both", "ЗМІНА-001-first" in both and "ЗМІНА-002-second" in both, both)
candidates = section(cli(clone, "--since", commits["first"]).stdout, "Кандидати в нові задачі")
check("the candidates follow --since too", "ВІДКЛАДЕНЕ-002-second" in candidates and "ВІДКЛАДЕНЕ-001-first" not in candidates, candidates)
late = section(cli(clone, "--since", "2026-02-15").stdout, "Кандидати в нові задачі")
check("…and so do the simplifier's passes: an older pass is not shown again", "ЗНАХІДКА-СПРОЩУВАЧА" in candidates and "ЗНАХІДКА-СПРОЩУВАЧА" not in late
      and "кандидатів немає" in late, late)
r = cli(clone, "--since", "не-commit-і-не-дата")
check("--since that is neither a commit nor a date: exit 2 and no document", r.returncode == 2 and r.stdout == "" and "--since" in r.stderr, r)
last = doc.rstrip().splitlines()[-1]
check("the document ends with the command for the next review", f"board.py review --since {commits['second'][:12]}" in last, last)
again = cli(clone, "--since", commits["second"][:12])
check("…and that command shows nothing done twice, while the open questions stay", again.returncode == 0
      and "ЗМІНА-" not in again.stdout and "нових готових задач немає" in section(again.stdout, "Зроблено")
      and "ПИТАННЯ-ОДИН" in again.stdout, section(again.stdout, "Зроблено"))
waits = section(cli(clone, "--since", commits["second"][:12]).stdout, "Чекає на власника")

# --- every unfilled answer --------------------------------------------------------------------
print("unfilled answers")
asks = board.parse((work / "tasks/blocked/008-asks.md").read_text(encoding="utf-8"))
blocks = review.open_questions(asks.questions)
check("the fixture: five answers, one filled", len(asks.answers) == 5 and asks.answers.count("") == 4, asks.answers)
check("one block per unfilled answer, whichever way the line is written", len(blocks) == 4
      and [n for n in ("ОДИН", "ДВА", "ТРИ", "ЧОТИРИ", "П'ЯТЬ") if any(f"ПИТАННЯ-{n}" in b for b in blocks)] == ["ОДИН", "ТРИ", "ЧОТИРИ", "П'ЯТЬ"], blocks)
check("the context above the first question comes with it", "ВАРІАНТ-А або ВАРІАНТ-Б" in blocks[0], blocks[0])
waiting = section(doc, "Чекає на власника")
check("the document has every unfilled one, and the gate's", all(f"ПИТАННЯ-{n}" in waiting for n in ("ОДИН", "ТРИ", "ЧОТИРИ", "П'ЯТЬ", "ВОРІТ")), waiting)
check("a filled answer and the template's hint are not asked again", "ПИТАННЯ-ДВА" not in waiting and "Питання-з-коментаря" not in waiting, waiting)
check("the count is said: five unfilled answers in two tasks", any("5" in line for line in waiting.splitlines()[:4]) and "008-asks.md" in waiting and "900-gate-escalation" in waiting, waiting.splitlines()[:4])
check("the draft report of a blocked task is pointed at", "tasks/blocked/report-008-asks.md" in waiting, waiting)
check("a settings proposal that waits for «так» is named as one, and that it differs from the live file", "apply-settings" in waiting
      and "docs/tasks/settings.json" in waiting and "відрізняється" in waiting, waiting)
check("the gate's question is named as one", "20260101T000000Z" in waiting and "закрити" in waiting, waiting)
check("open escalations: the one without a decision — not the closed, not the answered", "ЕСКАЛАЦІЯ-ВІДКРИТА" in waiting
      and "ЕСКАЛАЦІЯ-ЗАКРИТА" not in waiting and "ЕСКАЛАЦІЯ-ВИРІШЕНА" not in waiting, waiting)
check("parked: the item whose latest entry is PARKED — not the resumed one", "ВІДКЛАДЕНЕ-ЧЕКАЄ" in waiting and "ключ від сервісу" in waiting
      and "ВІДКЛАДЕНЕ-ПОВЕРНУТЕ" not in waiting, waiting)
check("rule proposals: the PROPOSED one only", "ПРАВИЛО-ПРОПОЗИЦІЯ" in waiting and "ПРАВИЛО-ВЖЕ-ПРИЙНЯТЕ" not in waiting, waiting)
with_state = cli(clone, state=state).stdout
check("with the state files: the gate's open escalation of this machine", "ШТАМП-ВОРІТ" in section(with_state, "Чекає на власника"))
check("--since does not hide what waits", waits == waiting, waits)
attended_part = waiting.split("### Задачі, що потребують вашої присутності", 1)[-1].split("\n### ", 1)[0]
check("a task that needs the owner present is under «Чекає на власника», by name and title (board 016)", "040-attended.md" in attended_part
      and "ЗАДАЧА-З-ВЛАСНИКОМ" in attended_part and "tasks/README.md" in attended_part, waiting)
check("…and an ordinary todo task is not there", "020-free.md" not in attended_part and "030-stands.md" not in attended_part, attended_part)
check("…its unanswered-question count is not disturbed by it", "040-attended.md" not in waiting.split("### Задачі, що потребують вашої присутності", 1)[0], waiting)

# --- the anomaly journal (board 021) ------------------------------------------------------------
print("anomalies")
odd = section(doc, "Аномалії")
check("the journal's entries are a section of their own: time, task, what happened, what was done", all(word in odd for word in
      ("2026-01-01 00:00 UTC — `001-first`", "АНОМАЛІЯ-СТАРА", "ЗРОБЛЕНО-СТАРЕ", "`дошка`", "АНОМАЛІЯ-НОВА", "ЗРОБЛЕНО-НОВЕ"))
      and "Нових записів за період: 2; усього в журналі `tasks/ANOMALIES.md`: 2" in odd and odd.find("АНОМАЛІЯ-СТАРА") < odd.find("АНОМАЛІЯ-НОВА"), odd)
odd = section(cli(clone, "--since", "2026-01-15").stdout, "Аномалії")
check("--since shows the new entries only, and says how many the journal holds", "АНОМАЛІЯ-НОВА" in odd and "АНОМАЛІЯ-СТАРА" not in odd
      and "Нових записів за період: 1; усього в журналі `tasks/ANOMALIES.md`: 2" in odd, odd)
odd = section(cli(clone, "--since", commits["second"]).stdout, "Аномалії")
check("nothing new since the last review: the section says so with a zero", "Нових записів за період: 0" in odd and "АНОМАЛІЯ" not in odd, odd)
odd = section(cli(clone, "--branch", "main").stdout, "Аномалії")
check("no journal at all: the section says the runner met nothing odd", "порожній" in odd and "АНОМАЛІЯ" not in odd, odd)

# --- the plan, the candidates, the health -----------------------------------------------------
print("plan, candidates, health")
plan = section(doc, "План")
check("the plan: todo/ in order", plan.find("020-free.md") != -1 and plan.find("020-free.md") < plan.find("030-stands.md"), plan)
line_030 = next(line for line in plan.splitlines() if "030-stands.md" in line)
line_020 = next(line for line in plan.splitlines() if "020-free.md" in line)
check("…what stands on a dependency says which one and where it is", "008" in line_030 and "blocked" in line_030 and "020" in line_030 and "todo" in line_030, line_030)
check("…and the one that can start is not said to stand", "стоїть" not in line_020 and "стоїть" in line_030, line_020)
line_040 = next(line for line in plan.splitlines() if "040-attended.md" in line)
check("…an attended task is in the plan as one the runner does not take, never as «наступна»", "лише з присутнім власником" in line_040
      and "наступна" not in line_040, line_040)
candidates = section(doc, "Кандидати в нові задачі")
check("candidates: «Відкладене» and «Чого мені бракувало» of the finished reports", "ВІДКЛАДЕНЕ-001-first" in candidates
      and "ВІДКЛАДЕНЕ-002-second" in candidates and "БРАКУВАЛО-002-second" in candidates, candidates)
check("candidates: the simplifier's findings", "ЗНАХІДКА-СПРОЩУВАЧА" in candidates and "F-11111111" in candidates, candidates)
health = section(doc, "Здоров'я")
check("health: the last full test run on record", "ПРОГІН-ТЕСТІВ" in health, health)
check("health: the newest golden-set file, two of three as expected", "results-b.json" in health and "2 із 3" in health and "results-a.json" not in health, health)
check("health: the persistent context, counted through the import", "7 із 200" in health, health)
check("health: without the state files it says the costs are not visible", "costs.json" in health and "$" not in health, health)
health = section(with_state, "Здоров'я")
check("health: the costs of the period (all three tasks since the tag)", "$4.25" in health, health)
health = section(cli(clone, "--since", "2026-01-15", state=state).stdout, "Здоров'я")
check("…and of a shorter period only what was spent in it", "$2.75" in health and "$4.25" not in health, health)

# --- the state now ----------------------------------------------------------------------------
print("the state now")
now = section(with_state, "Стан зараз")
check("from the state files: the task, that the runner works, the cost", "009-in-work" in now and "працює" in now and "$0.50" in now, now)
for status, said in (("state=waiting-limit task=009-in-work since=2026-02-01T00:00:00Z", "ліміт"),
                     ("state=stalled task=009-in-work since=2026-02-01T00:00:00Z reason=no-commit", "no-commit"),
                     ("state=waiting-owner task=- since=2026-02-01T00:00:00Z", "чекає власника")):
    now = section(cli(clone, state=state_files(top, status)).stdout, "Стан зараз")
    check(f"…{status.split()[0]} is said in words, with its reason", said in now, now)
now = section(doc, "Стан зараз")
check("without the state files: from git — the task in doing/ and since when", "009-in-work.md" in now and "2026-02-01" in now and "git" in now, now)
elapsed = review.elapsed(datetime(2026, 2, 1, tzinfo=UTC), datetime(2026, 2, 2, 3, 4, tzinfo=UTC))
check("a duration is said in days, hours and minutes", elapsed == "1 дн 3 год 4 хв", elapsed)

# --- origin, not the checkout -----------------------------------------------------------------
print("origin, not the checkout")
write(work, "tasks/done/003-third/task.md", task("003 — Третя"))
write(work, "tasks/done/003-third/report.md", report("003-third"))
git(work, "add", "-A")
git(work, "commit", "-q", "-m", "board: 003-third → done", date="2026-03-01T00:00:00Z")
commits["third"] = git(work, "rev-parse", "HEAD")
git(work, "push", "-q", "origin", BRANCH)
before = snapshot(clone, skip=(".git/objects/",))
refs = git(clone, "for-each-ref")
r = cli(clone)
check("a clone that never fetched the newest commit shows it", r.returncode == 0 and "ЗМІНА-003-third" in r.stdout and commits["third"][:7] in r.stdout, r.stderr)
check("…and only objects were added: no ref, no index, no HEAD, no FETCH_HEAD, no file of the tree",
      snapshot(clone, skip=(".git/objects/",)) == before and git(clone, "for-each-ref") == refs,
      sorted(set(snapshot(clone, skip=(".git/objects/",)).items()) ^ set(before.items()))[:6])

# The runner's checkout in the middle of a task: an unpushed commit, a task half moved, an edit,
# a new file. The review reads what origin has and leaves all of it alone.
write(work, "tasks/done/004-unpushed/task.md", task("004 — Не надіслана"))
write(work, "tasks/done/004-unpushed/report.md", report("004-unpushed"))
git(work, "add", "-A")
git(work, "commit", "-q", "-m", "board: 004-unpushed → done", date="2026-03-02T00:00:00Z")
(work / "tasks/doing/009-in-work.md").rename(work / "tasks/blocked/009-in-work.md")
write(work, "tasks/blocked/008-asks.md", "зіпсовано посеред запису")
write(work, "src/half.py", "def half(:\n")
dirty = git(work, "status", "--porcelain")
before = snapshot(work)
r = cli(work, state=state_files(top, "state=running task=009-in-work since=2026-02-01T00:00:00Z"))
check("in the runner's checkout mid-task the review works", r.returncode == 0 and all(f"\n## {t}" in r.stdout for t in TITLES), r.stderr)
check("…shows what origin has: the pushed task, not the unpushed one, the questions as they were pushed",
      "ЗМІНА-003-third" in r.stdout and "004-unpushed" not in r.stdout and "ПИТАННЯ-ОДИН" in r.stdout and "зіпсовано" not in r.stdout)
check("…says the runner is on the task", "009-in-work" in section(r.stdout, "Стан зараз") and "працює" in section(r.stdout, "Стан зараз"))
check("…and leaves the checkout exactly as it was", snapshot(work) == before and git(work, "status", "--porcelain") == dirty)

# --- origin out of reach ----------------------------------------------------------------------
print("origin out of reach")
r = cli(clone, "--offline")
check("--offline: the last state this clone knows, and it says so", r.returncode == 0 and "ЗМІНА-002-second" in r.stdout
      and "ЗМІНА-003-third" not in r.stdout and "--offline" in r.stdout.split("\n## ")[0], r.stdout[:500])
git(clone, "remote", "set-url", "origin", str(top / "nowhere.git"))
r = cli(clone)
check("origin unreachable: the last known state, with a note", r.returncode == 0 and "ЗМІНА-002-second" in r.stdout
      and "недосяжний" in r.stdout.split("\n## ")[0], r.stdout[:500] + r.stderr)
bare = top / "empty"
bare.mkdir()
git(bare, "init", "-q", "-b", "main")
r = cli(bare)
check("no origin and nothing known: exit 2, a reason, no document", r.returncode == 2 and r.stdout == "" and BRANCH in r.stderr, r)
shutil.copytree(clone, top / "elsewhere")
git(top / "elsewhere", "remote", "set-url", "origin", str(origin))
r = cli(top / "elsewhere", "--branch", "unattended/absent")
check("a branch origin does not have: exit 2", r.returncode == 2 and "unattended/absent" in r.stderr, r)

# --- the session command and the operator's instruction ---------------------------------------
print("the command and the manual")
command = (ROOT / ".claude/commands/review.md").read_text(encoding="utf-8")
check("/review exists and runs the review", "board.py review" in command and command.startswith("---\ndescription:"), command[:200])
check("/review writes into the inbox: BOARD_INBOX, by default ~/engine-ops/tasks-inbox", "BOARD_INBOX" in command and "~/engine-ops/tasks-inbox" in command)
check("/review says it changes nothing else", "tasks/TEMPLATE.md" in command and "git show" in command)
for manual in ("tasks/README.md", "templates/project/tasks/README.md"):
    check(f"{manual} tells the operator how to run the review and send it", "board.py review" in (ROOT / manual).read_text(encoding="utf-8"))
check("board.py lists the command", "board.py review" in (board.__doc__ or ""))

shutil.rmtree(top, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
