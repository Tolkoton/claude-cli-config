# 1735 — Брак тесту (overseer): for both tasks/README.md and templates/project/tasks/README.md, rule 9 names the action `seal-goals` (with `action-line seal-goals`) among what the runner does on the owner's «так»

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-for-both-tasks-readme-md-and-templates-project-tasks-readme-e2fc303c

## Що сталося
Overseer прийняв юніт `-|787-open-item-088-first-goals-seal-unattended|unit 1` (PASS, запит `20261013T041616Z-02a931`) і знайшов брак тесту: the seed manual installed into every project lists the allowed actions without the first seal, so an agent in a freshly installed project — the very case board 088 raised — reads that the runner acts only from a list where seal-goals is absent; both suites pass today because no check reads the seed for this action Де: `tests/test_goals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T04:39:16Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «for both tasks/README.md and templates/project/tasks/README.md, rule 9 names the action `seal-goals` (with `action-line seal-goals`) among what the runner does on the owner's «так»»: тест червоніє на тому, що описано вище (the seed manual installed into every project lists the allowed actions without the first seal, so an agent in a freshly installed project — the very case board 088 raised — reads that the runner acts only from a list where seal-goals is absent; both suites pass today because no check reads the seed for this action), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
