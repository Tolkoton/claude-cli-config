# 829 — Брак тесту (overseer): the owner's review of a runner stopped with `state=idle reason=extra-cap`: the runner line says that tasks with extra sessions wait for the weekly sum, and does not say that todo/ holds nothing

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-owner-s-review-of-a-runner-stopped-with-state-idle-reaso

## Що сталося
Overseer прийняв юніт `-|110-extra-sessions-after-ordinary-and-weekly-cap|unit 1` (PASS, запит `20261011T203356Z-604a6c`) і знайшов брак тесту: today the line reads 'зупинився: у todo/ нічого немає (`idle`) …; причина: `extra-cap`' because STATES['idle'] at .claude/unattended/board_review.py:74 was written when todo-empty was the only idle reason; no test builds a status file with reason extra-cap, so the false sentence passes Де: `tests/test_board_review.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T20:59:36Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the owner's review of a runner stopped with `state=idle reason=extra-cap`: the runner line says that tasks with extra sessions wait for the weekly sum, and does not say that todo/ holds nothing»: тест червоніє на тому, що описано вище (today the line reads 'зупинився: у todo/ нічого немає (`idle`) …; причина: `extra-cap`' because STATES['idle'] at .claude/unattended/board_review.py:74 was written when todo-empty was the only idle reason; no test builds a status file with reason extra-cap, so the false sentence passes), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
