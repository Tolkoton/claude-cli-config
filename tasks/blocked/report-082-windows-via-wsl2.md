# 082 — «Windows через WSL2»: звіт (задача чекає вашої відповіді)

**Стан.** Усе, що задача просила збудувати, зроблено й закомічено; повний набір тестів зелений
(81 набір із 81). Задача лежить у `blocked/` з одним питанням: у документі цілей є пункт N1
«Підтримка Windows: поки що ні», і змінити його можна лише вашим «так».

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
- **Документ цілей не змінено.** Пропозиція поправки до N1 лежить у `.engine/goals/proposed.md`
  і чекає вашого «так».
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
- `python3 .claude/hooks/goals.py proposal` — «a lawful amendment: version 2 -> 3; changed or struck: N1».

## Витрати
Платних прогонів не було. Сесія агента — близько $1.7.

## Commit-и
`7fe57ea` (робота) і commit, що переносить задачу в `blocked/`.

## Відкладене
- Пройти `docs/WINDOWS.md` на справжній машині з Windows від початку до кінця. Це може зробити лише
  людина з такою машиною; що піде інакше — нова задача.
- Адреси встановлювачів `uv` і Claude Code в інструкції я записав з пам'яті й не перевіряв у мережі;
  поруч стоїть посилання на офіційну інструкцію Claude Code.
- Після вашого «так»: перевірити `goals.py status`, переглянути `.engine/goals/to-review.md`, якщо
  він з'явиться, і закрити задачу.

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
