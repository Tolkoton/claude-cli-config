# 024 — Другий прохід спрощувача по двигуну: звіт

## Що змінилось для власника
- **Нічого не видалено і не змінено.** У коді та інструкціях змін немає; додано лише цей звіт і сирі записи проходу в `.engine/simplifier/second-pass/`.
- **26 знахідок: 20 «confirm», 6 «flag_only», жодної «auto_remove».** Валідатор не відхилив жодної; три понизив із confirm до flag_only (код без тесту, що його захищає).
- **Постійний контекст: 191 рядок із 200. Цей прохід не звільняє жодного рядка.** У чотирьох файлах, які читає кожна розмова (`CLAUDE.md` 11, `AGENTS.md` 75, `.claude/engine-rules.md` 100, `.engine/rules.md` 5), спрощувач не знайшов нічого зайвого.
- **Текст, який модель читає на вимогу, може скоротитися приблизно на 230 рядків** (11 знахідок у навичках і агентах). Це моя оцінка за діапазонами рядків; точне число буде після застосування.
- **Код: близько 150–200 рядків**, майже все — дві знахідки: окремий розбирач стенограми в `overseer_stop.py` (68 рядків) і шлях «живої сцени» в аудиті (з тестами, що тримають лише його).
- **Частка повернень: 0 із 16 (0,0 %; коридор 5–20 %).** Лічильник радить «прибирати сміливіше». Усі 16 видалень зроблено вчора, тож висновок ранній.
- **Три знахідки — ті самі, що лишилися з першого проходу** (`annotate_echo.py`, `--reset-only`, шлях живої сцени — кандидати B8 у `tasks/CANDIDATES.md`). Спрощувач знайшов їх удруге незалежно.
- **Від вас:** рішення, що з цього застосувати. Застосування — окрема задача, як 011.

## Знахідки коротко
| № | Знахідка | Де | Категорія | Дія | Що можна прибрати |
|---|---|---|---|---|---|
| 1 | F-ce5aa3f9 | `.claude/hooks/complexity_budget.py:143-154` | duplication | confirm | Три hook-и розбирають `project.env` кожен по-своєму і розходяться на коментарях та цифрах у ключах; лишити один розбирач із `gate.py` |
| 2 | F-dc3ce935 | `.claude/hooks/overseer_stop.py:604-671` | duplication | flag_only | Другий розбирач стенограми (68 рядків) для старого протоколу; те саме вже робить `overseer_verdict.turn_events` |
| 3 | F-294cae10 | `.claude/hooks/gate.py:402-403` | shallow_module | confirm | Обгортка `contract_allowances`, значень якої ніхто не читає |
| 4 | F-231cea95 | `.claude/hooks/lesson_queue.py:546` | duplication | confirm | Друга копія регулярного виразу; є `pending_proposals()` |
| 5 | F-06b341e7 | `.claude/hooks/second_opinion.py:326` | defensive_for_impossible | confirm | Умова `asked and` усередині перебору `asked` — завжди істинна |
| 6 | F-2f351d2e | `.claude/hooks/simplifier.py:92-93` | duplication | confirm | Копія `utc_now`, яка вже є в імпортованому `simplify_signals` |
| 7 | F-fd58f428 | `.claude/hooks/lesson_queue.py:633-650` | duplication | flag_only | `project_root` визначено сім разів, `read_envelope` — чотири |
| 8 | F-ffae4a64 | `evals/annotate_echo.py` | dead_code | flag_only | Одноразовий скрипт, який своє відпрацював; ніхто не викликає (був у першому проході) |
| 9 | F-10ac19c7 | `evals/run_audit_scenarios.py:541-553` | dead_code | confirm | Шлях «живої сцени»: усі 12 сцен тепер записані; разом із ним ідуть живі випадки в чотирьох наборах тестів |
| 10 | F-8787b78e | `evals/run_hook_scenarios.py:298-300` | dead_code | flag_only | Прапорець `--reset-only`, якого ніхто не викликає (був у першому проході) |
| 11 | F-dc92ddb7 | `.claude/unattended/runstate.py:59-60` | duplication | confirm | Два подвійні `mkdir` поспіль (ще рядки 244-245) |
| 12 | F-3eaf4d11 | `.claude/unattended/board_review.py:47` | dead_code | confirm | Константа `EXIT_REFUSED`, якої ніхто не читає |
| 13 | F-9b4cac6b | `.claude/unattended/board_review.py:67-68` | dead_code | confirm | Переклад станів `stalled` і `deadline`, яких виконавець після задачі 021 не пише |
| 14 | F-44da981f | `.claude/unattended/board.py:100-104` | defensive_for_impossible | confirm | Запасний імпорт для Python до 3.11, якого решта двигуна не підтримує |
| 15 | F-f179afac | `.claude/unattended/watch.sh` | dead_code | flag_only | Скрипт без жодного виклику; типовий шлях до журналу вже не існує. Ризик повернення — середній |
| 16 | F-e3907eba | `.claude/skills/overseer/SKILL.md:24-65` | duplication | confirm | Розділ про заявку «unit complete» повторює `engine-rules.md` майже дослівно |
| 17 | F-8f6efdd4 | `.claude/agents/overseer.md:19-26` | duplication | confirm | Два абзаци мандата повторюють «Operating principles» того ж файла і статтю 2 конституції |
| 18 | F-4f664b0e | `.claude/agents/slice-planner-critic.md:309-316` | duplication | confirm | Списки «What you do NOT do» у трьох критиках повторюють їхній власний текст і `critic-core` |
| 19 | F-fa0bc666 | `.claude/skills/slice-builder/SKILL.md:256-267` | duplication | confirm | «Cadence discipline» — примітка про зміну проти старої версії навички |
| 20 | F-6e6fb0a4 | `.claude/skills/slice-builder/SKILL.md:228-237` | duplication | confirm | Список «What you DO NOT do» — третє формулювання тих самих заборон |
| 21 | F-01a38b13 | `.claude/skills/self-learning-orchestrator/SKILL.md:25-73` | duplication | confirm | Схема-діаграма з двома шляхами до файлів, яких немає; правильна таблиця йде одразу після неї |
| 22 | F-d85e9d0c | `.claude/skills/self-learning-orchestrator/triggers/decision-checkpoint.md:29-37` | dead_code | confirm | «Кодові фрази» для навичок, яких у репозиторії немає (ще п'ять файлів навички) |
| 23 | F-09fdfe03 | `.claude/skills/self-learning-orchestrator/triggers/pre-commit-checkpoint.md:17-29` | duplication | confirm | Зашита команда `uv run ruff … pytest`: те саме роблять ворота, а тут немає ні uv, ні `src/` |
| 24 | F-652d2800 | `.claude/skills/documentation/SKILL.md:124-141` | duplication | confirm | «Anti-patterns» — третє формулювання правил того ж файла |
| 25 | F-7b629745 | `.claude/skills/self-learning-orchestrator/SKILL.md:159-164` | dead_code | confirm | «Compatibility notes»: один пункт хибний, другий нічого не змінює |
| 26 | F-481a5c06 | `.claude/skills/self-learning-orchestrator/references/promotion-paths.md:152-165` | dead_code | flag_only | Журнал `.claude/promotion-candidates.md`, якого ніхто не читає |

## Постійний контекст і частка повернень
- **Зараз 191 із 200 рядків** (`wc -l CLAUDE.md AGENTS.md .claude/engine-rules.md .engine/rules.md`). Запас — 9 рядків.
- **Знахідок у цих чотирьох файлах — нуль.** Після задачі 011 у них лишилося те, що спрощувач вважає потрібним.
- **На вимогу — близько 230 рядків** у файлах, які модель читає лише коли бере навичку чи запускає агента. Найбільші: діаграма навички пам'яті (49), розділ навички наглядача (до 42), списки заборон у трьох критиках (25), «Anti-patterns» навички документації (18).
- **Частка повернень:** `0 of the last 16 removals came back (0.0 %; the corridor is 5-20 %)`. Замало часу, щоб щось повернулося.

## Що я перевірив сам
- Кожну відповідь агента прогнав через `simplifier.py validate` із запитом, з яким його запущено: 26 дійсних, 0 відхилених, 3 понижені.
- Очима звірив із диском: подвійні `mkdir` у `runstate.py`, константу `EXIT_REFUSED`, запасний імпорт у `board.py`, умову в `second_opinion.py:326`, обгортку в `gate.py:402-403`, регулярний вираз у `lesson_queue.py:546`, сім визначень `project_root`, відсутність викликів `watch.sh`, `annotate_echo.py` і `--reset-only`, два неіснуючі шляхи в діаграмі навички пам'яті, єдину згадку `promotion-candidates`. Усе збіглося.
- Решту знахідок по інструкціях (16–20, 22–25) я **не звіряв** рядок за рядком — вони на судженні спрощувача.

## Демонстрація на хвилину
```text
$ git status --short        # до запису звіту
?? .engine/simplifier/second-pass/

$ wc -l CLAUDE.md AGENTS.md .claude/engine-rules.md .engine/rules.md | tail -1
  191 total

$ python3 .claude/hooks/simplifier.py reversals
Reversal rate: 0 of the last 16 removals came back (0.0 %; the corridor is 5-20 %) — almost nothing comes back: the simplifier removes too little — be bolder

$ python3 .claude/hooks/simplifier.py validate .engine/simplifier/second-pass/answer-hooks.json --request .engine/simplifier/second-pass/request-hooks.txt
7 valid, 0 rejected, 0 lowered
```

## Витрати
- **Сам прохід — приблизно 12 доларів із дозволених 15.** Чотири агенти-спрощувачі на Fable, близько 645 тис. токенів. Це оцінка за лічильником розмови; окремого рахунку на агента немає.
- Уся розмова на момент написання звіту — близько 14 доларів; точну суму записує виконавець у `.claude/state/board/costs.json`.
- Аудит не запускався (`Аудит потрібен: ні`). Друга модель (Gemini) вимкнена, не запускалася.

## Commit-и
Один: звіт, сирі записи проходу і перенесення задачі в `done/`.

## Відкладене
- **Застосування знахідок** — окрема задача за вашим рішенням.
- **Знахідки не внесено в `.engine/simplifier/report.md` і в чергу уроків** (пояснення нижче). Команда `simplifier.py decide <id>` шукає знахідку за записами маршрутизації, тож перед застосуванням їх треба буде провести через `route`.
- **Черга уроків: 40 записів, прибирання пам'яті прострочене.** У цій задачі не розбирав.
- Лінзи «вимоги» та «архітектура» не запускав: задача називає лише код та інструкції.

## Рішення, які я ухвалив сам
- **Не запускав `simplifier.py route`.** Він дописав би 26 записів у чергу уроків (де вже 40 при порозі 30) і в `.engine/simplifier/report.md`. Задача каже «усе лише в звіт», тому знахідки — тут і в `.engine/simplifier/second-pass/` (запити, відповіді, результат валідатора).
- **Чотири запити замість трьох:** `.claude/unattended` окремо, бо задача називає його окремо, а в першому проході його не було.
- **Запит агентові передавав посиланням на файл запиту**, а не текстом у повідомленні. Цього разу працював справжній тип агента `simplifier` із трьома інструментами (у першому проході — загальний агент).
- **У відповіді по `.claude/unattended` прибрав префікс `/home/lao/engine/` зі шляхів.** Агент написав абсолютні шляхи; зміст не змінено.
- **Три повторні знахідки з першого проходу не викидав**, а позначив як повторні: незалежне підтвердження корисне для вашого рішення.
- **Не казав агентам, що вже знайдено раніше**, щоб не підказувати висновок.

## Усі знахідки з доказами
Текст знахідок — як його написав спрощувач (англійською), після валідатора.

### Код: `.claude/hooks` — 7

- `F-ce5aa3f9` **.claude/hooks/complexity_budget.py:143-154** — duplication, **confirm**: Three hooks each parse .claude/project.env with their own reader (gate.parse_env_text, complexity_budget.project_env, overseer_stop._load_project_env) and they disagree on a trailing `# comment` and on key names with digits; two of the three can go once the hooks that already import gate (overseer_stop, complexity_budget via record_in_gate_format) read the file through gate.parse_env_text.
  - read `.claude/hooks/gate.py:182`: parse_env_text: key `[A-Z_][A-Z0-9_]*`, matched quotes stripped, otherwise the value is cut at ` #` (line 192)
  - read `.claude/hooks/complexity_budget.py:151`: project_env: key `[A-Z_]+` (no digits), `.strip("\"'")` only — `KEY=value # note` keeps the note in the value
  - read `.claude/hooks/overseer_stop.py:150`: _load_project_env: partition on `=`, quotes stripped, no comment handling — the third reading of the same file
  - read `.claude/hooks/overseer_stop.py:742`: overseer_stop already imports gate (`import gate` in _active_contract and _note_refusal), so the dependency exists
  - read `.claude/hooks/complexity_budget.py:598`: complexity_budget already imports gate lazily in record_in_gate_format
  - read `tests/test_gate.py:54`: project.env values are written and read end to end through gate.py; tests/test_complexity_budget.py:81 and tests/test_source_dirs.py:14 do the same for the other two readers
  - judgement: the 'standard library only' note in each docstring is about third-party packages, not about importing a sibling hook; gate_allows.py already takes the git and reason helpers from gate for exactly the 'never disagree' reason
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: .claude/hooks/gate_allows.py:39 ('imports gate.py so the two can never disagree')
- `F-dc3ce935` **.claude/hooks/overseer_stop.py:604-671** — duplication, **flag_only**: _has_tool_signal (with its own _is_turn_boundary at 594-601) is a second reverse-scan parser of the transcript that the fresh protocol already has as overseer_verdict.turn_events plus the two `any(...)` lines of _claimed_unit; the former protocol keeps its behaviour if its one caller uses those instead, and the 68-line parser goes.
  - signal `S-d8399e91`: _has_tool_signal: complexity 26, the limit is 13
  - signal `S-203be875`: _has_tool_signal: nesting 5, the limit is 3
  - read `.claude/hooks/overseer_verdict.py:193`: turn_events: same turn boundary (_is_turn_boundary at 180-182, identical to overseer_stop.py:594-601), same tool_use blocks, same input dicts
  - read `.claude/hooks/overseer_stop.py:778`: _claimed_unit computes the same edit+check signal from turn_events in two lines (790-792)
  - grep `.claude/hooks/overseer_stop.py:963`: _has_tool_signal has one caller, the former-protocol branch of main; no test names it
  - read `tests/test_overseer_fresh.py:150`: the former protocol itself is kept on purpose and tested ('not wired yet: the claim gets the former self-audit request') — the fence holds for the branch, not for a second parser
  - read `.claude/hooks/overseer_stop.py:901`: main only falls back to the former protocol on ImportError of overseer_verdict; both files ship in the same directory, so the only reachable fallback case already has overseer_verdict importable
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: .claude/hooks/overseer_stop.py:47-55 (WHO AUDITS: the former protocol stays until the settings are applied)
- `F-294cae10` **.claude/hooks/gate.py:402-403** — shallow_module, **confirm**: contract_allowances only re-keys contract_grants into a dict whose values nobody reads (guard_python and guard_config test membership only), so bypass_guard can pass contract_grants(root) straight through and the wrapper goes.
  - grep `.claude/hooks/gate.py:502`: the single caller: `allowed = contract_allowances(root)` in bypass_guard
  - read `.claude/hooks/gate.py:433`: guard_python: `kind in allowed` — membership on the keys
  - read `.claude/hooks/gate.py:490`: guard_config: `rel.lower() in allowed or base.lower() in allowed` — membership on the keys
  - read `.claude/hooks/gate_allows.py:236`: gate_allows uses contract_grants(root) directly and reads the (name, reason) values it needs
  - read `tests/test_gate.py:395`: the sealed-contract grant path is exercised (the test seals a contract by its sha256)
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-231cea95` **.claude/hooks/lesson_queue.py:546** — duplication, **confirm**: digest counts pending proposals with a regex that is pending_proposals() minus the capture group; `len(pending_proposals(root))` gives the same number and the second copy of the pattern goes.
  - read `.claude/hooks/lesson_queue.py:290`: pending_proposals: re.findall(r"^## RP-(\w+) — \S+ — PROPOSED", ..., re.MULTILINE)
  - read `.claude/hooks/lesson_queue.py:546`: digest: len(re.findall(r"^## RP-\w+ — \S+ — PROPOSED", ..., re.MULTILINE)) on the same file
  - read `tests/test_lesson_queue.py:324`: session-start (digest) is run and its text asserted; it stays green with the count taken from pending_proposals
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-06b341e7` **.claude/hooks/second_opinion.py:326** — defensive_for_impossible, **confirm**: In `[r for r in asked if asked and ...]` the `asked and` test runs only while iterating `asked`, where it is always true; dropping it changes nothing.
  - read `.claude/hooks/second_opinion.py:326`: last_day = [r for r in asked if asked and str(r.get("utc", ""))[:13] == str(asked[-1].get("utc", ""))[:13]]
  - read `.claude/hooks/second_opinion.py:322`: the empty record returns early at 322-323 anyway; an empty `asked` iterates zero times
  - read `tests/test_second_opinion.py:326`: `cost` is run on a filled and on an empty record
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-2f351d2e` **.claude/hooks/simplifier.py:92-93** — duplication, **confirm**: simplifier.utc_now is byte-for-byte simplify_signals.utc_now, which simplifier already imports; the local copy (and second_opinion's use of it) can point at the one in simplify_signals.
  - read `.claude/hooks/simplify_signals.py:250`: def utc_now() -> str: return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
  - read `.claude/hooks/simplifier.py:59`: import simplify_signals
  - grep `.claude/hooks/second_opinion.py:292`: second_opinion calls simplifier.utc_now (also at 343); gate.py:165 and overseer_verdict.py:93 hold two more identical copies
  - read `tests/test_second_opinion.py:326`: the stamp's format is exercised through the record and the `cost --month` default
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-fd58f428` **.claude/hooks/lesson_queue.py:633-650** — duplication, **flag_only**: project_root is defined seven times across the hooks (and read_envelope four times) with the same CLAUDE_PROJECT_DIR → git → cwd logic; the modules that already import a sibling (lesson_queue is imported by gate, simplifier and overseer_stop; gate_allows already uses gate.project_root) could keep one copy.
  - grep `.claude/hooks/gate.py:172`: project_root also at complexity_budget.py:583, lesson_queue.py:633, overseer_verdict.py:97, overseer_stop.py:109 (_get_project_dir), overseer_phase.py:31, contract_fingerprint.py:34
  - grep `.claude/hooks/gate.py:984`: read_envelope also at lesson_queue.py:643, overseer_verdict.py:643, overseer_stop.py:575 (_read_envelope) — same isatty/json/dict check
  - read `.claude/hooks/gate_allows.py:327`: gate_allows calls gate.project_root() instead of carrying its own — the pattern already exists in the directory
  - judgement: the copies differ only in whether they .resolve() and in a 5 s timeout; a consolidation is a two-way door, but the choice of which variant wins is the owner's
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found

### Код: `engine.py` і `evals` — 3

- `F-ffae4a64` **evals/annotate_echo.py** — dead_code, **flag_only**: The one-time script that back-filled `echo` annotations into result files recorded before the runner checked the echo itself has done its job and nothing invokes it; the runner records the echo at run time and every baseline already carries the field, so the file and its private copies of scripted_lines/relayed/USAGE_LIMIT_RE can go while every current workflow stays the same (two prose mentions need a one-line edit).
  - signal `S-4f59e197`: pylint: 17 similar lines, evals/annotate_echo.py:51-68 and evals/run_audit_scenarios.py:447-464 (scripted_lines + relayed duplicated)
  - read `evals/annotate_echo.py:23-24`: its own docstring: 'The runner (run_audit_scenarios.py) performs the same check at run time since package 2b, so only files recorded before that need this.'
  - read `evals/run_audit_scenarios.py:445-470`: the runner's scripted_lines/relayed/echo_refused_message do the same check for every new run; recorded-turn runs get `echo: fixture` (run_audit_scenarios.py:540)
  - grep `evals/README.md:197`: the only references outside the file are prose: evals/README.md:197 and the report-line text in evals/compare_audits.py:202; grep over tests/ for 'annotate_echo' returns nothing — no test, hook, script or suite invokes it
  - read `tasks/CANDIDATES.md:95`: already on the owner's candidates list (F-0e61f4ce, B8) awaiting a decision; still on disk unchanged
  - judgement: the reason it was written — annotate files recorded before package 2b — is fulfilled and cannot recur: any file the current runner writes is annotated as it is recorded
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .engine/architecture/archive/engine-package-2b.json:94 ('annotate_echo.py for earlier files') — a one-time migration task, now done
  - валідатор: confirm -> flag_only: logic with no test protecting it is flagged, not acted on
- `F-10ac19c7` **evals/run_audit_scenarios.py:541-553** — dead_code, **confirm**: The live-scene branch of run_once (prompt A relayed by a session, the echo check, the refusal error) and its helpers — ECHO_MAX_TURNS (line 132), ECHO_REFUSED_PREFIX (156), scripted_lines/relayed/echo_refused_message (445-470), the two-sessions-per-run count (837) — serve no scene: every one of the 12 scenarios is a recorded turn, so the recorded-turn path alone measures the overseer; what keeps the branch alive is tests/_live_scenes.py and the live cases in four suites, which would go with it (and evals/README.md:155-156, 188-198 would need trimming). compare_audits.py's 'echo refused' bucket (192-193) stays: recorded baselines still carry those errors.
  - signal `S-ce9ae588`: run_once: complexity 35, the limit is 13 — the prompt-A branch is one of its two arms
  - read `evals/scenarios/audit/expected.json:7-267`: all 12 scenarios carry `turn_fixture`; none has a prompt A
  - read `evals/README.md:19`: 'Since board 018 every one is a recorded turn … the audit is done by the agent overseer in a fresh context, so a live relay of the turn adds nothing'
  - read `tests/test_audit_turn_fixture.py:93-94`: a test pins it: 'board 018: every scene is a recorded turn now, 01 included — no prompt A in any scenario file'
  - read `tests/_live_scenes.py:5-7`: 'Since board 018 every real scene is a recorded turn … but the runner still supports live scenes and these suites keep that path checked' — the only reason given to keep it is that tests test it
  - grep `tests/test_audit_runner_resume.py:40`: live_copy is imported by test_audit_runner_resume.py and test_audit_tiers.py; the claude shims in test_audit_first_verdict.py:67 and test_audit_turn_fixture.py:160 also answer a prompt A — four suites would need their live cases removed
  - read `tasks/CANDIDATES.md:48`: the owner's candidates table lists this path (B8, «шлях живої сцени») as removable because all scenes are recorded
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: tasks/CANDIDATES.md:48 (B8) — board 018 made every scene a recorded turn; no goal asks for a live relay
- `F-8787b78e` **evals/run_hook_scenarios.py:298-300** — dead_code, **flag_only**: The --reset-only option (parser lines 298-300, handler lines 330-337) exists 'between manual audit runs'; audit runs are performed by run_audit_scenarios.py, which builds a fresh sandbox per run, and nothing in the repository invokes or documents the flag, so it can go while every documented invocation of the hook runner keeps working (reset_sandbox itself stays: run_scenario, run_all and run_gate_evals.py use it).
  - signal `S-bd8fb9a9`: run_all: complexity 26, the limit is 13 — the reset-only early exit is one of its branches
  - read `evals/run_hook_scenarios.py:298-300`: help text: 'return the sandbox to its initial commit and exit (use between manual audit runs)'
  - read `evals/run_audit_scenarios.py:509-511`: run_once calls make_sandbox.sh for every run — no sandbox is reused between audit runs
  - grep `evals/run_hook_scenarios.py:330`: 'reset-only'/'reset_only' occur only inside run_hook_scenarios.py; zero hits in tests/, evals/README.md, make_sandbox.sh or any script
  - read `evals/run_gate_evals.py:41`: reset_sandbox is imported there, so the function is live; only the CLI flag has no caller
  - read `tasks/CANDIDATES.md:96`: already on the owner's candidates list (F-bc000a33, B8) awaiting a decision; still on disk unchanged
  - тести: none; ризик повернення: low; захищене: ні; простежується до: none found
  - валідатор: confirm -> flag_only: logic with no test protecting it is flagged, not acted on

### Код: `.claude/unattended` — 5

- `F-dc92ddb7` **.claude/unattended/runstate.py:59-60** — duplication, **confirm**: The second of two identical consecutive `path.parent.mkdir(parents=True, exist_ok=True)` lines in `_write_json` (and the same doubled `HEARTBEAT.parent.mkdir(...)` at lines 244-245 of `main`) can go; one call already creates the directory and nothing changes without the repeat.
  - read `.claude/unattended/runstate.py:59-60`: two byte-identical `path.parent.mkdir(parents=True, exist_ok=True)` statements in a row
  - read `.claude/unattended/runstate.py:244-245`: two byte-identical `HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)` statements in a row inside the `heartbeat` branch
  - signal `S-f1244afc`: main: nesting 11 — the lead that pointed at the CLI dispatch where the second pair sits
  - grep `tests/test_session_launch.py:89`: the test reads `.claude/state/unattended/state.json` written through `_write_json`; session-claude.sh:34 ticks `runstate.py heartbeat` in the same run
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-3eaf4d11` **.claude/unattended/board_review.py:47** — dead_code, **confirm**: The module constant `EXIT_REFUSED = 2` in board_review.py has no reader; the refusal exit is returned by `board.cmd_review` from board.py's own `EXIT_REFUSED`, so the documented exit code stays 2 without it.
  - grep `.claude/unattended/board_review.py:47`: 'EXIT_REFUSED' appears in board_review.py only at its definition
  - grep `.claude/unattended/board.py:713-715`: `cmd_review` catches `board_review.ReviewError` and returns board.py's `EXIT_REFUSED`; no `board_review.EXIT_REFUSED` reference exists anywhere in the repository
  - read `tests/test_board_review.py:325-345`: the review suite drives `board.py review` through its CLI, so the exit code path is exercised without this constant
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-9b4cac6b` **.claude/unattended/board_review.py:67-68** — dead_code, **confirm**: The `STATES` entries `stalled` and `deadline` translate runner states that board-runner.sh no longer writes (since board 021 it parks the task instead); `STATES.get(word, word)` keeps the review working for any status word, so the review's output for every live state is unchanged without them.
  - read `.claude/unattended/board_review.py:61-70`: STATES maps eight words; `runner_lines` (line 274) reads it with `STATES.get(word, word)`
  - grep `.claude/unattended/board-runner.sh:46`: the runner's own contract lists `state=<running|waiting-limit|idle|waiting-owner|stopped|error>`; every `status`/`finish` call in the script (lines 230, 467, 486, 508, 510, 515, 543, 546) uses one of those six, `deadline` at line 450 is a `park_task` reason, not a state, and `stalled` does not occur in the script
  - grep `tests/test_board_runner.py:1156-1157`: a test asserts the runner's head no longer lists stalled or deadline among its states
  - read `tests/test_board_review.py:339-343`: the review test feeds `state=stalled … reason=no-commit` and checks only that `no-commit` (the reason) is printed, which the fallback still does
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found (board 021 report: the runner parks instead of stopping with these states)
- `F-44da981f` **.claude/unattended/board.py:100-104** — defensive_for_impossible, **confirm**: The `try: from datetime import UTC … except ImportError` fallback for Python < 3.11 guards an interpreter the rest of the engine rules out: the two callers of board.py (gate.py, lesson_queue.py) and its two companions on the same runner (board_review.py, board_state.py) import `UTC` unconditionally, so `from datetime import UTC, datetime` alone keeps behaviour identical.
  - read `.claude/unattended/board.py:100-104`: try/except ImportError around `from datetime import UTC, datetime` with a `timezone.utc` fallback
  - grep `.claude/hooks/gate.py:67`: `from datetime import UTC, datetime` unconditional; gate.py:48 says 'Python 3.11+'; gate.py:737 is the caller of `board.gate_question`
  - grep `.claude/hooks/lesson_queue.py:61`: `from datetime import UTC, datetime` unconditional; lesson_queue.py:50 says 'Python 3.11+'; lesson_queue.py:383 is the caller of `board.rule_question`
  - read `.claude/unattended/board_state.py:36`: `from datetime import UTC, datetime` unconditional in the module board-runner.sh invokes on every attempt (board-runner.sh:120); board_review.py:40 likewise, imported by board.py's own `review` command
  - grep `.claude/hooks/overseer_stop.py:3`: `requires-python = ">=3.12"` on another hook of the same installed set
  - тести: characterization_exists; ризик повернення: low; захищене: ні; простежується до: none found
- `F-f179afac` **.claude/unattended/watch.sh** — dead_code, **flag_only**: watch.sh has no caller in any script, test, command or README table, and its default log path `.claude/unattended/logs/supervisor.log` no longer exists since package 3c moved the supervisor's logs to `.claude/state/unattended/logs/`; removing it changes nothing the supervisor, the runner or the tests do, and the lesson it embodies (D-18) stays recorded in unattended-decisions.md.
  - grep `.claude/unattended/unattended-decisions.md:176`: the only mention outside the file itself: D-18 names it as the fix for an ask-prompting inline watcher; no script, test, settings or README row invokes it
  - read `.claude/unattended/watch.sh:43-55`: defaults to `$HERE/logs/supervisor.log` and writes `.watch-run`/`.watch-seen` under `$HERE/logs/`, i.e. inside the tracked `.claude/unattended/` directory
  - read `.claude/unattended/supervisor.sh:40-42`: `STATE_DIR=.claude/state/unattended`, `SUP_LOG=$STATE_DIR/logs/supervisor.log` — the log watch.sh polls by default is not where the supervisor writes
  - read `.claude/unattended/README.md:147-159`: the Files table lists supervisor.sh, runstate.py, session-claude.sh, session-sim.sh, recheck_parked.py, rotate.sh, config.sh — not watch.sh
  - grep `engine.py:124`: the installer's migration list moves `.claude/unattended/logs/` to `.claude/state/unattended/logs/`, so a fresh install has no directory for watch.sh's default
  - тести: none; ризик повернення: medium; захищене: ні; простежується до: none found (D-18 records the lesson; no goal or contract asks for the watcher itself)
  - валідатор: confirm -> flag_only: logic with no test protecting it is flagged, not acted on

### Інструкції: CLAUDE.md, правила, навички, агенти, команди — 11

- `F-e3907eba` **.claude/skills/overseer/SKILL.md:24-65** — duplication, **confirm**: The section 'Claiming a unit complete (the Stop-hook trigger)' restates, almost sentence for sentence, .claude/engine-rules.md § 'Overseer protocol' (the sentinel, the structural-evidence rule, N from the contract else 1, never on WIP/RED/question turns, launch the agent with exactly that line, change nothing, end the turn, BLOCK → fix and claim again, three BLOCKs park, the plan phase guard), which is in every session's context; the skill can keep only what engine-rules does not say — the Agent-tool parameters in step 1 and the 'no valid verdict → repeated twice, then parked' bullet — together with the by-hand audit, the halt markers and the former protocol.
  - read `.claude/skills/overseer/SKILL.md:24-43`: sentinel alone on its own line, N from .engine/slices/<slug>.md or 1, only for a genuine unit, structural evidence (edit on a code path per project.env + verification command), phase guard on `plan`
  - read `.claude/skills/overseer/SKILL.md:45-65`: launch the agent with the prompt and nothing else, change nothing until it answers, end the turn; PASS/BLOCK (fix, claim again, another overseer, three in a row park)/ADR/ESCALATE routing pointer
  - read `.claude/engine-rules.md:41-50`: the same sentinel conditions, the same 'N from .engine/slices/<slug>.md, else 1 — never on a work-in-progress, RED-only or question-answering turn', the same launch/change-nothing/end-turn steps, 'After a BLOCK you fix and claim again — another overseer judges it; three BLOCKs on one unit park the task'
  - read `.claude/engine-rules.md:51-53`: the plan phase guard that SKILL.md:42-43 repeats
  - grep `.claude/hooks/overseer_stop.py:257`: the hook points at '§ The former protocol' of the SKILL, not at this section; tests/test_overseer_fresh.py:152-154 assert the hook's own text ('12-check', 'Launch the agent'), not the skill's
  - judgement: the first pass removed the SKILL's copy of 'Verdict routing' on the same ground (report.md F-f42f1239); this is the remaining copy of the neighbouring engine-rules section
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/engine-rules.md:41-53
- `F-8f6efdd4` **.claude/agents/overseer.md:19-26** — duplication, **confirm**: The two mandate paragraphs 'You are NOT a cheerleader …' and 'The builder's claims default to suspect … Demand specific evidence … Surface at least one alternative … Reasoned pushback is the expected output' say exactly what the file's own 'Operating principles' section says forty lines later (principles 1-4) and what Constitution Article 2 already imposes on every agent; the paragraphs can go and the agent's rules are unchanged.
  - read `.claude/agents/overseer.md:23-26`: 'The builder's claims default to suspect, not trusted. Demand specific evidence for every DONE claim. Surface at least one alternative when a single approach is proposed. Reasoned pushback is the expected output, not the exception.'
  - read `.claude/agents/overseer.md:65-75`: principle 1 'Verify before agreeing … before accepting any done/verified/tested claim', principle 2 'Technical correctness over social comfort', principle 3 'Surface at least one alternative when only one approach is proposed', principle 4 anti-Goodhart
  - read `.claude/constitution.md:27-30`: Article 2: 'Any done / verified / works / tested / safe claim defaults to suspect. Reasoned pushback is the expected output of a critic, not the exception. Being agreeable is not the job; being correct is.'
  - read `.claude/engine-rules.md:98-100`: every agent reads and obeys the constitution
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/constitution.md Article 2; .claude/agents/overseer.md:65-85
- `F-4f664b0e` **.claude/agents/slice-planner-critic.md:309-316** — duplication, **confirm**: The closing 'What you do NOT do' list of the slice critic restates lines earlier in the same file (write nothing: 40-41; blind to the planner's reasoning: 38; escalate product decisions: 260-291; tool or back-edge for external claims: 61-74; one BLOCKING objection: 295-297) and critic-core §1 (never chain blocks, never manufacture objections); the same pattern closes feature-critic.md:113-120 (each line = its lines 27-34, 93-97, 59, 101-105 or critic-core) and master-critic.md:142-150 (= its lines 35-40, 109-115, 84-89, 65, 49-52 or critic-core), so all three lists can go with every rule still stated once.
  - read `.claude/agents/slice-planner-critic.md:309-316`: do NOT write or edit any file / reveal or invent the planner's reasoning / make product-design decisions / adjudicate an external-system claim yourself / chain multiple BLOCKING objections / manufacture objections
  - read `.claude/agents/slice-planner-critic.md:38-41`: 'You do NOT see the planner's chain-of-thought … You write NOTHING except your critique output. You never edit the artifact or any code.'
  - read `.claude/agents/critic-core.md:43-54`: 'Never manufacture objections to look thorough; never pass to be agreeable' and 'One verdict per run … Never chain blocks' — inherited by all three critics (feature-critic.md:16-19, master-critic.md:18-23, slice-planner-critic.md:43-48)
  - read `.claude/agents/feature-critic.md:113-120`: 'You do NOT accept an integration claim on narrative — tracer bullet or back-edge' repeats lines 52-54 and 93-94; 'You do NOT debate what the playbook or a contract check already settles' repeats line 59; 'do NOT chain BLOCKs … or manufacture objections (Art. 3)' is critic-core
  - read `.claude/agents/master-critic.md:142-150`: 'do NOT bless a one-way door autonomously' repeats 109-115; 'do NOT accept a tech-stack premise on reputation — PoC' repeats 84-89; 'do NOT debate what the playbook already settles' repeats 65; 'do NOT run the full lens list mechanically — Self-Discover' repeats 49-52
  - judgement: the first pass removed the slice critic's duplicate VoI gate on the ground that it 'adds only the slice-level algorithm mix and the per-phase lenses' (F-a463a292); these lists are the same kind of residue
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/agents/critic-core.md:13-16 (each level critic states only what is specific to it)
- `F-fa0bc666` **.claude/skills/slice-builder/SKILL.md:256-267** — duplication, **confirm**: The 'Cadence discipline' section is a change note addressed to someone who knew the previous version ('What the old per-cycle STOPs were protecting…', 'This is the part of the old rule that was load-bearing, and it is unchanged') and its four points restate rules 1, 3, 6 and 7 and Step 4 of the same file, while its last paragraph restates engine-rules § 'The three reasons to stop'; it can go together with the two other change-note sentences at lines 186 ('that block stays exactly as it is') and 226 ('These triggers stay exactly as written … What changes is that they park'), and the builder's rules are unchanged.
  - read `.claude/skills/slice-builder/SKILL.md:256-267`: 'one gate … one park class'; 'What the old per-cycle STOPs were protecting was drift'; 1 write before you build (= rule 1 and rule 6, line 12 and 47), 2 record every transition (= rule 3, line 16 and Step 4 line 153), 3 do not chain past a bad state (= line 153), 4 park don't stop (= lines 56, 111, 168); 'The run stops for exactly three reasons … Nothing else.'
  - read `.claude/engine-rules.md:74-82`: 'The three reasons to stop, and there are no others' — the same three reasons and the same 'not reasons'
  - read `.claude/skills/slice-builder/SKILL.md:186`: 'Do NOT commit on the user's behalf — that block stays exactly as it is, and it is a review checkpoint, not a stopping condition'
  - read `.claude/skills/slice-builder/SKILL.md:226`: 'These triggers stay exactly as written. They are genuine … conditions — reason 1. What changes is that they park the item instead of stopping the world.'
  - judgement: 'old', 'stays exactly as it is', 'what changes' describe a diff against an earlier skill, not a rule for the agent reading it now; a fresh agent has no earlier version to compare
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/engine-rules.md:74-82
- `F-6e6fb0a4` **.claude/skills/slice-builder/SKILL.md:228-237** — duplication, **confirm**: The 'What you DO NOT do' list is the third statement of prohibitions already in the same file: mutation testing and wide-lens tests (rule 6 line 54, anti-patterns 193-194), ADRs (197), commit on the user's behalf (186), logging/observability (196, 216), implementing the next slice / other slices' tests (199), decomposition and architecture files (207-215, 230 = the master-architect/feature-architect routing); it can go and every prohibition stays stated.
  - read `.claude/skills/slice-builder/SKILL.md:228-237`: no .engine/architecture/ writes, no mutmut/cosmic-ray/code-reviewer/security-auditor, no ADRs, no decomposition, no commit, no folder restructures, no tests for OTHER slices, no logging/observability/metrics
  - read `.claude/skills/slice-builder/SKILL.md:188-199`: anti-patterns: mutation testing (mutmut, cosmic-ray), wide test design, new abstractions, retry/circuit breaker/structured logging, ADRs or architecture files, refactor of existing modules, implementing the NEXT slice
  - read `.claude/skills/slice-builder/SKILL.md:54`: 'What is NEVER added at slice level: mutmut / cosmic-ray mutation testing, exhaustive hypothesis property tests, wide-lens enumeration'
  - read `.claude/skills/slice-builder/SKILL.md:186`: 'Do NOT commit on the user's behalf'
  - тести: none; ризик повернення: low; захищене: ні; простежується до: none found
- `F-01a38b13` **.claude/skills/self-learning-orchestrator/SKILL.md:25-73** — duplication, **confirm**: The ASCII 'trigger state machine' routes the same moments to the same trigger files as the dispatch table that follows it (lines 79-87), but with two paths that do not exist (triggers/session-end.md, triggers/periodic.md — the files are session-end-dreaming.md and periodic-maintenance.md) and a step ('cue plan-mode skill') that belongs to the delegation map removed in the first pass; the diagram can go and the table, which is correct, remains the only routing.
  - read `.claude/skills/self-learning-orchestrator/SKILL.md:65`: '→ triggers/session-end.md' and line 71 '→ triggers/periodic.md'; line 36 '→ cue plan-mode skill'
  - grep `.claude/skills/self-learning-orchestrator/SKILL.md:65`: 'session-end.md' and 'periodic.md' as trigger paths occur only in this diagram; the files under triggers/ are decision-checkpoint, periodic-maintenance, pre-commit-checkpoint, session-end-dreaming, session-start, stuck-protocol
  - read `.claude/skills/self-learning-orchestrator/SKILL.md:75-89`: 'How to dispatch (the only rule)': the table maps the same seven moments to the real trigger files and says 'Read only the trigger file that applies'
  - judgement: first-pass finding F-b90eb594 (applied) removed the cue-phrase delegation the diagram's 'Task start' box still points to
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/skills/self-learning-orchestrator/SKILL.md:75-89
- `F-d85e9d0c` **.claude/skills/self-learning-orchestrator/triggers/decision-checkpoint.md:29-37** — dead_code, **confirm**: The 'Speak the cue phrase … This triggers decisions-log-adr-lite … If that skill is not installed, use the inline fallback' prelude names a delegate skill that exists nowhere in this repository, so the fallback is the only path; the same residue of the removed delegation map sits in pre-commit-checkpoint.md:19-23 and :54 (pre-commit-self-review-checklist, decisions-log-adr-lite), stuck-protocol.md:40-42 and :46-48 (a conversation_search tool nothing provides), :60-64 (execution-feedback-debugging), :75-79 and :89 (plan-mode / feature-architect cue phrases), session-start.md:82 (claude-code-project-scaffolding), periodic-maintenance.md:85 (progress-file-for-long-tasks) and promotion-paths.md:88 (skill-creator); dropping the cue-phrase sentences leaves each trigger's inline procedure, which is what runs today.
  - read `.claude/skills/self-learning-orchestrator/triggers/decision-checkpoint.md:29-37`: 'Speak the cue phrase aloud so the per-skill activates … This triggers decisions-log-adr-lite … If decisions-log-adr-lite is not available, append this directly to decisions.md'
  - grep `.claude/skills/self-learning-orchestrator/triggers/pre-commit-checkpoint.md:23`: the names pre-commit-self-review-checklist, execution-feedback-debugging, decisions-log-adr-lite, progress-file-for-long-tasks, claude-code-project-scaffolding, skill-creator appear only inside this skill's own trigger/reference files, .claude/README.md's diagram label and the first-pass records; no .claude/skills/<name>, user/skills/<name> or templates entry exists
  - grep `.claude/skills/self-learning-orchestrator/triggers/stuck-protocol.md:47`: 'conversation_search' occurs nowhere else in the repository; the next step (line 53) is the grep that actually runs
  - read `.engine/simplifier/report.md:66-67`: F-b90eb594 (applied): the delegation map was removed 'leaving the triggers' inline fallbacks as the only path, which is the path taken today'
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .engine/simplifier/report.md:66 (F-b90eb594)
- `F-09fdfe03` **.claude/skills/self-learning-orchestrator/triggers/pre-commit-checkpoint.md:17-29** — duplication, **confirm**: Step 1 'Self-review' tells the session to run a hard-coded `uv run ruff format . && uv run ruff check . && uv run mypy src && uv run pytest -q` and not to proceed on red, which is what the Stop gate already does with the project's own commands from .claude/project.env (and blocks the turn on failure); the step and the same hard-coded line in checklists/session-end.md:7 can go, and the gate's verification is unchanged.
  - read `.claude/skills/self-learning-orchestrator/triggers/pre-commit-checkpoint.md:25-29`: 'uv run ruff format . && uv run ruff check . && uv run mypy src && uv run pytest -q' — 'Fix any issues. Do not proceed to Step 2 with red gates.'
  - read `.claude/engine-rules.md:33-38`: 'verify-on-stop.sh runs the project's lint, type-check and tests when code changed, and blocks the turn on a failure'
  - read `.claude/hooks/verify-on-stop.sh:2-5`: 'find the changed files, read .claude/project.env, run lint, types and tests, block with the real error — lives in gate.py now'
  - grep `.claude/project.env:82`: TEST_CMD="bash tests/run_all.sh --fast" — this repository has no uv, ruff, mypy or src/, so the hard-coded line is wrong here and ignores the configured commands in any project
  - read `.claude/skills/self-learning-orchestrator/checklists/session-end.md:7`: the same toolchain line as a checklist item
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/engine-rules.md:33-38
- `F-652d2800` **.claude/skills/documentation/SKILL.md:124-141** — duplication, **confirm**: The 'Anti-patterns' list is the third statement of rules the same file already gives twice — as core principles (34-57) and as hard rules (98-122): unpruned generated entry files (= 54-55), every command pasted in (= 45-48, 103), overlapping agent/human docs (= 38-40, 106-107), emphasis everywhere (= 100-101), large `@`-imports (= 45-48), editing an accepted ADR (= 51-53, 116-118); the list can go and every rule stays stated, with the 200-line cap also enforced by scripts/doc_audit.py.
  - read `.claude/skills/documentation/SKILL.md:124-141`: nine anti-patterns: auto-generating unpruned, pasting every command, overlapping docs, many IMPORTANT/MUST, @-importing large files, editing an accepted ADR, hand-written API reference, one README doing four jobs, 'later'
  - read `.claude/skills/documentation/SKILL.md:34-57`: core principles: single source of truth ('never restates'), progressive disclosure ('a 400-line AGENTS.md'), append-only decisions, 'Generated output is a draft … Always prune'
  - read `.claude/skills/documentation/SKILL.md:98-122`: hard rules: ≤200 lines, never duplicate AGENTS.md and docs/, ADRs append-only, 'They are short on purpose — emphasis only works when it is rare'
  - read `.claude/skills/documentation/scripts/doc_audit.py:76-104`: check_entry_files enforces the 200-line cap and the @AGENTS.md import mechanically
  - read `.claude/skills/documentation/references/diataxis.md:68-69`: 'Generate it from docstrings or an OpenAPI spec wherever possible' and line 95 'One giant README doing all four jobs' — the two remaining anti-patterns already live in the reference the skill points to
  - тести: none; ризик повернення: low; захищене: ні; простежується до: .claude/skills/documentation/SKILL.md:98-101 ('short on purpose — emphasis only works when it is rare')
- `F-7b629745` **.claude/skills/self-learning-orchestrator/SKILL.md:159-164** — dead_code, **confirm**: The remaining 'Compatibility notes' state that master-architect and feature-architect 'may keep their own task-scoped reflections.md' — neither command mentions reflections.md — and that the hooks are 'orthogonal', which changes nothing an agent does; both bullets can go.
  - read `.claude/skills/self-learning-orchestrator/SKILL.md:159-164`: 'the engine's hooks provide PostToolUse / Stop hooks … this skill is orthogonal' and 'master-architect and feature-architect own architectural artifacts and may keep their own task-scoped reflections.md'
  - grep `.claude/skills/self-learning-orchestrator/SKILL.md:163`: 'reflections.md' occurs only inside this skill's own files, .claude/README.md and the simplifier records; .claude/commands/master-architect.md and feature-architect.md do not name it
  - read `.claude/commands/master-architect.md:182-191`: the artifacts master-architect owns: domain-map, architecture-map, INDEX, ADRs, premise nodes — no reflections file
  - judgement: the first pass removed the third bullet of this section (the '12 research-backed skills'); the two left describe no procedure and one is false
  - тести: none; ризик повернення: low; захищене: ні; простежується до: none found
- `F-481a5c06` **.claude/skills/self-learning-orchestrator/references/promotion-paths.md:152-165** — dead_code, **flag_only**: 'How to detect a promotion candidate' instructs appending hits to `.claude/promotion-candidates.md` and scanning it at periodic maintenance, but periodic-maintenance.md's pass 5 never reads that file and nothing else in the repository names it; the paragraph describes a ledger nothing consumes.
  - read `.claude/skills/self-learning-orchestrator/references/promotion-paths.md:160-165`: 'Lightweight tracking: append to .claude/promotion-candidates.md … At periodic-maintenance, scan this file for entries with ≥ 3 matching hits'
  - grep `.claude/skills/self-learning-orchestrator/references/promotion-paths.md:160`: 'promotion-candidates' appears only on this line in the whole repository
  - read `.claude/skills/self-learning-orchestrator/triggers/periodic-maintenance.md:77-88`: pass 5 looks 'across all memory layers' with four criteria; no step opens a candidates file
  - тести: none; ризик повернення: low; захищене: ні; простежується до: none found
