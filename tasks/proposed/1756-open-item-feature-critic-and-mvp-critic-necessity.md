# 1756 — feature-critic and mvp-critic: necessity and proportionality as in master-critic

Залежить від: —
Аудит потрібен: ні

## Що сталося
Board 201 gave master-critic's goals-fit lens four checks (покриття, необхідність, пропорційність захисних механізмів, узгодженість доводів) and put necessity and proportionality before the search for bypasses; the owner kept feature-critic and mvp-critic out of that task. The same failure — a critic hunting bypasses of a mechanism nobody asked for — can happen at the feature level and in an MVP design.

- Записано: 2026-10-18T20:00:12Z, board 201
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Give feature-critic's and mvp-critic's goals lens the necessity and proportionality checks and the same order (before inversion/premortem/bypasses), and the one fix for an element without a source (remove it or move it to proposals); a definition test like tests/test_goals_roles.py.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
