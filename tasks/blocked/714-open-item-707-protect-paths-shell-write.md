# 714 — Захищені шляхи можна записати командою оболонки: protect-paths.sh бачить лише Edit/Write

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 707-protect-paths-shell-write

## Що сталося
Знайдено під час 707 (запис .engine/bugs/002-overseer-bash-edit.md, розділ 4). protect-paths.sh стоїть на PreToolUse лише для Edit|Write|MultiEdit, а block-dangerous.sh (Bash) захищених шляхів не знає. Перевірено подачею конверта в block-dangerous.sh — кожна з команд проходить (exit 0): printf x > .claude/constitution.md; echo {} > .claude/settings.json; sed -i s/a/b/ .github/workflows/ci.yml; python3 -c 'open(".claude/constitution.md","w").write("x")'; cat .env. Тобто «Hard-denied» з engine-rules.md (редагування конституції, налаштувань, міграцій, workflows; читання .env) тримається для оболонки лише на слові агента. Після факту запис у settings.json чи constitution.md видно в git diff, але жоден hook його не зупиняє.

- Записано: 2026-10-06T02:56:05Z, агент

## Що зробити
Спершу проєкт рішення у звіті, потім виправлення. Варіанти: (а) block-dangerous.sh відмовляє Bash-команді, текст якої називає захищений шлях разом із записом (>, >>, tee, sed -i, cp/mv у нього, open(…,'w')) або читанням .env — один перелік шляхів на обидва hook-и; (б) перевірка після факту на Stop: захищений файл змінився в дереві — хід блокується з вимогою повернути. Показати негативні випадки (git diff -- .claude/settings.json, grep у settings.json мають проходити). .claude/settings.json не правити: block-dangerous.sh уже підключений до Bash.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Чому зупинилась
- 2026-10-06T07:17:55Z — 3 спроб(и) поспіль не дали жодного commit-а; виконавець переніс задачу в `blocked/` і взяв наступну. Незакомічену роботу агента виконавець зберіг у гілці `wip/714-open-item-707-protect-paths-shell-write/20261006T071753Z` в origin (повернути в робоче дерево: `git fetch origin wip/714-open-item-707-protect-paths-shell-write/20261006T071753Z && git cherry-pick -n FETCH_HEAD`) і у сховку git на сервері виконавця (`git stash apply bb6b26b9c465e971cfa72af16b8dcfe729ed1b48`).

## Питання до власника
1. Задача застрягла: агент кілька спроб поспіль нічого не закомітив. Що робити далі? Будь-яка відповідь поверне задачу в чергу з новим лічильником спроб; вказівку агентові напишіть тут же.
   Відповідь:
