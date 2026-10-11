# 766 — Overseer відклав юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` — звіт

## Що змінилось для власника
- Нічого окремо: пункт закрито як дубль, за вашою відповіддю. Юніт дороблено з patch-а в задачі 739: commit `a2b20d0`,
  і overseer дав на нього PASS (запит `20261011T080431Z-d38a0a`, перша спроба після вашої відповіді).
- Вада з BLOCK 1, через яку пункт з'явився, — повідомлення hook-а `overseer_stop.py` відсилало по чернетку ADR чи
  ескалацію до спільного `.engine/overseer/ledger.md`, який оновлює лише ручний `fold`, — виправлена в тому ж commit-і:
  тепер воно називає весь журнал, `python3 .claude/hooks/journal.py show ledger`.

## Демонстрація на хвилину
```bash
git show --stat a2b20d0 | head -5                                              # робота юніта, з patch-а
grep -c '"request": "20261011T080431Z-d38a0a".*"verdict": "PASS"' .claude/state/overseer/verdicts.jsonl   # 1
grep -n 'journal.py show ledger' .claude/hooks/overseer_stop.py | head -3      # куди тепер веде повідомлення
```

## Як перевірено
- `git log`: `a2b20d0` — «739: journals one file per session (ledger, parked, anomalies, lesson queue)…», після нього
  `af95039` (739 → done).
- `.claude/state/overseer/verdicts.jsonl`: для `unit_key` `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1`
  єдиний вердикт після повернення задачі — PASS, `attempt: 1`; його test gap лежить окремою задачею 778.
- `.claude/hooks/overseer_stop.py:295–296`: текст `FRESH_ROUTE_REASON` веде до `journal.py show ledger` і прямо каже,
  що спільний `ledger.md` сам може ще не мати запису.
- У цій задачі код не змінювався, тож тести наново не запускались.

## Відкладене
- Нічого. Задача 739 закрита своїм звітом у `tasks/done/739-open-item-gitattributes-merge-union-append-only-lo/`.

## Рішення, які я ухвалив сам
- Audit юніта наново не просив: PASS на нього вже є, а відповідь — «закрий як дубль».
- Незакомічені зміни в робочому дереві — `.engine/goals.md` і видалений `.engine/goals/proposed.md` — не чіпав і не
  комітив: вони були там до початку цієї сесії й належать поправці до цілей із задачі 103 (дія `amend-goals`), не цій
  задачі. Через них `git status` після закриття не буде чистим.

## Витрати
Додаткових сесій Claude не було.

## Діапазон commit-ів
Лише commit, що переносить задачу в `done/`. Робота юніта — `a2b20d0` (задача 739).
