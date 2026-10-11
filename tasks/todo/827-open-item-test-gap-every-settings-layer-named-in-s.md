# 827 — Брак тесту (overseer): every settings layer named in SETTINGS is either checked or reported: assert that a listed settings file that is absent is a visible line of the suite (skipped by name), and that at least the two exis

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-every-settings-layer-named-in-settings-is-either-checked-or-

## Що сталося
Overseer прийняв юніт `-|109-simplifier-on-opus-not-fable|unit 1` (PASS, запит `20261011T195342Z-3467e3`) і знайшов брак тесту: the loop at tests/test_model_roles.py:125 silently skips a missing file - templates/project/.claude/settings.json does not exist today, so a layer moved or renamed drops out of both the Fable check and the cheaper-model check with the suite still green Де: `tests/test_model_roles.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T19:55:24Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «every settings layer named in SETTINGS is either checked or reported: assert that a listed settings file that is absent is a visible line of the suite (skipped by name), and that at least the two exis»: тест червоніє на тому, що описано вище (the loop at tests/test_model_roles.py:125 silently skips a missing file - templates/project/.claude/settings.json does not exist today, so a layer moved or renamed drops out of both the Fable check and the cheaper-model check with the suite still green), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
