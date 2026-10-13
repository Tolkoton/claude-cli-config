# 1701 — Брак тесту (overseer): the hotfix follow-up site at the class boundary: `hotfix.py debt` on a board that holds `done/199-x/` writes `1101-hotfix-followup-…`, and with `todo/250-y.md` beside `done/103-x/` still writes `104-…

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-hotfix-follow-up-site-at-the-class-boundary-hotfix-py-de-8df58b29

## Що сталося
Overseer прийняв юніт `task-class-overflow|401-task-numbers-by-class-build|unit 1` (PASS, запит `20261012T001754Z-109051`) і знайшов брак тесту: the only site case seeds 004, 010 and 103, so a `next_number(tasks)` that answers max(taken under 200)+1 or max(taken)+1 without task_classes passes it; no foreign-class or c99 number is ever on the hotfix board Де: `tests/test_hotfix.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T00:30:43Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the hotfix follow-up site at the class boundary: `hotfix.py debt` on a board that holds `done/199-x/` writes `1101-hotfix-followup-…`, and with `todo/250-y.md` beside `done/103-x/` still writes `104-…`»: тест червоніє на тому, що описано вище (the only site case seeds 004, 010 and 103, so a `next_number(tasks)` that answers max(taken under 200)+1 or max(taken)+1 without task_classes passes it; no foreign-class or c99 number is ever on the hotfix board), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
