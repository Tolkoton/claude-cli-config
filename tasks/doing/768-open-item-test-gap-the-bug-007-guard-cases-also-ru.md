# 768 — Брак тесту (overseer): the bug-007 guard cases also run `testing.py guard` under each older interpreter on PATH (shutil.which('python3.12'), 'python3.11' once 748 lands) and assert the same decision with rc 0. Or: a check t

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-bug-007-guard-cases-also-run-testing-py-guard-under-each

## Що сталося
Overseer прийняв юніт `-|747-open-item-602-testing-guard-resolve-loop|unit 1` (PASS, запит `20261010T113546Z-b1deb7`) і знайшов брак тесту: reverting .claude/hooks/testing.py:953 to Path(target).resolve() keeps tests/test_testing.py at 192/0 under python3 (3.13.16), the interpreter tests/run_all.sh:96 and the Stop gate use (reproduced on the base code in /tmp/ov747/before). The traceback-and-undecided call comes back on 3.12 and only a manual python3.12 run would catch it Де: `tests/test_testing.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T11:42:46Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the bug-007 guard cases also run `testing.py guard` under each older interpreter on PATH (shutil.which('python3.12'), 'python3.11' once 748 lands) and assert the same decision with rc 0. Or: a check t»: тест червоніє на тому, що описано вище (reverting .claude/hooks/testing.py:953 to Path(target).resolve() keeps tests/test_testing.py at 192/0 under python3 (3.13.16), the interpreter tests/run_all.sh:96 and the Stop gate use (reproduced on the base code in /tmp/ov747/before). The traceback-and-undecided call comes back on 3.12 and only a manual python3.12 run would catch it), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
