# 1765 — Брак тесту (overseer): a supersede round that settles a parked slice whose open item the owner has already answered: asserts that the item stays in blocked/, and asserts what the ledger's unparked entry says about it (or th

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-supersede-round-that-settles-a-parked-slice-whose-open-ite-e9ea6e25

## Що сталося
Overseer прийняв юніт `-|304-parked-slice-superseded-by-new-contract|unit 1` (PASS, запит `20261024T144335Z-104c46`) і знайшов брак тесту: the ledger's unparked entry says 'none waited unanswered' and the slice runs on while the owner's answer stays unread in blocked/; no test pins what should happen to that answer Де: `tests/test_testing_supersede.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-24T17:47:30Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a supersede round that settles a parked slice whose open item the owner has already answered: asserts that the item stays in blocked/, and asserts what the ledger's unparked entry says about it (or that the slice is not unparked)»: тест червоніє на тому, що описано вище (the ledger's unparked entry says 'none waited unanswered' and the slice runs on while the owner's answer stays unread in blocked/; no test pins what should happen to that answer), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
