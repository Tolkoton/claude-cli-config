# 1726 — Брак тесту (overseer): with two requests on disk whose request.json carries NO created_ns field (every request written before board 752), the later id is the baseline: the same tree claimed again asks for no audit, and with

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-two-requests-on-disk-whose-request-json-carries-no-crea-585a99de

## Що сталося
Overseer прийняв юніт `-|752-open-item-overseer-stop-last-request-by-mtime|unit 1` (PASS, запит `20261012T082058Z-8c8a30`) і знайшов брак тесту: last_request written as read_json(...)["created_ns"] (or int(created) on None) raises KeyError/TypeError, _code_changed_in_tree catches it and returns False, and a unit written by shell is never audited on any project that already holds old requests; every planted request in the suite copies created_ns from a real one, so all checks stay green. Tried by hand: the code is right now (isinstance check, falls back to 0). Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T08:25:07Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with two requests on disk whose request.json carries NO created_ns field (every request written before board 752), the later id is the baseline: the same tree claimed again asks for no audit, and with the ids the other way round it does; a request without the field beside one with it of the same second loses to it»: тест червоніє на тому, що описано вище (last_request written as read_json(...)["created_ns"] (or int(created) on None) raises KeyError/TypeError, _code_changed_in_tree catches it and returns False, and a unit written by shell is never audited on any project that already holds old requests; every planted request in the suite copies created_ns from a real one, so all checks stay green. Tried by hand: the code is right now (isinstance check, falls back to 0).), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
