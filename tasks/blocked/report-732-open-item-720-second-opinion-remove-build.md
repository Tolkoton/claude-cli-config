# 732 — Друга думка Gemini прибрана з двигуна: чернетка звіту (задача в `blocked/`)

## Чому задача тут, а не в `done/`
- Усе прибрано, крім одного файла: `evals/run_second_opinion_evals.py`. Delete guard не дає агентові видалити його
  функції `ask_gemini` і `ask_claude`: жоден тест їх не торкався. Пропустити таке видалення можуть лише ви —
  підтвердженням у своєму терміналі або дозволом у запечатаному slice contract. Писати «тест» для коду, який ми
  прибираємо, означало б обійти guard, тому я цього не робив.
- Без `.claude/hooks/second_opinion.py` цей скрипт уже не запускається: він називає відсутній модуль, і це перевіряє
  тест. Решту зміни закомічено. Питання — у задачі.

## Що змінилось для власника
- **Прибрано:**
  - скрипт `.claude/hooks/second_opinion.py` (вимір `evals/run_second_opinion_evals.py` чекає на вас, див. вище);
  - тести `tests/test_second_opinion.py` і `tests/test_second_opinion_evals.py` разом з їхніми рядками в
    `tests/fast-suites.txt` і `tests/hook-env-exempt.txt`;
  - ключі `SECOND_OPINION`, `SECOND_OPINION_MODEL`, `SECOND_OPINION_PRICE_IN`, `SECOND_OPINION_PRICE_OUT`,
    `SECOND_OPINION_MAX_USD` з коментарями в `.claude/project.env` двигуна і в шаблоні для проєктів;
  - розділи про другу думку в `.claude/references/simplifier.md`, `.claude/references/hooks.md`,
    `docs/engine-limits.md`, `docs/ARCHITECTURE.md`.
- **`simplifier.py`** працює так, як до задачі 013. Таблиці понижень у `route` немає, рядка другої думки у звіті немає,
  окремого рахунку другої думки в `reversals` і порівняння її вердиктів із вашими рішеннями немає.
  - **`decide` лишився.** Ним користується не лише друга думка: `delete_guard.py confirm` записує ним ваше
    підтвердження видалення. Тепер він пише лише ваше рішення, без вердикту другої моделі. Так велить задача:
    «що користується, лиши».
- **Лишено як запис:** результат виміру `evals/baseline/linux-ubuntu-22.04/second-opinion-evals-2026-10.json` і набір
  прикладів `evals/scenarios/second-opinion/`. В `evals/README.md` про них один рядок: що це, коли виміряно, що пороги
  не пройдено, а скрипти лежать в історії git (commit-и `43cd0aa` і `79c40f5`).
- **Ключ Gemini і файл `simplifier-key.sh` у теці оператора агент не бачить і не чіпає.** Відкликати ключ у Google і
  прибрати файл (і його виконання перед стартом runner-а) можете лише ви.
- **Задача 736** (ключ Gemini видно агентові через середовище сесії) втратила предмет: скрипта, якому потрібен ключ,
  більше немає. Я поставив у ній питання, чи закрити її, і переніс у `blocked/`. Але поки runner експортує ключ зі
  `simplifier-key.sh`, змінна в середовищі сесій лишається — тому раджу прибрати і виконання файла.

## Демонстрація на хвилину
```bash
python3 tests/test_simplifier.py | grep GONE -A4
grep -rni "second.opinion" --exclude-dir=.git . | grep -v "^./tasks/\|^./.engine/\|^./tests/fixtures/\|second-opinion-evals-2026-10.json\|scenarios/second-opinion/"
```
Друга команда показує лише законні місця:
- рядок-запис в `evals/README.md`;
- назву файла-фікстури в `tests/test_board.py` (`tests/fixtures/board-inbox`, яку за умовою задачі не чіпаємо);
- негативні перевірки GONE в `tests/test_simplifier.py`;
- сам `evals/run_second_opinion_evals.py`, що чекає на вас.

## Як перевірено
- `tests/test_simplifier.py` — 96 пройдено, 0 провалено. Нові перевірки GONE-*:
  - скрипта другої думки немає, а скрипт виміру, що лишився, не запускається й називає відсутній модуль;
  - відповідь, у якій ще є друга думка, за `SECOND_OPINION="on"` нічого не знижує: auto_remove лишається auto_remove,
    confirm — confirm, а звіт нічого не каже про другу думку;
  - `decide` пише рішення без другої моделі;
  - `reversals` про неї мовчить.
  - Mutant, що повертає зниження з задачі 013, на цьому червоніє.
- `test_delete_guard` 64/0 (`confirm` через `decide`), `test_goals` 87/0, `test_complexity_budget` 50/0,
  `test_engine_install` 49/0, `test_ownership` 99/0, `test_hook_env` 25/0, `test_board` 276/0; `test_engine_lint`
  (ruff + mypy --strict) — чисто; `bash tests/run_all.sh --fast` — 38 наборів зелені; golden set — 281/281, поведінка та
  сама.
- Повного `bash tests/run_all.sh` не запускав: цієї ночі власник просив обходитись швидким набором і тестами зміни.
- Overseer: **PASS** `20261010T100144Z-f733a2`, і ще раз після того, як скрипт виміру повернувся в дерево, — **PASS** `20261010T103208Z-66db60`. Обидва overseer-и прогнали й повний набір у своїй копії: 87 наборів зелені.

## Проєкти, у які двигун уже встановлено
- `engine.py update` прибирає файл двигуна, якого немає в новій версії: `second_opinion.py` піде як «retired by the
  engine» (`engine.py`, план оновлення), якщо проєкт його не правив. Якщо правив — лишиться, і оновлення про це скаже.
- Ключі `SECOND_OPINION*` у `project.env` проєкту ніхто більше не читає, тож нічого не ламають (це видно з перевірки
  GONE: `SECOND_OPINION="on"` нічого не змінює).

## Витрати
Додаткових сесій Claude не було. Overseer — субагент цієї сесії.

## Рішення, які я ухвалив сам
- `decide` не прибрав, бо ним користується `delete_guard.py confirm` (задача так і каже).
- Задачу 736 переніс у `blocked/` з питанням, а не закрив сам: її предмет зник, але закрити задачу — ваше рішення.
