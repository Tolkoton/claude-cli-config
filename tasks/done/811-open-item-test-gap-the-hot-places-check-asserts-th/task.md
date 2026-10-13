# 811 — Брак тесту (overseer): the hot-places check asserts the whole sentence «Hot places are counted among the files of code only» at its start and «go under the table as one line»; the template check asserts the placeholder «<pa

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-hot-places-check-asserts-the-whole-sentence-hot-places-a

## Що сталося
Overseer прийняв юніт `-|093-onboard-rules-and-hot-places|unit 1` (PASS, запит `20261011T125309Z-aacb94`) і знайшов брак тесту: «Hot places are never counted among the files of code only», «they are «not code»» without where the line goes, and a template line «Not code that changes often: ignore» all pass today Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:54:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the hot-places check asserts the whole sentence «Hot places are counted among the files of code only» at its start and «go under the table as one line»; the template check asserts the placeholder «<pa»: тест червоніє на тому, що описано вище («Hot places are never counted among the files of code only», «they are «not code»» without where the line goes, and a template line «Not code that changes often: ignore» all pass today), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
