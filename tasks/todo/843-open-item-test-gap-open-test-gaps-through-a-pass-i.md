# 843 — Брак тесту (overseer): open_test_gaps (through a PASS in tests/test_overseer_fresh.py section 7b) with two gaps whose checks are longer than 2000 characters and differ only after character 2000: two items in todo/, the row'

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-open-test-gaps-through-a-pass-in-tests-test-overseer-fresh-p-3806b4ef

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 2` (PASS, запит `20261011T222951Z-19d4b8`) і знайшов брак тесту: a key taken from the check after the GAP_CHECK_CHARS cut (key=gap_key(check) instead of gap_key(str(gap['check']))) gives both gaps one item and the suite stays green — the longest pair in PAIRS is about 260 characters, well under 2000; the turn's stated property 'a check longer than 2000 characters is keyed whole' has no test (my probe: two items today) Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T22:33:26Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «open_test_gaps (through a PASS in tests/test_overseer_fresh.py section 7b) with two gaps whose checks are longer than 2000 characters and differ only after character 2000: two items in todo/, the row's two gaps name two different tasks, and the second found again returns its own item»: тест червоніє на тому, що описано вище (a key taken from the check after the GAP_CHECK_CHARS cut (key=gap_key(check) instead of gap_key(str(gap['check']))) gives both gaps one item and the suite stays green — the longest pair in PAIRS is about 260 characters, well under 2000; the turn's stated property 'a check longer than 2000 characters is keyed whole' has no test (my probe: two items today)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
