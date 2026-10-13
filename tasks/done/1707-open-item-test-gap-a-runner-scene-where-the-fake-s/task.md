# 1707 — Брак тесту (overseer): a runner scene where the fake session writes the settings AND rewrites .claude/state/gate/protected/runner.json to the new hash: asserts the settings are as before the session, the task is in blocked/

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-runner-scene-where-the-fake-session-writes-the-settings-an-11fea20d

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T030239Z-df119a`) і знайшов брак тесту: today's `after` returns 0 for that session and every existing scene still passes, because none touches the runner's snapshot Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T03:16:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a runner scene where the fake session writes the settings AND rewrites .claude/state/gate/protected/runner.json to the new hash: asserts the settings are as before the session, the task is in blocked/ with reason protected, and events.log has protected-restored»: тест червоніє на тому, що описано вище (today's `after` returns 0 for that session and every existing scene still passes, because none touches the runner's snapshot), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
