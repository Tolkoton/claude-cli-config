# 802 — Брак тесту (overseer): a check asserts that step 5 (the owner decides) or step 6 sends the agent back to the reader for what the owner's words changed, not only that step 4 mentions it

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-check-asserts-that-step-5-the-owner-decides-or-step-6-send

## Що сталося
Overseer прийняв юніт `-|092-onboard-unattended-and-fresh-reader|unit 1` (PASS, запит `20261011T121803Z-a3aa5d`) і знайшов брак тесту: the second run of the reader is described only inside step 4; an edit that leaves step 5 leading straight to step 6 with no reference to it - as it is today - passes, and so would a later edit that deletes 'A rule whose source fell away in this second check goes back to the owner as a question' (81/0 with only 'does not stay confirmed' kept) Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:30:22Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a check asserts that step 5 (the owner decides) or step 6 sends the agent back to the reader for what the owner's words changed, not only that step 4 mentions it»: тест червоніє на тому, що описано вище (the second run of the reader is described only inside step 4; an edit that leaves step 5 leading straight to step 6 with no reference to it - as it is today - passes, and so would a later edit that deletes 'A rule whose source fell away in this second check goes back to the owner as a question' (81/0 with only 'does not stay confirmed' kept)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
