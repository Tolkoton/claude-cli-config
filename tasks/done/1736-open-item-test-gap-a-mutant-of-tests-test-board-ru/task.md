# 1736 — Брак тесту (overseer): a mutant of tests/test_board_runner.py's own subject: with the `seal-goals` entry removed from OWNER_ACTIONS (or from ACTION_FILES) in board.py, the scenario «the owner answered «так»: the document is

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-mutant-of-tests-test-board-runner-py-s-own-subject-with-th-ff1eba8c

## Що сталося
Overseer прийняв юніт `-|787-open-item-088-first-goals-seal-unattended|unit 1` (PASS, запит `20261013T041616Z-02a931`) і знайшов брак тесту: the turn states no mutant was run against the runner suite; the four scenarios were seen green only, so a runner that never hands the action over is shown caught by reading the assertions, not by a failing run Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T04:39:16Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a mutant of tests/test_board_runner.py's own subject: with the `seal-goals` entry removed from OWNER_ACTIONS (or from ACTION_FILES) in board.py, the scenario «the owner answered «так»: the document is sealed, by the runner» goes red»: тест червоніє на тому, що описано вище (the turn states no mutant was run against the runner suite; the four scenarios were seen green only, so a runner that never hands the action over is shown caught by reading the assertions, not by a failing run), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
