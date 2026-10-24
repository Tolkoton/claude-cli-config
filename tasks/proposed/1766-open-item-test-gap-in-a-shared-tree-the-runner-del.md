# 1766 — Брак тесту (overseer): In a shared tree the runner deletes a working-code file while the present session writes nothing: the Stop gate does not block and opens no escalation

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-in-a-shared-tree-the-runner-deletes-a-working-code-file-whil-8a0e890c

## Що сталося
Overseer прийняв юніт `-|305-stop-gate-shared-tree|unit 1` (PASS, запит `20261024T184017Z-fd9ff0`) і знайшов брак тесту: dropping the `own` filter from deleted_code (gate.py deleted_code) still passes every test in test_shared_tree.py, because no case deletes a foreign file Де: `tests/test_shared_tree.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-24T19:10:51Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «In a shared tree the runner deletes a working-code file while the present session writes nothing: the Stop gate does not block and opens no escalation»: тест червоніє на тому, що описано вище (dropping the `own` filter from deleted_code (gate.py deleted_code) still passes every test in test_shared_tree.py, because no case deletes a foreign file), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
