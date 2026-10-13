# 1745 — Брак тесту (overseer): an interpreter-independent bug-007 case: testing.guard called in-process for the tester's Write on the symlink loop, with pathlib.Path.resolve patched to raise RuntimeError('Symlink loop') as it does

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-an-interpreter-independent-bug-007-case-testing-guard-called-117bbd8c

## Що сталося
Overseer прийняв юніт `-|768-open-item-test-gap-the-bug-007-guard-cases-also-ru|unit 1` (PASS, запит `20261013T081738Z-d631e4`) і знайшов брак тесту: on a machine whose python3 is 3.13+ with neither python3.11 nor python3.12 on PATH, .claude/hooks/testing.py:954 reverted to Path(target).resolve() keeps tests/test_testing.py green: the older-interpreter cases are skipped with a 'note' line and exit 0 Де: `tests/test_testing.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T08:20:40Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «an interpreter-independent bug-007 case: testing.guard called in-process for the tester's Write on the symlink loop, with pathlib.Path.resolve patched to raise RuntimeError('Symlink loop') as it does up to 3.12, returns the decision the name gets (deny 'test files only' for src/loop.py, None for tests/test_loop.py) — or the suite fails, not notes, when no interpreter older than 3.13 ran the loop cases»: тест червоніє на тому, що описано вище (on a machine whose python3 is 3.13+ with neither python3.11 nor python3.12 on PATH, .claude/hooks/testing.py:954 reverted to Path(target).resolve() keeps tests/test_testing.py green: the older-interpreter cases are skipped with a 'note' line and exit 0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
