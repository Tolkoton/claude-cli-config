# Пакети проєкту вирішує агент, без питання власникові

Клас: 3
Залежить від: —
Потрібна присутність власника: ні
Режим: соло
Аудит потрібен: ні
Додаткові сесії: ні

## Рішення власника
Слова власника (2026-10-23): «чому це я маю погоджувати якісь там залежності? Це є саме останнє, де я треба. Агент
сам краще знає, який софт він пише і що йому для того потрібно. Тому нам треба… правку в двигун, що ці такого класу
питання вирішуються ним».

## Що сталося
У проєкті thinkhow задача 105 винесла власникові питання: назвати явно в `pyproject.toml` пакети `google-auth`,
`pyyaml` і `httpx`. Код їх уже використовує, і вони стоять як залежності інших пакетів. Причина питання — правило
«adding or removing packages» у розділі Ask-gated `.claude/engine-rules.md` і рядки менеджерів пакетів у `ask`
`.claude/settings.json`. Unattended агент не може їх виконати і паркує задачу з питанням.

## Що зробити
- Додавання й видалення залежностей проєкту його власним менеджером пакетів (`uv add/remove`, `poetry add/remove`,
  `npm install/uninstall`, `cargo add/remove` …) перенести з Ask-gated в Auto-allowed: у `.claude/engine-rules.md` і з
  `ask` в `allow` у `.claude/settings.json` (і в інших копіях settings двигуна, якщо там те саме).
  `.claude/settings.json` агент сам не править: він готує повний файл `docs/tasks/settings.json`, перевіряє його
  `settings_check.py` і ставить задачу в `blocked/` з рядком `board.py action-line apply-settings` (README,
  «Дії, які виконує runner»); на «так» власника файл застосовує runner.
- Гігієну агент тримає сам, без питання. Записати одним рядком у правилах:
  - пакет ставиться через менеджер проєкту, lock-файл оновлюється в тому самому commit-і; жодного встановлення поза
    середовищем проєкту;
  - пакет і чому він потрібен названо у звіті задачі.
- Публікація пакетів, `curl | sh` і `sudo` лишаються забороненими, як і раніше.
- Перевір, що шаблони задач і навички (`/feature-architect`, `/plan-slice`, `slice-builder`) більше не вимагають
  питати власника про пакет. `/maintain` питає про **оновлення** версій — це окрема річ, її не чіпати.

## Готово, коли
- У свіжо встановленому проєкті unattended агент додає пакет менеджером проєкту без питання і без паркування.
- Публікація пакетів, як і раніше, відмовляється.

## Питання до власника

### 1. Як провести цю правку, коли auto mode не дає агентові змінювати власні дозволи?
Сесія runner-а йде з `--permission-mode auto`. Його classifier тричі відмовив з причиною `[Self-Modification]`:
на правку `.claude/engine-rules.md` (через Bash і через Edit) і навіть на `board.py action-line apply-settings`.
Задача саме й послаблює дозволи агента, тому classifier її не пропускає. Обходити його я не став. У дереві нічого не
змінено, крім цього розділу.

Що я підготував і зроблю, щойно правку буде дозволено (рішення ухвалив сам):
- `.claude/engine-rules.md`, Ask-gated: замість «adding or removing packages (uv, poetry, pip, npm, cargo…)» —
  «an install outside the project's environment (`pip`, `pipx`, `gem install`, a global `-g`)». Auto-allowed:
  дописати «the project's packages through its own manager (`uv`, `poetry`, `npm`, `yarn`, `pnpm`, `cargo`, `go`,
  `bundle` add/remove) — the lock file in the same commit, the package and why it is needed named in the report».
- `docs/tasks/settings.json` (пропозиція налаштувань): прибрати з `ask` правила `uv add/remove`, `poetry add/remove`,
  `npm install/uninstall`, `yarn add/remove`, `pnpm add/remove`, `cargo add/remove`, `go get`, `go mod tidy`,
  `bundle add/remove`; додати глобальні форми `npm install -g`, `npm install --global`, `pnpm add -g`, `yarn global`.
  `pip`, `pipx`, `gem install` лишаються в `ask`: вони ставлять пакет поза manifest і lock-файлом проєкту. До `allow`
  дописувати нічого не треба: там уже стоїть `Bash`.
- `.claude/hooks/park-ask-gated.py`: список `ASK_GATED` дзеркалить нову `ask` (`tests/test_push_by_environment.py`
  перевіряє дзеркало). `evals/scenarios/hooks/60-park-ask-gated.json` і `tests/test_push_by_environment.py:217`:
  `uv add requests` тепер проходить без паркування, тож негативний випадок перейде на `pip install requests`.
  Також буде новий випадок: `uv add requests` unattended — allow.
- Документи: `.claude/references/permission-philosophy.md`, `docs/TEMPLATE-SETUP.md` («The shared `ask` list»),
  `.claude/commands/maintain.md:12` (там сказано, що зміна пакетів — дія власника; правда тепер лише щодо
  **оновлення** версій, і саме питання `/maintain` лишається без змін).
- Публікація пакетів, `curl | sh`, `sudo` лишаються в deny, як і були.

Варіанти:
- **А (раджу):** запустити задачу в інтерактивній сесії з вами (`claude` у теці двигуна, «візьми задачу 302»). Там
  кожну правку дозволів ви підтверджуєте самі, а я роблю все з переліку вище, з тестами й reader-ом.
- **Б:** ви вносите правку руками за переліком вище, а задача повертається до мене лише для перевірки й звіту.
- **В:** дозволити runner-у такі правки, тобто додати правило дозволу для Bash або запускати runner не в `auto`. Не
  раджу: це послаблює захист не лише для цієї задачі.

Відповідь:
