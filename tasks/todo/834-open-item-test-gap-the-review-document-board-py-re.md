# 834 — Брак тесту (overseer): the review document (board.py review on a synthetic repository, as tests/test_board_review.py builds it) with extra-sessions.jsonl in its state: the «Зроблено» block of a task the runner led ends with

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-review-document-board-py-review-on-a-synthetic-repositor

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 3` (PASS, запит `20261011T213454Z-2685e2`) і знайшов брак тесту: done_section and task_line that no longer append extra_line(...) (.claude/unattended/board_review.py:313 and :428): the review goes silent about extra sessions and test_core_units (111/0), test_board_review (112/0) and test_board (303/0) stay green — today only the helper extra_line and task_costs are asserted (tests/test_core_units.py:719) Де: `tests/test_board_review.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T21:53:46Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the review document (board.py review on a synthetic repository, as tests/test_board_review.py builds it) with extra-sessions.jsonl in its state: the «Зроблено» block of a task the runner led ends with»: тест червоніє на тому, що описано вище (done_section and task_line that no longer append extra_line(...) (.claude/unattended/board_review.py:313 and :428): the review goes silent about extra sessions and test_core_units (111/0), test_board_review (112/0) and test_board (303/0) stay green — today only the helper extra_line and task_costs are asserted (tests/test_core_units.py:719)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
