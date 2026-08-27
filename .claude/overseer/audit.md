# Overseer self-improvement audit log

Proposals from the overseer for changes to its own SKILL.md. The overseer
NEVER modifies SKILL.md directly — proposals here await human ratification
(propose → gate → ratify → replay).

This file is the V2 path. In V1, the overseer just appends proposals; the
human reads them and edits SKILL.md manually when ratified.

## Proposal format

```
## <ISO timestamp UTC> — <proposed change>
- Evidence: <ledger entries supporting this — minimum 3 cited>
- Rationale: <why this would improve the overseer>
- Risk: <how this could go wrong>
- Status: PROPOSED | RATIFIED | REJECTED
```

## When to propose

- A pattern fired 5+ times across 3+ slices and is not in the current
  12-check checklist → propose adding it.
- A current check fires often but is reversed by the human in
  escalations.md → propose tuning or removal.
- A class of escalation is consistently waved through → propose
  autonomous handling.

## What NOT to propose

- Removing any check just because it triggers BLOCKs frequently. Frequent
  BLOCKs are the point. Anti-Goodhart.
- Adding checks that mimic existing tooling (linters, type checks).
- Lowering the citation-or-prune threshold.

---

## 2026-08-27T17:20:00Z — RATIFIED — Unattended-operation cadence: park-and-continue replaces stop-and-wait

- **Status: RATIFIED** by the owner's message of 2026-08-27 ("Fix the stop
  conditions for unattended operation"), which states verbatim: *"This message is
  the human ratification for the whole scope below."* Article 7 order followed:
  logged here before any edit was made.
- **Ratified scope** — `.claude/skills/slice-builder/SKILL.md`,
  `.claude/skills/overseer/SKILL.md`, `CLAUDE.md`,
  `.claude/commands/plan-slice.md`, `.claude/commands/feature-architect.md`, and
  a new `.claude/overseer/parked.md`. Owner reviews every diff before the rules
  take effect.
- **Explicitly excluded from the grant** — `.claude/constitution.md` (Article 7,
  human-only; a wording proposal is filed separately below), every
  `permissions.deny` and `permissions.ask` entry, the `git commit` block,
  `block-dangerous.sh`, `protect-paths.sh`, the 3-attempt loop guard, and
  RED-before-GREEN as a discipline.
- **The principle installed** — stop only for (1) something only a human can
  supply, (2) a falsified premise that invalidates committed work, (3) nothing
  left in the queue that can move. Everything else is decided, logged, continued.
- **Evidence** — the stop-cause diagnosis produced this session against
  `.claude/settings.json`, the six hooks, `CLAUDE.md`, `AGENTS.md`, and the five
  active skills; 17 turn boundaries were traced to `slice-builder/SKILL.md`
  alone (lines 12, 47, 91-97, 107, 119, 134, 139, 140, 141, 143, 145, 155, 171,
  234-239), none of which map to any of the three legitimate reasons.
- **Interpretation applied where the grant was internally in tension.** FIX 3
  says an escalation is logged and acted on via your own recommendation; FIX 4
  says *"a genuine one-way door (money, real external system, irreversible data)
  still parks and waits."* Implemented as FIX 4's rule governing FIX 3's
  mechanism: never block on an interactive prompt; **decide** two-way doors and
  log them provisionally; **park** one-way doors. This is what keeps Article 5
  intact, which the same message ordered preserved.
- **Risk accepted, named here so it is reviewable** — the audit becomes
  self-adjudicating for two-way doors. The 12 checks, their evidence
  requirements, and the mandatory ledger write are unchanged; only verdict
  *routing* changes. The compensating control is that
  `.claude/overseer/parked.md` and `escalations.md` become a review queue, and a
  queue nobody reads is the failure mode. Surface threshold set at **3 parked
  ratification items, or any single one-way door** — see the skill edits.

## 2026-08-27T17:20:00Z — PROPOSED (constitution — HUMAN MUST APPLY, do not let an agent edit this file)

- **Target:** `.claude/constitution.md`, Article 5. Filed as a proposal, not an
  edit, because Article 7 makes the constitution human-only and the owner's
  ratifying message explicitly exempted it: *"This is the one file in this whole
  task you must not touch."*
- **Rationale:** Article 5 is correct and stays. It is currently silent on what
  ratification means when no human is in the loop, and that silence is what makes
  every hard gate default to a blocking wait.
- **Proposed wording — append to Article 5, after the door test:**

  > **Unattended reading.** When no human is in the loop, a *one-way door* parks:
  > the item stops, work continues elsewhere, and the door is surfaced at the next
  > legitimate interruption. It is never decided autonomously. A *two-way door*
  > that a gate was merely being careful about is decided, logged as provisional
  > with its cost-to-reverse, and reviewed when a human returns. Absence of a
  > human is never grounds to walk through a one-way door.

- **Risk:** the one-way/two-way classification becomes load-bearing and is made
  by the same agent that benefits from classifying generously. Mitigation is the
  provisional log — every autonomous call is recorded with cost-to-reverse, so a
  wrong classification is visible on review rather than silent.
- **Status: PROPOSED — awaiting human application.**

## 2026-08-27T17:17:56Z — Anchor verdict-marker detection so a mention cannot trigger the continue loop

- **Target:** `.claude/hooks/overseer_stop.py`, not `SKILL.md`. This file's header
  scopes proposals to SKILL.md; the defect is in the hook that invokes it. Flagging
  the scope stretch rather than filing it silently.
- Evidence:
  - `.claude/hooks/overseer_stop.py:75` — `PASS_MARKER_RE = re.compile(r"OVERSEER_PASS\b")`.
  - `.claude/hooks/overseer_stop.py:425` — `if PASS_MARKER_RE.search(message):` matches
    the raw message with no line anchor and no code-span exclusion.
  - `.claude/overseer/.last_continue_sha`, written 2026-08-27 18:52 local. The CONTINUE
    branch fired on a session turn that only *described* the protocol in prose: no slice
    contract exists (`.claude/overseer/slice/` is absent), no code was edited, and no
    unit sentinel was emitted.
  - Ledger citations: none available — `.claude/overseer/ledger.md` holds no entries.
    This rests on a first-party in-session trace, not on the 3-entry pattern threshold
    in "When to propose". Recorded as a defect report, not a pattern claim.
- Rationale: `UNIT_DONE_RE` (line 68) already requires its sentinel *alone on its own
  line*, precisely so that a mention cannot fire the audit. The four verdict markers
  have no equivalent anchoring, so the two branches disagree about what counts as
  emitting a marker versus quoting one. Any turn that documents, reviews, or teaches
  the protocol enters the autonomous loop — and this repo is the protocol's own
  template, so those turns are routine here, not exotic. The failure is silent: it
  consumes the `.last_continue_sha` slot and injects a continue instruction against a
  slice that does not exist.
- Options (pick one at ratification):
  - (a) Anchor all verdict markers to line-start under `re.MULTILINE`, matching
    `UNIT_DONE_RE`'s existing discipline. Cheapest, and makes the hook enforce what
    SKILL.md's "Verdict format" section already requires.
  - (b) Strip fenced and inline code spans from `message` before matching. Also handles
    prose that legitimately begins a line with a marker name, but adds a parser to a
    hook that currently has none.
- Risk: (a) would stop honouring a real verdict that is indented or emitted mid-line;
  SKILL.md already forbids that shape, but a lenient turn that used to halt correctly
  would now pass through. (b) could strip a genuine marker an agent formatted as code.
  Both errors run toward *fewer* injections rather than missed halts, since
  `HALT_MARKER_RE` is evaluated first (line 421) and would take the same anchoring.
- **Status: RATIFIED and APPLIED 2026-08-27.** Ratified by the owner's blanket
  grant ("anything else you find that stops 24/7 operation, fix it under the same
  pre-ratification. Log it, don't ask"). Option (a) taken — all three marker
  regexes now anchor with `^[ \t]*` under `re.MULTILINE`, matching
  `UNIT_DONE_RE`'s existing discipline. Option (b) rejected: a code-span parser
  is more machinery than the residual justifies.
- **Residual, accepted and documented:** a marker at line-start *inside a fenced
  code block* still fires. Option (b) would close it. Left open because the
  realistic failure — discussing markers in prose, tables, and inline code — is
  now covered, and a session that puts a bare marker at column 0 of a fenced
  block is indistinguishable from one emitting it for real.
- Verified: 10/10 regression cases green, including the four prose shapes that
  previously fired (backticked mention, CLAUDE.md bullet, markdown table row,
  mid-sentence). `--dry-run` still emits a block, so the wiring is intact.
