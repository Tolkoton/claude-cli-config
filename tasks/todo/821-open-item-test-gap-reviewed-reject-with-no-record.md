# 821 — Брак тесту (overseer): reviewed-reject with no record of arrived numbers and a --known revision that already holds a number the runner itself rejected earlier: assert what the script does with it (today it counts as the own

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-reviewed-reject-with-no-record-of-arrived-numbers-and-a-know

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261011T150334Z-ff0cbc`) і знайшов брак тесту: after a lost .claude/state/board/reviewed-accepted a number that reached origin by any unguarded push is accepted for good; tests/test_board.py tries --known only with numbers the owner committed Де: `tests/test_board.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T15:18:46Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «reviewed-reject with no record of arrived numbers and a --known revision that already holds a number the runner itself rejected earlier: assert what the script does with it (today it counts as the own»: тест червоніє на тому, що описано вище (after a lost .claude/state/board/reviewed-accepted a number that reached origin by any unguarded push is accepted for good; tests/test_board.py tries --known only with numbers the owner committed), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
