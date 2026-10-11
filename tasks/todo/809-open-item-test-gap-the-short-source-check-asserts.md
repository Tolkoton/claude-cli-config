# 809 — Брак тесту (overseer): the short-source check asserts what makes one sentence a rule: «it is a rule when the code keeps it» and «name the check, the test or the call sites that do»

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-short-source-check-asserts-what-makes-one-sentence-a-rul

## Що сталося
Overseer прийняв юніт `-|093-onboard-rules-and-hot-places|unit 1` (PASS, запит `20261011T125309Z-aacb94`) і знайшов брак тесту: «and it is a rule» with no condition, or the sentence without what confirms it, passes today — the task's own distinction (one sentence confirmed in code vs a guess) is held only from the guess side Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:54:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the short-source check asserts what makes one sentence a rule: «it is a rule when the code keeps it» and «name the check, the test or the call sites that do»»: тест червоніє на тому, що описано вище («and it is a rule» with no condition, or the sentence without what confirms it, passes today — the task's own distinction (one sentence confirmed in code vs a guess) is held only from the guess side), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
