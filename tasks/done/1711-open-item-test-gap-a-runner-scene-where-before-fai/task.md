# 1711 — Брак тесту (overseer): a runner scene where `before` fails (exit non-zero, nothing printed): asserts the session is not started, or that the board stops / the owner is asked

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-runner-scene-where-before-fails-exit-non-zero-nothing-prin-ef84bb44

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T033237Z-a582a3`) і знайшов брак тесту: a runner that starts the session with an empty GUARD_BEFORE and guards nothing — today's behaviour, seen by no scene Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T03:36:39Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a runner scene where `before` fails (exit non-zero, nothing printed): asserts the session is not started, or that the board stops / the owner is asked»: тест червоніє на тому, що описано вище (a runner that starts the session with an empty GUARD_BEFORE and guards nothing — today's behaviour, seen by no scene), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
