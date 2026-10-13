# 1720 — Брак тесту (overseer): a declared name written with underscores, capitals or an extra and a marker (python_dateutil, Scikit_Learn==1.0, Pillow[jpeg]>=9 ; python_version>"3.8") is found in IMPORT_NAMES: no signal when dateut

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-declared-name-written-with-underscores-capitals-or-an-extr-1fa73c5b

## Що сталося
Overseer прийняв юніт `-|728-open-item-059-dependency-signal-import-name-and-te|unit 1` (PASS, запит `20261012T063313Z-0aafe5`) і знайшов брак тесту: import_names written as IMPORT_NAMES.get(name.lower()) without the [-_.]+ normalization — the suite's only non-canonical spelling is 'PyYAML>=6', which lower() alone resolves, so every check stays green while python_dateutil is reported as unused; tried by hand, the code is right now Де: `tests/test_simplify_signals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T06:35:54Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a declared name written with underscores, capitals or an extra and a marker (python_dateutil, Scikit_Learn==1.0, Pillow[jpeg]>=9 ; python_version>"3.8") is found in IMPORT_NAMES: no signal when dateutil, sklearn and PIL are imported»: тест червоніє на тому, що описано вище (import_names written as IMPORT_NAMES.get(name.lower()) without the [-_.]+ normalization — the suite's only non-canonical spelling is 'PyYAML>=6', which lower() alone resolves, so every check stays green while python_dateutil is reported as unused; tried by hand, the code is right now), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
