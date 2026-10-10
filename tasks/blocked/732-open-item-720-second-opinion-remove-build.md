# 732 — Прибрати з двигуна другу думку Gemini (відповідь власника «так» у задачі 720)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 720-second-opinion-remove-build

## Що сталося
Вимір задачі 013 (2026-10-06): два пороги з трьох не пройдено — Gemini заперечив 45% правильних знахідок simplifier-а (поріг 10%) і впіймав стільки ж хибних, скільки свіжий Claude. У задачі 720 власник відповів «так» на питання «Прибрати з двигуна збудовану другу думку (скрипт, таблицю понижень, ключі налаштувань, тести), лишивши результат виміру?». Друга думка всюди вимкнена (SECOND_OPINION=off), тож поведінка simplifier-а від прибирання не змінюється. Звіти: tasks/done/013-gemini-second-opinion-build/report.md, tasks/done/720-open-item-013-second-opinion-remove-or-keep/report.md. Нічого не чекає на цю задачу, крім задачі 736 (ключ Gemini в середовищі сесії): після прибирання її предмет зникає.

- Записано: 2026-10-07T13:04:05Z, агент

## Що зробити
Мала робота, одним slice-ом; платних прогонів немає. Прибрати: (1) .claude/hooks/second_opinion.py; (2) у .claude/hooks/simplifier.py — таблицю понижень у route, другу думку у звіті, команду decide і окремий рахунок другої думки в reversals; simplifier після цього має працювати точно як до задачі 013 (commit 43cd0aa показує, що саме було додано; перед видаленням decide і reversals перевір, що ними не користується ніщо, крім другої думки, — що користується, лиши); (3) evals/run_second_opinion_evals.py — без скрипта другої думки він не працює; (4) tests/test_second_opinion.py і tests/test_second_opinion_evals.py та їхні рядки в tests/fast-suites.txt і tests/hook-env-exempt.txt; (5) ключі SECOND_OPINION, SECOND_OPINION_MODEL, SECOND_OPINION_PRICE_IN, SECOND_OPINION_PRICE_OUT, SECOND_OPINION_MAX_USD з коментарями в .claude/project.env і templates/project/.claude/project.env; (6) розділи й рядки про другу думку в .claude/references/simplifier.md, .claude/references/hooks.md, docs/engine-limits.md, evals/README.md. Лишити як запис: результат виміру evals/baseline/linux-ubuntu-22.04/second-opinion-evals-2026-10.json і набір прикладів evals/scenarios/second-opinion/ — з одним рядком в evals/README.md: що це, коли виміряно, що пороги не пройдено і що скрипт виміру лежить в історії git (назви commit). Не чіпати: tasks/, tests/fixtures/board-inbox/, історичні записи в .engine/ (ledger, artifacts, bugs, simplifier/second-pass, lesson-queue). Перевірити, чи проєкт, у який двигун уже встановлено, після оновлення не лишається зі старим second_opinion.py (як engine.py прибирає файли, яких у новій версії немає) і чи зайві ключі SECOND_OPINION* у його project.env нічого не ламають; якщо лишається — записати у звіт або окремим відкритим пунктом, не розширюючи цю задачу. Перевірка: grep -ri 'second.opinion' поза tasks/, .engine/, tests/fixtures/ і лишеним записом виміру нічого не знаходить; негативний випадок — simplifier.py decide і second_opinion.py більше не існують і виклик дає зрозумілу відмову, а не traceback; набори тестів simplifier-а зелені; повний набір тестів один раз наприкінці. У звіті сказати власникові: ключ Gemini й файл simplifier-key.sh у теці оператора агент не бачить і не чіпає — відкликати ключ і прибрати файл може лише власник; і запропонувати закрити задачу 736 як таку, що втратила предмет (питанням, якщо вона ще відкрита).

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
1. Усе з задачі зроблено, крім одного файла. Скрипт `.claude/hooks/second_opinion.py`, тести, ключі
   `SECOND_OPINION*`, розділи документації й друга думка в `simplifier.py` прибрані. Overseer дав PASS (запити
   `20261010T100144Z-f733a2` і `20261010T103208Z-66db60`). Але delete guard не дає агентові видалити
   `evals/run_second_opinion_evals.py`: його функції `ask_gemini` і `ask_claude` не мали тесту, а таке видалення пропускає
   лише ваше слово. Без `second_opinion.py` скрипт уже не запускається (`ModuleNotFoundError`, це перевіряє тест).

   Як прибрати його? Раджу (а): у своєму терміналі `git rm evals/run_second_opinion_evals.py && git commit -m "board 732:
   the second opinion's measurement script, after the hook"`, а потім напишіть тут «готово». Інші варіанти:
   - (б) лишити файл як непрацюючий запис поруч із виміром;
   - (в) інше — напишіть як.

   За (а) агент, що виконає відповідь, в тому самому commit-і змінить перевірку GONE в `tests/test_simplifier.py`: зараз
   вона чекає, що скрипт є і не запускається, тому після видалення почервоніє. До вашої відповіді
   `python3 evals/run_second_opinion_evals.py` закінчується traceback-ом `ModuleNotFoundError`. Будь-яка відповідь
   поверне задачу в чергу.
   Відповідь:
