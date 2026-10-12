# 1703 — Gates: bypass guard рахує рядки через splitlines і не бачить gate-allow після символу U+2028

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: gate-bypass-guard-splitlines

## Що сталося
gate.py guard_python бере source_lines = text.splitlines(), а номери коментарів дає tokenizer, який рахує лише newline. Якщо у файлі є літеральний символ, на якому splitlines ділить рядок (U+2028, U+2029, x0b, x0c, x85), від того місця рахунки розходяться на один, і justified() шукає gate-allow не в тому рядку: справжній gate-allow рядком вище не зараховується, хід блокується. Знайдено в задачі 401 на tests/test_task_class_table.py:305 і :786.

- Записано: 2026-10-12T02:00:58Z, агент

## Що зробити
Рахувати рядки так само, як tokenizer (text.split з newline або keepends), і додати негативний і позитивний випадок у tests/test_gate.py: файл із літеральним U+2028 вище за noqa з gate-allow рядком вище — знахідка justified; без gate-allow — block.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
