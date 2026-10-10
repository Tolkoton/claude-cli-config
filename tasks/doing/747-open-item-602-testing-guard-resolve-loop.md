# 747 — testing.py guard: symlink loop у file_path дає traceback до Python 3.12

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 602-testing-guard-resolve-loop

## Що сталося
Знайдено пошуком тих самих місць у виправленні 006 (.engine/bugs/006-py313-symlink-loop.md, розділ 4). .claude/hooks/testing.py:951 (guard, PreToolUse hook для slice-tester): Path(target).resolve() без try. На Python 3.11 і 3.12 file_path, що є symlink loop, дає RuntimeError, тобто traceback у hook-у з exit 1. PreToolUse hook з exit 1 не блокує, тож guard пропускає цей виклик без рішення; сам запис через loop однаково падає з ELOOP. На 3.13 traceback немає. Цей рядок з'явився в задачі 062 того самого дня, що й виправлення 005, і в список запису 005 не потрапив.

- Записано: 2026-10-08T18:49:42Z, агент

## Що зробити
/bugfix: тест (спершу червоний), що tester-ів Write/Edit у file_path-loop отримує звичайне рішення guard-а, а не traceback. Червоний він буде лише під Python 3.12 або 3.11, тож доказ — bugfix.py prove --cmd "python3.12 tests/…" (python3.12 є на сервері двигуна). Найменше виправлення — os.path.realpath() замість resolve(), як у goals.py:350.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
