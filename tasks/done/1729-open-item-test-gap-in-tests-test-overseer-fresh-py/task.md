# 1729 — Брак тесту (overseer): in tests/test_overseer_fresh.py section 7b: a PASS answer carrying test_gaps while the gate's escalation is open (the scene of the check at line 313) - the row is BLOCK and the item opened in tasks/to

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-in-tests-test-overseer-fresh-py-section-7b-a-pass-answer-car-cd8f6ba9

## Що сталося
Overseer повернув юніт `-|757-open-item-test-gap-item-text-after-a-block|unit 1` (BLOCK, запит `20261012T094520Z-396ac5`) і назвав ще й брак тесту: open_test_gaps choosing its words from the overseer's answered verdict instead of the recorded row (for example by passing obj['verdict'] in, or by finish() calling it before row.update) writes «Overseer прийняв юніт … (PASS…)» into an item for a unit the ledger records as BLOCK, and both new checks stay green: neither tries an answer whose recorded verdict differs from the answered one. Today's code reads the row and gives «повернув … (BLOCK…) і назвав ще й брак тесту» in that case, which no test pins Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T09:48:02Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «in tests/test_overseer_fresh.py section 7b: a PASS answer carrying test_gaps while the gate's escalation is open (the scene of the check at line 313) - the row is BLOCK and the item opened in tasks/todo says `(BLOCK, запит …)` with «повернув», never «прийняв» or PASS»: тест червоніє на тому, що описано вище (open_test_gaps choosing its words from the overseer's answered verdict instead of the recorded row (for example by passing obj['verdict'] in, or by finish() calling it before row.update) writes «Overseer прийняв юніт … (PASS…)» into an item for a unit the ledger records as BLOCK, and both new checks stay green: neither tries an answer whose recorded verdict differs from the answered one. Today's code reads the row and gives «повернув … (BLOCK…) і назвав ще й брак тесту» in that case, which no test pins), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
