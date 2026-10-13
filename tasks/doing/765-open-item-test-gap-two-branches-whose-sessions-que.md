# 765 — Брак тесту (overseer): two branches whose sessions queue the same lesson candidate (same source and essence, so the same id) on different dates: after the merge, lesson_queue.entries() lists the id once

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-two-branches-whose-sessions-queue-the-same-lesson-candidate-

## Що сталося
Overseer прийняв юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` (PASS, запит `20261010T092308Z-b56fee`) і знайшов брак тесту: today journal.open_candidates keeps both lines, because they differ by date. Probe /tmp/ov739d/probe/p2.py prints 'queue entries: 2 [9b8f1577, 9b8f1577]', so `lesson_queue.py list` and the LESSON_REVIEW count show one candidate twice. Task 739 asked that every reader be checked for duplicates, and no test tries this one Де: `tests/test_journal.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-10T09:48:29Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «two branches whose sessions queue the same lesson candidate (same source and essence, so the same id) on different dates: after the merge, lesson_queue.entries() lists the id once»: тест червоніє на тому, що описано вище (today journal.open_candidates keeps both lines, because they differ by date. Probe /tmp/ov739d/probe/p2.py prints 'queue entries: 2 [9b8f1577, 9b8f1577]', so `lesson_queue.py list` and the LESSON_REVIEW count show one candidate twice. Task 739 asked that every reader be checked for duplicates, and no test tries this one), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
