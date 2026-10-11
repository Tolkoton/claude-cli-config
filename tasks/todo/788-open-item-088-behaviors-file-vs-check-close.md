# 788 — Запис поведінок builder-а в .engine/slices/ ламає check-close і лічильник self-added

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 088-behaviors-file-vs-check-close

## Що сталося
Задача 088 (fresh-install E2E). Навичка slice-builder (.claude/skills/slice-builder/SKILL.md:181) велить для sealed contract-а тримати список поведінок поруч: `.engine/slices/<slug>.behaviors.md`. `mode.py check-close` (mode.py:434) у режимі «конвеєр» вважає кожен .md у .engine/slices/ slice contract-ом і вимагає печатки — у пробі агент отримав відмову закриття, переніс файли в .engine/artifacts/build/ і записав аномалію. Поруч друга вада: `testing.py self_added` (testing.py:582) рахує кожен рядок зі словом «self-added» у файлах `<slug>*.md` — у пробі рядок «No behaviour was self-added» дав self_added_behaviours = 1 (це помітив overseer); той самий glob `<slug>*.md` зачепить і чужий slice, чий slug починається так само (todo і todo-done).

- Записано: 2026-10-11T09:59:28Z, агент

## Що зробити
Спершу тести, червоні на обох випадках: (1) check-close у режимі «конвеєр» із sealed contract-ом і файлом <slug>.behaviors.md поруч; (2) self_added на рядку-запереченні й на двох slug-ах зі спільним початком. Далі узгодити одне місце для запису поведінок між навичкою, mode.py і testing.py, а лічильник зробити точним (позначка на рядку поведінки, а не слово будь-де; файли лише цього slug-а).

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
