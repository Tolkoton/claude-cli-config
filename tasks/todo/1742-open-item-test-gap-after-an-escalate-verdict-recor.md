# 1742 — Брак тесту (overseer): after an ESCALATE verdict recorded over a ledger with three older entries, what the Stop hook's route message names (the `journal.py show ledger` command, else the file) holds that request's OVERSEER_

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-after-an-escalate-verdict-recorded-over-a-ledger-with-three-63e3fe2b

## Що сталося
Overseer прийняв юніт `-|762-open-item-test-gap-after-an-adr-required-verdict-i|unit 1` (PASS, запит `20261013T071648Z-abf129`) і знайшов брак тесту: ESCALATE uses the same FRESH_ROUTE_REASON, but only ADR_REQUIRED is followed to the ledger; an escalation entry written without its question/options, or a route for ESCALATE split off with the old 'newest entry of .engine/overseer/ledger.md' wording, passes today's board 762 checks Де: `tests/test_overseer_fresh.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T07:20:51Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «after an ESCALATE verdict recorded over a ledger with three older entries, what the Stop hook's route message names (the `journal.py show ledger` command, else the file) holds that request's OVERSEER_ESCALATE entry with the escalation as its top entry»: тест червоніє на тому, що описано вище (ESCALATE uses the same FRESH_ROUTE_REASON, but only ADR_REQUIRED is followed to the ledger; an escalation entry written without its question/options, or a route for ESCALATE split off with the old 'newest entry of .engine/overseer/ledger.md' wording, passes today's board 762 checks), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
