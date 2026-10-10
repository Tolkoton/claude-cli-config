# 758 — Брак тесту (overseer): a task whose owner line is «Режим: ескіз» and which carries a `## Режим піднято` section to соло (mode.py raise соло, the way out gate.py's own sketch/outside message suggests) changes src/app.py → ga

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-task-whose-owner-line-is-and-which-carries-a-section-to-mo

## Що сталося
Overseer прийняв юніт `-|099-modes-sketch|unit 1` (PASS, запит `20261010T041355Z-370e62`) і знайшов брак тесту: a sketch_mode() that reads the owner line (`.owner`) instead of the mode in force (`.current`) would keep blocking a raised task, and today's tests/test_sketch_quarantine.py stays 12/0 Де: `tests/test_sketch_quarantine.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T04:35:28Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a task whose owner line is «Режим: ескіз» and which carries a `## Режим піднято` section to соло (mode.py raise соло, the way out gate.py's own sketch/outside message suggests) changes src/app.py → ga»: тест червоніє на тому, що описано вище (a sketch_mode() that reads the owner line (`.owner`) instead of the mode in force (`.current`) would keep blocking a raised task, and today's tests/test_sketch_quarantine.py stays 12/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
