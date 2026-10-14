# 791 — Runner у новому проєкті: Claude Code ігнорує allow-правила, доки теку не позначено довіреною

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 088-runner-untrusted-workspace

## Що сталося
Задача 088 (fresh-install E2E). Перша сесія runner-а в щойно створеному проєкті написала в stderr (.claude/state/board/logs/010-todo-cli-1.json.err): «Ignoring 13 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. Run Claude Code interactively here once and accept the trust dialog, or set projects[…].hasTrustDialogAccepted: true in ~/.claude.json». Задача все одно пройшла (`--permission-mode auto`), але 13 allow-правил двигуна в такому проєкті не діють, і ніде про це не сказано: ні в docs/TEMPLATE-SETUP.md, ні в .claude/unattended/README.md, ні в підсумку runner-а. Файл .err ніхто не читає.

- Записано: 2026-10-11T09:59:28Z, агент

## Що зробити
У TEMPLATE-SETUP.md (крок 7) і в .claude/unattended/README.md написати: перед першим запуском runner-а відкрити Claude Code в проєкті один раз і прийняти діалог довіри. Runner-ові: якщо в .err сесії є цей рядок — запис у журнал аномалій (один раз на проєкт) і рядок у підсумку. Перевірити тестом із shim-ом claude, що друкує цей рядок у stderr.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
