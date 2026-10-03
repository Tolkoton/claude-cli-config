---
name: self-learning-orchestrator
description: Orchestrates the self-learning loop across a Claude Code dev cycle — knows WHEN to read, update, or distill the project's living memory (CLAUDE.md, decisions.md, MEMORY.md files, claude-progress.md, reflections.md) and dispatches to the right sub-skill at each moment. Use this skill at session start (read prior learning), when a substantive decision is being made, when stuck for more than ~20 minutes, before any commit, at session/task end (distill lessons), and on periodic maintenance days. Also use whenever the user mentions "session start", "session end", "wrap up", "done for now", "/clear", "/bye", "stuck", "tried everything", "we picked", "going with", "trade-off", "ready to commit", "review my changes", "wrap up the task", "memory maintenance", "review CLAUDE.md", "this took forever to debug", "remember this for next time", "lesson learned", or whenever you notice a workflow moment (just opened a new session, just fixed a non-obvious bug, just completed a task) where memory should be consulted or updated. Proactively detect these moments even if the user has not explicitly asked.
---

# Self-Learning Orchestrator

Orchestrate the project's living memory across the development lifecycle. This skill is the *trigger dispatcher*: it recognizes WHICH self-learning moment is happening and routes to the right protocol. It does not duplicate the content of the per-artifact skills — it speaks their cue phrases so they activate.

## What this skill manages

A layered memory stack with deliberately different update frequencies:

| Artifact | Scope | Lifetime | Update cadence |
|---|---|---|---|
| `CLAUDE.md` | project | forever | rare, deliberate |
| `decisions.md` | project | append-only forever | per substantive decision (~weekly) |
| `.engine/architecture/MEMORY.md` | project | append-only, periodic prune | per session-end |
| `~/.claude/memory/<tech>/MEMORY.md` | global per-tech | append-only forever, periodic consolidate | per session-end |
| `claude-progress.md` | task | deleted on completion | per commit |
| `<task>/reflections.md` | task | archived on completion | per failed attempt |

Mismatching the cadence is the most common failure mode. CLAUDE.md is not a place to log every bug; MEMORY.md is not a place to record every commit. The triggers below map each moment to the correct artifact.

## The trigger state machine

```
                            ┌────────────────────────────────┐
                            │ Session start (every session)  │
                            │   → triggers/session-start.md  │
                            └────────────────────────────────┘
                                          │
                                          ▼
                            ┌────────────────────────────────┐
       ┌────── new task ───►│ Task start                     │
       │                    │   → cue plan-mode skill        │
       │                    │   → maybe create progress.md   │
       │                    └────────────────────────────────┘
       │                                  │
       │                                  ▼
       │      ┌────────────────────────────────────────────────────────┐
       │      │ Execution loop                                          │
       │      │                                                         │
       │      │  edits ──► hooks (ruff, mypy, pytest)                  │
       │      │      │                                                  │
       │      │      ├─ substantive decision?                          │
       │      │      │    → triggers/decision-checkpoint.md            │
       │      │      │                                                  │
       │      │      ├─ stuck >20 min?                                  │
       │      │      │    → triggers/stuck-protocol.md                 │
       │      │      │                                                  │
       │      │      ├─ bug fix >15 min?                                │
       │      │      │    → lesson queue (lightweight capture)        │
       │      │      │                                                  │
       │      │      └─ ready to commit?                                │
       │      │           → triggers/pre-commit-checkpoint.md          │
       │      │                                                         │
       │      └────────────────────────────────────────────────────────┘
       │                                  │
       │                                  ▼
       │                    ┌────────────────────────────────┐
       └────── more ────────┤ Task done?                     │
              tasks         │   no → next task               │
                            │   yes → session-end-dreaming    │
                            │     → triggers/session-end.md   │
                            └────────────────────────────────┘

       ────────────────── independent cadence ──────────────────
                            ┌────────────────────────────────┐
                            │ Periodic (weekly/monthly)      │
                            │   → triggers/periodic.md       │
                            └────────────────────────────────┘
```

## How to dispatch (the only rule)

When invoked, identify which moment is happening and read the matching trigger file:

| If the moment is... | Read |
|---|---|
| New session starting / first message after `/clear` | `triggers/session-start.md` |
| About to make a real choice with alternatives | `triggers/decision-checkpoint.md` |
| Tried ≥3 approaches without progress | `triggers/stuck-protocol.md` |
| About to commit / "done with this" | `triggers/pre-commit-checkpoint.md` |
| User said "/clear", "/bye", "wrap up", or task is complete | `triggers/session-end-dreaming.md` |
| User asked for memory maintenance or a periodic review | `triggers/periodic-maintenance.md` |
| User said "lesson learned: ..." or "remember this for next time" | `lesson_queue.py add`, see "Lesson capture" below |

Read **only the trigger file that applies**. Do not preload everything — each trigger has independent context needs.

## Lesson capture (lightweight, inline) — the queue is filled by hooks too

`.engine/lesson-queue.md` is one line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`
(source: gate, overseer, parked, escalation, agent). **Hooks fill it without you**: a Stop block of the
gate, an `OVERSEER_BLOCK` verdict, a parked item and an escalation are added automatically, once each
(`.claude/hooks/lesson_queue.py`). You add a line yourself only when you found a **non-obvious cause** —
something a fresh session would not guess from the code:

```bash
python3 .claude/hooks/lesson_queue.py add --source agent --slice <slice> "<what was non-obvious and what is actually true>"
```

Do not queue what the code, the tests or git history already say, and do not stop to write an ADR.

**Triage is the hook's request, not yours to schedule.** After an overseer verdict of PASS the hook appends
`LESSON_REVIEW_REQUESTED` to the continue text when the queue is not empty. For each candidate run
`python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`:
`memory` needs `--text` and two `--cite` ledger entries (the memory file's citation-or-prune rule);
`rule` needs `--text` and `--why` and writes a **proposal** to `.engine/rule-proposals.md`; `engine` writes
`.engine/engine-feedback.md`; `discard` just removes it. A resolved candidate leaves the queue.

**Stuck.** Three identical failures in a row make a hook hand you the stuck protocol
(`triggers/stuck-protocol.md`) as additional context; a success resets the count. Follow it; it never blocks.

**Session start.** A short digest (latest memory headings, queue size, proposals waiting) arrives as
session context; when it says MEMORY CLEAN-UP DUE, run `triggers/periodic-maintenance.md`, then
`python3 .claude/hooks/lesson_queue.py cleanup-done`.

**Nothing reaches the persistent context by itself.** A rule proposal becomes a rule only after the overseer
passes it (a ledger entry naming `rule-proposal <id>` with OVERSEER_PASS) and `lesson_queue.py promote <id>`
appends it to `.engine/rules.md`, which CLAUDE.md imports under a 200-line budget. Never edit CLAUDE.md for a lesson.

## Delegation map (cue phrases that activate other skills)

This skill stays thin by speaking phrases the per-artifact skills already match:

| Concern | Cue phrase (Claude speaks aloud in reasoning) | Skill that activates |
|---|---|---|
| Plan the task | "let me use plan-mode decomposition for this" | `plan-mode-and-task-decomposition` |
| Resume a task | "let me check claude-progress.md for resume context" | `progress-file-for-long-tasks` |
| Record a decision | "this is an ADR-worthy decision; let me apply the ADR-lite format" | `decisions-log-adr-lite` |
| Self-review before commit | "let me run the pre-commit self-review checklist" | `pre-commit-self-review-checklist` |
| Debug a stuck failure | "let me apply execution-feedback-debugging discipline here" | `execution-feedback-debugging` |
| End-of-task lesson distillation | "let me do session-dreaming for this task" | `session-dreaming` (from master-architect bundle) OR fall back to `triggers/session-end-dreaming.md` |
| Navigate before editing unfamiliar code | "let me apply codebase-navigation-strategy first" | `codebase-navigation-strategy` |

If a delegated skill is not installed, the trigger file in `triggers/` contains the fallback inline protocol — orchestrator never silently fails.

## Hard rules

1. **Always read CLAUDE.md and the relevant MEMORY.md files at session start.** Skipping this is the single largest learning leak — every subsequent decision is uninformed by prior lessons.
2. **Never write to CLAUDE.md, decisions.md, or MEMORY.md silently.** Attended: show the user what you propose to add and where, and get explicit confirmation. Unattended, or in answer to the hook's `LESSON_REVIEW_REQUESTED`: that request is the confirmation for `.engine/overseer/MEMORY.md` (through `resolve --to memory`, which refuses without two ledger citations) and for the two proposal files; **CLAUDE.md and `.engine/rules.md` are never written by hand or by a hook — only `promote` writes the latter, after an overseer PASS.** Memory pollution is irreversible without git archaeology.
3. **One artifact per piece of knowledge.** A specific fact lives in exactly one of: CLAUDE.md (rule), decisions.md (rationale), MEMORY.md (experience), reflections.md (per-task), code comment (per-line). Duplication causes drift. See `references/artifact-scope-decision-tree.md`.
4. **Defer non-blocking captures to the queue.** Bug fix in flow with a non-obvious cause? `lesson_queue.py add`, do not stop to write a full ADR. The queue is triaged when the hook asks (after an overseer PASS) and at session-end.
5. **Session-end is non-optional.** Skipping session-end-dreaming silently drops all lesson candidates accumulated during the session. If a session is ending and the queue is non-empty, process it before `/clear`.
6. **Periodic maintenance is non-optional.** Without prune, MEMORY.md and CLAUDE.md rot to the point of being ignored. Schedule weekly or monthly, treat as real work.
7. **Promotion path is one-way and rare.** A pattern in MEMORY.md may *eventually* be promoted to a Skill, but only after appearing in 3+ projects. Inverse demotion (skill → memory) never happens.

## What this skill does NOT do

- It does NOT replace `master-architect` for architectural design. Master-architect handles Phase 1–4 architectural work and writes its own `.engine/architecture/` artifacts. Self-learning-orchestrator coordinates the *cross-cutting* memory lifecycle around it.
- It does NOT replace `slice-builder` for implementation. Self-learning-orchestrator handles the memory lifecycle around implementation — ad-hoc bug fixes, refactors, exploration sessions — not the slice itself.
- It does NOT write code. It coordinates the memory layer that informs all code work.

## When to skip this skill entirely

- Throwaway scripts in `/tmp/`.
- Single-line typo fixes that need no context.
- User explicitly says "just do it, no protocol".
- Interactive REPL sessions with no commit at the end.

For everything else — every real coding session — run at minimum the session-start trigger.

## References

- `references/artifact-scope-decision-tree.md` — which artifact a given fact belongs in
- `references/lesson-classification.md` — tech vs project vs both vs discard (used in session-end-dreaming)
- `references/memory-pollution-prevention.md` — limits, anti-patterns, when to prune
- `references/promotion-paths.md` — memory → skill, lesson → ADR, draft → rule
- `checklists/session-end.md` — quick checklist before `/clear` or `/bye`

## Compatibility notes

Designed to compose with the broader project setup:
- the engine's hooks provide PostToolUse / Stop hooks (quality gates) — those are execution feedback, not learning artifacts; this skill is orthogonal.
- `master-architect` and `feature-architect` own architectural artifacts and may keep their own task-scoped `reflections.md`. This orchestrator handles the *between-task* and *across-task* memory; it defers when they're active.
- The 12 research-backed skills (decisions-log-adr-lite, progress-file-for-long-tasks, pre-commit-self-review-checklist, plan-mode-and-task-decomposition, execution-feedback-debugging, etc.) are the delegates this orchestrator triggers via cue phrases.
