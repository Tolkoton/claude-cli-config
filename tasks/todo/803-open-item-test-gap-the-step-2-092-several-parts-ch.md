# 803 — Брак тесту (overseer): the 'step 2 (092)' several-parts check asserts that the part with no check is the first question, and that it goes into the risk zones as «no check ran» and into the premise log

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-step-2-092-several-parts-check-asserts-that-the-part-wit

## Що сталося
Overseer прийняв юніт `-|092-onboard-unattended-and-fresh-reader|unit 1` (PASS, запит `20261011T121803Z-a3aa5d`) і знайшов брак тесту: deleting ', and that part is the first question' or ', and that part goes into the risk zones as «no check ran» and into the premise log (step 8)' leaves the suite at 81/0: the snapshot is then taken with nothing recording which part it does not measure; likewise the profile template's 'if one part of the project ran none, name that part here' can be deleted with 81/0 Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:30:22Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'step 2 (092)' several-parts check asserts that the part with no check is the first question, and that it goes into the risk zones as «no check ran» and into the premise log»: тест червоніє на тому, що описано вище (deleting ', and that part is the first question' or ', and that part goes into the risk zones as «no check ran» and into the premise log (step 8)' leaves the suite at 81/0: the snapshot is then taken with nothing recording which part it does not measure; likewise the profile template's 'if one part of the project ran none, name that part here' can be deleted with 81/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
