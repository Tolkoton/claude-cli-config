# 1715 — Брак тесту (overseer): for run_analyst_evals, run_manager_evals and run_tester_evals: a run stopped by --max-usd after one session of two writes status `partial` (through the CLI, on the shim)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-for-run-analyst-evals-run-manager-evals-and-run-tester-evals-ccee0b3d

## Що сталося
Overseer прийняв юніт `-|725-open-item-eval-runners-failed-session-as-result|unit 1` (PASS, запит `20261012T054046Z-c44b55`) і знайшов брак тесту: a runner that passes len(runs) instead of the plan (len(todo) / len(args.scenes)) to status() says `complete` for a run its ceiling cut short; today only the simplifier has this case (the suite skips the other three with `continue`) Де: `tests/test_eval_runners_failed_session.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T05:45:15Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «for run_analyst_evals, run_manager_evals and run_tester_evals: a run stopped by --max-usd after one session of two writes status `partial` (through the CLI, on the shim)»: тест червоніє на тому, що описано вище (a runner that passes len(runs) instead of the plan (len(todo) / len(args.scenes)) to status() says `complete` for a run its ceiling cut short; today only the simplifier has this case (the suite skips the other three with `continue`)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
