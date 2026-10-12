# 734 — Які інструменти мають critics і simplifier: якщо є Bash — та сама read-only межа, що й для overseer

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: critics-simplifier-tools-readonly

## Що сталося
Задача 055 зробила read-only в perimeter лише агента overseer: hooks дивляться на agent_type, рівний overseer. Інші агенти, що мають лише читати й судити, цим не охоплені. Попередній огляд frontmatter у .claude/agents/, зроблений у сесії 2026-10-06 і не перевірений глибше: simplifier і business-analyst мають tools: Read, Grep, Glob — Bash і edit tools у них немає; critic-core, master-critic, feature-critic, slice-planner-critic і mvp-critic рядка tools не мають зовсім, тобто дістають усі інструменти, зокрема Bash, Edit і Write.

- Записано: 2026-10-06T15:03:14Z, агент

## Що зробити
Перевірити для кожного агента в .claude/agents/: які інструменти він має за frontmatter і які йому справді потрібні за його інструкцією — чи critic запускає proof-of-concept або tracer bullet, чи пише файли й куди. Для кожного, хто має Bash або edit tools, але за роллю лише читає й судить, запропонувати межу: або звузити tools у frontmatter, або та сама read-only межа в perimeter, що й для overseer — перелік агентів замість одного імені в protect-paths.sh і block-dangerous.sh, shell_readonly.py той самий. Якщо агентові за роллю треба писати — наприклад critic веде файл дебатів або PoC у тимчасовій теці — назвати точно, куди, і дозволити лише це. Спершу проєкт рішення з таблицею: агент, інструменти зараз, що потрібно, пропозиція. Будування зачіпає perimeter hooks, тому воно — у сесії з власником; тести на кожного агента з негативними випадками і golden set.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
