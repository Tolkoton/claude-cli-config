# 842 — Брак тесту (overseer): open_test_gaps (through a PASS in tests/test_overseer_fresh.py section 7b) with two gaps whose checks are longer than 200 characters and differ only after character 200: two items in todo/, each with

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-open-test-gaps-through-a-pass-in-tests-test-overseer-fresh-p-f7570014

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 2` (PASS, запит `20261011T222507Z-616e98`) і знайшов брак тесту: a key taken from the check after the 200-character cut (today's code: one_line(gap['check'], 200) before gap_key) gives both gaps one item and the suite stays green — both pairs of PAIRS are shorter than 200 characters Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T22:27:23Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «open_test_gaps (through a PASS in tests/test_overseer_fresh.py section 7b) with two gaps whose checks are longer than 200 characters and differ only after character 200: two items in todo/, each with »: тест червоніє на тому, що описано вище (a key taken from the check after the 200-character cut (today's code: one_line(gap['check'], 200) before gap_key) gives both gaps one item and the suite stays green — both pairs of PAIRS are shorter than 200 characters), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
