---
name: live-build
description: Timeboxed build discipline for a live, observed coding session — a technical interview, a recorded demo, or pairing in front of an audience. Runs fixed wall-clock phases against a real clock, one planning pass, one blind critic gate, a three-check audit per unit, and an on-screen decision ledger. ONLY use when the user explicitly invokes it by name ("/live-build", "run live-build", "start live-build"). Never activate for ordinary development, for a request to work quickly, for a request to timebox something, or for any task where the user did not name this skill.
---

# live-build

A live audience changes what discipline is affordable. Silence is expensive, stopping to
ask is expensive, and every phase boundary is something a watcher can see. This skill
trades depth of verification for legibility and pace.

**The one rule:** the clock is real and the ledger is on screen. Everything else bends.

This is a stripped-down profile of a much larger system. What was cut and why is in
`ARCHITECTURE.md`, phrased so it can be defended out loud. Read it before the session,
not during.

---

## 0. Setup — before the clock starts (~20 seconds)

Run this once, as the first thing. It starts the clock and writes the ledger header in the
same command, substituting only the task name:

```bash
rm -f /tmp/live-build-*; date -u +%s > /tmp/live-build-t0
printf '# Live build — %s\n\nStarted %s · 55-minute build budget · 3 units, the third droppable\nEvery entry is stamped with minutes elapsed since that start.\n' "TASK IN FIVE WORDS" "$(date -u +'%H:%M:%S UTC')" | tee LIVE-LEDGER.md
```

**The start time is generated, never typed.** In a dry run of this profile the header time
was hand-written and drifted about two minutes from the real `t0` in both sessions — every
subsequent stamp was correct and the header disagreed with all of them. A header that
contradicts the timestamps below it is worse than no header, because it makes a watcher
distrust the numbers that are actually right.

`LIVE-LEDGER.md` is the only file this skill creates outside the deliverable. Abandoning
the session costs one `rm`. See `FALLBACK.md`.

---

## 1. The ledger command — the same command every time

Every phase boundary and every decision is written with this exact one-liner. Two
substitutions only: `HEADLINE` and `BODY`. Nothing else varies.

```bash
E=$(( $(date -u +%s) - $(cat /tmp/live-build-t0) )); printf '\n### T+%02d:%02d — %s\n%s\n' $((E/60)) $((E%60)) "HEADLINE" "BODY" | tee -a LIVE-LEDGER.md
```

`tee -a` appends to the file **and** prints to the terminal in one call, so the entry is
visible whether the watcher is reading the file or the transcript.

Because it is one fixed command, a phase with no stamp is a visible omission in the
transcript, not a forgotten habit. **If you reach a phase boundary and have not run it,
you are behind — run it before doing anything else.**

Write in plain engineering English. No check numbers, no unit IDs beyond "Unit 2", no
skill vocabulary. Someone who has never seen this system must understand every line while
half-listening to a human talk.

### Entry shapes

**A decision.** Every non-obvious choice, at the moment it is made.

```
### T+09:14 — Retry on server errors, not on bad requests
Chose: two retries with a short backoff, for 5xx and timeouts only.
Instead of: retrying every failure, which hammers the upstream on a bad request.
Because: a 400 will never succeed on a second attempt; a 503 usually will.
```

The `Instead of:` line is mandatory and is the single most valuable line in the artifact.
If no alternative was considered, the decision was not made — it was defaulted into. Say
so: `Instead of: nothing — this is the obvious default and I did not weigh alternatives.`

**Plan frozen** (end of Phase 1), **outside review** (end of Phase 2), **unit done** (end
of each build unit), **requirement changed**, and **done for this session** — shapes given
in their phases below.

---

## 2. Phases and their boxes

`t0` is the setup command above. Every boundary is stamped.

| # | Phase | Box | Ends at |
|---|---|---|---|
| 1 | Frame, detect, plan — **hard stop** | 5 min | T+5 |
| 2 | Blind critic on the plan (real 120s cap) | 2 min | T+7 |
| 3 | Unit 1 — the contract boundary, and its test | 15 min | T+22 |
| 4 | Unit 2 — the riskiest logic, and its test | 15 min | T+37 |
| 5 | Unit 3 — wire-up and the rest — **droppable** | 10 min | T+47 |
| 6 | Close — full run, summary, what is left | 8 min | T+55 |
| — | Reserve — absorbs one requirement change | 5 min | T+60 |

First executable code lands at **T+7**, not T+12. That is deliberate and is a bet — see
§4.1.

### The phase-boundary hold — every phase ends by stopping

At the end of every phase, without exception:

1. Run the ledger stamp for that phase.
2. Print a two-to-four line summary of what just happened and what the next phase will do.
3. **Stop. Wait for the operator to say continue. Do not begin the next phase.**

**This is not a question and must not be phrased as one.** Do not ask "shall I proceed?",
do not offer options, do not use a question mark. Print the state of the world and halt.
The operator is talking through the pause; a question would interrupt them, which is the
opposite of the point.

The hold is free. It consumes no budget, because the wall-clock boxes measure the phase,
not the pause, and the operator is narrating during it. It exists because a phase's model
side completes in roughly twenty seconds while its human side takes minutes — without a
hold the model races ahead of the narration and the session reads as the model driving
with a person watching, which inverts what is being demonstrated.

This does not weaken §6. §6 forbids stopping to **ask**; this is stopping to **pace**.
They are different acts and only one of them costs the operator anything.

**A phase that runs 3 minutes over its box does not get extended.** Cut scope inside the
phase, stamp what you cut, and move to the next boundary on time. The clock is the part
the audience can see; a blown box that is announced is a demonstration of judgment, and a
blown box that is hidden is just being late.

---

## 3. Phase 1 — Frame, detect, plan (T+0 → T+5, hard stop)

### 1a. Detect the ground (30 seconds, one command)

The repo may be empty, may not be Python, may have no runner. Find out in one bounded
call rather than discovering it at T+20:

```bash
ls -1 package.json pyproject.toml setup.py go.mod Cargo.toml pom.xml build.gradle Gemfile composer.json 2>/dev/null; echo "--- runners ---"; for c in pytest npm go cargo mvn gradle bundle; do command -v $c >/dev/null && echo "$c: yes"; done; echo "--- tests ---"; ls -d test tests spec __tests__ 2>/dev/null
```

- Something came back → use it. Match the repo's existing conventions; do not import your
  own.
- Nothing came back → pick the stack the task implies, and **stamp the assumption**:
  `Chose: Python 3 with pytest. Instead of: asking. Because: the repo is empty and the
  task names FastAPI; a wrong guess costs one file, and asking costs 30 seconds of
  silence.`

Do not spend a second minute here. An unknown runner is a ledger line, not a blocker.

### 1b. Frame (2 minutes)

Four things, no more:

1. **Building** — one sentence, the observable outcome.
2. **Contract** — the seam: function or endpoint signature, input types, return shape, how
   failure is reported. This is what the per-unit audit checks against, so it must be
   written down, not held in your head.
3. **Riskiest piece** — the single place where a naive implementation would look correct
   and be wrong. Exactly one. This is where the second test goes.
4. **Not building** — at least two explicit exclusions. An empty exclusion list means no
   scope discipline, and scope is one of the three things audited.

Dependencies are injected — external clients, clocks, and config are parameters, never
imports inside the module. This is not purity; it is what makes the failure-path test
runnable in seconds with no network, and there is no time for anything slower.

### 1c. Plan the three units (2 minutes)

One line each: what it delivers, and which of the two tests (if either) lands in it.
Unit 3 is written knowing it may be dropped, so nothing in units 1-2 may depend on it.

### 1d. Stamp and freeze

```
### T+04:50 — Plan frozen
Building: <one sentence>
Contract: <the signature, verbatim>
Riskiest piece: <what, and why it fools a naive implementation>
Not building: <exclusions, comma separated>
Units: 1 <name> · 2 <name> · 3 <name, droppable>
```

**Hard stop at T+5.** A plan that is 80% right and frozen beats a plan that is 95% right
at T+9. The per-unit audit catches contract drift within fifteen minutes anyway.

---

## 4. Phase 2 — One blind critic, one real cap (T+5 → T+7)

The critic reviews **the plan, before implementation**. It never runs on code, and it
never runs twice. In the full system a planner-critic loop runs to convergence; here it
gets one shot, because a second round costs more than the errors it finds at this scale.

### The mechanism, and why it is this one

Write the plan to a file and launch a **separate `claude` process** with an OS-enforced
timeout, in the background:

```bash
cat > /tmp/live-build-critic-in.txt <<'PROMPT'
You are reviewing a build plan for a 45-minute live coding session. You can see only the
plan below — not the author's reasoning. Do not be agreeable; the plan defaults to
suspect. But raise an objection ONLY if all four are true: (1) it would change what gets
built, (2) it can be settled by an observation or a clearly stronger argument, (3) it is
about this plan and not about architecture above it or style below it, (4) it is not a
duplicate of another objection.

Return at most ONE blocking objection — the single most important — in under 120 words.
If nothing meets all four bars, reply exactly: PASS.

PLAN:
<paste the frozen plan here>
PROMPT
timeout 120 claude -p "$(cat /tmp/live-build-critic-in.txt)" < /dev/null 2>/dev/null > /tmp/live-build-critic-out.txt; echo "EXIT:$?" >> /tmp/live-build-critic-out.txt
```

Run that with `run_in_background: true`.

**Both redirections are load-bearing and were found by this failing in a dry run.**
Without `< /dev/null` the process blocks waiting on standard input and burns three seconds
before proceeding. Without `2>/dev/null` any permission-configuration warnings the binary
prints land in the same file as the verdict and bury it. If the critic returns something
that does not look like a verdict, check that both redirections are present before
concluding the critic failed.

Why a separate process rather than a subagent: **the cap has to be real.** A subagent call
cannot be cancelled or bounded from inside the session, so a "2-minute cap" on one would
be a cap nothing can apply. `timeout 120` is enforced by the operating system. It is also
a genuinely fresh context — a different process, with nothing inherited — which is the
property that stops a critic from rubber-stamping work it helped produce.

At T+7, collect with one call:

```bash
cat /tmp/live-build-critic-out.txt
```

- `EXIT:0` and a verdict → act on it.
- `EXIT:124` → the timeout fired. Proceed without it. Stamp that it was discarded.
- No `EXIT:` line at all (background start was delayed) → proceed without it, stamp it,
  and do not wait. Do not revisit it later; a critic verdict that arrives during unit 1 is
  reviewing a plan that is already being built and is worth less than the interruption
  costs.

### 4.1 The seam-skeleton exception (read this before defending it)

**The rule is: no implementation before the critic returns. This is the one exception.**

During the critic window (T+5 → T+7) you may write **only**:

- the module or route file with the agreed signatures and type annotations,
- value objects / response models named in the contract,
- an empty test file with imports and the two test names as stubs.

You may **not** write: any branch, any call to the dependency, any error handling, any
assertion body. Nothing that encodes a decision the critic might overturn.

If the critic rejects the seam, **delete the file and start it again** — do not patch it.
The blast radius is bounded to roughly 10-20 lines of signature by construction, which is
why the exception is affordable. Stamp the deletion; a watcher seeing the file disappear
should see why in the ledger.

The honest framing under questioning: this trades a small amount of rework risk against
two minutes of dead air on a shared screen, and it is a bet, not a free lunch. If the
critic overturns the seam, the bet lost, and the ledger will say so.

### Stamp

```
### T+07:02 — Outside review of the plan: <no blocking objection | one objection>
Said: <the objection in one sentence, or "nothing blocking">
Did: <changed the contract to X | noted and continued, because Y | discarded, it ran past
      the two-minute cap>
```

---

## 5. Phases 3-5 — Build units (T+7 → T+47)

Each unit: write the code, write its test if this unit carries one, run the tests, audit,
stamp. No RED/GREEN/REFACTOR announcement ceremony, no per-transition stop, no behavior
enumeration round. The order still holds — a test is written against the contract, not
against the implementation you just wrote.

### Tests: exactly where they earn their place

**Two tests. Four is the hard ceiling.**

1. **The contract boundary** — the seam does what the plan says it does, called the way a
   caller will call it.
2. **The riskiest piece** — the one named in Phase 1b, usually the failure path.

For each, state in one line what wrong implementation it would catch. A test that passes
against a plausible wrong implementation is not a test, it is decoration. This is a
weaker guarantee than watching a test fail first, and it is written down as weaker in
`ARCHITECTURE.md`.

Never in this profile: mutation testing, property-based sweeps, exhaustive behavior
enumeration, security/performance/concurrency lenses, or a test for a behavior nobody
agreed to build.

### The audit — three checks, at the end of every unit

Mechanical, not evaluative. Each is answered with an artifact, not a judgment.

1. **Does it do what we agreed?** Quote the contract line from the frozen plan and point
   at the code that satisfies it.
2. **Do the tests pass?** Paste the actual command and its actual output. "Tests pass"
   without visible output is not an answer — and on a shared screen the absence is what
   the audience notices.
3. **Did anything get built we did not agree to?** List every file and public function
   this unit created; compare against the plan's list. Name any extra and why it exists.

If check 3 finds something unagreed and it is not a change to *what we are building*,
keep it and say why in one line. If it **is** a change to what we are building, that is a
stop condition (§6).

### Stamp

```
### T+21:40 — Unit 1 done: <name>
Does what we agreed: yes — <the contract line it satisfies>
Tests: <N> passed — <the exact command>
Anything unagreed: no
```

---

## 6. Decide, don't ask

Default is **decide and report in one line, with the reason**, in the ledger. Every stop
is dead air on a shared screen.

This calibration is inherited, not invented — it is the critical-interrupt set from the
parent system's feature-level orchestrator, narrowed. Nothing was added to it.

**Stop only for these three:**

1. **A product decision that changes what we agreed to build** — a threshold, an
   acceptance criterion, user-visible behavior that the frozen plan did not answer and
   cannot be derived from it.
2. **The contract cannot be built as agreed** — the seam is wrong, or the task turns out
   to be a different size than the plan assumed.
3. **A genuinely irreversible decision the plan did not pre-decide.** Note that in a
   45-minute throwaway build almost nothing is irreversible, so this should essentially
   never fire. If it seems to be firing, it is probably a two-way door and you should
   decide it.

**Never stop for:** a library choice, an error-handling style, a naming question, a file
layout, a test framework, a confirmed assumption. Decide, stamp one line, keep typing.

Two rules carried over verbatim in spirit:

- **A probe that confirms the assumption never interrupts.** Only a falsified one does,
  and only if it changes what we agreed to build.
- **Batch the interrupts.** If you must stop, ask everything pending in one exchange, each
  with your recommendation, so it costs one turn and not three.

Non-convergence — a limit in §7 hit — is **reported with a recommendation, not asked**.

---

## 7. Stop conditions — instruction, not enforcement

In the parent system, limits like these are enforced by hooks the model cannot bypass.
**Here they are instructions the model checks against itself, and nothing stops a model
that ignores its own limit.** That is stated plainly in `ARCHITECTURE.md` because it is
the sharpest question available about this design.

The mitigation is visibility, not enforcement: the unit counter and the elapsed clock are
printed at every boundary, so a violation is visible to the human watching. **In this
profile the human is the enforcement mechanism.**

Check these at every phase boundary and state the count in the stamp when it is not the
first:

| Limit | Number | On hitting it |
|---|---|---|
| Build units | 3 | Stop building. Go to Phase 6. |
| Fix attempts on one failing test | 2 | Third failure: stop, report the failure and the two attempts, recommend cutting the unit. Do not invent a fourth approach. |
| Critic invocations | 2, ever — one on the plan (§4), one on the final diff (§9) | Never a third. Not on a re-plan, not mid-unit, not on a failing test. |
| Re-plans per requirement change | 1 | A second change to the *same* requirement stops and asks. |
| Tests | 2 planned, 4 absolute | Do not add a fifth — **except** after a requirement change that introduces a risk class the plan did not contain, which buys at most 2 more. Stamp the raise and why. A requirement moving is a legitimate reason; four feeling tight is not. |
| Phase overrun | 3 min | Cut scope inside the phase; never extend the box. |
| Files outside the plan's file list | 0 without a ledger line | Every extra file gets a stamped line or does not get created. |

**Amending a limit.** A limit that binds is amended only with a ledger entry naming the
new risk class that justifies it. Without that rule the pattern is that every limit
dissolves at the exact moment it first costs something, which is the moment it was written
for. "The requirement changed and replay attacks are a risk the plan did not contain" is a
new risk class. "Four felt tight" is not, and neither is "this one is nearly done."

---

## 8. Requirement change mid-flight

The most likely live event. It has a fixed procedure so it costs a known amount.

**Step 1 — restate it (15 seconds).** Say the change back in one sentence, in the
interviewer's own words. Do not start typing until it is restated; misunderstanding a
requirement change is more expensive than any other error available in this session.

**Step 2 — re-open only the affected contract line (2 minutes).** Not the whole plan. Read
the frozen plan, find the line or lines the change touches, rewrite only those. Everything
whose contract line is untouched is kept, including its tests.

**Step 3 — discard, visibly (1 minute).** Delete the code whose contract line changed.
Say the line count out loud. Do not patch around a changed contract — patched-around code
is how a live session quietly turns into a mess an audience can see.

**Step 4 — stamp (1 minute).**

```
### T+30:15 — Requirement changed: <the change, in the interviewer's words>
Keeping: <what survives, and why it is unaffected>
Throwing away: <what dies — N lines in <file>>
Cost: 4 minutes of replanning, plus <what pays for the rebuild — see below>
```

**No second critic pass.** The critic budget is one invocation and it is spent.

### What it costs — the arithmetic, stated honestly

Four minutes covers restating, re-planning, and discarding. It does **not** cover
rebuilding what was discarded. The rebuild is paid for in scope, and the absorber is
**unit 3**:

- **Change before T+22** — 4 minutes from the reserve, and the rebuild fits inside units 2
  and 3. Full scope may still land.
- **Change between T+22 and T+37** — 4 minutes from the reserve, and **unit 3 is dropped**
  to pay for the rebuild. Say this at the moment of the change, not at T+47: *"this costs
  us the wire-up step; we'll finish with the endpoint tested but not mounted."*
- **Change after T+37** — there is nothing left to drop. **It costs scope, not time.**
  Name precisely what will not be built, keep the clock, and finish on time with less.
  Do not extend the session to absorb a late change.

A change that arrives after T+47 is recorded in the ledger and not built. That is the
correct answer, and saying it plainly is a better demonstration than a rushed
half-implementation.

---

## 9. Phase 6 — Close (T+47 → T+55)

1. Run the full test suite once. Paste the real output.

2. **The close-out blind audit — the second and last critic invocation.**

   The three per-unit checks are run by the same model that wrote the code. This is the
   one pass that is not. Same mechanism as §4, same timeout, same redirections, given only
   the frozen plan and the final diff — never the reasoning that produced either:

   ```bash
   { git diff HEAD > /tmp/live-build-diff.txt 2>/dev/null || git diff > /tmp/live-build-diff.txt; }
   [ -s /tmp/live-build-diff.txt ] || git diff --no-index /dev/null . > /tmp/live-build-diff.txt 2>/dev/null
   cat > /tmp/live-build-audit-in.txt <<'PROMPT'
   You are auditing the result of a 45-minute live coding session. You can see only the
   agreed plan and the final diff — not the author's reasoning, and not the conversation.

   Answer two questions, in under 150 words total:
   1. Does the diff deliver the contract in the plan? Name anything in the contract that
      is missing or that the diff implements differently.
   2. Does the diff contain anything the plan did not agree to? Name each file, function
      or behaviour that has no line in the plan.

   Do not comment on style, naming, or test coverage depth. Do not be agreeable — but do
   not manufacture findings either. If the diff delivers the contract and nothing beyond
   it, reply exactly: CLEAN.

   PLAN:
   PROMPT
   cat /tmp/live-build-plan.txt >> /tmp/live-build-audit-in.txt
   printf '\n\nDIFF:\n' >> /tmp/live-build-audit-in.txt
   cat /tmp/live-build-diff.txt >> /tmp/live-build-audit-in.txt
   timeout 120 claude -p "$(cat /tmp/live-build-audit-in.txt)" < /dev/null 2>/dev/null > /tmp/live-build-audit-out.txt; echo "EXIT:$?" >> /tmp/live-build-audit-out.txt
   ```

   Run it with `run_in_background: true`, then collect with `cat /tmp/live-build-audit-out.txt`.

   **The verdict goes into the ledger verbatim, whatever it says.** A finding against the
   work is the single most valuable line the artifact can carry — it is the only evidence
   in the whole session that the audit was capable of returning something other than
   approval. Never paraphrase it, never soften it, never omit it because the session is
   nearly over. If it names something real and there is time, fix it and stamp the fix; if
   there is not, stamp it as a known finding and say so out loud.

   Same failure handling as §4: `EXIT:124` or a missing `EXIT:` line means proceed without
   it and stamp that it was discarded.

   ```
   ### T+51:20 — Independent check of the finished work: <CLEAN | one finding>
   Said: <verbatim, including anything critical>
   Did: <fixed it and re-ran the tests | recorded as a known finding, no time to fix
         | discarded, it ran past the two-minute cap>
   ```

3. Stamp the closing entry:

```
### T+54:30 — Done for this session
Built: <what works, in one sentence>
Proven by: <the tests, named, and the command that runs them>
Not built: <what was scoped out, and when>
Known gaps: <what a reviewer should not assume is covered — say the mocked boundary out loud>
```

4. Say the gaps out loud too. The largest one is almost always the same: the external
   dependency was faked in tests and never called for real. That is a deliberate cut of
   this profile, not an oversight, and naming it first is stronger than being asked.
5. Do not commit. Stage if asked; the commit is the human's.

---

## 10. Anti-patterns — refuse these mid-session

If the session drifts toward any of these, name the drift in one line and keep building:
abstract base classes or protocols with exactly one implementation, factories, plugin
systems, `*Manager` / `*Service` indirection, retry policies or circuit breakers that
nobody asked for, structured logging, observability, a config system, a database when a
dict is the agreed contract, or starting the next unit's work "while we're here."

The response is one sentence: *"That's outside what we agreed to build — I'll note it as a
follow-up and keep going."* Then stamp it under `Not building` and continue.
