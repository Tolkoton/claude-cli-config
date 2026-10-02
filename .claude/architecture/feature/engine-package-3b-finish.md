# Feature engine-package-3b-finish — decomposition

Frame source: `docs/plan/package-3b-finish.md` (the owner's review of package 3b, verbatim).
Every numbered item there is an **owner requirement**: it is not up for review by the
architect or the critic. What the critic checks is how each requirement is met — the
seams, the tests, the contracts between slices. Where a requirement meets the repository
and leaves a choice open, the choice is an **agent decision**, marked as such below and
logged as AUTONOMOUS in `.claude/overseer/escalations.md`.

## Goal

Finish package 3b after the owner's review: take the S2 stand-down out and close the
source of duplicate hooks at its origin, let push leave the hook's protected-branch block,
make unattended sessions independent of the personal `defaultMode`, reshape the personal
layer, propose a PermissionRequest hook for the project's own data under `.claude/`, and
fix the small things the last report listed.

## Acceptance criteria (the plan's "ГОТОВО, КОЛИ")

1. Every hook-checks suite green, the new ones included.
2. The scenario set identical to `evals/baseline/Laos-MacBook-Pro/results-package-3b.json`
   except for intended, listed differences; the new reference recorded as
   `evals/baseline/Laos-MacBook-Pro/results-package-3b-finish.json`.
3. `uvx ruff check` and `uvx mypy --strict` clean on every Python file touched.
4. The ownership map knows every new file.

## Build parameters

- Same branch, new commits only; no revert, reset or rebase. One slice = one commit,
  English, saying WHY. After each slice: all hook-checks, the scenario set against the 3b
  baseline, ruff + mypy --strict on changed Python.
- Timestamps in records: UTC from `date -u`, never guessed.
- Owner-only: wiring the new hook into `.claude/settings.json` (proposal + command), S8
  (personal layer into `~/.claude`), S9 (cloud probe). The rest of `docs/plan/package-3b.md`
  still applies (no push, no sudo, no real write under `~/.claude`, no skill renames).

## Premises (verified 2026-10-02 against code.claude.com; re-used from package 3b)

- P1 Settings: scalars override by level (local > project > user), lists merge.
  `permissions.defaultMode` values `auto` and `bypassPermissions` take effect from user or
  managed settings only — the personal layer IS user settings, so `auto` is legal there.
- P2 Hooks: an identical handler in two settings files runs once; different command
  strings run twice. The fix round removes the runtime stand-down and instead stops the
  engine's own tooling from ever writing a second copy into the home directory.
- P3 Cloud: `CLAUDE_CODE_REMOTE=true`; user and local settings not read there.
- P4 `claude --permission-mode <mode>` exists in the installed CLI (2.1.287) with
  `acceptEdits` among its choices (checked with `claude --help`).
- P5 PermissionRequest hooks: the sample `auto-approve-web.py` already emits
  `{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}`;
  whether THIS Claude Code version honours it for Edit/Write/MultiEdit is exactly what F5's
  real-session check establishes — it is not assumed.

## Slices (the DAG)

- **F1 remove-stand-down** (owner item 1) — delivers: `engine_stand_down()` and its call
  removed from all nine hooks and from the four copies in `claude-autonomy/scripts/`;
  `ENGINE_HOOK_ALWAYS_RUN` removed everywhere (runner, probe, docs); the runner still
  executes the session checkout's copy for subdirectory scenarios, and the ruff/mypy
  clean-up stays; the claude-autonomy skill no longer writes hook copies into the home
  directory — user scope installs a settings file WITHOUT a `hooks` block
  (`assets/settings.user.json.template`, agent decision: a separate template rather than
  prose asking the model to strip a key); `test_hooks_fire_once.py` replaced by
  `test_no_home_hook_copies.py` (a user-scope install into a temporary home wires no hook;
  no hook has an exit-0 path conditioned on another copy existing). · depends on: —.
- **F2 push-leaves-the-hook** (owner item 2) — delivers: the protected-branch block in
  `block-dangerous.sh` names `commit` only and its message names the matched subcommand;
  `test_commit_policy.py` asserts `Bash(git push:*)` in `permissions.ask` and
  `Bash(git push --force*)`, `Bash(git push -f *)` in `permissions.deny` of the LIVE
  `.claude/settings.json` (S7 is applied, so the live file is the contract) and of the
  proposal; scenarios `bd-push-on-main` and `bd-push-on-protected-branch-in-worktree`
  expect `allow`, new `bd-commit-on-unattended-branch-in-worktree` expects `allow`;
  `results-push-policy.json` renamed to what it is — `results-package-3a-copy.json` (agent
  decision on the name) — with every reference updated. · depends on: —.
- **F3 explicit-permission-mode** (owner item 3) — delivers: `session-claude.sh` passes
  `--permission-mode acceptEdits`; `test_session_launch.py` runs the launcher with a shim
  `claude` on PATH that records its argv (the repository's own rule for absent tools) and
  asserts the flag and value. · depends on: —.
- **F4 personal-layer-reshape** (owner item 4) — delivers: `user/settings.json` with
  `defaultMode: "auto"`, no model variables, the directories and the web allow kept;
  `test_personal_layer.py` and `test_settings_proposal.py` updated so each difference from
  the frozen "before" is listed with its reason; `docs/tasks/README.md` and
  `TEMPLATE-SETUP.md` say so. · depends on: —.
- **F5 approve-project-data** (owner item 5) — delivers: `.claude/hooks/approve-project-data.py`,
  a PermissionRequest hook that allows Edit/Write/MultiEdit when the target resolves
  (realpath, `..` and symlinks followed) to a path inside `$CLAUDE_PROJECT_DIR/.claude/`
  whose owner per `.claude/ownership.txt` is `project`, and decides nothing otherwise
  (exit 0, no output — agent decision: silent no-decision rather than the sample's exit 1,
  so the hook never shows an error for the common case); the ownership matcher
  re-implemented inside the hook (engine.py is not shipped into projects); the wiring as a
  proposal in `docs/tasks/settings.json` plus the apply command; `test_approve_project_data.py`
  (every path class, `..`, symlinks out); and a REAL headless session in a temporary
  project with the hook wired, showing the write under `.claude/overseer/` goes through
  with the hook and is refused without it. · depends on: — (the proposal file is shared
  with F4; F4 first).
- **F6 small-things** (owner item 6) — delivers: `recheck_parked.py` reads tokens from the
  `Unblocks when:` line only; `hook-checks/test_engine_lint.py` runs
  `ruff check --isolated .claude` and `mypy --strict` on the engine's Python, and AGENTS.md
  lists it; `test_engine_install.py` skips the hooks-equal-HEAD check with an explanation
  while `.claude/hooks` has uncommitted changes; `git commit -F <file>` documented as the
  canonical way when a message mentions a dangerous command; `feature-critic.md` and
  `critic-core.md` distinguish owner requirements from agent decisions and do not review
  the former. · depends on: —.
- **F7 records-and-baseline** — delivers: docs updated for F1–F6 (`engine-limits.md`,
  `TEMPLATE-SETUP.md`, `evals/README.md`, `AGENTS.md`), ownership map, the new baseline
  `results-package-3b-finish.json`, the report. · depends on: F1–F6.
- **F8 wire-approve-project-data (PARKED, owner)** — apply the proposal to
  `.claude/settings.json` with the one command in `docs/tasks/README.md`.
- **S8 apply-personal (PARKED, owner, carried over)** — after this round.
- **S9 cloud-probe (PARKED, owner, carried over)**.

## Inter-slice contracts

- F4 → F5: both edit `docs/tasks/settings.json`; F4 changes nothing there (the personal
  layer is `user/settings.json`), F5 adds the PermissionRequest group. `test_settings_proposal.py`
  must then list the hooks difference against the live file as intended until F8.
- F2 → F7: the renamed baseline is what `docs/plan/package-3b.md` step 6 named; the plan
  file itself is the owner's verbatim text and is NOT edited — the rename is recorded in
  the report and in the escalation that created the alias.
- F1 → F7: `docs/engine-limits.md` "One hook, one run per event" is rewritten around the
  closed source, not the removed stand-down.

## Integration exit criterion

The full hook-checks set green; the scenario set against `results-package-3b.json` differs
only in the listed scenarios (two push cases flip to allow, one new worktree commit case);
the new baseline recorded; the real headless session shows the PermissionRequest hook
lifting a prompt in this Claude Code version.

## Open items requiring human decision

None that block. F8, S8, S9 are parked with their commands.
