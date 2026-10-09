# 097 — Режими А: читач режиму, рядок «Режим:» і підняття

Залежить від: 080
Потрібна присутність власника: ні
Аудит потрібен: ні
Платні прогони: ні

## Що зробити
Збудувати точно за схваленим проєктом `tasks/done/080-modes-design/report.md` і відповідями власника в `tasks/done/080-modes-design/task.md` (розділи 3 і 5):
- `.claude/hooks/mode.py show` — друкує режим задачі, супровід, «без нагляду», тип роботи і джерело кожного; нічого не пише;
- рядок `Режим: ескіз|соло|конвеєр` під назвою задачі: `board.py` його розбирає; задача без рядка — Соло; невідоме значення task board не бере з inbox і каже чому; `board.py review` показує режим кожної задачі;
- `mode.py raise <режим> --why "…"` — дописує в задачу в `doing/` розділ `## Режим піднято`; униз відмовляє; чинний режим — вищий із рядка власника й останнього підняття; файла стану режиму немає, тож наступна задача починає зі свого рядка або із Соло;
- недійсні поєднання відхиляє скрипт: `/hotfix` і `/bugfix` в Ескізі, `/hotfix` у Конвеєрі;
- підняття скасовує лише власник, видаливши розділ `## Режим піднято` з файла задачі;
- п'ять місць, що самі обчислюють «без нагляду» (`.claude/unattended/board.py` і `env-probe.sh`, `.claude/hooks/goals.py`, `hotfix.py`, `park-ask-gated.py`), питають читача;
- runner дописує рядок режиму в перше повідомлення сесії; `overseer_verdict.py` (складає пакет запиту на вимогу `overseer_stop.py`) кладе його в пакет, рядок про це — в `overseer.md`;
- `tasks/README.md`, `tasks/TEMPLATE.md`, `docs/OWNER-GUIDE.md` (новий розділ «Як обрати режим»): режим на задачу; вгору агент сам, униз — власник; підняття діє до кінця задачі; правило 2 для агента каже, що розділ `## Режим піднято` дописує лише `mode.py raise`;
- `tests/test_model_roles.py`: `mode.py` і рядок `Режим:` моделей не згадують.
`settings.json` і конституція не змінюються. Карантин Ескізу і перевірка при закритті — задачі 098 і 099, не тут.

## Готово, коли
- Негативні випадки показано першими: `Режим: абищо` не береться з inbox; `mode.py raise соло` на задачі в Конвеєрі відмовляє; `/hotfix` з `Режим: ескіз` відмовляє.
- Задачу підняли в Конвеєр і закрили; наступна без рядка — `mode.py show` каже «соло».
- Наявні задачі без рядка працюють, як працювали; повний набір тестів зелений.

## Чому зупинилась
- 2026-10-08T22:03:41Z — overseer тричі поспіль відхилив один юніт (-|097-modes-reader-and-line|unit 1); runner переніс задачу в `blocked/` і взяв наступну.
  - BLOCK 1 (2026-10-08T21:06:00Z, запит `20261008T204533Z-278819`, перевірка #1): false-DONE: the task's exit line «повний набір тестів зелений» (tasks/doing/097-modes-reader-and-line.md:24) is false on this tree. I ran `bash tests/run_all.sh` and 2 of 86 suites are red: test_release.py (140 passed, 6 failed) and test_settings_proposal_install.py (IndexError). Both are green at HEAD 000f998. The cause is .claude/unattended/board.py:189, which now imports hooks/mode.py at module top. The fixtures of those two suites copy board.py without mode.py, so board.py dies with ModuleNotFoundError: No module named 'mode'. This is the same break the builder already fixed in evals/run_a
  - BLOCK 2 (2026-10-08T21:31:20Z, запит `20261008T211443Z-db1e9d`, перевірка #4): masked test gap: no test checks that a raise changes what /hotfix and /bugfix are refused. If mode.py:218 reads `parse(text).owner` (the owner's line only) instead of `parse(text).current`, test_mode still gives 54/0 and no other suite tests a raise together with a refusal. That wrong version lets `/hotfix` start on a task raised соло→конвеєр and refuses `/bugfix` on an ескіз task raised to соло. Add checks that go through hotfix.py start and bugfix.py prove on a raised task: (a) no line, `mode.py raise конвеєр` → /hotfix refused 'in the mode «конвеєр»' and no card written; (b) `Режим: ескіз`
  - BLOCK 3 (2026-10-08T21:54:31Z, запит `20261008T213659Z-039e64`, перевірка #4): masked test gap: nothing tests that the raise refuses to go down from a mode that was itself raised. If mode.py:235 compares the target with `mode.owner` instead of `mode.current`, test_mode still passes 64/0, and the agent can take a task with «Режим: ескіз» that it raised to конвеєр back down to соло by running `mode.py raise соло`. The turn lists this exact mutant («a raise compared with the owner's line instead of the mode in force») as CAUGHT, and on this tree that is not true. Add a check: `Режим: ескіз`, `mode.py raise конвеєр`, then `mode.py raise соло` gives exit 2 with «a raise goes

## Питання до власника
1. Три overseer-и поспіль відхилили юніт цієї задачі; їхні вердикти — у розділі «Чому зупинилась». Що робити далі? Будь-яка відповідь поверне задачу в чергу, і юніт отримає три нові спроби; вказівку агентові напишіть тут же.
   Відповідь:
