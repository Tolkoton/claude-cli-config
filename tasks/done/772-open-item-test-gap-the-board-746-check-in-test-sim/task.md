# 772 — Брак тесту (overseer): the board 746 check in test_simplifier_evals also asserts the boundary sentence stands in the «Is it a trap?» step: 'a parameter or a constant no caller sets is another matter'

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-board-746-check-in-test-simplifier-evals-also-asserts-th

## Що сталося
Overseer прийняв юніт `-|-|unit 1` (PASS, запит `20261011T052150Z-850689`) і знайшов брак тесту: deleting the last sentence of the paragraph at .claude/agents/simplifier.md:61-62 keeps tests/test_simplifier_evals.py at 302/0 (the check at line 347 asserts only 'only reads and never sets', 'environment variable' and '`flag_only` at most'); without that sentence the rule can be read to cover the planted wholesale flag, and the recall measured in ten paid sessions would no longer be protected by any free test Де: `tests/test_simplifier_evals.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-11T05:34:24Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the board 746 check in test_simplifier_evals also asserts the boundary sentence stands in the «Is it a trap?» step: 'a parameter or a constant no caller sets is another matter'»: тест червоніє на тому, що описано вище (deleting the last sentence of the paragraph at .claude/agents/simplifier.md:61-62 keeps tests/test_simplifier_evals.py at 302/0 (the check at line 347 asserts only 'only reads and never sets', 'environment variable' and '`flag_only` at most'); without that sentence the rule can be read to cover the planted wholesale flag, and the recall measured in ten paid sessions would no longer be protected by any free test), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
