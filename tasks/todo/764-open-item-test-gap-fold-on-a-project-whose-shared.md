# 764 — Брак тесту (overseer): fold on a project whose shared ledger holds no entry yet (the template), with a session file holding hand-written text plus one entry of today: after the fold, journal.text shows that entry exactly on

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-fold-on-a-project-whose-shared-ledger-holds-no-entry-yet-the

## Що сталося
Overseer прийняв юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` (PASS, запит `20261010T081516Z-f002d8`) і знайшов брак тесту: merged() sorts the stray text after the young entry, so the shared file's copy becomes 'entry + stray' and the session file's clean copy is added again. Probe /tmp/ov739c/probe/p1.py prints 'case1 after fold: entry 2', and passes_in_a_row would count that PASS twice. Today's test seeds an older shared entry, so the stray sticks to that one and the duplicate never shows Де: `tests/test_journal.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-10T08:55:57Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «fold on a project whose shared ledger holds no entry yet (the template), with a session file holding hand-written text plus one entry of today: after the fold, journal.text shows that entry exactly on»: тест червоніє на тому, що описано вище (merged() sorts the stray text after the young entry, so the shared file's copy becomes 'entry + stray' and the session file's clean copy is added again. Probe /tmp/ov739c/probe/p1.py prints 'case1 after fold: entry 2', and passes_in_a_row would count that PASS twice. Today's test seeds an older shared entry, so the stray sticks to that one and the duplicate never shows), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
