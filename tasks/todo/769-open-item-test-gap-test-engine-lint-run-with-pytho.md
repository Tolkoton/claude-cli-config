# 769 — Брак тесту (overseer): test_engine_lint, run with python3.11 absent from PATH (a PATH shim without it), reports the oldest-Python check as FAIL (or reaches 3.11 through uv/uvx the way ruff and mypy fall back) and exits non-

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-test-engine-lint-run-with-python3-11-absent-from-path-a-path

## Що сталося
Overseer прийняв юніт `-|748-open-item-602-python311-fstring|unit 1` (PASS, запит `20261010T114754Z-dd8612`) і знайшов брак тесту: with python3.11 hidden from PATH, HEAD's broken testing.py:202 gives 'note python3.11 is not on PATH ...' and 'PASS: engine lint clean', rc 0 (reproduced in /tmp/ov748/before). The 3.11 regression this unit fixed passes every machine that lacks 3.11, against the file's own rule at tests/test_engine_lint.py:16 Де: `tests/test_engine_lint.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T12:14:40Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «test_engine_lint, run with python3.11 absent from PATH (a PATH shim without it), reports the oldest-Python check as FAIL (or reaches 3.11 through uv/uvx the way ruff and mypy fall back) and exits non-»: тест червоніє на тому, що описано вище (with python3.11 hidden from PATH, HEAD's broken testing.py:202 gives 'note python3.11 is not on PATH ...' and 'PASS: engine lint clean', rc 0 (reproduced in /tmp/ov748/before). The 3.11 regression this unit fixed passes every machine that lacks 3.11, against the file's own rule at tests/test_engine_lint.py:16), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
