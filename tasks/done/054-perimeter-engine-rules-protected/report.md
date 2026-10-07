# 054 — Захист .engine/rules.md у perimeter: звіт

## Що змінилось для власника
Файл `.engine/rules.md`, який потрапляє в always-loaded context кожної розмови, агент більше не може змінити сам — ні через Edit/Write/MultiEdit, ні shell-командою. Читати його можна, як і раніше. Єдиний законний запис — `lesson_queue.py promote`, який runner запускає поза сесією після вашого «так».

Зроблено в сесії з власником 2026-10-06; зміну власник схвалив до застосування. `.claude/settings.json` не змінювався.

## Демонстрація на хвилину
```bash
python3 tests/test_rules_file_protected.py | tail -1    # PASS 43   FAIL 0
python3 evals/run_hook_scenarios.py --engine-ref HEAD \
  --compare evals/baseline/linux-ubuntu-22.04/results-task-054.json | tail -1   # PASS 181/181
```

## Що зроблено
- **`.claude/hooks/protected-path-list.sh`** — один шаблон у `GUARDED_PATTERNS`. Список спільний для `protect-paths.sh` і `block-dangerous.sh` (задача 714), тож обидва hooks дістали захист однією зміною.
- **Документи:** `docs/engine-limits.md` (пункт у розділі про захищений шлях у shell-команді), `.claude/references/hooks.md`.
- **Задача 717** — до переліку файлів перевірки на Stop додано `.engine/rules.md`, із вимогою пропускати зміну, застосовану runner-ом; проставлено «Залежить від: 714» (ваша відповідь у тій задачі).
- **Нова задача 731** — скорочення, переписування чи видалення правила тим самим шляхом, що й `promote`, включно з чисткою застарілих рядків від self-learning-orchestrator. Ваше уточнення записано окремим розділом: сама зміна правила йде без сесії з вами; присутність власника стосується лише будування механізму, якщо воно зачіпає perimeter.

## Перевірено
- `tests/test_rules_file_protected.py` — 43 перевірки:
  - 19 shell-форм запису заблоковано, шлях названо в причині: `>`, `>>`, heredoc, `tee -a`, `sed -i`, `perl -pi`, `cp`, `mv` у файл і з нього, `rm`, `truncate`, `dd of=`, `open(…,"a")`, `write_text`, `git rm`, `git checkout <rev> --`, `git restore --source`, абсолютний шлях після `cd`, після іншої команди;
  - 5 — Edit, Write, MultiEdit, відносний шлях, вкладений проєкт: denied;
  - 14 законних shell-команд пройшли: `cat`, `grep`, `wc`, `git diff --`, `git log --`, `cp` із файла, `git checkout --`, `git restore`, запуск `lesson_queue.py promote`, запис у `.engine/lesson-queue.md`, `.engine/rule-proposals.md`, `docs/rules.md`, `.engine/old-rules.md`, `.claude/engine-rules.md`;
  - 5 — Edit/Write сусідніх файлів не заборонено.
- До зміни hooks пропускали всі 16 форм запису першої проби.
- Golden set: 181/181; 167 сценаріїв поводяться, як у `results-task-017.json`, 14 нових (9 для `block-dangerous.sh`, 5 для `protect-paths.sh`). Новий baseline `results-task-054.json`.
- Повний `bash tests/run_all.sh` — 73 suites зелені.
- Що `promote` вимагає вашої відповіді й відмовляє в сесії, тут не перевірялось наново: це тримає `tests/test_lesson_queue.py`, він зелений.

## Що варто знати
- **До задачі 731 скоротити чи прибрати правило агент не може взагалі.** `promote` відмовляє, коли always-loaded context переходить 200 рядків, і радить скоротити файл — цей шлях з'явиться лише з 731. Зараз у файлі жодного правила, тож межа далеко.
- **Не ловить** того самого, що й 714: шлях у змінній, запис зі скрипта, який команда лише запускає. Це закриває 717.
- **`.engine/rule-proposals.md` лишається відкритим** для запису: `promote` звіряє sha256 тексту з вашою відповіддю на task board.

## Commit-и
`742808d` (шаблон, тести, golden-сценарії, документи) і commit закриття задачі після нього, гілка `unattended/work`. Push не робився.

## Рішення, які я ухвалив сам
- **Окремий suite, а не доповнення `test_shell_protected_paths.py`:** файл стереже обидва hooks, і перевірка обох в одному місці читається простіше.
- **Suite поза fast-набором** (близько 13 с).
- **Задача пройшла повз `doing/`** — виняток власника для цієї сесії (задача 740).
