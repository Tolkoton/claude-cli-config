# 771 — перевірка «python3.11 compiles every Python file» тепер справді бере кожен файл: звіт

## Що змінилось для власника
- **Тест знайшов справжню ваду, тому перевірку змінено** (commit `48df456`). `tests/test_engine_lint.py` друкував
  «python3.11 compiles every Python file of the repository», а передавав інтерпретатору 158 файлів із 259 tracked:
  лише файли двигуна під `.claude/`, `engine.py`, `evals/*.py` і `tests/*.py`.
- **Тепер перелік файлів дає git:** `git ls-files --cached --others --exclude-standard '*.py'` — усі tracked файли на
  будь-якій глибині (і `evals/scenarios/**`) плюс нові, яких git не ігнорує. Рядок перевірки каже це сам:
  «…every Python file of the repository — tracked, or new and not ignored (260)».
- **Test gap тримає новий набір `tests/test_engine_lint_tracked.py`** (14 перевірок, у швидкому наборі, близько 6 с).
- **Ще дві малі зміни в тій самій перевірці:**
  - якщо git не дав жодного файлу, вона друкує FAIL, а не компілює нуль файлів і проходить;
  - перелік знайденого обрізається на 3000 символах, а не на 300 — інакше третій файл у ньому вже не видно.
- **На цьому сервері сама перевірка, як і раніше, не запускається:** `python3.11` тут немає, lint друкує примітку й
  `PASS`. Це окрема задача в черзі — `tasks/todo/1725-open-item-test-gap-test-engine-lint-reports-a-form.md`.

## Демонстрація на хвилину
```bash
python3 tests/test_engine_lint_tracked.py
```

Набір будує тимчасовий git-репозиторій з усіма tracked `.py` файлами і ставить першим на PATH stand-in з назвою
`python3.11`: той записує, які файли йому передали, і компілює їх цим самим інтерпретатором із граматикою, втриманою
на 3.11 (`ast.parse(..., feature_version=(3, 11))`).

Прогони цієї сесії:

| Що запущено | Результат |
|---|---|
| lint, яким він був (RED) | `FAIL: 4 passed, 10 failed` — «158 handed, 259 tracked»; з `type Row = ...` у `watch.py` lint друкує `PASS: engine lint clean` |
| lint, яким він є (GREEN) | `PASS: 14 passed, 0 failed` |
| mutant без `"--others"` (RED) | `FAIL: 13 passed, 1 failed` — новий файл поза git не названо |
| mutant без `"--exclude-standard"` (RED) | `FAIL: 10 passed, 4 failed` — передано ігнорований `ignored/broken.py` |
| `python3 tests/test_engine_lint.py` зі stand-in на PATH, справжнє дерево | `ok python3.11 compiles every Python file of the repository — tracked, or new and not ignored (260)`, `PASS: engine lint clean` |
| `python3 tests/test_engine_lint_oldest.py` | `PASS: 7 passed, 0 failed` |
| `bash tests/run_all.sh --fast` | `PASS: 49 suites green (fast subset)` |
| `bash tests/run_all.sh` | `PASS: 102 suites green` (було 101) |

- У RED-сцені 3.12-only форми стоять у трьох місцях: `type Row = ...` у `evals/scenarios/tester-property/watch.py`,
  `def first[T](...)` у `evals/scenarios/tester/scenes/order/right.py` і `type Row = ...` у новому файлі, ще не доданому
  в git. Lint має вийти з ненульовим кодом і назвати всі три.
- Overseer: **PASS** `20261013T093006Z-1514aa`. Він відтворив RED на lint-і з HEAD (у нього «159 handed, 260 tracked» —
  уже з новим файлом тесту), обидва mutant-и і додав свій: гілка «git listed none» як `elif False` — `12 passed, 2 failed`.
  Нового test gap-у не записав.
- Mutant-и запускались у копії поза деревом; робоче дерево для них не змінювалось.

Не перевірено:
- **Жоден прогін не був під справжнім `python3.11`** — на сервері його немає (є 3.10, 3.12, 3.13). Stand-in відмовляє
  `type X = ...` і `def f[T]()`, але пропускає f-string-форми 3.12 (backslash у виразі, повторна зовнішня лапка) — саме
  той клас, з якого почалась задача 748.
- **У дереві вже є така форма:** `evals/run_simplifier_evals.py:364` (повторна зовнішня лапка в f-string). Її показує
  `ruff --target-version py311`; на машині зі справжнім `python3.11` lint на ній червоний — і був червоний до цієї
  задачі, бо файл входив і в старий перелік. У 101 щойно охопленому файлі ruff таких форм не знайшов (прогін overseer-а).
  Рядок не виправлено: його разом із тестом має виправити задача 1725.
- Нове формулювання рядка («tracked, or new and not ignored») тест не звіряє дослівно — лише число файлів у ньому.

## Витрати
- Додаткових сесій Claude не було. Overseer — subagent цієї сесії.
- Швидкий набір: один прогін. Повний набір: один прогін.

## Діапазон commit-ів
- `a00add1` — задача в `doing/`.
- `48df456` — `tests/test_engine_lint.py`, новий `tests/test_engine_lint_tracked.py`, рядок у `tests/fast-suites.txt`,
  journal overseer-а.
- наступний commit — цей звіт і перенесення в `done/`.

## Відкладене
- **Lint на машині без `python3.11`** не компілює жодного з 260 файлів, а ruff судить лише 35 файлів двигуна — задача
  1725 у `todo/`. Її формулювання («every file its own compile check names») тепер означає перелік git, тож нової
  задачі я не відкривав.

## Рішення, які я ухвалив сам
- **Розширив перелік, а не звузив напис.** Задача дозволяла будь-що з двох. `watch.py` дописується в модулі сцен під час
  eval-ів, тож форма, якої 3.11 не читає, там — справжня поломка, а не питання напису.
- **До tracked додав нові не ігноровані файли (`--others --exclude-standard`).** Старий glob бачив щойно створений
  `tests/*.py` ще до `git add`; лише tracked — це було б звуження для роботи в процесі. Ціна: чернетка `.py` з новішим
  синтаксисом, залишена в дереві поза git, зробить lint червоним на машині з `python3.11`. Скасовується одним прапорцем.
- **Без git перевірка тепер FAIL, а не тихий прохід** — за правилом самого файлу: gate, що не може запуститись, не
  запустився. Єдиний, хто запускає lint у копії без `.git`, — `test_engine_lint_oldest`, і він спершу прибирає
  `python3.11` з PATH, тож до цієї гілки не доходить.
- **Stand-in замість справжнього `python3.11` — на кожній машині,** не лише там, де його немає: сцена однакова всюди, і
  рядок 364 не робить «зелений» прогін червоним там, де 3.11 є.
- **Обрізання 300 → 3000 символів:** три знахідки в одному рядку не вміщались у 300, і третій файл зникав зі звіту lint-а.
- **Набір додано у швидкий (`tests/fast-suites.txt`),** як і сусідній `test_engine_lint_oldest`: сам lint стоїть на
  Stop gate.
- **`evals/run_simplifier_evals.py:364` не чіпав:** задача 1725 вимагає показати RED саме на цьому рядку.
