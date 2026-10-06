# 017 — Посилити block-dangerous для push: звіт

## Що змінилось для власника
Hook тепер сам зупиняє небезпечні форми push, хоч що відповіли б на запит дозволу: force push у будь-якому написанні, видалення віддаленої гілки і push у захищену гілку. Звичайний push робочої гілки, як і раніше, йде через правило `ask`. Агентові push у `main` і `stable` заборонено; release робить оператор поза Claude Code.

Перелік захищених гілок налаштовується: `PUSH_PROTECTED_BRANCHES` у `.claude/project.env` (типово `main stable`). Проєкт із `master` чи `production` називає їх там. Ключ охороняє gate: змінити його робота, яку оцінюють, не може.

Зроблено в сесії з власником 2026-10-06; зміну і три рішення до неї власник схвалив до застосування. `.claude/settings.json` не змінювався.

## Демонстрація на хвилину
```bash
python3 tests/test_push_hardening.py | tail -1     # PASS 84   FAIL 0
python3 tests/test_commit_policy.py | tail -1      # PASS 28/28 commit-policy cases
python3 evals/run_hook_scenarios.py --engine-ref HEAD \
  --compare evals/baseline/linux-ubuntu-22.04/results-task-017.json | tail -1   # PASS 167/167
```

## Що зроблено
- **`.claude/hooks/block-dangerous.sh`** — нова секція на чистому bash. Знаходить кожен `git … push` у команді (за `git -C <dir>`, `git -c k=v`, після роздільника, з кількома пробілами чи tab) і читає аргументи по словах до наступного роздільника:
  - **force push:** `--force`, `--force-with-lease[=…]`, `--force-if-includes`, `--mirror`, злиті короткі прапорці з `f` (`-f`, `-uf`), refspec із `+`;
  - **видалення віддаленої гілки:** `--delete`, прапорці з `d`, refspec `:гілка`;
  - **push у захищену гілку:** refspec із таким призначенням (`main`, `HEAD:main`, `x:refs/heads/main`), `--all` і `--branches`, push без refspec (або з `HEAD`), коли checked-out гілка захищена.
- **`PUSH_PROTECTED_BRANCHES`** — додано в обидва `project.env` (цього репозиторію і шаблона) з порожнім значенням, тобто типовим. Hook читає ключ через `sed`, не виконуючи файл.
- **`.claude/hooks/gate.py`** — ключ додано до `SCOPE_KEYS`: зміну пропускає лише sealed slice contract, який називає ключ; причина в самому `project.env` чи дозвіл на весь файл не проходять. Порядок, коми і записане типове значення зміною не вважаються.
- **Документи:** `docs/engine-limits.md` (розділ «A dangerous push» з обмеженнями і таблиця commit policy), `.claude/references/hooks.md`, `gate.md`, `permission-philosophy.md`, `docs/TEMPLATE-SETUP.md`.

## Рішення власника в цій сесії
1. **`bd-push-on-main` і рядок у `tests/test_commit_policy.py` перевернуто на block.** Це скасовує частину рішення від 2026-10-01 (push у `main` тоді лишили правилу `ask`). Тому умова задачі «golden set тотожний, крім нових сценаріїв» виконана з одним винятком — цим сценарієм.
2. **Два доповнення понад текст задачі:** push без refspec на захищеній гілці та `--all` / `--branches`.
3. **`main` і `stable` — типові, перелік налаштовується** ключем під охороною gate.

## Перевірено
- `tests/test_push_hardening.py` — 84 перевірки:
  - 39 небезпечних форм заблоковано, причина названа;
  - 29 законних команд пройшли: push робочої гілки, `-u origin HEAD`, `--tags`, tag, `origin release`, `feat/main`, `main:feat/copy`, `-o <option>`, `git stash push`, `git checkout -f`, `git branch -d`, `git fetch origin main`, `docker push …:main`;
  - 11 — ключ у `project.env`: власний перелік замінює типовий, коми й одинарні лапки, порожній і відсутній ключ дають `main stable`, значення з `$(…)` не виконується;
  - 5 — охорона gate: зміна з власною причиною — block, дозвіл на весь файл — block, sealed contract із назвою ключа — проходить, запис типового значення — не зміна, вилучення рядка — block.
- До зміни hook пропускав 30 із 37 небезпечних форм першої проби.
- Golden set: 167/167; 142 сценарії поводяться, як у `results-task-714.json`, 24 нові, 1 перевернутий. Новий baseline `results-task-017.json`, на нього переведено `docs/working-on-the-engine.md` і `evals/README.md`.
- Повний `bash tests/run_all.sh` — 72 suites зелені.
- `ruff`, `mypy` і `shellcheck` не запускались.

## Чого це не ловить (прийнято власником, записано в `docs/engine-limits.md`)
- Push зі скрипта, який команда лише запускає (`engine.py release`, runner).
- Remote, refspec або прапорець у змінній чи з підстановки.
- Push у захищену гілку через налаштування, коли локальна гілка називається інакше: upstream на `origin/main`, `push.default`, `remote.<name>.push`.
- Alias (`git config alias.p push`).
- **Відмова без шкоди:** лапки не розбираються, тож команда, чиє повідомлення цитує такий push, теж дістане відмову. Так сталося й у цій сесії: скрипт із таким рядком у heredoc довелося записати файлом через Write.

## Commit-и
`e737235` (зміна, тести, golden-сценарії, документи) і commit закриття задачі після нього, гілка `unattended/work`. Push не робився.

## Рішення, які я ухвалив сам
- **Три старі буквальні шаблони в `DANGEROUS_PATTERNS` лишив.** Нова секція їх перекриває, але на них посилаються `tests/lint_patch.py` та інші тести; для `git push -f <remote>` першим відповідає старий шаблон, і повідомлення тоді старе («Pattern matched»).
- **Ключ у `SCOPE_KEYS`, а не в `GATE_KEYS`.** Суворіший із двох рівнів охорони: послабити захист гілки з причиною, яку пише сама робота, було б надто легко.
- **`test_push_hardening.py` поза fast-набором** (близько 27 с): Stop gate його не запускає, повний набір — так.
- **Задача пройшла повз `doing/`** — виняток власника для цієї сесії (задача 720).
