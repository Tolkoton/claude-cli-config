# Пакет 3б, раунд виправлень — фінальний звіт (2026-10-02)

Гілка `unattended/2026-10-02-package-3b`, лише нові commit-и поверх твого `7abf751`
(S7 застосовано: `.claude/settings.json` == `docs/tasks/settings.json` на момент старту —
перевірено байт у байт). Нічого не відкочено, не переписано, не push-нуто. План —
`docs/plan/package-3b-finish.md`; контракт — `.claude/architecture/feature/engine-package-3b-finish.md`;
черга — `.claude/architecture/feature-dag.json` (попередня черга 3б — в `architecture/archive/engine-package-3b.json`).

## 1. Таблиця commit-ів

| # | commit | що | перевірка |
|---|---|---|---|
| 0 | `2b9da96` | план дослівно в `docs/plan/package-3b-finish.md` | — |
| 1 | `a0f5109` | контракт фічі; черга F1–F8 (+S8/S9 перенесені) | критик: REVISE (#1 обсяг перейменування) → PASS у раунді 2 |
| 2 | `6172293` | **F1** stand-down прибрано з 9 hook-ів і 4 копій; `ENGINE_HOOK_ALWAYS_RUN` прибрано; claude-autonomy у user-scope ставить лише settings без hook-ів (`settings.user.json.template`) | `test_no_home_hook_copies` 25/25; сценарії 86/86 тотожно еталону 3б |
| 3 | `8fc4223` | **F2** push виходить із блоку захищених гілок; повідомлення називає підкоманду; ask/deny закріплено тестом; 2 сценарії → allow, +1 worktree-commit; `results-push-policy.json` → `results-package-3a-copy.json` | `test_commit_policy` 28/28; сценарії: 84 тотожні, 3 задумані відмінності |
| 4 | `12361a1` | **F3** `session-claude.sh` передає `--permission-mode acceptEdits` | `test_session_launch` 9/9 (shim `claude` записує argv) |
| 5 | `3b8f034` | **F4** особистий шар: `defaultMode: auto`, без змінних моделей | `test_personal_layer` 28/28; `test_settings_proposal` 10/10 (6 задуманих відмінностей із причинами) |
| 6 | `0d91f4d` | **F5** `approve-project-data.py` (PermissionRequest), пропозиція підключення, тести, справжні headless-сесії | `test_approve_project_data` 40/40; `evals/probe_permission_hook.sh`: A exists / B absent / C absent |
| 7 | `e81924b` | **F6** дрібниці: `recheck_parked` читає лише рядок Unblocks; `test_engine_lint`; `test_engine_install` пропускає порівняння з HEAD на брудних hook-ах; `git commit -F` задокументовано; критики розрізняють вимоги власника | `test_recheck_parked` 7/7; `test_engine_lint` — ruff і mypy --strict чисті на 9 файлах двигуна (21 знахідку виправлено) |
| 8 | (цей) | **F7** docs, очікування карти власності, еталон `results-package-3b-finish.json`, parked F8, ledger, цей звіт | `test_ownership` 53/53; еталон 87/87 |

Підсумок: 25 наборів hook-checks зелені (5 нових); золотий набір **87/87**, проти еталону 3б —
**84 тотожні, 3 задумані відмінності** (`bd-push-on-main` block→allow,
`bd-push-on-protected-branch-in-worktree` block→allow, новий `bd-commit-on-unattended-branch-in-worktree`);
`uvx ruff check` і `uvx mypy --strict` чисті на всіх Python-файлах, яких торкнувся раунд, і на всьому
Python двигуна (`test_engine_lint`).

## 2. По пунктах

### 2.1 Stand-down прибрано (F1)
Видалено `engine_stand_down()` і виклики з 9 hook-ів та 4 копій у `claude-autonomy/scripts`;
`ENGINE_HOOK_ALWAYS_RUN` прибрано з runner-а, зонда й документації. Лишилось від S2: чистка
ruff/mypy у 4 Python-hook-ах і запуск hook-а з того checkout-у, де «почалася сесія»
(`project_dir` у сценаріях worktree). Джерело дублів закрито: єдине, що двигун колись
ставив у `~/.claude/hooks/`, — user-scope навички claude-autonomy; тепер user-scope пише
`assets/settings.user.json.template` (шаблон проєкту без блоку `hooks`) і жодного скрипта,
з поясненням у SKILL.md. **Перевірено:** `test_no_home_hook_copies.py` 25/25 — симуляція
user-scope установки в тимчасову домівку рівно за кроком 3 SKILL.md не підключає hook-ів і не
створює `hooks/`; обидва шаблони збігаються в усьому, крім `hooks`; у жодному hook-у, копії,
runner-і чи зонді немає `engine_stand_down`/`STOOD_DOWN`/`ENGINE_HOOK_ALWAYS_RUN`; копії
навички байт у байт рівні живим hook-ам. `test_hooks_fire_once.py` видалено разом із механізмом.

### 2.2 Push не блокує hook (F2)
У блоці захищених гілок `block-dangerous.sh` лишився лише `commit`; повідомлення —
`BLOCKED: direct git commit on protected branch '<гілка>'` (раніше друкувалося друге слово
команди, для `git -C dir commit` — `-C`). **Закріплено тестом** на живому `.claude/settings.json`
і на пропозиції: `Bash(git push:*)` в `ask`, `Bash(git push --force*)` і `Bash(git push -f *)` у
`deny`, жодного push у `allow`. Сценарії: `bd-push-on-main` і `bd-push-on-protected-branch-in-worktree`
чекають `allow` (другий збережено, щоб worktree лишався виміряним і для push);
`bd-commit-on-unattended-branch-in-worktree` (allow) доводить, що гілка у worktree
визначається. **Перейменування:** `results-push-policy.json` → `results-package-3a-copy.json`
з label, що пояснює; оновлено лише живі посилання (сам label і цей звіт); закриті записи
(ledger, escalations, звіт і контракт 3б, label замороженого еталону 3б, твій дослівний
план) не переписувалися — зафіксовано записом `3b-finish-F2-baseline-name`, що заміщує
`3b-baseline-alias`. Жоден скрипт і жоден живий документ старого імені не вживав.

### 2.3 Сесії без нагляду (F3)
`session-claude.sh` викликає `claude -p … --permission-mode acceptEdits --output-format json`,
з коментарем чому (defaultMode лежить в особистому шарі, якого немає в проєкті і який не
читає хмара). **Перевірено:** `test_session_launch.py` 9/9 — справжній launcher у копії
`.claude/unattended/` у тимчасовому проєкті зі shim-ом `claude` на PATH, що записує argv і
відповідає як `--output-format json`; у argv є `-p <prompt>`, `--permission-mode acceptEdits`
двома сусідніми словами, `--output-format json`, нема `--dangerously-skip-permissions`;
відповідь shim-а лягла туди, куди лягла б справжня, і вартість із неї прочитана.

### 2.4 Особистий шар (F4)
`user/settings.json`: `defaultMode: "auto"` (легально лише на рівні user — саме туди шар і
зливається, `/docs/en/settings-reference`), ключа `env` немає зовсім (4 змінні моделей
прибрано, не перенесено), `additionalDirectories` і `WebFetch`/`WebSearch` лишилися.
`test_settings_proposal.py` тепер перелічує **кожну** задуману відмінність від замороженого
знімка «до» з причиною: `permissions.deny` (S4), `permissions.defaultMode` (F4),
`env.ANTHROPIC_DEFAULT_{SONNET,OPUS,HAIKU}_MODEL` (F4: закріплення старих моделей),
`env.CLAUDE_CODE_SUBAGENT_MODEL` (F4: не задокументовано), `hooks` (F5) — 7 тотожних, 6
задуманих, 10/10. Документи (`docs/tasks/README.md`, `TEMPLATE-SETUP.md`, `engine-limits.md`)
кажуть те саме. **Виміряно на твоїй машині (лише читання):** із застосованим S7 і ще не
застосованим S8 ефективні налаштування сьогодні **не мають** `defaultMode`, 7
`additionalDirectories` і дозволу `WebFetch`/`WebSearch` (parity: 3 відмінності, 4 тотожні) —
вони повернуться після `engine.py install --personal` (S8). Саме через це в цій сесії зникли
додаткові робочі теки.

### 2.5 Hook PermissionRequest для даних проєкту (F5)
`.claude/hooks/approve-project-data.py`: на подію PermissionRequest для Edit/Write/MultiEdit
відповідає `allow`, якщо шлях після `Path.resolve()` (символьні посилання й `..` розкрито)
лежить усередині `$CLAUDE_PROJECT_DIR/.claude/` **і** його власник за `.claude/ownership.txt`
— `project`. Інакше — нічого не вирішує (exit 0, порожній stdout). Ніколи не забороняє.
Матчер власності — копія `compile_pattern` з `engine.py` (двигун не постачає `engine.py`
у проєкти). Підключення — **пропозиція** в `docs/tasks/settings.json` (один handler у
`PermissionRequest`, більше нічого не змінено — `test_settings_proposal` це стверджує) з
командою в `docs/tasks/README.md`. **Тести:** `test_approve_project_data.py` 40/40 проти
тимчасового проєкту зі справжньою картою власності — 12 дозволів (project-дані відносним і
абсолютним шляхом, усі три інструменти, `..` що лишається всередині), 13 мовчань
(engine/machine/user/зовні), 7 втеч (`..` за межі `.claude/` і за межі проєкту, symlink-файл
і symlink-тека назовні, чужий `.claude/`, symlink **на** проєкт — розкривається і слушно
дозволяється), 8 «не моя справа». **Справжня перевірка** (`evals/probe_permission_hook.sh`,
Claude Code 2.1.287, haiku, ≈$0.02/сесія): A — hook підключено, запис у
`.claude/architecture/probe.md` **відбувся** («Done.», файл є, stdout hook-а — рішення allow);
B — hook підключено, запис у `src/probe.md` **відхилено**; C — без hook-а той самий запис, що в
A, **відхилено** («requires permission to create the sensitive file»). Два відкриття дорогою:
headless-сесія в теці, якій ніколи не давали trust інтерактивно, **ігнорує** `.claude/settings.json`
того проєкту, hook-и теж («Ignoring N permissions.allow entries … this workspace has not been
trusted») — тому зонд передає підключення через `--settings`; і `overseer/probe.md` за картою
— `engine` (у `overseer/` project-овані лише 5 іменованих файлів і `slice/`), тож перший
прогін побачив, як hook слушно мовчить.

### 2.6 Дрібниці (F6)
- `recheck_parked.py`: токени читаються лише з рядка `Unblocks when:` (`UNBLOCKS_RE`);
  `test_recheck_parked.py` 7/7 — згадка в Evidence чи в іншому рядку не резюмує, виконаний
  токен у правильному рядку резюмує, невиконаний — ні.
- `hook-checks/test_engine_lint.py`: `ruff check --isolated` + `mypy --strict` на Python,
  який карта власності називає `engine` (9 файлів); через `uvx`, інакше інструменти з PATH,
  інакше **FAIL** з причиною. Перший прогін знайшов 21 знахідку (runstate.py — голі `dict`,
  `Any`-повернення, затінена `node`; recheck_parked.py — `re.M`; test_selfref.py; doc_audit.py
  — тип повернення генератора) — усі виправлено, не приглушено. Додано в `AGENTS.md`.
- `test_engine_install.py`: порівняння hook-ів з HEAD пропускається зі списком брудних файлів і
  поясненням, якщо `.claude/hooks` має незакомічені зміни. Продемонстровано: тимчасово
  дописаний рядок у `env-check.sh` → `skip … M .claude/hooks/env-check.sh`; після відновлення — 49/49.
- `docs/engine-limits.md`: канонічний спосіб commit-у з небезпечними словами в повідомленні —
  `git commit -F <файл>` (hook бачить шлях, не текст), плюс еквіваленти для документації й
  тестів. Hook не послаблено.
- `critic-core.md` §0 і `feature-critic.md`: вимоги власника не переглядаються (неможлива —
  лише нотатка з доказами); рішення агента — переглядаються повністю; названо об'єкцію раунду 1
  пакету 3б, яка мала бути нотаткою.

### 2.7 Критерії «ГОТОВО»
- Усі набори зелені — так (25).
- Золотий набір тотожний еталону 3б, крім перелічених 3 відмінностей; новий еталон
  `evals/baseline/Laos-MacBook-Pro/results-package-3b-finish.json` — 87/87.
- ruff і mypy --strict чисті.
- Карта власності знає про нові файли: `approve-project-data.py` і `settings.user.json.template`
  — engine (постачаються); `probe_permission_hook.sh`, `test_engine_lint.py` — project;
  `test_ownership` 53/53.

## 3. Автономні рішення (escalations.md, AUTONOMOUS, CLOSED; час — `date -u`)

| id | рішення | чому не питав |
|---|---|---|
| `3b-finish-F1-user-scope-template` | окремий шаблон без hook-ів замість інструкції моделі «викинь ключ» | файл можна перевірити тестом; інструкцію — ні |
| `3b-finish-F2-baseline-name` | `results-package-3a-copy.json`; закриті записи не переписуються | це копія 3а; переписувати журнал — ламати append-only (критик #1) |
| `3b-finish-F5-no-decision-shape` | «немає рішення» = exit 0 + порожній stdout; дозвіл лише для `project`; зонд через `--settings` і ціль у `architecture/` | exit 1 показував би помилку на кожному звичайному записі; headless без trust ігнорує settings проєкту; `overseer/<довільне>` за картою — engine |
| `3b-finish-F6-lint-scope` | lint-перевірка судить лише `engine`-овані .py (не спайки в `artifacts/`); знахідки виправлено, не приглушено | карта каже, що є кодом двигуна; червоний спайк проєкту ламав би прогін усім |

## 4. Відкладене («лише за мною») — `parked.md`

**F8 — підключити hook** (потім перезапустити Claude Code; тест надрукує `APPLIED`):
```bash
cp docs/tasks/settings.json .claude/settings.json && python3 hook-checks/test_settings_proposal.py
```
**S8 — особистий шар у `~/.claude`** (бекап `~/.claude/settings.json.engine-backup-<UTC>` поруч;
поверне `defaultMode: auto`, 7 тек і WebFetch/WebSearch, яких зараз на машині немає):
```bash
python3 engine.py install --personal --ref unattended/2026-10-02-package-3b --dry-run
python3 engine.py install --personal --ref unattended/2026-10-02-package-3b
```
**S9 — зонд у хмарній сесії** на цьому репозиторії, вклей вивід:
```bash
bash .claude/unattended/env-probe.sh
```
Також за бажанням: `bash evals/probe_permission_hook.sh` у довіреному проєкті підтвердить, що
підключення через `.claude/settings.json` (а не `--settings`) спрацьовує так само.

## 5. Чого мені бракувало

1. **Trust робочої теки в headless-режимі.** Сесія `claude -p` в теці без інтерактивного trust
   ігнорує `.claude/settings.json` цього проєкту разом із hook-ами. Я не міг ні дати trust (це
   запис у `~/.claude.json`), ні запустити зонд у довіреному репозиторії (там діють його ж
   hook-и). Обхід — `--settings`. У двигуні варто: зонд із примітки перетворити на документовану
   процедуру «як перевірити hook у чистому проєкті» (зроблено в `probe_permission_hook.sh`).
2. **Карта власності й `overseer/`:** довільний файл під `.claude/overseer/` — `engine`. Для
   тимчасових нотаток агента правильне місце — `.claude/artifacts/`; це тепер у `engine-limits.md`.
   Якщо хочеш, щоб hook дозволяв будь-який запис в `overseer/`, це рядок у карті — твоє рішення.
3. **Критик знову витратив раунд** (~92k токенів) на обсяг фрази «усі посилання» — слушно, але
   це той тип зауваження, який §0 у `critic-core` тепер має утримувати в нотатках.
4. **Hook `block-dangerous.sh` і мої ж тексти** — як і минулого разу; цього разу без втрат,
   бо всі такі тексти йшли через Write/скрипти/`-F` (тепер задокументовано).
5. **`test_engine_lint` одразу червоний** через старі знахідки в `runstate.py` — виправлено, але це
   показує, що до цього раунду типізацію двигуна ніхто не перевіряв.
6. **Контекст машини:** після твого S7 і до S8 моя сесія втратила додаткові робочі теки
   (`~/.claude`, `/tmp/claude`) — передбачувано, але варто робити S7 і S8 разом.

## 6. Витрати і час

- Commit-и раунду: `11:44`–`12:11` локально (UTC+2) для F0–F6, F7 ≈ `12:15`; усього ≈ 35 хв
  роботи плюс ≈ 10 хв стартової перевірки.
- Субагенти: критик 2 раунди ≈ 92k + 61k ≈ 153k токенів.
- Справжні headless-сесії: 7 запусків (3 у першому проході, 4 у перевірці/контролі) ≈ $0.15 разом.
- Прогонів golden-набору: 5 (кожен — свіжий sandbox), по 1–2 хв.
- Основна сесія ≈ 150k токенів контексту за лічильником; долари — у `/cost`.
