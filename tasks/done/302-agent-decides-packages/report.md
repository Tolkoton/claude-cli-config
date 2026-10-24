# Звіт: 302 — пакети проєкту вирішує агент

## Що змінилось для власника
- Агент сам додає й прибирає залежності проєкту власним менеджером проєкту: `uv add/remove`, `poetry add/remove`,
  `npm install/uninstall`, `yarn`/`pnpm add/remove`, `cargo add/remove`, `go get`, `go mod tidy`,
  `bundle add/remove`. Питання вам немає, задача без нагляду через це не паркується.
- Гігієна за агентом: lock-файл оновлюється в тому самому commit-і, а пакет і причина, чому він потрібен, названі у
  звіті задачі (`.claude/engine-rules.md:29-30`).
- Як і раніше, питають: встановлення поза середовищем проєкту (`pip`, `pipx`, `gem install`, глобальне `-g`:
  `npm install -g`, `pnpm add -g`, `yarn global`) — `.claude/engine-rules.md:19-20`. Публікація пакетів,
  `curl | sh` і `sudo` заборонені, як і були.
- **Оновлення** версій лишається вашим рішенням через `/maintain` (`.claude/commands/maintain.md:12-13`), його не чіпали.
- Важливо: у ваших проєктах зміна з'явиться після наступного релізу двигуна. `engine.py install/update` без `--ref`
  бере найновіший tag (зараз `v0.14.1`), а він старіший за цю правку. Реліз — ваша команда; аудит релізу
  `v0.14.2` уже стоїть задачею 118.

## Демонстрація на хвилину
Свіжий проєкт із `HEAD` двигуна (`5866741`), режим unattended (`.claude/state/overseer/mode` = `unattended`):
```
python3 engine.py install <tmp> --ref HEAD --no-register
  settings.json: `uv add` в ask — False; `npm install -g` в ask — True; публікація npm у deny — True
  park-ask-gated.py: uv add requests -> пропускає;  cargo add serde -> пропускає
                     pip install requests -> deny (park);  npm install -g typescript -> deny (park)
  block-dangerous.sh: публікація npm -> BLOCKED, rc=2
```
Той самий прогін без `--ref` (tag `v0.14.1`) ще паркує `uv add requests` — див. застереження вище.

Перевірки 2026-10-24: `tests/test_push_by_environment.py` PASS 109 / FAIL 0 (випадки задачі —
`tests/test_push_by_environment.py:219-225`), `tests/test_settings_proposal.py` PASS 28,
`tests/test_settings_proposal_install.py` 34 passed, `tests/test_maintain.py` PASS 62,
`bash tests/run_all.sh --fast` — 63 suites green. `settings_check.py`: `.claude/settings.json` збігається з
пропозицією `docs/tasks/settings.json`.

## Що зроблено за пунктами задачі
- Ask-gated → Auto-allowed у `.claude/engine-rules.md` — commit `e1436ae`. `ask` у `.claude/settings.json` —
  пропозицію `docs/tasks/settings.json` підготовано в `e1436ae`, runner застосував її на ваше «так» у `b21bfa3`.
  Інших копій settings двигуна з такими правилами немає: у `user/settings.json`,
  `.claude/settings.local.json.example` і `tests/fixtures/home-settings.json` правил менеджерів пакетів немає.
- Гігієна одним рядком у правилах — `.claude/engine-rules.md:29-30`, докладніше в
  `.claude/references/permission-philosophy.md:38`.
- Публікація, `curl | sh`, `sudo` лишились у deny — показано вище.
- Навички й шаблони: у `/feature-architect`, `/plan-slice`, `slice-builder` і `tasks/TEMPLATE.md` немає вимоги
  питати власника про пакет. «No new dependency» у `/hotfix` і `/bugfix` — межа обсягу самої правки, а не питання
  власникові; їх не чіпали. У `/maintain` уточнено, що додавання пакета — не його справа
  (`.claude/commands/maintain.md:12-13`); питання про оновлення лишилось як було.
- `.claude/hooks/park-ask-gated.py`: список `ASK_GATED` дзеркалить нову `ask`; в eval
  `evals/scenarios/hooks/60-park-ask-gated.json` негативний випадок перейшов на `pip install requests`.
  Документи: `.claude/references/permission-philosophy.md`, `docs/TEMPLATE-SETUP.md`.

## Витрати
Ця сесія — лише перевірка й звіт; додаткових сесій Claude не було. Основну правку зроблено в інтерактивній сесії з вами.

## Діапазон commit-ів
`6a74eaa` (перше взяття в `doing/`) … `e1436ae` (правка) … `b21bfa3` (застосування settings runner-ом) … commit закриття.

## Відкладене
- Поширення в проєкти — з релізом двигуна (задача 118, ваша команда `engine.py release`).

## Рішення, які я ухвалив сам
- `pip`, `pipx`, `gem install` лишились в `ask`: вони ставлять пакет поза manifest і lock-файлом проєкту, тобто це
  не «менеджер проєкту». Ціна повернення — один рядок в `ask`.
- Глобальні форми (`npm install -g`, `npm i -g`, `npm install --global`, `pnpm add -g/--global`, `yarn global`)
  додано в `ask`: без них правило для `npm install` пропускало б і глобальне встановлення.
- Команда, яка хоче паузу перед кожною новою залежністю, може повернути правила менеджера у свій `ask`
  (`.claude/references/permission-philosophy.md:64-66`).
