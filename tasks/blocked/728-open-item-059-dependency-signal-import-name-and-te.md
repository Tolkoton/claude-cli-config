# 728 — Сигнал unused-dependency: ім'я пакета проти імені імпорту, і залежність, яку імпортує лише тест

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 059-dependency-signal-import-name-and-tests-only

## Що сталося
Задача 059: у складнішому evaluation set pyyaml стоїть у [project].dependencies, а імпортує його (як yaml) лише tests/test_price_fixtures.py. Сигнал .claude/hooks/simplify_signals.py каже «pyyaml is declared and no module named pyyaml is imported» — тобто вказує на правильний рядок із хибної причини: він порівнює ім'я дистрибутива з ім'ям модуля (межа записана в docs/engine-limits.md: pillow / PIL) і не розрізняє «не імпортує ніхто» та «імпортують лише тести». Наслідок у вимірі (evals/baseline/linux-ubuntu-22.04/simplifier-hard-evals-2026-10-07.json): simplifier знайшов цю залежність у 4 сесіях із 5 і щоразу лише як flag_only; у сесії 4 він прямо назвав сигнал «a false lead», у сесії 5 знахідки немає зовсім.

- Записано: 2026-10-07T02:47:51Z, агент

## Що зробити
Тест спершу в tests/test_simplify_signals.py. (1) Ім'я імпорту: коротка таблиця відомих розбіжностей (pyyaml→yaml, pillow→PIL, beautifulsoup4→bs4, python-dateutil→dateutil, scikit-learn→sklearn, opencv-python→cv2 тощо) — пакет, чий модуль імпортовано, сигналу не дає. (2) Runtime-залежність, яку імпортують лише файли тестів, дає окремий текст сигналу: «imported only by tests: <файл>» (це кандидат у dev-групу, не на видалення). Оновити рядок у docs/engine-limits.md і перевірку запиту в tests/test_simplifier_evals.py (складніший набір). Платних прогонів не треба; чи змінився recall на цьому пункті — видно при наступному платному вимірі.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника

Стан роботи (2026-10-12): зроблено, перевірено і закомічено в цій гілці.
- Ім'я імпорту: у `.claude/hooks/simplify_signals.py` коротка таблиця `IMPORT_NAMES` (pyyaml→yaml, pillow→PIL, beautifulsoup4→bs4, python-dateutil→dateutil, scikit-learn→sklearn, opencv-python→cv2 та інші, разом 25 рядків). Пакет, чий модуль імпортовано, сигналу не дає; пакет, якого не імпортує ніхто, названо за іменем імпорту («pillow is declared and no module named PIL is imported»).
- Залежність, яку імпортують лише тести: окремий текст — `<name> is a runtime dependency imported only by tests: <файли>`. У цьому repository сигнал для складнішого evaluation set тепер такий: `pyyaml is a runtime dependency imported only by tests: evals/scenarios/simplifier-hard/project/tests/test_price_fixtures.py`.
- `docs/engine-limits.md` (розділ «The simplifier») оновлено: що таблиця знає, де сигнал і далі хибить (пакет поза таблицею, `importlib`, namespace package), і окремий пункт про «imported only by tests». У `tests/test_simplifier_evals.py` нова перевірка запиту складнішого набору.
- Тести: `python3 tests/test_simplify_signals.py` — на коді до зміни нові випадки червоні, після — `PASS 46 FAIL 0`; `python3 tests/test_simplifier_evals.py` — `PASS 306 FAIL 0`, без зміни hook-а `PASS 305 FAIL 1`; `bash tests/run_all.sh` — `PASS: 98 suites green`. Платних прогонів не було.
- Рішення, які я ухвалив сам: (1) новий текст лишається в kind `unused-dependency`, без окремого kind — щоб підсумки `/maintain` і історія метрик рахували як раніше; (2) файл тесту — те, що так називає `complexity_budget.is_test`, за шляхом відносно теки `pyproject.toml`; у тексті сигналу шлях від кореня repository; (3) функцію розбито на три (`import_names`, `imported_modules`, `importers`): `unused_dependency_signals` більше не перевищує межі complexity (було 19 при межі 13) і nesting (було 5 при межі 3); (4) у таблицю додано ще кілька відомих розбіжностей понад названі в задачі (attrs, pyjwt, python-dotenv, protobuf тощо).
- Overseer (request `20261012T063313Z-0aafe5`) не знайшов жодної невдалої перевірки й сам відтворив і RED, і GREEN, але вердикт записано як BLOCK 1 із 3 лише тому, що відкрита gate escalation 2026-10-12T01:56:46Z чужої задачі (slice `numbers-class-table`, файл `tests/test_task_class_table.py`, питання `tasks/blocked/902-gate-escalation-20261012T015646Z.md`). Цього файлу моя робота не торкається; закрити escalation агент не може і не має. Дві прогалини в тестах, які назвав overseer, лежать задачами `tasks/todo/1719-…` і `tasks/todo/1720-…`.

Чого бракує до `done/`: запису PASS overseer-а і `report.md`.

1. Як закрити цю задачу? Варіанти: (а) ви відповідаєте «так» на питання 902 (або закриваєте escalation у своєму терміналі: `python3 .claude/hooks/gate.py --close-escalation 2026-10-12T01:56:46Z`), а тут пишете «закрито» — агент знову заявляє unit, новий overseer перевіряє, задача йде в `done/` зі звітом; (б) не хочете зараз вирішувати 902 — напишіть «чекати»: задача лишиться тут, код уже в гілці й нічого не блокує. Порада агента: (а) — робота готова, бракує лише запису PASS. Те саме питання стоїть у задачах 719, 725 і 726.
   Відповідь: закрито
