# 008 — Лічильник «застряг»: підключення через пропозицію налаштувань. Звіт (чернетка)

Задача чекає вашої відповіді в `tasks/blocked/008-stuck-counter-wiring.md`. Це звіт про зроблене
до запитання; після застосування агент допише результат і перенесе його в `done/` як `report.md`.

## Що змінилось для власника
- Обидва hook-и лічильника «застряг» тепер у пропозиції `docs/tasks/settings.json`:
  `lesson_queue.py stuck` на `PostToolUse` і на `PostToolUseFailure`, для Bash, з лімітом 5 с.
- Налаштування застосовуються одним шляхом:
  `cp docs/tasks/settings.json .claude/settings.json && python3 tests/test_settings_proposal.py`.
  Скрипт `apply-lesson-hooks.py`, його фрагмент `lesson-hooks.json` і їхній тест прибрано.
- `tests/test_settings_proposal.py` зелений і до застосування, і після. Два нові hook-и записано
  в ньому як задуману відмінність із причиною (ваше рішення від 2026-10-03, пакет пам'яті).
  Будь-який інший зайвий чи зниклий hook тест не пропускає.
- Живий `.claude/settings.json` я не змінював. Лічильник на результатах Bash запрацює лише після
  застосування і перезапуску Claude Code.
- Нове на дошці: якщо під питанням агента стоїть рядок `Дія виконавця: …`, ваша відповідь `так`
  означає «виконати». Виконує виконавець `board-runner.sh`, не агент. Дозволених дій дві, і
  перелік зашито в код: застосувати пропозицію налаштувань, закрити ескалацію воріт.
- Виконавець застосує саме той файл, про який вас питали: у рядку дії стоїть його sha256. Якщо
  пропозицію після запитання змінили — не застосує і поверне задачу агентові.
- Якщо тест після копіювання червоний, виконавець повертає попередній файл.
- Відповідь `так`, вписану просто на сервері, виконавець стирає і питає знову — так само, як із
  `закрити` для воріт. Усередині сесії агента дія не виконується взагалі.
- **Після відповіді запустіть виконавця заново.** Той, що працює зараз, стартував до цієї зміни:
  він лишить задачу в `blocked/` і дії не виконає.
- Після дії задача повертається агентові: він перевіряє результат і пише остаточний звіт.

## Демонстрація на хвилину
Тест пропозиції зараз, до застосування (`python3 tests/test_settings_proposal.py`, скорочено):

```text
  ok   proposal: the only hooks added against the live file are the two stuck-counter handlers, and the only removal is approve-project-data on PermissionRequest
  ok   proposal: the stuck counter is wired once on PostToolUse and once on PostToolUseFailure, for Bash, with a timeout
  ok   the old second way to apply is gone: no merge script, no fragment
  ok   effective settings: 6 identical, 7 intended difference(s)
  ok   effective hooks: the frozen handlers plus exactly the two stuck-counter handlers
  info not applied yet: the live .claude/settings.json still differs from the proposal
PASS 17   FAIL 0
```

Шлях відповіді `так` на синтетичному репозиторії зі справжнім виконавцем і підставним `claude`
(`python3 tests/test_board_runner.py`, розділ board 008):

```text
board 008, the demonstration: the question with an offer → the owner's «так» → the runner applies
  ok   unanswered: nothing is applied, no agent starts, the runner waits for the owner
  ok   the owner answered «так»: the live file is the proposal
  ok   …applied by the runner, before any agent was started
  ok   …committed by itself: the settings file and nothing else
  ok   …the offer is replaced by the outcome; the answer stays
  ok   …then the task went back to todo/ and the agent closed it with a report
  ok   …everything pushed, the tree clean, idle
  ok   a second run applies nothing again
```

Спроба виконати дію з сесії агента (справжній вивід, у цьому репозиторії):

```text
$ python3 .claude/unattended/owner_action.py apply-settings x
owner-action: the owner's actions are refused inside a Claude Code session (CLAUDECODE is set). The board runner takes them, started from the owner's terminal or service.
[exit 2]
```

## Перевірки
- Повний набір, один раз наприкінці: `bash tests/run_all.sh` — 51 набір зелений (було 52: набір
  `test_lesson_hooks_proposal` прибрано разом зі скриптом, його перевірки hook-ів перейшли в
  `test_settings_proposal`).
- Золотий набір проти `evals/baseline/linux-ubuntu-22.04/results-package-costs.json`: однакова
  поведінка в усіх 114 сценаріях.
- ruff і `mypy --strict` на змінених Python-файлах — чисто.
- Тест пропозиції бачив червоним: одразу після додавання hook-ів у пропозицію (до правки тесту) і
  з третім, стороннім hook-ом у пропозиції (2 падіння). Із живим файлом, рівним пропозиції, —
  зелений, пише `APPLIED`.
- Нові тести дошки бачив червоними з навмисно зламаним кодом: без перевірки, звідки прийшла
  відповідь, — 4 падіння; коли `unblock` віддавав задачу з `так` агентові — 1 падіння.
- Не перевірено наживо: справжній виконавець на цій задачі. Це станеться з вашою відповіддю.

## Витрати
Платних прогонів не було. Вартість сесії записує виконавець у `.claude/state/board/costs.json`.

## Діапазон commit-ів
`2c0a931` (робота) і наступний commit — перенесення задачі в `blocked/` з питанням.

## Відкладене
- Остаточний `report.md` і перенесення в `done/` — після застосування.
- У проєкті, куди двигун встановлено, дія `apply-settings` спрацює лише там, де є свої
  `docs/tasks/settings.json` і `tests/test_settings_proposal.py`; інакше виконавець відмовить і
  поверне задачу агентові. Постачати цей механізм пропозицій у проєкти — окреме рішення.

## Рішення, які я ухвалив сам
- Прибрав не лише `apply-lesson-hooks.py`, а й `lesson-hooks.json` та `test_lesson_hooks_proposal.py`:
  другий примірник тих самих hook-ів розійшовся б із пропозицією.
- Рядок дії містить sha256 пропозиції. Задача цього не вимагала; без цього `так` схвалювало б
  будь-який файл, що лежатиме там у момент запуску.
- Після дії задача повертається агентові, а не йде одразу в `done/`: звіт пише агент, і він же
  перевіряє результат. Ціна — одна коротка сесія.
- Виконавець сам комітить застосований `.claude/settings.json` окремим commit-ом. Досі він
  комітив лише `tasks/`.
- Закриття ескалації воріт лишив як було (його пропонує саме питання воріт); у спільному переліку
  дозволених дій воно другим рядком.
- Правило для агента (№ 9) і розділ для власника дописав у `tasks/README.md` і в його зразок для
  нових проєктів.
- Запис `B-wiring-stuck-bash` у `parked.md` і вузол B5 у `feature-dag.json` виправив на нову
  команду; запис лишається відкритим до застосування.
- Чернетку звіту поклав поруч із задачею в `blocked/` під іменем, яке дошка не вважає задачею.
- Попутно перейменував одну змінну в `tests/test_board_runner.py`: вона затіняла функцію, і
  `mypy --strict` на цьому файлі падав ще до моїх змін.
