# Feature engine-package-3b — decomposition

Frame source: `docs/plan/package-3b.md` (the owner's text, verbatim). This artifact
restates it as the feature contract the slices are built from. Nothing here was asked
of the owner again; where the plan and the repository disagree, the disagreement is
written down under *Open items* with the decision taken, not re-asked.

## Goal

Finish package 3 ("the frame"). The engine's settings split into a shared layer that
ships with every project and a personal layer that is the owner's alone and is merged
into the owner's home configuration by the engine itself. The commit policy is decided by
the environment the session runs in. A hook wired at two levels still fires once per
event. Plus the small items the plan lists.

## Acceptance criteria (from the plan, "ГОТОВО, КОЛИ")

1. Every hook-checks suite is green, the new ones included.
2. The hook scenario set is identical to the golden baseline except for intended,
   documented differences. A new baseline is recorded under
   `evals/baseline/<this machine>/results-package-3b.json` (macOS, not clean Ubuntu).
3. `ruff` and `mypy --strict` (through `uvx`) are clean on every Python file touched.
4. The ownership map knows every new file.
5. `docs/TEMPLATE-SETUP.md` describes the personal layer.

## Build parameters (from the plan, "ПОРЯДОК РОБОТИ")

- Branch: `unattended/2026-10-02-package-3b` from `engine/push-policy`; one slice = one
  commit; messages in English and say WHY.
- After every slice, explicitly: all `hook-checks/test_*.py`; the hook scenarios against
  the push-policy baseline; `uvx ruff` and `uvx mypy --strict` on changed Python.
- Cheap-to-reverse decisions are taken and logged in `escalations.md` (AUTONOMOUS format).
- Owner-only items are parked as DAG nodes with the exact unblocking step.
- Claude Code facts are verified against code.claude.com before they are relied on.
- Never: touch the sibling clone or `main`/`stable`; push; sudo; a real write under
  `~/.claude` (dry-run only); rename an existing skill.

## Premises verified (docs read 2026-10-02; the sources are listed in the final report)

- P1 Settings precedence, highest first: managed, command line, project local, shared
  project, user. A key set higher overrides the same key lower. List keys such as
  `permissions.allow` MERGE across files. `env` merges per key. —
  code.claude.com/docs/en/settings, /settings-reference.
- P2 Hooks: "Hook entries merge across settings levels rather than replacing each
  other"; "If you define the same handler in more than one settings file, it runs once";
  all matching hooks run in parallel. Order across levels is NOT documented. Handlers
  run in the current directory; `${CLAUDE_PROJECT_DIR}` is the project root where the
  session started, even after `cd` or a worktree. — /hooks.
- P3 Cloud session: `CLAUDE_CODE_REMOTE` is `"true"` in a cloud session and unset in
  the local CLI; `CLAUDE_CODE_REMOTE_SESSION_ID` carries the session id there. User and
  project-local settings are NOT read in a cloud session; the shared project file is.
  — /env-vars, /settings ("Settings in cloud sessions").
- P4 Bash permission rules: `*` matches any text; a rule without `*` is an exact
  match; `:*` equals a trailing ` *`; deny, then ask, then allow, first match wins and a
  narrower allow cannot carve out of a deny; deny/ask rules apply to every subcommand of
  a compound command. — /permissions.
- P5 The owner's real `~/.claude/settings.json` holds only `model` and `theme`; there is
  no `~/.claude/hooks` directory. (Read-only inspection, this session.)
- P6 `engine/push-policy` is the same commit as `engine/package-3a` (`9249b82`), so the
  golden baseline recorded for 3a is the baseline of the push-policy engine.

## Out of scope (deliberately)

- Editing `.claude/settings.json`, `.claude/settings.local.json`, `.claude/constitution.md`
  (owner-only by `protect-paths.sh`); the engine produces a full proposed file, a test
  of that proposal, and one apply command instead.
- Applying `install --personal` to the owner's real home.
- Running the environment probe in a real cloud session; the cloud switch ships OFF.
- Splitting `CLAUDE.md` into engine rules and project text (package 2b's job).
- Renaming any existing skill.

## Slices (the DAG)

- **S1 personal-layer** — delivers: `user/settings.json` holding the personal keys
  (defaultMode, WebFetch/WebSearch allow, model env, home additionalDirectories);
  `engine.py install --personal` merging it into the home settings with `--dry-run`,
  idempotence, foreign keys kept, a backup before writing; tests on a temporary home;
  `evals/settings_parity.py` computing the effective user+project settings before and
  after the split — "before" is the owner's real `~/.claude/settings.json` read-only plus
  the live shared file; the test suite uses a fixture with the same shape (P5) so the
  claim "the same values as today" is made against the real machine in the report and
  against the fixture in the suite. · contract out: the personal file's key set, the
  merge rules, the proposed shared `.claude/settings.json` in `docs/tasks/` AND the one
  apply command in `docs/tasks/README.md` (what S7's unblock step names) · depends on: —
  · **TRACER BULLET (build first)** — it is the one chain that crosses engine.py, the
  ownership map, the docs' settings semantics and the parity check.
- **S2 hooks-fire-once** — delivers: the personal layer wires no hooks (asserted by a
  test) and `install --personal` refuses a personal file with a `hooks` key; the
  read-only report on the owner's home settings; and a **static stand-down rule** in
  every engine hook for the one case P2 leaves open — the same script wired at two
  levels under *different* command strings (a home-level `~/.claude/hooks/x.sh` next to
  the project's `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh`; identical strings already run
  once per the docs). The rule depends on files, never on timing or order: a hook whose
  own path is not `$CLAUDE_PROJECT_DIR/.claude/hooks/<its name>` exits 0 when the
  project's `.claude/settings.json` or `settings.local.json` wires `hooks/<its name>`;
  otherwise it runs. A stand-down is never silent: the hook prints
  `STOOD_DOWN: <its name> defers to <the project's copy>` on stderr (exit 0, so the
  harness treats it as an allow, but captured output tells a stand-down from an allow —
  the critic's O5). `ENGINE_HOOK_ALWAYS_RUN=1` disables the stand-down (the only override,
  in the safe direction) so a foreign hook directory can still be measured by `evals/`.
  Regression: `hook-checks/test_hooks_fire_once.py` re-runs every MUST_BLOCK /
  MUST_REFUSE case of `test_deny_gaps.py` and `test_guardrail_paths.py` through the
  project's OWN copy under a stand-down-shaped environment (a `CLAUDE_PROJECT_DIR` whose
  `.claude/settings.json` wires the hook) and asserts each still blocks, and asserts the
  home-level copy stands down with the marker in the same environment. The critic's O1 asked to drop the runtime rule; kept because the owner's frame
  names "wired in both ~/.claude/settings.json and the project → once per event" as a
  goal, and the different-string case is real (the claude-autonomy skill installs copies
  into a home folder). Logged as an AUTONOMOUS decision. · contract out: the stand-down
  rule, its override, and the runner change that executes `<project_dir>/.claude/hooks/`
  when a scenario starts the session in a subdirectory · depends on: S1.
- **S3 commit-policy-by-environment** — delivers: `.claude/unattended/env-probe.sh`
  printing the facts a policy decides on; `block-dangerous.sh` deciding the commit rule
  by environment: attended local = refuse, unattended = `unattended/*`, cloud = the
  session's branch when `CLOUD_COMMIT_POLICY` is on (ships off); `commit_checkpoint.sh`
  keeps a run's suffixed branch and can commit the index as staged. · contract out: the
  switch name and the probe's output format · depends on: — (no fixture is shared with
  S1; S3 extends `hook-checks/test_commit_policy.py` and adds
  `hook-checks/test_commit_checkpoint.py`, both part of "the full hook-checks set").
- **S4 narrow-root-delete-deny** — delivers: `rm -fr`/`rm -rf` parity in the hook; a
  reference matcher implementing the documented Bash-rule semantics; a test that the
  proposed deny list plus the hook block `rm -rf /`, `rm -rf /*`, `rm -rf ~`,
  `rm -rf $HOME` and let `rm -rf /tmp/x` through; the deny-list change folded into the
  proposed `.claude/settings.json` of S1. · depends on: S1 (the proposal file).
- **S5 install-name-collision** — delivers: `install.sh` refuses when a `user/skills`
  name equals an engine skill name, with the reason; the prefix convention for new
  personal skills documented. · depends on: —.
- **S6 docs-and-records** — delivers: `docs/engine-limits.md` (one session, one
  repository; the branch is the session's); the personal layer in
  `docs/TEMPLATE-SETUP.md`; the stale escalation closed; ownership map complete; the
  new macOS baseline recorded. · depends on: S1–S5.
- **S7 apply-shared-settings (PARKED, owner)** — apply `docs/tasks/settings.json` to
  `.claude/settings.json` with the one command S1 prints.
- **S8 apply-personal (PARKED, owner)** — run `engine.py install --personal` for real.
- **S9 cloud-probe (PARKED, owner)** — run the probe in a cloud session, then decide the
  switch.

## Inter-slice contracts

- S1 → S2: `user/settings.json` is the personal layer; S2 asserts it has no `hooks` key
  and `engine.py install --personal` refuses one.
- S1 → S4: `docs/tasks/settings.json` is the single proposed shared file; S4 edits its
  deny list and its test reads it.
- S3 → S6: the probe's output lines are what `docs/engine-limits.md` tells the owner to
  paste back.
- S1–S5 → S6: every new path is named in `.claude/ownership.txt` under the right owner.

## Integration exit criterion

`hook-checks/test_personal_layer.py` installs the personal layer into a temporary home,
runs the parity script against the proposed shared file, and shows the effective values
equal today's; the full hook-checks set (S1–S5's new suites included) and the scenario
set are green; the new baseline is recorded.

## Deferred to later features

- A `--personal` uninstall (removing the layer's keys from the home file) — why later:
  the owner asked for merge semantics that never delete; revisit when a key is retired.
- Splitting `CLAUDE.md` — package 2b.

## Open items requiring human decision

- None that block. Three nodes are parked for the owner's hands (S7, S8, S9); each
  carries its exact unblocking command.
- Plan step 6 names a baseline file `results-push-policy.json` that does not exist;
  by P6 the 3a baseline is the same engine, so it is copied under that name (logged as
  an AUTONOMOUS decision).
