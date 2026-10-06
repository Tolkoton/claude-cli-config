# 719 — Петля символьних посилань дає traceback у doc_audit.py та в скриптах evals/

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 718-resolve-loop-outside-hooks

## Що сталося
Знайдено другим аудитом виправлення 005 (.engine/bugs/005-resolve-loop-other-scripts.md, розділ 4): та сама причина — Path.resolve() на петлі символьних посилань піднімає RuntimeError до Python 3.12 включно — лишилась поза .claude/hooks, .claude/unattended та engine.py, які охопило виправлення 005. Відтворено наглядачем: .claude/skills/documentation/scripts/doc_audit.py:152 (посилання в Markdown на петлю: traceback; на відсутній файл — «broken link to …»); evals/run_audit_scenarios.py:649 (--tasks-dir <петля>: traceback; на відсутню теку — «refusing to start paid sessions: no task of this session is in …/doing/»). Та сама форма рядка, не перевірено запуском: evals/run_simplifier_evals.py:84 (tasks_dir.resolve()), evals/environment.py:78 (path.resolve() у try, що ловить лише ValueError), evals/run_hook_scenarios.py:115 і :210 (шлях зі сценарію; поруч є написана відмова SandboxError), :356 (--hooks-dir). Корінь пісочниці чи теки сценаріїв з командного рядка (run_audit_scenarios.py:387,709; run_gate_evals.py:168; run_hook_scenarios.py:116,211,216,349; doc_audit.py:54) — це корінь, а не шлях усередині нього: написаної відмови для нього немає. Наслідок усюди — traceback замість написаної відмови; платний прогін не починається, нічого не псується. На Python 3.13 і новіших resolve() без strict на петлі не піднімає нічого (документація pathlib).

- Записано: 2026-10-06T08:32:49Z, агент

## Що зробити
/bugfix: для кожного місця, де скрипт має написану відмову (doc_audit.py:152, run_audit_scenarios.py:649, run_simplifier_evals.py:84, environment.py:78, run_hook_scenarios.py:115, :210, :356), — тест (спершу червоний), що шлях-петля дає цю відмову, а не traceback; потім найменше виправлення (os.path.realpath замість resolve() або except RuntimeError, як у виправленні 005). Пошук тих самих місць — по всьому Python і shell репозиторію поза tests/: git ls-files | grep -v ^tests/ , рядки з «resolve(» — і в записі назвати кожен рядок. Якщо власник вважає це не вартим роботи — закрити без змін.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
