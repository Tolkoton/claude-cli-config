# 818 — Брак тесту (overseer): record in a session with an unparseable .engine/baseline.json on disk: assert what the message says about the file (that a file exists and is not a snapshot the script wrote — `load` already returns t

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-record-in-a-session-with-an-unparseable-engine-baseline-json

## Що сталося
Overseer прийняв юніт `-|095-onboard-profile-template-and-first-snapshot|unit 1` (PASS, запит `20261011T134556Z-2ad1f1`) і знайшов брак тесту: today the output is «there is no snapshot yet; this is what the first one would record» although a file is on disk (reproduced: «{ not json» + 25 failing tests); no test runs `record` on a corrupt snapshot, so any wording passes Де: `tests/test_baseline.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:47:16Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «record in a session with an unparseable .engine/baseline.json on disk: assert what the message says about the file (that a file exists and is not a snapshot the script wrote — `load` already returns t»: тест червоніє на тому, що описано вище (today the output is «there is no snapshot yet; this is what the first one would record» although a file is on disk (reproduced: «{ not json» + 25 failing tests); no test runs `record` on a corrupt snapshot, so any wording passes), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
