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

Append to `.engine/overseer/parked.md`:

```
## <ISO timestamp UTC> — <slice slug or item id> — PARKED
- Blocked on: <the specific thing needed, in one line>
- Class: human-input | ask-gated | one-way-door | falsified-premise | external-verification
- Reversibility: <cost to reverse if decided wrong — required for one-way-door>
- Evidence: <file:line / test name / spike path / transcript turn>
- Unblocks when: <the observable event that lets this resume>
- Continued with: <what was worked on instead, or "queue exhausted">
```

For an ask-gated command: `Class: ask-gated`, the exact command under `Blocked on`,
`Unblocks when: a human runs it or the session becomes attended`. `park-ask-gated.py` denies
such a command unattended and hands you this instruction if you forget. Move an entry to
`RESUMED` in place when it unblocks; keep the history.

Surface the parked queue to the human when, and only when: nothing in the unblocked queue
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
