# 830 — Брак тесту (overseer): run_all.sh --fast on a list where the longer name comes first ('test_one_more.py' then 'test_one.py', both files present) runs both suites: --list prints tests/test_one_more.py and tests/test_one.py,

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-run-all-sh-fast-on-a-list-where-the-longer-name-comes-first-

## Що сталося
Overseer прийняв юніт `-|104-registry-files-merge-union|unit 1` (PASS, запит `20261011T211719Z-e997b0`) і знайшов брак тесту: a dedup that compares by name prefix or stem — `case " ${SUITES[*]-} " in *"${line%.py}"*) continue` at tests/run_all.sh:58 — silently drops test_one.py from the Stop-gate subset when test_one_more.py is listed before it, and tests/test_registry_merge.py stays at PASS 18 FAIL 0: the check at :147 only tries the order 'test_one.py, test_one_more.py', where no containment can occur Де: `tests/test_registry_merge.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T21:20:56Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «run_all.sh --fast on a list where the longer name comes first ('test_one_more.py' then 'test_one.py', both files present) runs both suites: --list prints tests/test_one_more.py and tests/test_one.py, »: тест червоніє на тому, що описано вище (a dedup that compares by name prefix or stem — `case " ${SUITES[*]-} " in *"${line%.py}"*) continue` at tests/run_all.sh:58 — silently drops test_one.py from the Stop-gate subset when test_one_more.py is listed before it, and tests/test_registry_merge.py stays at PASS 18 FAIL 0: the check at :147 only tries the order 'test_one.py, test_one_more.py', where no containment can occur), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
