# 019 — М'яка зупинка виконавця: звіт

## Що змінилось для власника
- **Виконавця тепер можна зупинити, нічого не втративши:** `bash .claude/unattended/board-runner.sh --stop-after-task`. Команда ставить прапорець `.claude/state/board/stop-after-task` і одразу повертається.
- **Виконавець дивиться на прапорець між задачами.** Поточну задачу агент доводить до кінця (`done/` або `blocked/`), виконавець її надсилає, наступну не починає, зупиняється зі станом `stopped` (причина `stop-after-task`, код виходу 0) і сам прибирає прапорець.
- **Якщо виконавець не працює,** команда нічого не ставить, каже про це й виходить із кодом 1. Прапорець, що лишився від виконавця, який помер, новий виконавець прибирає на старті й працює як звичайно.
- **В інструкції для оператора** (`tasks/README.md`, розділ «Виконавець», і шаблон для нових проєктів) написано: зупиняти лише так, процес не вбивати.
- **Увага: виконавець, який працює зараз (pid 1124686, запущений о 18:46 UTC), цієї команди ще не знає** — він запущений зі старим кодом і прапорця не перевіряє. Команда почне діяти після його наступного запуску. Цього разу дочекайтеся, поки він зупиниться сам.

## Демонстрація на хвилину
`python3 tests/test_board_runner.py` (близько трьох хвилин; останній розділ — «the soft stop»). Там справжній `board-runner.sh` працює в тимчасовому репозиторії з підробленим `claude`, який посеред першої задачі сам викликає `--stop-after-task`:

```text
the soft stop: --stop-after-task
  ok   the command, given while a task is running, exits 0 and says the runner will stop
  ok   the current task is finished, the next one is not started
  ok   state=stopped, the task named, reason=stop-after-task
  ok   the flag is removed
  ok   the finished task was pushed, the lock released, the stop is in the events and the summary
  ok   the next start is an ordinary one: the second task is done
  ok   the flag file alone is enough, and a task still open is continued to its end: three calls, then stopped
  ok   the work of the task is all committed: nothing is lost
  ok   a task that ends in blocked/ is a finished task too: stopped, the next one not started
  ok   the negative case: no flag — both tasks are done, state=idle
  ok   no runner is working: the command refuses (exit 1), says so, and leaves no flag
  ok   …the same with the lock of a runner that died
  ok   a flag left over from a runner that died does not stop the new one: removed at the start, the task is done
```

До зміни ці перевірки падали: команда була невідомою опцією, а виконавець після першої задачі брав другу.

## Перевірки
- **Повний набір, один раз наприкінці:** `bash tests/run_all.sh` — 59 наборів, усі зелені; `tests/test_board_runner.py` — 165 перевірок (було 149), з них 16 нових.
- Золотий набір hook-ів не запускав: жодного hook-а не змінено.
- Перевірок стилю в проєкті не налаштовано (`LINT_CMD` порожній); `bash -n` для скрипта чистий.
- Платних прогонів не було (`Аудит потрібен: ні`).
- На живому виконавці не перевіряв: це означало б зупинити той, що зараз веде цю розмову.

## Витрати
- Ця розмова: близько $1,2 на момент написання звіту. Точну цифру покаже `board.py summary` після завершення.

## Діапазон commit-ів
- `e288be3` (задачу взято в роботу) … `8c899ea` (уся робота) і commit, яким задачу перенесено в `done/`.

## Відкладене
- **Зупинка посеред задачі.** Прапорець діє лише між задачами — так сказано в задачі. Якщо задача триває години, стільки ж чекатиме й зупинка; способу «зупинись після поточної спроби» немає.
- **`supervisor.sh`** (другий спосіб роботи, від DAG) такої команди не має — задача була про виконавця дошки.

## Рішення, які я ухвалив сам
- **Без живого виконавця команда прапорця не ставить** (код 1). Інакше прапорець лежав би до наступного запуску і зупинив би його після першої ж задачі, коли про прохання вже забули.
- **Прапорець, що був до старту, новий виконавець прибирає** (подія `stop-flag-stale`): хто запускає виконавця, хоче, щоб він працював.
- **Будь-яка зупинка прибирає прапорець** — і тоді, коли виконавець зупинився з іншої причини (`stalled`, `deadline`, порожня `todo/`): прохання вже виконано.
- **Задача, що пішла в `blocked/`, теж закінчена задача:** виконавець зупиняється після неї так само, як після `done/`.
- **Прапорець можна поставити й руками** (`touch`), команда лише перевіряє, що є кому його прочитати, і пише подію `stop-requested`.
- **Той самий абзац додано в шаблон** `templates/project/tasks/README.md` і в `.claude/unattended/README.md`, щоб нові проєкти отримали інструкцію разом із командою.
