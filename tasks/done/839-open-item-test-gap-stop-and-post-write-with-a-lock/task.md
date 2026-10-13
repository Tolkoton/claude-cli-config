# 839 — Брак тесту (overseer): stop and post_write with a lockfile that names ruff and a stand-in `uv` (and `poetry`) that execs the command from PATH, as the real runner does for a tool outside the default groups: the global ruff

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-stop-and-post-write-with-a-lockfile-that-names-ruff-and-a-st-74024bc0

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 1` (PASS, запит `20261011T221449Z-99bf32`) і знайшов брак тесту: today's cases at tests/test_gate.py:311 and :326 assert only that `uv run ruff` / `poetry run ruff format` was issued when the lock names ruff — they pass while the stand-in runner hands the call to the global ruff 0.0.1; no test tries a lock that names the tool with a runner that does not start the locked one Де: `tests/test_gate.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T22:17:38Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «stop and post_write with a lockfile that names ruff and a stand-in `uv` (and `poetry`) that execs the command from PATH, as the real runner does for a tool outside the default groups: the global ruff »: тест червоніє на тому, що описано вище (today's cases at tests/test_gate.py:311 and :326 assert only that `uv run ruff` / `poetry run ruff format` was issued when the lock names ruff — they pass while the stand-in runner hands the call to the global ruff 0.0.1; no test tries a lock that names the tool with a runner that does not start the locked one), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
