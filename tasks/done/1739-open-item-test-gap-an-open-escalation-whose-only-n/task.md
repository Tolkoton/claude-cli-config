# 1739 — Брак тесту (overseer): an open escalation whose only named file was deleted by the task in `work` still refuses that task's PASS, and another task's accepted PASS records the file as held (or otherwise leaves the deletion u

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-an-open-escalation-whose-only-named-file-was-deleted-by-the-b023cafe

## Що сталося
Overseer прийняв юніт `-|301-gate-escalation-holds-only-its-own-work|unit 1` (PASS, запит `20261013T061751Z-4f47aa`) і знайшов брак тесту: today the lock covers nothing: gate_allows.changed_since / differs ignore a deleted file, so task A's own PASS is accepted while the escalation is open and board.py next offers it — reproduced on this tree and on a copy of HEAD (pre-existing, not introduced by board 301) Де: `tests/test_escalation_scope.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T06:24:03Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «an open escalation whose only named file was deleted by the task in `work` still refuses that task's PASS, and another task's accepted PASS records the file as held (or otherwise leaves the deletion unjudged) until the escalation is closed»: тест червоніє на тому, що описано вище (today the lock covers nothing: gate_allows.changed_since / differs ignore a deleted file, so task A's own PASS is accepted while the escalation is open and board.py next offers it — reproduced on this tree and on a copy of HEAD (pre-existing, not introduced by board 301)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
