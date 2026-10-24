# 1763 — Брак тесту (overseer): a test where a method Report.render is removed and a new class carries the same body as a method under a different name (or a module function) asserts no delete/untested finding

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-test-where-a-method-report-render-is-removed-and-a-new-cla-81ef841e

## Що сталося
Overseer прийняв юніт `-|303-delete-guard-renamed-move|unit 1` (PASS, запит `20261024T134958Z-a36c46`) і знайшов брак тесту: the shape match runs on bare() names and on method bodies, but no test covers a qualified (method) definition. A change that dropped methods from Moved.shapes, or normalized on the qualified name rather than the bare one, would pass today's tests Де: `tests/test_delete_guard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-24T13:51:32Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a test where a method Report.render is removed and a new class carries the same body as a method under a different name (or a module function) asserts no delete/untested finding»: тест червоніє на тому, що описано вище (the shape match runs on bare() names and on method bodies, but no test covers a qualified (method) definition. A change that dropped methods from Moved.shapes, or normalized on the qualified name rather than the bare one, would pass today's tests), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
