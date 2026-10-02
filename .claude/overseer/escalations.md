# Overseer escalations log

Records every PRODUCT_DECISION / BLOCKER_CLASSIFICATION / DESIGN_FORK /
ADR_RATIFICATION escalation and the human's resolution. Used in the
2-week audit to tune escalation thresholds.

## Entry format

```
## <ISO timestamp UTC> — <category> — <slice slug>
- Question: <text>
- Options offered: <list>
- Recommendation: <overseer's pick + one-line rationale>
- Human chose: <final decision>
- Latency to decision: <minutes/hours>
- Notes: <if human changed mind, if recommendation was wrong, etc.>
```

## Audit signal interpretation (re-read at the 2-week mark)

- **Human waved through immediately, picked recommendation as-is** → next
  time, this class of question can likely be handled without escalation.
  Propose change in audit.md.
- **Human reversed the recommendation** → overseer is over-confident on
  this class. Tune the check prompt; consider weakening the recommendation
  language.
- **Human deliberated long, chose other** → correct escalation, healthy
  use of human time.

---

## Second entry format — AUTONOMOUS two-way-door decisions

The format above has no slot for a decision the AI made itself: every field
(`Human chose`, `Latency to decision`) presumes a human answered. But CLAUDE.md's
verdict routing says a two-way door is *logged here and continued*, not
escalated. A decision with nowhere to be recorded stays open in working memory
and gets re-raised turn after turn, which is a stop wearing a question mark.
That happened for real on node S3 — decided once, re-surfaced to the owner three
times, never written down. Hence this second shape:

```
## <ISO timestamp UTC> — AUTONOMOUS — <item id>
- Decision: <what was decided, in one line>
- Door: two-way
- Cost to reverse: <concretely, what it would take>
- Why not escalated: <which Article 5 test it passes>
- Evidence: <what made this the right call>
- Falsified by: <the observation that would make this wrong>
- Status: CLOSED
```

**CLOSED means closed.** Once an entry exists here, the decision is not an open
question. Re-raising it with the owner is not diligence — it is an illegitimate
stop, because it asks a human to ratify something Article 5 assigns to the AI.
If new evidence genuinely falsifies it, append a NEW entry that supersedes this
one; do not reopen the old one in conversation.

---

## 2026-08-27T19:45:00Z — AUTONOMOUS — S3
- Decision: reopened DAG node S3 from `done` to `todo`, preserving its previous
  evidence under `prior_evidence` rather than overwriting it.
- Door: two-way
- Cost to reverse: one JSON edit. Nothing was built on the reopening, and the
  original evidence was never destroyed, which is what kept it two-way.
- Why not escalated: not a product decision, not a threshold, not a public
  contract, not irreversible data. Article 5 assigns it to the AI.
- Evidence: the owner's instruction named S3 as "the next ready node", but S3
  was `done`. Its OWN recorded evidence admitted the gap -- `format-on-edit.sh`
  was never actually exercised because `ruff` is absent, so the passing
  observation proved nothing. Reopening made the instruction coherent instead of
  contradicting it. Vindicated: the session then found four real defects there.
- Falsified by: the owner saying they meant a different S3, or that the prior
  evidence was in fact complete.
- Status: CLOSED

## 2026-08-27T20:05:00Z — CAPABILITY_GRANT — harness self-repair
- Question: may a supervisor-spawned session write under `.claude/`, so an
  overnight run can repair the harness instead of only diagnosing it?
- Evidence that forced the question: session S3 found four real hook defects,
  proved them against copies, and could apply none of them -- "every write under
  .claude/ denied by the sensitive-path classifier". It staged a patch and
  parked. The defects were applied by the attended orchestrator, not by the run.
- Options offered: (a) grant nothing, accept diagnose-only overnight runs;
  (b) grant all of `.claude/`; (c) grant three directories, keep the guardrails
  denied, and pair it with a patch gate.
- Recommendation: (c) -- the narrow grant. An agent that may edit its own
  permissions has no permissions.
- Human chose: (c). "так дозволяю", 2026-08-27.
- Latency to decision: same session.
- What was actually granted: Edit/Write/MultiEdit under `.claude/hooks/`,
  `.claude/unattended/`, `.claude/architecture/`, in `settings.local.json` --
  machine-local, because `settings.json` ships with the template and must not
  pre-grant this to every downstream project.
- What stays denied, in BOTH mechanisms: `constitution.md`, `settings.json`,
  `settings.local.json`. Deny beats allow in the permission list, and
  `protect-paths.sh` now refuses them independently -- because a permission list
  can be re-widened by editing the file that defines it.
- Verified: `hook-checks/test_guardrail_paths.py`, 5 refused / 5 allowed.
- Notes: the first version of that test reported every file as writable,
  including `.env`. protect-paths.sh signals a denial by PRINTING a decision and
  exiting 0, not by a non-zero exit. The `.env` control is what exposed the bad
  test. Kept in the suite for that reason.

## 2026-08-27T20:06:00Z — PRODUCT_DECISION — commits during an overnight run — CLOSED
- Question: does `git commit` stay a human-only checkpoint when a run is meant
  to last a night?
- Why it matters: work accumulates in the index. Today 41 files accumulated and
  the owner reviewed them, which worked. Unattended for eight hours, each session
  builds on top of unreviewed staged work, and one bad change is inherited by
  everything after it.
- Recommendation: keep the deny on `main`, and allow commits ONLY onto a
  dedicated `unattended/<date>` branch. That preserves the checkpoint -- nothing
  reaches `main` without a human -- while giving each session a verified base.
  It requires an owner change to the deny list; the AI cannot grant it.
- Human chose: the recommendation, verbatim -- "дозволяю коміти в гілку
  unattended/<дата>", 2026-08-27.
- Implemented: `block-dangerous.sh` now allows a commit ONLY when the current
  branch matches `unattended/*`, using the S7 command-position pattern so
  `cd x && git commit` and `git -C dir commit` are covered on both sides. An
  undeterminable branch falls through to refused -- it fails closed.
  `.claude/unattended/commit_checkpoint.sh` creates or switches to the branch and
  commits tracked modifications only (`git add -u`, never `-A`: an unattended run
  produces logs and scratch patches, and sweeping them in makes the review
  surface unreadable).
- Verified: `hook-checks/test_commit_policy.py`, 11/11 against real throwaway
  repos with real branches checked out.
- STILL BLOCKED on the owner: `settings.json` carries `Bash(git commit*)` in
  `permissions.deny`, deny beats allow, so no rule in `settings.local.json` can
  re-enable it -- and `settings.json` is now unwritable by the AI under D-23.
  The final enabling step is the owner's BY CONSTRUCTION, which is the design
  working rather than a defect. See the exact change in PROGRESS.md.
- Closed 2026-10-02 (package 3b, S6): the owner edit was made in the 2026-08-27 session —
  `git log -S'Bash(git commit' -- .claude/settings.json` shows the rule added in 8029d22
  and removed in 63df312 ("checkpoint(harness): unattended run baseline"), the D-27
  session. Verified today: the live `.claude/settings.json` carries
  no `Bash(git commit*)` deny, `block-dangerous.sh` allows a commit on `unattended/*`
  (test_commit_policy.py 20/20), and this run's own commits on
  `unattended/2026-10-02-package-3b` are the proof in use. The policy has since grown
  the environment table (cloud switch, ships off) — see docs/engine-limits.md.
- Status: CLOSED

## 2026-10-02T08:37:00Z — AUTONOMOUS — 3b-baseline-alias
- Decision: `evals/baseline/clean-ubuntu-24.04/results-push-policy.json` is created as a copy
  of `results-package-3a.json` with a label saying so, instead of being recorded afresh.
- Door: two-way
- Cost to reverse: delete one file.
- Why not escalated: not a product decision, not a threshold; the plan's step 6 names a file
  that does not exist, and `engine/push-policy` and `engine/package-3a` are the same commit
  (`9249b82`), so the 3a results ARE the push-policy engine's results. A clean-Ubuntu run
  cannot be made from this macOS machine; the honest move is a labelled alias, not a
  re-recording under a different environment presented as the same.
- Evidence: `git rev-parse engine/push-policy engine/package-3a`; HEAD measured against the
  3a file before any work: 77/77 identical.
- Falsified by: a hook or scenario change between the 3a recording and `9249b82` (none:
  the commits after the recording touch evals/ and docs/ only).
- Status: CLOSED

## 2026-10-02T08:38:00Z — AUTONOMOUS — 3b-S1-personal-keys
- Decision: ALL seven `permissions.additionalDirectories` entries move to the personal layer,
  `/tmp/claude/` included; `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` stays shared; the personal
  layer is read from the git ref like every other engine file and the home directory comes
  from `--home`, else Claude Code's own `CLAUDE_CONFIG_DIR`, else `~/.claude`.
- Door: two-way
- Cost to reverse: move a line between two JSON files and re-run `test_settings_proposal.py`.
- Why not escalated: the plan says "additionalDirectories з моїми домашніми теками"; six of
  the seven are home paths and the seventh is this machine's scratch directory, which is
  no more a project's business than the home paths. The block cap is engine behaviour, not
  a personal preference. Reading from the ref keeps "an install can be repeated byte for
  byte" true for the personal layer too. `CLAUDE_CONFIG_DIR` is the documented way to
  relocate `~/.claude` (code.claude.com/docs/en/env-vars); honouring anything else would
  make `install --personal` write where Claude Code does not read.
- Evidence: `evals/settings_parity.py compare` on the owner's real `~/.claude/settings.json`
  (read-only) + the live shared file vs. the real home file + `user/settings.json` merged in
  memory + `docs/tasks/settings.json`: identical, 13/13 effective settings.
- Falsified by: a project that legitimately needs `/tmp/claude/` as an additional directory
  for every contributor — then it belongs in the shared file again.
- Status: CLOSED

## 2026-10-02T08:39:00Z — AUTONOMOUS — 3b-S1-frozen-before
- Decision: the proposal test compares against a FROZEN effective-settings snapshot
  (`docs/tasks/effective-before-split.json`, computed from a home fixture of the owner's
  file's shape plus the shared file before the split) rather than against the live
  `.claude/settings.json`.
- Door: two-way
- Cost to reverse: regenerate the snapshot with one command (`settings_parity.py effective`).
- Why not escalated: a test that reads the live file as "before" inverts the moment the
  owner applies the proposal (the live file then IS the proposal, and "before" would be
  wrong). A frozen before holds on both sides of the apply, which is what a test the owner
  runs after the apply needs. The S4 deny-list change will be an intended, named difference
  against the same snapshot.
- Evidence: `hook-checks/test_settings_proposal.py`, 8/8, with a control showing the
  proposal WITHOUT the personal layer is not today's settings.
- Falsified by: the owner changing the live shared file for an unrelated reason before
  applying — then the snapshot must be regenerated and the test says so by failing.
- Status: CLOSED

## 2026-10-02T08:52:00Z — AUTONOMOUS — 3b-S2-stand-down
- Decision: every engine hook carries a static stand-down — not the project's own copy AND
  the project wires `hooks/<name>` → exit 0 with `STOOD_DOWN: …` on stderr — although the
  feature-critic's round-1 O1 asked to drop any runtime rule because identical handlers
  already run once. Kept, respecified (file-based, no dependence on order or timing, a
  marker so it is never mistaken for an allow, `ENGINE_HOOK_ALWAYS_RUN=1` as the only
  override and only in the running direction); the critic passed it in round 3.
- Door: two-way
- Cost to reverse: delete one function and one line from nine hooks (the skill's four
  copies follow by `cp`), delete test_hooks_fire_once.py, revert the runner change.
- Why not escalated: the owner's frame names the case verbatim — hooks wired in
  `~/.claude/settings.json` AND in the project must fire once per event — and the docs
  dedupe only IDENTICAL command strings; a home-level copy is wired under a different
  string (`~/.claude/hooks/x.sh`), which is exactly what the claude-autonomy skill installs.
  A design choice inside the engine's own files, reversible in one commit: Article 5
  assigns it to the AI. The critic's valid half (a silent exit 0 is indistinguishable from
  an allow) was adopted, not argued with.
- Evidence: hook-checks/test_hooks_fire_once.py 33/33 — nine home copies stand down with
  the marker, the project's copies still block all 10 deny and 4 refuse cases in the same
  environment, a project that wires nothing leaves the home copy guarding.
- Falsified by: Claude Code documenting that handlers are deduplicated by resolved script
  path rather than by command string — then the rule is dead weight and comes out.
- Status: CLOSED

## 2026-10-02T09:00:00Z — AUTONOMOUS — 3b-S3-cloud-switch
- Decision: the cloud commit switch is `CLOUD_COMMIT_POLICY` in `.claude/project.env`
  (values `off` | `session-branch`, shipped `off`, absent = off), read with `sed` rather
  than `source`; "the session's branch" means the branch the cloud session has checked
  out, any name, except the five protected ones; the switch stays off locally even when
  the key says `session-branch`; the environment probe lives at
  `.claude/unattended/env-probe.sh`, prints `key=value` lines, reports environment
  variables by NAME and prints values only for an allow-list of non-secret ones.
- Door: two-way
- Cost to reverse: one key renamed in two project.env files and two scripts; the probe is
  a stand-alone file.
- Why not escalated: the owner decided the policy table; what remained was where the
  switch lives and what it reads. project.env is already the hooks' runtime configuration
  surface and is a `project` file, so flipping it is a per-project decision that never
  ships back out of a project. `sed` instead of `source` because a deny hook must not
  execute a project file to decide a denial. "Any non-protected branch" because the shape
  of a cloud session's branch is precisely what the probe exists to observe — guessing a
  prefix (`claude/…`) would encode an unverified premise into a deny control.
- Evidence: test_commit_policy.py 20/20 (8 environment cases), test_commit_checkpoint.py
  19/19, test_env_probe.py 15/15 (a planted ANTHROPIC_API_KEY value and a user:token@ in
  a remote URL never appear in the output); 4 new hook scenarios.
- Falsified by: the probe showing a cloud session checks out a protected branch name, or
  that CLAUDE_CODE_REMOTE is not set as documented — then the rule changes on evidence.
- Status: CLOSED

## 2026-10-02T09:06:00Z — AUTONOMOUS — 3b-S4-dot-slash-rule
- Decision: besides the root rule the plan names, the `./` + `*` deny rules (both
  spellings) are removed from the proposal; `Bash(rm --recursive *)`, `~/*` and `$HOME*`
  stay as they are.
- Door: two-way
- Cost to reverse: two lines in docs/tasks/settings.json and one list in the test.
- Why not escalated: the plan's reason for narrowing the root rule — "the star also
  catches rm -rf /tmp/something" — applies verbatim to `./*`, which refused
  `rm -rf ./build`, the most ordinary delete an agent issues; test_deny_gaps.py even lists
  `rm -rf ./build` as a must-allow, where only the hook was measured. The hook refuses the
  literal `./*`. `~/*` and `$HOME*` are left alone because the hook refuses every
  `rm -rf ~…` and `rm -rf $HOME…` anyway, so narrowing them would change nothing
  observable; `--recursive *` is a long form agents do not type.
- Evidence: hook-checks/test_root_delete_deny.py — before the change `rm -rf ./build` and
  `rm -fr ./build` were `list=deny`; after it 37/37, with the live file shown to carry both
  defects.
- Falsified by: a project that wants `rm -rf ./<anything>` refused by the list rather than
  by the hook — it adds the rule back in its own settings.json.
- Status: CLOSED

## 2026-10-02T09:09:00Z — AUTONOMOUS — 3b-S5-collision-scope
- Decision: install.sh compares personal skill names against engine SKILLS and engine
  COMMANDS (both are /<name>), not against agents; the prefix for new personal skills is
  `my-`; a collision refuses the whole deployment before anything is linked.
- Door: two-way
- Cost to reverse: one list in install.sh, one word in the docs.
- Why not escalated: the owner asked for the check and for "a documented prefix"; which
  prefix and whether commands count are implementation choices with no external contract.
  Commands count because they share the slash namespace with skills; agents do not, they
  are addressed by the Task tool. Refuse-everything rather than skip-one because a
  half-deployed set of personal skills is harder to notice than none.
- Evidence: hook-checks/test_install_collision.py 12/12, including the real install.sh
  against this repository into a temporary home (no collision today; live-build deploys).
  Writing it found a bug in the first version: `engine_names | grep -q` under pipefail
  reported failure on every hit but the last name.
- Falsified by: Claude Code documenting that user skills and project commands live in
  separate namespaces — then the command half of the check is noise and comes out.
- Status: CLOSED

## 2026-10-02T09:14:00Z — AUTONOMOUS — 3b-S6-baseline-name
- Decision: the new reference results live at `evals/baseline/Laos-MacBook-Pro/results-package-3b.json`
  (the machine's LocalHostName; the plan says `<назва цієї машини>`), recorded from the S5
  commit (179ed43): S6 changes documents, the ownership map and tests, no hook, so the hook
  outcomes at S6 are those at S5 and the final run re-confirms it against this file.
- Door: two-way
- Cost to reverse: rename a directory; re-record with one command.
- Why not escalated: a file name and a recording point, both fixed by the plan's wording
  and by what changes between the two commits.
- Evidence: 86/86 scenarios pass on macOS 14.8.9 (Darwin 23.6.0), jq 1.8.2, Python 3.12.3;
  the 77 shared with results-push-policy.json identical, the 9 new ones (4 cloud-commit,
  5 rm-root/-fr) listed as the intended differences in the final report.
- Falsified by: nothing — a renamed directory is still the same data.
- Status: CLOSED
