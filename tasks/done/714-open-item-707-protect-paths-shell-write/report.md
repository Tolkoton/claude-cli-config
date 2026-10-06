# 714 — Захищені шляхи через shell: звіт

## Що змінилось для власника
Команда оболонки більше не може записати в захищений файл і не може прочитати секрет. Раніше `protect-paths.sh` стеріг ці шляхи лише від Edit/Write, а `block-dangerous.sh` (Bash) списку не знав: запис у конституцію чи спільні налаштування і читання env-файла проходили. Тепер обидва hooks читають один список, і Bash-команда, що пише в захищений шлях або називає секрет, дістає відмову з поясненням. Читати guarded-файли (конституцію, налаштування, workflows, міграції) можна, як і раніше.

Зроблено в сесії з власником 2026-10-06; зміну власник схвалив словом «так» до застосування. `.claude/settings.json` не змінювався: hook уже підключений до Bash.

## Демонстрація на хвилину
```bash
python3 tests/test_shell_protected_paths.py | tail -1      # PASS 112   FAIL 0
python3 evals/run_hook_scenarios.py --engine-ref HEAD \
  --compare evals/baseline/linux-ubuntu-22.04/results-task-714.json | tail -1   # PASS 143/143
```
Наживо hook двічі зупинив і цю сесію: heredoc із переліком проб і commit message, що згадував назву dotfile зі списку. Це описаний false positive (нижче), обхід — текст у файл через Write або без назви шляху.

## Що зроблено
- **`.claude/hooks/protected-path-list.sh` (новий)** — єдиний список: `SECRET_PATTERNS` (заборонено писати й читати), `GUARDED_PATTERNS` (читати можна, писати ні), `ALLOWED_PATTERNS` (`.claude/project.env`, застарілий `index.lock` у `.git/`). Шаблони тек і dotfiles стали `(^|/)name`: відносний шлях від кореня проєкту раніше не збігався.
- **`.claude/hooks/shell_paths.py` (новий)** — розбирає команду, одне зі слів якої збіглося зі списком. Запис: ціль `>`/`>>`, `tee`, `rm`, `mv`, `truncate`, `touch`, `chmod`, останній аргумент `cp`/`ln`/`install`, `sed -i`/`perl -i`, `dd of=`, `--output`, `curl -o`, `git rm`/`git mv`, `git checkout <rev> --`/`git restore --source`, у вбудованому коді `open()` з режимом запису, `write_text()`, `writeFileSync()`, `os.replace()`, `shutil.copy()`.
- **`.claude/hooks/block-dangerous.sh`** — викликає перевірку після `DANGEROUS_PATTERNS`; **`protect-paths.sh`** — список винесено, логіка та сама.
- **Fail-closed:** без `python3` команда, що називає захищений шлях, відхиляється цілком; без файла списку обидва hooks відхиляють кожен виклик.
- **Документи:** `docs/engine-limits.md` (розділ «A protected path in a shell command»), `.claude/references/hooks.md`, `permission-philosophy.md`.

Із гілки `wip/714-…/20261006T071753Z` узято все, крім `.engine/lesson-queue.md` і `.engine/overseer/ledger.md` (записи нічного прогону).

## Перевірено
- `tests/test_shell_protected_paths.py` — 112 перевірок, 0 провалів.
- Окрема проба через живий hook у цьому клоні — 44 із 44:
  - 27 форм обходу заблоковано: `>` і `>>`, `tee`, `cp`, `mv`, `rm`, `truncate`, `dd of=`, `curl -o`, `sed -i`, `perl -pi`, `git rm`, `git checkout <rev> --`, `git restore --source`, `python3 -c` з `open(…,"w")` і `write_text`, `node -e` з `writeFileSync`, `bash -c '…; rm …'`, запис у `.git/config`, читання env-файлів, ключа SSH, `secrets/`, AWS credentials;
  - 17 законних команд пройшли: `git diff --`, `grep` і `cat` guarded-файла, `cp` із нього, `git checkout --`, `git restore`, `rm -f .git/index.lock`, запис у `.claude/project.env`, `jq .key`, `process.env`, `ls` теки workflows, `git log --`, звичайні тести, `sed -i` звичайного файла.
- Golden set: 143/143 проходять свої очікування; 135 старих сценаріїв поводяться так само, як у `results-task-039.json`, 8 нових (5 block, 3 allow) додано. Записано новий baseline `results-task-714.json`, на нього тепер посилаються `docs/working-on-the-engine.md` і `evals/README.md`.
- Повний `bash tests/run_all.sh` — 71 suite зелений.
- `ruff` і `mypy` окремо не запускались.

## Чого це не ловить
- Шлях у змінній або складений із частин, `cd dir` і потім гола назва файла, запис зі скрипта, який команда лише запускає, `xargs`. PreToolUse hook має лише текст команди. Ці форми закриває задача **717** (перевірка на Stop), яка тепер розблокована.
- **Відмова без шкоди:** команда, що лише цитує такий запис чи назву секрету в повідомленні (heredoc, commit message, `--what` для дошки).

## Commit-и
`c808107` (зміна, тести, golden-сценарії, документи) і commit закриття задачі після нього, гілка `unattended/work`. Push не робився.

## Рішення, які я ухвалив сам
- **Новий baseline golden set.** Без нього порівняння з `results-task-039.json` щоразу показувало б 8 відмінностей. Звіт 041 (release audit) порівнював зі старим — його цифра 135/135 лишається правдивою для того моменту.
- **Задача пройшла повз `doing/`** — виняток, дозволений власником у сесії: `doing/` тримав runner (013). Про саму ваду дошки заведено задачу **730**.
