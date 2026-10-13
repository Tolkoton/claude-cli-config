# 1753 — 789: slice, якого builder не відкрив через testing.py, для скриптів і далі unknown

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 789-slice-never-opened

## Що сталося
Після задачі 789 активний slice без картки IN PROGRESS — це останній, відкритий командою testing.py request <slug> --point a під задачею з doing/. Якщо builder цей крок пропустив, audit request знову має slice unknown і contract null, а testing gate не має кого тримати: sealed contract у .engine/slices/ сам по собі slice активним не робить (docs/engine-limits.md, «The active slice»).

- Записано: 2026-10-13T23:41:34Z, агент, задача 789
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Вирішити, чи потрібен третій крок у gate.active_slice: коли під задачею не відкрито жодного slice-а, а в .engine/slices/ рівно один sealed contract без рядка opened, вважати активним його — тоді overseer_stop.py відповість TESTING NOT SETTLED замість audit-у без contract-а. Спершу тест на таку сцену. Розвилка: так (закриває пропуск, але при кількох contract-ах, спланованих наперед, вибору немає) або лишити межею в документі.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
