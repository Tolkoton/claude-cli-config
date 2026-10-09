#!/usr/bin/env python3
"""The owner's two rules of board 053, where a machine can hold them.

  1. QUALITY OVER PRICE. A task carries no dollar limit. Since board 078 there is no category of
     paid runs: extra Claude sessions are ordinary work and need no leave, an old «Платні прогони:»
     line is ignored, and only the overseer's audit run keeps the owner's «Аудит потрібен: так»
     (the eval runners and the audit runner are checked in their own suites and in
     test_paid_run_gate.py). The task template carries no such line and no dollar limit, and the
     rules say what stands against a loop: BOARD_MAX_USD.
  2. TECHNICAL TERMS IN ENGLISH wherever the owner reads. The questions the scripts write
     (gates, rules, a stuck task, an open item), the anomaly journal and the owner's documents
     use overseer, simplifier, gates, runner, task board, inbox, slice… — and none of the
     Ukrainian renderings that stood there before. The questions are produced here by the
     real functions, not read from the source.

The two machine-read lines keep working in their wording before this board («Ескалація воріт:»,
«Дія виконавця:»): a question already lying in blocked/ is still the runner's to act on.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0
# The renderings the owner's rule retires. «Аудит потрібен:» is a field the board reads, not prose.
RETIRED = re.compile(r"наглядач|спрощувач|\bворота\b|\bворіт\b|\bворотам|виконавець|виконавц|\bзріз|\bгак(и|ів|а|у)?\b|\bдошк[аиуоюі]|"
                     r"вхідних задач|теку вхідних|\bкритик|планувальник|будівельник|тестувальник|менеджер|аналітик|пісочниц|"
                     r"мутаційн|золотий набір|\bаудит(?! потрібен)", re.IGNORECASE)
# Read by the owner, or written into what the owner reads.
OWNER_TEXT = ("tasks/README.md", "tasks/TEMPLATE.md", "templates/project/tasks/README.md", "templates/project/tasks/TEMPLATE.md",
              "templates/project/tasks/TEMPLATE-onboard.md", "docs/OWNER-GUIDE.md", ".claude/unattended/board.py",
              ".claude/unattended/board_review.py", ".claude/unattended/board-runner.sh", ".claude/unattended/owner_action.py",
              ".claude/hooks/gate.py", ".claude/hooks/lesson_queue.py", ".claude/hooks/maintain.py", ".claude/hooks/testing.py",
              ".claude/hooks/overseer_stop.py", ".claude/hooks/overseer_verdict.py", ".claude/hooks/goals.py", ".claude/hooks/hotfix.py",
              ".claude/hooks/simplifier.py", ".claude/hooks/bugfix.py")
TERMS = ("overseer", "simplifier", "critic", "planner", "builder", "tester", "test manager", "business analyst", "slice", "slice contract",
         "gates", "hook", "runner", "task board", "inbox", "audit", "golden set", "invariant", "property-based testing",
         "mutation testing", "spike", "sandbox")


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def retired(text: str) -> list[str]:
    """The lines of `text` that still carry a retired rendering. A line that reads the old
    wording of a machine line (a regular expression with both forms) is not prose."""
    return [line.strip()[:160] for line in text.splitlines() if RETIRED.search(line) and "(?:" not in line]


spec = importlib.util.spec_from_file_location("engine_board", ROOT / ".claude/unattended/board.py")
assert spec and spec.loader
board = importlib.util.module_from_spec(spec)
sys.modules["engine_board"] = board
spec.loader.exec_module(board)

print("the check itself: it sees a retired rendering, and lets the board's own field through")
check("negative — a line with «наглядач» is caught", retired("Поки питання відкрите, наглядач не приймає роботу.") != [])
check("negative — «виконавця дошки», «ворота», «зрізу», «теку вхідних задач», «аудиту» are each caught",
      all(retired(s) for s in ("відповідь виконавця дошки", "Ворота зупинили роботу", "тести зрізу x", "у теку вхідних задач", "після аудиту")))
check("«Аудит потрібен: так» is the board's field, not a rendering", retired("Аудит потрібен: так") == [])
check("the English terms pass", retired("Overseer тричі відхилив slice; gates червоні; runner узяв наступну задачу з task board.") == [])

print("the text the owner reads carries no retired rendering")
for rel in OWNER_TEXT:
    found = retired((ROOT / rel).read_text(encoding="utf-8"))
    check(rel, not found, found[:3])

print("the questions the scripts write, produced by the real functions")
with tempfile.TemporaryDirectory(prefix="owner-terms-") as tmp:
    tasks = Path(tmp) / "tasks"
    for column in board.COLUMNS:
        (tasks / column).mkdir(parents=True)
    b = board.Board(tasks)
    gate = board.gate_question(b, "2026-10-06T10:00:00Z", 3, "s1", ["src/a.py"], ["lint: E501"], "")
    text = gate.read_text(encoding="utf-8") if gate else ""
    check("the gates' question: gates, overseer, runner, slice — and nothing retired",
          all(w in text for w in ("Gates зупинили роботу", "overseer", "runner", "- Slice: s1", "Ескалація gates: 2026-10-06T10:00:00Z")) and not retired(text),
          retired(text) or text[:400])
    check("…and the board reads it as the gates' question", gate is not None and board.read(gate).gate == "2026-10-06T10:00:00Z")
    rule = board.rule_question(b, "abc12345", "Текст правила.", "Чому.", "задача 001", "прийняти", "a" * 64)
    text = rule.read_text(encoding="utf-8") if rule else ""
    check("the rule question: overseer advises, the runner acts — and nothing retired",
          "Рекомендація overseer-а: прийняти" in text and f"Дія runner-а: promote-rule {'a' * 64}" in text and not retired(text), retired(text) or text[:400])
    check("…and the board reads the action it offers", rule is not None and board.read(rule).action == "promote-rule")
    item = board.open_item(b, "blocked", "Overseer відклав юніт: 2", "Що сталося.", question="Що робити далі?")
    text = item.read_text(encoding="utf-8") if item else ""
    check("an open item: nothing retired in what the board adds around the words given", item is not None and not retired(text), retired(text))
    for reason, word in (("no-commit", "runner"), ("deadline", "runner"), ("budget", "BOARD_MAX_USD"), ("three-blocks", "overseer"), ("returned", "runner")):
        (tasks / "doing" / f"01{len(reason)}-stuck.md").write_text("# x\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Що зробити\n- …\n\n## Питання до власника\n", encoding="utf-8")
        parked = board.park(b, f"01{len(reason)}-stuck", reason, "3", "")
        text = parked.read_text(encoding="utf-8") if parked else ""
        check(f"a stuck task ({reason}): says «{word}», asks the owner, nothing retired",
              parked is not None and word in text and "Відповідь:" in text and not retired(text), retired(text) or text[-500:])
        if parked:
            parked.unlink()
    journal = (tasks / board.ANOMALIES).read_text(encoding="utf-8")
    check("the anomaly journal: its head and the runner's entries name the runner and the task board, nothing retired",
          "runner" in journal and "task board" in journal and not retired(journal), retired(journal))
    check("the budget question says the guard stops a loop and the owner's answer continues the task",
          "запобіжник" in board.PARK_REASONS["budget"][0] and "поверне задачу в чергу" in board.PARK_REASONS["budget"][1], board.PARK_REASONS["budget"])

print("a question asked before this board is still read")
old = board.parse("# 900\n\nЗалежить від: —\nАудит потрібен: ні\nЕскалація воріт: 2026-10-03T10:15:00Z\n\n## Питання до власника\n1. Закрити ескалацію?\n   Відповідь: так\n")
check("«Ескалація воріт:» is the gates' question, and «так» closes it", old.gate == "2026-10-03T10:15:00Z" and old.closes)
old = board.parse(f"# 062\n\n## Питання до власника\n1. Застосувати?\n   Дія виконавця: apply-settings {'b' * 64}\n   Відповідь: так\n")
check("«Дія виконавця:» is the offered action, and «так» approves it", old.action == "apply-settings" and old.action_arg == "b" * 64 and old.approves)
new = board.parse(f"# 062\n\n## Питання до власника\n1. Застосувати?\n   Дія runner-а: apply-settings {'b' * 64}\n   Відповідь: так\n")
check("«Дія runner-а:» is read the same", new.action == "apply-settings" and new.approves)
check("negative — a line that names another actor offers nothing", board.parse(f"# 1\n\n## Питання до власника\n1. Так?\n   Дія агента: apply-settings {'b' * 64}\n   Відповідь: так\n").action == "")

print("board 078: no category of paid runs — an old «Платні прогони:» line is ignored")
for header in ("Платні прогони: так", "Платні прогони: ні", "Платні прогони: до $5", "Платні прогони: так, до 5 доларів", "Платні прогони: так\nПлатні прогони: ні"):
    task = board.parse(f"# x\n\nЗалежить від: 1\nАудит потрібен: ні\n{header}\n\n## Що зробити\n- …\n")
    check(f"{header!r}: the task reads as if the line were not there", task.depends == (1,) and not task.audit and not hasattr(task, "paid"), task)
check("the board's reader keeps no paid-run guard", not any(hasattr(board, n) for n in ("paid_refusal", "paid_ceiling", "line_unread", "paid_leave", "PAID")))
with tempfile.TemporaryDirectory(prefix="owner-terms-audit-") as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    check("no task in doing/: the audit is refused", board.audit_refusal(tasks) is not None)
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: ні\nПлатні прогони: так\n\n## Що зробити\n", encoding="utf-8")
    check("an old «Платні прогони: так» opens no audit: refused, and the task is named", "001-a.md" in str(board.audit_refusal(tasks)), board.audit_refusal(tasks))
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: так\nПлатні прогони: до $5\n\n## Що зробити\n", encoding="utf-8")
    check("«Аудит потрібен: так» beside an old unreadable line: the audit goes on — the old line stops nothing", board.audit_refusal(tasks) is None)
    check("…and the task in hand is the one the extra sessions are booked to", board.in_hand(tasks) == "001-a")
    (tasks / "doing/002-b.md").write_text("# 002\n\nАудит потрібен: так\n", encoding="utf-8")
    check("negative — two tasks in doing/: the audit is refused, and no task is in hand for the books", board.audit_refusal(tasks) is not None and board.in_hand(tasks) == "")

print("both rules are written where they are read")
rules = (ROOT / ".claude/engine-rules.md").read_text(encoding="utf-8")
check("the engine rules: quality over price, no dollar limit, BOARD_MAX_USD against a loop",
      "Quality over price" in rules and "no dollar limit" in rules and "BOARD_MAX_USD" in rules and "or a dollar limit" not in rules)
check("the engine rules: technical terms stay English wherever the owner reads, with the reference named",
      "technical terms stay English" in rules and "`unattended.md`" in rules)
reference = (ROOT / ".claude/references/unattended.md").read_text(encoding="utf-8")
check("the reference carries both rules and each term of the owner's list",
      "Quality over price" in reference and "BOARD_MAX_USD" in reference and all(t in " ".join(reference.split()) for t in TERMS),
      [t for t in TERMS if t not in " ".join(reference.split())])
for rel in ("tasks/README.md", "templates/project/tasks/README.md", "docs/OWNER-GUIDE.md"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    check(f"{rel}: «Якість понад ціну» with BOARD_MAX_USD, and the terms rule with the owner's list",
          "Якість понад ціну" in text and "BOARD_MAX_USD" in text and "Технічні терміни — англійською" in text and all(t in " ".join(text.split()) for t in TERMS),
          [t for t in TERMS if t not in " ".join(text.split())])
    check(f"{rel}: no dollar limit is asked of a task, and no leave for extra sessions (board 078)",
          "лімітом у доларах" not in text and "Платні прогони: так" not in text and "задача 078" in text)
for rel in ("tasks/README.md", "templates/project/tasks/README.md"):
    flat = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
    check(f"{rel}: says what board 078 decided — extra sessions are ordinary work, booked per task, the audit stays the owner's",
          "## Додаткові сесії Claude" in (ROOT / rel).read_text(encoding="utf-8") and "Окремої згоди на них не треба" in flat
          and "extra-sessions.jsonl" in flat and "Аудит потрібен: так" in flat and "просто ігнорується" in flat
          and "Згода — лише слово «так» на початку рядка" not in flat)
for rel in ("tasks/TEMPLATE.md", "templates/project/tasks/TEMPLATE.md"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    check(f"{rel}: no «Платні прогони:» line (board 078) and no dollar sum anywhere",
          "Платні прогони" not in text and not re.search(r"\d\s*(?:долар|\$|USD)", text) and "Аудит потрібен: ні" in text)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
