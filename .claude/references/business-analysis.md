# Business analysis — the analyst's method

Read on demand by `/business-analyst` (the conversation with the owner) and by the agent
`business-analyst` (the answer to an architect's request). Not loaded at launch. It holds
general method only: no client, project, person, sum or example a real case could be
recognised by ever goes into this file. A line is added here only through the lesson queue
(source `analyst`) and the owner's review — the analyst does not rewrite its own method.

The analyst decides nothing. It asks, sharpens, finds contradictions and writes down. Goals,
principles, thresholds and done-when are the owner's (constitution, Article 5).

## 1. The real goal behind the request

The first wording of a request is usually a solution, not a problem: someone wants X, thought
of Y, and asks for help with Y. Do not start designing Y.

- **Step back.** "What are you trying to get done with this? What does not work without it?"
- **Five whys.** Keep asking why until a concrete thing shows: a step that takes too long, money
  that leaks, a process that stops.
- A goal is written down only after it has passed "which problem does this solve".

## 2. Who the value is for

Name them before any goal: the **user** whose work gets easier, faster or less error-prone; the
**owner of the process**, who pays, answers for the budget or carries the legal risk; and the
**people it gets harder for** — support, security, operators. If nobody in the three groups
gains, the thing is not needed. This is the document's section «Для кого і навіщо».

## 3. The five opening questions — one at a time

1. What is broken right now? Where does the process stop or fail today?
2. What happens if we do nothing at all? If the business lives calmly without it for half a
   year, say so: the goal is postponed or dropped.
3. Who bears the loss right now?
4. What is the workaround today — the spreadsheet, the notebook, the message thread? The
   workaround shows how the thing will really be used.
5. On the thirtieth day after launch, how will we know it worked? What will be observably
   different?

Ask one, wait for the answer, push back on vagueness, then the next.

## 4. How each kind of line is written

- **Goal (G) — an outcome, not an output, and observable.** "Build a page with filters" is an
  output. "An operator finds a request in seconds instead of minutes" is an outcome. Value is
  stated in objective units — time saved, defect rate, time to result, throughput — never
  "more convenient". Ask "what will you see when this has worked" and write that:
  `- G1. <what must happen> — видно з того, що <the observable sign>.`
- **Principle (P) — a real choice between two good things.** "We value quality" is rejected:
  nobody values the opposite. `- P1. <X> понад <Y>. Приклад: <a decision this principle
  settles>.` Every principle carries one example of a decision it settles; without one it has
  not been understood yet.
- **Non-goal (N) — mandatory, never empty.** What suggests itself and is deliberately not done,
  and why: `- N1. <what we do not do> — бо <why>.` Non-goals protect the architecture from
  early complication.
- **Hard constraint (C) — with its source.** Three families to walk through: law and regulation
  (personal data, licences of what is reused, where data may live); budget and resources (a
  ceiling on running cost, hardware, limits and prices of outside services); time. For time,
  separate a **hard deadline** (an outside event that cannot move) from a **wished date** — with
  a wished date, scope wins over the date. `- C1. <the constraint> — джерело: <how we know>.`
- **Done when (D) — for the whole project**, checkable: `- D1. <condition>.` Readiness of a
  single task is not written here; the gate and the overseer hold that.
- **Open (Q)** — what the owner has not decided, and what architects assume until then.

Numbers are permanent. A line that no longer holds is struck through with a date
(`- ~~G2. …~~ (скасовано <date>)`), never deleted and never renumbered: an old citation must not
point at new content.

## 5. Before the owner approves — reread the draft against the traps

- **A solution instead of a problem.** A goal that names a button, a table, a tool.
- **Metrics for show.** Easy numbers that say nothing (things counted, accounts created). Once a
  measure becomes the target it stops measuring. Prefer measures of behaviour: work carried to
  the end, people who come back, time actually saved.
- **Invented requirements.** "What if tomorrow we need…": write only what is confirmed needed
  today. Whatever the owner did not ask for and no goal needs is taken out or moved to «Відкрите».
- **The golden hammer.** A familiar heavy tool named in a goal where something simple would do.
- **A contradiction left for later.** Two goals pulling apart with no principle saying which
  wins. That is a question for the owner now, in this conversation — not for an architect later.

## 6. When the analyst is called after the first conversation

Only by an architect, only for one of four reasons, and the list is closed:

| # | Reason | Looks like |
|---|---|---|
| 1 | **The document is silent.** The options differ in their consequence for the user or the business and no line says which is better | keep history for a year or for ever |
| 2 | **The document contradicts itself.** Two goals or two principles pull apart and no priority is written | "answers instantly" against "data always fresh" |
| 3 | **The decision would touch a non-goal, a constraint or a done-when** — including a finding from below that makes a goal unreachable as written, and effort out of proportion: most of the work going into a case the goals do not name | a check showed D2 cannot be met inside C1 |
| 4 | **The goals are changing** — the owner changes them, or there is silent drift: "it would also be nice if…", an exception to a rule ("always, except…"), an entity that changed its meaning, a test that suddenly needs new inputs | a new goal, a lifted non-goal |

Drift is named as a change of goals, never passed as "a small edit".

**Not reasons:** a technical choice with no consequence for the user or the business (the
architect decides); a technical one-way door (it goes straight to the owner, as before — the
analyst would be an extra link); a question from a slice (it goes to `/feature-architect`
first, who decides whether it is one of the four).

## 7. The request and the two answers

The architect writes `.engine/goals/requests/NNN.md` and starts the agent with that path alone:

```markdown
# Запит NNN до бізнес-аналітика
From: master-architect | feature-architect
Reason: 1 | 2 | 3 | 4
Door: two-way | one-way

## Рішення
## Варіанти
## Що каже документ
## Чого бракує
```

The agent sees the request, `.engine/goals.md` and its «Зміни» — not the architect's
conversation, so it does not inherit a leaning towards one option. It answers with exactly one
of two forms, which the architect pastes under `## Відповідь аналітика`:

```
ANALYST_ANSWER: QUOTE
Line: P2
Quote: <the line's text, verbatim, everything after "P2. ">
```

Allowed only when a standing line of the sealed document settles the choice **as written**.
Reading "in the spirit of the document", combining two lines into a third, or quoting a struck
line is forbidden. `python3 .claude/hooks/goals.py quote <request>` compares the quote with the
document; a quote that is not there makes the answer void and the request goes to the owner.

```
ANALYST_ANSWER: OWNER_DECISION
Питання: <plain language, no jargon>
Варіанти: <each option and the strongest case for it>
Порада: <which, and why>
Поправка: <the ready text of the line(s) to add or change, with numbers>
```

Until the owner answers: a two-way door — the architect acts on the advice, marks the decision
`PROVISIONAL` and goes on; a one-way door — that branch is parked and other work is taken.

## 8. Changing the approved document

The document is sealed (`goals.py seal`); a changed one is not in force. It changes only by the
owner's answer:

1. Write the whole new document to `.engine/goals/proposed.md`: the version raised by one, the
   changed lines, a line in «Зміни» (`- v<N>, <date> — <what and why>; request NNN`). Struck
   lines stay struck, numbers are never reused.
2. `python3 .claude/hooks/goals.py proposal` — it refuses an unlawful amendment and prints which
   decisions cite the changed lines.
3. Ask the owner. With the owner present: show the amendment; on approval the owner runs
   `python3 .claude/hooks/goals.py seal --owner-approved` in their own terminal after the text is
   in place. Without the owner: the question goes to `tasks/blocked/` with the line
   `python3 .claude/unattended/board.py action-line amend-goals` prints under it; the owner's
   «так» has the board runner apply and seal it. An agent never seals a changed document.
4. Every decision that cited a changed line is listed in `.engine/goals/to-review.md`; the
   architect rereads each and ticks it.

## 9. The owner's corrections are lessons

When the owner corrects the document on their own remark, not on an architect's request — "this
was not in the goals and should have been", "the principle is written wrongly" — the analyst
should have asked. Queue it: `python3 .claude/hooks/lesson_queue.py add --source analyst "<what
was not asked>"`. The owner's review decides whether it becomes a line of this file.
