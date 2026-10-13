# 1747 — Брак тесту (overseer): a check that .claude/commands/owner-review.md no longer tells the session to number a new task by hand "below 800 (800 and up are rule questions and the gate's)" and instead names the classes of tasks

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-check-that-claude-commands-owner-review-md-no-longer-tells-a15116a9

## Що сталося
Overseer прийняв юніт `-|401-task-numbers-by-class-build|unit 2` (PASS, запит `20261013T175857Z-2bd4b7`) і знайшов брак тесту: the instruction at .claude/commands/owner-review.md:103 is wrong since S1 (the slice contract's «Deferred», line 419, says so and sets the trigger «before task 401 closes») and every suite is green with it; no test reads that sentence, so the task can close with the owner's review session numbering into class 7 Де: `tests/test_board.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T18:05:02Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a check that .claude/commands/owner-review.md no longer tells the session to number a new task by hand "below 800 (800 and up are rule questions and the gate's)" and instead names the classes of tasks/CLASSES.md (classes 7, 8, 9 not the owner's) or the unnumbered inbox file with a `Клас:` line»: тест червоніє на тому, що описано вище (the instruction at .claude/commands/owner-review.md:103 is wrong since S1 (the slice contract's «Deferred», line 419, says so and sets the trigger «before task 401 closes») and every suite is green with it; no test reads that sentence, so the task can close with the owner's review session numbering into class 7), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
