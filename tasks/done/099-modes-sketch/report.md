# 099 — Режими В: Ескіз — звіт

## Що змінилось для власника
- **Режим ескіз працює повністю.** Ваше «так» на `docs/tasks/settings.json` runner застосував (`40dff67`); я перевірив
  наживо: `reader` без рядка запиту не запускається, а з рядком — читає запис, і PASS у журнал пише скрипт, не автор.
- **Карантин:** задача в режимі ескіз, що змінила файл поза `sketches/`, `.engine/` і `tasks/`, — блок; робочий код,
  що посилається на `sketches/`, — блок у будь-якому режимі; код ескізу gates не перевіряють.
- **Закриття ескізу:** runner закриває його лише із записом `.engine/sketches/<назва>.md`, PASS читача на цьому записі
  і без змін поза карантином. Три BLOCK читача поспіль — задачу відкладає runner.
- Ескіз робочим кодом не стає: перенесення — нова задача.

## Що збудовано (commit `9367ae4`, overseer PASS `20261011T061554Z-cefbce`)
- **Роль `reader`** (`.claude/agents/reader.md`, `.claude/hooks/reader.py`): свіжий контекст, лише читання; старт лише
  рядком `READER_REQUEST <id>`; PASS або BLOCK пише скрипт із відповіді агента; запис, змінений під час читання, —
  недійсне читання.
- **Карантин у `gate.py`**, **`mode.py check-close` для ескізу**, **шаблон запису** `.claude/references/sketch-record.md`,
  розділ у `slice-builder`, `docs/engine-limits.md` (чого карантин не ловить), `tests/test_model_roles.py` (`reader` —
  роль перевірки).
- **Після третього BLOCK, за вашою відповіддю:** (а) записи в `.engine/` і `tasks/` — ніколи не робочий код, хоч би що
  казав `CODE_EXTENSIONS`; (б) типові `ruff`, `mypy`, `pytest` повних шарів оминають `sketches/` в корені; власні
  `LINT_CMD` / `TYPECHECK_CMD` / `TEST_CMD` проєкту мають виключати `sketches/` самі (сказано в `docs/engine-limits.md`).
  Delete guard теж не судить код ескізу.

## Демонстрація на хвилину
```
python3 tests/test_sketch_quarantine.py     # PASS 29   FAIL 0 — негативні випадки першими
python3 tests/test_reader.py                # PASS 23   FAIL 0 — запуск reader без рядка запиту відхилено
python3 tests/test_mode.py                  # ескіз без запису або без PASS не закривається
python3 .claude/hooks/reader.py status      # останній вердикт: PASS 20261011T085117Z-ea69f8
```

## Жива перевірка після застосування налаштувань (ця сесія)
- `python3 .claude/unattended/settings_check.py` — «.claude/settings.json is the proposal; nothing to apply»;
  `python3 tests/test_settings_proposal.py` — PASS 27, FAIL 0. У чинному файлі `reader.py guard` (рядок 186) і
  `reader.py record` (рядок 297).
- **Негативний випадок першим:** агент `reader`, запущений без запиту, — відхилено hook-ом: «No reader request is
  pending, so the reader is not started».
- **Позитивний:** запис `.engine/sketches/reader-live-check.md` (питання саме про ці два hook-и, команда і її вивід) →
  `reader.py request` надрукував `READER_REQUEST 20261011T085117Z-ea69f8` → агент `reader` відповів PASS →
  `.engine/reader/ledger.md` отримав запис `READER_PASS` від скрипта; я журнал не писав.
- `bash tests/run_all.sh` — 91 набір зелений, rc=0 (один прогін, наприкінці задачі).

## Витрати
Додаткових сесій Claude не було. Overseer і reader — субагенти сесій задачі.

## Commit-и
`9367ae4` (код) · `40dff67` (налаштування, застосував runner) · commit цього закриття (звіт, запис живої перевірки,
журнал читача).

## Відкладене
- Три браки тестів від overseer-а — задачі `773`, `774`, `775` у `todo/`; `758` — тест уже є в `9367ae4`, задачу закриє
  той, хто її візьме.
- У робочому дереві лежать незакомічені `.engine/goals.md` (версія 4) і видалений `.engine/goals/proposed.md` — це
  поправка задачі `103` (вона в `todo/`), не цієї задачі; уже записано в журналі аномалій сесією задачі 736. Не чіпав і
  не комітив.

## Рішення, які я ухвалив сам
- Живу перевірку зробив справжнім записом ескізу без коду під `sketches/` і лишив його та журнал читача в гілці як
  доказ (обидва під `.engine/`, тож ні gates, ні `check-close` їх робочим кодом не вважають).
- Виключення для `ruff` — абсолютний шлях до `sketches/` в корені, для `mypy` — `^sketches/`: голе ім'я виключило б і
  `src/sketches/`. Виключення додаються лише там, де тека `sketches/` є.
- Delete guard виправив у межах цієї задачі: `gate.py` обіцяє, що код ескізу не перевіряє жоден guard.
- `.engine/artifacts/099-sketch/wip.patch` видалено раніше: його вміст — commit `9367ae4`.
