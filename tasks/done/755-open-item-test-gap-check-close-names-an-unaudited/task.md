# 755 — Брак тесту (overseer): check-close names an unaudited commit of src/модуль.py (a non-ASCII working-code file name)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-check-close-names-an-unaudited-commit-of-src-py-a-non-ascii-

## Що сталося
Overseer прийняв юніт `-|098-modes-check-close|unit 1` (PASS, запит `20261010T015728Z-02fe05`) і знайшов брак тесту: git diff-tree without -z or core.quotePath=false quotes the path (mode.py:341). The suffix becomes 'py"', the file is not counted as code, and the check exits 0 Де: `tests/test_mode.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T02:16:58Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «check-close names an unaudited commit of src/модуль.py (a non-ASCII working-code file name)»: тест червоніє на тому, що описано вище (git diff-tree without -z or core.quotePath=false quotes the path (mode.py:341). The suffix becomes 'py"', the file is not counted as code, and the check exits 0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
