# 1752 — Брак тесту (overseer): a scene in tests/test_fresh_install_gate.py: fresh install, a check command set in the seeded .claude/project.env (LINT_CMD="npm run lint", and TEST_CMD), Step 6 smoke before any commit — asserting bl

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-scene-in-tests-test-fresh-install-gate-py-fresh-install-a-5fccccb3

## Що сталося
Overseer прийняв юніт `-|786-open-item-088-gate-fresh-install-untracked|unit 1` (PASS, запит `20261013T221332Z-fc25b4`) і знайшов брак тесту: the only check after LINT_CMD is set (line 141) asserts that the report does not contain «CODE_EXTENSIONS»; it would stay green if the gate blocked on «the gate's own settings (LINT_CMD)». Today that change passes only as «changed, justified» (gate.py:652, config_justified) — I added no gate-allow line, so the justification comes from text already in the seeded file, not from the comparison with the seed; a reworded comment in the seed, or `added` computed against the seed, turns the guide's sentence false with all 20 checks green Де: `tests/test_fresh_install_gate.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-13T22:45:38Z, overseer (overseer_verdict.py)
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Дописати перевірку «a scene in tests/test_fresh_install_gate.py: fresh install, a check command set in the seeded .claude/project.env (LINT_CMD="npm run lint", and TEST_CMD), Step 6 smoke before any commit — asserting blocks(p) == [] and no block decision, as docs/TEMPLATE-SETUP.md:70-72 promises («so does a .claude/project.env in which you set SOURCE_DIRS or the check commands»)»: тест червоніє на тому, що описано вище (the only check after LINT_CMD is set (line 141) asserts that the report does not contain «CODE_EXTENSIONS»; it would stay green if the gate blocked on «the gate's own settings (LINT_CMD)». Today that change passes only as «changed, justified» (gate.py:652, config_justified) — I added no gate-allow line, so the justification comes from text already in the seeded file, not from the comparison with the seed; a reworded comment in the seed, or `added` computed against the seed, turns the guide's sentence false with all 20 checks green), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
