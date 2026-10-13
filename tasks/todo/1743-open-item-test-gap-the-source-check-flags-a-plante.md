# 1743 — Брак тесту (overseer): the source check flags a planted suite whose listing call and shared directory are on different lines: `left = glob.glob(` then `os.path.join(tempfile.gettempdir(), 'x-*'))`

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-source-check-flags-a-planted-suite-whose-listing-call-an-75d0a53d

## Що сталося
Overseer прийняв юніт `-|767-open-item-test-gap-test-tmp-cleanup-s-source-check|unit 1` (PASS, запит `20261013T075103Z-44305d`) і знайшов брак тесту: shared_listings reads one line at a time; a listing of the shared directory wrapped over two lines returns [] and the suite passes the check Де: `tests/test_tmp_cleanup.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T07:52:34Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the source check flags a planted suite whose listing call and shared directory are on different lines: `left = glob.glob(` then `os.path.join(tempfile.gettempdir(), 'x-*'))`»: тест червоніє на тому, що описано вище (shared_listings reads one line at a time; a listing of the shared directory wrapped over two lines returns [] and the suite passes the check), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
