# 1719 — Брак тесту (overseer): a pyproject.toml that itself sits under a directory named tests/ (for example tests/fixtures/proj/pyproject.toml with src/app.py importing a declared dependency) gives no signal for that dependency, a

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-pyproject-toml-that-itself-sits-under-a-directory-named-te-bfbfab1d

## Що сталося
Overseer прийняв юніт `-|728-open-item-059-dependency-signal-import-name-and-te|unit 1` (PASS, запит `20261012T063313Z-0aafe5`) і знайшов брак тесту: an implementation that calls is_test on the path from the repository root (base / f) instead of the path under the pyproject.toml — it would call every importer of such a project a test and report each used dependency as 'imported only by tests'; today's nested case uses services/api, where both rules agree. docs/engine-limits.md:695 states the rule and no check holds it; I tried the case by hand and the code is right now Де: `tests/test_simplify_signals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T06:35:54Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a pyproject.toml that itself sits under a directory named tests/ (for example tests/fixtures/proj/pyproject.toml with src/app.py importing a declared dependency) gives no signal for that dependency, and a dependency only its own src/app_test.py imports is 'imported only by tests'»: тест червоніє на тому, що описано вище (an implementation that calls is_test on the path from the repository root (base / f) instead of the path under the pyproject.toml — it would call every importer of such a project a test and report each used dependency as 'imported only by tests'; today's nested case uses services/api, where both rules agree. docs/engine-limits.md:695 states the rule and no check holds it; I tried the case by hand and the code is right now), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
