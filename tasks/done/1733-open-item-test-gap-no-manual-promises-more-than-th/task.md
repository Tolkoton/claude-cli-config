# 1733 — Брак тесту (overseer): no manual promises more than the limits section: assert for tasks/README.md, templates/project/tasks/README.md, .claude/unattended/README.md, docs/OWNER-GUIDE.md and .claude/commands/owner-review.md t

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-no-manual-promises-more-than-the-limits-section-assert-for-t-e803b217

## Що сталося
Overseer прийняв юніт `-|100-modes-reader-for-documents|unit 1` (PASS, запит `20261013T010504Z-1364da`) і знайшов брак тесту: a manual that keeps the pointer to «The same Linux user» and again says the runner never sends a commit holding such a number passes today's checks: they look for the section's name and the path, and exclude «sends nothing» in docs/engine-limits.md only Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T01:21:24Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «no manual promises more than the limits section: assert for tasks/README.md, templates/project/tasks/README.md, .claude/unattended/README.md, docs/OWNER-GUIDE.md and .claude/commands/owner-review.md that the sentence about the runner removing a number stands beside «in the ordinary way» / «не від навмисного обходу», and that the phrases the narrowing removed («sends nothing it does not pass», «the commit that is about to be sent») are in none of them»: тест червоніє на тому, що описано вище (a manual that keeps the pointer to «The same Linux user» and again says the runner never sends a commit holding such a number passes today's checks: they look for the section's name and the path, and exclude «sends nothing» in docs/engine-limits.md only), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
