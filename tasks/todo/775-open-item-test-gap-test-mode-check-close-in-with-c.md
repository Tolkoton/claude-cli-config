# 775 — Брак тесту (overseer): test_mode, check-close in соло with CODE_EXTENSIONS and SOURCE_DIRS empty: a task whose commit changed only sketches/rate/probe.py and its report closes with nothing missing (no overseer PASS asked fo

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-test-mode-check-close-in-with-code-extensions-and-source-dir

## Що сталося
Overseer прийняв юніт `-|099-modes-sketch|unit 1` (PASS, запит `20261011T061554Z-cefbce`) і знайшов брак тесту: removing "sketches/" from RECORDS at .claude/hooks/mode.py:96 keeps test_mode at 97/0 (mutant run in /tmp/ov099x/m); the docstring's «never under tasks/, .engine/ or sketches/» is held by no test, and a task that carries a sketch file would be turned back for an audit the design does not ask for Де: `tests/test_mode.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-11T06:28:14Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «test_mode, check-close in соло with CODE_EXTENSIONS and SOURCE_DIRS empty: a task whose commit changed only sketches/rate/probe.py and its report closes with nothing missing (no overseer PASS asked fo»: тест червоніє на тому, що описано вище (removing "sketches/" from RECORDS at .claude/hooks/mode.py:96 keeps test_mode at 97/0 (mutant run in /tmp/ov099x/m); the docstring's «never under tasks/, .engine/ or sketches/» is held by no test, and a task that carries a sketch file would be turned back for an audit the design does not ask for), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
