# 1710 — Брак тесту (overseer): a runner scene where the fake session changes the settings and makes the guard unable to run its comparison (the kept-copies directory or discarded/ replaced by a file, or unwritable): asserts the set

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-runner-scene-where-the-fake-session-changes-the-settings-a-eecdc96e

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T033237Z-a582a3`) і знайшов брак тесту: today's board-runner.sh logs `protected-check-failed rc=1` and starts the next session on the changed settings; all 16 runner scenes and 44 guard checks stay green Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T03:36:39Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a runner scene where the fake session changes the settings and makes the guard unable to run its comparison (the kept-copies directory or discarded/ replaced by a file, or unwritable): asserts the settings are as before the session or the runner stops with state=error reason=protected, and that no further session is started»: тест червоніє на тому, що описано вище (today's board-runner.sh logs `protected-check-failed rc=1` and starts the next session on the changed settings; all 16 runner scenes and 44 guard checks stay green), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
