# 728 — Сигнал unused-dependency: ім'я пакета проти імені імпорту, і залежність, яку імпортує лише тест — звіт

## Що змінилось для власника
- **Сигнал знає ім'я імпорту пакета.** У `.claude/hooks/simplify_signals.py` коротка таблиця `IMPORT_NAMES`
  (pyyaml→yaml, pillow→PIL, beautifulsoup4→bs4, python-dateutil→dateutil, scikit-learn→sklearn, opencv-python→cv2 та
  інші). Пакет, чий модуль імпортовано, сигналу більше не дає; пакет, якого не імпортує ніхто, названо за іменем
  імпорту: «pillow is declared and no module named PIL is imported».
- **Runtime-залежність, яку імпортують лише тести, має окремий текст:**
  `<name> is a runtime dependency imported only by tests: <файли>` — це кандидат у dev-групу, не на видалення. Для
  складнішого evaluation set сигнал тепер каже правду про pyyaml (текст — у демонстрації нижче).
- **`docs/engine-limits.md`** (розділ «The simplifier») каже, що таблиця знає і де сигнал і далі хибить: пакет поза
  таблицею, `importlib`, namespace package. У `tests/test_simplifier_evals.py` — перевірка запиту складнішого набору.
- **Задача чекала вас не через код.** Перший audit не знайшов жодної невдалої перевірки, але PASS не приймався, поки
  була відкрита gate escalation задачі 902. Ви її закрили й відповіли «закрито»; новий overseer перевірив роботу
  наново — PASS (request `20261012T214331Z-8efaee`). Код у цій сесії не змінювався.
- **Задача лежить у `blocked/`, а не в `done/`, і знову не через код.** `mode.py check-close` не приймає цей PASS:
  `tests/test_simplifier_evals.py` після commit-а `431a3f1` змінила задача 730 (commit `e8b168c`, 62 рядки додано, 1
  прибрано — випадки scorer-а), а перевірка шукає PASS на вміст файлів саме з того commit-а. Питання 2 у задачі — як
  це закрити (те саме, що в задачах 725 і 726).
- Чи змінився recall simplifier-а на цьому пункті — буде видно при наступному вимірі; у цій задачі вимірів не було.

## Демонстрація на хвилину
```bash
python3 tests/test_simplify_signals.py     # PASS 46   FAIL 0
python3 tests/test_simplifier_evals.py     # PASS 322   FAIL 0
python3 .claude/hooks/simplify_signals.py --scope full --json   # шукайте "unused-dependency"
```
Перевірено в цій сесії на дереві `92e1a24` (Python 3.12.13):
- обидва suites зелені: `PASS 46   FAIL 0` і `PASS 322   FAIL 0` (у першій сесії було 306; ще 16 — задачі 730);
- сигнали цього repository: `pyyaml is a runtime dependency imported only by tests:
  evals/scenarios/simplifier-hard/project/tests/test_price_fixtures.py` і
  `requests is declared and no module named requests is imported`;
- зі старим hook-ом (тимчасовий worktree, прибраний): `tests/test_simplify_signals.py` — два рядки `FAIL` і далі
  `KeyError: 'httpx'`, код 1 (підсумкового рядка немає); `tests/test_simplifier_evals.py` — `PASS 321   FAIL 1`;
- `bash tests/run_all.sh` — `PASS: 98 suites green`, код 0;
- overseer сам відтворив усі ці числа, а ще перевірив на власному пробному проєкті імена з великими літерами
  (Pillow, PyJWT), extras із marker-ом і файл тесту поза `tests/` — усе поводиться, як заявлено.

## Витрати
- Додаткових сесій Claude скриптами evals не було.
- Два audit-и overseer-а (один у першій сесії, один у цій) — звичайні subagent-и в сесії runner-а.
- Повний набір тестів: один прогін у першій сесії, один у цій (обидва — 98 suites зелені).

## Діапазон commit-ів
- `423d5ca` — задача в `doing/` (база).
- `431a3f1` — код, тести, `docs/engine-limits.md` і перенесення в `blocked/` з питанням.
- `92e1a24` — задача знову в `doing/` після вашої відповіді.
- наступний commit — цей звіт, turn file для overseer-а, ledger сесії, перенесення в `blocked/` з питанням 2.

## Відкладене
- `tasks/todo/1719-…` — test gap першого audit-у: `pyproject.toml`, що сам лежить у теці з назвою `tests/`.
- `tasks/todo/1720-…` — test gap: оголошене ім'я з підкресленнями, великими літерами, extras і marker-ом.
- Зауваження другого overseer-а (не test gap і не помилка): текст «imported only by tests» перелічує всі файли тестів
  без межі, тож у проєкті, де, скажімо, pytest стоїть серед runtime-залежностей, рядок сигналу буде завдовжки з усе
  дерево тестів і цілим піде в запит simplifier-а. Задача межі не ставила; варто глянути, коли наступного разу
  мірятимуть розмір запиту.
- Відомі межі, записані в `docs/engine-limits.md`: пакет поза таблицею (наприклад `ruamel.yaml` шукається як
  `ruamel_yaml`), `importlib`, namespace package (`protobuf` мовчить за будь-якого імпорту `google.*`).

## Рішення, які я ухвалив сам
- **Після відмови check-close переніс задачу в `blocked/` сам:** отримати PASS на вміст `tests/test_simplifier_evals.py`
  з commit-а `431a3f1` неможливо, а commit, що лише торкається цього файлу заради перевірки, був би обходом.
- **Новий текст лишається в kind `unused-dependency`,** без окремого kind — щоб підсумки `/maintain` і історія
  метрик рахували як раніше.
- **Файл тесту — те, що так називає `complexity_budget.is_test`,** за шляхом відносно теки `pyproject.toml`; у
  тексті сигналу шлях від кореня repository.
- **Функцію розбито на три** (`import_names`, `imported_modules`, `importers`): `unused_dependency_signals` була
  понад межу complexity (19 при межі 13) і nesting (5 при межі 3).
- **У таблиці кілька відомих розбіжностей понад названі в задачі** (attrs, pyjwt, python-dotenv, protobuf тощо).
- **Unit заявив руками, а не через Stop hook:** код після останнього request не мінявся, тож hook audit-у не попросив
  би. Turn file `.engine/artifacts/overseer/turn-2026-10-12-board-728-close.md` і `overseer_verdict.py request` — шлях
  зі skill `overseer`.
- **Повний набір тестів запустив ще раз:** після першої сесії гілка отримала commit-и інших задач, і overseer мав
  судити теперішнє дерево.
- **Задачі 1719 і 1720 не закривав сам** — у `doing/` одночасно лише одна задача.
