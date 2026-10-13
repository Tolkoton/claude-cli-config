# 1714 — Брак тесту (overseer): a guard check: `after` with a snapshot whose guarded file is absent now because `git ls-files` fails (a broken index) — asserts the comparison is an error or the files are restored, never exit 0

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-guard-check-after-with-a-snapshot-whose-guarded-file-is-ab-2fccb325

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T043134Z-a04397`) і знайшов брак тесту: guarded() ignores git's return code: with git failing, `before` silently records only the four NAMED files and migrations / CI workflows go unguarded for that session; no check tries a failing git Де: `tests/test_protected_guard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T04:58:19Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a guard check: `after` with a snapshot whose guarded file is absent now because `git ls-files` fails (a broken index) — asserts the comparison is an error or the files are restored, never exit 0»: тест червоніє на тому, що описано вище (guarded() ignores git's return code: with git failing, `before` silently records only the four NAMED files and migrations / CI workflows go unguarded for that session; no check tries a failing git), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
