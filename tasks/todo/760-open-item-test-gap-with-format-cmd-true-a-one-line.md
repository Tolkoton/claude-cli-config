# 760 — Брак тесту (overseer): with FORMAT_CMD="true", a one-line edit to a .toml and a .yaml file (both handled by the built-in prettier branch) makes no formatter call and gives a one-line numstat

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-with-format-cmd-true-a-one-line-edit-to-a-toml-and-a-yaml-fi

## Що сталося
Overseer прийняв юніт `-|749-open-item-602-cloud-formatter-whole-file|unit 1` (PASS, запит `20261010T060655Z-dcb14d`) і знайшов брак тесту: an off switch that spares the toml/yaml prettier handler, e.g. a per-handler check that lists only md/yml/json/py, passes OFF-1 and OFF-2 today. The engine tracks .claude/ruff.toml, several pyproject.toml files and evals/scenarios/simplifier-hard/project/tests/fixtures/prices.yaml, all of which prettier would rewrite Де: `tests/test_format_on_edit.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T06:12:40Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «with FORMAT_CMD="true", a one-line edit to a .toml and a .yaml file (both handled by the built-in prettier branch) makes no formatter call and gives a one-line numstat»: тест червоніє на тому, що описано вище (an off switch that spares the toml/yaml prettier handler, e.g. a per-handler check that lists only md/yml/json/py, passes OFF-1 and OFF-2 today. The engine tracks .claude/ruff.toml, several pyproject.toml files and evals/scenarios/simplifier-hard/project/tests/fixtures/prices.yaml, all of which prettier would rewrite), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
