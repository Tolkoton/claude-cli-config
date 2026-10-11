# 841 — Брак тесту (overseer): post_write and stop with a lockfile that names ruff and a runner stand-in that exits non-zero (and one that prints nothing) when asked where the tool is: the runner is not used, the engine's lookup de

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-post-write-and-stop-with-a-lockfile-that-names-ruff-and-a-ru-e685b66d

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 1` (PASS, запит `20261011T222058Z-755ac8`) і знайшов брак тесту: runner_has that ignores the return code or treats an empty answer as 'found' — a broken or offline `uv run` would then be taken as the project's pin and the step would fail with the runner's error or pass through to PATH; every stand-in in tests/test_gate.py and tests/test_format_on_edit.py answers with exit 0 and a path Де: `tests/test_gate.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T22:24:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «post_write and stop with a lockfile that names ruff and a runner stand-in that exits non-zero (and one that prints nothing) when asked where the tool is: the runner is not used, the engine's lookup de»: тест червоніє на тому, що описано вище (runner_has that ignores the return code or treats an empty answer as 'found' — a broken or offline `uv run` would then be taken as the project's pin and the step would fail with the runner's error or pass through to PATH; every stand-in in tests/test_gate.py and tests/test_format_on_edit.py answers with exit 0 and a path), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
