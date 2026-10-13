# 763 — Брак тесту (overseer): fold then text() on a session file that holds text outside the entry format, still younger than KEEP_DAYS: the stray text appears exactly once

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-fold-then-text-on-a-session-file-that-holds-text-outside-the

## Що сталося
Overseer прийняв юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` (PASS, запит `20261010T072544Z-167382`) і знайшов брак тесту: after a fold the stray is stuck onto the last entry of the shared file and added again from the session file, so text() shows it twice Де: `tests/test_journal.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T07:49:44Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «fold then text() on a session file that holds text outside the entry format, still younger than KEEP_DAYS: the stray text appears exactly once»: тест червоніє на тому, що описано вище (after a fold the stray is stuck onto the last entry of the shared file and added again from the session file, so text() shows it twice), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
