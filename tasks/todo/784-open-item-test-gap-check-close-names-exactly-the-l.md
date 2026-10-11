# 784 — Брак тесту (overseer): check-close names exactly the last commit (and not the BLOCKed one) when an unaudited commit changes the same file AFTER the fix that got a PASS; and names only the unaudited commit when it changes th

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-check-close-names-exactly-the-last-commit-and-not-the-blocke

## Що сталося
Overseer прийняв юніт `-|754-open-item-test-gap-check-close-names-the-commit-of|unit 1` (PASS, запит `20261011T083503Z-861bd3`) і знайшов брак тесту: an implementation that treats a file as settled once any covered commit of the task touched it, whatever came later (e.g. `replaced` computed over all commits before the loop), passes 087–090 and lets unaudited code close the task Де: `tests/test_mode.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T08:48:33Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «check-close names exactly the last commit (and not the BLOCKed one) when an unaudited commit changes the same file AFTER the fix that got a PASS; and names only the unaudited commit when it changes th»: тест червоніє на тому, що описано вище (an implementation that treats a file as settled once any covered commit of the task touched it, whatever came later (e.g. `replaced` computed over all commits before the loop), passes 087–090 and lets unaudited code close the task), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
