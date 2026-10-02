# Feature engine-package-2b — decomposition

Frame source: `docs/plan/package-2b.md` (the owner's text, verbatim and complete — it ends
with the report section). Every numbered item is an owner requirement; the critic checks how
each is met, not whether. Branch `unattended/2026-10-02-package-2b` from `v0.11.0`.
Rules carried over from `docs/plan/package-3c.md`: one slice = one commit, English messages
that say why, every suite + the golden set (`results-package-3c.json`) after each slice,
`uvx ruff check --isolated` + `uvx mypy --strict` on touched Python, times in UTC.

## Goal

The text a session always carries (CLAUDE.md, AGENTS.md and what they import) becomes short
and clean: the engine's standing rules move into one engine-owned file that `engine.py`
ships and updates, a new project starts from small clean seeds instead of this repository's
own files, an existing project's text is never rewritten outside a marked block, four kinds
of stale text are removed, two stable overseer defects are fixed in the text the overseer
reads, and the Stop gate of this repository becomes a fast subset. Measured by an audit
before (v0.11.0) and after (HEAD).

## Acceptance (owner's "done when", verbatim in intent)

- every suite green; golden set identical to the 3c reference except intended differences;
- persistent context ≤ 200 lines (a test counts);
- scenarios 01 and 08 fixed per the audit, no other scenario worse (beyond noise);
- the decana report exact; ruff and mypy --strict clean.

## Out of scope (deliberately)

- Any edit to `.claude/settings.json` (owner-only; none is needed by this package).
- Rewriting a project's own text in CLAUDE.md/AGENTS.md: the engine reports, the owner edits.
- Reworking the overseer's checks beyond the two named defects.
- The vendored self-learning skill's mechanisms (lesson queue, memory files) — only the
  four phantom slash commands are removed from its trigger text.

## Decisions (agent, each logged AUTONOMOUS in escalations.md)

- **D1 rules file name and place:** `.claude/engine-rules.md`, owned by the `engine .claude/**`
  rule, so `engine.py update` replaces it while the project has not edited it. Not
  `.claude/CLAUDE.md` and not `.claude/rules/` — both are paths Claude Code may load on
  its own, and the owner wants exactly one path in: the `@` import.
- **D2 budget shape:** `.claude/engine-rules.md` ≤ 100 lines, this repository's CLAUDE.md
  ≤ 20, AGENTS.md ≤ 80; the seeds smaller still. The test resolves `@` imports recursively
  (own-line `@path` tokens), fails on an unresolved import, and asserts ≤ 200 for (a) this
  repository and (b) a project seeded from `templates/project/`.
- **D3 what moves to references:** `.claude/references/hooks.md` (the hook table, input
  parsing with jq/python3, inspect/disable, the script hole, the recursion guards and the
  kill switch) and `.claude/references/unattended.md` (mode file semantics, the session
  contract, the park-instead-of-ask rule in full, the supervisor's status table). The rules
  file keeps one line per topic that says when to open which reference.
- **D4 the marked block:** `<!-- >>> engine: ... -->` / `<!-- <<< engine -->` around the
  single import line in the seed CLAUDE.md, mirroring the `.gitignore` block. `engine.py`
  may rewrite ONLY the text between those markers (and only when the ref's block differs);
  project text outside is byte-identical after every update — that is the invariant item 4
  states, and a test asserts it.
- **D5 the report for a changed copy:** a `note` line per file: the import line to add, and
  every run of ≥ 3 consecutive non-blank lines that appear, after trailing-whitespace
  normalisation, in some version of the engine's own CLAUDE.md (or of the seed) — reported as `lines a–b (<first heading in the
  run>)`. The engine never edits those lines.
- **D6 pristine detection widened:** a project file equal to ANY historical blob of its seed
  path counts as pristine too (today only the target path's history counts), so a project
  seeded from `templates/project/CLAUDE.md` is still recognised after the seed changes.
- **D7 the jq paragraph:** no paragraph names macOS; the paragraph that is false everywhere
  is the unattended README's "REQUIRED: four hooks silently enforce nothing without it"
  (false since the python3 fallback, 2026-09). Every jq paragraph the model reads is
  rewritten OS-neutrally and against the current hooks: jq or python3, refuse with neither.
- **D8 overseer fixes (item 6), causes re-derived from `audit-v0.11.0-run1-broken-instrument.json`
  and `audit-pre-3c.json`:** 01 — the overseer treats output that did not arrive as a tool
  result in the session as non-existent ("the RED/GREEN/smoke output in the completion claim
  came from no command run in this session", BLOCK #1 ×3 at v0.11.0; BLOCK #2 ×3 at
  2788357 on the same ground), and the skill forbids it to run anything ("You do NOT … run
  tests"), so a pasted output can never become evidence and the only move is BLOCK. 08 —
  "What you do NOT do" routes a decision that conflicts with the contract to
  `ESCALATE (SCOPE_AMENDMENT)` ("an ADR authored here would unilaterally override a ratified
  slice decision", ×3), which overrides #8's own verdict. Fix, in SKILL.md: evidence is what
  the repository confirms — the overseer MAY run the named tests, lint and smoke read-only
  and reproduce a RED by withholding nothing (it checks the test would fail without the
  change by reading it, or by a commit order); a quoted RED/GREEN/smoke consistent with the
  repository counts; the transcript's tool-call shape is not evidence either way (a session
  may paste what it captured; a resumed session shows none); #1, #2 and #5 share that rule.
  #8 always returns `OVERSEER_ADR_REQUIRED` with a draft ADR that records the divergence from
  the contract; the ADR routing decides who ratifies; SCOPE_AMENDMENT stays with #11.
- **D10 the instrument (critic round 1, confirmed by a probe):** two defects of package 3c
  broke every audit session at v0.11.0 — (a) the fixture still ships the slice contract at
  `.claude/overseer/slice/ref-tax.md` while a post-3c overseer reads `.engine/slices/`
  (`make_sandbox.sh` copies fixtures after the install, so the migration table never sees
  them); (b) the runner never passed `--settings`, and in a never-trusted sandbox a headless
  session loads no project settings: `uv run pytest` "requires approval", the ledger Edit is
  refused (probe 2026-10-02T16:10Z: plain → 2 denials; `--settings .claude/settings.json` →
  0 denials, 4 passed, ledger appended). Slice P0a fixes both before any measurement; both
  runs of this package use the fixed instrument. The 10 runs already paid ($6.83) are kept
  as `audit-v0.11.0-run1-broken-instrument.json` — the package-3c check item 0 asked for.
- **D11 the P0 fork:** the before-run is restarted in full on the fixed instrument rather than
  continued or sampled: a pair measured on two instruments is not a pair, and the owner's
  "others not worse" needs every scenario. Estimated $0.68/run × 30 ≈ $21 on top of $6.83 —
  inside the $35 cap; a usage-limit break is resumed with `--resume`.
- **D9 fast gate:** `tests/run_all.sh --fast` runs the suites named in `tests/fast-suites.txt`
  (each with its measured time); `TEST_CMD="bash tests/run_all.sh --fast"` in this
  repository's project.env; the full set stays the pre-tag check.

## Slices (the DAG) — one commit each

- **P0a instrument** — `git mv` the fixture to `fixtures/.engine/slices/ref-tax.md`; the runner
  passes `--settings <sandbox>/.claude/settings.json` to both sessions (the fix
  `session-claude.sh` got in 3c); pre-flight builds one sandbox and asserts every path named
  in `PROGRESS.fixture.md` exists in it; `evals/README.md`; the resume test's shim ignores
  the new flag. · depends on: — · **first commit**.
- **P0 audit-before** (item 0) — `run_audit_scenarios.py --engine-ref v0.11.0 --runs 3` →
  `audit-v0.11.0.json` on the fixed instrument; `--resume` on a break; cap $35 for the whole
  item including the stopped run; sessions lost to usage limits listed separately. The
  runner builds sandboxes from the ref, so engine edits in the working tree cannot leak in —
  only `evals/` must stay untouched while it runs. · depends on: P0a.
- **P1 rules-file** (items 1, 2) — `.claude/engine-rules.md` from CLAUDE.md's engine text,
  condensed; `.claude/references/{hooks,unattended}.md`; this repository's CLAUDE.md = the
  marked block + `@AGENTS.md` + a few project lines; AGENTS.md shortened; `tests/test_context_budget.py`.
  **TRACER BULLET — done 16:01Z, before the critic round**: a throwaway repository whose
  CLAUDE.md held only the marked block with `@.claude/engine-rules.md`, `claude -p
  --setting-sources project,local`, answered with the passphrase that exists only in the
  imported file; the negative control without the import answered NONE (PR-2b-01). The
  budget test matches the loader's rule — any `@path` token outside code spans/blocks, not
  only own-line ones — and asserts `.claude/CLAUDE.md` and `.claude/rules/` are absent so
  nothing is loaded twice. · depends on: —.
- **P2 seeds** (item 3) — `templates/project/CLAUDE.md` and `templates/project/AGENTS.md`;
  ownership map seeds point at them; TEMPLATE-SETUP steps 4–5; `make_sandbox.sh` unchanged
  (it installs through engine.py); test: a fresh install gets the templates, not this
  repository's files, and the sandbox's CLAUDE.md imports the rules; the tests build a
  temporary engine repository from the working tree and commit it (engine.py reads refs,
  never the working tree — as `tests/test_engine_install.py` does). Plus one real session
  (cents): a sandbox built by `make_sandbox.sh` from the P2 commit, `--settings`, asked for a
  sentence that exists only in `.claude/engine-rules.md` — the seed → install → import chain
  proven before P7 pays for it. · depends on: P1.
- **P3 existing-projects** (item 4) — engine.py: marked-block maintenance (D4), pristine →
  note / `--reseed-pristine` (D6), changed → the report (D5); `tests/test_claude_md_update.py`:
  a v0.11.0 install updated to HEAD (pristine → reseeded, both files), an edited copy
  (project text outside the block byte-identical, exact line ranges in the note,
  idempotent), a copy with the new block whose block text was changed by the ref — all on a
  temporary engine repository committed from the working tree; decana
  `--dry-run` read-only, its note quoted in the report and checked by hand against the
  file. · depends on: P2.
- **P4 hygiene** (item 5) — the four phantom commands out of every file under `.claude/`,
  `AGENTS.md`, `templates/`, `docs/` (the test greps the whole tree; 9 files of the
  self-learning skill, `AGENTS.md`, `.claude/README.md` today); jq paragraphs (D7); `templates/project/.engine/overseer/{parked,escalations}.md`
  without this repository's dates/nodes; `tests/test_text_hygiene.py`. · depends on: P1.
- **P5a overseer-text-08** (item 6, second defect) — `.claude/skills/overseer/SKILL.md`: #8
  returns `OVERSEER_ADR_REQUIRED` with a draft ADR recording the divergence; the
  "What you do NOT do" bullet no longer routes a contract conflict to SCOPE_AMENDMENT. Cause
  evidenced by six 08 sessions (pre-3c ×3, v0.11.0 ×3: 0 denials, contract readable, ESCALATE
  SCOPE_AMENDMENT each time). · depends on: — (verified by P7).
- **P5b overseer-text-01** (item 6, first defect) — the cause of 01 is re-derived from P0's
  transcripts on the fixed instrument, because every 01 session so far (pre-3c ×3, v0.11.0 ×3)
  records `permission_denials` ≥ 1: the overseer DID try to run the tests and the instrument
  refused — D8's "the skill forbids it" is confounded. If 01 matches on the fixed instrument,
  the record says "01's cause was the instrument (D10), fixed by P0a" and SKILL.md gets no
  evidence relaxation (the #1/#2/#5 wording that 02/04/05 measure stays as it is). If 01 still
  blocks, the fix is derived from what those transcripts say and stays as narrow as that.
  · depends on: P0.
- **P6 fast-gate** (item 8) — D9; `run_all.sh` today treats `$1` as a substring filter, so
  `--fast` becomes a flag and the budget test asserts `--fast` runs ≥ 1 suite; the flag and
  `TEST_CMD` land in one commit; both times measured. · depends on: P1 (AGENTS.md text).
- **P7 audit-after** (item 7) — same line, `--engine-ref HEAD` (the commit of P6 or later),
  `audit-post-2b.json`, cap $35; `evals/compare_audits.py` (standard library): per
  scenario matched/valid before and after (metric: matched fraction over sessions without a
  tooling or usage-limit error), the noise from the two 3c "before" runs, a
  difference real only when larger than that noise; 01 and 08 must match, no scenario
  worse; usage-limit sessions listed separately; output `.engine/overseer/audit-2b-compare.md`.
  · depends on: P0, P1–P6.
- **P8 records** — report `docs/plan/package-2b-report.md`, DAG, ledger, escalations,
  parked, PROGRESS, memory, evals README. · depends on: P7.

## Contracts

- P1 → P2: the seed CLAUDE.md's marked block text is defined once (the seed file); engine.py
  (P3) reads the canonical block from the ref's seed, never from a constant.
- P1 → P3: `.claude/engine-rules.md` is the file the report's import line names; the
  duplicate-text scan compares against `history("CLAUDE.md") ∪ history(seed path)`.
- P0a → P0, P7: both measurements run on the same instrument (fixture at the post-3c path,
  `--settings` passed); the runner records the engine commit of each.
- P5a/P5b → P7: the audit runs against a commit that contains both; P7 records that commit.
- P0 → P7: `compare_audits.py` counts a must-fix scenario as met when it matches ≥ 2/3 after
  AND (the improvement is real OR it already matched ≥ 2/3 before); only then is 01's fix
  possibly "the instrument" and the comparison still passes.
- P6 → Stop gate: `tests/fast-suites.txt` names only existing suites (the budget test checks
  the list resolves).

## Premises

- PR-2b-01 Claude Code loads `@.claude/engine-rules.md` from a project's CLAUDE.md in a
  headless session with `--setting-sources project,local` — the path the audit runner
  uses. Verified by the P1 tracer probe (one real session).
- PR-2b-02 `make_sandbox.sh` installs the engine through `engine.py install --ref`, so the
  sandbox's CLAUDE.md is the seed of the ref, not this repository's file. By code reading.
- PR-2b-04 A headless session in a never-trusted directory loads no project settings unless
  `--settings` names the file; with it, the engine's allow list and hooks apply. Verified by
  the permission probe (D10) and by package 3c's C5.
- PR-2b-03 The noise between the two 3c "before" runs is 0.00 on every scenario where
  both have valid sessions (01, 07, 08); where only one has, noise is undefined and the
  comparison reports it as such.

## Order of events (recorded honestly)

P0a's fixture move, the runner's `--settings` and pre-flight, and `evals/compare_audits.py`
were written in the working tree between critic rounds 1 and 2, before this contract was
sealed, because round 1's finding was an instrument defect that every later step depends on
and the stopped run was burning money. All of it is committed as P0a: the comparison script is part of the instrument.

## Critic

Round 2: REVISE — the 01 cause is confounded by the instrument (every 01 session records
denials of the overseer's own test runs), and a fix that relaxes #1/#2/#5 risks 02/04/05.
Applied: P5 split into P5a (08, now) and P5b (01, after P0, re-derived); compare_audits
counts an already-matching must-fix scenario as met; the tests of P2/P3 build a temporary
engine repository; P2 gains a one-session passphrase check in a built sandbox; D5 normalises
trailing whitespace; the order of events above.

Round 1: REVISE — the P5→P7 premise was falsified by the v0.11.0 transcripts on disk: the
fixture's slice contract sits at the pre-3c path, so no SKILL.md text could make 01/08
match. Applied as P0a and D10; the probe found the second defect (no `--settings`). Notes
applied: tracer against a built sandbox (done as a throwaway repository; the seed path is
covered by P2's install test), mid-line imports in the budget test, `--fast` as a flag with
a ≥ 1-suite assertion, the comparison metric named, the hygiene test greps the tree. The P0
fork is decided in D11.

## Open items requiring the owner (parked, none blocks the package)

- none new; C8b (post-3c audit), S8, S9 stay parked from earlier packages. C9 was applied
  by the owner (commit 8e46a65) and is marked done.
