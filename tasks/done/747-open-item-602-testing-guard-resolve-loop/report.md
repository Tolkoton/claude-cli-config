# 747 — testing.py guard на symlink loop: звіт

## Що змінилось для власника
- Guard tester-а (PreToolUse hook `testing.py guard`) на Python 3.11–3.12 падав із traceback-ом на `file_path`, що є
  symlink loop (`Path.resolve()` кидав `RuntimeError`). Hook із exit 1 нічого не вирішує, тож такий запис tester-а
  проходив без рішення. Тепер шлях іде через `os.path.realpath()`, як у `goals.py`, і петля отримує звичайне рішення:
  поза тестовими файлами — відмову «The tester writes test files only», як тестовий файл — дозвіл.
- Повний запис бага (контракт і звіт виправлення) — `.engine/bugs/007-testing-guard-resolve-loop.md`.

## Демонстрація на хвилину
```bash
python3.12 tests/test_testing.py | grep "bug 007"
python3 .claude/hooks/bugfix.py prove --record .engine/bugs/007-testing-guard-resolve-loop.md \
  --test tests/test_testing.py --cmd "python3.12 tests/test_testing.py" --expect "RuntimeError: Symlink loop"
```

## Як перевірено
- Відтворено з першої спроби: під 3.12 три шляхи-петлі давали `rc=1` і `RuntimeError: Symlink loop`, під 3.13 — рішення
  guard-а (запис, розділ 2).
- Тест `tests/test_testing.py`, два випадки «bug 007». До виправлення під python3.12: `190 passed, 2 failed`
  (`rc=1 RuntimeError: Symlink loop`). Після: `192 passed, 0 failed` під 3.12 і під 3.13.
- `bugfix.py prove`: `PROVED: tests/test_testing.py fails on eb7d167 and passes on the working tree; the failure shows
  «RuntimeError: Symlink loop»`.
- Бюджет: 0 нових файлів, +1 рядок коду, 0 нових публічних імен (`complexity_budget.py check`: within budget).
- `test_engine_lint` — чисто; `bash tests/run_all.sh --fast` — 38 наборів зелені.
- Overseer: **PASS** `20261010T113546Z-b1deb7`. Він сам повторив доказ (PROVED) і RED під python3.12. Його брак тесту —
  регресійний тест червоніє лише під python3.12, а набори й Stop gate запускаються під python3 (3.13). Це відкритий пункт
  `tasks/todo/768-open-item-test-gap-the-bug-007-guard-cases-also-ru.md`.

## Що варто знати
- Під Python 3.11 `testing.py` не запускається взагалі: `SyntaxError` у f-рядку (форма з 3.12). Це задача 748, вона в
  черзі. Поки її не виправлено, виправлення 747 на 3.11 не видно.
- Ті самі `resolve()` в `evals/` — предмет задачі 719 (теж у черзі). У hook-ах інших незахищених місць пошук не знайшов
  (запис, розділ 4).

## Витрати
Додаткових сесій Claude не було. Overseer — субагент цієї сесії.

## Рішення, які я ухвалив сам
- Тест — у наборі `test_testing` (розділ про guard), а не в новому файлі: там уже є всі перевірки guard-а, і набір під
  3.12 проходить за 32 секунди.
