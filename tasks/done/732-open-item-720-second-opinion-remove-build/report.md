# 732 — Друга думка Gemini прибрана з двигуна

## Що змінилось для власника
- **Другої думки Gemini в двигуні більше немає.** Прибрано:
  - скрипт `.claude/hooks/second_opinion.py`;
  - скрипт виміру `evals/run_second_opinion_evals.py` — його видалили ви, commit `ed7a4af` (delete guard не дав цього
    агентові);
  - тести `tests/test_second_opinion.py` і `tests/test_second_opinion_evals.py` з їхніми рядками в
    `tests/fast-suites.txt` і `tests/hook-env-exempt.txt`;
  - ключі `SECOND_OPINION`, `SECOND_OPINION_MODEL`, `SECOND_OPINION_PRICE_IN`, `SECOND_OPINION_PRICE_OUT`,
    `SECOND_OPINION_MAX_USD` з коментарями в `.claude/project.env` двигуна і в шаблоні для проєктів;
  - розділи про другу думку в `.claude/references/simplifier.md`, `.claude/references/hooks.md`,
    `docs/engine-limits.md`, `docs/ARCHITECTURE.md`.
- **`simplifier.py` працює так, як до задачі 013.** Таблиці понижень у `route`, рядка другої думки у звіті й окремого
  рахунку другої думки в `reversals` немає.
  - **Команда `decide` лишилась:** нею `delete_guard.py confirm` записує ваше підтвердження видалення. Тепер вона пише
    лише ваше рішення, без вердикту другої моделі.
- **Лишено як запис:** результат виміру `evals/baseline/linux-ubuntu-22.04/second-opinion-evals-2026-10.json` і набір
  прикладів `evals/scenarios/second-opinion/`. В `evals/README.md` про них один рядок: що це, коли виміряно
  (2026-10-06), що два пороги з трьох не пройдено, і де скрипти в історії git — збудовано в commit `43cd0aa`, остаточний
  вигляд у `79c40f5`, скрипт виміру видалено в `ed7a4af`. У цій сесії я виправив у ньому лише кінець: там було сказано,
  що скрипт виміру ще стоїть.
- **Ключ Gemini і файл `simplifier-key.sh`** у теці оператора агент не бачить і не чіпає. З вашої відповіді в задачі 736:
  файл і рядок, що виконував його перед стартом runner-а, оператор прибрав, а ключ у Google не відкликаєте. У
  середовищі цієї сесії змінної `GEMINI_API_KEY_SIMPLIFIER` немає (перевірено лише, чи вона задана; значення я не читав).
- **Задача 736** втратила предмет. Ви відповіли на неї «так», вона лежить у `todo/`, і runner закриє її окремо.

## Демонстрація на хвилину
```bash
python3 tests/test_simplifier.py | grep GONE -A5
ls .claude/hooks/second_opinion.py evals/run_second_opinion_evals.py
grep -rnIi "second.opinion" --exclude-dir=.git --exclude-dir=tasks --exclude-dir=.engine --exclude-dir=fixtures . \
  | grep -v "second-opinion-evals-2026-10.json:\|evals/scenarios/second-opinion/"
```
- Друга команда каже «No such file or directory» про обидва файли.
- Третя показує лише три законні місця: рядок-запис в `evals/README.md`, назву файла-фікстури в `tests/test_board.py`
  (фікстури `tests/fixtures/board-inbox` задача велить не чіпати) і перевірки GONE в `tests/test_simplifier.py`.

## Як перевірено
- `tests/test_simplifier.py` — 96 пройдено, 0 провалено. Перевірки GONE-*:
  - обох скриптів немає;
  - відповідь, у якій ще є друга думка, за `SECOND_OPINION="on"` нічого не знижує, і звіт про неї мовчить;
  - `decide` пише рішення без другої моделі.
- Негативний випадок:
  - `python3 .claude/hooks/second_opinion.py` і `python3 evals/run_second_opinion_evals.py` — «can't open file … No
    such file or directory», без traceback;
  - `simplifier.py decide` без аргументів — рядок usage і «the following arguments are required: finding, answer».
- Повний набір `bash tests/run_all.sh`, один раз наприкінці: **90 наборів зелені**.
  - Перший запуск я сам обмежив десятьма хвилинами, і його зупинило на 15-му наборі (усі 15 зелені). Другий запуск
    дійшов до кінця.
- Overseer:
  - PASS `20261010T100144Z-f733a2` і PASS `20261010T103208Z-66db60` на commit `7f9c831` (прибирання);
  - PASS `20261011T065410Z-7e3795` на commit закриття `969ec8c` — це audit усього дерева, як воно є тепер, разом із
    вашим commit-ом `ed7a4af`. Overseer сам прогнав повний набір: 90 наборів зелені.

## Що не сходиться: перевірка закриття (`mode.py check-close`)
- Перевірка каже, що мінімуму режиму «соло» немає: на commit `7f9c831` вона не знаходить PASS overseer-а.
- PASS на нього є, навіть два, і вони записані в `.engine/overseer/ledger.md`. Але перевірка читає не ledger, а стан
  hooks у `.claude/state/overseer/`. Він не лежить у git, а ті audit-и пройшли в іншому клоні, тож на цьому сервері їх
  немає.
- Новим audit-ом цього не закрити: `tests/test_simplifier.py` і `evals/README.md` після `7f9c831` змінили ваш commit
  `ed7a4af` і commit закриття, тож вміст файлів уже не той, що був у `7f9c831`.
- Обходити перевірку я не став: стан hooks агент не пише. Тому runner, найімовірніше, поверне цю задачу в `blocked/` з
  питанням до вас. Раджу відповісти, що задачу можна закрити: код у його теперішньому стані має PASS.
- Записано в журнал аномалій і відкрито пункт на task board (ключ `check-close-pass-from-another-clone`), щоб
  перевірку виправити.

## Проєкти, у які двигун уже встановлено
- `engine.py update` прибирає файл двигуна, якого немає в новій версії: `second_opinion.py` піде як «retired by the
  engine», якщо проєкт його не правив. Якщо правив — лишиться, і оновлення про це скаже.
- Ключі `SECOND_OPINION*` у `project.env` такого проєкту ніхто не читає, тож вони нічого не ламають (це перевіряє GONE:
  `SECOND_OPINION="on"` нічого не змінює). Прибирати їх звідти оновлення не буде — вони лишаться зайвими рядками.

## Витрати
Додаткових сесій Claude не було. Overseer у попередній сесії — її субагент.

## Діапазон commit-ів
`7f9c831` (прибирання) → `ed7a4af` (ваш commit: скрипт виміру і перевірка GONE) → `969ec8c` (рядок в `evals/README.md`, закриття) → commit
із записом audit-у і цим звітом.

## Відкладене
- Виправлення `check-close` — окремий відкритий пункт у `tasks/todo/` (див. вище).
- Задача 736 уже в черзі з вашою відповіддю.

## Рішення, які я ухвалив сам
- `decide` не прибрав: ним користується `delete_guard.py confirm` (задача так і каже — «що користується, лиши»).
- Задачу 736 не закривав у цій задачі: вона окремо лежить у `todo/` з вашим «так».
- Чернетку звіту `tasks/blocked/report-732-…md` прибрав: її зміст — у цьому звіті.
