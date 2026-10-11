# 833 — Брак тесту (overseer): open_test_gaps on a project whose tasks/ directory is not a task board (a Python package `tasks/` with __init__.py and no todo/ doing/ blocked/ done/): a PASS with a gap writes nothing under tasks/ an

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-open-test-gaps-on-a-project-whose-tasks-directory-is-not-a-t

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 2` (PASS, запит `20261011T212743Z-5c49ed`) і знайшов брак тесту: today the only sign of a board is `(root / 'tasks').is_dir()` at .claude/hooks/overseer_verdict.py:626 and board.open_item creates the column itself: in my run a project with only tasks/__init__.py got tasks/todo/700-open-item-test-gap-test-with-tax-rounds-half-up-as.md written into its package; the suite's 'without a task board' case tries only a project with no tasks/ at all Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T21:34:50Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «open_test_gaps on a project whose tasks/ directory is not a task board (a Python package `tasks/` with __init__.py and no todo/ doing/ blocked/ done/): a PASS with a gap writes nothing under tasks/ an»: тест червоніє на тому, що описано вище (today the only sign of a board is `(root / 'tasks').is_dir()` at .claude/hooks/overseer_verdict.py:626 and board.open_item creates the column itself: in my run a project with only tasks/__init__.py got tasks/todo/700-open-item-test-gap-test-with-tax-rounds-half-up-as.md written into its package; the suite's 'without a task board' case tries only a project with no tasks/ at all), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
