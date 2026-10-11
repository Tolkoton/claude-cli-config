# 109 — Simplifier на Opus замість Fable — звіт

## Що змінилось для власника
- **Simplifier тепер працює на Opus.** У `.claude/agents/simplifier.md` рядок `model: fable` замінено на `model: opus`.
  Це єдиний рядок `model:` в усіх визначеннях двигуна (`.claude`, `templates`, `user`).
- **Жоден агент двигуна не закріплений за Fable, і це перевіряє тест.** `tests/test_model_roles.py` має новий розділ:
  жодне з 60 визначень і жоден шар налаштувань не називає Fable, а simplifier стоїть на `opus`.
- **Формулювання про найсильнішу модель оновлено** в `docs/ARCHITECTURE.md:38`: critics і overseer — на моделі сесії,
  simplifier — на Opus, найсильніша модель двигуна — Opus. Довідка `.claude/references/simplifier.md` теж каже `opus`.
- Записи вимірів у `evals/baseline/` не чіпав.

## Демонстрація на хвилину
```
git grep -n -E '^model:' -- .claude templates user   # один рядок: .claude/agents/simplifier.md:11:model: opus
python3 tests/test_model_roles.py                    # PASS 65   FAIL 0
python3 tests/test_simplifier.py                     # PASS 96   FAIL 0
```
- До зміни, з уже написаними перевірками: `test_model_roles.py` — PASS 63, FAIL 2; `test_simplifier.py` — PASS 95, FAIL 1.
- Негативні випадки в тесті: підкладене визначення з `model: fable`, `claude-fable-5-1` чи `Fable` і шар налаштувань
  із Fable — відхилено; `opus`, `inherit` і визначення без рядка `model` — прийнято.
- `bash tests/run_all.sh --fast` — 40 наборів зелені. `bash tests/run_all.sh` — 92 набори зелені, код виходу 0
  (один повний прогін, наприкінці задачі).
- Overseer: PASS `20261011T195342Z-3467e3`.

## Витрати
Додаткових сесій Claude не було. Overseer — субагент сесії задачі.

## Commit-и
`a136863` (зміна, тести, журнал overseer-а, дві нові задачі в `todo/`) · commit цього закриття (звіт і перенесення в `done/`).

## Відкладене
- Два браки тестів від overseer-а лежать задачами в `todo/`:
  - `826` — ніщо не перевіряє, що жоден скрипт чи runner не передає запуску `--model fable`. Сьогодні таких немає:
    `--model` є лише в п'яти скриптах `evals/run_*.py`, і всюди типове значення порожнє.
  - `827` — тест мовчки пропускає шар налаштувань, якого немає на диску (`templates/project/.claude/settings.json`
    не існує), тож перевірено два шари, а не три.
- `.engine/goals.md`, рядок P5 («працює лише найсильніша модель») не змінював: Fable він не називає, а документ цілей
  змінює лише власник. Якщо хочете записати там «Opus» прямо — це окрема поправка через `/business-analyst`.
- У черзі уроків лишилось 25 кандидатів від попередніх задач; я закрив лише два свої (вони вже є задачами `826` і `827`).

## Рішення, які я ухвалив сам
- **Simplifier закріплено за `opus`, а не залишено без рядка `model`.** Без рядка він ішов би за моделлю сесії, і
  сесія, запущена на Fable, повернула б його на Fable. Ціна: якщо сесія колись піде на моделі, сильнішій за Opus,
  simplifier лишиться на Opus, доки рядок не змінять. Повернути — один рядок.
- Не чіпав як історію: `evals/baseline/`, записи в `.engine/`, копії старих задач у `tests/fixtures/board-inbox/`,
  `docs/plan/`. Перелік псевдонімів моделей, які дозволяє документація Claude Code (у `tests/test_model_roles.py` і
  журналі premises), теж лишився: це факт про поле `model`, а не закріплення.
