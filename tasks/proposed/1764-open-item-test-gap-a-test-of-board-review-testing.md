# 1764 — Брак тесту (overseer): a test of board_review.testing_section with a ledger holding a `parked` row and then an `unparked` row for the same slice (by=no-end), and a `round` row with `by`: asserts that «Знято: новий slice con

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-test-of-board-review-testing-section-with-a-ledger-holding-e7d1a649

## Що сталося
Overseer прийняв юніт `-|304-parked-slice-superseded-by-new-contract|unit 1` (PASS, запит `20261024T144335Z-104c46`) і знайшов брак тесту: lifted() looking at every[:at] instead of every[at:], or matching the wrong slice, would show the owner a parked slice as still parked (or show a lift that never happened), and today's 124 board_review checks still pass because none of them builds an unparked row Де: `tests/test_board_review.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-24T17:47:30Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a test of board_review.testing_section with a ledger holding a `parked` row and then an `unparked` row for the same slice (by=no-end), and a `round` row with `by`: asserts that «Знято: новий slice contract `no-end`» appears under «Відкладені slice-и», that the round line names «новий slice contract `no-end`», and that the verdict word for `superseded` is used»: тест червоніє на тому, що описано вище (lifted() looking at every[:at] instead of every[at:], or matching the wrong slice, would show the owner a parked slice as still parked (or show a lift that never happened), and today's 124 board_review checks still pass because none of them builds an unparked row), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
