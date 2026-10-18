# 1758 — master-critic: the mark [не слова власника] removes a protective element the owner's words back (scene i, board 501)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: focus-501-i

## Що сталося
Scene i failed after on both attempts and passed before: on domain-map-clean with goals-v2 the critic makes a BLOCKING objection to remove «Перевірка знеособлення», because G4 is wholly marked [не слова власника] and goals-fit check 6 says a mechanism resting only on marked words is not built. But interview item 7 has the owner's own words for G4 («друзі між собою журнали одне одного бачити не мають»); the mark is on the analyst's wording, not on the substance. The new rule made the critic remove what the fixture says must stay (a goal line, a scenario, a cost).

- Записано: 2026-10-18T21:45:17Z, агент
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
In .claude/agents/master-critic.md, goals-fit check 6: the mark means «check the substance», not «drop the element» — an element whose substance the owner said (in the core or in the journal) stands; only an element with no owner's words behind it at all becomes a question for the owner, and a question, not a removal. Consider giving the critic the interview journal for this check (today it gets only the product_frame). Then rerun: python3 evals/run_focus_evals.py --scenes i g h

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
