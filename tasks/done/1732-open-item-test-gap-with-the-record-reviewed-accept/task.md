# 1732 — Брак тесту (overseer): with the record reviewed-accepted present, a number that arrives in tasks/.reviewed through a pull the runner did not make (the owner's commit in origin, pulled by hand into the runner's checkout betw

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-the-record-reviewed-accepted-present-a-number-that-arri-9007ac5a

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261013T010504Z-1364da`) і знайшов брак тесту: today _arrived reads only the record when it exists (.claude/unattended/board.py:716), so the guard at the top of the loop removes the owner's own number, commits and pushes the removal, and the anomaly journal calls it «записано на цій машині»; every test brings the owner's number through the runner's own pull or inbox (tests/test_board_runner.py:1913, 1921), where reviewed-accept follows at once. Read from the code, not reproduced: the hook refused my write of the file in /tmp Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T01:21:24Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with the record reviewed-accepted present, a number that arrives in tasks/.reviewed through a pull the runner did not make (the owner's commit in origin, pulled by hand into the runner's checkout between two runs) — assert what the next run does with it: it stays, or its removal is what the manuals say»: тест червоніє на тому, що описано вище (today _arrived reads only the record when it exists (.claude/unattended/board.py:716), so the guard at the top of the loop removes the owner's own number, commits and pushes the removal, and the anomaly journal calls it «записано на цій машині»; every test brings the owner's number through the runner's own pull or inbox (tests/test_board_runner.py:1913, 1921), where reviewed-accept follows at once. Read from the code, not reproduced: the hook refused my write of the file in /tmp), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
