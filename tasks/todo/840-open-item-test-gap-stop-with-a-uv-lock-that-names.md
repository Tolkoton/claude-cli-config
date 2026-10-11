# 840 — Брак тесту (overseer): stop with a uv.lock that names ruff but not mypy, a runner stand-in that starts the project's own ruff, [tool.mypy] in pyproject.toml and a global mypy of another version on PATH: the log has no `uv r

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-stop-with-a-uv-lock-that-names-ruff-but-not-mypy-a-runner-st-28b62e1c

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 1` (PASS, запит `20261011T222058Z-755ac8`) і знайшов брак тесту: check_tool calling tool_prefix(root, 'ruff') (or tool_prefix(root)) for every tool: mypy would go through `uv run mypy` to the global one whenever ruff is the project's, and test_gate (124/0) stays green — every board 108 scene has only [tool.ruff] and no mypy stand-in, so the mypy step is never built there Де: `tests/test_gate.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T22:24:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «stop with a uv.lock that names ruff but not mypy, a runner stand-in that starts the project's own ruff, [tool.mypy] in pyproject.toml and a global mypy of another version on PATH: the log has no `uv r»: тест червоніє на тому, що описано вище (check_tool calling tool_prefix(root, 'ruff') (or tool_prefix(root)) for every tool: mypy would go through `uv run mypy` to the global one whenever ruff is the project's, and test_gate (124/0) stays green — every board 108 scene has only [tool.ruff] and no mypy stand-in, so the mypy step is never built there), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
