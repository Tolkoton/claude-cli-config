# 1763 — consult: a silent document on what the user gets is the owner's, even behind a two-way door (focus scene f-trap fails after 204)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 503-scene-f-trap-owner-want

## Що сталося
Board 503: focus scene f-trap (business-analyst consult on request-silent.md: which language the app talks in; the document has no line on it; the request asks «чи всі друзі пишуть українською і чи важливо це власникові») answered NOT_REQUIRED in both AFTER attempts, with the smallest form «вирішує архітектор як two-way door: одна мова». Expected and in 502: OWNER_DECISION. In its own words the agent reasons with board 204's §0: only the owner can answer, but the answer is not needed now, and the door is two-way, so it is the architect's. That clashes with §6 case 1 of .claude/references/business-analysis.md («The document is silent. The options differ in their consequence for the user or the business and no line says which is better») and with consult's «When in doubt, this one» in .claude/agents/business-analyst.md: the language the user is talked to in is what the owner wants, not how it works.

- Записано: 2026-10-23T20:41:51Z, агент
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Change the definition: in .claude/references/business-analysis.md §0 and in the consult part of .claude/agents/business-analyst.md, say that 'needed now' holds for a request an architect has already asked, when the options differ in what the user gets and the document is silent (§6 case 1): that is OWNER_DECISION even behind a two-way door; NOT_REQUIRED with «вирішує архітектор як two-way door» stays for a doubt over how something works, where the options do not differ for the user. Then re-run: python3 evals/run_focus_evals.py --scenes f f-trap --twice f-trap --out evals/baseline/@env/focus-evals-<task>.json (f must stay NOT_REQUIRED naming N3).

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
