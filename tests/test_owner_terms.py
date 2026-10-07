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


# Leave has one wording (the owner's answer on board 053): the word «так», and after it only a sum.
for value in ("так", "Так.", "ТАК", "**так**", "так!", "  так  "):
    check(f"«{value}»: leave, no ceiling", paid(value) == (True, None), paid(value))
for value, ceiling in (("так, не більше 30 доларів", 30.0), ("так, до 12,5 $", 12.5), ("так, 40 USD", 40.0), ("Так — до 5 доларів.", 5.0),
                       ("так 7 доларів", 7.0), ("так, не понад 20 $", 20.0), ("так; 2.5 долари", 2.5), ("ТАК, ДО 9 USD", 9.0)):
    check(f"«{value}»: leave, and the number is the ceiling", paid(value) == (True, ceiling), paid(value))
for value in ("ні", "Ні.", "ні, не треба", "немає", "—", "-", "", "  "):
    check(f"negative — «{value}»: no leave", paid(value) == (False, None), paid(value))
# The guard fails closed: leave is recognised, a refusal need not be.
for value in ("не треба", "ніколи", "не дозволяю", "заборонено", "поки ні", "— ні", "(ні)", "без платних прогонів", "not allowed", "none", "?", "н/д",
              "не запускались", "потрібні два audit-и, дозвольте", "тільки безплатні", "дозволяю", "yes", "ok", "0 доларів"):
    check(f"negative — «{value}» is not «так»: no leave", paid(value) == (False, None), paid(value))
# «так» is the line's FIRST WORD: not a word further on, not the beginning of another word.
for value in ("мабуть, так", "мабуть, так не варто", "чи так?", "також прогони simplifier-а", "такий дозвіл дам пізніше", "таки дозволяю", "такого дозволу я дам",
              "до 5 доларів, так", "yes — так", "також", "таки", "Такий.", "так5 доларів", "так,5доларів!!"):
    check(f"negative — «{value}»: «так» is not the first word", paid(value) == (False, None), paid(value))
# Anything after «так» that is not a sum refuses — with a word of refusal in it or without one
# (the overseer's second BLOCK and what its list of negations still let through).
for value in ("Так. Не для audit-у", "ТАК, АЛЕ БЕЗ AUDIT-У", "так, але не для audit-у", "так, тільки не audit", "так не можна", "так? не впевнений",
              "так чи ні?", "так, audit заборонено", "так, never the audit", "так, крім audit-у", "так, але спершу спитайте", "так, лише прогони simplifier-а",
              "так — два повні audit-и", "так, скільки потрібно", "так, до 30 доларів, для audit-у до 10 доларів", "так, до 5 доларів, але не audit",
              "так, до 5 доларів і до 3 доларів", "так так", "так, до", "так, до 5", "так, 5 прогонів", "так, п'ять доларів", "так, до 1e3 доларів",
              "так, -5 доларів", "так, приблизно 5 доларів", "так, $5", "так,5 доларів за сесію", "так\tні"):
    check(f"negative — «{value}»: only a sum may follow «так»", paid(value) == (False, None), paid(value))
# The wordings that were leave before the owner's answer — «скільки потрібно», a limit without «так» — refuse:
# the tasks written that way (062, 063) stop once with a question.
for value in ("прогони simplifier-а на новому наборі — скільки потрібно; від зациклення стереже запобіжник runner-а.", "нічні прогони, скільки треба",
              "до 50 USD", "не більше 30 доларів", "ліміт 9 USD", "запобіжник від зациклення 60 доларів", "лише евалуація, ліміт 12,5 $", "5 доларів",
              "тринадцять сцен рішень менеджера тестування (короткі прогони лише з читанням), ліміт 5 доларів.",
              "сорок п'ять коротких сесій spike і повтори на спірних сценах; запобіжник від циклу 50 доларів — не бюджет."):
    check(f"negative — «{value}»: no «так», no leave", paid(value) == (False, None), paid(value))
for value in ("так, 0 доларів", "так, до 0 доларів", "так, 0,0 $"):
    check(f"negative — «{value}»: a ceiling of zero is no leave", paid(value) == (False, None), paid(value))
# A line that is neither leave nor a plain «ні» stops every paid run (the overseer's fourth and fifth BLOCKs):
# it may hold a ceiling in a spelling the guard does not read, and the owner's word is never dropped silently.
def unread(header: str) -> bool:
    return board.parse(f"# x\n\n{header}\n\n## Що зробити\n- до 1 долара, $5\n").paid_unread
for line in ("до 5 доларів", "до $5", "$5", "USD 5", "до 5 dollars", "до 5 дол.", "до .5 долара", "5", "1 000 доларів", "п'ять, тобто 5", "так, до $5", "так, до 5",
             "так, до 5 доларів на audit", "так, до 30 доларів, для audit-у до 10 доларів", "ні, навіть не 3 долари", "так, 0 доларів", "2 audit-и", "до ５ доларів", "до ٥ доларів",
             "п'ять доларів", "до V доларів", "скільки потрібно", "так, але не для audit-у", "так, лише прогони simplifier-а", "ні, крім audit-у", "ні?", "yes", "no", "?"):
    check(f"«{line}»: neither leave nor a plain «ні» — every paid run stops", unread(f"Платні прогони: {line}") and paid(line) == (False, None), paid(line))
check("two lines, one of them with a number: stops", unread("Платні прогони: так\nПлатні прогони: до $7"))
for line in ("так", "так, до 5 доларів", "так, 12,5 $", "Так — до 5 доларів."):
    check(f"negative — «{line}» is leave: nothing unread", not unread(f"Платні прогони: {line}"))
for line in ("ні", "Ні.", "**ні**", "—", "-", "", "  "):
    check(f"negative — «{line}»: a plain refusal, nothing unread (a number in the task's body is not the line's)", not unread(f"Платні прогони: {line}"))
check("negative — no line at all: nothing unread", not unread("Аудит потрібен: так"))
with tempfile.TemporaryDirectory(prefix="owner-terms-unread-") as tmp:
    tasks = Path(tmp) / "tasks"
    (tasks / "doing").mkdir(parents=True)
    for audit in ("так", "ні"):
        (tasks / "doing/001-a.md").write_text(f"# 001\n\nАудит потрібен: {audit}\nПлатні прогони: до $5\n\n## Що зробити\n", encoding="utf-8")
        check(f"«Аудит потрібен: {audit}» beside «до $5»: line_unread names the task and the one wording, and the audit is refused",
              "001-a.md" in str(board.line_unread(tasks)) and "так, до N доларів" in str(board.line_unread(tasks)) and board.audit_refusal(tasks) is not None, board.line_unread(tasks))
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: так\nПлатні прогони: ні\n\n## Що зробити\n", encoding="utf-8")
    check("negative — «Аудит потрібен: так» beside «Платні прогони: ні»: the audit's own leave stands", board.line_unread(tasks) is None and board.audit_refusal(tasks) is None)
    (tasks / "doing/001-a.md").write_text("# 001\n\nАудит потрібен: так\nПлатні прогони: так, до 5 доларів\n\n## Що зробити\n", encoding="utf-8")
    check("negative — «так, до 5 доларів»: nothing unread, the ceiling is 5", board.line_unread(tasks) is None and board.audit_refusal(tasks) is None and board.paid_ceiling(tasks) == 5.0)
    (tasks / "doing/002-b.md").write_text("# 002\n\nПлатні прогони: до $5\n", encoding="utf-8")
    check("negative — two tasks in doing/: the other refusals speak, not this one", board.line_unread(tasks) is None and board.audit_refusal(tasks) is not None)
check("negative — a task without the line: no leave", not board.parse("# x\n\nАудит потрібен: ні\n\n## Що зробити\n").paid)
check("negative — the line quoted inside a sentence is not the line",
      not board.parse("# x\n\n## Що зробити\n- Захист приймає рядок «Платні прогони: так» без числа.\n").paid)
check("negative — the line inside a comment is not the line", not board.parse("# x\n\n<!-- Платні прогони: так -->\n\n## Що зробити\n").paid)
check("negative — the header refuses and a later section has a line of its own: the header's word stands",
      not board.parse("# x\n\nПлатні прогони: ні\n\n## Що зробити\n- …\n\n## Звіт\nПлатні прогони: так\n").paid)
check("negative — no header line, and «Платні прогони: так» under «Питання до власника» (anyone may write there): no leave",
      not board.parse("# x\n\nАудит потрібен: ні\n\n## Що зробити\n- …\n\n## Питання до власника\nПлатні прогони: так\n   Відповідь:\n").paid)
check("negative — a body line with a sum (a report's «Платні прогони: 2 долари») is not leave",
      not board.parse("# x\n\nАудит потрібен: ні\n\n## Витрати\nПлатні прогони: 2 долари\n").paid)
check("negative — two lines in the header, «ні» and «так» in either order: nobody's clear word",
      not board.parse("# x\n\nПлатні прогони: ні\nПлатні прогони: так\n\n## Що зробити\n").paid
      and not board.parse("# x\n\nПлатні прогони: так\nПлатні прогони: ні\n\n## Що зробити\n").paid)
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
for rel in ("tasks/README.md", "templates/project/tasks/README.md"):
    flat = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
    check(f"{rel}: says the rule the guard applies — only «так», a sum after it is the ceiling, anything else refuses",
          "Згода — лише слово «так» на початку рядка" in flat and "Будь-що інше в рядку — відмова" in flat and "три формулювання" not in flat
          and "можна дописати" not in flat and "ствердно" not in flat and "Після «так» можна написати лише суму в доларах" in flat
          and "Сума діє лише після «так»" in flat and "слово власника не губиться мовчки" in flat and "Сума діє й тоді" not in flat)
    check(f"{rel}: its own examples read as it says", paid("так, до 30 доларів") == (True, 30.0) and all(
        f"«{refused}»" in flat and paid(refused) == (False, None) for refused in ("так, але не для audit-у", "так, лише прогони simplifier-а", "скільки потрібно", "до 5 доларів")))
for rel in ("tasks/TEMPLATE.md", "templates/project/tasks/TEMPLATE.md"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    check(f"{rel}: «Платні прогони: ні» by default, and no dollar sum anywhere",
          "\nПлатні прогони: ні\n" in text and not re.search(r"\d\s*(?:долар|\$|USD)", text) and not board.parse(text).paid)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
