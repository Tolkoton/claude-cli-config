# 1737 — Брак тесту (overseer): with an ordinary (not attended) task in doing/ and a cleanup task in todo/, `board.py summary` does not print «чекає, поки закриється задача з присутнім власником: <cleanup>», and `board.py start <cle

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-an-ordinary-not-attended-task-in-doing-and-a-cleanup-ta-d9292a43

## Що сталося
Overseer прийняв юніт `-|838-open-item-108-cleanup-in-todo-beside-attended|unit 1` (PASS, запит `20261013T051625Z-e0eebb`) і знайшов брак тесту: `held_cleanup` reading `self.files("doing")` instead of `self.in_hand(True)` — any task in doing/ counted as the owner's attended one — leaves tests/test_cleanup.py at PASS 49 FAIL 0 (mutant M4 in /tmp/audit-copy-838), while the summary would tell the owner a cleanup task waits for an attended task that does not exist Де: `tests/test_cleanup.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T05:32:19Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with an ordinary (not attended) task in doing/ and a cleanup task in todo/, `board.py summary` does not print «чекає, поки закриється задача з присутнім власником: <cleanup>», and `board.py start <cleanup>` is refused with the «one task at a time» message, not the cleanup-waits message»: тест червоніє на тому, що описано вище (`held_cleanup` reading `self.files("doing")` instead of `self.in_hand(True)` — any task in doing/ counted as the owner's attended one — leaves tests/test_cleanup.py at PASS 49 FAIL 0 (mutant M4 in /tmp/audit-copy-838), while the summary would tell the owner a cleanup task waits for an attended task that does not exist), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
