# 1746 — Брак тесту (overseer): a check in tests/test_board.py (beside the NEGATIVE of board 401) that neither tasks/CLASSES.md nor templates/project/tasks/CLASSES.md says the order of the rows is the order of the queue — e.g. both

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-check-in-tests-test-board-py-beside-the-negative-of-board-efb602a9

## Що сталося
Overseer прийняв юніт `-|401-task-numbers-by-class-build|unit 2` (PASS, запит `20261013T175857Z-2bd4b7`) і знайшов брак тесту: with the removed sentence «Порядок рядків таблиці — це порядок, у якому runner бере класи. Щоб змінити пріоритет, переставте рядки» put back into BOTH tables (a temporary copy), tests/test_board.py stays PASS 344 FAIL 0, test_task_class_table 134 passed, test_owner_terms 67/0, test_text_hygiene 8/0: the NEGATIVE check reads the two README manuals only, and the table's own introduction is where the false promise stood until this turn Де: `tests/test_board.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T18:05:02Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a check in tests/test_board.py (beside the NEGATIVE of board 401) that neither tasks/CLASSES.md nor templates/project/tasks/CLASSES.md says the order of the rows is the order of the queue — e.g. both carry «Порядок рядків нічого не переставляє» and neither carries «переставте рядки»»: тест червоніє на тому, що описано вище (with the removed sentence «Порядок рядків таблиці — це порядок, у якому runner бере класи. Щоб змінити пріоритет, переставте рядки» put back into BOTH tables (a temporary copy), tests/test_board.py stays PASS 344 FAIL 0, test_task_class_table 134 passed, test_owner_terms 67/0, test_text_hygiene 8/0: the NEGATIVE check reads the two README manuals only, and the table's own introduction is where the false promise stood until this turn), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
