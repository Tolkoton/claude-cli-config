# Пакет 3б — фінальний звіт (2026-10-02)

Гілка `unattended/2026-10-02-package-3b`, від `engine/push-policy` (`9249b82`). Нічого не
push-нуто, нічого не злито. План — `docs/plan/package-3b.md`; контракт фічі —
`.claude/architecture/feature/engine-package-3b.md`; черга — `.claude/architecture/feature-dag.json`.

## 1. Таблиця commit-ів

| # | commit | що | перевірка |
|---|---|---|---|
| 0 | `173821e` | план дослівно в `docs/plan/package-3b.md` (попередня сесія) | — |
| 1 | `cd00c40` | старий граф → `architecture/archive/harness-hardening.json`; контракт фічі; новий граф (9 вузлів); `results-push-policy.json` як позначена копія 3а | HEAD до роботи: 77/77 тотожно 3а |
| 2 | `1263d01` | **S1** особистий шар: `user/settings.json`, `engine.py install --personal`, `evals/settings_parity.py`, `docs/tasks/{settings.json,README.md,effective-before-split.json}` | `test_personal_layer` 29/29, `test_settings_proposal` 8/8, паритет на моїй машині 13/13; сценарії 77/77 |
| 3 | `aa33b43` | **S2** hook-и спрацьовують один раз: статичний stand-down з маркером `STOOD_DOWN` у 9 hook-ах; runner виконує копію того checkout-у, де «почалася сесія» | `test_hooks_fire_once` 33/33; 16 старих зауважень ruff/mypy у 4 Python-hook-ах прибрано; сценарії 77/77 |
| 4 | `60300d6` | **S3** політика commit-ів за середовищем: таблиця в hook-у, перемикач `CLOUD_COMMIT_POLICY` (off) у `project.env`, `env-probe.sh`, `commit_checkpoint.sh` (суфіксна гілка, `--staged`, дзеркало хмарного правила) | `test_commit_policy` 20/20, `test_commit_checkpoint` 19/19, `test_env_probe` 15/15; 4 нові сценарії |
| 5 | `8dfec4c` | **S4** deny-список: точні правила кореня, `-fr` дзеркалить `-rf`, правило `./*` прибрано; у hook-у паритет `-rf`/`-fr`; `evals/permission_rules.py` | `test_root_delete_deny` 37/37; 5 нових сценаріїв |
| 6 | `179ed43` | **S5** `install.sh` відмовляється від особистої навички з іменем навички/команди двигуна; префікс `my-` | `test_install_collision` 12/12 (разом зі справжнім `install.sh` у тимчасову домівку) |
| 7 | `6b95cb7` | **S6** `docs/engine-limits.md`, особистий шар у `TEMPLATE-SETUP.md`, застарілий запис escalations закрито, карта власності, `evals/README`, `AGENTS.md`, еталон `evals/baseline/macos-14/results-package-3b.json` | `test_ownership` 49/49; еталон 86/86 |
| 8 | (цей) | записи: escalations (часові мітки вирівняно за commit-ами), parked (S7–S9), ledger, цей звіт | — |

Підсумок після останнього commit-а: 22 набори hook-checks зелені (8 нових); сценарії
**86/86** на macOS, проти `results-push-policy.json` — **77 тотожних, 9 задуманих
відмінностей** (усі — нові сценарії, перелічені нижче); `uvx ruff check` і
`uvx mypy --strict` чисті на всіх 17 Python-файлах, яких торкнулася гілка; `bash -n` чистий
на 12 shell-скриптах.

## 2. По пунктах плану

### 2.1 Поділ налаштувань (S1)

**Зроблено.** `.claude/settings.json` (запропонований у `docs/tasks/settings.json`) лишає
спільне: `allow/ask/deny`, усі hook-и, `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`. В особистий шар
`user/settings.json` перейшли: `defaultMode: acceptEdits`; усі 7 `additionalDirectories`
(шість домашніх тек і `/tmp/claude/`); `WebFetch`, `WebSearch` з `allow`; 4 змінні моделей
(`ANTHROPIC_DEFAULT_{SONNET,OPUS,HAIKU}_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`).

`engine.py install --personal [--ref] [--dry-run] [--home DIR]` зливає шар у
`~/.claude/settings.json` (або `$CLAUDE_CONFIG_DIR/settings.json`): ключі шару ставить,
списки доповнює лише тим, чого бракує, чужі ключі не чіпає, перед записом робить
`settings.json.engine-backup-<UTC>`, повторний запуск — 0 змін. Шар із ключем `hooks`
відмовляє (exit 2). Шар читається з git-ref, як і решта файлів двигуна.

**Терміни.** *Ефективні налаштування* — те, що реально діє після злиття рівнів user →
project → local за документованими правилами: скаляр бере найвищий рівень, списки
зливаються, `fallbackModel`/`modelPicker` беруться цілком. *Паритет* — рівність ефективних
налаштувань двох конфігурацій.

**Перевірено.** `evals/settings_parity.py compare` на **справжньому** `~/.claude/settings.json`
(тільки читання) + живий `.claude/settings.json` проти справжнього домашнього файлу зі злитим
у пам'яті шаром + `docs/tasks/settings.json`: **13/13 ефективних налаштувань тотожні**.
`test_personal_layer.py` 29/29 на синтетичному двигуні й тимчасових домівках (dry-run нічого
не пише; свіжий файл; злиття з чужими ключами; ідемпотентність; бекап; 5 відмов;
`CLAUDE_CONFIG_DIR`). `test_settings_proposal.py` 8/8 — порівнює пропозицію + шар із
**замороженим** знімком «до поділу» (`docs/tasks/effective-before-split.json`), тому
працює і до, і після того, як ти застосуєш файл.

Dry-run проти справжньої домівки: 2 зміни (`permissions`, `env` з шару), `model` і `theme`
збережено, нічого не записано, бекапу не з'явилося.

### 2.2 Політика commit-ів за середовищем (S3)

**Зроблено.** У `block-dangerous.sh` — таблиця:

| середовище | commit | push |
|---|---|---|
| моя машина з наглядом | відмова (commit — твоя контрольна точка) | `ask`; force push — deny |
| без нагляду | дозволено лише в `unattended/*` | `ask` → park через `park-ask-gated.py` |
| хмара (`CLAUDE_CODE_REMOTE=true`) | дозволено у власній незахищеній гілці сесії **лише** коли `CLOUD_COMMIT_POLICY="session-branch"` у `.claude/project.env`; постачається `off` | `ask`; force push — deny |

Перемикач читається `sed`-ом, не `source` (deny-hook не повинен виконувати файл проєкту).
`.claude/unattended/env-probe.sh` друкує факти `key=value`: тип сесії, `CLAUDE_*`/`ANTHROPIC_*`
**лише за іменами** (значення — тільки для allow-list несекретних), гілка, тип checkout-у,
remote-и з замаскованим `user:token@`, які settings-файли присутні, інструменти і — вердикт
політики саме тут. На моїй машині: `session_kind=attended-local`, `cloud_commit_policy=off`,
`commit_policy_here=allow` (бо гілка `unattended/*`).

`commit_checkpoint.sh`: зберігає суфіксну гілку (`unattended/<дата>-<пакет>`) замість того,
щоб форкнути на сьогоднішню дату; `--staged` комітить рівно індекс (бо `git add -u` ніколи
не додає новий файл); дзеркалить хмарне правило у власному захиснику — на цьому шляху жоден
hook не бачить команду.

**Перевірено.** `test_commit_policy.py` 20/20 на справжніх репозиторіях (8 випадків
середовища: хмара без ключа / з off / з on / з on на main / force push з on / локально з on
/ unattended-гілка в хмарі); `test_commit_checkpoint.py` 19/19; `test_env_probe.py` 15/15
(підкладене значення `ANTHROPIC_API_KEY` і токен у URL ніде не з'являються); 4 нові
сценарії `bd-commit-cloud-*`.

### 2.3 Hook-и без подвійного виконання (S2)

**Факт із документації.** Той самий handler, визначений у двох settings-файлах, Claude Code
виконує один раз; подвійно виконується лише той самий скрипт під **різними** рядками команди
(домашній `~/.claude/hooks/x.sh` поруч із проєктним `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh`
— саме так ставить копії навичка claude-autonomy).

**Зроблено.** У кожному з 9 hook-ів — `engine_stand_down()`: копія, що не є
`$CLAUDE_PROJECT_DIR/.claude/hooks/<ім'я>`, виходить з кодом 0, якщо проєкт підключає
`hooks/<ім'я>` у `settings.json` або `settings.local.json`. Рішення — лише з файлів, ніколи з
порядку чи часу. Stand-down **ніколи не мовчить**: `STOOD_DOWN: <ім'я> defers to <копія
проєкту>` у stderr (allow — це exit 0 з **порожнім** stderr). `ENGINE_HOOK_ALWAYS_RUN=1` —
єдиний override, і лише в безпечному напрямку. Проєкт без hook-ів лишає домашню копію
працювати. Особистий шар hook-ів не підключає; `install --personal` відмовляє такому шару.

Runner `evals/run_hook_scenarios.py`: для сценарію з `project_dir` (worktree) виконує копію
того checkout-у, як це робив би Claude Code; з `--hooks-dir` ставить override.

**Звіт про мій справжній `~/.claude/settings.json`** (тільки читання): ключі `model`,
`theme`. Ключа `hooks` немає, теки `~/.claude/hooks` немає — **дублів немає**.

**Перевірено.** `test_hooks_fire_once.py` 33/33: 9 домашніх копій stand-down з маркером;
у тому самому середовищі проєктні копії блокують усі 10 deny-випадків `test_deny_gaps` і
4 refuse-випадки `test_guardrail_paths`; проєкт без hook-ів — домашня копія блокує.

### 2.4 install.sh і збіг імен (S5)

**Зроблено.** Перед будь-яким лінкуванням `install.sh` порівнює імена `user/skills/*` з
іменами навичок (`.claude/skills/*`) **і** команд (`.claude/commands/*.md`) двигуна; збіг —
відмова з поясненням, що і що затінить, і з конвенцією: нові особисті навички —
`user/skills/my-<name>`. `live-build` не перейменовано.

**Перевірено.** `test_install_collision.py` 12/12. Перша версія мала помилку:
`engine_names | grep -q` під `pipefail` — ранній вихід grep посилає SIGPIPE продюсеру, і
конвеєр звітує невдачу на збіг будь-якого імені, крім останнього (`overseer` пропускало,
`plan-slice` ловило). Замінено на цикл; тест, що знайшов це, лишився.

### 2.5 Deny `Bash(rm -rf /*)` (S4)

**Зроблено.** У пропозиції: точне правило кореня (для `-rf`, `-fr`, `-r`), `-fr` дзеркалить
кожне правило `-rf`, правило `./` + `*` прибрано (той самий дефект — воно забороняло
`rm -rf ./build`). Катастрофічні літерали, яких правило не виразить точно (`/*`, `./*`),
блокує hook, де всі rm-шаблони тепер приймають і `-rf`, і `-fr`. `evals/permission_rules.py`
— еталонний матчер документованої семантики (`*` — будь-який текст, `:*` == ` *`, без `*`
— точний збіг, складена команда збігається, якщо збіглася будь-яка підкоманда).

**Перевірено.** `test_root_delete_deny.py` 37/37: заблоковано список ∪ hook — `rm -rf /`,
`rm -rf /*`, `rm -rf ~`, `rm -rf $HOME`, їх `-fr`-близнюки, `.`, `./*`, складена команда
(13); пропущено обома — тимчасові теки за абсолютним шляхом, `./build`, `.venv`, `build dist`
(8); показано, що **живий** файл сьогодні забороняє `rm -rf /tmp/claude/scratch` і
`rm -fr ./build`. 5 нових сценаріїв.

### 2.6 Обмеження в docs/ (S6)

`docs/engine-limits.md`: одна сесія — один репозиторій (`block-dangerous.sh` визначає гілку за
`$CLAUDE_PROJECT_DIR`, а не за `cd`; Claude Code тримає цю змінну на головному checkout-і
навіть у worktree); hook-и бачать команду, яку агент набирає, а не команду зі скрипта;
hook-и скануть весь текст команди (помилкові спрацювання на цитати — свідомі);
одноразовість і маркер `STOOD_DOWN` (`grep` у `session-*.log`); рівні settings; хмара читає
лише спільний файл; `*` у deny; таблиця політики commit-ів.

### 2.7 Застарілий запис escalations (S6)

Запис 2026-08-27 «commits during an overnight run» — `OPEN`/«IMPLEMENTED — awaiting one owner
edit» → `CLOSED`. Підтвердження: `git log -S'Bash(git commit' -- .claude/settings.json` —
правило додано в `8029d22`, прибрано в `63df312` (сесія D-27); живий файл правила не має;
commit-и цієї гілки — доказ у дії.

### 2.8 Решта критеріїв «ГОТОВО»

- Карта власності: `user/settings.json` (user), `docs/tasks/`, `docs/engine-limits.md`,
  `evals/settings_parity.py`, `evals/permission_rules.py`, `hook-checks/fixtures/` (project);
  `env-probe.sh`, `commit_checkpoint.sh` — engine (постачаються). `test_ownership` 49/49.
- `docs/TEMPLATE-SETUP.md` Step 3: таблиця «спільне / особисте / локальне для машини»,
  `install --personal`, префікс `my-`, 9 hook-ів, посилання на обмеження.
- Еталон `evals/baseline/macos-14/results-package-3b.json`: 86/86, macOS 14.8.9
  (Darwin 23.6.0), jq 1.8.2, Python 3.12.3, записаний з commit-а S5 (S6 hook-ів не чіпає);
  фінальний HEAD проти нього — тотожний.
- Задумані відмінності від `results-push-policy.json` (усі — нові id): `bd-commit-cloud-switch-off`,
  `bd-commit-cloud-switch-on`, `bd-commit-cloud-switch-on-but-main`,
  `bd-commit-local-with-cloud-switch-on`, `bd-rm-rf-root`, `bd-rm-rf-root-star`,
  `bd-rm-fr-root`, `bd-rm-rf-tmp-absolute-allowed`, `bd-rm-fr-build-allowed`.

## 3. Автономні рішення (усі в `.claude/overseer/escalations.md`, формат AUTONOMOUS, CLOSED)

| id | рішення | чому не питав |
|---|---|---|
| `3b-baseline-alias` | `results-push-policy.json` — позначена копія 3а: `engine/push-policy` == `engine/package-3a` | чистий Ubuntu із macOS не записати; план назвав файл, якого не було |
| `3b-S1-personal-keys` | усі 7 `additionalDirectories` → особисте (і `/tmp/claude/`); `STOP_HOOK_BLOCK_CAP` — спільне; шар читається з ref; домівка — `--home` → `CLAUDE_CONFIG_DIR` → `~/.claude` | паритет 13/13 доводить відсутність ефекту; `CLAUDE_CONFIG_DIR` — документований спосіб перенести `~/.claude` |
| `3b-S1-frozen-before` | тест пропозиції порівнює із замороженим знімком, не з живим файлом | інакше тест інвертується в момент, коли ти застосуєш файл |
| `3b-S2-stand-down` | stand-down залишено попри зауваження критика в раунді 1, перевизначено як статичне правило з маркером; критик дав PASS у раунді 3 | твоя рамка прямо називає випадок «підключено і в домівці, і в проєкті» |
| `3b-S3-cloud-switch` | перемикач у `project.env`, читається `sed`; «гілка сесії» — будь-яка незахищена; зонд друкує імена змінних, значення — за allow-list | `project.env` — наявна поверхня конфігурації hook-ів; префікс хмарної гілки — саме те, що зонд має спостерегти, а не вгадувати |
| `3b-S4-dot-slash-rule` | прибрано і правило `./*`; `~/*`, `$HOME*`, `--recursive *` лишено | той самий дефект, що й у кореня (`rm -rf ./build` заборонявся); інші нічого спостережуваного не змінили б |
| `3b-S5-collision-scope` | збіг перевіряється з навичками **і** командами, не з агентами; префікс `my-`; відмова цілком, не пропуск одного | навички й команди ділять простір `/<ім'я>`; напівзадеплоєний набір непомітніший за жоден |
| `3b-S6-baseline-name` | тека за LocalHostName машини (з задачі 030 — `macos-14`); запис із commit-а S5 | S6 hook-ів не чіпає |

Відхилення від контракту феатур-критика (раунд 1, O1 — «прибери stand-down») зафіксоване як
рішення; його валідну половину (O5 — exit 0 без маркера невідрізнимий від allow) прийнято.

## 4. Відкладені вузли («лише за мною») — `.claude/overseer/parked.md`

**S7 — застосувати спільний `settings.json`.** З кореня репозиторію:
```bash
cp docs/tasks/settings.json .claude/settings.json && python3 hook-checks/test_settings_proposal.py
```
Тест надрукує `APPLIED`. Потім перезапусти Claude Code (settings читаються на старті).

**S8 — застосувати особистий шар до справжнього `~/.claude`.** Спершу dry-run, потім по-справжньому:
```bash
python3 engine.py install --personal --ref unattended/2026-10-02-package-3b --dry-run
python3 engine.py install --personal --ref unattended/2026-10-02-package-3b
```
Бекап: `~/.claude/settings.json.engine-backup-<UTC>` поруч із файлом. Краще разом із S7: до
того особисті ключі стоятимуть двічі (без шкоди — значення ті самі).

**S9 — зонд у хмарній сесії.** У хмарній сесії Claude Code на цьому репозиторії:
```bash
bash .claude/unattended/env-probe.sh
```
Вклей вивід. Дивитись на `session_kind`, `env.CLAUDE_CODE_REMOTE`, `git_branch`,
`git_remotes`, `settings_user/local` (мають бути absent). Тоді — `CLOUD_COMMIT_POLICY="session-branch"`
у `.claude/project.env` або лишити `off`.

Також не твоє, але варто знати: гілку ніхто не push-нув і не злив; усі commit-и — на
`unattended/2026-10-02-package-3b`.

## 5. Джерела (code.claude.com, прочитано 2026-10-02 через субагента claude-code-guide)

- `/docs/en/settings` — «Settings precedence»: вищий рівень перекриває той самий ключ нижче;
  «Lists merge instead of overriding» (`permissions.allow` тощо); винятки `fallbackModel`,
  `modelPicker`.
- `/docs/en/hooks` — «Hooks merging, deduplication, and execution»: «Hook entries merge across
  settings levels…»; «All matching hooks run in parallel. If you define the same handler in
  more than one settings file, it runs once»; порядок між рівнями не документований;
  `${CLAUDE_PROJECT_DIR}` лишається коренем, де почалася сесія, і в worktree.
- `/docs/en/env-vars` — `CLAUDE_CODE_REMOTE` = `true` у хмарній сесії; `CLAUDE_CODE_REMOTE_SESSION_ID`;
  `ANTHROPIC_DEFAULT_*_MODEL`. `CLAUDE_CODE_SUBAGENT_MODEL` **не документовано** (лишено як є,
  бо воно в твоєму живому файлі).
- `/docs/en/claude-code-on-the-web` — у хмарній сесії читається спільний `.claude/settings.json`;
  `~/.claude/settings.json` і `.claude/settings.local.json` — не читаються. Про `git commit`
  із хмари прямого твердження немає — звідси зонд і вимкнений перемикач.
- `/docs/en/permissions` — `*` збігається з будь-яким текстом, правило без `*` — точне, `:*` ==
  ` *`; складена команда розбивається на `&&`, `||`, `;`, `|`, `|&`, `&`, newline; deny/ask
  діють, якщо збіглася будь-яка підкоманда. Порядок deny→ask→allow одним реченням не
  сформульовано; матчер реалізує deny-first як єдиний порядок, що не перетворює deny на allow.
- `/docs/en/settings-reference` — `defaultMode` і `additionalDirectories` дозволені на будь-якому
  рівні (`auto`/`bypassPermissions` — лише user/managed).

## 6. Чого мені бракувало

1. **Hook `block-dangerous.sh` блокував мої ж правки п'ять разів** — heredoc-и й commit-повідомлення,
   що *згадували* `rm -rf /*` чи `git push --force`. Це документована поведінка, але вона
   коштувала ~5 повторних спроб. Обхід: Write/Edit-інструмент, скрипти з файлів,
   `git commit -F <файл>`. Варто змінити в двигуні: не чіпати шаблони (false negative гірший),
   але дати **документований канонічний спосіб** писати такі тексти (вже є в
   `engine-limits.md`), і, можливо, навчити hook пропускати `git commit -F <path>` як окрему
   форму — текст повідомлення тоді не в команді.
2. **Файл еталону з плану не існував** (`results-push-policy.json`). Довелося вирішувати сам
   (копія з поясненням). Варто: план, що називає файл, має назвати і команду, яка його створює.
3. **`recheck_parked.py` зчитав токен `file:` зі згадки в тексті** й позначив S7 «RESUMED».
   Повернув, переформулював. Варто змінити в двигуні: парсити токени лише з початку слова після
   `Unblocks when:` і не в лапках/бектіках — або попередити в parked.md, що синтаксис токенів у
   тексті не згадують.
4. **`CLAUDE_CODE_SUBAGENT_MODEL` не документовано** — поклав в особистий шар як є, бо так у
   живому файлі. Якщо змінна мертва, це твоє, не моє, рішення її прибрати.
5. **Порядок deny→ask→allow не підтверджений документацією одним реченням** — матчер реалізує
   deny-first; для тестів цього пакету важливий лише deny/не-deny.
6. **16 старих зауважень ruff/mypy у 4 Python-hook-ах** (BLE001, PLW1510, ISC004, FURB177,
   type-args) — довелося прибрати в S2, щоб «змінені файли чисті» було правдою. Варто: один
   прогін `ruff check --isolated .claude` у CI двигуна, щоб таке не накопичувалось.
7. **`test_engine_install.py` порівнює hook-и з HEAD** — під час роботи над hook-ами він
   червоний до commit-а, що шумить у «після кожного зрізу прогони всі тести». Варто: порівнювати
   з робочою копією або позначати цей кейс як «потребує commit-а».
8. **Час у моїх escalations-записах був вгаданий** (я не знав зсуву зони); вирівняв за
   commit-ами. Варто: шаблон запису з командою `date -u`.
9. **Без прав на `.claude/settings.json`** — за дизайном; усе підготовано як пропозиція (S7).
10. **Критик забрав три раунди (~235k токенів)** на одну тезу (stand-down). Корисно: раунд 2
    знайшов реальну дірку (мовчазний exit 0). Але раунд 1 спирався на неповне прочитання
    рамки. Варто: давати критикові рамку з позначеними «вимогами власника» окремо від
    «рішень агента».

## 7. Витрати і час

- Commit-и: план `09:41` (локально, попередня сесія); цієї сесії — з `10:39` до `11:14`
  (S1→S6, 35 хв на шість зрізів після ~20 хв читання стану й перевірки документації); записи
  і звіт — до ~`11:25`. Усього від плану ≈ 1 год 45 хв.
- Токени субагентів: перевірка документації ≈ 75k; критик 81k + 92k + 62k ≈ 235k; разом ≈ 310k.
- Основна сесія: за лічильником бюджету ≈ 400k токенів контексту (точна сума в доларах —
  у `/cost` цієї сесії; я її не бачу).
- Прогонів сценаріїв (кожен — свіжий sandbox з `uv sync`): 8, по ~1–2 хв.
