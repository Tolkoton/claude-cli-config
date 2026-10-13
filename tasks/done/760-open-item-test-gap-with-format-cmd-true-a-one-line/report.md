# 760 — FORMAT_CMD="true" вимикає prettier handler і для .toml та .yaml — звіт

## Що змінилось для власника
- **Брак тесту закрито.** `tests/test_format_on_edit.py` тепер тримає й два розширення вбудованого prettier handler-а,
  яких не тримала жодна перевірка: з `FORMAT_CMD="true"` зміна одного рядка в `tool.toml` і в `prices.yaml` не дає
  жодного виклику formatter-а і лишається diff-ом в один рядок (numstat `1 1`) — у випадках OFF-1 і OFF-2.
- **Нові перевірки не порожні.** Control OFF-3 (`FORMAT_CMD` порожній) вимагає, щоб prettier був викликаний саме на цих
  двох файлах і diff-и виросли.
- **Код hook-а не мінявся:** вади тест не знайшов. Off switch у `.claude/hooks/gate.py` (`format_file`, рядок 1226)
  повертається раніше, ніж дивиться на розширення.
- **Задача чекала вас не через код.** Перший audit не знайшов жодної невдалої перевірки, але PASS не приймався, поки
  була відкрита gate escalation задачі 902. Ви її закрили й відповіли «закрито»; новий overseer перевірив роботу
  наново — PASS (request `20261013T033733Z-a64a23`), браку тесту не назвав. Код у цій сесії не змінювався.

## Демонстрація на хвилину
```bash
python3 tests/test_format_on_edit.py      # PASS 29   FAIL 0
```
У виводі під `OFF-1` рядок `ok   no ruff, black, prettier or jq call for .py, .md, .json, .yml, .toml, .yaml`, під
`OFF-3` — `ok   the built-in handlers ran and the diffs grew: OFF-1 and OFF-2 are not vacuous`.

Перевірено в цій сесії на дереві `be0ab01`:
- зелений прогін: код 0, `PASS 29   FAIL 0`;
- червоний прогін, у тимчасовому worktree (прибраному): рядок 1226 `.claude/hooks/gate.py` звужено до
  `if fmt.strip() == "true" and ext in ("md", "yml", "json", "py"):` — код 1, `PASS 26   FAIL 3`: OFF-1 «the engine
  formats nothing» (у журналі `prettier --write --log-level silent …/tool.toml` і `…/prices.yaml`), OFF-1 «a one-line
  edit must stay a one-line diff» (обидва файли `more`), OFF-2 «the off switch covers the built-in handlers»;
- брак був справжній: тест, яким він був до commit-а `c65a11e`, на тому самому mutant-і — `PASS 29   FAIL 0`;
- `bash tests/run_all.sh` — `PASS: 99 suites green`, код 0 (1105 секунд); швидкий набір окремо запустив overseer:
  `PASS: 46 suites green (fast subset)`;
- overseer сам відтворив зелений прогін, червоний на mutant-і та прогін старого тесту.

Не перевірено: справжній prettier. Тест, як і весь suite, ставить на PATH shim-и, що записують свої аргументи й
дописують рядок у файл; що справжній prettier переписав би `.toml` і `.yaml` файли двигуна — твердження першого
audit-у, тут не міряне.

## Витрати
- Додаткових сесій Claude не було.
- Два audit-и overseer-а (один у першій сесії, один у цій) — звичайні subagent-и в сесії runner-а.
- Повний набір тестів: один прогін у першій сесії, один у цій.

## Діапазон commit-ів
- `c65a11e` — тест (один файл, 9 рядків додано, 3 прибрано).
- `be0ab01` — задача знову в `doing/` після вашої відповіді.
- наступний commit — цей звіт, turn file для overseer-а, ledger сесії, перенесення в `done/`.

## Відкладене
- Нічого. Overseer нових test gaps не назвав.

## Рішення, які я ухвалив сам
- **Окремого випадку OFF-4 не писав:** два файли додано до спільного набору `UNFORMATTED`, тож ті самі три випадки
  (OFF-1, OFF-2 і control OFF-3) тримають і нові розширення.
- **Unit заявив руками, а не через Stop hook:** код після першого request не мінявся, тож hook audit-у не попросив би.
  Turn file `.engine/artifacts/overseer/turn-2026-10-13-board-760-close.md` і `overseer_verdict.py request` — шлях зі
  skill `overseer`, той самий, яким закрито 719, 730, 740, 751, 756 і 757.
- **Повний набір тестів запустив ще раз:** після першої сесії гілка отримала commit-и інших задач.
- **Неточність у turn file лишив як є:** там швидкий набір першої сесії названо «45 suites»; сьогодні їх 46 (один suite
  додано пізніше). Turn file — те, що читав overseer, тому після PASS його не правив.
