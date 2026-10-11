# 822 — Брак тесту (overseer): a fake agent commits tasks/.reviewed holding a number and an undecodable byte (b'777\n\xff\n'), then the runner pushes (stop after attempt; end of task; gate question): assert no commit the runner pus

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-fake-agent-commits-tasks-reviewed-holding-a-number-and-an-

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261011T154542Z-af0fbd`) і знайшов брак тесту: a guard that crashes on the file and an error stop that pushes anyway — today origin receives the number and every test is green Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T15:48:00Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a fake agent commits tasks/.reviewed holding a number and an undecodable byte (b'777\n\xff\n'), then the runner pushes (stop after attempt; end of task; gate question): assert no commit the runner pus»: тест червоніє на тому, що описано вище (a guard that crashes on the file and an error stop that pushes anyway — today origin receives the number and every test is green), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
