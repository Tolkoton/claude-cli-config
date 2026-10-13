# 1725 — Брак тесту (overseer): test_engine_lint reports a form newer than MIN_PYTHON in every file its own compile check names (engine.py, evals/*.py, tests/*.py, not only the 34 files under .claude/) on a machine without python3.1

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-test-engine-lint-reports-a-form-newer-than-min-python-in-eve-5679cff5

## Що сталося
Overseer прийняв юніт `-|751-open-item-ruff-target-version-after-748|unit 1` (PASS, запит `20261012T073757Z-eb9421`) і знайшов брак тесту: A 3.12-only form outside .claude/ passes wherever python3.11 is absent, and one is in the tree now: evals/run_simplifier_evals.py:364 reuses the outer quote inside an f-string (`{n['id']}` inside f'...' inside f"..."). The suite prints 'PASS: engine lint clean' here, and its compile check would turn red on any machine that has python3.11. The line has to be fixed together with the test Де: `tests/test_engine_lint.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T07:39:54Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «test_engine_lint reports a form newer than MIN_PYTHON in every file its own compile check names (engine.py, evals/*.py, tests/*.py, not only the 34 files under .claude/) on a machine without python3.11 — for example by running ruff --target-version over that set and failing on `invalid-syntax` lines only — and is red on evals/run_simplifier_evals.py:364 as it stands today»: тест червоніє на тому, що описано вище (A 3.12-only form outside .claude/ passes wherever python3.11 is absent, and one is in the tree now: evals/run_simplifier_evals.py:364 reuses the outer quote inside an f-string (`{n['id']}` inside f'...' inside f"..."). The suite prints 'PASS: engine lint clean' here, and its compile check would turn red on any machine that has python3.11. The line has to be fixed together with the test), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
