# 761 — Брак тесту (overseer): with a `timeout` shim on PATH that records its argv, a cloud session on a shallow clone runs the fetch as `timeout <n> git -C <root> fetch …` with n below the SessionStart limit (60 s). With a fetch t

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-a-timeout-shim-on-path-that-records-its-argv-a-cloud-se

## Що сталося
Overseer прийняв юніт `-|750-open-item-602-cloud-shallow-clone|unit 1` (PASS, запит `20261010T062108Z-16e3d8`) і знайшов брак тесту: an env-check.sh that never sets LIMIT, or sets `timeout 5000`, passes all 28 cases today (both mutants survived in /tmp/ov750/scripts/mut3.py). Then a hung fetch gets the whole hook killed by Claude Code, and the failure line and the lesson digest that follows it are lost. Де: `tests/test_env_check.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T06:26:45Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with a `timeout` shim on PATH that records its argv, a cloud session on a shallow clone runs the fetch as `timeout <n> git -C <root> fetch …` with n below the SessionStart limit (60 s). With a fetch t»: тест червоніє на тому, що описано вище (an env-check.sh that never sets LIMIT, or sets `timeout 5000`, passes all 28 cases today (both mutants survived in /tmp/ov750/scripts/mut3.py). Then a hung fetch gets the whole hook killed by Claude Code, and the failure line and the lesson digest that follows it are lost.), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
