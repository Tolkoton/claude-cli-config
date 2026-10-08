# 748 — Під Python 3.11 testing.py не парситься, хоча hooks пишуть «Python 3.11+»

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 602-python311-fstring

## Що сталося
Знайдено в задачі 602 під час прогону suites під трьома інтерпретаторами. .claude/hooks/testing.py:202: carried = f"<! -- row: {compact.replace('--', '-\\u002d')} -->\n" — backslash усередині виразу f-string дозволено лише з Python 3.12 (PEP 701). Під 3.11.17: SyntaxError: f-string expression part cannot include a backslash; tests/test_goals.py, tests/test_lesson_queue.py і tests/test_contract_fingerprint.py падають на 3.11 через імпорт testing.py. Водночас docstring-и hooks кажуть «Standard library only; Python 3.11+».

- Записано: 2026-10-08T18:49:52Z, агент

## Що зробити
Перевірити весь Python двигуна під 3.11 (python3.11 -m py_compile для кожного файлу поза tests/ і в tests/) і або виправити такі рядки, щоб 3.11 справді працював, або — якщо таких місць багато — поставити власникові питання, чи мінімальною версією стає 3.12, і тоді виправити рядки «Python 3.11+».

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
