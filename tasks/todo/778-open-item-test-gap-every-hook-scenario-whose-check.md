# 778 — Брак тесту (overseer): every hook scenario whose check_file lies under .engine/journal/ sets CLAUDE_CODE_SESSION_ID in its env to the session named by that file (golden.md ↔ golden)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-every-hook-scenario-whose-check-file-lies-under-engine-journ

## Що сталося
Overseer прийняв юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` (PASS, запит `20261011T080431Z-d38a0a`) і знайшов брак тесту: a scenario that watches .engine/journal/<journal>/golden.md with `expect_file_changed: false` but without the env line (or with another session name): the hook writes another session's file, so the scenario can never go red — the same blindness the new check in tests/test_journal.py catches only for the shared files Де: `tests/test_journal.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T08:17:20Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «every hook scenario whose check_file lies under .engine/journal/ sets CLAUDE_CODE_SESSION_ID in its env to the session named by that file (golden.md ↔ golden)»: тест червоніє на тому, що описано вище (a scenario that watches .engine/journal/<journal>/golden.md with `expect_file_changed: false` but without the env line (or with another session name): the hook writes another session's file, so the scenario can never go red — the same blindness the new check in tests/test_journal.py catches only for the shared files), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
