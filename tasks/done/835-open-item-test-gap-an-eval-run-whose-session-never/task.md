# 835 — Брак тесту (overseer): an eval run whose session never started (--claude names a file that does not exist; BOARD_STATE_DIR set, a task in doing/) leaves no row in extra-sessions.jsonl, while a session that started and repor

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-an-eval-run-whose-session-never-started-claude-names-a-file-

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 3` (PASS, запит `20261011T213454Z-2685e2`) і знайшов брак тесту: book_session called for every row, error rows included (evals/run_simplifier_evals.py:400): today two runs with a missing executable book two sessions at 0.0 USD to the task in hand, so the runner's summary says «додаткових сесій Claude: 2 (0.00 USD)» for a task that started none; the board 059 case at tests/test_simplifier_evals.py:608 runs this very scene without looking at the books Де: `tests/test_simplifier_evals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T21:53:46Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «an eval run whose session never started (--claude names a file that does not exist; BOARD_STATE_DIR set, a task in doing/) leaves no row in extra-sessions.jsonl, while a session that started and repor»: тест червоніє на тому, що описано вище (book_session called for every row, error rows included (evals/run_simplifier_evals.py:400): today two runs with a missing executable book two sessions at 0.0 USD to the task in hand, so the runner's summary says «додаткових сесій Claude: 2 (0.00 USD)» for a task that started none; the board 059 case at tests/test_simplifier_evals.py:608 runs this very scene without looking at the books), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
