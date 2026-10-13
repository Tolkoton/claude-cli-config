# 807 — Брак тесту (overseer): the engine's-rules check asserts the direction of the sign: «the project's code and data — a candidate» and «the way an agent works (…) — the engine's» as whole phrases, and the verdict of each exampl

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-engine-s-rules-check-asserts-the-direction-of-the-sign-t

## Що сталося
Overseer прийняв юніт `-|093-onboard-rules-and-hot-places|unit 1` (PASS, запит `20261011T125309Z-aacb94`) і знайшов брак тесту: swapping the halves («the way an agent works — a candidate; the project's code and data …»), writing «is not a candidate even when it says» for the secrets rule, writing «in a task file is a candidate», or deleting «, one lesson at a time» — each leaves tests/test_onboard.py at PASS 91 FAIL 0 Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:54:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the engine's-rules check asserts the direction of the sign: «the project's code and data — a candidate» and «the way an agent works (…) — the engine's» as whole phrases, and the verdict of each exampl»: тест червоніє на тому, що описано вище (swapping the halves («the way an agent works — a candidate; the project's code and data …»), writing «is not a candidate even when it says» for the secrets rule, writing «in a task file is a candidate», or deleting «, one lesson at a time» — each leaves tests/test_onboard.py at PASS 91 FAIL 0), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
