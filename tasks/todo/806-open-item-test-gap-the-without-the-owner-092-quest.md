# 806 — Брак тесту (overseer): the 'without the owner (092)' questions check asserts the first bullet (that no check could be run), that the questions are written numbered, and the 'one language (092)' check asserts the fallback to

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-without-the-owner-092-questions-check-asserts-the-first-

## Що сталося
Overseer прийняв юніт `-|092-onboard-unattended-and-fresh-reader|unit 1` (PASS, запит `20261011T121803Z-a3aa5d`) і знайшов брак тесту: deleting the bullet '- that no check could be run (step 2), when that is so;', the word 'numbered' (the starter is told a number of questions), the fallback clause or the quotation sentence each leaves the suite at 81/0 Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:30:22Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'without the owner (092)' questions check asserts the first bullet (that no check could be run), that the questions are written numbered, and the 'one language (092)' check asserts the fallback to»: тест червоніє на тому, що описано вище (deleting the bullet '- that no check could be run (step 2), when that is so;', the word 'numbered' (the starter is told a number of questions), the fallback clause or the quotation sentence each leaves the suite at 81/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
