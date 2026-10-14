# 789 — У конвеєрі ніхто не позначає slice IN PROGRESS: overseer отримує slice unknown і contract null

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 088-active-slice-unknown-in-pipeline

## Що сталося
Задача 088 (fresh-install E2E). gate.active_slice читає slice із картки IN PROGRESS у .engine/PROGRESS.md, але ні /feature-architect, ні /plan-slice, ні навичка slice-builder не кажуть таку картку ставити (про неї говорять лише /bugfix і /hotfix). У пробі builder одразу писав «DONE», тому обидва запити audit-у (20261011T093903Z-8f0871, 20261011T095229Z-64b463) мали `"slice": "unknown"`, `"contract": null` і той самий unit_key `-|010-todo-cli|unit 1` для двох різних slice-ів; у ledger заголовки «— unknown — OVERSEER_PASS». Наслідки: перевірка «contract змінився між запитом і вердиктом» не працює (contract null); лічильник трьох BLOCK спільний для різних slice-ів задачі; complexity budget slice contract-а не міряється, бо активного slice-а немає. Overseer сам знайшов contract і написав про це як про відхилення.

- Записано: 2026-10-11T09:59:28Z, агент

## Що зробити
Спершу тест: запит audit-у в проєкті зі sealed contract-ом .engine/slices/<slug>.md і задачею в режимі «конвеєр» має назвати slice і sha256 contract-а. Далі або навичка slice-builder ставить картку IN PROGRESS на початку slice-а (і тест тексту навички це тримає), або активний slice визначає скрипт — наприклад, з останнього рядка «the slice opens» у .engine/testing/ledger.md, який testing.py уже пише. Раджу друге: не залежить від того, чи агент не забув.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
