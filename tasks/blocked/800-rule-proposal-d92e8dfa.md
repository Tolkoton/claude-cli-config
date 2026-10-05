# 800 — Зробити урок правилом? Пропозиція RP-d92e8dfa

Залежить від: —
Аудит потрібен: ні
Пропозиція правила: RP-d92e8dfa

## Що сталося
Із роботи над проєктом винесено урок, схожий на постійне правило. Уроки не стають правилами
самі: це правило з'явиться лише з вашої згоди. Наглядач може радити, але не вирішує.

- Текст правила — саме так, слово в слово, він потрапить у `.engine/rules.md`, який читає кожна розмова:

  > A suite that runs a hook pins CLAUDE_PROJECT_DIR to its own sandbox: inherited, the Stop gate hands it this repository, and the suite answers differently from the gate than by hand.

- Чому: The Stop gate runs TEST_CMD with CLAUDE_PROJECT_DIR naming this project. tests/test_deny_gaps.py let block-dangerous.sh read this repository's branch through it, so on an unattended/* branch its commit cases came back ALLOWED — green by hand, red from the gate (2026-10-02, package 3c fix, X7). test_deny_hooks.py had needed the same pin before it. Nothing checks a new suite for it: 24 test files mention the variable and each pins it by hand.
- Звідки урок: lesson #d92e8dfa (escalation, -, 2026-10-03)
- Рекомендація наглядача: немає

## Що зробити
Це питання до власника, не робота для агента. Відповіді «так» і «ні» виконує виконавець дошки.
Якщо власник відповів інакше — це вказівка агентові: виконай її (щоб змінити текст правила,
закрий цю пропозицію — `python3 .claude/hooks/lesson_queue.py reject d92e8dfa --why "<слова власника>"` —
і подай нову), запиши у звіт і закрий задачу. Сам `promote` не запускай і `Відповідь:` не заповнюй.

## Готово, коли
Власник відповів, і виконавець записав правило або закрив пропозицію.

## Питання до власника
Варіанти відповіді:
- `так` — урок стає правилом: рядок вище буде додано до `.engine/rules.md`.
- `ні` — правилом не стає; пропозицію закрито.
- будь-який інший текст — вказівка агентові (наприклад, як переписати правило).

1. Зробити це правилом?
   Дія виконавця: promote-rule eacbb35d1a61b1f5522587ae6aaf19e2defbab2d8e35c521ff9d96163d5bdd73
   Відповідь: Не правилом. Закрий цю пропозицію і зроби натомість: спільний помічник для тестів, який сам ставить CLAUDE_PROJECT_DIR у тимчасову теку тесту, і перевірку, яка ловить нові набори тестів, що запускають hook-и без цього помічника. Детерміновані тести; коротко у звіт.
