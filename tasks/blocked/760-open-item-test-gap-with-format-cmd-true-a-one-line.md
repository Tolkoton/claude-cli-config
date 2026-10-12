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

Стан роботи (2026-10-12): зроблено, перевірено і закомічено в цій гілці (commit `c65a11e`).
- `tests/test_format_on_edit.py`, розділ OFF-*: до файлів, у яких змінюється один рядок, додано `tool.toml` і `prices.yaml` — два розширення вбудованого prettier handler-а, яких жодна перевірка не тримала. OFF-1 і OFF-2 тепер вимагають для них теж: жодного виклику formatter-а і numstat `1 1`. OFF-3 (control, `FORMAT_CMD` порожній) вимагає виклику prettier на обох файлах і більшого diff-а — тож нові перевірки не порожні.
- Червоний прогін: у `.claude/hooks/gate.py` (рядок 1205) тимчасово звузив off switch до `fmt.strip() == "true" and ext in ("md", "yml", "json", "py")` — `python3 tests/test_format_on_edit.py` дає `PASS 26   FAIL 3`, exit 1: у журналі `prettier --write --log-level silent …/tool.toml` і `…/prices.yaml`, numstat обох «more». Старий тест на тому самому mutant-і — `PASS 29   FAIL 0`: брак тесту був справжній.
- Зелений прогін: на коді, як він є (`git checkout -- .claude/hooks/gate.py`), — `PASS 29   FAIL 0`.
- `bash tests/run_all.sh --fast` — `PASS: 45 suites green (fast subset)`; `bash tests/run_all.sh` — `PASS: 98 suites green`.
- Код hook-а не мінявся: вади тест не знайшов — off switch повертається раніше, ніж дивиться на розширення.
- Рішення, які я ухвалив сам: окремого розділу OFF-4 не писав, а додав два файли до спільного набору `UNFORMATTED` — так ті самі три випадки (OFF-1, OFF-2 і control OFF-3) покривають і нові розширення.
- Overseer (request `20261012T095814Z-b1e185`) не знайшов жодної невдалої перевірки і сам відтворив червоний і зелений прогони, але вердикт записано як BLOCK 1 із 3 лише тому, що відкрита gate escalation 2026-10-12T01:56:46Z чужої задачі (slice `numbers-class-table`, файл `tests/test_task_class_table.py`, питання `tasks/blocked/902-gate-escalation-20261012T015646Z.md`). Цього файла моя робота не торкається; закрити escalation агент не може і не має. Браку тесту overseer цього разу не назвав.

Чого бракує до `done/`: запису PASS overseer-а і `report.md`.

1. Як закрити цю задачу? Варіанти: (а) ви відповідаєте «так» на питання 902 (або закриваєте escalation у своєму терміналі: `python3 .claude/hooks/gate.py --close-escalation 2026-10-12T01:56:46Z`), а тут пишете «закрито» — агент знову заявляє unit, новий overseer перевіряє, задача йде в `done/` зі звітом; (б) не хочете зараз вирішувати 902 — напишіть «чекати»: задача лишиться тут, зміна вже в гілці й нічого не блокує. Порада агента: (а) — робота готова, бракує лише запису PASS. Те саме питання стоїть у задачах 719, 725, 726, 728, 730, 740, 751, 752, 756 і 757.
   Відповідь: закрито
