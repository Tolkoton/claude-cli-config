# Unattended work — the detail behind the rules

Read this when `.claude/state/overseer/mode` says `unattended`, when a supervisor is driving
the session, or when you must park an item. The rules themselves are in
`.claude/engine-rules.md`; the supervisor's own documentation is
`.claude/unattended/README.md` and its design decisions `unattended-decisions.md`.

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
`RESUMED` in place when it unblocks; keep the history. `recheck_parked.py` re-opens an item
automatically when its `Unblocks when:` line carries a machine-checkable token (`env:VAR`,
`file:PATH`, `node:ID`, `mode:attended`, `premise:ID`).

Surface the parked queue to the human when, and only when: nothing in the unblocked queue
can move; a single item is parked on a one-way door; three or more items are parked awaiting
ratification (the contract is systematically under-specified); or a premise in
`.engine/premises/premise-log.md` flips to `falsified` and committed work depends on it.

## The session contract (a supervisor is driving)

When `.claude/unattended/supervisor.sh` spawned this session, four obligations hold:

1. **Tick the heartbeat** while working: `python3 .claude/unattended/runstate.py heartbeat`.
   Together with the `.engine/PROGRESS.md` mtime this is the liveness signal; a session that
   updates neither for `STALL_TIMEOUT_SEC` is killed as wedged.
2. **Write a terminal status before you exit**:
   `runstate.py set finished|parked|halted "<reason>" "<what would unblock it>"`, or
   `set unit-done` when a unit is complete and work remains.
3. **Record cost**: `runstate.py add-cost <usd>`.
4. **Never invent `finished`.** If you stop without writing a status, leave it at `working`:
   the supervisor reads that as a death and retries, which is recoverable. A false `finished`
   is a silent overnight halt, which is not. Bias every ambiguous case toward the recoverable
   error.

Mapping to the three legitimate stops: `parked` = something only a human can supply, or a
falsified premise; `finished` = nothing left in the queue; `halted` = a cap fired and a human
must look.

## The continue guard

While an unattended run is live (mode file says `unattended`, the run state is `working`),
`overseer_stop.py` blocks the orchestrating session from ending its turn for any reason that
is not one of the three legitimate stops (`UNATTENDED_CONTINUE`, capped at 25 re-injections).
A session spawned by the supervisor is exempt: it must be able to exit with `unit-done`, and
a dying one must leave `working` behind. To stop for real, emit an `OVERSEER_` halt marker
naming the reason.
