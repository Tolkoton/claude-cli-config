# 825 — Брак тесту (overseer): board.py reviewed-clean with HEAD detached at a clean commit while the branch ref given to the push holds an unrecorded number: exit 2

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-board-py-reviewed-clean-with-head-detached-at-a-clean-commit

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261011T162015Z-a15936`) і знайшов брак тесту: reviewed_clean judging HEAD instead of the ref that is pushed returns 0 Де: `tests/test_board.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T16:22:43Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «board.py reviewed-clean with HEAD detached at a clean commit while the branch ref given to the push holds an unrecorded number: exit 2»: тест червоніє на тому, що описано вище (reviewed_clean judging HEAD instead of the ref that is pushed returns 0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
