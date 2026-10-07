# 900 — Gates зупинили роботу: потрібне ваше рішення

Залежить від: —
Аудит потрібен: ні
Ескалація gates: 2026-10-07T07:40:13Z

## Що сталося
Перевірки наприкінці ходу (gates) не пройшли 3 раз(и) поспіль, і агент не зміг цього
виправити. Хід завершено; зроблене лежить на диску. Поки це питання відкрите, overseer не
приймає роботу, яка зачіпає ці файли.

- Slice: (none)
- Файли:
  - .claude/commands/owner-review.md
  - .claude/hooks/block-dangerous.sh
  - .claude/hooks/protected-path-list.sh
  - .claude/hooks/shell_paths.py
  - .claude/references/hooks.md
  - docs/engine-limits.md
  - evals/scenarios/hooks/10-block-dangerous.json
  - evals/scenarios/hooks/20-protect-paths.json
  - tasks/README.md
  - templates/project/tasks/README.md
  - tests/fast-suites.txt
  - tests/test_board_review.py
  - tests/test_overseer_readonly.py
  - tests/test_owner_perimeter.py
- На чому зупинилося:
  - TESTS FAILED (bash tests/run_all.sh --fast):
- Повний звіт (на сервері): `.claude/state/gate/last-report.json`

## Що зробити
Це питання поставили gates, а не агент. Агент на нього не відповідає і сам ескалацію не
закриває: відповідь «так» виконує runner. Якщо власник відповів інакше — це
вказівка агентові: виконай її, допиши внизу нове питання «Тепер закрити ескалацію?» з порожнім
рядком відповіді й поверни задачу в `tasks/blocked/`.

## Готово, коли
Власник відповів «так», і runner закрив ескалацію.

## Питання до власника
Варіанти відповіді:
- `так` — рівно це одне слово: зауваження gates прийнято або вже виправлено; ескалацію буде закрито,
  роботу з цими файлами можна приймати далі.
- будь-який інший текст (і «так, але…» теж) — вказівка агентові, що саме виправити; ескалація
  лишається відкритою.

1. Закрити ескалацію?
   Відповідь: так
