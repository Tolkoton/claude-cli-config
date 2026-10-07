# Unattended work — the detail behind the rules

Read this when `.claude/state/overseer/mode` says `unattended`, when the board runner started
the session, or when you must park an item. The rules themselves are in
`.claude/engine-rules.md`; the runner's own documentation is `.claude/unattended/README.md`,
the board's manual `tasks/README.md`.

## The mode file

`.claude/state/overseer/mode` with the content `unattended` declares that nobody is in the
loop. Absent, or any other content, means attended — the default, so an interactive session
behaves exactly as before and a server run opts in explicitly
(`echo unattended > .claude/state/overseer/mode`).

What the mode changes, and only this: an interactive hard gate in `/plan-slice` or
`/feature-architect` becomes a park. The item waits, work continues elsewhere, and the gate is
surfaced at the next legitimate interruption. What it does **not** change — these hold in both
modes: the slice-builder cadence (one gate on the behavior list, then run the list through);
verdict routing (resolvable findings are fixed and logged, not escalated); the three reasons to
stop; Article 5 — a genuine one-way door (money, a real external system, irreversible data, a
published contract) parks and waits in **both** modes.

## Parking an item

Everything that can be open is a file of the task board, and it is closed the way every task is:
by moving to `tasks/done/`. To park an item, put it there:

```bash
python3 .claude/unattended/board.py open-item --to blocked --title "<the item, in a line>" \
    --what "<what happened, the exact thing needed, the evidence>" --question "<what you ask the owner>"
```

`--to blocked` is a question for the owner (`7NN-open-item-….md` with an empty `Відповідь:`; any
answer returns it to `todo/` as an instruction); `--to todo` is work an agent can do later
(`--do` says what); `--key <item id>` names the item, so a second call returns the task still
open instead of writing another. If the item is your own board task, ask in that task and move
it to `tasks/blocked/` instead (`tasks/README.md`, rule 4).

For an ask-gated command: the exact command in `--what`, and the question is whether the owner
runs it. `park-ask-gated.py` denies such a command unattended and hands you this instruction if
you forget.

`.engine/overseer/parked.md` and `.engine/overseer/escalations.md` are history. They are only
appended to — an AUTONOMOUS decision, closed by being logged, still goes to `escalations.md`;
a project without `tasks/` parks in `parked.md` — nothing in them is ever marked closed, and
nothing reads them to learn what is open: the owner's review shows `tasks/blocked/`.

Surface what is parked to the human when, and only when: nothing in the unblocked queue
can move; a single item is parked on a one-way door; three or more items are parked awaiting
ratification (the contract is systematically under-specified); or a premise in
`.engine/premises/premise-log.md` flips to `falsified` and committed work depends on it.

## Unattended work is the task board

There is one way to work with nobody watching: the task board. `.claude/unattended/board-runner.sh`
takes the tasks in `tasks/todo/` one at a time and starts a fresh session for each, with the mode
file saying `unattended` and `CLAUDE_UNATTENDED_SESSION=1` in the environment. Such a session
follows the «Правила для агента» of `tasks/README.md`: it ends with its task in `tasks/done/`
(with `report.md`) or in `tasks/blocked/` (with questions for the owner), committed through
`.claude/unattended/commit_checkpoint.sh`. A session that ends with the task still in
`tasks/doing/` is continued by the runner; one that cannot move is parked by the runner, never
by waiting. The feature DAG (`.engine/architecture/feature-dag.json`) is a plan `/feature-architect`
writes and follows inside a task — nothing executes it by itself.

## The owner's two rules (board 053)

**Quality over price.** Quality is the base of the system, not price. A task carries no dollar
limit: paid runs take what an honest result needs. The owner's leave is the line
`Платні прогони: так` (or `Аудит потрібен: так` for the audit) — no number; a dollar number the
owner did write there is a ceiling the paid-run scripts stop before. The line is read in the task's
header only and leave is recognised, not assumed: the line is the word «так», after which only a
dollar sum above zero may stand («так, до 30 доларів»); anything else in the line refuses, though a sum in it
still caps a run that another word of the owner opened (`Аудит потрібен: так`, `--owner-approved`). Only the runner's per-task
guard (`BOARD_MAX_USD`) stands against a loop: it does not cut the work, it parks the task with a
question, and the owner's answer continues it with the same budget again. Where something
proves too long or too dear — measure first, then simplify in a task of its own.

**Technical terms in English, wherever the owner reads** — a report's «Що змінилось для власника»,
a question in `blocked/`, the review, whatever a script writes for the owner. The terms as
practitioners use them: overseer, simplifier, critic, planner, builder, tester, test manager,
business analyst, slice, slice contract, gates, hook, runner, task board, inbox, audit, golden
set, invariant, property-based testing, mutation testing, spike, sandbox, and the like. In a
Ukrainian sentence the term keeps its English form and takes a hyphenated ending when it must
(`runner-а`, `slice-ів`, `audit-у`). A rare term may get a short Ukrainian gloss; the term itself
stays English. No invented Ukrainian translations («наглядач», «ворота», «зріз», «виконавець»…).
The lines the board reads — `Аудит потрібен:`, `Платні прогони:`, `Відповідь:` — are written as they are.
