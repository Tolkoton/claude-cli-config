# 771 — Брак тесту (overseer): the python3.11 compile check covers every tracked .py file (git ls-files '*.py', 238 today) or, if the narrower set is intended, says so in its label

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-python3-11-compile-check-covers-every-tracked-py-file-gi

## Що сталося
Overseer прийняв юніт `-|748-open-item-602-python311-fstring|unit 1` (PASS, запит `20261010T114754Z-dd8612`) і знайшов брак тесту: a 3.12-only form (backslash in an f-string expression, `type X = ...`, `def f[T]()`) in evals/scenarios/tester-property/watch.py or any other evals/scenarios/** file passes. tests/test_engine_lint.py:92 globs only top-level evals/*.py and tests/*.py, so it checks 140 of 238 files while printing 'every Python file of the repository' Де: `tests/test_engine_lint.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T12:14:40Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the python3.11 compile check covers every tracked .py file (git ls-files '*.py', 238 today) or, if the narrower set is intended, says so in its label»: тест червоніє на тому, що описано вище (a 3.12-only form (backslash in an f-string expression, `type X = ...`, `def f[T]()`) in evals/scenarios/tester-property/watch.py or any other evals/scenarios/** file passes. tests/test_engine_lint.py:92 globs only top-level evals/*.py and tests/*.py, so it checks 140 of 238 files while printing 'every Python file of the repository'), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
