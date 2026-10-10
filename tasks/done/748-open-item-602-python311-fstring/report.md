# 748 — Python 3.11 знову підтримано: звіт

## Що змінилось для власника
- Hook-и кажуть «Standard library only; Python 3.11+», але `.claude/hooks/testing.py` під 3.11 не запускався:
  backslash усередині виразу f-рядка (рядок 202) дозволено лише з 3.12. Тому під 3.11 падали й усі, хто імпортує
  `testing.py` (`test_goals`, `test_lesson_queue`, `test_contract_fingerprint`). Заміну винесено з f-рядка, і
  поведінка та сама: рядок журналу тестування пишеться точно так, як раніше.
- **Перевірено весь Python репозиторію**, як просить задача: `python3.11` компілює кожен файл `.claude/`, `engine.py`,
  `evals/` і `tests/` (140 файлів). Таке місце було лише одне, тож питання про мінімальну версію 3.12 не потрібне.
- **Щоб це не повторилось:** `tests/test_engine_lint.py` (у швидкому наборі) тепер компілює всі ці файли найстаршим
  підтримуваним інтерпретатором `python3.11`, якщо він є на машині. Якщо його немає, набір каже про це рядком `note`.

## Демонстрація на хвилину
```bash
python3 tests/test_engine_lint.py | grep python3.11
python3.11 tests/test_goals.py | tail -1
```

## Як перевірено
- Без виправлення нова перевірка червоніє й називає місце:
  `FAIL python3.11 compiles every Python file of the repository (140) .claude/hooks/testing.py:202: f-string expression
  part cannot include a backslash`. З виправленням — `ok`.
- Під python3.11: `test_goals` 87/0, `test_lesson_queue` 101/0, `test_contract_fingerprint` 16/0, `test_testing` 192/0.
  Тепер і випадки бага 007 (задача 747) зелені під 3.11. Під python3 (3.13): `test_testing` 192/0.
- `bash tests/run_all.sh --fast` — 38 наборів зелені; ruff і mypy — чисто.
- Overseer: **PASS** `20261010T114754Z-dd8612`. Він сам скомпілював усі 238 Python-файлів репозиторію під 3.11 (усі
  чисті) і прогнав повний набір із python3 = 3.11: 88 наборів зелені. Три його пункти браку тестів — відкриті пункти:
  - `tasks/todo/769-open-item-test-gap-test-engine-lint-run-with-pytho.md`;
  - `tasks/todo/770-open-item-test-gap-testing-ledger-with-a-row-whose.md`;
  - `tasks/todo/771-open-item-test-gap-the-python3-11-compile-check-co.md`.
  Зміст пунктів: перевірка мовчить, коли python3.11 немає на машині; рядок журналу тестування з `--` не має свого
  тесту; перевірка компіляції бере 140 файлів, а не всі 238.

## Витрати
Додаткових сесій Claude не було. Overseer — субагент цієї сесії.

## Рішення, які я ухвалив сам
- Перевірку версії поклав у `test_engine_lint`, а не в окремий набір: це той самий «лінт» усього Python двигуна, він
  уже в швидкому наборі, а компіляція в пам'яті займає менше секунди.
- Без `python3.11` на машині перевірка не червоніє, а каже `note`: інші середовища двигуна можуть не мати старішого
  Python, і червоний набір там означав би не ваду коду, а машину.
