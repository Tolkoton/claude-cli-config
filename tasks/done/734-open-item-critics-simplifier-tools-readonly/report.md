# 734 — Інструменти critics і simplifier: проєкт рішення

Це проєкт рішення, а не збудована річ: жодного файла двигуна не змінено, платних сесій не було.
Будування — окрема задача `tasks/blocked/1723-open-item-734-critics-readonly-build.md`,
вона чекає на вашу відповідь на два питання з розділу «Питання до власника».

## Що змінилось для власника
- **У коді нічого.** Є таблиця по всіх одинадцяти агентах із `.claude/agents/` і пропозиція межі.
- **Попередній огляд від 2026-10-06 підтверджено і уточнено.** П'ять агентів — `critic-core`,
  `master-critic`, `feature-critic`, `slice-planner-critic`, `mvp-critic` — не мають рядка `tools`
  у frontmatter і тому дістають усі інструменти сесії. Це не лише Bash, Edit і Write, а й `Agent`
  (critic може запустити власного subagent-а) і всі MCP tools, підключені до сесії (у цій сесії
  серед них є такі, що створюють файли в Google Drive). Perimeter hooks їх не стримують: read-only
  межа стосується лише імені `overseer`.
- **За інструкціями жоден critic нічого не пише.** PoC будує `/master-architect`, tracer bullet —
  `/feature-architect`; critic лише вимагає їх маркером. Bash за роллю потрібен одному —
  `slice-planner-critic`.
- **Побічна знахідка поза межами задачі:** `slice-tester` через edit tools пише лише тестові
  файли, але його Bash не обмежує ніщо (питання 2).

## Проєкт рішення

### 1. Що перевірено і як
- Frontmatter кожного файла `.claude/agents/*.md` прочитано; перелік агентів, який Claude Code
  показав цій сесії, каже те саме: для п'яти critics — «Tools: All tools», для `overseer` —
  «Read, Grep, Glob, Bash».
- Документація Claude Code (`https://code.claude.com/docs/en/sub-agents`, прочитано 2026-10-12):
  `tools` — «Inherits every tool available to subagents if omitted», разом із MCP tools; subagent
  за замовчуванням може запускати власних subagent-ів; є поле `disallowedTools`; hook дістає ім'я
  агента з frontmatter як `agent_type`.
- Hooks запущено руками з envelope, де `agent_type` — `overseer`, `slice-planner-critic` і
  `master-critic`, команда `echo x > docs/note.md` і Write у `docs/note.md`:

  | `agent_type` | Bash (`block-dangerous.sh`) | Write (`protect-paths.sh`) |
  |---|---|---|
  | `overseer` | exit 2, «the overseer agent is read-only» | deny |
  | `slice-planner-critic` | exit 0 — дозволено | дозволено |
  | `master-critic` | exit 0 — дозволено | дозволено |

  Причина — порівняння з одним іменем: `.claude/hooks/block-dangerous.sh:353` і
  `.claude/hooks/protect-paths.sh:52`.
- Чи вистачить `slice-planner-critic` тієї самої межі, що й `overseer`: команди, які називає його
  інструкція, подано на `shell_readonly.py`. Дозволено (exit 0): запис чернетки в `/tmp` через
  heredoc, `python3 .claude/hooks/testing.py invariants <файл у /tmp>`, `python3 -m pytest --help`,
  `rg -n foo .`. Відмова (exit 2): `echo x > .engine/slices/a.md`, `git stash`.

### 2. Таблиця: агент, інструменти зараз, що потрібно, пропозиція

| Агент | Інструменти зараз | Що потрібно за інструкцією | Пропозиція |
|---|---|---|---|
| `overseer` | Read, Grep, Glob, Bash; read-only межа в perimeter (задача 055) | запускати тести, читати git, відтворювати RED у копії під `/tmp` | без змін |
| `reader` | Read, Grep, Glob | читати запис і джерела | без змін |
| `business-analyst` | Read, Grep, Glob (`tests/test_goals.py:295` це перевіряє) | читати документ цілей і запит | без змін |
| `simplifier` | Read, Grep, Glob (`tests/test_simplifier.py:331`) | читати код | без змін |
| `test-manager` | Read, Grep, Glob (`tests/test_testing.py:737`); `testing.py guard` ще й відмовляє в edit tools і `Agent` (`.claude/hooks/testing.py:948`) | читати контракт і факти від скрипта | без змін |
| `slice-tester` | Read, Grep, Glob, Write, Edit, Bash; edit tools — лише тестові файли (`.claude/hooks/testing.py:950`–`957`) | писати й запускати тести — роль не «лише читає» | поза цією задачею; Bash без межі — питання 2 |
| `critic-core` | рядка `tools` немає → усі | нічого: «Not invoked directly» у власному описі, це спільний текст для critics | `tools: Read, Grep, Glob` |
| `master-critic` | усі | читати maps, ADRs і codebase (`.claude/agents/master-critic.md:39`–`40`) та playbook (`:43`–`45`). PoC лише вимагає маркером `MASTER_CRITIC_POC_REQUIRED`; будує його architect (`.claude/commands/master-architect.md:50`) | `tools: Read, Grep, Glob` |
| `feature-critic` | усі | «use Read/Grep/Glob» (`.claude/agents/feature-critic.md:33`). Tracer bullet лише вимагає маркером `FEATURE_CRITIC_PREMISE_PROBE_REQUIRED`; будує його `/feature-architect` | `tools: Read, Grep, Glob` |
| `mvp-critic` | усі | жодного інструмента не названо: дизайн і документ цілей йому передають | `tools: Read, Grep, Glob` — читати дозволено, щоб звірити дизайн із `.engine/goals.md` |
| `slice-planner-critic` | усі | «Read/Grep/Glob/Bash for inspection only… You write NOTHING» (`.claude/agents/slice-planner-critic.md:39`–`40`); `rg`, `--help`, micro-probe, документація залежності (`:62`); `testing.py invariants` на чернетці, збереженій у тимчасовий файл (`:134`–`135`) | `tools: Read, Grep, Glob, Bash, WebFetch, WebSearch` і та сама read-only межа в perimeter, що й для `overseer`: запис лише в `/tmp`, `/var/tmp`, `$TMPDIR` |

Жодному агентові, що лише читає й судить, за роллю не треба писати в дерево проєкту. Файла дебатів
critics не ведуть: дебати — частина відповіді (`.claude/agents/critic-core.md`, розділ «4. Output»).
Єдине місце запису — тимчасова тека для чернетки й micro-probe в `slice-planner-critic`, і її
`shell_readonly.py` вже дозволяє.

### 3. Межа: два шари (порада на питання 1)
1. **Frontmatter — перший шар.** Рядок `tools` за таблицею для п'яти critics. Лише він прибирає
   `Agent` і MCP tools: hooks двигуна стоять перед Bash, edit tools, WebFetch/WebSearch і `Agent`,
   а виклик MCP tool не бачить жоден.
2. **Perimeter — другий шар.** Замість одного імені — перелік `READONLY_AGENTS` у
   `.claude/hooks/protected-path-list.sh` (його вже читають обидва hooks): `overseer`, п'ять
   critics, `simplifier`, `business-analyst`, `reader`, `test-manager`. Для агента з переліку
   `protect-paths.sh` відмовляє в будь-якому edit tool, `block-dangerous.sh` віддає команду
   `shell_readonly.py` — той самий скрипт, без нових правил. Навіщо другий шар, коли є перший:
   frontmatter — один рядок у файлі, який проєкт може змінити чи загубити при оновленні; тоді межа
   зникає мовчки. Для агентів без Bash і edit tools другий шар нічого не коштує: hook просто не
   спрацьовує.
3. **Тексти відмов** називають агента: зараз «the overseer agent is read-only» вписано в
   `.claude/hooks/shell_readonly.py:261` і в обидва hooks; ім'я стає параметром. Порада «скопіюй
   дерево в `/tmp`, щоб відтворити RED» лишається для `overseer`; critic-ові — «чернетку й probe
   тримай у `/tmp`».
4. **`.claude/settings.json` не змінюється:** matchers `Bash` і `Edit|Write|MultiEdit|NotebookEdit`
   уже стоять.

### 4. Тести й golden set (для задачі будування)
- `tests/test_overseer_readonly.py`: ті самі блоки для кожного імені з переліку — запис у дерево
  відхилено, запис у `/tmp` і читання дозволено; edit tool відхилено. Негативні випадки: builder
  без `agent_type`, `slice-builder`, `slice-tester`, ім'я, що лише схоже (`master-critic-like`).
  Рядок 114 цього файла сьогодні бере `simplifier` як «інший агент, якому можна писати» — він
  перевернеться, і це має бути видно в diff.
- Новий тест frontmatter: кожен агент із `READONLY_AGENTS` має рядок `tools`, у ньому немає Write,
  Edit, MultiEdit, NotebookEdit, `Agent`; Bash — лише в `overseer` і `slice-planner-critic`;
  файл агента без рядка `tools`, підкладений у тимчасову копію, тест відхиляє.
- Golden set: у `evals/scenarios/hooks/10-block-dangerous.json` і `20-protect-paths.json` — по
  одному deny і одному allow на кожного нового агента з Bash чи без; `pp-another-agent-edit-allowed`
  (`slice-builder`) лишається allow. Новий baseline.
- Документи: `docs/engine-limits.md:186`–`187` («Only the agent `overseer` is covered…») і
  `.claude/references/hooks.md`.
- Живий прогін critic-а з вужчими tools (чи не дістає він зайвих відмов) — платний; у задачі
  будування він іде в межах тижневої суми додаткових сесій.

### 5. Чого це не ловить
- Те саме, що й для `overseer` (`docs/engine-limits.md`, розділ «The overseer agent is read-only»):
  запис, який робить скрипт чи тест, що його агент лише запускає; шлях у змінній як аргумент.
  У `overseer` це після факту ловить fingerprint дерева; у critics такого запобіжника немає, і
  проєкт його не додає — це окреме рішення, якщо знадобиться.
- `WebFetch` і `WebSearch` у `slice-planner-critic` нічого не пишуть у дерево, але це вихід назовні.
  Лишені, бо інструкція вимагає читати документацію залежності.

## Що я розглянув і відкинув
- **Лише frontmatter.** Найдешевше, але `slice-planner-critic` лишається з Bash без жодної межі, а
  загублений рядок `tools` ніхто не помітить.
- **Лише perimeter.** Не прибирає `Agent` і MCP tools.
- **`disallowedTools` замість `tools`.** Перелік заборон треба доповнювати з кожним новим tool і
  MCP server; перелік дозволів — ні.
- **Забрати Bash у `slice-planner-critic`.** Його інструкція тримається на перевірці інструментом
  («Falsification here = run the test, not debate»); без Bash він переходить на маркер
  `CRITIC_PREMISE_PROBE_REQUIRED` там, де міг перевірити сам.
- **Guard, що відмовляє в запуску `critic-core`.** Вужчі tools роблять такий запуск нешкідливим;
  окремий guard — нова річ без потреби.

## Питання до власника
1. **Яка межа для п'яти critics?**
   - А — лише рядок `tools` у frontmatter за таблицею.
   - Б — лише перелік агентів у perimeter hooks.
   - В — обидва шари (розділ 3).
   Порада: **В**. Frontmatter прибирає `Agent` і MCP tools, perimeter тримає межу, коли рядок
   `tools` зник, і єдиний стримує Bash у `slice-planner-critic`.
2. **Bash у `slice-tester`.** `testing.py guard` дозволяє йому edit tools лише на тестових файлах,
   але `echo … > src/x.py` через Bash не зупиняє ніщо; `docs/engine-limits.md:638` каже ширше, ніж
   є («`guard` keeps the tester from WRITING anything but test files»).
   - А — окрема задача після цього будування: правило «shell пише лише в тестові файли і `/tmp`».
   - Б — у тому самому будуванні.
   - В — лишити як є і виправити речення в `docs/engine-limits.md`.
   Порада: **А**. Це нове правило (дозволені місця запису — не лише тимчасові), а не той самий
   перелік імен; змішувати його з цим будуванням — більший diff у perimeter за один раз.

## Демонстрація на хвилину
```bash
cd /home/lao/engine
for a in overseer slice-planner-critic; do
  printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","agent_type":"%s","cwd":"%s","tool_input":{"command":"echo x > docs/note.md"}}' "$a" "$PWD" \
    | CLAUDE_PROJECT_DIR=$PWD bash .claude/hooks/block-dangerous.sh >/dev/null 2>&1; echo "$a exit=$?"
done
# overseer exit=2
# slice-planner-critic exit=0
grep -L '^tools:' .claude/agents/*.md     # п'ять файлів critics
```

## Витрати
Платних сесій Claude не запускав; одне читання сторінки документації.

## Діапазон commit-ів
Від `d333e01` (задачу взято в `doing/`) до commit-а, що переносить її в `done/`. Змінено лише файли
в `tasks/` і журнал аномалій.

## Відкладене
- Будування за цим проєктом — окрема задача, з власником у сесії, як вимагає задача 734.
- Живий прогін critics із вужчими tools — у задачі будування.
- Запобіжник після факту (fingerprint дерева) для critics — не пропоную, доки немає випадку.

## Рішення, які я ухвалив сам
- До таблиці внесено всіх одинадцять агентів, а не лише critics і simplifier: задача каже «для
  кожного агента в `.claude/agents/`».
- `WebFetch` і `WebSearch` у пропозиції для `slice-planner-critic` лишено; іншим critics — ні.
- У перелік perimeter запропоновано внести й агентів, які вже мають лише Read, Grep, Glob.
- Знахідку про Bash у `slice-tester` подано питанням, а не окремим записом на task board: чи це
  взагалі робити, вирішуєте ви.
- Крок `reader` з правила 6 `tasks/README.md` не виконано: `reader.py request` приймає лише
  `--record` зі шляхом до sketch, прапорця `--report` у скрипті немає (задача 100 лежить у
  `blocked/`). Так само закрито задачу 402; про це є запис аномалії.

## Нові записи на task board
- `tasks/blocked/1723-open-item-734-critics-readonly-build.md` — «Critics read-only: будування за проєктом 734», з рядком `Потрібна присутність власника: так` і одним питанням: будувати за
  порадами цього звіту чи інакше.
