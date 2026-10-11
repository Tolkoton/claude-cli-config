# 816 — Брак тесту (overseer): a line that names both .claude/overseer/ledger.md and .claude/overseer/slice/x.md gives one note naming .claude/overseer once, and a file already under .engine/ that names an old path is not reported

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-line-that-names-both-claude-overseer-ledger-md-and-claude-

## Що сталося
Overseer прийняв юніт `-|094-install-moves-and-onboard-dirty-tree|unit 1` (PASS, запит `20261011T131917Z-0f4956`) і знайшов брак тесту: deleting the filter of nested roots in move_notes, or the `rel.startswith(".engine/")` half of skip, leaves the suite at 16/0 Де: `tests/test_install_move_notes.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:31:37Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a line that names both .claude/overseer/ledger.md and .claude/overseer/slice/x.md gives one note naming .claude/overseer once, and a file already under .engine/ that names an old path is not reported»: тест червоніє на тому, що описано вище (deleting the filter of nested roots in move_notes, or the `rel.startswith(".engine/")` half of skip, leaves the suite at 16/0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
