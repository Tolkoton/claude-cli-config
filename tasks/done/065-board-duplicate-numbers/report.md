# 065 — Дві задачі з одним номером на task board: звіт

## Що змінилось для власника
- **Відповідь через inbox більше не може стерти чуже питання.** Коли в колонці лежать кілька файлів з одним
  номером, файл з inbox стосується лише того, що має точно таку саму назву, і замінює тільки його. Якщо
  такої назви немає — нічого не видаляється, файл лишається в inbox, а в `tasks/ANOMALIES.md` з'являється
  запис (один раз, а не при кожному проході runner-а). Це діє і для `blocked/`, і для `todo/`.
- **Під час rebase чи merge gates не створюють файлів на task board.** Якщо Stop gate здається, поки в
  репозиторії є `rebase-merge`, `rebase-apply` або `MERGE_HEAD`, escalation записується як завжди (overseer
  так само не приймає роботу з цими файлами), але на task board — лише запис у журналі аномалій. Питання
  «Закрити ескалацію?» з'являється в `blocked/`, щойно rebase чи merge завершився: його ставить перший
  наступний прогін Stop gate або runner перед наступною задачею (`gate.py --ask-waiting`).
- **Два файли з одним номером в одній колонці — помилка, яку видно.** Рядок «ПОМИЛКА: один номер 900 у двох
  файлах у blocked/: …» показують `board.py summary`, огляд (`board.py review`, розділ «Стан зараз») і нова
  команда `board.py check` (код виходу 1, якщо помилка є). На нинішній task board таких немає: `check` — 0.
- Описано в `tasks/README.md` (і в шаблоні проєкту) та `.claude/references/gate.md`.

## Демонстрація на хвилину
Пункти 1 і 3 — на синтетичній task board з двома файлами номер 900 (як 2026-10-07):
```text
$ board.py check
ПОМИЛКА: один номер 900 у двох файлах у blocked/: 900-gate-escalation-20261006T212543Z.md, 900-gate-escalation-20261007T074013Z.md — перенумеруйте всі, крім одного: відповідь через inbox і залежності знаходять задачу за номером
exit=1
$ board.py import-inbox      # в inbox лежить 900-answer.md з відповіддю «так»
900-answer.md skipped: 900 is the number of several files in one column and none has this name
  (обидва файли в blocked/ на місці, 900-answer.md лишився в inbox)
  tasks/ANOMALIES.md:
  - Що сталося: файл `900-answer.md` з inbox має номер, який у `blocked/` носять кілька файлів (…), і жоден з них не має такої самої назви
  - Що зроблено: нічого не видалено й не замінено; файл лишився в inbox. …
  - Хто записав: task board (import-inbox)
$ board.py import-inbox      # той самий файл під точною назвою 900-gate-escalation-20261006T212543Z.md
900-gate-escalation-20261006T212543Z.md answered: tasks/blocked/900-gate-escalation-20261006T212543Z.md
  900-gate-escalation-20261006T212543Z.md:   Відповідь: так
  900-gate-escalation-20261007T074013Z.md:   Відповідь:          ← друге питання ціле
```
Пункт 2 — справжній `gate.py` на синтетичному репозиторії (`python3 tests/test_gate_allows.py`, останній розділ):
```text
ok   rebase-merge: the escalation is open, and no file is written to tasks/blocked/
ok   rebase-merge: the escalation is in the anomaly journal, which says why the owner is not asked yet
ok   rebase-merge: nothing goes to the log parked.md, and the session is told the question comes later
ok   rebase-merge: a later turn that is still inside the rebase asks nothing either
ok   rebase-merge gone: the question is asked — one file, the escalation's own stamp, the file and the count the gate blocked on
ok   rebase-merge gone: asked once
ok   the case of 2026-10-07 — a second escalation during a rebase that hid the first question: two questions, two numbers
ok   negative — no board in the project: a rebase changes nothing, the escalation is parked in the log as before
```
Те саме перевірено для `rebase-apply` і `MERGE_HEAD`. Останній рядок перед зміною падав: відтворював саме
випадок 2026-10-07 — два файли з номером 900. Окремо, руками в терміналі, пункт 2 я не показав: вбудована
перевірка безпеки сесії відмовила в команді, що прибирає теку-позначку rebase, і я її не обходив.

## Перевірка
- Нові перевірки спершу впали з правильної причини (стара поведінка: друге питання стерто; файл у `blocked/`
  під час rebase; жодного рядка «ПОМИЛКА»), потім позеленіли.
- Повний набір наприкінці задачі, `bash tests/run_all.sh`: **80 suite-ів із 81 зелені, 1 червоний** —
  `test_engine_lint` (mypy: бракувало анотації типу в одному рядку `gate.py`). Після цього я виправив анотацію
  і ще одну нестабільну нову перевірку (дві escalation-и в межах однієї секунди отримують один stamp — у тест
  додано паузу) і перезапустив лише зачеплені suite-и: `test_engine_lint`, `test_gate`, `test_gate_allows`
  (чотири рази поспіль), `test_board`, `test_board_review`, `test_board_runner` — зелені. Повний набір удруге
  не запускав (він іде близько 40 хвилин; правило — раз наприкінці задачі).

## Витрати
Платних прогонів не було. Сесія агента — близько $3.

## Commit-и
Один commit, що закриває цю задачу (після `29e0988`): `gate.py`, `board.py`, `board_review.py`,
`board-runner.sh`, чотири файли тестів, три документи, звіт.

## Відкладене
- **Stamp escalation-ї має точність до секунди.** Дві escalation-и в одну секунду — це один stamp і одне
  питання. Так було й раніше; у житті між ними щонайменше один хід агента, тому я цього не чіпав.
- **Інші способи сховати файли task board від робочого дерева** (`git stash -u`, checkout іншої гілки) цією
  зміною не покриті: позначок rebase чи merge тоді немає. Наслідок тепер видно (`board.py check`, огляд) і
  він не руйнівний (inbox нічого не стирає), але сам дублікат так з'явитися ще може.
- Runner не зупиняється на рядку «ПОМИЛКА» — він лише показує його в підсумку. Перенумерувати файл і досі
  має людина.

## Рішення, які я ухвалив сам
- Додав окрему команду `board.py check` з кодом виходу, а не лише рядок у `summary` й огляді: її можна
  викликати зі скрипта.
- Дублікати перевіряються в усіх чотирьох колонках, `done/` теж.
- Правило «лише точна назва» діє і для `todo/`, не тільки для `blocked/`.
- Запис у журнал аномалій про файл, що лишився в inbox, робиться один раз: runner проходить inbox перед
  кожною задачею, і без цього журнал заповнювався б однаковими записами.
- Під час rebase чи merge escalation не пишеться і в `.engine/overseer/parked.md` — у задачі сказано «лише в
  anomaly log». У проєкті без task board нічого не змінилося: там запис у `parked.md`, як раніше.
- Відкладене питання ставлять і Stop gate (на початку кожного прогону), і runner: сесія, у якій стався
  rebase, може закінчитися раніше, ніж він завершиться.
