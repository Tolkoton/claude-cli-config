# 786 — Stop gate блокує щойно встановлений двигун до першого commit-а — звіт

## Що змінилось для власника
- **Свіже встановлення більше не блокує Stop gate.** Після `engine.py install` і до першого commit-а gate не судить
  файл, якого немає в HEAD і який байт у байт збігається з записаним у `.claude/engine-lock.json`. Smoke-перевірка з
  кроку 6 `docs/TEMPLATE-SETUP.md` на такому проєкті мовчить (exit 0); кандидат в уроки про hook-и двигуна в перший
  commit не потрапляє.
- **Обрано перший варіант із задачі** (gate не судить незмінені файли двигуна й seed-файли), не лише текст у документі.
- **`.claude/project.env`, налаштований до commit-а (крок 2), теж проходить**, якщо ви задали `SOURCE_DIRS` чи команди
  перевірок: gate порівнює файл із його seed-ом, а не з порожнечею. Раніше будь-яка правка давала «the diff changes
  CODE_EXTENSIONS».
- **Що блокує й далі, доки ви не закомітите** (gate не відрізняє це від роботи сесії): зміна `CODE_EXTENSIONS`,
  `PROJECT_MARKER`, `DELETE_GUARD_LINES`, `PUSH_PROTECTED_BRANCHES`; змінений `.claude/ruff.toml`; `noqa` у файлі
  двигуна; а при запуску gate руками — змінені `.claude/settings.json`, constitution чи `.engine/rules.md`. Це
  написано в `docs/TEMPLATE-SETUP.md` (крок 1, «After the command»): commit після встановлення і ще один після
  кроків 2–5, перед smoke-перевіркою.
- **У lock з'явився ключ `seeds`** (blob кожного seed-файлу); старий lock без нього читається як порожній. Текст
  seed-ів `engine.py` кладе в `.claude/state/install/seeds/` (machine state, у git не потрапляє).
- **Те саме після `engine.py update` без commit-а не виправлено** — це пропозиція 1750 (нижче).

## Демонстрація на хвилину
```
python3 tests/test_fresh_install_gate.py     # PASS 20   FAIL 0 — справжнє встановлення робочого дерева
```
- До виправлення той самий тест: 10 з 16 перевірок червоні; smoke-перевірка давала decision block з 11 знахідками
  (шість `bypass/noqa`, дві `bypass/config`, три `protected/changed`).
- Негативні випадки, кожен побачено як block: `noqa`, дописаний у встановлений hook (Stop і pre_commit); змінені
  `CODE_EXTENSIONS`, `ruff.toml`, constitution і `.engine/rules.md`; без lock і з нечитабельним lock; tracked
  `project.env`, повернутий до seed-а після commit-а; підмінена копія seed-а.
- `bash tests/run_all.sh` на остаточному коді — 105 suites зелені.
- Overseer: BLOCK `20261013T214941Z-50dfbf` (мій текст у кроці 6 обіцяв тишу і після кроку 2 — це було неправдою),
  після виправлення PASS `20261013T221332Z-fc25b4`.

## Витрати
Додаткових сесій Claude не було. Overseer — двічі, субагент сесії задачі.

## Commit-и
`85c30de` (правило, `installed.py`, `seeds` у lock, тест) · `f7b0009` (порівняння із seed-ом, документи) · commit
цього закриття.

## Відкладене
- **Пропозиція 1750** (`tasks/proposed/1750-open-item-786-update-not-committed.md`): після `engine.py update` без
  commit-а gate блокує на оновлених tracked-файлах; відтворено на тимчасовому проєкті. Там розвилка: довіряти lock і
  для tracked-файлів (послаблює bypass guard) чи сказати в документі закомітити оновлення. Раджу друге.
- **Пропозиція 1751** (брак тесту від першого audit-у) уже виконана у `f7b0009`: сцена з `SOURCE_DIRS` є в тесті. Її
  можна закрити без роботи.
- **Пропозиція 1752** (брак тесту від другого audit-у): сцена з `LINT_CMD` перевіряє лише, що не названо
  `CODE_EXTENSIONS`, а не що block-у немає. Не дописував: це новий код після PASS.
- Overseer помітив поза задачею: зміна `LINT_CMD` чи `TEST_CMD` у ще не закоміченому `project.env` проходить як
  «justified» через текст `gate-allow` у коментарях самого seed-а. Так було й до цієї задачі; не чіпав.

## Рішення, які я ухвалив сам
- **Дві умови разом, не одна:** файла немає в базі diff-а і blob збігається з lock. Тому tracked `project.env`,
  повернутий до seed-а, лишається зміною, а lock після першого commit-а нічого не виправдовує.
- **Те саме правило для `protected_guard.py`** (порівняння з HEAD без snapshot): три `protected/changed` на
  недоторканих constitution, settings і `.engine/rules.md` були частиною того самого block-у, хоч задача їх не називала.
- **Текст seed-ів — у machine state, не в lock:** потрібен лише до першого commit-а на цій машині; копії вірять,
  лише поки її blob збігається з lock.
- **Новий модуль `.claude/hooks/installed.py`** замість коду в `gate.py`: ним користуються і gate, і guard.
- **`tests/test_gate_allows.py`:** до списку модулів, без яких gate не працює, додано `installed.py`.
- Новий тест не в швидкому наборі (близько 15 с: копіює репозиторій і встановлює його кілька разів).
