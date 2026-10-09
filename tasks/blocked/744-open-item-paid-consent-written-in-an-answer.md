# 744 — Згода на платні прогони, написана у відповіді, нічого не відкриває — двічі за день

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: paid-consent-written-in-an-answer

## Що сталося
Задачі 727 і 729 (обидві — open-item із питанням «дозволити платні прогони?»): власник відповів «Так … Платні прогони: так» у рядку «Відповідь:», задача повернулась у чергу, а runner платних прогонів відмовив, бо рядок читається лише вгорі задачі. Обидві задачі пішли в blocked/ вдруге з тим самим питанням — два зайві кола через власника. Причина — формулювання питання: воно не каже, куди писати рядок.

- Записано: 2026-10-07T14:31:23Z, агент

## Що зробити
Зроби так, щоб питання про платні прогони саме вело власника до дії, яка відкриває прогін: або board.py open-item / текст питання каже прямо «додайте вгорі задачі рядок Платні прогони: так», або board.py unblock, побачивши у відповіді на таке питання «Платні прогони: так», зупиняється з підказкою замість повернення в чергу. Який із двох — вирішує агент; захист (згода лише окремим рядком власника вгорі задачі) не послаблювати. Платних прогонів не треба.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Чому зупинилась
- 2026-10-09T00:11:39Z — overseer тричі поспіль відхилив один юніт (-|744-open-item-paid-consent-written-in-an-answer|unit 1); runner переніс задачу в `blocked/` і взяв наступну.
  - BLOCK 1 (2026-10-08T22:45:39Z, запит `20261008T222941Z-ab3426`, перевірка #1): false-DONE — the turn's figures reproduce, but the task's goal is not met for tasks made from the template. The goal (744 «Що зробити») is that the question leads the owner to the action that opens the run. Every task made from tasks/TEMPLATE.md already has the header line `Платні прогони: ні`, and the new note still says «допишіть угорі цієї задачі окремий рядок `Платні прогони: так`». An owner who does exactly that and answers «додано» ends up with two «Платні прогони:» lines. Two lines give no leave and leave paid_unread true. unblock returns the task to todo/ anyway, and paid_refusal refus
  - BLOCK 2 (2026-10-08T23:22:24Z, запит `20261008T230546Z-9340e7`, перевірка #4): masked test gap: no test checks that «додано» counts only as the answer to the board's own note. If `noted and` is dropped at .claude/unattended/board.py:593, tests/test_board.py still gives PASS 292 FAIL 0, yet the turn lists exactly this mutant («додано» without a note before it) as CAUGHT. That wrong version keeps back any answered blocked task whose last answer is «додано» and whose header has no leave, for example an agent's credential question «додайте токен … і напишіть тут «додано»». The board then writes a false paid-runs note on it instead of returning it to todo/. Fix: add a check w
  - BLOCK 3 (2026-10-09T00:09:38Z, запит `20261008T234702Z-1473c0`, перевірка #4): masked test gap: the tests never check that the leave is caught when it is in an answer that is not the last one. If board.py:595 `any(PAID_ANSWER.search(answer) for answer in answers)` becomes `bool(answers) and bool(PAID_ANSWER.search(answers[-1]))`, tests/test_board.py still gives 298/0 and tests/test_board_runner.py 273/0. That wrong version brings back the 744 failure for every task with more than one question. Example: question 1 «Дозволити платні прогони?» answered «Так… Платні прогони: так», question 2 «A чи B?» answered «B». The task goes back to todo/ with no note, the paid run is re

## Питання до власника
1. Три overseer-и поспіль відхилили юніт цієї задачі; їхні вердикти — у розділі «Чому зупинилась». Що робити далі? Будь-яка відповідь поверне задачу в чергу, і юніт отримає три нові спроби; вказівку агентові напишіть тут же.
   Відповідь:
