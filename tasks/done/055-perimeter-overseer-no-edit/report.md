# 055 — Заборона overseer-у щось правити — у perimeter hooks: звіт

## Що змінилось для власника
Overseer тепер справді лише читає й судить, і тримають це perimeter hooks, а не скрипт протоколу аудиту. Усередині агента відмову дістає будь-який edit tool і будь-яка shell-команда, що пише поза тимчасовою текою. Раніше edit tools забороняв `overseer_verdict.py`, а його Bash не обмежувало ніщо: запис помічали лише після факту, за fingerprint дерева.

Одна дія чекає на вас: питання **732** у `blocked/` — «Застосувати пропозицію налаштувань?». Після вашого «так» runner застосує два рядки matcher. Живий аудит ще не перевірено: це задача **733** з дозволом на платний прогін.

Зроблено в сесії з власником 2026-10-06; зміну і три доповнення власник схвалив до застосування.

## Демонстрація на хвилину
```bash
python3 tests/test_overseer_readonly.py | tail -1     # PASS 163   FAIL 0
python3 tests/test_settings_proposal.py | tail -1     # PASS 21   FAIL 0
python3 evals/run_hook_scenarios.py --engine-ref HEAD \
  --compare evals/baseline/linux-ubuntu-22.04/results-task-055.json | tail -1   # PASS 201/201
```

## Що зроблено
- **`.claude/hooks/protect-paths.sh`** — якщо `agent_type` в envelope дорівнює `overseer`, deny на будь-який шлях, раніше за всі списки. Hook читає й `notebook_path`.
- **`.claude/hooks/block-dangerous.sh`** — команду overseer-а розбирає новий **`shell_readonly.py`**. Запис дозволено лише в `/tmp`, `/var/tmp`, `$TMPDIR` і `/dev/null`. Відмова на: ціль запису деінде (redirect, `tee`, `rm`, `cp`, `sed -i`, вбудований код); git-команди, що міняють дерево, index чи refs; formatter або linter із `--fix`.
- **`.claude/hooks/overseer_verdict.py`** — з `guard` прибрано гілку про edit tools (дубль). Лишились заборона overseer-у запускати агентів і перевірка fingerprint → INVALID як запобіжник.
- **`.claude/agents/overseer.md`** — у розділі «What you do NOT do» додано, що hooks відмовляють, і точний спосіб зробити копію.
- **Пропозиція налаштувань** — `docs/tasks/settings.json`: `protect-paths.sh` стає перед `Edit|Write|MultiEdit|NotebookEdit`, guard — лише перед `Agent|Task`. `tests/test_settings_proposal.py` і `tests/test_settings_proposal_install.py` зелені і до застосування, і після (друге перевірено на тимчасовій копії).
- **Документи:** `docs/engine-limits.md` (розділ «The overseer agent is read-only»), `.claude/references/hooks.md`.

## Що знайшли тести і чого не було в показаному diff
1. **Проєкт під `/tmp` вважався тимчасовим місцем.** Тестові репозиторії та sandbox-и evals лежать саме там, і весь запис у них проходив. Тепер шлях усередині проєкту, який аудитують, ніколи не тимчасовий.
2. **Копія через `mktemp -d` діставала відмову.** Саме так інструкція overseer-а вчить робити копію, а шлях у змінній hook вважав невідомим. Тепер ім'я, присвоєне з `mktemp` у тій самій команді, означає тимчасову теку; з `-p` чи `--tmpdir=` — ні.
3. **`tests/test_settings_proposal_install.py`** вимагав, щоб живий файл дорівнював пропозиції, і падав, поки пропозиція чекає на «так». Перевірка тепер чесна в обох станах.

## Перевірено
- `tests/test_overseer_readonly.py` — 163 перевірки:
  - 58 форм запису всередині агента заблоковано;
  - 58 законних команд пройшли: тести й лінтери, `--check`, читання git, `grep 'a > b'`, вивід у `/tmp`, `git clone . /tmp/copy`, усе всередині копії;
  - 12 — стеження за робочою текою і `mktemp` (обидва боки);
  - 22 — builder без `agent_type` та інші агенти: ті самі команди не заборонено;
  - 2 — без `python3` команди агента відхиляються, builder-а — ні;
  - 9 — edit tools (6 denied усередині агента, 3 негативні);
  - 2 — guard: Edit більше не його справа, Agent усередині агента заборонено.
- Golden set: 201/201; 180 сценаріїв без змін, 21 новий (14 для `block-dangerous.sh`, 5 для `protect-paths.sh`, 1 для guard, 1 перейменований і перевернутий на allow: `ovg-edit-inside-the-agent-is-not-its-business`). Baseline — `results-task-055.json`.
- Повний `bash tests/run_all.sh` на остаточному дереві: 73 із 74 suites зелені; єдиний червоний — `test_settings_proposal_install.py` (пункт 3 вище), після виправлення окремо 35/35. Повний набір після цього виправлення ще раз не запускався.
- `ruff` і `mypy --strict` на `shell_readonly.py` — чисто (`tests/test_engine_lint.py`).

## Чого не зроблено
- **Smoke audit не запущено.** `run_audit_scenarios.py --tier smoke --owner-approved` відмовив: усередині сесії Claude Code прапорець не рахується (`CLAUDECODE` встановлено). За вашою вказівкою це задача **733** з «Аудит потрібен: так». До неї невідомо, чи дістає overseer зайві відмови в живому аудиті.
- **Шаблона settings у `templates/` немає** — проєкти беруть `.claude/settings.json` рушія, тож оновлювати там нічого.
- **Налаштування не застосовано** — це робить runner після «так» на 732. До того `NotebookEdit` усередині overseer не заборонить ніхто; у його frontmatter цього tool немає.

## Чого це не ловить
- Запис, який робить тест чи скрипт, що його overseer лише запускає.
- Шлях у змінній як аргумент (як ціль запису — відмова), `cd` у subshell, `>` усередині тексту `python3 -c "…"`.
- Усе це, як і раніше, ловить fingerprint дерева → вердикт INVALID.
- Охоплено лише агента `overseer`. Critics не мають рядка `tools` у frontmatter, тобто мають усе, зокрема Bash і Edit; simplifier і business-analyst — лише Read, Grep, Glob. Це задача **734**.

## Нові записи на дошці
- **732** (`blocked/`) — «Застосувати пропозицію налаштувань?» з рядком дії `apply-settings`.
- **733** — smoke audit після 055.
- **734** — інструменти critics і simplifier.
- **735** — `tests/test_simplifier.py` наприкінці стирає `/tmp/simplifier-*` чужих прогонів; через це Stop gate один раз упав під час цієї сесії, поки на машині йшли три прогони одночасно.

Номери 730–735 узято із запасом: 720–724 на origin уже зайняв runner.

## Commit-и
`6a86d43` (зміна, тести, golden-сценарії, пропозиція налаштувань, документи) і commit закриття задачі після нього, гілка `unattended/work`. Push не робився.

## Рішення, які я ухвалив сам
- **Розбір у окремому `shell_readonly.py`**, що спирається на `shell_paths.py` із 714, а не розширення останнього: правила інші (кожен шлях, а не захищені), і помилка в одному не ламає другий.
- **Питання про налаштування — окремим записом 732**, а не переносом 055 у `blocked/`: решта задачі зроблена й перевірена.
- **Suite поза fast-набором.**
- **Задача пройшла повз `doing/`** — виняток власника для цієї сесії (задача 730).
