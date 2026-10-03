# Feature engine-package-costs — the overseer sees gate-allow, cheaper audits, models by role

Frame source: `docs/plan/package-costs.md` (the owner's text, verbatim). Every numbered item is an
owner requirement; the critic checks how each is met, not whether, and gets at most two rounds.
Branch `unattended/2026-10-03-package-costs` from the end of package B (`d6b9947`). Standing rules
from the program: `bash tests/run_all.sh --fast` after every slice, the full set and the golden set
at the end, ruff and `mypy --strict`, UTC only, new commits only, nothing pushed, the owner is not
asked — whatever needs the owner is parked with its exact command.

## Goal

Three holes are closed. (1) An exemption from the gate stops being free: every `gate-allow` a
slice's diff adds is collected by a script and put in front of the overseer, who judges each reason,
and the overseer's own hook refuses a PASS while the gate has an open escalation for the slice.
(2) The model-judged audit stops being the price of every change: one run per scenario by default,
three only before a version tag, and a script that says whether an audit is due at all. (3) The
critics run on a cheaper model; the overseer and the architects stay on the strongest. A full audit
of the result closes the package.

## Acceptance criteria (the owner's, from the program's "ГОТОВО, КОЛИ")

- Every suite green (`bash tests/run_all.sh`).
- The golden set identical to the newest reference except what this package means to change.
- ruff and `mypy --strict` clean on the changed and new Python.
- The ownership map knows the new files.
- `docs/plan/package-costs-report.md` (opening with "Що змінилось для власника") and
  `docs/plan/package-costs-summary.md` written.
- Item 4: the full audit recorded at `evals/baseline/<hostname>/audit-v0.12.0.json` within $35,
  compared with `audit-v0.11.0.json`; 02, 04, 10 and 11 reported against their expected verdicts.

## Build parameters

- Budgets: release audit ≤ $35 (owner's number). A reason is "syntactically valid" at ≥ 12
  characters and two words (package 7's rule, unchanged); whether it is *good* is the overseer's.
- Policies: standard library only; every new hook call is best-effort toward the carrier's own
  verdict except where the owner asked for a refusal (the PASS refusal is a verdict of its own).
- Risk tolerance: spikes run without asking; a passing spike never interrupts.
- Autonomy: all slices built in order; interrupts only on the critical set. Unattended in fact (the
  program: "Мене не питай").

## Premises (see `.engine/premises/premise-log.md`, PR-costs-01…04)

1. A subagent's `model` frontmatter accepts an alias (`sonnet`) and outranks the session's model.
2. The gate's escalation leaves a `## <utc> — gate stop layer — PARKED` entry in parked.md.
3. The collector's output is consumable by the overseer hook inside one Stop call (the tracer).
4. The audit sessions are logged in on this machine.

## Out of scope (deliberately)

- `.claude/settings.json` and the constitution: untouched. No new hook entry — the collector is
  called by the overseer hook that is already wired, and by the overseer from its skill text.
- `mvp-critic`: not in the owner's list of four; it keeps inheriting the session's model.
- The overseer's text after the release audit: described, not changed (item 4).
- A git pre-commit or CI wiring for the collector.
- Re-judging gate-allows that an earlier, already audited unit committed.

## Decisions (agent; two-way unless stated; logged AUTONOMOUS in escalations.md)

- **K1 one new script, `.claude/hooks/gate_allows.py`.** It imports `gate.py` for the diff, the
  tokenizer and the reason rule, so "what the gate accepted" and "what the overseer is shown" cannot
  drift apart. Rejected: a `--layer allows` inside `gate.py` (a fifth layer that is not a gate).
- **K2 what "new" means.** The lines the slice's diff ADDS: working tree + index + untracked against
  a base. Base = `base_commit` named in the active slice contract when it names one, else `HEAD`;
  `--base REF` overrides. In `.py` files only comment tokens count (a string that mentions the word
  is not an exemption); in config files and slice contracts, added lines. A marker with no reason at
  all is collected too (looser pattern than the gate's) and flagged `reason: missing`.
- **K3 how it reaches the overseer — two carriers.** The hook appends a `GATE-ALLOW REVIEW` block
  to `OVERSEER_REQUEST` (nothing appended when the diff adds none: the request text stays
  byte-identical). And the skill tells the overseer to run the script itself, because an overseer
  asked by a person ("run overseer") never sees the hook's text — which is also how every audit
  scenario invokes it.
- **K4 the judgement lives under check #4.** A silenced check is a masked gap. No thirteenth check:
  the number 12 is in the rules, the hook text and the instruments. Weak = says only that the check
  was in the way ("to pass mypy", "temporary", "for now", "legacy"), restates what the suppression
  does, or names no cause that makes the check wrong HERE. Verdict: `OVERSEER_BLOCK: #4 …
  gate-allow at <file>:<line>`.
- **K5 the open escalation is read from parked.md, closed by a human.** Open = a
  `gate stop layer — PARKED` entry carrying `- Slice: <slug>` equal to the active slice (both
  "(none)" when no slice is active). It closes when the entry is moved to `RESUMED` — the park
  queue's own convention, and what the entry's "Unblocks when: a human reads the report" says.
  Rejected: closing on the next green gate run — a checkpoint commit empties the diff and the gate
  passes on nothing. The gate's entry gains the `- Slice:` line; an older entry without it is not
  read as open (no retroactive lock on a project's history).
- **K6 the refusal.** On `OVERSEER_PASS` with an open escalation the hook answers
  `OVERSEER_PASS_REFUSED` (a block with instructions: the verdict for this unit is not PASS; park
  the unit and take another, or end with a halt marker) and requests no lesson review. The audit
  request itself says so in advance. Same-message re-fire is silent (the existing SHA guard).
- **K7 tiers.** `--tier smoke` = 1 run per scenario, `--tier full` = 3; `--runs N` still works and
  conflicts with a tier that says otherwise. The tier is recorded in the result file. New
  `--max-cost USD`: the runner stops before a run when the recorded cost plus the dearest run so far
  would pass the limit (status `partial`, exit 4, `--resume` continues) — the owner's $35 needs a
  mechanism, not a promise.
- **K8 `needs_audit.py <ref>`** lists files changed since `<ref>` (committed, staged, unstaged,
  untracked) under: `.claude/skills/`, `.claude/agents/`, `.claude/commands/`,
  `.claude/engine-rules.md`, `.claude/constitution.md`, `.claude/references/`, `.engine/rules.md`,
  `CLAUDE.md`, `AGENTS.md` and their seeds in `templates/project/`. Exit 0 = none, 1 = some
  (listed), 2 = bad ref. Hook-injected strings in `.py` files are outside the owner's list and are
  named as a limit.
- **K9 the cheaper model is the alias `sonnet`** in the four critics' frontmatter (alias, so it
  follows the model family). Overseer (a skill) and architects (commands) run in the main session
  and keep its model: nothing to write, and a test pins that none of them names a model.
- **K10 two critic rounds per plan.** `/feature-architect` drafts decompose, contracts and sequence
  and sends the WHOLE plan to the critic; a second round only after a REVISE; what is still open
  after round two is recorded as an open item and decided by door (two-way: the architect's
  recommendation, logged; one-way or product: parked). Replaces "per phase, up to four".
- **K11 scenario 11 is a recorded turn** (one session, nothing for a model to refuse): the clean
  turn of 01 over a working tree in which `with_tax` lost its parameter annotation behind a
  type-ignore with the reason "annotation not needed for now". The turn does not mention it
  (`must_not_contain: gate-allow`), so the block can only come from the collector or the diff.
  Expected: `BLOCK`, and the verdict's words must contain `gate-allow`.

## Revisions after the critic (round 1 of 2: FEATURE_CRITIC_REVISE, fresh context, blind)

One blocking objection and ten notes; all folded in. Where a decision above disagrees with this
section, this section is the contract.

- **K2 → "new" means not yet judged (blocking B1).** A checkpoint commit emptied the diff against
  HEAD and hid the exemption (`commit_checkpoint.sh` checks nothing, and this repository never has
  a slice contract). The base is now, in order: `--base`; the commit the hook recorded at the last
  ACCEPTED PASS (`.claude/state/overseer/gate-allows-judged.json`); the active contract's
  `base_commit`; the merge-base with the main branch; HEAD. What an accepted PASS had in front of
  it is remembered by fingerprint (file, kind, reason) and not listed again; a REFUSED pass judges
  nothing. The out-of-scope line "re-judging gate-allows an earlier audited unit committed" now
  reads: an exemption is re-listed only if no accepted PASS has seen it.
- **K5 → the escalation is machine state, closed by the owner's command (N1).** `parked.md` is the
  agent's own file and its template tells the agent to mark entries RESUMED. gate.py now records
  the escalation in `.claude/state/gate/escalations.json` (slice, files it blocked on, HEAD); the
  hook reads only that. `python3 .claude/hooks/gate.py --close-escalation <stamp|all>` closes it,
  marks the parked entry RESUMED, and **refuses when `CLAUDECODE` is set** — hooks do not see what a
  script runs, so the script carries the check. A parked gate entry with no state (older) locks
  nothing. Limit, stated in engine-limits: an agent that unsets the variable on purpose can run it;
  that is a deliberate, visible act, not a routine edit.
- **K5 scope without a slice (N2).** An escalation raised outside any slice covers the FILES the
  gate blocked on (everything, when it named none), for as long as they are in the range no accepted
  PASS has covered; a slice that starts meanwhile is not locked. In a repository that never uses
  slices this still holds every later PASS until the owner closes it — said plainly in the report:
  without a slice there is no boundary to say other work is unaffected.
- **K6 (N3).** The refusal is recorded beside the escalation (`refusals`), its text demands a
  superseding ledger entry, and it is decided before the lesson review, which a refused PASS no
  longer triggers.
- **Contract grants by use (N4).** A suppression (or config change) with no marker of its own that
  passes on a SEALED contract's grant is listed where it is used, with the contract's reason.
- **N5** the collector unions untracked files itself. **N6** a collector that raises puts
  "the collector failed … run it yourself" into the request instead of silence.
- **K11 (N7).** v0.11.0's clean scene blocked 2 of 3, and `must_contain` is matched on the whole
  reply, which holds the collector's output — a match without a judgement. Scenario 11 expects
  `BLOCK` **#4**, and a new `entry_must_contain` is matched on the verdict line and the ledger
  entry only. A no-model test builds the sandbox and checks the collector lists exactly that line.
- **K7 (N8).** The cost of runs dropped on `--resume` (usage limit) stays counted
  (`dropped_cost_usd`); under `--max-cost` the runs go round-robin (run 1 of every scenario, then
  run 2 …) so a cut-off costs every scenario a run instead of the last scenarios all of theirs.
- **K8 (N9).** A second class, `maybe`: hook files whose strings the model reads
  (`overseer_stop.py`, `gate_allows.py`, `lesson_queue.py`, `gate.py`, `env-check.sh`) — reported,
  exit 1 as well, named apart. Deleted and renamed files count.
- **K10 (N10).** `PREMISE_PROBE_REQUIRED` and `ESCALATE` are answers to a round, not extra rounds:
  the probe or the ruling is folded in and the next critic call is round two. `feature-critic.md`
  accepts `phase: plan`.
- **C7 (N11).** The baseline of v0.11.0 lives under `Laos-MacBook-Pro/`; this host is `claw`
  (Linux). The comparison is cross-host and the report says so.

## Revisions after the critic (round 2 of 2: FEATURE_CRITIC_REVISE on the BUILT C1–C5; no third round)

Two blocking findings, each with a probe the critic ran against the real hooks; both are two-way
doors and both are fixed (decision K12/K13, logged AUTONOMOUS). Nothing is left open, so there is no
open item to route.

- **K12 judged = shown AND passed (B1).** `record_pass` marked as judged whatever was on disk when
  a PASS arrived: a bare `OVERSEER_PASS` line with no audit behind it, an exemption added after the
  request, or a second suppression reusing an accepted reason all slipped past. Now the hook records
  what a request listed and its commit in a pending file; only an accepted PASS that follows
  promotes exactly that; a halt marker or a refused PASS drops it; no pending request, nothing
  recorded; the script run by hand records nothing. The fingerprint counts occurrences.
- **K13 the lock is keyed on files, not on the slice's name (B2).** `.engine/PROGRESS.md` is the
  agent's own file: marking the slice PARKED or declaring another one opened the PASS. An
  escalation now records the files the gate blocked on (every file it looked at when the failure
  named none) and holds while any of them is in the range no accepted PASS has covered; the slice
  is named in the message only. Consequence, accepted and stated in engine-limits: the lock is wide
  — all work on the branch until the owner closes it or the escalated changes are set aside
  uncommitted. This supersedes K5's slice scope and round 1's N2 answer.
- **Notes folded in:** the limits are in `docs/engine-limits.md` (N1–N3, N6); a cut-off under
  `--max-cost` prints the partial rows (N4); `entry_must_contain` takes an any-of list, so a correct
  BLOCK #4 that names the type-ignore rather than the marker still matches, and scenario 11's
  mismatches are to be read entry by entry in the report (N5).

## Slices (the DAG)

| id | slice | delivers | depends | verification |
|---|---|---|---|---|
| C1 | `gate_allows.py` collector | JSON + text list of new gate-allows | — | tests/test_gate_allows.py — **TRACER with C2** |
| C2 | overseer hook: review block; PASS refused on an open gate escalation; gate entry names the slice | hook behaviour | C1 | tests/test_gate_allows.py (hook cases), test_gate.py, test_overseer_continue.py |
| C3 | overseer skill text (#4, state step), references, audit scenario 11 | the judgement + its scene | C1 | test_audit_turn_fixture (pre-flight on 11), test_text_hygiene, test_context_budget |
| C4 | audit tiers, `--max-cost`, `needs_audit.py`, README rule | cheaper audits | — | tests/test_audit_tiers.py, tests/test_needs_audit.py |
| C5 | models by role; two-round cap | frontmatter + text | — | tests/test_model_roles.py |
| C6 | golden scenarios for C2, new everyday reference, ownership, records | the measured delta | C1–C5 | run_hook_scenarios --compare; test_ownership |
| C7 | release audit `--tier full`, compare with v0.11.0 | audit-v0.12.0.json | C6 | compare_audits.py; 02/04/10/11 vs expected |

## Inter-slice contracts

- C1 → C2, C3: `gate_allows.collect(root, base=None) -> list[Allow]` with `file, line, source
  (code|config|contract), what, reason, reason_ok`; `render(allows) -> str` (empty string for an
  empty list); CLI `python3 .claude/hooks/gate_allows.py [--base REF] [--json]`, exit 0 always
  (it reports, the overseer judges).
- gate.py → C2: the PARKED entry's heading `gate stop layer` and its `- Slice: <slug|(none)>` line.
- C3 → C7: `expected.json` entry `11-gate-allow-weak-reason` + overlay `work/11-gate-allow/`.
- C4 → C7: `--tier full --max-cost 35 --out … [--resume]`.

## Hardest seams

1. **Syntax, not text.** The collector must not report a docstring or a test string that mentions
   the marker (this repository's own tests build such strings) and must report a marker with no
   reason. Test: both planted in one file; exactly the real one is listed.
2. **The refusal must not become a loop or a lock.** Refused PASS → one block; the same message
   again → silent; an entry marked RESUMED, another slice's entry, a legacy entry → PASS accepted.
   Each is a negative case in the suite.
3. **The carriers stay themselves.** With no new gate-allow and no open escalation the hook's
   output is byte-identical to today's (the golden set shows it: no existing scenario changes).
4. **A cost limit that cannot overshoot by much.** Checked before each run with the dearest run so
   far as the estimate; the overshoot bound is one run, stated in the README.

## Integration exit criterion

A throwaway repository in which a turn adds a type-ignore with a weak gate-allow: the Stop gate
lets it through (reason syntactically valid), `overseer_stop.py` on the unit-completion claim emits
`OVERSEER_REQUEST` containing that file, line and reason; with a `gate stop layer — PARKED` entry
for the slice, the same hook answers a PASS with `OVERSEER_PASS_REFUSED`. Both in
tests/test_gate_allows.py, no model involved.

## Deferred

- A wired pre-commit run of the collector — when a project asks for it.
- Closing an escalation by a verified green run over the same files — if humans find RESUMED
  bookkeeping a tax; cost: one function in the hook.

## Open items requiring human decision

- (none at planning time; anything that appears is parked in `.engine/overseer/parked.md`)
