# 1717 — Брак тесту (overseer): with three files where a scene is 3/3, 3/3 and lost in the third, the record's noise is 0.0 (not null) and the report's sentence 'Measured from fewer runs than were given' names it as (2 of 3 runs)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-three-files-where-a-scene-is-3-3-3-3-and-lost-in-the-th-187bec13

## Що сталося
Overseer прийняв юніт `-|726-open-item-058-noise-three-files|unit 1` (PASS, запит `20261012T061608Z-287b1c`) і знайшов брак тесту: the report's list is built with `scene["noise"] is not None` (evals/compare_audits.py:238); written as `if scene["noise"]` it would drop every holed scene whose holding runs agree — a 0.00 measured from fewer runs would go unnamed — and today's suite stays green, because its only holed scene has noise 0.33 Де: `tests/test_audit_noise.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T06:18:04Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with three files where a scene is 3/3, 3/3 and lost in the third, the record's noise is 0.0 (not null) and the report's sentence 'Measured from fewer runs than were given' names it as (2 of 3 runs)»: тест червоніє на тому, що описано вище (the report's list is built with `scene["noise"] is not None` (evals/compare_audits.py:238); written as `if scene["noise"]` it would drop every holed scene whose holding runs agree — a 0.00 measured from fewer runs would go unnamed — and today's suite stays green, because its only holed scene has noise 0.33), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
