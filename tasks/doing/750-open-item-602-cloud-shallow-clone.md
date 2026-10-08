# 750 — Свіжий хмарний клон shallow: дві suites fast-набору червоні

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 602-cloud-shallow-clone

## Що сталося
Знайдено в задачі 602. Хмарна сесія стартує з shallow clone (88 commit-ів, жодного tag). tests/test_legacy_records_survive.py потребує tag v0.10.1 (FAIL v0.10.1 is available as the pre-move engine), tests/test_analyst_evals.py — commit cebc005 (FileNotFoundError …/dry/before/.claude/agents/master-critic.md). Обидві входять у bash tests/run_all.sh --fast, тобто в TEST_CMD Stop gate-а, тож у свіжій хмарній сесії gate блокує кожен turn зі зміною коду. У 602 власник дозволив git fetch --unshallow --tags origin, після чого обидві зелені (9/0 і 41/0).

- Записано: 2026-10-08T18:50:18Z, агент

## Що зробити
Спершу проєкт: або setup script хмарного середовища робить git fetch --unshallow --tags (це налаштування середовища — дія власника), або ці дві suites, коли історії немає, кажуть про це однозначно і не рахуються червоними як помилка коду (не skip без пояснення). Питання до власника — який варіант.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
