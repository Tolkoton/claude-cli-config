# 824 — Брак тесту (overseer): a fake agent commits a number into tasks/.reviewed on the work branch and leaves the branch (detached HEAD at the commit before, or another branch), then the runner pushes — stop after the attempt, an

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-fake-agent-commits-a-number-into-tasks-reviewed-on-the-wor

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261011T162015Z-a15936`) і знайшов брак тесту: a push check that reads HEAD while `git push` sends $BRANCH — today origin's unattended/work:tasks/.reviewed is '777\n' and all 309 checks are green Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T16:22:43Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a fake agent commits a number into tasks/.reviewed on the work branch and leaves the branch (detached HEAD at the commit before, or another branch), then the runner pushes — stop after the attempt, an»: тест червоніє на тому, що описано вище (a push check that reads HEAD while `git push` sends $BRANCH — today origin's unattended/work:tasks/.reviewed is '777\n' and all 309 checks are green), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
