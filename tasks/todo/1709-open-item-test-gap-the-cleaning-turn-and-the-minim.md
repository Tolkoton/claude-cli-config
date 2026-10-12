# 1709 — Брак тесту (overseer): the cleaning turn and the minimum turn (attempt called from the two other places in board-runner.sh) with a session that changes a guarded file while the task is back in doing/: asserts the task is pa

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-cleaning-turn-and-the-minimum-turn-attempt-called-from-t-c1c3a02a

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T030239Z-df119a`) і знайшов брак тесту: only run_task reads PROTECTED after attempt; guard_session returns early when the task is in doing/, so from the other two callers the files are put back but nobody is asked Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T03:16:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the cleaning turn and the minimum turn (attempt called from the two other places in board-runner.sh) with a session that changes a guarded file while the task is back in doing/: asserts the task is parked or a question is opened»: тест червоніє на тому, що описано вище (only run_task reads PROTECTED after attempt; guard_session returns early when the task is in doing/, so from the other two callers the files are put back but nobody is asked), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
