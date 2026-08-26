# What was cut, and what that costs

`live-build` is a reduction of a production agentic development system: four levels of
hierarchical planning, blind critics in fresh contexts, twenty-odd components, six
lifecycle hooks, a Python overseer running a twelve-check audit per unit of work, three
recursion guards, and an append-only ledger. That system is tuned for multi-day builds
under strict TDD. This one is tuned for forty-five minutes in front of an audience.

Every cut below is a real loss. Where a cut trades safety for speed, it says so.

---

## The sharpest question: enforcement versus instruction

**A hook is enforcement. A skill is instruction.** The parent system's discipline is
mostly executed by the harness whether or not the model cooperates: a `PreToolUse` hook
blocks the command before it runs, a `Stop` hook refuses to let the turn end. A skill is
text in the model's context. It can only ask.

That distinction decides what could survive the port at all:

| Parent mechanism | Kind | Here |
|---|---|---|
| Stop hook auto-triggering the audit on a unit-completion claim | **Enforcement** | Instruction: "run the three checks at the end of every unit." Skippable. Caught only by the missing audit line being visible in the on-screen ledger. |
| Stop hook running lint, types and tests, blocking turn end on failure | **Enforcement** | Instruction: check 2 demands the pasted command output. A model *could* claim green without running. On a shared screen the absence of output is what the audience notices. |
| `PreToolUse` guard blocking `rm -rf`, `git commit`, force-push, `curl | sh`, `sudo` | **Enforcement** | **Lost outright.** No skill can stop a bash call. Mitigated procedurally, not technically: run in a throwaway repo on a throwaway branch (`PREFLIGHT.md`). This is an accepted risk, not a solved problem. |
| `PreToolUse` guard on secrets, migrations, CI workflows | **Enforcement** | **Lost outright.** Low exposure in a greenfield 45-minute build; real if the session lands in a repo that matters. Same procedural mitigation. |
| Three recursion guards on the audit loop | **Enforcement** | **Not ported, deliberately** — see below. |
| Critic reviews the artifact, blind, in a fresh context | Structural | **Kept at full strength.** A separate OS process with nothing inherited is as blind as the parent's subagent. This is the one discipline that loses nothing, because it was never enforced by a hook — it was enforced by the *shape* of the call. |
| Ledger is append-only | *Already instruction in the parent* | Instruction, plus the file is on screen. Marginally stronger here. |

**On that last row.** It is easy to assume the parent's append-only ledger is protected by
the same guard that protects `.env` and `migrations/`. It is not. The path guard's deny
list is twenty-eight patterns and none of them matches the ledger; the permission deny
list never mentions `.claude/` at all; the only hook that names the ledger names it inside
a prompt string it injects into the model. Append-only is a convention the model follows
in both systems. Worth knowing before defending it as enforced.

**On the recursion guards.** The parent's three guards — an envelope flag, two SHA
idempotency files, and a verdict marker — exist to stop a Stop hook that re-injects itself
from looping forever. There is no hook here, so there is no loop, so there is nothing for
them to guard. They were not translated; they were retired alongside the mechanism they
protected. The live profile's real runaway risk is different — a model burning eight
minutes retrying one failing test, or re-planning twice — so a different limit was written
for it: two fix attempts, one re-plan, three units, two critic invocations.

**And those limits are instruction too.** Nothing stops a model from ignoring a number it
was told to respect. The mitigation is not technical: the unit counter and the elapsed
clock are printed at every phase boundary, so a violation is visible to the person
watching. **In this profile the human in the room is the enforcement mechanism.** That is
a genuine downgrade from a hook and should be conceded immediately if asked, because the
alternative — claiming a skill enforces anything — is false and will be caught.

---

## Cuts, and what each one was protecting against

### Three of four planning levels

Project architecture, feature decomposition, and the MVP framing level are gone, along
with their three dedicated critics. They protect against committing to a wrong
architecture or a wrong decomposition on work measured in weeks. There is one seam here
and no decomposition to get wrong. Their cheapest path costs hours. **Risk: none
meaningful at this scale.**

### The planner-critic convergence loop

The parent loops planner against critic until the critic finds no surviving blocking
objection, then runs a fresh cold-reader over the whole artifact to catch what the
round-anchored critic drifted past. Here the critic gets **one shot, capped at two
minutes**, and there is no cold reader.

**Lost:** convergence. A plan that is eighty percent right ships at eighty percent.
**Still caught by:** the per-unit audit compares code against the written contract, so
contract-level error surfaces within fifteen minutes rather than at the end. **Accepted:**
a subtly wrong plan that is internally consistent survives the whole session.

### RED → GREEN → REFACTOR, and the stop at every transition

The parent writes one test at a time, shows the failing output, implements minimally,
shows green, refactors, shows green again, and halts for the human at each transition —
roughly six checkpoints per behavior. Here: write the test against the contract, write the
code, run once.

**Lost:** proof that the test could ever have failed. A test written after the code can be
shaped by the code without anyone noticing. **Partially replaced by:** a one-line statement
of the wrong implementation each test would catch. **That is weaker than watching it fail,
and it is not a substitute.** Say so plainly rather than describing the sentence as
equivalent — it is a cheaper signal that catches the most obvious tautological assertions
and misses subtle ones.

### The real-system smoke script

The parent does not consider a slice complete until a script exercises the real external
system and a human confirms the result by eye. Cut entirely: a live session has no real
credentials and no admin panel to check.

**Lost:** the only check that green tests correspond to a working integration. **Nothing
replaces it.** This is the second-largest accepted risk in the profile and the one most
worth naming before an interviewer names it: everything demonstrated is proven against a
faked boundary. `SKILL.md` requires saying that out loud in the closing summary.

**One qualification, learned by running this.** When the external API needs no
authentication, a real call costs seconds and unit 3 should make one — a dry run of this
profile hit the live GitHub API from the mounted endpoint and got a real star count back,
which is a genuine integration check obtained for free. The cut is real when credentials
are involved, which is the common case in an interview; it is not a reason to skip a real
call that happens to be available. Check whether the boundary is reachable before assuming
it is not.

### Nine of twelve audit checks

Kept: contract match, tests-pass-with-evidence, scope. Those three cover the failures that
actually occur inside forty-five minutes, and all three are answered mechanically — quote
the contract line, paste the output, diff the file list — rather than by judgment.

Of the nine cut, four lose nothing here: fabricated-RED has no ceremony left to fabricate,
handoff-rationale protects session resumption that will not happen, ADR-required is
replaced by the ledger being a better decision record than a document nobody opens, and
stale-evidence is largely handled by every phase carrying a timestamp. Two are folded into
instructions rather than audited: masked-test-gap becomes the one-line justification per
test, and hardest-seam becomes the single riskiest piece named in the plan. One —
missed-alternative — moves into the ledger's mandatory `Instead of:` line, which is
**stronger** than the check it replaces, because it is written at the moment of the
decision and is visible to the audience rather than surfaced in an audit nobody reads.

Two are cut with real loss. **Soft-verdict-on-hard-data** protected against "seems fast
enough" sitting next to an unmeasured number; there is no performance work in forty-five
minutes, so the risk is small and accepted. **Bias-toward-agreement** is the uncomfortable
one.

### The devil's-advocate quota — replaced, not cut

The parent requires that after three consecutive passes the auditor spend a full check
building the strongest case that the developer is wrong, visibly, even if it still passes.
That check exists precisely because a self-audit drifts toward agreement.

The quota itself does not survive: with three units, a three-pass streak *is* the
successful path, so it would fire on every good session and cost two minutes of visible
theatre in a sixty-minute budget.

**What it is replaced by is not a weaker version of itself — it is a different and
arguably better mechanism.** At Phase 6 the critic runs a second and final time, in a
fresh process, given only the frozen plan and the final diff, and asked two questions:
does this deliver the contract, and does it contain anything nobody agreed to. Its verdict
goes into the ledger verbatim, including a negative one.

That is a real adversary rather than the same model grading its own work, which is what
the quota was a proxy for. It costs about fifteen seconds. It is also *better* placed than
the quota: the quota fires on a streak, which is a heuristic for "you have probably stopped
looking"; this fires on the finished artifact, which is the thing anyone actually cares
about being wrong.

**What remains uncovered.** The three per-unit checks are still self-administered, so a
unit can be waved through mid-session and only caught at the end — the close-out audit
finds it late or not at all if the diff looks plausible. The mitigation is that all three
per-unit checks are mechanical rather than evaluative (quote the contract line, paste the
output, diff the file list), which is harder to rubber-stamp than a judgment. That is
partial, and it is the honest residual: **one blind pass at the end, three self-checks
along the way.** Better than the earlier design, which had no adversary anywhere, and
weaker than a twelve-check audit run by a separate agent on every unit.

### The memory and governance layer

Cross-session learning, the cross-slice memory file, the self-improvement proposal log, the
premise log, progress files, ADRs, the documentation skill, the repo-configuration skill,
and the per-project hook config are all gone. They serve a system with a next session and a
repo it owns. A ninety-minute session in a stranger's repo has neither, and writing config
into a repo that is not mine would be the wrong behavior regardless of time. **Risk: none.**

### The constitution

Eight articles reduced to four, folded into the skill rather than kept as a separate
document: verify the load-bearing premise (as a bounded probe or an explicit stamped
assumption), claims are suspect until evidenced (the pasted-output bar), the human owns
product decisions (the escalation calibration), and critics are blind and fresh (kept
intact). Anti-Goodhart and cite-or-prune are dropped because there is no metric to game and
no memory to pollute in one sitting; self-improvement and the discovery-reopens-a-higher-
decision back-edge are dropped because both need a lifetime this session does not have.

---

## What the dry runs did and did not validate

This profile was run end-to-end twice before being trusted: a star-count endpoint, and a
webhook receiver with a requirement change injected mid-run. Both finished around 2:10.
**That number is not evidence the timing design works, and it must not be presented as
such.**

**Validated — mechanics.** The critic mechanism really invokes, returns inside its cap
(12s and 16s), and returned a genuine blocking objection both times: in run 1 a contract
with no channel for a dead connection, in run 2 a security ordering stated backwards. The
ledger format holds up. The timestamping works. The requirement-change procedure executed
against a real change and cost 38 seconds of model time. The seam-rejection path was
genuinely exercised — run 1's critic rejected the seam, the skeleton written during the
critic window was deleted and rewritten rather than patched, and the rollback was cheap
exactly as designed.

**Not validated — time discipline. Nothing about it.** No phase came within an order of
magnitude of its box. The "3 minutes over, cut scope, never extend" rule **has never
fired once**. Neither has the phase-overrun path, the unit-3 drop under time pressure
(run 2 dropped it, but by decision, not because the clock forced it), or any decision
made under actual time constraint. The entire timing design — the boxes, the hard stop at
T+5, the T+37 scope-versus-time cutover — is unexercised.

The reason is structural and worth stating: the runs measured model execution with no
human in the loop. A real session's 55 minutes is almost entirely human time — framing
aloud, narrating, being interrupted, reading output on a shared screen. So the two runs
tested every mechanism *except* the one the profile is named for.

The phase-boundary hold exists because of this finding. It does not fix it. **The first
real test of the time discipline will be the first real session.**

## Two things added rather than cut

**The clock as an artifact.** The parent has no notion of wall time; work takes what it
takes. Here every phase boundary runs one fixed command that stamps elapsed time and
appends to the ledger in the same call. This is the only piece of the design that exists
because of the audience rather than despite it — and the fixed-command form matters, since
a phase with no stamp is then a visible omission rather than a habit someone forgot.

**The ledger as the deliverable.** In the parent the ledger is an audit trail read by the
next audit. Here it is the primary artifact: plain English, headline-first, four lines per
decision, no internal vocabulary, optimised for someone reading it live while listening to
a person talk. The `Instead of:` line carries most of its value, because a decision without
a rejected alternative was not decided, it was defaulted into — and that is exactly what an
audience is trying to distinguish.

---

## Where this skill lives, and why that is a design decision

The skill's source of truth is `user/skills/live-build/` in the `claude-cli-config` repo,
symlinked to `~/.claude/skills/live-build`. Both paths are the same inode: there is one
copy of every file, edits in the repo are live immediately, and a stale deployed copy is
impossible by construction. `install.sh` recreates the link on any machine.

It is **not** under `<repo>/.claude/skills/`, and that is the load-bearing part. Skills
there are project-scoped — Claude Code loads them only when the working directory is that
project. Verified from an unrelated directory: the five skills in `.claude/skills/` do not
appear, and `live-build` does. A skill that only resolves inside its own repo does not
exist at the interview, which is the one place it has to work.

Symlink rather than copy, also verified rather than assumed: the loader dereferences
symlinks. The alternative is what this repo already does by hand for hooks, where
`~/.claude/hooks/verify-on-stop.sh` has drifted 224 lines from the repo copy and two hooks
are missing from the home copy entirely. That divergence is the argument.

## The one deliberate rule violation

`SKILL.md` says no implementation before the critic returns, then permits signatures and
type annotations to be written during the two-minute critic window.

That is a real exception to a real rule, and it is a bet: it trades a bounded rework risk —
ten to twenty lines of signature, deleted and rewritten rather than patched if the critic
rejects the seam — against two minutes of silence on a shared screen. It is affordable only
because the blast radius is bounded by construction: no branch, no call, no assertion, no
error handling may be written in that window, so nothing that encodes a decision the critic
could overturn exists yet.

It is written as an exception rather than hidden inside the phase description because an
interviewer who notices it should find that it was noticed first.
