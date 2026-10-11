# 813 — Брак тесту (overseer): a configuration file in a subdirectory and one matched by a pattern of LINT_CONFIGS (packages/web/.eslintignore, .eslintrc.json, .golangci.yaml) that excludes an old directory gets its note 2

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-configuration-file-in-a-subdirectory-and-one-matched-by-a-

## Що сталося
Overseer прийняв юніт `-|094-install-moves-and-onboard-dirty-tree|unit 1` (PASS, запит `20261011T131917Z-0f4956`) і знайшов брак тесту: replacing the fnmatch over LINT_CONFIGS at engine.py:333 with `rel in ("pyproject.toml", ".prettierignore", ".pre-commit-config.yaml")` leaves tests/test_install_move_notes.py at PASS 16 FAIL 0: the fixture has only root-level files with exact names Де: `tests/test_install_move_notes.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:31:37Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a configuration file in a subdirectory and one matched by a pattern of LINT_CONFIGS (packages/web/.eslintignore, .eslintrc.json, .golangci.yaml) that excludes an old directory gets its note 2»: тест червоніє на тому, що описано вище (replacing the fnmatch over LINT_CONFIGS at engine.py:333 with `rel in ("pyproject.toml", ".prettierignore", ".pre-commit-config.yaml")` leaves tests/test_install_move_notes.py at PASS 16 FAIL 0: the fixture has only root-level files with exact names), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
