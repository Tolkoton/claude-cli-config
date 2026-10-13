# 1740 — Брак тесту (overseer): with the task named in an open escalation's `work` still in tasks/doing/, the runner does not start another session for it (or the behaviour is asserted and documented as intended)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-the-task-named-in-an-open-escalation-s-work-still-in-ta-f6be46a2

## Що сталося
Overseer прийняв юніт `-|301-gate-escalation-holds-only-its-own-work|unit 1` (PASS, запит `20261013T061751Z-4f47aa`) і знайшов брак тесту: board.py next prints tasks/doing/401-a.md with exit 0 under an open escalation on that task's file; no test tries the doing/ column, only todo/ Де: `tests/test_escalation_scope.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T06:24:03Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with the task named in an open escalation's `work` still in tasks/doing/, the runner does not start another session for it (or the behaviour is asserted and documented as intended)»: тест червоніє на тому, що описано вище (board.py next prints tasks/doing/401-a.md with exit 0 under an open escalation on that task's file; no test tries the doing/ column, only todo/), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
