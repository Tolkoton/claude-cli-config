# 1751 — Брак тесту (overseer): a scene in tests/test_fresh_install_gate.py: fresh install, one line appended to the seeded .claude/project.env that changes none of the gate's keys (SOURCE_DIRS only), Step 6 smoke before any commit

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-scene-in-tests-test-fresh-install-gate-py-fresh-install-on-1c80ed9d

## Що сталося
Overseer повернув юніт `-|786-open-item-088-gate-fresh-install-untracked|unit 1` (BLOCK, запит `20261013T214941Z-50dfbf`) і назвав ще й брак тесту: today the gate answers «the diff changes CODE_EXTENSIONS … restore CODE_EXTENSIONS» for an edit that left CODE_EXTENSIONS alone, and all 16 checks stay green: the only project.env scene (line 121) changes CODE_EXTENSIONS itself Де: `tests/test_fresh_install_gate.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T22:10:22Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a scene in tests/test_fresh_install_gate.py: fresh install, one line appended to the seeded .claude/project.env that changes none of the gate's keys (SOURCE_DIRS only), Step 6 smoke before any commit — asserting whichever behaviour the fix settles on (no block; or a block whose text names the uncommitted install and the commit to make, not CODE_EXTENSIONS)»: тест червоніє на тому, що описано вище (today the gate answers «the diff changes CODE_EXTENSIONS … restore CODE_EXTENSIONS» for an edit that left CODE_EXTENSIONS alone, and all 16 checks stay green: the only project.env scene (line 121) changes CODE_EXTENSIONS itself), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
