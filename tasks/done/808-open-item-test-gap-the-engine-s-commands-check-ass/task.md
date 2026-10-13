# 808 — Брак тесту (overseer): the engine's-commands check asserts «one row in the map» beside «not run in step 2»

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-engine-s-commands-check-asserts-one-row-in-the-map-besid

## Що сталося
Overseer прийняв юніт `-|093-onboard-rules-and-hot-places|unit 1` (PASS, запит `20261011T125309Z-aacb94`) і знайшов брак тесту: deleting «one row in the map» (the engine's commands then vanish from the map altogether) leaves the suite at 91/0 Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:54:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the engine's-commands check asserts «one row in the map» beside «not run in step 2»»: тест червоніє на тому, що описано вище (deleting «one row in the map» (the engine's commands then vanish from the map altogether) leaves the suite at 91/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
