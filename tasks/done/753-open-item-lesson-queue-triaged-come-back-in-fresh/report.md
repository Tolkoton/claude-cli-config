# 753 — Черга уроків: відкинуті кандидати повертаються у свіжому клоні — звіт

## Що змінилось для власника
- Нічого міняти не довелося: вади вже немає. Її прибрала задача 739 (commit `a2b20d0`, 2026-10-11) — через добу
  після того, як цей пункт записано (2026-10-10). Кандидат, розібраний у fresh clone, більше не повертається.
- Код у цій задачі не змінювався. Додано лише сценарій відтворення поруч зі звітом (`repro.py`) і одну дрібну
  задачу в `todo/` (1727) про застарілий опис у docstring.
- Чому вада зникла: до 739 `resolve` викреслював рядок кандидата з `.engine/lesson-queue.md`, а пам'ятав id лише
  файл `.claude/state/lessons/seen.json`, якого у fresh clone немає. Після 739 `resolve` нічого не викреслює, а
  дописує resolution line (`- <дата> | resolved:<куди> | … #<id>`) у journal, який лежить у git; `add()` вважає
  відомим кожен id, що стоїть у journal. Тобто «розібрано» тепер пам'ятає git, а не одна машина — це сильніше, ніж
  те, що просила задача (дописати id у `seen.json`: він лишився б на тій самій машині).

## Демонстрація на хвилину
```bash
T=tasks/done/753-open-item-lesson-queue-triaged-come-back-in-fresh
python3 $T/repro.py; echo "exit $?"                      # сьогоднішній hook: exit 0
rm -rf /tmp/old753 && mkdir /tmp/old753 && git archive a2b20d0^ .claude/hooks | tar -x -C /tmp/old753
python3 $T/repro.py /tmp/old753; echo "exit $?"          # hook до задачі 739: exit 1, вада
python3 tests/test_journal.py | tail -1                  # PASS 58   FAIL 0
```
Сценарій — той, що в задачі: кандидати `parked` і `escalation` стоять у черзі з git, стан машини стерто (fresh
clone), перший `collect` (сів), `resolve --to discard`, ще один `collect`; далі негативний випадок — новий запис
PARKED і `collect`.

Сьогоднішній hook:
```
after resolve --to discard: []
after the next collect: [] <- must be empty
after a NEW parked entry and collect: ['c7423841'] <- must hold one
RESULT: the triaged candidates stayed out, the new one was queued
```
Hook до задачі 739 (`a2b20d0^`):
```
after resolve --to discard: []
after the next collect: ['75a5e79a', 'e06fb2ae'] <- must be empty
after a NEW parked entry and collect: ['75a5e79a', 'c7423841', 'e06fb2ae'] <- must hold one
RESULT: THE BUG: triaged candidates came back
```

## Що з «Що зробити» в задачі
- **`remember(id)` у `resolve()`** — не зроблено, бо вже не потрібно: `resolve()` закінчується викликом `close()`,
  який дописує resolution line у journal, а `add()` (`.claude/hooks/lesson_queue.py:201-202`) відмовляє кожному id,
  що стоїть у journal. `journal.py fold` рядок розібраного кандидата прибирає, а resolution line лишає, тож id
  відомий і після fold.
- **`remember` у сіві для id, що вже в черзі** — не зроблено з тієї ж причини: id, що стоїть у черзі, `add()`
  знаходить у journal, `seen.json` для цього не потрібен.
- **Тест «fresh state, кандидат у черзі з git, resolve discard — не повертається»** — уже є, його додала задача 739:
  `tests/test_journal.py:248-256`, перевірка «a fresh clone does not queue again a candidate the journal holds as
  triaged (no seen ids needed)». Вона стирає `.claude/state` двічі — до і після розбору; розбір у ній зроблено
  викликом `close()` — тим самим, яким закінчується `resolve()` (`.claude/hooks/lesson_queue.py:481`). Нового тесту
  я не писав.
- **Негативний випадок «новий кандидат після цього додається»** — показано в `repro.py` (останній крок, вивід вище);
  у наборах те, що новий запис PARKED після сіву потрапляє в чергу, тримає `tests/test_lesson_queue.py:180` —
  перевірка «a PARKED entry is collected, its RESUMED twin is not» у блоці «the collectors».

## Як перевірено
- Вада відтворюється на hook-у до 739 і не відтворюється на сьогоднішньому — два прогони `repro.py`, вивід вище.
- Наявний тест справді тримає цей захист: у копії репозиторію поза робочим деревом я прибрав з `add()` перевірку
  journal (лишив тільки `if ident in seen_ids(root):`) — `python3 tests/test_journal.py` дав `PASS 57   FAIL 1`,
  і впала саме перевірка «a fresh clone does not queue again a candidate the journal holds as triaged (no seen ids
  needed)». На незміненому коді — `PASS 58   FAIL 0`.
- `python3 tests/test_lesson_queue.py` — `PASS 101   FAIL 0`.
- Повний набір тестів не запускав: жоден файл із робочим кодом не змінено.

## Відкладене
- `tasks/todo/1727-open-item-lesson-queue-docstring-seen-ids-after-73.md`: docstring модуля
  (`.claude/hooks/lesson_queue.py:26-28`) досі каже, що кандидата пам'ятає лише `seen.json`. Поведінка правильна,
  застарів опис. Не виправив тут, бо це зміна файла hook-а, а PASS overseer-а на такі зміни зараз не записується —
  відкрита gate escalation із задачі 902.

## Рішення, які я ухвалив сам
- Не виконувати «Що зробити» дослівно: дописувати id у `seen.json` — це латати пам'ять однієї машини, коли джерелом
  правди вже став journal у git. Зайвий код без жодного випадку, який він би закривав.
- Не додавати ще один тест на шлях через `collect`: `collect` додає кандидатів лише через `add()`, а саме `add()` і
  перевіряє тест із 739; шлях через `collect` один раз показано в `repro.py`.
- `repro.py` поклав поруч зі звітом, а не в `tests/`: це доказ для цієї задачі, а не постійна перевірка.
- Звіт не читав `reader`, хоча `tasks/README.md` (правило 6) цього вимагає для задачі без робочого коду: команди
  `python3 .claude/hooks/reader.py request <задача> --report` ще немає — `reader.py request` знає лише `--record`
  (відповідь: «the following arguments are required: --record»). Її будувала задача 100, яка лежить у `blocked/`.
  `mode.py check-close` для режиму `соло` без commit-ів із робочим кодом вимагає тільки `report.md`. Записав це в
  журнал аномалій і закрив задачу в `done/`.

## Витрати
Додаткових сесій Claude не було.

## Діапазон commit-ів
`cc143c5` (задача → `doing/`) і commit, що переносить її в `done/`. Робочий код не змінено.
