# Parked queue — items that cannot move, and what each is waiting on

The mechanism that replaces stop-and-wait. When an item cannot proceed, it is
parked here with the specific thing it needs, and work continues on the next
unblocked item. Nothing halts the run except an empty unblocked queue.

Governed by the unattended-operation cadence ratified 2026-08-27 (see
`audit.md`). Article 5 still governs what may be decided autonomously: one-way
doors park, two-way doors are decided and logged provisionally.

## The three legitimate reasons to surface to a human

1. **Human-only input** — a credential, a deploy, a provisioning step, a person
   with a phone, ratification of a genuine one-way door.
2. **Falsified premise** — a load-bearing assumption is refuted in a way that
   invalidates work already committed to.
3. **Queue exhausted** — every remaining item is parked or done.

Anything else is decided, logged, and continued.

## Surface thresholds

Surface the parked queue when ANY of these is true:

- Nothing in the unblocked queue can move (reason 3).
- A single item is parked on a **one-way door** — money, a real external system,
  irreversible data, a public contract (reason 1).
- **Three or more** items are parked awaiting ratification. Three is the signal
  that the contract itself is systematically under-specified, which is a human
  problem, not an item problem.
- A premise in `.engine/premises/premise-log.md` flips to `falsified` and any
  parked or completed item depends on it (reason 2, Constitution Art. 8).

## Entry format

```
## <ISO timestamp UTC> — <slice slug or item id> — <PARKED | RESUMED | SURFACED>
- Blocked on: <the specific thing needed, in one line>
- Class: human-input | ask-gated | one-way-door | falsified-premise | external-verification
- Reversibility: <cost to reverse if decided wrong — required for one-way-door>
- Evidence: <file:line / test name / spike path / transcript turn>
- Unblocks when: <the observable event that lets this resume>
- Continued with: <what was worked on instead, or "queue exhausted">
```

Move an entry to `RESUMED` in place when it unblocks; keep the history.

## Parked items
