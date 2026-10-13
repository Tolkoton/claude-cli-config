# 1713 — Брак тесту (overseer): a runner scene: the session changes .claude/settings.json and the runner is killed (TERM, and KILL) while it runs; the runner is started again — asserts the settings are as before the session, or that

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-runner-scene-the-session-changes-claude-settings-json-and-ba998bba

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T043134Z-a04397`) і знайшов брак тесту: today's runner: the restart records the changed settings as its `before`, starts three sessions on them and closes both tasks; all 318 checks stay green because the only kill scene (`--status and a kill`) touches no guarded file Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T04:58:19Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a runner scene: the session changes .claude/settings.json and the runner is killed (TERM, and KILL) while it runs; the runner is started again — asserts the settings are as before the session, or that the second start stops with state=error reason=protected / puts a question in blocked/, and that no further session is started on the changed file»: тест червоніє на тому, що описано вище (today's runner: the restart records the changed settings as its `before`, starts three sessions on them and closes both tasks; all 318 checks stay green because the only kill scene (`--status and a kill`) touches no guarded file), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
