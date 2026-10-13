# 804 — Брак тесту (overseer): the 'step 5 (092)' grouping check asserts that a grouped question 'names each of them by its number', and the order check asserts 'then the rest' and that a rule the reader had reworded counts among t

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-step-5-092-grouping-check-asserts-that-a-grouped-questio

## Що сталося
Overseer прийняв юніт `-|092-onboard-unattended-and-fresh-reader|unit 1` (PASS, запит `20261011T121803Z-a3aa5d`) і знайшов брак тесту: deleting 'the question then names each of them by its number, and', ', then the rest' or ', a rule the reader had you reword' each leaves the suite at 81/0: one «yes» can then cover candidates the owner was never shown by name Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:30:22Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'step 5 (092)' grouping check asserts that a grouped question 'names each of them by its number', and the order check asserts 'then the rest' and that a rule the reader had reworded counts among t»: тест червоніє на тому, що описано вище (deleting 'the question then names each of them by its number, and', ', then the rest' or ', a rule the reader had you reword' each leaves the suite at 81/0: one «yes» can then cover candidates the owner was never shown by name), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
