# Звіт — 404 Runner не паркує задачу за віком

## Що змінилось для власника

- **Сам час задачу більше не зупиняє.** Перевірку «задача відкрита довше за 12 год → `blocked/`» прибрано з
  `.claude/unattended/board-runner.sh`. Задача, яка й далі комітить, працює стільки, скільки їй треба.
- **Інші запобіжники лишились як були:** `no-commit` (три спроби поспіль без commit-а, `BOARD_STALL_ATTEMPTS`),
  `reader-blocks`, `BOARD_MAX_USD`, три BLOCK overseer-а.
- **Прибрано те, що лишилося без діла:** змінну `BOARD_TASK_MAX_SEC` / `TASK_MAX` у runner-і, поле `age_sec` у
  `board_state.py`, причину `deadline` у `board.py` («задача відкрита довше за {n} год»). Тепер
  `board.py park <задача> deadline` відмовляє (код 2). Згадки про дванадцять годин прибрано з
  `tasks/README.md`, `templates/project/tasks/README.md`, `.claude/unattended/README.md` і
  `docs/OWNER-GUIDE.md`. В обидва `README.md` дописано речення: «Сам час задачу не зупиняє (задача 404)».
- **Старі записи читаються, як і раніше.** Розділ `## Чому зупинилась` з рядком `deadline` у задачі чи запис
  у журналі аномалій — звичайний текст, і жоден скрипт не розбирає з нього назву причини. Тест показує: стара
  задача з таким записом читається, ваша відповідь у ній зараховується, і `unblock` повертає її в `todo/`.
- **Оновлення двигуна у вашому проєкті (thinkhow), де ці рядки закоментовано,** проходить без конфлікту, але
  не саме собою. `engine.py` не зливає файли, тож конфлікту не буває. Змінений вами `board-runner.sh` він
  тримає (`keep … edited in the project; the engine's version is not applied`) і завершується з кодом 1.
  Нову версію файла застосовує окрема команда:
  `python3 engine.py update <проєкт> --take .claude/unattended/board-runner.sh`. Вона замінює ваш файл версією
  двигуна, у якій цієї перевірки вже немає. Решта файлів (`board.py`, `board_state.py`) оновлюється без `--take`.

## Демонстрація на хвилину

```
python3 tests/test_board_runner.py | sed -n 45,48p
  ok   the default wait is 15 minutes, the stall 3 attempts; no limit on a task's age (board 404)
a task older than twelve hours
  ok   started 40 hours ago and committing: not parked — it resumes its conversation, works on and is done
  ok   NEGATIVE — started 40 hours ago and committing nothing: parked for no-commit after three attempts, as before; the next task is done
```

Оновлення проєкту, де власник закоментував перевірку. Перевірено у тимчасовому проєкті: встановлено з
`e8f09f5`, рядки закоментовано й закомічено, далі `update` на дерево з цією зміною:

```
keep    .claude/unattended/board-runner.sh  — edited in the project; the engine's version is not applied
update  .claude/unattended/board.py
update  .claude/unattended/board_state.py
Held back: the project changed these engine files. Review each one; `--take <path>` applies the engine's version.
(exit 1)
… --take .claude/unattended/board-runner.sh
update  .claude/unattended/board-runner.sh  — taken over on request (--take)
(exit 0; у файлі не лишилося ні TASK_MAX, ні age_sec)
```

## Перевірки

- `bash tests/run_all.sh` — `PASS: 120 suites green`.
- `tests/test_board_runner.py` — PASS 380, FAIL 0. Нові перевірки: задача, почата 40 год тому, яка комітить, не
  паркується і доходить до `done/`. Задача того ж віку без commit-ів паркується за `no-commit` після трьох спроб.
  Ще одна перевірка стежить, що в runner-і немає `BOARD_TASK_MAX_SEC`, `TASK_MAX`, `age_sec` і `deadline`.
  Колишні тести «13 год → паркується» і «11 год → працює» прибрано: вони перевіряли саме ту межу, якої вже немає.
- `tests/test_board.py` — PASS 345, FAIL 0: `park … deadline` відмовляє, стара задача із записом `deadline`
  читається й повертається в `todo/`. `tests/test_owner_terms.py` — PASS 66, FAIL 0.
- `grep -rn "TASK_MAX\|age_sec\|deadline" .claude/unattended/` — лише коментар у `board.py:1391`.
- Overseer: PASS (`20261023T175950Z-0fd8dd`).

## Витрати

Додаткових сесій Claude не запускав. Перша спроба overseer-а обірвалась на ліміті використання, і після
продовження його запущено вдруге. Окрім цієї сесії, витрат немає.

## Діапазон commit-ів

`e8f09f5..4746fab` (робота — один commit `4746fab`), далі commit перенесення задачі в `done/`.

## Відкладене

- Немає.

## Рішення, які я ухвалив сам

- **`started_utc` у `costs.json` лишився.** Без нього огляд не покаже, скільки задача в роботі
  (`board_review.py`), а `retry` і далі скидає його разом з лічильником спроб. Прибрано лише `age_sec`, бо його
  читала тільки перевірка за віком.
- **Сумісності для старого runner-а, який хтось змінив інакше, немає.** Якщо проєкт тримає власну версію
  runner-а, де перевірку за віком не закоментовано, новий `board_state.py` не відповість на `get age_sec`. Тоді
  умова в shell дасть помилку й буде хибною, тобто задачу за віком не запаркує. Саме цього задача й хоче, тому
  окремого шляху для старого `deadline` не лишав. Звіт `engine.py update` все одно назве такий файл у «Held back».
- **Документи історії не чіпав:** `docs/plan/package-board*.md`, `.engine/architecture/feature/engine-package-board.md`
  і звіти закритих задач описують, як було тоді.
