# 090 — Повний прохід simplifier-а після складнішого evaluation set: звіт

## Що змінилось для власника
- **Третій повний прохід simplifier-а по двигуну зроблено**: п'ять сесій агента (дві половини `.claude/hooks`, `.claude/unattended`, `engine.py` з `evals`, інструкції). **35 знахідок**: 3 `auto_remove`, 12 `confirm`, 20 `flag_only`. Validator не відхилив і не понизив жодної.
- **Застосовано лише три `auto_remove`** — кожна окремим commit-ом із трейлером `Simplifier-Finding`. Це мертві імена: константа `QUEUE_REL` у `lesson_queue.py`, функція `consents` і константа `ANOMALIES` у `board.py`.
- **Прибрано 9 рядків коду, додано 2** (два коментарі тепер називають `is_word` замість `consents`); чисте скорочення 7 рядків. Поведінка не змінилась.
- **Частка повернень: 0 із останніх 20 (0,0 %; коридор 5–20 %).** Лічильник і далі каже «прибирати сміливіше». Три нові видалення зроблено сьогодні, тож повертатися їм ще не було коли.
- **Від вас чекає питання 795 у `tasks/blocked/`**: які з 12 знахідок `confirm` застосувати. Серед них одна про документ цілей (N6 повторює заборону з P5) — вона лише ваша і лише через поправку до `goals.md`.
- **20 `flag_only` — для вашого огляду, без питання.** 18 із них — дублювання одного правила у двох і більше модулях (найбільше: чотири копії запуску сесії в eval runner-ах; `project_root` у семи hook-ах; `utc_now` у п'яти).
- **Скромний урожай — це чесний результат.** Після двох попередніх проходів (36 застосованих знахідок) простого мертвого коду майже не лишилось; те, що simplifier бачить тепер, — здебільшого дублювання, яке він за власним правилом подає не вище `flag_only`.
- **Постійний context: 181 рядок із 200.** Одна знахідка `confirm` (AGENTS.md:47) його стосується, але рядків не звільняє.

## Застосовано (auto_remove)
| Знахідка | Commit | Що прибрано | Який тест тримає поведінку |
|---|---|---|---|
| F-05f30e6e | `59b9add` | `.claude/hooks/lesson_queue.py`: `QUEUE_REL` — шлях черги відтоді, як задача 739 віддала його `journal.py`, ніхто не читає | `tests/test_lesson_queue.py`, `tests/test_journal.py` |
| F-09271eb4 | `6c39006` | `.claude/unattended/board.py`: `consents` — жодного виклику; правило «рівно одне слово „так“» живе в `Task.says` і `is_word` | `tests/test_board.py:803-812` |
| F-fcaa8bdd | `47f50aa` | `.claude/unattended/board.py`: `ANOMALIES` — ім'я файла журналу тримає `journal.JOURNALS` | `tests/test_board.py:383-391`, `tests/test_journal.py` |

Повернутих: **0**.

## Чекає вашого рішення — 12 `confirm` (питання 795)
| Знахідка | Де | Що можна прибрати |
|---|---|---|
| F-4ac917e4 | `.claude/hooks/test_touch.py:55` | параметр `layer` у `TestIndex`: зберігається і ніде не читається |
| F-0cfec5bf | `.claude/hooks/testing.py:482` | параметр `base` у `tree_overlay`: тіло завжди бере `HEAD` |
| F-77a3c83b | `.claude/hooks/testing.py:391` | параметр `feature` у `slug_of`: не вживається, тягнеться через п'ять викликів |
| F-4c4dba24 | `.claude/hooks/bugfix.py:80` | параметр `text` у `git`: жоден виклик його не задає |
| F-2850e235 | `.claude/hooks/overseer_stop.py:758-759` | дві умови перед безумовним `_passthrough()` (ще рядки 770-771): нічого не вирішують |
| F-7dc30102 | `AGENTS.md:47` | «This repository has none yet» про `.engine/goals.md` — уже неправда (версія 4, з печаткою), і це читає кожна сесія |
| F-f6211225 | `.claude/references/hooks.md:16` | речення про «former protocol», якого hook уже не має; суперечить тій самій клітинці |
| F-5cb3805b | `.claude/agents/overseer.md:63-65` | абзац про відсутній slice contract — старіше, м'якше правило, ніж правило режимів у тому ж файлі |
| F-cfa4cb0b | `.claude/commands/feature-architect.md:314-329` | списки «Hard constraints» наприкінці `/feature-architect`, `/plan-slice`, `/master-architect`: майже все повторює текст самої команди (кілька рядків там єдині — їх simplifier назвав, їх треба лишити) |
| F-59d166db | `.claude/commands/plan-slice.md:24-26` | визначення mode-файла в `/plan-slice` і `/feature-architect` дослівно повторює `engine-rules.md` |
| F-11a2726a | `.claude/skills/slice-builder/SKILL.md:58-72` | розділ «When to use this skill» повторює опис skill-а у frontmatter |
| F-93beed7c | `.engine/goals.md:27` | N6 повторює заборону з P5; **лише ваше рішення, лише поправкою до goals.md** |

Сім із дванадцяти я звірив із диском очима — збігаються: чотири параметри, подвійний `_passthrough`, AGENTS.md:47, hooks.md:16. Решту п'ять (усі про інструкції та документ цілей) рядок за рядком не звіряв: вони на судженні simplifier-а.

## Для огляду — 20 `flag_only`
Повний текст із доказами: `.engine/simplifier/report.md`, п'ять розділів «third pass».

| Знахідка | Де | Суть |
|---|---|---|
| F-6d2db84d | `evals/run_analyst_evals.py:222-239` | запуск однієї headless-сесії написано в чотирьох eval runner-ах; копії вже розійшлися (це ж місце править задача 725) |
| F-865f6087 | `evals/run_analyst_evals.py:284-295` | хвіст запису результатів — той самий блок у чотирьох runner-ах |
| F-8d999160 | `evals/run_analyst_evals.py:253` | прапорець `--owner-approved` у чотирьох runner-ах після задачі 078 нічого не робить; у двох підказка досі каже «the OWNER's word» |
| F-d14b19b6 | `evals/run_simplifier_evals.py:118-126` | `state_module()` — та сама функція, що в `run_audit_scenarios.py` |
| F-f25c8b29 | `engine.py:1462-1466` | правило «`--owner-approved` у сесії не діє» двічі: тут і в `run_audit_scenarios.py` (`engine.py` свідомо самодостатній) |
| F-af8f626a | `.claude/hooks/gate_allows.py:116-121` | розбір hunk-ів diff-у написано тричі (`gate.py`, `gate_allows.py`, `testing.py`) |
| F-5048fe40 | `.claude/hooks/gate_allows.py:124-139` | пошук suppression-ів по рядках — двічі (`gate.guard_python` і тут) |
| F-18d1b3cb | `.claude/hooks/baseline.py:67` | `utc_now()` визначено однаково в п'яти модулях |
| F-41bccc40 | `.claude/hooks/complexity_budget.py:712-717` | друга копія `project_root` поруч із `gate.project_root` |
| F-baa9f51b | `.claude/hooks/delete_guard.py:119` | розбір `CODE_EXTENSIONS` у трьох місцях |
| F-65c10103 | `.claude/hooks/baseline.py:55` | таблиця `STEP_PART` = `gate.SNAPSHOT_PART` |
| F-9190c95c | `.claude/hooks/simplifier.py:275-276` | «файли, які зачепила зміна» рахуються двічі тими самими двома рядками |
| F-d7080136 | `.claude/hooks/delete_guard.py:65` | граматика цілі знахідки у двох регулярних виразах |
| F-a901cc04 | `.claude/hooks/goals.py:253-258` | правило кореня проєкту виписано в семи hook-ах |
| F-9a1f2d43 | `.claude/hooks/shell_readonly.py:142-156` | правило «ця команда пише у свій аргумент» повторює `shell_paths.by_command` (захищений шлях) |
| F-7590cb9e | `.claude/unattended/board.py:213` | `OWNER_ACTIONS` — другий перелік дозволених дій, якого код не читає і який уже розійшовся зі справжнім (`owner_action.ACTIONS`) |
| F-ffc05097 | `.claude/unattended/board.py:592-593` | «найменший вільний номер» і пошук уже написаного питання — тричі в одному модулі |
| F-8f254854 | `.claude/unattended/board_review.py:679-698` | правило «яку задачу бере runner» утретє (ще `Board.eligible` і `summary`) |
| F-a68cc94a | `.claude/references/permission-philosophy.md:23` | два місця описують ask-правило для надсилання гілки в origin, якого після задачі 603 немає |
| F-1b463977 | `.claude/skills/overseer/SKILL.md:89-98` | розділ про проєкт без handler-ів повторює те, що hook сам друкує |

## Рядки і числа
| Що | Значення |
|---|---|
| Знахідок | 35 (5 + 12 + 4 + 5 + 9 за п'ятьма сесіями) |
| Відхилено / понижено validator-ом | 0 / 0 |
| Застосовано | 3 (усі `auto_remove`) |
| Код: прибрано / додано / чисто | 9 / 2 / −7 (`git diff --numstat e25c8d7 47f50aa`) |
| Інструкції | без змін |
| Частка повернень | 0 із останніх 20 (0,0 %) |
| Постійний context | 181 із 200 рядків, без змін |

## Демонстрація на хвилину
```bash
git log --format='%h %s' e25c8d7..47f50aa --grep='Simplifier-Finding'      # три commit-и
python3 .claude/hooks/simplifier.py reversals                               # 0 of the last 20 …
python3 .claude/hooks/simplifier.py validate .engine/simplifier/third-pass/answer-hooks-gates.json \
  --request .engine/simplifier/third-pass/request-hooks-gates.txt           # 12 valid, 0 rejected, 0 lowered
```

## Перевірки
- `bash tests/run_all.sh` — тричі, перед кожним commit-ом видалення, з цим видаленням у дереві: **91 із 91 suites green** щоразу.
- Golden set: `evals/run_hook_scenarios.py` на `e25c8d7` і на `47f50aa`, `evals/compare.py` — **identical behaviour in all 281 scenarios**; усі 281 зелені. Чесна межа (її назвав overseer): golden set перевіряє hook-и, а два з трьох видалень — у `board.py`; їх тримають `tests/test_board.py` і `tests/test_board_runner.py`, не golden set.
- Проти закоміченого baseline `results-task-738-086.json` HEAD відрізнявся ще до моїх змін — у 9 сценаріях про надсилання гілки (задача 603). Це не від цієї задачі; baseline я не оновлював.
- Delete guard: видалення `consents` пропущено (`delete/passed`: модуль має `tests/test_board.py`).
- overseer: **PASS**, запит `20261011T105705Z-fa7976` — сам повторив повний набір (91/91), golden set (281 тотожні) і validate п'яти відповідей.
- Залишковий ризик, який назвав overseer: `board.py` і `lesson_queue.py` встановлюються в інші проєкти; якщо чийсь власний скрипт імпортував `board.consents` чи `lesson_queue.QUEUE_REL`, цей репозиторій того не бачить. Жодне з імен ніде не описане як інтерфейс; повернути — один рядок.

## Витрати
- П'ять сесій simplifier-а (fable): близько 910 тис. токенів, приблизно **$17–18** за лічильником розмови; окремого рахунку на агента немає, це оцінка.
- Audit overseer-а: близько 62 тис. токенів, приблизно $1,5.
- Сесію агента, що виконувала задачу, рахує runner.

## Діапазон commit-ів
`e25c8d7..` цей commit: `2118514` (записи проходу), `59b9add`, `6c39006`, `47f50aa` (три видалення), `e95c90f` (питання 795), закриття задачі.

## Відкладене
- **Питання 795** (`tasks/blocked/`) — 12 знахідок `confirm`.
- **20 `flag_only`** — у `.engine/simplifier/report.md`; задач на них не клав: чи варте кожне дублювання об'єднання — ваше рішення, а F-6d2db84d перетинається з уже відкритою задачею 725.
- **Черга уроків: 36 кандидатів** (32 додав цей прохід — по одному на знахідку); hook нагадує про clean-up пам'яті. Не розбирав: кандидати цього проходу закриються разом із вашими рішеннями щодо знахідок.
- Baseline golden set не оновлював (див. «Перевірки»).
- **Хибна тривога hook-а `park-ask-gated.py`**: він відмовив команді, яка лише записувала цей звіт, бо в тексті звіту стояли слова команди надсилання гілки. Нічого не надсилалось; звіт записано іншим інструментом. Запис — у журналі аномалій.

## Рішення, які я ухвалив сам
- **П'ять сесій, не чотири.** `.claude/hooks` — близько 12 тис. рядків; поділив на дві половини (gates і решта), щоб кожна сесія прочитала своє уважно. Обсяг той самий, що й у другому проході, плюс `.claude/references` і `.engine/goals.md` в інструкціях.
- **Сесії запущено одним реченням, що вказує на файл запиту**, а не вставленим текстом запиту (до 12 КБ кожен). Агент прочитав той самий текст; відповіді проходять validate проти збережених запитів.
- **Тести не входили в scope** — як і в перших двох проходах.
- **Повний набір тестів — перед кожним із трьох видалень**, не раз наприкінці: так вимагає правило `auto_remove` (`.claude/references/simplifier.md`), і воно суворіше за загальне «повний набір один раз».
- **Жодної `confirm` не застосовано**, хоч кілька очевидні (AGENTS.md:47): задача дозволяє лише `auto_remove`.
- **Одне питання на всі 12 `confirm`**, а не дванадцять задач — як у задачі 024.
