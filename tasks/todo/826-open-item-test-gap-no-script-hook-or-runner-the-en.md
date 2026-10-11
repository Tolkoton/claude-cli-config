# 826 — Брак тесту (overseer): no script, hook or runner the engine ships passes a fixed Fable model to a run: assert that no tracked *.sh / *.py under .claude/, evals/ and engine.py contains `--model` followed by a literal value m

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-no-script-hook-or-runner-the-engine-ships-passes-a-fixed-fab

## Що сталося
Overseer прийняв юніт `-|109-simplifier-on-opus-not-fable|unit 1` (PASS, запит `20261011T195342Z-3467e3`) і знайшов брак тесту: a runner with a hard-coded `--model fable` (or `default="fable"` in evals/run_simplifier_evals.py:359) puts the simplifier's runs back on Fable and tests/test_model_roles.py stays at PASS 65 FAIL 0 - the task's «чи запусками» is checked by nothing Де: `tests/test_model_roles.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T19:55:24Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «no script, hook or runner the engine ships passes a fixed Fable model to a run: assert that no tracked *.sh / *.py under .claude/, evals/ and engine.py contains `--model` followed by a literal value m»: тест червоніє на тому, що описано вище (a runner with a hard-coded `--model fable` (or `default="fable"` in evals/run_simplifier_evals.py:359) puts the simplifier's runs back on Fable and tests/test_model_roles.py stays at PASS 65 FAIL 0 - the task's «чи запусками» is checked by nothing), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
