# 758 — Брак тесту: ескіз, піднятий до соло, і карантин ескізу — звіт

## Що змінилось для власника
- Нічого окремо: перевірка, якої просить задача, вже є в `tests/test_sketch_quarantine.py` (рядки 119–124) — вона
  прийшла разом із доробленим юнітом задачі 099, commit `9367ae4`. Overseer назвав цей брак тесту на першій спробі
  юніта (запит `20261010T041355Z-370e62`), а тест дописано в наступних спробах того самого юніта.
- Код не мінявся: вади тест не знайшов. `sketch_mode()` у `.claude/hooks/gate.py` (рядок 1263) читає режим, що діє
  (`.current`), тож задача з рядком «Режим: ескіз» і розділом `## Режим піднято` до соло змінює `src/app.py` без
  block-а `sketch/outside`.

## Демонстрація на хвилину
```bash
python3 tests/test_sketch_quarantine.py | grep "raised to соло"   # ok — … the mode in force decides — no sketch/outside
python3 tests/test_sketch_quarantine.py | tail -1                 # PASS 29   FAIL 0
```

## Як перевірено
- Червоний прогін — на тому, що описав overseer. У `.claude/hooks/gate.py`, рядок 1263, тимчасово замінив
  `.current == "ескіз"` на `.owner == "ескіз"` (mutant «читає рядок власника») і запустив
  `python3 tests/test_sketch_quarantine.py`: `PASS 28   FAIL 1`, exit 1, червона рівно одна перевірка —
  `FAIL a sketch raised to соло (mode.py raise, the way out the block names): the mode in force decides — no sketch/outside   [('src/app.py', None, 'sketch/outside')]`.
- Зелений прогін — на коді, як він є (`git checkout -- .claude/hooks/gate.py`, `git status` чистий):
  `PASS 29   FAIL 0`, exit 0.
- Швидкий набір тестів: `bash tests/run_all.sh --fast` — `PASS: 45 suites green (fast subset)`.

## Відкладене
- Нічого.

## Рішення, які я ухвалив сам
- Нової перевірки не дописував: наявна робить саме те, що описано в «Що зробити» (той самий сценарій, і червоніє на
  названому mutant-і), друга така сама була б дублем.
- Mutant спершу спробував на копії `.claude/hooks/` у тимчасовій теці — там червоніли три інші перевірки, бо копії
  бракувало решти репозиторію, а не через mutant; цей прогін відкинув і повторив на справжньому файлі, після чого
  повернув його через `git checkout`.
- Читача (`reader`) на цей звіт не просив: `python3 .claude/hooks/reader.py request … --report` з правила 6 у цьому
  репозиторії ще немає (`reader.py request` приймає лише `--record`; задача 100, яка це будує, лежить у `blocked/`).
  `python3 .claude/hooks/mode.py check-close` на цю задачу відповідає «мінімум режиму «соло» є».
- Повний набір тестів не запускав: жоден файл коду чи тесту не змінено.

## Витрати
Додаткових сесій Claude не було.

## Діапазон commit-ів
Лише commit-и task board цієї задачі (`f55a3e9` — у `doing/`, і той, що переносить її в `done/`); робочого коду немає.
