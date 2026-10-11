# 798 — Брак тесту (overseer): the 'never (091)' account-identifier check asserts both sources: 'neither from a document nor from the output of a command you ran'

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-never-091-account-identifier-check-asserts-both-sources-

## Що сталося
Overseer прийняв юніт `-|-|unit 1` (PASS, запит `20261011T114650Z-103600`) і знайшов брак тесту: deleting 'neither from a document' leaves the suite green: the rule that stood before this task (identifiers found in documents are not copied) can now be dropped unnoticed, since the check looks only for 'nor from the output of a command' Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T11:59:12Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'never (091)' account-identifier check asserts both sources: 'neither from a document nor from the output of a command you ran'»: тест червоніє на тому, що описано вище (deleting 'neither from a document' leaves the suite green: the rule that stood before this task (identifiers found in documents are not copied) can now be dropped unnoticed, since the check looks only for 'nor from the output of a command'), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
