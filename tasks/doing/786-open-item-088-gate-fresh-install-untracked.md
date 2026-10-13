# 786 — Stop gate блокує щойно встановлений двигун до першого commit-а

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 088-gate-fresh-install-untracked

## Що сталося
Задача 088 (fresh-install E2E). Після `engine.py install --ref HEAD` у порожній проєкт і до першого commit-а smoke-перевірка з docs/TEMPLATE-SETUP.md, крок 6 (`echo '{"stop_hook_active":false}' | bash .claude/hooks/verify-on-stop.sh`) друкує `gate[stop] 11 finding(s), exit 2` і decision block: bypass guard вважає «зміною» власні файли двигуна, які ще untracked — шість noqa в .claude/hooks/auto-approve-web.py і park-ask-gated.py, CODE_EXTENSIONS у .claude/project.env, .claude/ruff.toml. Перша сесія Claude Code, відкрита до commit-а встановлення, була б заблокована на Stop файлами, яких не писала. Та сама перевірка ще й кладе кандидата в чергу уроків проєкту (`bypass/noqa .claude/hooks/auto-approve-web.py:48`), і він потрапляє в перший commit. Після commit-а встановлення gate мовчить (exit 0).

- Записано: 2026-10-11T09:59:28Z, агент

## Що зробити
Спершу тест, червоний на свіжому встановленні без commit-а. Далі одне з двох: gate не судить файли, які за .claude/engine-lock.json є незміненими файлами двигуна (blob збігається), і seed-файли в їхньому початковому вигляді; або принаймні крок 6 у TEMPLATE-SETUP.md і рядок «next» у виводі engine.py кажуть закомітити встановлення до першої сесії й до smoke-перевірки. Раджу перше: друге лишає пастку.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
