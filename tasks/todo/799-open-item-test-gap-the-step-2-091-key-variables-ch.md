# 799 — Брак тесту (overseer): the 'step 2 (091)' key-variables check asserts that step 2 says a paid key may carry none of the searched words and that the names a script itself asks for are read ('a paid key may carry none of thes

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-step-2-091-key-variables-check-asserts-that-step-2-says-

## Що сталося
Overseer прийняв юніт `-|-|unit 1` (PASS, запит `20261011T120041Z-0990e4`) і знайшов брак тесту: deleting ', and a paid key may carry none of these words: read the names a script itself asks for' from .claude/commands/onboard.md leaves tests/test_onboard.py at PASS 62 FAIL 0, so the word filter 'key|token|secret|passw|credential' can again become the whole of the listing unnoticed Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:02:17Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'step 2 (091)' key-variables check asserts that step 2 says a paid key may carry none of the searched words and that the names a script itself asks for are read ('a paid key may carry none of thes»: тест червоніє на тому, що описано вище (deleting ', and a paid key may carry none of these words: read the names a script itself asks for' from .claude/commands/onboard.md leaves tests/test_onboard.py at PASS 62 FAIL 0, so the word filter 'key|token|secret|passw|credential' can again become the whole of the listing unnoticed), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
