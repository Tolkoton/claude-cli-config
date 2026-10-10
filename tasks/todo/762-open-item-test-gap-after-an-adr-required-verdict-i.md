# 762 — Брак тесту (overseer): after an ADR_REQUIRED verdict is recorded, the file named in the Stop hook's route message holds that verdict's entry as its newest one (or the message names `journal.py show ledger`)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-after-an-adr-required-verdict-is-recorded-the-file-named-in-

## Що сталося
Overseer прийняв юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` (PASS, запит `20261010T072544Z-167382`) і знайшов брак тесту: a message that still says 'newest entry of .engine/overseer/ledger.md' while write_ledger writes .engine/journal/ledger/<session>.md; today every suite reads through journal_text and passes Де: `tests/test_overseer_fresh.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T07:49:44Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «after an ADR_REQUIRED verdict is recorded, the file named in the Stop hook's route message holds that verdict's entry as its newest one (or the message names `journal.py show ledger`)»: тест червоніє на тому, що описано вище (a message that still says 'newest entry of .engine/overseer/ledger.md' while write_ledger writes .engine/journal/ledger/<session>.md; today every suite reads through journal_text and passes), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
