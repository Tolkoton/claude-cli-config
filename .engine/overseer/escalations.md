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
(`Human chose`, `Latency to decision`) presumes a human answered. But the engine
rules' verdict routing says a two-way door is *logged here and continued*, not
escalated. A decision with nowhere to be recorded stays open in working memory
and gets re-raised turn after turn, which is a stop wearing a question mark.
Hence this second shape:

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

## 2026-10-02T09:54:03Z — AUTONOMOUS — 3b-finish-F1-user-scope-template
- Decision: the claude-autonomy skill's user scope installs a SEPARATE template (assets/settings.user.json.template, the project template without its hooks block) rather than prose telling the model to drop the hooks key from the shared template.
- Door: two-way
- Cost to reverse: delete one JSON file and point step 3 back at the shared template.
- Why not escalated: the owner decided that user scope installs no hooks; how the skill achieves it is an implementation choice. A file the test can parse beats an instruction a model may or may not follow — test_no_home_hook_copies.py asserts the template has no hooks block and agrees with the project template on everything else.
- Evidence: hook-checks/test_no_home_hook_copies.py 25/25.
- Falsified by: the two templates drifting apart on a non-hooks key — the test fails the moment they do.
- Status: CLOSED

## 2026-10-02T09:54:03Z — AUTONOMOUS — 3b-finish-F2-baseline-name
- Decision: results-push-policy.json is renamed results-package-3a-copy.json (supersedes 3b-baseline-alias on the name, not on the content); only its own label and the finish-round report are updated. The closed records that name the old file as a fact (ledger, escalations, the 3b report, the 3b contract, the frozen results-package-3b.json label, the owner's verbatim docs/plan/package-3b.md) are not rewritten.
- Door: two-way
- Cost to reverse: `git mv` back.
- Why not escalated: the owner asked for a name that says what the file is; it is a copy of results-package-3a.json. Rewriting closed records would corrupt the audit trail this repository keeps append-only (the feature-critic's #1 in this round). No script or live document consumed the old name.
- Evidence: repo-wide grep for the old name: hits only in closed records and the plan files; test_commit_policy.py 28/28.
- Falsified by: a live document found to point at the old name — then it is updated, not the records.
- Status: CLOSED

## 2026-10-02T10:07:29Z — AUTONOMOUS — 3b-finish-F5-no-decision-shape
- Decision: approve-project-data.py says 'no decision' as exit 0 with empty stdout (not the sample's exit 1), approves only `project`-owned paths under .claude/ by the ownership map, and the real-session probe hands the wiring to the CLI with --settings and targets .claude/architecture/.
- Door: two-way
- Cost to reverse: three small edits in one file and one in the probe script.
- Why not escalated: the owner decided what the hook approves and that it must be proven in a real session; the output shape for 'not mine' and the probe's mechanics are implementation. Exit 1 would surface a non-blocking error line on every ordinary write; exit 0 silent is the documented 'no decision'. --settings because a headless session in a never-trusted directory ignores that project's settings, hooks included (measured). architecture/ because overseer/<arbitrary>.md is engine-owned by the map and the hook rightly stays silent there — the first probe run showed exactly that.
- Evidence: test_approve_project_data.py 40/40; evals/probe_permission_hook.sh: A exists / B absent / C absent on Claude Code 2.1.287, haiku, ~$0.02 per session; the hook's logged stdout in case A was the allow decision, in the overseer/probe.md run it was empty.
- Falsified by: a Claude Code version that treats exit 0 + empty stdout on PermissionRequest as something other than 'no decision' — the probe would show B or C creating a file.
- Status: CLOSED

## 2026-10-02T10:09:37Z — AUTONOMOUS — 3b-finish-F6-lint-scope
- Decision: test_engine_lint.py judges the Python the ownership map calls `engine` (what ships), not every .py under .claude/: spike code under .claude/artifacts/ is project data and is excluded. The 21 mypy findings in runstate.py, recheck_parked.py and test_selfref.py were fixed rather than suppressed.
- Door: two-way
- Cost to reverse: one function in the test; the typing fixes stand on their own.
- Why not escalated: the owner asked for `ruff check --isolated .claude` and mypy on the engine's Python; the map says which Python is the engine's. A failing check on a project's spike would make every project's run red for code the engine does not own.
- Evidence: test_engine_lint.py: 7 engine-owned Python files, ruff clean, mypy --strict clean; test_selfref.py 10 refused / 8 allowed still.
- Falsified by: an engine Python file the map misclassifies as project — test_ownership.py would catch the map first.
- Status: CLOSED

## 2026-10-02T12:06:14Z — AUTONOMOUS — 3c-C2-layout-and-legacy-rules
- Decision: machine state keeps each file's old name under `.claude/state/<component>/`; `settings.local.json` and `worktrees/` stay where Claude Code puts them; the old record paths get explicit `project` rules before the `.claude/**` catch-all; the live records keep their entries and only the template header a record starts with follows its moved seed; approve-project-data.py is removed with the move (nothing project-owned is left under .claude/ for it to approve).
- Door: two-way
- Cost to reverse: the generic path pass in reverse; one commit.
- Why not escalated: the owner fixed the destinations; file names inside `.claude/state/`, rule order in the map and the header sync are implementation. The legacy rules are what the critic's premise probe demanded (test_legacy_records_survive.py).
- Evidence: 87/87 scenarios identical to results-package-3b-finish.json after the move; every suite green; the probe 9/9.
- Falsified by: a project whose records diverge from the seed header — untouched by design, the test tolerates it.
- Status: CLOSED

## 2026-10-02T12:06:14Z — AUTONOMOUS — 3c-C3-migration-shape
- Decision: migration is a table in engine.py applied before every other action, only when the ref's map knows `.engine/`; a conflict is `keep` with both files untouched (exit 1); emptied old directories are pruned; stale machine-state files a project still tracks at the old paths are NOT migrated (ephemeral by definition) and fall under the engine's existing retire/keep rule.
- Door: two-way
- Cost to reverse: one function and one tuple in engine.py.
- Why not escalated: the owner specified the table, the conflict rule, --dry-run and the tests; ordering and the machine-state exclusion are implementation. decana's dry run shows the result on real data with no loss.
- Evidence: test_migration.py 40/40; decana --dry-run: 17 moves, 0 losses.
- Falsified by: a project that WANTS its tracked machine state carried over — then two rows in the table.
- Status: CLOSED

## 2026-10-02T12:09:47Z — AUTONOMOUS — 3c-C4-fingerprint-shape
- Decision: the fingerprint is `.claude/state/contracts/<slug>.sha256` holding the digest and the contract path; `seal` refuses to overwrite (exit 3) and the planner is told never to delete a fingerprint itself; the overseer finds the active contract by the IN PROGRESS block of .engine/PROGRESS.md (complexity_budget's convention) and, on a mismatch, blocks with an escalation instruction under the same per-message guard as an audit; a contract with no fingerprint is audited as before.
- Door: two-way
- Cost to reverse: one hook file, two functions in overseer_stop.py, one paragraph in plan-slice.
- Why not escalated: the owner specified seal-on-approval, refuse-overwrite, compare-before-audit, escalate-on-change and tests for both cases; the file format, the discovery of the active contract and the no-fingerprint behaviour are implementation. Auditing pre-3c contracts as before avoids blocking every project in flight.
- Evidence: test_contract_fingerprint.py 15/15 against the real Stop hook.
- Falsified by: a project whose PROGRESS.md does not mark the slice IN PROGRESS — then there is no active contract and no check; the complexity gate has the same limit.
- Status: CLOSED

## 2026-10-02T12:16:38Z — AUTONOMOUS — 3c-C5-once-measurement
- Decision: the "hooks do not fire twice with --settings" check is measured by the headless session's own event stream (`--output-format stream-json --verbose` records `hook_started` per handler): in this trusted repository the SessionStart block's two handlers ran twice in total with and without `--settings .claude/settings.json`; the stream does not record PreToolUse/Stop handlers, so those rest on the same documented rule (identical handler → once). Not measured by `--debug`, whose log at this version does not list hook commands.
- Door: two-way
- Cost to reverse: re-run `evals`-style with another instrument when Claude Code exposes one.
- Why not escalated: the owner asked for a real-session check; which instrument shows the count is implementation. Six sessions on haiku, about $0.10 in total.
- Evidence: /tmp/claude-hooks-once/{with,without}-3.jsonl — 2 hook_started each (SessionStart:startup ×2), 0 extra with --settings.
- Falsified by: a stream showing 4 SessionStart handlers with --settings — then the handlers are not identical and the launcher must drop the flag or the project must change.
- Status: CLOSED

## 2026-10-02T12:16:38Z — FINDING (no decision) — Write(...) deny rules are inert
- Claude Code 2.1.287 warns at session start, for every `Write(<path>)` rule in permissions.deny: "not matched by file permission checks — only Edit(path) rules are. Use Edit(<path>) instead (Edit rules cover all file-modifying tools)". The live .claude/settings.json and the proposal carry twelve such rules; protect-paths.sh covers the same paths independently, so nothing is unguarded, but the rules are dead text. Owner-only (settings.json): fold into the next docs/tasks proposal.

## 2026-10-02T12:23:29Z — AUTONOMOUS — 3c-C6-references
- Decision: of the retired skill's three references, permission-philosophy.md moves to .claude/references/ with two stale sentences corrected (commit is governed by the hook's branch rule, push by the ask rule alone); hooks-reference.md (four of nine hooks) and auto-mode-and-flags.md (guessed flag names, Auto Mode described as a sandbox) are deleted. block-dangerous.sh's message names the engine and the script instead of the skill.
- Door: two-way
- Cost to reverse: `git revert` of one commit restores the files.
- Why not escalated: the owner said to keep what is still true and delete what is stale; which is which was checked against the live settings file and Claude Code 2.1.287's behaviour. No scenario or test depended on the old message text.
- Evidence: test_no_home_hook_copies.py 15/15 incl. "no live file points at the retired skill"; 28 suites green.
- Falsified by: a reader who needs the per-hook reference — CLAUDE.md's hook table and docs/engine-limits.md are where it lives now.
- Status: CLOSED

## 2026-10-02T12:23:29Z — AUTONOMOUS — 3c-C7-test-cmd
- Decision: with hook-checks/ renamed tests/, this repository's own .claude/project.env sets TEST_CMD="true" (the seed project.env is unchanged); tests/run_all.sh is the runner AGENTS.md names.
- Door: two-way
- Cost to reverse: one line in project.env.
- Why not escalated: the alternative — TEST_CMD running the whole suite — would add minutes to every turn end for a repository whose checks are run by hand after each slice anyway, and the owner's standing instruction is not to rely on this repository's Stop gate. A real project's gate is untouched.
- Evidence: bash tests/run_all.sh: 28 suites green after the rename.
- Falsified by: the owner wanting the Stop gate to run the suite here — one line.
- Status: CLOSED

## 2026-10-02T14:05:12Z — AUTONOMOUS — 3c-fix-X1-heartbeat-threshold
- Decision: a heartbeat younger than 900 s (config.sh's STALL_TIMEOUT_SEC default, copied as STALL_TIMEOUT_S into engine.py) counts as a live supervisor; so does supervisor.lock at the old OR the new place. State is then reported as `keep … stop it first` (exit 1) and data still moves.
- Door: two-way
- Cost to reverse: one constant.
- Why not escalated: the owner asked for "a fresh heartbeat"; the harness already defines fresh as "younger than the stall timeout", and reading the shell default into Python keeps the two in step without executing config.sh from the installer.
- Evidence: tests/test_state_migration.py 31/31 — lock case, fresh-heartbeat case, stale-heartbeat case.
- Falsified by: a project that sets STALL_TIMEOUT_SEC far above 900 and a supervisor that writes its heartbeat less often — then the constant should read config.sh.
- Status: CLOSED

## 2026-10-02T14:05:12Z — AUTONOMOUS — 3c-fix-X5-test-shape
- Decision: the owner's text ends at "Тест:"; the test asserts (a) no Write(<path>) deny rule remains in the proposal and (b) every deny rule dropped against the live file is a Write(...) whose Edit(...) twin is kept, and the deny difference from the frozen pre-split settings carries the reason.
- Door: two-way
- Cost to reverse: two checks in one test.
- Why not escalated: the requirement and its rationale were complete; only the test's wording was cut off, and (a)+(b) are what the rationale says must hold.
- Evidence: tests/test_settings_proposal.py 13/13; 12 Write rules removed, 12 Edit twins present.
- Falsified by: the owner's intended test being something else — one edit.
- Status: CLOSED

## 2026-10-02T14:05:12Z — FINDING — decana dry run exits 1 for a reason outside this round
- `engine.py update ~/Documents/GitHub/decana --ref HEAD --dry-run` (read-only): 3 state moves (.claude/overseer/state, .last_audit_sha, .continue_count → .claude/state/overseer/), no keep and no remove for any state file — item 5's substance holds. The exit code is 1, not 0, because decana edited three engine files (commands/plan-slice.md, settings.json, skills/slice-builder/SKILL.md) and the engine holds them back as it always did; exit 0 there would need `--take` or a merge by the owner.

## 2026-10-02T14:21:07Z — AUTONOMOUS — 3c-fix-X7-own-project-env (supersedes 3c-C7-test-cmd)
- Decision: this repository's .claude/project.env now describes the engine: SOURCE_DIRS=".claude/hooks .claude/unattended evals tests", CODE_EXTENSIONS="py sh", TEST_CMD="bash tests/run_all.sh". The owner asked for SOURCE_DIRS and TEST_CMD; "sh" in CODE_EXTENSIONS is the agent's addition, because the hooks are shell and a hook edit that does not run the suite would be the one edit the gate exists for.
- Door: two-way
- Cost to reverse: three lines in project.env.
- Why not escalated: the owner's instruction (item 7) falsifies 3c-C7-test-cmd's premise that the Stop gate should not run the suite here; CODE_EXTENSIONS follows from it. engine.py and install.sh at the root are files, so SOURCE_DIRS cannot name them; they still trigger verification by extension, only not the overseer's code signal.
- Evidence: bash tests/run_all.sh — 100.4 s wall before the change; tests/test_source_dirs.py; a live run of verify-on-stop.sh against a dirty tree (see the ledger).
- Falsified by: the suite growing past what a turn end can bear — then TEST_CMD should name a fast subset and run_all.sh stays the slice-end check.
- Status: CLOSED

## 2026-10-02T14:21:07Z — FINDING — SOURCE_DIRS with a multi-segment entry was inert on absolute paths
- overseer_stop._is_code_path matched an entry such as backend/src (the documented monorepo example) or .claude/hooks against a RELATIVE path only; Claude Code sends absolute ones. Every sandbox and scenario uses the single-segment "src", which took a different branch, so nothing caught it. Fixed in X7 (one containment test replaces the segment walk); pinned by tests/test_source_dirs.py.

## 2026-10-02T14:44:23Z — AUTONOMOUS — 3c-fix-X8-runner-save-shape
- Decision: run_audit_scenarios.py saves after every RUN (the owner said every scenario; a run is the unit paid for and the cost of saving is the same), writes temp-then-replace, records the resolved engine COMMIT and refuses --resume on a different commit, model, settings layers or runs-per-scenario; an existing --out without --resume is refused rather than replaced; --only takes a comma-separated list.
- Door: two-way
- Cost to reverse: each rule is one condition in main(); the file format only gained keys (engine_commit, status, pending).
- Why not escalated: all are the owner's item 8 made concrete. The two refusals exist because forgetting a flag or moving HEAD between a crash and a resume are the two cheapest ways to destroy or contaminate paid results, and the second was the critic's blocking finding. The documented re-record command now needs the old file removed first; evals/README.md says so.
- Evidence: tests/test_audit_runner_resume.py 32/32 with a claude shim and a SIGKILL at run 3; ~12 s.
- Falsified by: a legitimate need to top up a file to more runs per scenario — then runs_per_scenario mismatch should become "continue up to the larger number" (one condition).
- Status: CLOSED

## 2026-10-02T14:44:23Z — FINDING — item 9's "45 mypy findings" were 9
- The package 3c report counted the lines of mypy's output: nine errors, each call-overload error followed by six "possible overload variants" notes (6 x 6 = 36), 45 lines. The file had 9 strict errors at v0.10.1 and 9 at the start of the addendum. The report is corrected in place; the plan text keeps the owner's wording.

## 2026-10-02T14:44:23Z — FINDING — a suite can be green by hand and red from the Stop gate
- The gate runs TEST_CMD with Claude Code's hook environment, where CLAUDE_PROJECT_DIR names the project. tests/test_deny_gaps.py let block-dangerous.sh read this repository's branch through it, so on an unattended/<date> branch its commit cases came back ALLOWED — only from the gate. Seen on the first gate run of X7; pinned like test_deny_hooks. Any suite that calls a hook without pinning CLAUDE_PROJECT_DIR has the same exposure; the whole set ran green from the gate afterwards (102 s).

## 2026-10-02T19:40:00Z — AUTONOMOUS — 2b-D7-jq-paragraph
- Decision: no paragraph names macOS, so the owner's "false jq paragraph" was located by what is false: the unattended README's "REQUIRED: four hooks silently enforce nothing without it" (false since the python3 fallback) and the evals README naming jq alone. Every jq paragraph the model reads now says: jq or python3, refuse with neither, install either with the OS's package manager (.claude/references/hooks.md).
- Door: two-way
- Cost to reverse: a few lines of prose.
- Why not escalated: the requirement (true text, any OS) is clear; only which paragraph the owner meant is ambiguous, and fixing all of them satisfies every reading.
- Evidence: grep for jq across the tree; tests/test_text_hygiene.py pins the rule and that both deny hooks really fall back to python3.
- Falsified by: the owner naming a different paragraph — then that one gets the same treatment.
- Status: CLOSED

## 2026-10-02T19:40:00Z — AUTONOMOUS — 2b-D10-instrument
- Decision: the before-run was stopped after 10 runs ($6.83) and the instrument fixed first — the audit fixture moved to .engine/slices/ (the path a post-3c overseer reads), the runner passes --settings <sandbox>/.claude/settings.json and pre-flights the fixtures against a built sandbox, a usage-limit answer is recorded as an error that --resume redoes. Both runs of the package use the fixed instrument; the stopped run is kept as audit-v0.11.0-run1-broken-instrument.json.
- Door: two-way
- Cost to reverse: one commit (e7b89c4); the stopped run's $6.83 cannot be unspent.
- Why not escalated: the owner's item 0 asks for a check of package 3c, and this IS its result — two 3c defects that made every audit session block for want of evidence it was not allowed to gather; measuring a broken instrument for $20 more would have answered nothing. Money stayed inside the $35 cap (estimate $28 total for item 0).
- Evidence: every 01 session at v0.11.0 "the slice contract .engine/slices/ref-tax.md is missing", ledger_entry_written=false, permission_denials 2-13; permission probe 16:10Z: plain → 2 denials, --settings → 0.
- Falsified by: a clean before-run that still shows the same denials — then the cause is elsewhere (the allow list itself).
- Status: CLOSED

## 2026-10-02T19:40:00Z — AUTONOMOUS — 2b-D11-restart-before-run
- Decision: restart the before-run in full on the fixed instrument rather than continue the stopped file or sample 01/08 only.
- Door: two-way
- Cost to reverse: about $21 of sessions (0.68 $/run × 30), already inside the cap.
- Why not escalated: a before/after pair measured on two instruments is not a pair, and the owner's "no other scenario worse" needs every scenario on the same footing; the cap is not exceeded.
- Evidence: $6.83 spent + ~$21 ≈ $28 < $35; audit-v0.11.0-run1-broken-instrument.json label.
- Falsified by: the clean run exceeding the cap through usage-limit retries — then the remainder parks as money.
- Status: CLOSED

## 2026-10-02T19:40:00Z — AUTONOMOUS — 2b-critic-convergence
- Decision: the feature-critic loop closed at round 4 with its PREMISE_PROBE_REQUIRED folded in as the exit criteria of P5a/P5b (one scenario session per edited text, cents, before P7) — no BLOCKING objection survives; a fifth round would be the circuit-breaker's owner ruling, which the owner's correction 3 ("repeat round 3 before building") did not ask for.
- Door: two-way
- Cost to reverse: one more critic round (~100k tokens).
- Why not escalated: every round's finding was distinct, real and applied (fixture path; confounded 01 cause; engine.py freeze during P0; cheap probe before P7); the remaining notes are recorded in the contract.
- Evidence: .engine/architecture/feature/engine-package-2b.md § Critic.
- Falsified by: P7 failing on a text that a probe would have caught — the probes exist precisely for that.
- Status: CLOSED

## 2026-10-02T19:40:00Z — AUTONOMOUS — 2b-P9-phase-script (owner correction 2)
- Decision: the phase guard is set through `python3 .claude/hooks/overseer_phase.py set plan | clear | show`, named in the engine rules and used by /plan-slice and /feature-architect; the agent never writes .claude/state/ with its own tools. The alternative the owner named — a hook that sets the phase by event (UserPromptSubmit on a planning command) — needs a .claude/settings.json change, which is owner-only, so it is not built; the script is also what such a hook would call.
- Door: two-way
- Cost to reverse: one script, three text edits, one test.
- Why not escalated: the owner asked for exactly one of the two paths; the script needs no settings change and works today.
- Evidence: the classifier's refusal of `printf plan > .claude/state/overseer/state` (16:19Z); tests/test_overseer_phase.py shows set → _phase_is_plan True, clear → False.
- Falsified by: the classifier refusing the script too — then the hook path is the only one and needs a docs/tasks proposal.
- Status: CLOSED

## 2026-10-02T20:05:00Z — AUTONOMOUS — 2b-D4-D5-D6-claude-md-shape
- Decision: (D4) the seed CLAUDE.md carries a marked block (`<!-- >>> engine: ... -->` / `<!-- <<< engine -->`) around the one import line, and engine.py rewrites only the text between the markers when the ref's seed block differs — the invariant of item 4 made checkable; (D5) an edited old copy is never touched, the report names the import line and the line ranges duplicating .claude/engine-rules.md (runs ≥ 3 non-blank lines found in the engine's own history, trailing whitespace ignored, import lines end a run, table separators are neutral); (D6) a project file equal to any historical blob of its SEED path is pristine too.
- Door: two-way
- Cost to reverse: the block logic is one function pair and one action verb; the report is one function; D6 is one set union.
- Why not escalated: the owner's two bullets (pristine → reseed, edited → exact report) are met literally; the block maintenance is what "outside a marked block" implies going forward, and it changes nothing in a project that keeps the block as seeded.
- Evidence: tests/test_claude_md_update.py 29/29; decana --dry-run (read-only) boundaries verified by hand.
- Falsified by: a project that legitimately edits inside the block — then the block must be compared against the engine's history before rewriting (one more condition).
- Status: CLOSED

## 2026-10-02T20:05:00Z — FINDING — decana carries the old rules inline, partly edited
- `engine.py update ~/Documents/GitHub/decana --ref HEAD --dry-run` (read-only): CLAUDE.md is an edited old copy; the report names `@.claude/engine-rules.md` to add and seven ranges to delete (1–11, 37–43, 45–48, 52–92, 111–115, 119–145, 166–176); the gaps are decana's own edits of the rules ("### Commits are yours; the branch and the remote are the human's", a changed ask list, an extra hook row, a parked-queue paragraph). AGENTS.md lines 17–29 are the old seed's active-agents table and pipeline section. Exit 1 only for the three engine files decana edited (plan-slice.md, settings.json, slice-builder/SKILL.md), as in 3c. Nothing was written.
