# 1712 — Брак тесту (overseer): the cleaning-turn scene must fail on a runner that puts the file back without asking: a guarded change made by the cleaning turn while the task is in doing/ (and the same for the mode-minimum turn, wh

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-cleaning-turn-scene-must-fail-on-a-runner-that-puts-the-699a6cab

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T033237Z-a582a3`) і знайшов брак тесту: the pre-fix runner (guard_session returning early for a task in doing/) passes both cleaning-turn checks, as the turn itself reports and my pre-fix run confirms (PASS 12 FAIL 4, neither failure in that scene); already on the board as tasks/todo/1709, still open Де: `tests/test_board_runner.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T03:36:39Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the cleaning-turn scene must fail on a runner that puts the file back without asking: a guarded change made by the cleaning turn while the task is in doing/ (and the same for the mode-minimum turn, which has no scene) asserts the question item exists»: тест червоніє на тому, що описано вище (the pre-fix runner (guard_session returning early for a task in doing/) passes both cleaning-turn checks, as the turn itself reports and my pre-fix run confirms (PASS 12 FAIL 4, neither failure in that scene); already on the board as tasks/todo/1709, still open), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
