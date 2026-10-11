# 797 — Брак тесту (overseer): the 'step 2 (091)' key-variables check asserts both outcomes for a script that would spend a session key: it is «not run», or it runs with the variable explicitly unset AND 'the row says which variabl

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-step-2-091-key-variables-check-asserts-both-outcomes-for

## Що сталося
Overseer прийняв юніт `-|-|unit 1` (PASS, запит `20261011T114650Z-103600`) і знайшов брак тесту: deleting ' and the row says which variable' (the task's «і це записано»), or deleting the «not run» alternative so that only the unset run remains, leaves the suite at PASS 62 FAIL 0 Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T11:59:12Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'step 2 (091)' key-variables check asserts both outcomes for a script that would spend a session key: it is «not run», or it runs with the variable explicitly unset AND 'the row says which variabl»: тест червоніє на тому, що описано вище (deleting ' and the row says which variable' (the task's «і це записано»), or deleting the «not run» alternative so that only the unset run remains, leaves the suite at PASS 62 FAIL 0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
