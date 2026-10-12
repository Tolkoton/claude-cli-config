# 725 — Інші платні скрипти вимірювань: сесія, яку API не пустив, — помилка, а не результат

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: eval-runners-failed-session-as-result

## Що сталося
Задача 014 виправила це в evals/run_audit_scenarios.py: сесія з is_error (401 «Failed to authenticate») записувалась як прогін без вердикту, файл — як complete. run_tester_evals.py, run_manager_evals.py, run_analyst_evals.py, run_simplifier_evals.py, run_second_opinion_evals.py на ту саму ваду не перевірено.

- Записано: 2026-10-06T18:56:02Z, агент

## Що зробити
Тест спершу на shim-і claude (відповідь з is_error і api_error_status 401): такий прогін — помилка, файл не complete. Потім найменша зміна в кожному скрипті, де тест червоний. Окремо, із зауваження наглядача до 014: у compare_audits.py сцена, що є лише в одному файлі і не має жодної чинної сесії, зараз «only after» з успішним підсумком — підсумковий рядок має сказати про це (тест спершу).

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника

Стан роботи (2026-10-12): зроблено і закомічено в цій гілці.
- Чотири runner-и (`evals/run_analyst_evals.py`, `run_manager_evals.py`, `run_tester_evals.py`, `run_simplifier_evals.py`): сесія з `is_error` (401) уже була рядком помилки без оцінки. Виправлено те, що довкола: файл результатів тепер має `"status"` — `complete`, `partial` або `no-results`; summary рахує такі сесії в `errors` і не бере їх у жоден знаменник (analyst і tester писали «0 of 1»); `run_simplifier_evals.py` завершувався з кодом 0, коли одна сесія відповіла, а іншу API не пустив, або коли прогін обрізала `--max-usd`, — тепер код 1.
- `evals/compare_audits.py`: сцена, що є лише в одному файлі й не має там жодної чинної сесії, лишається «only after» / «only before» з кодом 0, але рядок `Result:` тепер називає її як не виміряну.
- `evals/run_second_opinion_evals.py` із задачі вже не існує (прибрано задачею 732).
- Тести: новий suite `tests/test_eval_runners_failed_session.py` — `PASS 40   FAIL 0` (до коду червоний); три нові випадки в `tests/test_audit_no_session.py` — `PASS 31   FAIL 0`; `bash tests/run_all.sh --fast` — `PASS: 45 suites green (fast subset)`. Повний `bash tests/run_all.sh` запускався раз, до останніх двох правок: 97 із 98 suites зелені, червоний був `tests/test_simplifier_evals.py` (точне порівняння summary без нового ключа `errors`); після правки цього тесту він `PASS 305   FAIL 0`. Після виправлення за BLOCK overseer-а повний набір не повторювався.
- Рішення, які я ухвалив сам: два старі тести (`tests/test_tester_evals.py`, `tests/test_tester_property_evals.py`) закріплювали старі знаменники з рядком помилки — змінив очікування на нові; `compare_audits.py` у випадку «лише в одному файлі» код завершення не міняє; ці чотири runner-и, на відміну від `run_audit_scenarios.py`, не зупиняються на першій відмові у вході й не мають `--resume`; `--rescore` у `run_simplifier_evals.py` не чіпав.
- Overseer: перший audit (request `20261012T054046Z-c44b55`) — BLOCK #1 по суті: код завершення `run_simplifier_evals.py`; виправлено. Його дві прогалини в тестах лягли в `tasks/todo/1715-…` і `tasks/todo/1716-…` — обидва випадки вже є в новому suite, ці задачі лишилось тільки закрити. Другий audit (request `20261012T054646Z-7acbd2`) не знайшов жодної невдалої перевірки, але записаний як BLOCK 2 із 3 лише тому, що відкрита gate escalation 2026-10-12T01:56:46Z чужої задачі (slice `numbers-class-table`, файл `tests/test_task_class_table.py`, питання `tasks/blocked/902-gate-escalation-20261012T015646Z.md`). Цього файлу моя робота не торкається; закрити escalation агент не може і не має.

Чого бракує до `done/`: запису PASS overseer-а і `report.md`.

1. Як закрити цю задачу? Варіанти: (а) ви відповідаєте на питання 902 (або закриваєте escalation у своєму терміналі: `python3 .claude/hooks/gate.py --close-escalation 2026-10-12T01:56:46Z`), а тут пишете «закрито» — агент знову заявляє unit, новий overseer перевіряє, задача йде в `done/` зі звітом; (б) не хочете зараз вирішувати 902 — напишіть «чекати»: задача лишиться тут, код уже в гілці й нічого не блокує. Порада агента: (а) — робота готова, бракує лише запису PASS. Те саме питання стоїть у задачі 719.
   Відповідь:
