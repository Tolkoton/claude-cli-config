# 832 — Брак тесту (overseer): evals/hook_coverage.coverage_site with a recording uvx stand-in: the argv carries `--from coverage==<VERSIONS['coverage']>`; and run_tester_evals.PYTEST / HYPOTHESIS equal the tuples built from spec('

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-evals-hook-coverage-coverage-site-with-a-recording-uvx-stand

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 1` (PASS, запит `20261011T212337Z-0ec3d0`) і знайшов брак тесту: a `--from` value built from a variable or an f-string (`f"{name}"`, `"cover" + "age"`) is outside the UNPINNED pattern and the substring check at tests/test_tool_versions.py:83 passes on the import alone; no test in tests/ asserts the coverage spec that reaches uvx (grep for `coverage==` and `spec('coverage')` in tests/*.py finds nothing) Де: `tests/test_tool_versions.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T21:27:38Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «evals/hook_coverage.coverage_site with a recording uvx stand-in: the argv carries `--from coverage==<VERSIONS['coverage']>`; and run_tester_evals.PYTEST / HYPOTHESIS equal the tuples built from spec('»: тест червоніє на тому, що описано вище (a `--from` value built from a variable or an f-string (`f"{name}"`, `"cover" + "age"`) is outside the UNPINNED pattern and the substring check at tests/test_tool_versions.py:83 passes on the import alone; no test in tests/ asserts the coverage spec that reaches uvx (grep for `coverage==` and `spec('coverage')` in tests/*.py finds nothing)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
