# 100 — Режими Г: агент-читач для задач без робочого коду і список в огляді власника

Залежить від: 099
Потрібна присутність власника: ні
Аудит потрібен: ні
Платні прогони: ні

## Що зробити
Збудувати точно за схваленим проєктом `tasks/done/080-modes-design/report.md` і відповідями власника в `tasks/done/080-modes-design/task.md` (розділ 6; відповідь власника 4):
- задачу, що не змінила робочого коду, перед закриттям читає `reader` (збудований у 099): кожне посилання каже те, що йому приписано; кожен пункт «Що зробити» має відповідь; кожне питання до власника — розвилка з варіантами й порадою; технічні терміни англійською. BLOCK — автор виправляє, читає інший читач; три BLOCK поспіль — задачу відкладає runner, як з overseer-ом;
- `mode.py check-close`: задача без робочого коду без PASS читача не закривається (хід назад, потім `blocked/`);
- `board.py review`: розділ «Змінені документи й проєкти — переглянь» — усі закриті задачі без робочого коду, без винятків; для кожної — назва, змінені документи, вердикт читача. Запис висить, доки власник не переглянув; закриття задачі на власника не чекає;
- «переглянув» — номер задачі у `tasks/.reviewed`, через гілку або inbox; `/owner-review` готує цей файл разом із відповідями власника; агент його не пише. Знайдена власником проблема — нова задача, яку готує `/owner-review`;
- `tasks/README.md`, `.claude/unattended/README.md`, `docs/OWNER-GUIDE.md`.
Поправка до G2 — окрема задача 096; ця від неї не залежить, але саме вона робить новий G2 правдою.

## Готово, коли
- Негативні випадки показано першими: задача без коду без PASS читача — хід назад, потім `blocked/`; запис в огляді не зникає, доки номера немає в `tasks/.reviewed`; номер, дописаний агентом у сесії, відхилено.
- Після номера в `tasks/.reviewed` від власника запис зникає з огляду.
- Повний набір тестів зелений.

## Чому зупинилась
- 2026-10-11T16:23:29Z — overseer тричі поспіль відхилив один юніт (-|100-modes-reader-for-documents|unit 1); runner переніс задачу в `blocked/` і взяв наступну. Незакомічену роботу агента runner зберіг у гілці `wip/100-modes-reader-for-documents/20261011T162327Z` в origin (повернути в робоче дерево: `git fetch origin wip/100-modes-reader-for-documents/20261011T162327Z && git cherry-pick -n FETCH_HEAD`) і у сховку git на сервері runner-а (`git stash apply a907a7cad04c028e2c9c0bd2784f4cdb237030e7`).
  - BLOCK 1 (2026-10-11T15:18:46Z, запит `20261011T150334Z-ff0cbc`, перевірка #1): false-DONE — the claim «the runner removes a number that did not arrive from the owner» and the test line «origin never has the number» do not hold on the runner's own pushes that are not the end-of-task push: with `--stop-after-attempt` a number the agent wrote into tasks/.reviewed and committed is pushed to origin (reproduced: origin's tasks/.reviewed is '001\n' after the stop) and stays there until the runner is started again, so the review, which reads origin, drops the entry exactly while the runner is stopped. Run `reviewed_guard` before EVERY push of the work branch (simplest: inside `p
  - BLOCK 2 (2026-10-11T15:48:00Z, запит `20261011T154542Z-af0fbd`, перевірка #1): false-DONE — the claim «the runner now removes a forged number from tasks/.reviewed before every push of the work branch» (and the task's «номер, дописаний агентом у сесії, відхилено») does not hold on the push the guard's own failure triggers: when `board.py reviewed-reject` exits non-zero, `reviewed_guard` calls `finish error`, which calls `push_branch quiet`, and the re-entry flag REVIEWED_GUARDING makes that push skip the guard — so the checkout is pushed with the number still in it. An agent reaches that path with one invalid byte: tasks/.reviewed = b'777\n\xff\n' makes `_text()` raise Un
  - BLOCK 3 (2026-10-11T16:22:43Z, запит `20261011T162015Z-a15936`, перевірка #1): false-DONE — the claim «the runner now sends the work branch only after checking the commit it is about to send» does not hold: `reviewed-clean` (and the guard) judge HEAD, while `push_branch` sends `$BRANCH`, and `stop_after_attempt` pushes with no check that the checkout is still on the branch. A fake agent that commits its number into tasks/.reviewed on unattended/work and then leaves the branch (`git switch --detach HEAD~1`, an auto-allowed command) gets it to origin on a stop after the attempt: reproduced, origin's unattended/work:tasks/.reviewed is '777\n', events show «pushed» with no `

## Питання до власника
1. Три overseer-и поспіль відхилили юніт цієї задачі; їхні вердикти — у розділі «Чому зупинилась». Що робити далі? Будь-яка відповідь поверне задачу в чергу, і юніт отримає три нові спроби; вказівку агентові напишіть тут же.
   Відповідь: Звужуємо обіцянку, як і в задачі 724. Перевірка `tasks/.reviewed` захищає від випадкової або наївної позначки: агент у сесії дописав номер у `tasks/.reviewed` і закомітив його — runner прибирає такий номер перед кожним push-ем робочої гілки, і запис в огляді власника не зникає. Від навмисного обходу вона не захищає і не може: сесія працює під тим самим користувачем Linux, що й runner. Межа така: обхід, для якого агент мусить навмисно діяти проти перевірки (перемкнути гілку перед push-ем, записати зіпсовані байти, щоб перевірка впала, і подібне), — задокументована межа, не вада; номер, дописаний звичайним способом, має прибиратися перед кожним push-ем, і те, що ти вже виправив після BLOCK 1, лишається. BLOCK 2 і BLOCK 3 з розділу «Чому зупинилась» — навмисний обхід. Запиши межу в `docs/engine-limits.md` розділом про межу «той самий користувач Linux»: якщо його ще немає — створи (задача 724 допише туди свій випадок), якщо вже є — допиши свій. Прибери з документів твердження, сильніші за це. Візьми роботу з гілки `wip/100-modes-reader-for-documents/20261011T162327Z` (команда — у розділі «Чому зупинилась»), доведи її до кінця і подай на audit. Відкритий пункт «сесії агента під окремим користувачем Linux»: якщо його ще немає — поклади, якщо вже є — допиши в нього випадок `tasks/.reviewed`.
