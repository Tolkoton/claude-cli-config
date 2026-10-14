# 1754 — Брак тесту (overseer): a scene in tests/test_active_slice.py that goes through the Stop hook's own reading: after `testing.py request add-cmd --point a` and one line appended to the sealed .engine/slices/add-cmd.md, oversee

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-scene-in-tests-test-active-slice-py-that-goes-through-the-c0cd61a5

## Що сталося
Overseer прийняв юніт `-|789-open-item-088-active-slice-unknown-in-pipeline|unit 1` (PASS, запит `20261013T234226Z-7b767b`) і знайшов брак тесту: the check named «the Stop hook's reading of a changed contract has its contract» (line 114) asserts only gate.active_slice(root) == "add-cmd"; nothing in the suite calls overseer_stop, so a Stop hook that went back to reading the card alone, or lost its import of gate, would leave the changed-contract check without a slice in a pipeline task — the very consequence task 789 names — with all 30 checks green. My probe shows it works today. Де: `tests/test_active_slice.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-14T00:02:57Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a scene in tests/test_active_slice.py that goes through the Stop hook's own reading: after `testing.py request add-cmd --point a` and one line appended to the sealed .engine/slices/add-cmd.md, overseer_stop._contract_changed(root) returns that contract and its fingerprint (and None before the edit)»: тест червоніє на тому, що описано вище (the check named «the Stop hook's reading of a changed contract has its contract» (line 114) asserts only gate.active_slice(root) == "add-cmd"; nothing in the suite calls overseer_stop, so a Stop hook that went back to reading the card alone, or lost its import of gate, would leave the changed-contract check without a slice in a pipeline task — the very consequence task 789 names — with all 30 checks green. My probe shows it works today.), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
