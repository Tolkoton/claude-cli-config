# 819 — Брак тесту (overseer): first snapshot with more than 20 entries in a session: assert the first 20 are listed and the line «… and N more» carries the right N (25 entries → «… and 5 more»)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-first-snapshot-with-more-than-20-entries-in-a-session-assert

## Що сталося
Overseer прийняв юніт `-|095-onboard-profile-template-and-first-snapshot|unit 1` (PASS, запит `20261011T134556Z-2ad1f1`) і знайшов брак тесту: an implementation that silently cuts the list at 20 with no remainder line, or prints a wrong remainder, passes: the tests only try 0 and 3 entries Де: `tests/test_baseline.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:47:16Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «first snapshot with more than 20 entries in a session: assert the first 20 are listed and the line «… and N more» carries the right N (25 entries → «… and 5 more»)»: тест червоніє на тому, що описано вище (an implementation that silently cuts the list at 20 with no remainder line, or prints a wrong remainder, passes: the tests only try 0 and 3 entries), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
