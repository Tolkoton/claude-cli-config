# 719 — Symlink loop дає traceback у doc_audit.py та в скриптах evals/ — звіт

## Що змінилось для власника
- **Symlink loop більше не дає traceback у чотирьох скриптах поза hooks.** Шлях, який є посиланням на себе
  (`loop -> loop`), тепер отримує ту саму написану відмову, що й шлях у нікуди:
  - `doc_audit.py`, посилання в Markdown на loop → `ERROR <файл>:<рядок> - broken link to '<ціль>'.`, код 1;
  - `evals/run_audit_scenarios.py --tasks-dir <loop>` → `refusing to start paid sessions: no task of this session is in
    <loop>/doing/.`, код 2;
  - `evals/environment.py`, `baseline_folder(<loop>)` → `None`, тож `--out <loop>` у runner-ах evals проходить аргумент;
  - `evals/run_hook_scenarios.py`: крок setup, що пише крізь loop, і `project_dir`-loop → `sandbox error: …`, код 2;
    `--hooks-dir <loop>` → кожен сценарій `absent`.
- **Однаково на Python 3.12 і 3.13.** До виправлення на 3.12 падали всі шість місць, на 3.13 — два (setup і
  `project_dir` у hook runner-і).
- **Побічна зміна, яку варто знати.** У `run_hook_scenarios.py` `except SandboxError` став `except (SandboxError,
  OSError)`. Тому будь-яка інша `OSError` під час прогону сценаріїв (наприклад, файл сценарію не читається) тепер теж
  друкується як `sandbox error: <помилка>` з кодом 2 — раніше це був traceback з кодом 1. Окремого тесту на цю ширшу
  поведінку немає; overseer назвав це найсильнішим запереченням, але не блоком.
- **Задача чекала вас не через код.** Перший audit не знайшов жодної невдалої перевірки, але PASS не приймався, поки була
  відкрита gate escalation задачі 902. Ви її закрили і відповіли «закрито»; новий overseer перевірив роботу наново —
  PASS (request `20261012T103424Z-43b5b4`). Код у цій сесії не змінювався.
- **Повний опис — у bug record** `.engine/bugs/008-resolve-loop-outside-hooks.md`: відтворення, причина, перелік кожного
  рядка з `resolve(` у репозиторії поза `tests/` (виправлено, вже закрито раніше, або свідомо лишено), доказ.

## Що з пунктів задачі
| Місце із задачі | Що зроблено |
|---|---|
| `doc_audit.py:152` | виправлено, тест є |
| `evals/run_audit_scenarios.py:649` (тепер `:703`) | виправлено, тест є |
| `evals/environment.py:78` | виправлено, тест є |
| `evals/run_hook_scenarios.py:115`, `:210`, `:356` | виправлено, тест на кожне |
| `evals/run_simplifier_evals.py:84` | рядка вже немає: після задачі 110 скрипт передає `tasks_dir` у `board_state.py`, який іде через `os.path.realpath` |
| корені (sandbox, `--root`, тека сценаріїв) | не чіпав: задача сама каже, що написаної відмови для кореня немає |
| пошук тих самих місць по всьому репозиторію поза `tests/` | зроблено, кожен рядок названо в розділі 4 bug record |

## Демонстрація на хвилину
```bash
python3 tests/test_symlink_loop_outside_hooks.py     # PASS 19   FAIL 0
d=$(mktemp -d); ln -s tl "$d/tl"
python3 evals/run_audit_scenarios.py --tasks-dir "$d/tl"   # refusing to start paid sessions: no task of this session is in …/tl/doing/.  (код 2, без traceback)
```
Перевірено в цій сесії на дереві `35074b7`:
- suite — `PASS 19   FAIL 0` на Python 3.12.13 і на 3.13;
- `python3 .claude/hooks/bugfix.py prove …` (повна команда — розділ 6 bug record) — `PROVED`: на `1e28bc5` suite
  червоний (`PASS 11   FAIL 8`), на дереві зелений;
- `bash tests/run_all.sh` — `PASS: 98 suites green`, код 0. Два перші запуски результату не дали (перший зупинив ліміт
  часу мого інструмента, другий я сам убив помилковим `pkill`); третій дійшов до кінця;
- overseer повторив усе це сам і додав три власні мутанти — кожен робить suite червоним.

Не запускав знову в цій сесії (це прогони попередньої сесії, розділ 5 bug record): шість мутантів автора, 281 сценарій
hooks, `ruff` і `mypy` на змінених файлах. `ruff` повторив overseer: `All checks passed!`.

## Витрати
- Додаткових сесій Claude скриптами evals не запускав. Два audit-и overseer-а (по одному на сесію задачі) — звичайні
  subagent-и в сесії runner-а.
- Повний набір тестів: один прогін до кінця у першій сесії (97 suites), один у цій (98 suites).

## Діапазон commit-ів
- `1e28bc5` — задача в `doing/` (база виправлення).
- `4833eca` — виправлення, suite, bug record, і перенесення в `blocked/` з питанням.
- `35074b7` — задача знову в `doing/` після вашої відповіді.
- commit цього звіту — перенесення в `done/`, запис другого audit-у в bug record, turn file для overseer-а.

## Відкладене
- `tasks/todo/1706-open-item-719-doc-audit-markdown-file-loop.md` — Markdown-файл, який сам є symlink loop: `doc_audit.py`
  падає з `OSError` у `read_text`. Інша причина (не `resolve()`), написаної відповіді для неї немає.
- Тесту на ширший `except` у `run_hook_scenarios.py` (стороння `OSError` → `sandbox error`, код 2) немає. Overseer це
  назвав, але test gap не відкрив; окремої задачі я не клав — поведінку описано в bug record, розділ 5.
- Lesson у черзі: `#075a8475` — пошук тієї самої причини має охоплювати всі файли репозиторію, а не лише теки з першого
  звіту.

## Рішення, які я ухвалив сам
- **Unit заявив руками, а не через Stop hook.** Stop hook просить audit лише коли код змінився після останнього request,
  а тут код не мінявся. Тому: turn file `.engine/artifacts/overseer/turn-2026-10-12-board-719-close.md` і
  `overseer_verdict.py request` — шлях, описаний у skill `overseer`.
- **Повний набір тестів запустив ще раз,** хоча в першій сесії він уже був зелений: відтоді гілка отримала commit-и
  інших задач, і overseer мав судити теперішнє дерево.
- **Bug record дописав одним рядком** про другий audit (розділ 7); решту не чіпав.
- (з першої сесії) `os.path.realpath` замість `resolve()` і ширший `except` замість двох власних перевірок у
  `run_scenario`: перший варіант відхилив complexity budget (`max_cyclomatic_per_function`), другий не додає жодної
  гілки.
