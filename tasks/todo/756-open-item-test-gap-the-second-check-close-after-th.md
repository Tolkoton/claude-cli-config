# 756 — Брак тесту (overseer): the second check-close, after the minimum turn back, exits 3 (e.g. task.md made non-UTF-8 during the turn back) → an anomaly entry, the task stays in done/, no park with reason minimum

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-second-check-close-after-the-minimum-turn-back-exits-3-e

## Що сталося
Overseer прийняв юніт `-|098-modes-check-close|unit 1` (PASS, запит `20261010T025936Z-166d4c`) і знайшов брак тесту: .claude/unattended/board-runner.sh:679 changed to `if false` reads a crash after the turn back as «missing» and parks the task as minimum, yet the 098 scenes stay 12/0 Де: `tests/test_board_runner.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T03:34:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the second check-close, after the minimum turn back, exits 3 (e.g. task.md made non-UTF-8 during the turn back) → an anomaly entry, the task stays in done/, no park with reason minimum»: тест червоніє на тому, що описано вище (.claude/unattended/board-runner.sh:679 changed to `if false` reads a crash after the turn back as «missing» and parks the task as minimum, yet the 098 scenes stay 12/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
