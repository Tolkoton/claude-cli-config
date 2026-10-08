# Звіт: 082 — Windows через WSL2

**Стан.** Задачу закрито. Усе, що вона просила збудувати, зроблено й закомічено раніше (`7fe57ea`);
на ваше «так» runner вніс поправку до N1 у документ цілей, і я перевірив результат.

## Що змінилось для власника
- **Є інструкція `docs/WINDOWS.md`.** Сім кроків від порожньої Windows до робочого двигуна:
  `wsl --install` і Ubuntu, інструменти (`git`, `jq`, `python3`, за потреби `uv`), налаштування git,
  проєкт у домашній теці Linux, Claude Code усередині WSL2, встановлення двигуна, перевірка. Окремо —
  робота через VS Code, таблиця типових пасток і чесний розділ про runner на Windows.
- **Двигун сам помічає WSL і дві пастки.** Hook `env-check.sh` на початку сесії каже, якщо проєкт
  лежить на диску Windows (`/mnt/c/...` — повільно і плутаються права файлів) або якщо git міняє
  закінчення рядків (`core.autocrlf` увімкнено — радить `input`). Коли все гаразд, він мовчить, як
  і раніше; на звичайному Linux і macOS нічого не змінилося.
- **У `docs/OWNER-GUIDE.md` з'явився розділ «Windows»,** а в `docs/TEMPLATE-SETUP.md` — розділ
  «Where it runs» з посиланням на інструкцію.
- **`.engine/goals.md` тепер версії 3 і запечатаний.** Поправку вніс runner на вашу відповідь «так»
  (2026-10-08T05:08:21Z, дія `amend-goals`); агент документа цілей не редагував. Змінено лише N1:
  не робимо *нативну* Windows (Git Bash, PowerShell), а всередині WSL2 двигун працює. У розділі
  «Зміни» з'явився рядок про v3. Переглядати наново нічого не треба: жодне рішення архітектора на
  N1 не посилається, тому `.engine/goals/to-review.md` не з'явився.
- **На справжній Windows інструкцію ніхто не пройшов.** Сервер — Linux; розпізнавання WSL перевірено
  на підроблених ознаках. Це написано і в самій інструкції.

## Демонстрація на хвилину
```
$ printf '[core]\n\tautocrlf = true\n' > /tmp/h/.gitconfig
$ echo "Linux version 5.15-microsoft-standard-WSL2" > /tmp/h/v
$ HOME=/tmp/h GIT_CONFIG_NOSYSTEM=1 ENGINE_PROC_VERSION=/tmp/h/v CLAUDE_PROJECT_DIR=/mnt/c/work/shop bash .claude/hooks/env-check.sh
## engine environment check — WSL
- the project is on a Windows disk (/mnt/c/work/shop) — from WSL every git command and test run there is many times slower, and file permissions are not kept: …
- git core.autocrlf is on — git rewrites line endings to CRLF on checkout, and a hook script with CRLF does not run … Set `git config --global core.autocrlf input`, then check the project out again.
Tell the user about the items above: the engine's docs/WINDOWS.md has the steps.

$ bash .claude/hooks/env-check.sh        # цей сервер, звичайний Linux
$                                        # порожньо

$ python3 .claude/hooks/goals.py status
.engine/goals.md is the document the owner approved
$ python3 .claude/hooks/goals.py proposal
no amendment is proposed (.engine/goals/proposed.md absent)
$ python3 .claude/hooks/goals.py affected N1
$                                        # порожньо: N1 ніхто не цитує
```

## Перевірка
- `tests/test_env_check.py`: 20 перевірок із 20 (було 8). Дванадцять нових — на підроблених ознаках
  WSL: рядок ядра (WSL2 і старіший, з великої літери), шлях проєкту, налаштування git. П'ять із них
  до зміни hook-а були червоні з потрібної причини. Є негативні випадки: звичайний Linux з тим самим
  шляхом і тим самим налаштуванням git мовчить; `/mnt/data` не вважається диском Windows;
  `core.autocrlf=input` мовчить; без `/proc/version` (macOS) hook мовчить і не падає.
- Повний набір: `bash tests/run_all.sh` — 81 набір із 81 зелений. Перший запуск обірвався на межі
  часу без результату, другий дійшов до кінця.
- Stop gate один раз був червоний: `test_no_machine_paths.py` прийняв мій вигаданий шлях із
  `/Users/<ім'я>/` за шлях конкретної машини. Шлях у тесті замінено на `/mnt/c/work/shop`.
- `python3 .claude/hooks/goals.py proposal` (до вашої відповіді) — «a lawful amendment: version 2 -> 3;
  changed or struck: N1».
- **Після дії runner-а.** Документ у робочому дереві збігається з пропозицією, про яку вас питали,
  байт у байт (`git show HEAD:.engine/goals/proposed.md | diff - .engine/goals.md` — порожньо); текст N1 —
  той самий, що стоїть у питанні 1 задачі. `git diff` документа: рядок `Версія`, рядок N1 і новий
  рядок у «Зміни» — більше нічого. Запечатано саме версію 3: записаний відбиток
  (`.claude/state/goals/goals.sha256`, `1059ddc1…`) дорівнює sha256 нинішнього файла і не дорівнює
  sha256 версії 2 (`5262b816…`).
- У цій сесії код двигуна не змінювався. `tests/test_env_check.py` — 20 із 20; повний набір
  наприкінці задачі: `bash tests/run_all.sh` — 82 набори з 82 зелені.

## Витрати
Платних прогонів не було. Перша сесія агента — близько $1.7, сесія закриття — близько $1.

## Commit-и
`7fe57ea` (робота) … `9589585` (задача в `blocked/`) … `6266e33` (runner: дію виконано) … commit цієї
сесії `board: 082-windows-via-wsl2 → done`. У ньому ж — зміна `.engine/goals.md` і видалення
`.engine/goals/proposed.md`, які runner лишив у робочому дереві.

## Відкладене
- Пройти `docs/WINDOWS.md` на справжній машині з Windows від початку до кінця. Це може зробити лише
  людина з такою машиною; що піде інакше — нова задача.
- Адреси встановлювачів `uv` і Claude Code в інструкції я записав з пам'яті й не перевіряв у мережі;
  поруч стоїть посилання на офіційну інструкцію Claude Code.
- `goals.py check` без аргументів повертає код 3: дев'ять старих документів
  `.engine/architecture/feature/engine-package-*.md` не мають розділу «Звірка з цілями». Вони
  написані до появи документа цілей і з цією поправкою не пов'язані (так само було у звіті 096);
  нічого не чіпав.
- Рядок про v3 у розділі «Зміни» має дату 2026-10-07 — день, коли пропозицію написано; runner вніс її
  2026-10-08. Текст — саме той, який ви схвалили, тому я його не правив.

## Рішення, які я ухвалив сам
- **«Згадка в README» стоїть у `docs/TEMPLATE-SETUP.md`.** Кореневого `README.md` у репозиторії
  немає; посібник зі встановлення — це те, що читає інженер першим. `.claude/README.md` — карта
  агентів, і вона копіюється в кожен проєкт, де `docs/WINDOWS.md` немає.
- **Інструкція українською,** як `docs/OWNER-GUIDE.md`; повідомлення hook-а — англійською, як решта
  його повідомлень.
- **Попередження лише про `core.autocrlf`, що дорівнює `true`.** Невстановлене значення на Linux
  нічого не переписує, тож hook про нього мовчить.
- **Диск Windows впізнається за шляхом** `/mnt/<одна літера>/`, а не за типом файлової системи:
  простіше і перевіряється без справжнього WSL.
- **WSL1 hook не відрізняє від WSL2:** рядок ядра для цього ненадійний. Перевірка версії
  (`wsl -l -v`) є в інструкції.
- **Встановлювачі в інструкції завантажуються у файл, а не подаються одразу в shell** — так само,
  як правила двигуна вимагають від агента.
- **N1 переписано на місці, а не закреслено:** пункт лишається чинним для нативної Windows, номер той самий.
- **Тестова змінна `ENGINE_PROC_VERSION`** дає тестам підставити рядок ядра замість `/proc/version`.
- **Закомітив зміну документа цілей і видалення пропозиції разом із закриттям задачі:** це результат
  дії runner-а (його commit `6266e33` містить лише файл задачі), а задача має закритися з чистим
  робочим деревом. Так само зроблено в задачі 096.
