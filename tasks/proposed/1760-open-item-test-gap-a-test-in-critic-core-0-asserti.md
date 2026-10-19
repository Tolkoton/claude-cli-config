# 1760 — Брак тесту (overseer): a test in critic-core §0 asserting the sentence that an unquoted «owner decision»/«рішення власника» mark is an agent decision and is reviewed (e.g. §0 holds 'without a quote is an agent decision')

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-test-in-critic-core-0-asserting-the-sentence-that-an-unquo-e7cb50ab

## Що сталося
Overseer прийняв юніт `critics-goals-discipline|202-business-goals-focus-second|unit 1` (PASS, запит `20261019T075835Z-cb0024`) і знайшов брак тесту: the contract's central rule. A §0 that names the two quote sources and drops the old clause, but never says that an unquoted mark is reviewed (or says the reverse), passes test_seam3_quote_rule_replaces_the_old_clause today Де: `tests/test_critics_goals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-19T08:00:20Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a test in critic-core §0 asserting the sentence that an unquoted «owner decision»/«рішення власника» mark is an agent decision and is reviewed (e.g. §0 holds 'without a quote is an agent decision')»: тест червоніє на тому, що описано вище (the contract's central rule. A §0 that names the two quote sources and drops the old clause, but never says that an unquoted mark is reviewed (or says the reverse), passes test_seam3_quote_rule_replaces_the_old_clause today), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
