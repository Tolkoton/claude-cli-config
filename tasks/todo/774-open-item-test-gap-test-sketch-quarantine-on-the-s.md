# 774 — Брак тесту (overseer): test_sketch_quarantine: on the stop layer a changed src/sketches/deep.py with a `# type: ignore` (or a deletion) is still judged by the bypass guard and the delete guard — a block is asserted, next to

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-test-sketch-quarantine-on-the-stop-layer-a-changed-src-sketc

## Що сталося
Overseer прийняв юніт `-|099-modes-sketch|unit 1` (PASS, запит `20261011T061554Z-cefbce`) і знайшов брак тесту: replacing `not f.startswith(SKETCHES)` at .claude/hooks/gate.py:1297 with `SKETCHES not in f` keeps test_sketch_quarantine at 29/0 and test_gate at 114/0 (mutant run in /tmp/ov099x/m); the case at tests/test_sketch_quarantine.py:163 tries the shared name only for the reference rule, not for the filter that drops files from every gate Де: `tests/test_sketch_quarantine.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-11T06:28:14Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «test_sketch_quarantine: on the stop layer a changed src/sketches/deep.py with a `# type: ignore` (or a deletion) is still judged by the bypass guard and the delete guard — a block is asserted, next to»: тест червоніє на тому, що описано вище (replacing `not f.startswith(SKETCHES)` at .claude/hooks/gate.py:1297 with `SKETCHES not in f` keeps test_sketch_quarantine at 29/0 and test_gate at 114/0 (mutant run in /tmp/ov099x/m); the case at tests/test_sketch_quarantine.py:163 tries the shared name only for the reference rule, not for the filter that drops files from every gate), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
