---
description: The owner's review session. Runs `board.py review` (read-only), walks the document with the owner section by section, and writes the owner's answers and new tasks as files into the board's inbox. Changes nothing else. Use when the owner wants to look at what was planned, what is done and what waits for them.
---

You are running the **owner's review** of the task board. The owner reviews when they have time,
not when a task ends; the runner may be in the middle of a task right now, and that is fine.

This session has exactly two effects: the owner sees the picture, and files appear in the board's
inbox. **Nothing else changes**: no edit in the repository, no `git add`, commit, push, pull,
fetch or switch, no `board.py` command other than `review`, nothing under `.claude/state/`, no
task moved between the board's directories. The runner takes the inbox in before its next task.

Speak the owner's language (the board is in Ukrainian). `$ARGUMENTS` is passed to the review as
is — typically `--since <commit|date>`; empty means "since the newest version tag".

## 1. Make the document

```bash
python3 .claude/unattended/board.py review $ARGUMENTS
```

It reads the work branch in origin through git and writes nothing. Exit 2 means there is no
document: show the owner the reason and stop. If the head of the document says origin was out of
reach, tell the owner the picture may be stale before anything else.

Note the commit in the line «Джерело» — the answers below are written against that commit.

## 2. Walk it with the owner, one section at a time

Give each section in a few sentences of your own, then the details the owner asks for, and wait
for the owner before moving on (`AskUserQuestion` is right here). Do not paste the whole document.

1. **Стан зараз** — what the runner is on, for how long, what it has cost, whether it stopped and why.
2. **Зроблено** — per finished task: what changed for the owner, then the decisions the agent
   took alone. Ask whether any of those decisions should be reversed — a reversal is a new task.
3. **Чекає на власника** — every open question, one at a time, with its context and options. The
   owner may answer, or leave it for later. Also the tasks that need the owner present (the runner
   never takes them; they are done in an interactive session, not in this one), the settings proposals, the open escalations,
   the parked items and the rule proposals: each either gets an answer, becomes a new task, or waits.
4. **План** — the order of `todo/` and what stands on a dependency. A change of order or a
   rewritten task is a file for the inbox (below).
5. **Кандидати в нові задачі** — for each: a task now, later, or never.
6. **Здоров'я** — say it plainly; a red number is a candidate for a task.

Never answer for the owner and never guess an answer from an earlier remark. Two answers act by
themselves, so read them back and get an explicit yes before writing them: `так` under a question
with the line «Дія виконавця: …» (the runner applies the settings proposal), and `закрити` on a
question of the gate (the runner closes the escalation).

## 3. Write the answers and the new tasks into the inbox

The inbox is `$BOARD_INBOX`, by default `~/engine-ops/tasks-inbox` (`mkdir -p` it if absent). It
must be the inbox of the machine the runner works on; if this session is elsewhere, say so and
give the owner the files to deliver instead of pretending they arrived.

**An answer** is the blocked task's own file with the `Відповідь:` lines filled:

- take the text exactly as origin has it: `git show <commit>:tasks/blocked/<name>.md`;
- write the owner's words after `Відповідь:` on that same line, verbatim, and change nothing else
  in the file — the line «Дія виконавця: …» least of all;
- save it under the same name in the inbox, and only when **every** answer in that file is
  filled: the board does not accept a copy that leaves a question open. If the owner answered
  only some, write nothing for that task and tell them which questions remain.

**A new task** is a file `NNN-short-latin-name.md` made from `tasks/TEMPLATE.md`:

- the number sets its place in the queue; pick one that is in no column of the board and not in
  the inbox, below 800 (800 and up are rule questions and the gate's). A number that is already in `todo/` **replaces**
  that task — use it only when the owner wants that task rewritten;
- fill `Залежить від:` and `## Що зробити` / `## Готово, коли` from what the owner said;
  `Аудит потрібен: ні` unless the owner asked for the paid audit; a paid run needs its own line
  with a dollar limit; «спершу проєкт» when the owner wants a design first;
- show the owner the text and write it once they agree.

## 4. Close the session

List every file written (path, and one line on what it is), every question left unanswered, and
print the command for the next review — the last line of the document. Then stop: starting the
runner, pushing, or applying anything is not part of the review.
