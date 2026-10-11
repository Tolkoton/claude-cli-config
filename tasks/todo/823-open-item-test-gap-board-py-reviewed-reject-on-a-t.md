# 823 — Брак тесту (overseer): board.py reviewed-reject on a tasks/.reviewed with invalid UTF-8: exit 0, the unrecorded number printed and removed from the file

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-board-py-reviewed-reject-on-a-tasks-reviewed-with-invalid-ut

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261011T154542Z-af0fbd`) і знайшов брак тесту: reviewed-reject exits 1 with a traceback (UnicodeDecodeError in _text), which the runner turns into an error stop with a push Де: `tests/test_board.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T15:48:00Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «board.py reviewed-reject on a tasks/.reviewed with invalid UTF-8: exit 0, the unrecorded number printed and removed from the file»: тест червоніє на тому, що описано вище (reviewed-reject exits 1 with a traceback (UnicodeDecodeError in _text), which the runner turns into an error stop with a push), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
