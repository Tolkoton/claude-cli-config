# 1721 — Брак тесту (overseer): a session whose answer holds TWO findings that each name a trap of another file prints, through the CLI, '2 naming a trap of another file (<id1>: <trap>; <id2>: <trap>)' — both ids and both traps in t

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-session-whose-answer-holds-two-findings-that-each-name-a-t-a6bcb4b4

## Що сталося
Overseer прийняв юніт `-|730-open-item-059-scorer-residuals|unit 1` (PASS, запит `20261012T070427Z-7abc4e`) і знайшов брак тесту: named_elsewhere() built over listed[:1], or with the count taken from the number of distinct traps instead of findings, prints one of the two and today's suite stays green: the only CLI case has exactly one such finding, and the two-finding case is asserted only on summary() Де: `tests/test_simplifier_evals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T07:14:32Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a session whose answer holds TWO findings that each name a trap of another file prints, through the CLI, '2 naming a trap of another file (<id1>: <trap>; <id2>: <trap>)' — both ids and both traps in the row»: тест червоніє на тому, що описано вище (named_elsewhere() built over listed[:1], or with the count taken from the number of distinct traps instead of findings, prints one of the two and today's suite stays green: the only CLI case has exactly one such finding, and the two-finding case is asserted only on summary()), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
