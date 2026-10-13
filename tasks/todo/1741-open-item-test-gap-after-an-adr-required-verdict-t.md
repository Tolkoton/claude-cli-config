# 1741 — Брак тесту (overseer): after an ADR_REQUIRED verdict, the route message's own words about position are held: it says the entry is the newest / at the top of what `journal.py show ledger` prints (assert on the position phras

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-after-an-adr-required-verdict-the-route-message-s-own-words-9ac737a8

## Що сталося
Overseer прийняв юніт `-|762-open-item-test-gap-after-an-adr-required-verdict-i|unit 1` (PASS, запит `20261013T071648Z-abf129`) і знайшов брак тесту: a FRESH_ROUTE_REASON that names the right command but says the draft is 'at the bottom of' / 'the oldest entry of' its output: named_by() runs the command and the top entry is correct, so all three board 762 checks pass while the builder is told to look in the wrong place Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T07:20:51Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «after an ADR_REQUIRED verdict, the route message's own words about position are held: it says the entry is the newest / at the top of what `journal.py show ledger` prints (assert on the position phrase beside the followed command, with a ledger of three older entries)»: тест червоніє на тому, що описано вище (a FRESH_ROUTE_REASON that names the right command but says the draft is 'at the bottom of' / 'the oldest entry of' its output: named_by() runs the command and the top entry is correct, so all three board 762 checks pass while the builder is told to look in the wrong place), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
