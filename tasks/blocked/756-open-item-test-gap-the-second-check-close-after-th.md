# 756 — Брак тесту (overseer): the second check-close, after the minimum turn back, exits 3 (e.g. task.md made non-UTF-8 during the turn back) → an anomaly entry, the task stays in done/, no park with reason minimum

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-second-check-close-after-the-minimum-turn-back-exits-3-e

## Що сталося
Overseer прийняв юніт `-|098-modes-check-close|unit 1` (PASS, запит `20261010T025936Z-166d4c`) і знайшов брак тесту: .claude/unattended/board-runner.sh:679 changed to `if false` reads a crash after the turn back as «missing» and parks the task as minimum, yet the 098 scenes stay 12/0 Де: `tests/test_board_runner.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T03:34:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the second check-close, after the minimum turn back, exits 3 (e.g. task.md made non-UTF-8 during the turn back) → an anomaly entry, the task stays in done/, no park with reason minimum»: тест червоніє на тому, що описано вище (.claude/unattended/board-runner.sh:679 changed to `if false` reads a crash after the turn back as «missing» and parks the task as minimum, yet the 098 scenes stay 12/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника

Стан роботи (2026-10-12): зроблено, перевірено і закомічено в цій гілці (commit `e66252f`); код runner-а не змінено.
- Нова перевірка в `tests/test_board_runner.py` (план `code-done break`, позначка «board 756»): агент закриває задачу з робочим кодом без audit, отримує хід назад, і в цьому ході `task.md` у `done/` стає не UTF-8 (новий крок fake-агента `break`). Другий `mode.py check-close` відповідає кодом 3. Перевіряється: задача лишилась у `done/`, у `blocked/` нічого немає, сесій дві, подія `minimum-missing` є, подій `task-parked` і `minimum-made` немає, у журналі аномалій — «мінімум режиму задачі не перевірено після ходу назад: `mode.py check-close` відповів кодом 3» і немає «задачу закрито без мінімуму її режиму».
- Червоний прогін: у копії дерева з `.claude/unattended/board-runner.sh:694` (у задачі це рядок 679 — файл відтоді зсунувся), заміненим на `if false; then`, `python3 tests/test_board_runner.py` дає `PASS 296   FAIL 1`, і єдина невдача — нова перевірка. Зелений прогін на коді, як він є: `PASS 297   FAIL 0`.
- Уточнення до тексту задачі: з такою зміною runner не «переносить задачу в blocked/ як minimum» — `board.py park` сам падає на `task.md` не в UTF-8, і runner зупиняється зі станом `error` (причина `park`). Тобто гілка, яку тепер тримає тест, захищає від зупинки всієї task board, а не лише від зайвого питання власникові.
- `bash tests/run_all.sh --fast` — `PASS: 45 suites green (fast subset)`; `bash tests/run_all.sh` — `PASS: 98 suites green`.
- Рішення, які я ухвалив сам: (а) новий крок fake-агента `break` замість розширення `done-broken` — той ламає файл у ході закриття, а тут він має зламатися саме в ході назад; (б) зміну runner-а для червоного прогону робив у тимчасовій копії дерева, не в робочому дереві.
- Overseer (request `20261012T085117Z-cd7ac9`) не знайшов жодної невдалої перевірки і сам відтворив обидва прогони, але вердикт записано як BLOCK 1 із 3 лише тому, що відкрита gate escalation 2026-10-12T01:56:46Z чужої задачі (slice `numbers-class-table`, файл `tests/test_task_class_table.py`, питання `tasks/blocked/902-gate-escalation-20261012T015646Z.md`). Цього файла моя робота не торкається; закрити escalation агент не може і не має.
- Overseer назвав один брак тесту: нова перевірка (і перевірка `done-broken` із задачі 098) не тримає, що runner після запису аномалії бере наступну задачу, а не зупиняється. Це задача `tasks/todo/1728-open-item-test-gap-in-the-code-done-break-scene-wi.md`.

Чого бракує до `done/`: запису PASS overseer-а і `report.md`.

1. Як закрити цю задачу? Варіанти: (а) ви відповідаєте «так» на питання 902 (або закриваєте escalation у своєму терміналі: `python3 .claude/hooks/gate.py --close-escalation 2026-10-12T01:56:46Z`), а тут пишете «закрито» — агент знову заявляє unit, новий overseer перевіряє, задача йде в `done/` зі звітом; (б) не хочете зараз вирішувати 902 — напишіть «чекати»: задача лишиться тут, тест уже в гілці й нічого не блокує. Порада агента: (а) — робота готова, бракує лише запису PASS. Те саме питання стоїть у задачах 719, 725, 726, 728, 730, 740, 751 і 752.
   Відповідь:
