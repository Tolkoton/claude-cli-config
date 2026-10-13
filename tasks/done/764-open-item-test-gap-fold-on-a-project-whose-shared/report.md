# 764 — перевірка «fold на проєкті, чий shared ledger ще без жодного запису» вже стоїть і червоніє на описаній ваді — звіт

## Що змінилось для власника
- **Нічого не змінено — ні тесту, ні коду.** Перевірка, якої просить задача, уже є в `tests/test_journal.py:362`:
  «a shared ledger with no entry yet and a young session file with a note and one entry: before and after a fold, the
  entry and the note each once, and the PASS counted once». Вона прийшла тим самим commit-ом `a2b20d0` (задача 739),
  що й `journal.py`: test gap закрито ще там, а пункт на task board лишився відкритим.
- **Перевірку перевірено в цій сесії:** на коді, як він є, вона зелена; на ваді з опису задачі — червона (таблиця нижче).
- **Вади в коді тест не знайшов.** `merged()` у `.claude/hooks/journal.py:176-182` кладе текст поза форматом запису в
  heading, а не серед записів, тож після fold він не прилипає до запису, і запис із session file вдруге не додається.

## Демонстрація на хвилину
```bash
python3 tests/test_journal.py      # PASS 58   FAIL 0
```
Що робить перевірка (`tests/test_journal.py:354-366`): новий проєкт, у якому `.engine/overseer/ledger.md` — це template
без жодного запису (`:355`); у session file `by-hand.md` журналу `ledger` лежать рядок «a note written past the format»
і один запис PASS із сьогоднішнім часом (`:358`). До і після `journal.fold(fresh)` перевірка вимагає: session file
лишився, `journal.text(fresh, "ledger")` містить запис `— slice-z — PASS` рівно один раз, рядок — рівно один раз, а
`overseer_verdict.passes_in_a_row(fresh, "slice-z")` дорівнює 1.

Прогони цієї сесії. Mutant-и — у копії репозиторію в `/tmp` (прибраній); робочий `journal.py` не чіпано. Кожен mutant
міняє лише гілку stray text у `merged()` (`.claude/hooks/journal.py:178-182`):

| `journal.py` | `python3 tests/test_journal.py` | Чи червона перевірка `:362` |
|---|---|---|
| як є | `PASS 58   FAIL 0` | ні — зелена |
| mutant `tailsub` — вада з опису задачі: stray text додається як ще один запис (`entries.append(stray)`), умова `stray not in shared and stray not in head` лишається | `PASS 57   FAIL 1` | так — єдина червона |
| mutant `tail`: stray text додається як запис, а шукається лише серед записів (`stray.strip() not in seen`) | `PASS 56   FAIL 2` | так |
| mutant `noguard`: stray text іде в heading, але в shared file його не шукають (`if stray.strip():`) | `PASS 56   FAIL 2` | так |

- На `tailsub` той самий сценарій, запущений окремим скриптом, дав: запис до fold — 1, після fold — 2; рядок — 1 і 1;
  `passes_in_a_row` — 2. Це саме те, що описав overseer («case1 after fold: entry 2», PASS рахується двічі). На коді,
  як він є, той самий скрипт дав 1, 1, 1, 1 і `passes_in_a_row` 1.
- На `tailsub` сусідня перевірка `tests/test_journal.py:351` (shared ledger зі старішим записом) лишається зеленою —
  як і сказано в задачі: stray text прилипає до старішого запису, і дублікат не з'являється. Ловить ваду саме `:362`.
- На `tail` і `noguard` другою червоною є перевірка `:351`.
- Швидкий набір: `bash tests/run_all.sh --fast` → `PASS: 47 suites green (fast subset)`.

Не перевірено:
- **Журнали, крім `ledger`.** Перевірка пише stray text лише в `ledger`; у `parked`, `anomalies` і черзі уроків те саме
  тестом не показано. Гілка коду для всіх журналів одна (`merged()`), крім черги уроків, де `split()` ділить за рядками
  (`.claude/hooks/journal.py:151-156`).
- **Probe overseer-а `/tmp/ov739c/probe/p1.py` не запускав:** на сервері його вже немає; сценарій відтворено своїм скриптом.
- **Повний набір тестів не запускав:** жоден файл, крім цього звіту, не змінено.

## Витрати
- Додаткових сесій Claude не було.
- Одне читання `reader`-а — звичайний subagent у сесії runner-а.
- Швидкий набір тестів: один прогін.

## Діапазон commit-ів
- `b4b5686` — задача в `doing/`.
- наступний commit — цей звіт, журнал `reader`-а і перенесення в `done/`.

## Відкладене
- Нічого.

## Рішення, які я ухвалив сам
- **Другої такої самої перевірки не дописував.** Задача каже «дописати перевірку», але вона вже є і червоніє саме на
  описаній ваді; ще одна з тим самим змістом лише подовжила б набір. Це моє тлумачення: задача — закрити test gap, а не
  додати рядок.
- **Вадою з опису взяв mutant `tailsub`:** stray text стає записом без часу, сортування ставить його після молодого
  запису, після fold він прилипає до цього запису в shared file, і чистий запис із session file додається знову. Якого
  саме вигляду був код на першій спробі юніта, у git не лишилось (739 — один commit), тому форма mutant-а — моя
  реконструкція з тексту вердикту; числа, які вона дає, збігаються з числами probe overseer-а.
- **Mutant-и запускав у копії в `/tmp`,** щоб робоче дерево лишалось чистим.
