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
