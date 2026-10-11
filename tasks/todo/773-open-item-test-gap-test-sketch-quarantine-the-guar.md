# 773 — Брак тесту (overseer): test_sketch_quarantine, the guards section: deleting a long function from src/sketches/kept.py (a directory that only shares the name, inside SOURCE_DIRS) is still the delete guard's block — asserts b

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-test-sketch-quarantine-the-guards-section-deleting-a-long-fu

## Що сталося
Overseer прийняв юніт `-|099-modes-sketch|unit 1` (PASS, запит `20261011T061554Z-cefbce`) і знайшов брак тесту: replacing `rel.startswith("sketches/")` at .claude/hooks/delete_guard.py:120 with `"sketches/" in rel` keeps test_sketch_quarantine at 29/0, test_delete_guard at 64/0 and test_gate at 114/0 (mutant run in /tmp/ov099x/m); working code under any directory named sketches would then be deleted without the guard Де: `tests/test_sketch_quarantine.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-11T06:28:14Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «test_sketch_quarantine, the guards section: deleting a long function from src/sketches/kept.py (a directory that only shares the name, inside SOURCE_DIRS) is still the delete guard's block — asserts b»: тест червоніє на тому, що описано вище (replacing `rel.startswith("sketches/")` at .claude/hooks/delete_guard.py:120 with `"sketches/" in rel` keeps test_sketch_quarantine at 29/0, test_delete_guard at 64/0 and test_gate at 114/0 (mutant run in /tmp/ov099x/m); working code under any directory named sketches would then be deleted without the guard), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
