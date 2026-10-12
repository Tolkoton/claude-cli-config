# 751 — ruff судить код двигуна з --target-version мінімального Python — звіт

## Що змінилось для власника
- **ruff тепер сам ловить синтаксис, якого не розуміє найстаріший підтримуваний Python.** `tests/test_engine_lint.py`
  передає йому `--target-version py311`, тож форму на кшталт рядка `testing.py:202` із задачі 748 видно й на машині,
  де `python3.11` немає.
- **Мінімальна версія записана в одному місці:** `MIN_PYTHON = "3.11"` у `.claude/hooks/tool_versions.py` (рядок 49).
  З неї тест бере і `py311` для ruff, і назву інтерпретатора `python3.11` для перевірки компіляції із задачі 748.
- **Тест сам тримає негативний випадок:** той самий виклик ruff на рядку з backslash усередині виразу f-string мусить
  бути червоним, інакше suite падає. Тобто прапорець не може тихо зникнути чи перестати щось означати.
- **Задача чекала вас не через код.** Перший audit не знайшов жодної невдалої перевірки, але PASS не приймався, поки
  була відкрита gate escalation задачі 902. Ви її закрили й відповіли «закрито»; новий overseer перевірив роботу
  наново — PASS (request `20261012T224738Z-689cdd`). Код у цій сесії не змінювався.
- **Чого це ще не ловить:** ruff із прапорцем судить лише 34 файли двигуна під `.claude/`, а не `engine.py`, `evals/`
  і `tests/`. Там уже є справжній рядок — `evals/run_simplifier_evals.py:364` має f-string, який розуміє лише
  Python 3.12. Це задача `tasks/todo/1725-open-item-test-gap-test-engine-lint-reports-a-form.md`.

## Демонстрація на хвилину
```bash
python3 tests/test_engine_lint.py      # PASS: engine lint clean
```
У виводі рядки `ok   ruff 0.17.0 check --isolated --target-version py311 <engine Python>  All checks passed!` і
`ok   ...and the same call is red on a form only a newer Python parses (a backslash inside an f-string's expression)`.

Перевірено в цій сесії на дереві `fe9e602` (Python 3.12.13; ruff 0.17.0 і mypy 2.4.0 через `uvx`):
- suite зелений: код 0, `PASS: engine lint clean`, 34 файли;
- три мутації в тимчасовому worktree (прибраному), по одній, кожна — код 1, `FAIL: engine lint has findings`:
  - `.claude/hooks/testing.py`, яким він був до виправлення 748 (`git show 568996d^:…`), —
    `.claude/hooks/testing.py:202:56: invalid-syntax: Cannot use an escape sequence (backslash) in f-strings on Python 3.11`;
  - прапорець прибрано з виклику — червоний негативний випадок (`exit 0: All checks passed!`);
  - `MIN_PYTHON` піднято до `3.12` — червоний той самий негативний випадок;
- `bash tests/run_all.sh` — `PASS: 98 suites green`, код 0 (692 секунди); усі 45 suites швидкого набору серед них;
- overseer сам відтворив зелений прогін і всі три мутації.

Не перевірено: перевірка компіляції із задачі 748 під справжнім `python3.11` — на цій машині його немає, suite друкує
рядок `note`. «Зелений на коді двигуна» показано для суду ruff над 34 файлами `.claude/`.

## Витрати
- Додаткових сесій Claude не було.
- Два audit-и overseer-а (один у першій сесії, один у цій) — звичайні subagent-и в сесії runner-а.
- Повний набір тестів: один прогін у першій сесії, один у цій.

## Діапазон commit-ів
- `1a17142` — задача в `doing/` (база).
- `d91e53b` — код і тест.
- `64d1b4c` — задача в `blocked/` з питанням; `fe9e602` — знову в `doing/` після вашої відповіді.
- наступний commit — цей звіт, turn file для overseer-а, ledger сесії, перенесення в `done/`.

## Відкладене
- `tasks/todo/1725-…` — test gap першого audit-у: розширити суд ruff із прапорцем на `engine.py`, `evals/` і `tests/`
  та виправити `evals/run_simplifier_evals.py:364`. У цій сесії перевірено, що рядок досі там:
  `uvx ruff@0.17.0 check --isolated --target-version py311 evals/run_simplifier_evals.py` — `Found 2 errors`
  (`Cannot reuse outer quote character in f-strings on Python 3.11`).
- Спостереження overseer-а, не оформлене задачею: рядок `ok   ruff … --target-version py311` у виводі suite — літерал,
  тож без прапорця він друкувався б так само; правду каже лише негативний випадок, і він у цій мутації червоний.
  Можна зробити заодно з 1725.

## Рішення, які я ухвалив сам
- **Мінімальну версію поклав у `tool_versions.py`:** там уже лежать усі версії, від яких залежить вердикт перевірки.
- **Набір файлів для ruff не розширював:** задача просить прапорець для наявного виклику; розширення — робота 1725.
- **Unit заявив руками, а не через Stop hook:** код після першого request не мінявся, тож hook audit-у не попросив би.
  Turn file `.engine/artifacts/overseer/turn-2026-10-12-board-751-close.md` і `overseer_verdict.py request` — шлях зі
  skill `overseer`, той самий, яким закрито 719, 725, 730 і 740.
- **Повний набір тестів запустив ще раз:** після першої сесії гілка отримала commit-и інших задач.
- **Задачу 1725 не закривав сам** — у `doing/` одночасно лише одна задача.
