# 770 — Брак тесту (overseer): testing.ledger() with a row whose value contains '--' and '-->' (e.g. a contract line 'a -- b -->'): the written line holds no '--' between '<! -- row: ' and ' -->', LEDGER_ROW_RE finds exactly one row

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-testing-ledger-with-a-row-whose-value-contains-and-e-g-a-con

## Що сталося
Overseer прийняв юніт `-|748-open-item-602-python311-fstring|unit 1` (PASS, запит `20261010T114754Z-dd8612`) і знайшов брак тесту: replacing testing.py:202 with `escaped = compact` (or writing the replacement as "-\u002d" with one backslash, which makes it a no-op) keeps tests/test_testing.py at 192 passed, 0 failed (mutant in /tmp/ov748/mut). A '-->' in a row value would then end the HTML comment early and the row would be lost or misread Де: `tests/test_testing.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T12:14:40Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «testing.ledger() with a row whose value contains '--' and '-->' (e.g. a contract line 'a -- b -->'): the written line holds no '--' between '<! -- row: ' and ' -->', LEDGER_ROW_RE finds exactly one row»: тест червоніє на тому, що описано вище (replacing testing.py:202 with `escaped = compact` (or writing the replacement as "-\u002d" with one backslash, which makes it a no-op) keeps tests/test_testing.py at 192 passed, 0 failed (mutant in /tmp/ov748/mut). A '-->' in a row value would then end the HTML comment early and the row would be lost or misread), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
