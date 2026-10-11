# 796 — Брак тесту (overseer): the 'step 2 (091)' key-variables check asserts that the listing comes BEFORE any script of the project is run (the phrase 'Before any script of the project is run' in step 2, and that it stands ahead

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-step-2-091-key-variables-check-asserts-that-the-listing-

## Що сталося
Overseer прийняв юніт `-|-|unit 1` (PASS, запит `20261011T114650Z-103600`) і знайшов брак тесту: replacing 'Before any script of the project is run, list' with 'At some point list' leaves tests/test_onboard.py at PASS 62 FAIL 0, though the task's point 1 and the check's own name say 'before any script runs' Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T11:59:12Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'step 2 (091)' key-variables check asserts that the listing comes BEFORE any script of the project is run (the phrase 'Before any script of the project is run' in step 2, and that it stands ahead »: тест червоніє на тому, що описано вище (replacing 'Before any script of the project is run, list' with 'At some point list' leaves tests/test_onboard.py at PASS 62 FAIL 0, though the task's point 1 and the check's own name say 'before any script runs'), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
