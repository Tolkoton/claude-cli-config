# 810 — Брак тесту (overseer): the older-engine's-records check asserts the list of what is read (decisions and deferred items of each slice contract, entries of the escalations log, lessons in its memory, ADRs) and the list of wha

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-older-engine-s-records-check-asserts-the-list-of-what-is

## Що сталося
Overseer прийняв юніт `-|093-onboard-rules-and-hot-places|unit 1` (PASS, запит `20261011T125309Z-aacb94`) і знайшов брак тесту: replacing the read-list with «its headings.» or the rest-list with «nothing else» leaves the suite at 91/0: only «decisions and rules», «ledgers» and the closing phrase are held Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:54:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the older-engine's-records check asserts the list of what is read (decisions and deferred items of each slice contract, entries of the escalations log, lessons in its memory, ADRs) and the list of wha»: тест червоніє на тому, що описано вище (replacing the read-list with «its headings.» or the rest-list with «nothing else» leaves the suite at 91/0: only «decisions and rules», «ledgers» and the closing phrase are held), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
