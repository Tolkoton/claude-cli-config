# 1759 — /master-architect «Читання цілей»: the owner's two roles, non-goals as nothing, research ideas only in «Пропозиції» (scene j, board 501)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: focus-501-j

## Що сталося
Scene j failed on both attempts (6 of 7 rubric points, then 4 of 7). Both times no question put G4 next to P3 for the owner who is a user and the developer at once (attempt 1 decided it alone in the G4 row; attempt 2 asked about G4 with G6). Attempt 2 also turned N3 into a mechanism (stop picking a week on an injury) and offered the researcher's injury filter as an option of a question, and did not put the consequences of D1 to the owner. The step in .claude/commands/master-architect.md (M1, step 1) does not name the two-role check, which business-analysis.md has for preseal.

- Записано: 2026-10-18T21:45:17Z, агент
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
In .claude/commands/master-architect.md, M1 step 1: (a) for every pair of lines, check the one person with two roles (the owner as a user and as the developer) and, when two lines pull apart for one role, ask the owner with both lines quoted; (b) a non-goal is never offered as a mechanism option in a question — a question about a non-goal asks only whether anything is needed at all; (c) research ideas appear only under «Пропозиції», never as options of a question; (d) a done-when line with a recurring ask of people (who, how often, who does not come back) is put to the owner with those consequences. Then rerun: python3 evals/run_focus_evals.py --scenes j

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
