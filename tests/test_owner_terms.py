#!/usr/bin/env python3
"""The owner's two rules of board 053, where a machine can hold them.

  1. QUALITY OVER PRICE. A task carries no dollar limit. The owner's leave for paid runs is the
     line «Платні прогони: так» — no number; a number, when the owner wrote one, is a ceiling.
     board.py reads that line once, for every paid-run guard (the eval runners and the audit
     runner are checked in their own suites and in test_paid_run_gate.py). The task template
     carries no dollar limit, and the rules say what stands against a loop: BOARD_MAX_USD.
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

print("«Платні прогони: так» — the owner's leave, no number")


def paid(value: str) -> tuple[bool, float | None]:
    task = board.parse(f"# x\n\nЗалежить від: —\nАудит потрібен: ні\nПлатні прогони: {value}\n\n## Що зробити\n- …\n")
    return task.paid, task.paid_ceiling


for value in ("так", "Так.", "**так**", "так — два повні audit-и", "прогони simplifier-а на новому наборі — скільки потрібно", "нічні прогони, скільки треба"):
    check(f"«{value}»: leave, no ceiling", paid(value) == (True, None), paid(value))
for value, ceiling in (("так, не більше 30 доларів", 30.0), ("лише евалуація, ліміт 12,5 $", 12.5), ("до 50 USD", 50.0)):
    check(f"«{value}»: leave, and the number is the ceiling", paid(value) == (True, ceiling), paid(value))
for value in ("ні", "Ні.", "ні, не треба", "немає", "—", "-", "", "  "):
    check(f"negative — «{value}»: no leave", paid(value) == (False, None), paid(value))
check("negative — a task without the line: no leave", not board.parse("# x\n\nАудит потрібен: ні\n\n## Що зробити\n").paid)
check("negative — the line quoted inside a sentence is not the line",
      not board.parse("# x\n\n## Що зробити\n- Захист приймає рядок «Платні прогони: так» без числа.\n").paid)
check("negative — the line inside a comment is not the line", not board.parse("# x\n\n<!-- Платні прогони: так -->\n\n## Що зробити\n").paid)
with tempfile.TemporaryDirectory(prefix="owner-terms-paid-") as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    check("no task in doing/: paid runs refused, the audit too", board.paid_refusal(tasks) is not None and board.audit_refusal(tasks) is not None)
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: ні\nПлатні прогони: ні\n\n## Що зробити\n", encoding="utf-8")
    check("negative — the template's own «Платні прогони: ні»: refused, and the task is named",
          "001-a.md" in str(board.paid_refusal(tasks)) and "001-a.md" in str(board.audit_refusal(tasks)), board.paid_refusal(tasks))
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: ні\nПлатні прогони: так\n\n## Що зробити\n", encoding="utf-8")
    check("«Платні прогони: так»: paid runs allowed, no ceiling", board.paid_refusal(tasks) is None and board.paid_ceiling(tasks) is None)
    check("…and it is leave for the paid audit as well", board.audit_refusal(tasks) is None)
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: так\n\n## Що зробити\n", encoding="utf-8")
    check("«Аудит потрібен: так» alone still opens the audit — and only the audit", board.audit_refusal(tasks) is None and board.paid_refusal(tasks) is not None)

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
    check(f"{rel}: no dollar limit is asked of a task", "лімітом у доларах" not in text and "Платні прогони: так" in text)
for rel in ("tasks/TEMPLATE.md", "templates/project/tasks/TEMPLATE.md"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    check(f"{rel}: «Платні прогони: ні» by default, and no dollar sum anywhere",
          "\nПлатні прогони: ні\n" in text and not re.search(r"\d\s*(?:долар|\$|USD)", text) and not board.parse(text).paid)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
