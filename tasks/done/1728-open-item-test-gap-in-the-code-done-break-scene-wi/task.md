# 1728 — Брак тесту (overseer): in the `code-done break` scene with a second task in todo/ (plan `code-done break done`): the runner exits 0, the second task ends in done/ with its report, and no `stop error` is in the events — «run

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-in-the-code-done-break-scene-with-a-second-task-in-todo-plan-732936f5

## Що сталося
Overseer прийняв юніт `-|756-open-item-test-gap-the-second-check-close-after-th|unit 1` (PASS, запит `20261012T085117Z-cd7ac9`) і знайшов брак тесту: an implementation that writes the anomaly entry and then stops the runner (`finish error …` instead of `return 0` at .claude/unattended/board-runner.sh:696) passes today's scene: it asserts neither r.returncode nor that the board goes on; the 098 scene `done-broken` for the first check-close (line 691) has the same hole Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T09:03:51Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «in the `code-done break` scene with a second task in todo/ (plan `code-done break done`): the runner exits 0, the second task ends in done/ with its report, and no `stop error` is in the events — «runner узяв наступну» as the anomaly entry itself says»: тест червоніє на тому, що описано вище (an implementation that writes the anomaly entry and then stops the runner (`finish error …` instead of `return 0` at .claude/unattended/board-runner.sh:696) passes today's scene: it asserts neither r.returncode nor that the board goes on; the 098 scene `done-broken` for the first check-close (line 691) has the same hole), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
