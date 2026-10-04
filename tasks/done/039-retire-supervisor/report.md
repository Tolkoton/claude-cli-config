# 039 — Прибрати supervisor.sh: автономна робота лише через дошку: звіт

## Що змінилось для власника
- **Автономна робота тепер має один спосіб — дошку і `board-runner.sh`.** `supervisor.sh`, що вів роботу за графом фічі, прибрано разом з усім, чим користувався лише він.
- **Граф фічі не зачеплено.** `.engine/architecture/feature-dag.json` лишився тим, чим його робить `/feature-architect`: планом фічі. Сам по собі його більше ніщо не виконує.
- **Прибрано 2246 рядків, додано 186** (commit-и `3dbdfa2` і `c582054`, 33 файли; файл нового еталона, ще 1466 рядків, тут не рахую). Перелік — нижче.
- **У встановлених проєктах `engine.py update` сам прибере ці файли.** Файл, який проєкт правив, лишиться на місці, і звіт оновлення про це скаже. Файли проєкту і стан старих запусків (`.claude/state/unattended/`) не чіпаються. Перевірено на справжньому встановленні версії v0.11.0.
- **Разом із supervisor-ом пішла одна поведінка hook-а кінця ходу:** «не давати сесії закінчити хід, поки автономний прогін живий» (до 25 разів). Вона існувала лише для сесії, що керувала supervisor-ом; сесії виконавця дошки вона ніколи не стосувалась. Це зміна hook-а `overseer_stop.py` — див. «Рішення, які я ухвалив сам», п. 1.
- **Новий еталон золотого набору: `results-task-039.json`, 135 сценаріїв** (було 138: три сценарії тієї самої поведінки прибрано). Решта 135 тотожні еталону `results-task-033.json`.
- **Тести зелені: 59 із 59 наборів** (було 62: чотири набори пішли разом із supervisor-ом, один новий). Повний прогін — на `3dbdfa2`; після нього змінився лише коментар у карті власності, і набори, що її читають, перезапущено окремо. Золотий набір — на `c582054`: 135 із 135. Платних прогонів не було.
- **Від вас нічого не потрібно.** Якщо десь ще працює старий supervisor — зупиніть його перед `engine.py update` (оновлення саме про це скаже, якщо побачить його замок або свіжий heartbeat).

## Що прибрано
| Що | Рядків |
|---|---|
| `.claude/unattended/supervisor.sh` — сам цикл | 357 |
| `.claude/unattended/runstate.py` — стан прогону, витрати, вибір вузла графа | 277 |
| `.claude/unattended/session-claude.sh`, `session-sim.sh` — запуск сесії на вузол і його імітація | 99 + 82 |
| `.claude/unattended/config.sh` — налаштування supervisor-а | 82 |
| `.claude/unattended/watch.sh` — спостерігач за supervisor-ом | 89 |
| `.claude/unattended/rotate.sh` — ротація його журналів | 75 |
| `.claude/unattended/recheck_parked.py` — повторна перевірка відкладеного перед кожним запуском сесії | 143 |
| `.claude/unattended/claude-unattended.service` — unit для systemd | 47 |
| у `overseer_stop.py` — «продовжуй, поки прогін живий» | 102 |
| три сценарії золотого набору (`osf-unattended-with-live-work-continues`, `osf-unattended-run-finished`, `osf-spawned-session-may-end`) | 156 |
| тести: `test_selfref.py`, `test_session_launch.py`, `test_recheck_parked.py`, `test_overseer_continue.py` | 70 + 99 + 86 + 50 |
| документація: розділи про supervisor у `.claude/unattended/README.md`, договір сесії в `.claude/references/unattended.md`, рішення D-1…D-20 в `unattended-decisions.md` | близько 400 |

Лишилося, бо цим користується дошка або hook-и: `board-runner.sh`, `board.py`, `board_state.py`, `board_review.py`, `owner_action.py`, `settings_check.py`, `commit_checkpoint.sh`, `env-probe.sh`.

## Що зроблено по пунктах
1. **Прибрано все, що було лише для supervisor-а** — таблиця вище.
2. **Граф фічі** не чіпав: ні файл, ні `/feature-architect`.
3. **Карта власності.** Окремої позначки «вилучено» в карті немає і не потрібно: файл, який двигун колись постачав і більше не постачає, лишається «файлом двигуна» за загальним правилом `.claude/**`, і `engine.py update` прибирає його сам. У карту дописано коментар, який це пояснює і називає прибране. Рядки про старий стан supervisor-а (`state.json`, `supervisor.lock` …) лишено: це стан машини в давно встановлених проєктах, його не можна ні комітити, ні видаляти.
4. **Документація.** `AGENTS.md`, `.claude/engine-rules.md`, `.claude/references/unattended.md`, `.claude/references/hooks.md`, `.claude/unattended/README.md`, `docs/engine-limits.md`, `docs/TEMPLATE-SETUP.md`, `evals/README.md`: автономна робота — це дошка і `board-runner.sh`.
5. **Еталон** `evals/baseline/linux-ubuntu-22.04/results-task-039.json`; команди в `AGENTS.md` і `evals/README.md` вказують на нього.

## Демонстрація на хвилину
Проєкт, встановлений зі справжньої v0.11.0 (із supervisor-ом), у якому проєкт дописав рядок у `config.sh`; оновлення до цієї версії:

```text
$ engine.py update shop --ref HEAD
  add     .claude/unattended/board-runner.sh
  add     .claude/unattended/board.py
  …
  remove  .claude/unattended/claude-unattended.service  — retired by the engine
  keep    .claude/unattended/config.sh  — retired by the engine but edited in the project; left in place
  remove  .claude/unattended/recheck_parked.py  — retired by the engine
  remove  .claude/unattended/rotate.sh  — retired by the engine
  remove  .claude/unattended/runstate.py  — retired by the engine
  remove  .claude/unattended/session-claude.sh  — retired by the engine
  remove  .claude/unattended/session-sim.sh  — retired by the engine
  remove  .claude/unattended/supervisor.sh  — retired by the engine
  remove  .claude/unattended/watch.sh  — retired by the engine
```

Код виходу тут 1 — так оновлення каже «є рядок, на який має глянути людина» (залишений `config.sh`).

Золотий набір проти старого еталона: три відмінності — рівно три прибрані сценарії; проти нового: `identical behaviour in all 135 scenarios`, `PASS 135/135`.

Новий тест `tests/test_supervisor_retired.py` (26 перевірок) тримає три речі: прибраних файлів немає, а файли дошки на місці; жоден робочий файл не називає прибраних скриптів (закриті записи — `tasks/`, `.engine/`, `docs/plan/`, старі еталони — історія, їх не переписував); оновлення справжнього старого встановлення поводиться, як у демонстрації. Друга перевірка була червона на моєму ж рядку в `tests/fast-suites.txt`, поки я його не виправив.

## Витрати
- Одна сесія агента, за її лічильником близько $3.2; точну суму записує виконавець у `.claude/state/board/costs.json`.
- Платних прогонів не було. Повний набір тестів запущено один раз (59 із 59; тривав близько двадцяти хвилин, з них понад десять — `test_board_runner.py`).

## Діапазон commit-ів
`735192b` (задача в `doing/`) … commit із цим звітом. Робочі: `3dbdfa2` (прибирання) і `c582054` (еталон, коментар у карті).

## Відкладене
- **Про «жодних посилань» чесно.** Назви `supervisor.sh` у робочих файлах більше немає. Слово «supervisor» лишилося в трьох місцях, і всі три — про старі встановлення: `engine.py` (не переносити стан, якщо в проєкті ще працює старий supervisor) з його тестом `test_state_migration.py`; рядки старого стану в карті власності та `.gitignore`; пояснення «це прибрано» в документації.
- **`tasks/CANDIDATES.md`, рядок C10** («вирішити долю supervisor.sh») — вирішено цією задачею. Сам дайджест не правив: це знімок задачі 022.
- **У `tasks/doing/` лежить чужий файл `report-028-close-stale-items.md`** — не моєї задачі, не чіпав.
- **Задача 037** згадує відкладене в `parked.md`: автоматичного повернення відкладених пунктів (`recheck_parked.py`) більше немає — див. рішення 3.

## Рішення, які я ухвалив сам
1. **Прибрав із hook-а `overseer_stop.py` поведінку «продовжуй, поки прогін живий».** Вона спрацьовувала лише коли режим `unattended`, сесію запустив не виконавець, і або supervisor писав «працюю», або в графі фічі був готовий вузол. Без supervisor-а перша умова мертва, а друга означала б, що hook до 25 разів не дає закінчити хід людині, яка відкрила сесію, поки працює виконавець дошки (він ставить режим `unattended` для всього репозиторію), — тобто виконував би граф «старим способом». Задача прямо називає «сценарії золотого набору» серед того, що прибрати, а це саме вони. Аудит юнітів, три BLOCK, запечатаний контракт, маркери зупинки — без змін (решта 135 сценаріїв тотожні). Повернути: `git revert` робочого commit-а.
2. **У hook-у периметра `block-dangerous.sh` змінив один рядок коментаря** («unattended (supervisor run)» → «unattended (the board runner)»). Коду не торкався; усі сценарії цього hook-а в золотому наборі тотожні. Кажу окремо, бо це файл захисту.
3. **`recheck_parked.py` прибрав.** Його запускав лише supervisor перед кожною сесією; дошка його не викликає, а одна з його умов (`node:ID`) читала граф фічі. Задача 028 запускала його руками як лічильник — для цього досить прочитати `parked.md`, а задача 037 і так переносить усе відкрите на дошку. З `.claude/references/unattended.md` прибрано згадку про позначки `env:` / `file:` / `node:` у рядку `Unblocks when:`.
4. **`unattended-decisions.md` не видалив, а скоротив.** Рішення D-1…D-20 — це будова supervisor-а, вони пішли (є в історії git). D-21…D-27 лишив: вони пояснюють живі механізми (hook заборон, політика commit-ів, перевірка латок, `settings.local.json`).
5. **Захист у `engine.py` «supervisor ще працює — стан не переношу» лишив.** Він потрібен саме тепер: проєкт зі старою версією може оновлюватися з живим supervisor-ом. Змінив лише коментарі.
6. **Історичні записи не переписував:** `tasks/done/`, `.engine/` (журнали, архів графів, знахідки спрощувача), `docs/plan/`, старі еталони.
