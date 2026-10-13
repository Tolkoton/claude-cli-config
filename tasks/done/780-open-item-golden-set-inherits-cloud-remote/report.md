# 780 — Golden set дає однаковий результат локально і в хмарній сесії: звіт

## Що змінилось для власника
- **Golden set більше не залежить від того, де його запущено.** `evals/run_hook_scenarios.py` тепер прибирає з
  середовища кожного hook-а змінні, які кажуть «де я»: `CLAUDE_CODE_REMOTE` (хмарний контейнер) і
  `CLAUDE_UNATTENDED_SESSION` (runner task board). Другу він прибирав і раніше; тепер обидві названо в одному місці —
  `PLACE_VARIABLES` (`evals/run_hook_scenarios.py:63-66`, застосування — рядки `226-227`).
- **Сценарій, якому така змінна потрібна, ставить її сам** у своєму `env`, як хмарні сценарії робили й досі. Жодного
  сценарію і жодного hook-а не змінено.
- **Обрано перший із двох варіантів задачі** (прибирає runner, а не сам сценарій `bd-commit-local-…`): так захищено
  всі 281 сценарій і кожен майбутній, а не один.
- **Нова suite `tests/test_golden_place_env.py`** (9 перевірок, близько 4 с, у швидкому наборі — `tests/fast-suites.txt`).

## Демонстрація на хвилину
```bash
CLAUDE_CODE_REMOTE=true python3 evals/run_hook_scenarios.py --engine-ref HEAD --compare evals/baseline/linux-ubuntu-22.04/results-task-102.json | tail -3
python3 tests/test_golden_place_env.py
```

Прогони цієї сесії:

| Що запущено | Результат |
|---|---|
| увесь golden set із `CLAUDE_CODE_REMOTE=true`, до зміни | `FAIL`: `bd-commit-local-with-cloud-switch-on` — `allow`, очікувано `block` |
| те саме після зміни, проти `results-task-102.json` | `identical behaviour in all 281 scenarios`, `PASS 281/281` |
| увесь golden set без змінної, після зміни | `PASS 281/281` |
| `tests/test_golden_place_env.py` на runner-і до зміни (RED, mutant «успадкування повернуто») | `PASS 5   FAIL 4` |
| `tests/test_golden_place_env.py` після зміни | `PASS 9   FAIL 0` |
| mutant: зі списку прибрано `CLAUDE_UNATTENDED_SESSION` | `PASS 7   FAIL 2` |
| `bash tests/run_all.sh --fast` | `PASS: 50 suites green (fast subset)` |
| `bash tests/run_all.sh` | `PASS: 103 suites green` |

- **Що перевіряє suite.** У синтетичному sandbox-і hook відмовляє, щойно бачить будь-яку з двох змінних. Runner,
  запущений із ними, доводить сценарій без `env` до hook-а без них; негативні випадки — сценарій, що ставить змінну сам,
  доходить із нею. Окремо — частковий прогін справжнього набору (`--only bd-commit-`) під `CLAUDE_CODE_REMOTE=true`.
- **Число RED.** Під час роботи перший запуск тесту на незміненому runner-і дав `PASS 4   FAIL 5`; разом із виправленням
  я переніс умову `returncode == 0` з однієї перевірки в іншу, і остаточний тест на старому runner-і дає `PASS 5   FAIL 4`
  (це відтворив overseer на копії в `/tmp`). Причина червоного та сама.
- Overseer: **PASS** `20261013T134859Z-0f3ef7`. Він сам відтворив GREEN, RED на старому runner-і, mutant без
  `CLAUDE_UNATTENDED_SESSION`, ще один власний mutant (`env` сценарію накладено до прибирання — `PASS 4   FAIL 5`), увесь
  golden set із обома змінними (`PASS 281/281`) і швидкий набір.

Не перевірено:
- **У справжньому хмарному контейнері набір у цій сесії не запускався.** «Хмарне середовище» тут — локальний shell зі
  встановленою `CLAUDE_CODE_REMOTE=true`, тобто саме та умова, яку називає задача.
- **Інші змінні контейнера не прибираються**: `CLAUDE_CODE_REMOTE_SESSION_ID` (жоден hook її не читає), `CLAUDE_CODE_SESSION_ID`
  (це «яка сесія», а не «де я»; сценарії journal ставлять її самі — задача 778), `CLAUDECODE`. Прогони цієї сесії й
  overseer-а йшли з `CLAUDECODE` і `CLAUDE_CODE_SESSION_ID` у середовищі — 281 із 281.

## Витрати
- Додаткових сесій Claude не було. Overseer — subagent цієї сесії.
- Golden set цілком: п'ять прогонів (три до зміни, два після). Швидкий набір: один прогін. Повний набір: один прогін.

## Діапазон commit-ів
- `ba8c0cb` — задача в `doing/`.
- `3d008a6` — `evals/run_hook_scenarios.py`, `tests/test_golden_place_env.py`, `tests/fast-suites.txt` і запис overseer-а в journal.
- наступний commit — цей звіт і перенесення в `done/`.

## Відкладене
- **Команда в документації порівнює із застарілим baseline.** `docs/working-on-the-engine.md:15` і `evals/README.md:36`
  називають `results-task-738-086.json`. Проти нього набір показує 9 відмінностей і виходить із кодом 1 на будь-якій
  машині, без жодної хмарної змінної: це дев'ять сценаріїв push із задачі 603, яких у тому baseline немає. Новіший
  `results-task-102.json` записала задача 102, яка чекає вашої відповіді в `blocked/`, тому документацію я не чіпав.
  Про те саме вже писали звіти задач 739 і 090.

## Рішення, які я ухвалив сам
- **Прибирає runner, а не один сценарій** — причину названо вище.
- **У списку дві змінні, не більше.** «І подібні» із задачі я прочитав як «змінні, за якими hook вирішує, де він»: серед
  змінних, які читають hooks, такі лише ці дві. `CLAUDECODE` агентові прибирати заборонено (`block-dangerous.sh`), і
  жоден hook golden set-у за нею нічого не вирішує.
- **Порівнював із `results-task-102.json`**, а не з baseline, названим у задачі: лише проти нього «зелений» узагалі можливий.
- **Suite додано у швидкий набір** (близько 4 с): golden set — двійник gate-а, тож те, що він передає hook-ові, варто
  перевіряти на кожному Stop.
- **Другий mutant зроблено на робочому дереві з поверненням рядка**; `git diff` після цього показував лише задуману зміну.
