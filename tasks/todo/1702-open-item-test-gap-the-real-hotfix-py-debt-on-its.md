# 1702 — Брак тесту (overseer): the real `hotfix.py debt` on its suite's synthetic project with one more task of a foreign class above the class-1 numbers (for example tasks/todo/250-y.md beside done/103-x/) writes tasks/todo/104-ho

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-real-hotfix-py-debt-on-its-suite-s-synthetic-project-wit-9b36d720

## Що сталося
Overseer прийняв юніт `task-class-overflow|401-task-numbers-by-class-build|unit 1` (PASS, запит `20261012T004536Z-d372cb`) і знайшов брак тесту: a debt command that numbers the follow-up itself with max(taken)+1 instead of calling next_number: the only CLI case seeds 004, 010 and 103 and answers 104 under that rule too, and the three new checks call hotfix.next_number directly, so they stay green — the site, not the function, is untested against a foreign class and the c99 boundary (the contract's Seam 2) Де: `tests/test_hotfix.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T00:58:38Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the real `hotfix.py debt` on its suite's synthetic project with one more task of a foreign class above the class-1 numbers (for example tasks/todo/250-y.md beside done/103-x/) writes tasks/todo/104-hotfix-followup-<card>.md; and with done/199-x/ it writes 1101-hotfix-followup-<card>.md»: тест червоніє на тому, що описано вище (a debt command that numbers the follow-up itself with max(taken)+1 instead of calling next_number: the only CLI case seeds 004, 010 and 103 and answers 104 under that rule too, and the three new checks call hotfix.next_number directly, so they stay green — the site, not the function, is untested against a foreign class and the c99 boundary (the contract's Seam 2)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
