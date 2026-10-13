# 779 — Брак тесту (overseer): check-close returns ('соло', []) for a chain on one file: commit on a BLOCK, then an unaudited commit, then a commit with a PASS

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-check-close-returns-for-a-chain-on-one-file-commit-on-a-bloc

## Що сталося
Overseer прийняв юніт `-|754-open-item-test-gap-check-close-names-the-commit-of|unit 1` (PASS, запит `20261011T083503Z-861bd3`) і знайшов брак тесту: an implementation that adds a commit's files to `replaced` only when a PASS tree saw them directly (not when the commit is covered through `replaced`) passes all four new cases, yet contradicts mode.py:55-57 for a chain of more than two commits Де: `tests/test_mode.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T08:48:33Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «check-close returns ('соло', []) for a chain on one file: commit on a BLOCK, then an unaudited commit, then a commit with a PASS»: тест червоніє на тому, що описано вище (an implementation that adds a commit's files to `replaced` only when a PASS tree saw them directly (not when the commit is covered through `replaced`) passes all four new cases, yet contradicts mode.py:55-57 for a chain of more than two commits), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
