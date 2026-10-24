# 1767 — Брак тесту (overseer): A session whose transcript holds one `git pull` (or another unresolvable write) beside a live runner is judged on the whole tree, and the report or systemMessage says why the shared-tree split was not

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-session-whose-transcript-holds-one-git-pull-or-another-unr-381892cc

## Що сталося
Overseer прийняв юніт `-|305-stop-gate-shared-tree|unit 1` (PASS, запит `20261024T184017Z-fd9ff0`) і знайшов брак тесту: nothing tells the owner why the incident came back after an unresolvable write; today's tests check only that the gate blocks, not that the fallback is explained Де: `tests/test_shared_tree.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-24T19:10:51Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «A session whose transcript holds one `git pull` (or another unresolvable write) beside a live runner is judged on the whole tree, and the report or systemMessage says why the shared-tree split was not applied»: тест червоніє на тому, що описано вище (nothing tells the owner why the incident came back after an unresolvable write; today's tests check only that the gate blocks, not that the fallback is explained), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
