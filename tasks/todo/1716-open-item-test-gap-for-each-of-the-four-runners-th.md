# 1716 — Брак тесту (overseer): for each of the four runners, through the CLI: one session answered and one refused gives status `partial`, summary errors 1 and a non-zero exit status

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-for-each-of-the-four-runners-through-the-cli-one-session-ans-990bc87f

## Що сталося
Overseer прийняв юніт `-|725-open-item-eval-runners-failed-session-as-result|unit 1` (PASS, запит `20261012T054046Z-c44b55`) і знайшов брак тесту: the simplifier exits 0 in exactly this case today and every suite is green; the mix is tried only in-process on summary() and status(), never on main()'s exit status Де: `tests/test_eval_runners_failed_session.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T05:45:15Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «for each of the four runners, through the CLI: one session answered and one refused gives status `partial`, summary errors 1 and a non-zero exit status»: тест червоніє на тому, що описано вище (the simplifier exits 0 in exactly this case today and every suite is green; the mix is tried only in-process on summary() and status(), never on main()'s exit status), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
