# 1761 — Брак тесту (overseer): in each goals-fit lens, assert that the 'except' in the BLOCKING sentence is limited to the mark: the same sentence says 'whose substance the owner never said', and no other BLOCKING sentence in the l

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-in-each-goals-fit-lens-assert-that-the-except-in-the-blockin-5b448d04

## Що сталося
Overseer прийняв юніт `critics-goals-discipline|202-business-goals-focus-second|unit 1` (PASS, запит `20261019T075835Z-cb0024`) і знайшов брак тесту: test_*_blocking_sentence_names_the_exception only looks for 'except' and the mark somewhere in the sentence. A broader exception, such as 'except anything touching [не слова власника] or a non-goal', would pass and quietly unblock non-goal breaches (scene g) Де: `tests/test_critics_goals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-19T08:00:20Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «in each goals-fit lens, assert that the 'except' in the BLOCKING sentence is limited to the mark: the same sentence says 'whose substance the owner never said', and no other BLOCKING sentence in the lens exempts non-goals or elements with no source»: тест червоніє на тому, що описано вище (test_*_blocking_sentence_names_the_exception only looks for 'except' and the mark somewhere in the sentence. A broader exception, such as 'except anything touching [не слова власника] or a non-goal', would pass and quietly unblock non-goal breaches (scene g)), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
