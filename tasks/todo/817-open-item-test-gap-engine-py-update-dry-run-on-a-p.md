# 817 — Брак тесту (overseer): `engine.py update --dry-run` on a project with a lock and records at the old paths prints the same two notes as install

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-engine-py-update-dry-run-on-a-project-with-a-lock-and-record

## Що сталося
Overseer прийняв юніт `-|094-install-moves-and-onboard-dirty-tree|unit 1` (PASS, запит `20261011T131917Z-0f4956`) і знайшов брак тесту: the task names install and update; the suite runs update only as the second run that moves nothing, so notes printed on install alone would pass Де: `tests/test_install_move_notes.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:31:37Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «`engine.py update --dry-run` on a project with a lock and records at the old paths prints the same two notes as install»: тест червоніє на тому, що описано вище (the task names install and update; the suite runs update only as the second run that moves nothing, so notes printed on install alone would pass), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
