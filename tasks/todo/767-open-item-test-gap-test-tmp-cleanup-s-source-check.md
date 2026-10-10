# 767 — Брак тесту (overseer): test_tmp_cleanup's source check plants each way of listing the shared temporary directory in a synthetic tests dir and flags every one: glob.glob(os.path.join(tempfile.gettempdir(), 'x-*')), Path('/tm

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-test-tmp-cleanup-s-source-check-plants-each-way-of-listing-t

## Що сталося
Overseer прийняв юніт `-|735-open-item-test-simplifier-removes-other-runs-tmp|unit 1` (PASS, запит `20261010T110220Z-525a69`) і знайшов брак тесту: SHARED_GLOB matches only the text `gettempdir()).glob(`. A suite that ends with `for p in glob.glob(os.path.join(tempfile.gettempdir(), 'simplifier-*')): shutil.rmtree(p)` or `Path('/tmp').glob('budget-*')` passes the check, and test_bugfix is not one of the suites run concurrently. Its leftover check could go back to scanning the shared directory and nothing would notice. Де: `tests/test_tmp_cleanup.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T11:23:52Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «test_tmp_cleanup's source check plants each way of listing the shared temporary directory in a synthetic tests dir and flags every one: glob.glob(os.path.join(tempfile.gettempdir(), 'x-*')), Path('/tm»: тест червоніє на тому, що описано вище (SHARED_GLOB matches only the text `gettempdir()).glob(`. A suite that ends with `for p in glob.glob(os.path.join(tempfile.gettempdir(), 'simplifier-*')): shutil.rmtree(p)` or `Path('/tmp').glob('budget-*')` passes the check, and test_bugfix is not one of the suites run concurrently. Its leftover check could go back to scanning the shared directory and nothing would notice.), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
