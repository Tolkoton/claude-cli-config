# 1724 — Брак тесту (overseer): with only an ATTENDED task in doing/ (no ordinary one), `start --attended tasks/todo/<ordinary>.md` exits 0 and the ordinary task stands in doing/ beside the attended one; then `next --attended` still

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-only-an-attended-task-in-doing-no-ordinary-one-start-at-66166627

## Що сталося
Overseer прийняв юніт `-|740-open-item-board-start-attended-separate-clone|unit 1` (PASS, запит `20261012T073304Z-d26b7d`) і знайшов брак тесту: an implementation of cmd_start that takes board.files("doing") for an ordinary task started with --attended (refusing it beside ANY task, as before the fix) passes every check today: the only ordinary-with-flag case has the runner's task in doing/, where both rules refuse. The module text at .claude/unattended/board.py:133 says the side is the task's, and nothing asserts the allowing half of it Де: `tests/test_board.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T07:35:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with only an ATTENDED task in doing/ (no ordinary one), `start --attended tasks/todo/<ordinary>.md` exits 0 and the ordinary task stands in doing/ beside the attended one; then `next --attended` still prints the attended task, not the ordinary one»: тест червоніє на тому, що описано вище (an implementation of cmd_start that takes board.files("doing") for an ordinary task started with --attended (refusing it beside ANY task, as before the fix) passes every check today: the only ordinary-with-flag case has the runner's task in doing/, where both rules refuse. The module text at .claude/unattended/board.py:133 says the side is the task's, and nothing asserts the allowing half of it), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
