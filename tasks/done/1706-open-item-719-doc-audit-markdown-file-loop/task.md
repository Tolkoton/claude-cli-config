# 1706 — doc_audit.py: файл Markdown, що сам є symlink loop, дає traceback

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 719-doc-audit-markdown-file-loop

## Що сталося
Знайдено під час виправлення 008 (.engine/bugs/008-resolve-loop-outside-hooks.md, розділ 4), інша причина, ніж у задачі 719: .claude/skills/documentation/scripts/doc_audit.py знаходить файли через rglob("*.md") (iter_markdown) і читає кожен через read_text(); файл loop.md -> loop.md дає «OSError: [Errno 40] Too many levels of symbolic links» з check_links — traceback, exit 1, жодного рядка звіту. resolve() тут ні до чого, тому виправлення 008 цього не торкалось. Те саме з будь-яким .md, який не читається (немає прав, broken symlink на теку тощо): читачів три — check_links, check_adrs, check_make_targets. Написаної очікуваної поведінки для такого файлу немає ніде (docstring скрипта перелічує п'ять перевірок, про нечитаний файл — нічого). Наслідок малий: скрипт лише читає, нічого не псується; audit документації не видає звіту, доки loop лежить у репозиторії.

- Записано: 2026-10-12T02:11:28Z, агент

## Що зробити
/bugfix. Очікуваної поведінки ніде не написано, тож спершу її треба назвати: порада агента — iter_markdown пропускає те, що не є файлом (is_file() для loop дає False), і скрипт пише WARN «<шлях> - not a readable file, skipped»; це two-way door, записати як рішення в bug record. Тест (спершу червоний) — поруч із наявними у tests/test_symlink_loop_outside_hooks.py. Якщо власник вважає це не вартим роботи — закрити без змін.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
