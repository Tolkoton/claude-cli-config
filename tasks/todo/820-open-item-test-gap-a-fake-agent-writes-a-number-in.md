# 820 — Брак тесту (overseer): a fake agent writes a number into tasks/.reviewed, commits it and raises a gate question in the same attempt (step gateq): origin's tasks/.reviewed never holds the number after the gate-question push

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-fake-agent-writes-a-number-into-tasks-reviewed-commits-it-

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261011T150334Z-ff0cbc`) і знайшов брак тесту: publish_gate_questions pushes the branch at board-runner.sh:390 with no reviewed_guard; a guard added only to stop_after_attempt would leave this push open and every test green Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T15:18:46Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a fake agent writes a number into tasks/.reviewed, commits it and raises a gate question in the same attempt (step gateq): origin's tasks/.reviewed never holds the number after the gate-question push»: тест червоніє на тому, що описано вище (publish_gate_questions pushes the branch at board-runner.sh:390 with no reviewed_guard; a guard added only to stop_after_attempt would leave this push open and every test green), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
