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
- A premise in `.claude/premises/premise-log.md` flips to `falsified` and any
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

## 2026-08-27T18:45:00Z — S4b — PARKED
- Blocked on: permission to launch `.claude/unattended/supervisor.sh`, which spawns `claude` subprocesses in a self-restarting loop. The auto-mode classifier denies it.
- Class: human-input
- Reversibility: n/a — nothing built against it
- Evidence: the denial names the remedy directly — *"the user can add a Bash permission rule to their settings."* A single real session via `session-claude.sh` was permitted and passed (S4a, $0.203); only the supervising loop is refused.
- Unblocks when: Claude Code is **restarted** so the new permission rule is read, or the owner runs `bash .claude/unattended/supervisor.sh` once themselves.
- Continued with: S5 (protect-paths exception), then the backlog was exhausted.
- Note: this is the correct behaviour, not a defect. An agent granting itself the right to run an unbounded loop of agents is exactly the decision a human should make.

### 2026-08-27T18:52:00Z — S4b — update: rule added, still blocked until restart
- The owner said "додай сам". Added to `.claude/settings.local.json` (gitignored, machine-local — NOT to `settings.json`, which ships with the template; a template that pre-grants every downstream project the right to auto-launch a loop of agents is a bad default):
  - `Bash(bash .claude/unattended/supervisor.sh:*)`
  - `Bash(.claude/unattended/supervisor.sh:*)`
- Retested once. **Still denied.** Cause is documented in this repo's own
  `claude-autonomy/SKILL.md:158-160`: *"Settings.json is read at session start.
  Your current session is still using the OLD permissions."*
- Did not retry further — repeated attempts against a denial would be working
  around its intent, not testing it.
- Still blocked on: a session restart, which only the owner can perform.

## 2026-08-27T18:07:44Z — S3 — PARKED
- Blocked on: S3 has no DAG node to plan from — there is no feature artifact defining it, and no S2 to inherit an edge from.
- Class: human-input
- Reversibility: n/a — nothing has been built against it
- Evidence: `.claude/architecture/` does not exist (no domain map, no architecture map, no feature artifacts); `.claude/overseer/slice/` does not exist; no `PROGRESS.md`; a repo-wide grep for `S1|S2|S3`, `slice DAG`, `S2→S3` outside the generic skill/command/doc text returns zero hits; `.claude/premises/premise-log.md` holds only the template placeholder `PR-example-01`.
- Unblocks when: the owner supplies the feature frame S3 belongs to — what the feature delivers, its acceptance criteria, and where S3 sits in the slice sequence. `/feature-architect <slug>` produces exactly this and would emit S3 as a node with a contract `/plan-slice` can consume.
- Continued with: queue exhausted — this was the only referent named.

## 2026-08-27T19:25:00Z — S4b — RESUMED
- Was blocked on: a Claude Code restart so the `settings.local.json` supervisor
  permission rule would be read.
- What unblocked it: the restart happened. `bash .claude/unattended/supervisor.sh`
  was permitted on first attempt this session.
- Evidence: supervisor run 18:52:51Z-18:53:30Z with the REAL `session-claude.sh`
  crossed a node boundary twice with no human turn — `spawn P1` -> `unit-done` ->
  "self-feeding to the next node" -> `spawn P2` -> `unit-done` -> "DAG exhausted"
  -> state `finished`, sessions=2, exit 0, $0.478. A throwaway 2-node DAG was
  required because the live DAG had no ready node.
- DAG node S4b is now `done`. It is also permanently unspawnable by D-16: its own
  title matches the self-reference guard on "Prove supervisor", which is correct —
  a node whose task is to run the supervisor must never be spawned by it.
- Three defects were found only because this ran for real, none of which the two
  prior proofs could surface:
  - **D-19** every real session was handed the literal `{NODE}` and never learned
    which node it was building (bash ate the placeholder's brace inside
    `${VAR:-default}`). Both earlier proofs exported `SESSION_PROMPT` explicitly,
    so the production default was the one path never exercised.
  - **D-20** the Stop hook's only continuation branch was unreachable in this
    repo, so the orchestrating session stopped after every turn. The autonomous
    loop was dead while reading as configured.
  - The first ask-clean watcher reported the run finished before it started, by
    matching a terminal line from an earlier run in the same log (fixed: anchored
    to the last start banner).
