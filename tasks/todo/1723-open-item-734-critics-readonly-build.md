# 1723 — Critics read-only: будування за проєктом 734

Залежить від: —
Потрібна присутність власника: так
Аудит потрібен: ні
Відкритий пункт: 734-critics-readonly-build

## Що сталося
Проєкт рішення 734 (tasks/done/734-open-item-critics-simplifier-tools-readonly/report.md) показав: critic-core, master-critic, feature-critic, slice-planner-critic і mvp-critic не мають рядка tools у frontmatter і дістають усі інструменти сесії — Bash, edit tools, Agent і MCP tools; perimeter hooks стримують лише agent_type overseer (block-dangerous.sh:353, protect-paths.sh:52). За інструкціями жоден critic не пише в дерево; Bash потрібен лише slice-planner-critic. Будування за розділами 2–4 звіту: рядок tools у п'яти файлах агентів; перелік READONLY_AGENTS у protected-path-list.sh замість одного імені в обох hooks, shell_readonly.py той самий, ім'я агента в тексті відмови; тести на кожного агента з негативними випадками, тест frontmatter, golden set і новий baseline; docs/engine-limits.md і .claude/references/hooks.md. Будування зачіпає perimeter hooks, тому воно — у сесії з власником (задача 734). Чекає на відповідь на два питання звіту.

- Записано: 2026-10-12T07:18:44Z, агент

## Що зробити
Це питання до власника, не робота для агента. Коли власник відповість, задача повернеться в чергу: виконай відповідь, запиши її у звіт і закрий задачу.

## Готово, коли
Власник відповів, і відповідь виконано.

## Питання до власника
1. Будувати за порадами звіту 734 — питання 1 варіант В (frontmatter і perimeter разом), питання 2 варіант А (Bash у slice-tester — окрема задача після цього будування)? «так» — будувати так; інакше напишіть, який варіант для кожного з двох питань.
   Відповідь: так
