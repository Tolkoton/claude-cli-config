# 1718 — Брак тесту (overseer): with three or more files where a scene is absent from one file altogether (no row, shown as —) and two other runs hold valid sessions for it, the noise is that of those two and the scene is named with

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-three-or-more-files-where-a-scene-is-absent-from-one-fi-d79b2c25

## Що сталося
Overseer прийняв юніт `-|726-open-item-058-noise-three-files|unit 1` (PASS, запит `20261012T061608Z-287b1c`) і знайшов брак тесту: the suite loses a scene only through ERROR sessions (LOST); an implementation that leaves out a run with a row of errors but answers n/a (or raises) when the row is missing passes every check today — I tried the case by hand and it works now, no test holds it Де: `tests/test_audit_noise.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T06:18:04Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with three or more files where a scene is absent from one file altogether (no row, shown as —) and two other runs hold valid sessions for it, the noise is that of those two and the scene is named with 'N of M runs'»: тест червоніє на тому, що описано вище (the suite loses a scene only through ERROR sessions (LOST); an implementation that leaves out a run with a row of errors but answers n/a (or raises) when the row is missing passes every check today — I tried the case by hand and it works now, no test holds it), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
