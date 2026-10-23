# 1762 — preseal: the consequence of a late choice as its own finding (focus scene e fails after 204)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: 503-scene-e-consequence

## Що сталося
Board 503: focus scene e (business-analyst preseal on goals-v1 + interview) failed in both AFTER attempts (evals/baseline/linux-ubuntu-22.04/focus-evals-task-503.json, runs e/after #1 and #2): 5 of the 6 findings, the missing one is 'consequence | D1'. Both times the agent wrote the consequences of D1 (a delayed request after every week, everyone answers every week, someone must remind) inside the 'late-choice | D1' finding, as «Наслідок для інформації» / «До відома». In 502 scene e passed. The likely cause (not proved by a run) is board 204's text: .claude/references/business-analysis.md §10 says «A consequence (consequence, late-choice) is told to the owner in one line as information», which reads as if the two kinds were one; .claude/agents/business-analyst.md (mode preseal) asks for «lines chosen from the analyst's options, or settled late — for each, the consequences», without saying which kind they are filed under.

- Записано: 2026-10-23T20:41:50Z, агент
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Change the definition, not the scene: in .claude/agents/business-analyst.md (mode preseal) and in .claude/references/business-analysis.md §10, say that a line chosen late or from the analyst's options gets two findings: 'late-choice' (that it was chosen late and whose words it carries) and 'consequence' (what will have to be built, what it asks of people), each with its own question or '—'. Then re-run: python3 evals/run_focus_evals.py --scenes e --twice e --out evals/baseline/@env/focus-evals-<task>.json. The other option, accepting a consequence inside late-choice in expected.json, changes the scene to fit the result, which board 503 forbids (nothing is tuned to the result).

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
