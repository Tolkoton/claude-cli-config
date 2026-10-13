# 1744 — Брак тесту (overseer): the source check flags a planted suite that binds the shared directory through a trailing call or the environment: `TMP = Path(tempfile.gettempdir()).resolve()` then `TMP.glob('x-*')`, and `os.listdir

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-source-check-flags-a-planted-suite-that-binds-the-shared-d5645f15

## Що сталося
Overseer прийняв юніт `-|767-open-item-test-gap-test-tmp-cleanup-s-source-check|unit 1` (PASS, запит `20261013T075103Z-44305d`) і знайшов брак тесту: NAMED_DIR is anchored at the closing bracket, so a binding ending in .resolve() is not remembered, and SHARED has no TMPDIR form; both planted suites return [] today Де: `tests/test_tmp_cleanup.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T07:52:34Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the source check flags a planted suite that binds the shared directory through a trailing call or the environment: `TMP = Path(tempfile.gettempdir()).resolve()` then `TMP.glob('x-*')`, and `os.listdir(os.environ['TMPDIR'])`»: тест червоніє на тому, що описано вище (NAMED_DIR is anchored at the closing bracket, so a binding ending in .resolve() is not remembered, and SHARED has no TMPDIR form; both planted suites return [] today), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
