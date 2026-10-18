# 1757 — master-critic: a person's manual work is not the system's mechanism (scene h, board 501)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: focus-501-h

## Що сталося
Scene h of evals/run_focus_evals.py failed after on both attempts (evals/baseline/linux-ubuntu-22.04/focus-evals-task-501.json): on domain-map-rev2 the master-critic says REVISE and names G3 and G6, but it never objects that «власник читає все і пише висновки» puts the conclusions in the owner's hands, while G3 and G6 say the system makes them. It took the owner's manual step as the mechanism. v0.13.0 missed it too.

- Записано: 2026-10-18T21:45:17Z, агент
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
In .claude/agents/master-critic.md, goals-fit check 5 (покриття): add one sentence — a step done by a person (the owner reads, writes, approves) is no mechanism of the system where the line says the system does it; and an owner's amendment like «власник читає все» is a right of access, not a duty to write (the rule master-architect.md already has). Then rerun: python3 evals/run_focus_evals.py --scenes h i

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
