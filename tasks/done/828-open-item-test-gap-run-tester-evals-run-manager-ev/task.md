# 828 — Брак тесту (overseer): run_tester_evals, run_manager_evals and run_analyst_evals at the weekly cap: with a task in doing/, a project.env cap and books at the cap, the fake claude is never started, stdout carries 'weekly cap

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-run-tester-evals-run-manager-evals-and-run-analyst-evals-at-

## Що сталося
Overseer прийняв юніт `-|110-extra-sessions-after-ordinary-and-weekly-cap|unit 1` (PASS, запит `20261011T203356Z-604a6c`) і знайшов брак тесту: `… or (analyst.shared.week_cap(args.tasks_dir) and None)` in all three tools — the cap is asked and ignored — leaves test_board.py at 303/0 and the three tools' suites at 49/0, 45/0 and 30/0: tests/test_board.py:1091 only greps for the name `week_cap(` in the source, and behaviour at the cap is tried for the simplifier and audit tools alone Де: `tests/test_tester_evals.py, tests/test_manager_evals.py, tests/test_analyst_evals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T20:59:36Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «run_tester_evals, run_manager_evals and run_analyst_evals at the weekly cap: with a task in doing/, a project.env cap and books at the cap, the fake claude is never started, stdout carries 'weekly cap»: тест червоніє на тому, що описано вище (`… or (analyst.shared.week_cap(args.tasks_dir) and None)` in all three tools — the cap is asked and ignored — leaves test_board.py at 303/0 and the three tools' suites at 49/0, 45/0 and 30/0: tests/test_board.py:1091 only greps for the name `week_cap(` in the source, and behaviour at the cap is tried for the simplifier and audit tools alone), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
