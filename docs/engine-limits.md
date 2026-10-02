# What the engine's guarantees assume — and where they stop

The hooks, the deny list and the commit policy hold under one assumption: **one Claude Code
session works on one repository, the one it was started in.** Everything below follows from
how Claude Code hands a hook its context, verified against code.claude.com on 2026-10-02
(`/docs/en/hooks`, `/docs/en/settings`, `/docs/en/permissions`,
`/docs/en/claude-code-on-the-web`, `/docs/en/env-vars`).

## One session, one repository

- **The branch is the session's, not the shell's.** `block-dangerous.sh` reads the branch of
  `$CLAUDE_PROJECT_DIR`, the project root where the session started — not of wherever a
  `cd` in the command leads. Claude Code keeps `${CLAUDE_PROJECT_DIR}` pointing at that
  root even inside a `git worktree`. So `cd ../other-clone && git commit` is judged by the
  session repository's branch. On an `unattended/*` branch it is allowed, although the
  other clone may be on `main`. The commit policy protects the repository the session
  belongs to; a second repository reached through the shell is outside it. Working on
  another clone is a job for another session started there (or for
  `commit_checkpoint.sh` with `CLAUDE_PROJECT_DIR=<that clone>`, whose own branch guard
  then applies to that clone).
- **The hooks that run are the session repository's.** `.claude/settings.json` of the
  project the session started in wires `$CLAUDE_PROJECT_DIR/.claude/hooks/<name>`. A
  second repository's hooks never run in this session, whatever its settings say.
- **`.claude/project.env` is read from the session repository**, so `CLOUD_COMMIT_POLICY`,
  `SOURCE_DIRS` and the rest describe that one project.

## Hooks guard tool calls, not scripts

`block-dangerous.sh`, `protect-paths.sh`, `park-ask-gated.py` and the `permissions.deny`
list evaluate **the Bash command the agent types**. A command run from inside a script the
agent wrote is seen by none of them (verified 2026-08-27: `git commit --dry-run` is refused
at top level and runs untouched from a two-line script). Two consequences:

- a script the agent writes is a hole through every hook, so a guard the policy depends on
  must live inside the script too — `commit_checkpoint.sh` re-checks the branch itself;
- the hook scans the **whole command text**, including quoted strings and heredoc bodies.
  Writing documentation that mentions a root delete or a force push through a shell heredoc
  is refused as if the command were being run. This is deliberate (a false positive is a
  nuisance, a false negative is a breach) and the hook is not weakened for it. The
  canonical ways around it:
  - **a commit whose message mentions a dangerous command**: write the message to a file
    and commit with `git commit -F <file>` — the hook sees `git commit -F path`, never the
    message text. Writing the message inline (`-m "…"` or a heredoc) puts the text in the
    command and is refused;
  - documentation or tests that quote such a command: write the file with the Edit/Write
    tool (not scanned), or run a helper script from a file instead of a heredoc; in a
    Python test split the literal (`"git push " + "--force"`).

## One hook, one run per event

Claude Code runs an identical hook handler defined in two settings files once. The same
script wired under two **different** command strings — a home-level `~/.claude/hooks/x.sh`
next to the project's `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh` — runs twice. The engine
closes this at the source rather than at run time:

- the engine's hooks live in every repository that installs it and are wired there, by that
  repository's `.claude/settings.json`, and nowhere else. Nothing the engine ships writes a
  hook into `~/.claude/`: the claude-autonomy skill's user scope installs a settings file
  with no `hooks` block and no scripts (`assets/settings.user.json.template`), the personal
  layer (`user/settings.json`) must not wire hooks, and `engine.py install --personal`
  refuses one that does. `hook-checks/test_no_home_hook_copies.py` pins all three;
- the hooks themselves contain **no** "stand down if another copy exists" logic. Package 3b
  briefly had one (`engine_stand_down()`); it was removed because its test — "does the
  project's settings text mention `hooks/<name>`" — also matched a mention in an allow rule,
  a wiring on another event, or a `disableAllHooks` file, so a home copy could go quiet
  while the project's copy was not running at all, and because it added an exit-0 path to
  the deny hooks. A deny hook has exactly two outcomes: refuse, or evaluate and allow;
- if you find a hook copy under `~/.claude/hooks/` on a machine, it predates this rule.
  Delete it and its wiring in `~/.claude/settings.json`; the repositories that need the
  guardrails get them from `engine.py install <project>`.

## Settings levels

- Scalars such as `permissions.defaultMode` come from the highest level that sets them
  (local > project > user); list keys such as `permissions.allow` **merge** across levels.
  That is why the personal layer can carry `defaultMode`, the home directories and the
  blanket `WebFetch`/`WebSearch` allow without any project noticing a change:
  `evals/settings_parity.py` shows the effective settings identical before and after the
  split. (`defaultMode: auto` is legal at the user level only — the layer IS user level.
  Unattended sessions do not depend on it: `session-claude.sh` passes
  `--permission-mode acceptEdits` itself.)
- A **cloud session** reads the shared `.claude/settings.json` (it is in the clone) and does
  **not** read `~/.claude/settings.json` or `.claude/settings.local.json`. The engine's
  hooks run there; the personal layer does not apply there. `CLAUDE_CODE_REMOTE` is
  `"true"` in a cloud session; `.claude/unattended/env-probe.sh` prints that and the other
  facts the commit policy decides on.

## Writes to the project's own data under `.claude/`

`approve-project-data.py` (PermissionRequest, Edit/Write/MultiEdit) answers allow when the
target resolves — symlinks and `..` followed — to a path inside the session repository's
`.claude/` whose owner in `.claude/ownership.txt` is `project`, and decides nothing
otherwise. Its limits: it reads the ownership map of the session repository, so a project
that edits its map changes what is approved; an arbitrary new file under
`.claude/overseer/` is `engine`-owned by the shipped map (only the five named records and
`slice/` are `project`) and is not approved — put ad-hoc notes under `.claude/artifacts/`;
and a headless session in a directory never trusted interactively ignores that project's
settings, hooks included, so there the hook fires only when handed to the CLI with
`--settings` (`evals/probe_permission_hook.sh` shows both). `protect-paths.sh` runs first
and still refuses its protected paths. The hook is temporary: when Claude Code offers a
narrower permission for this, it goes.

## The deny list's `*`

A `*` in a `Bash(...)` rule matches any text, so a rule like `Bash(rm -rf /` + `*)`
refuses every absolute path, not only the root. The list keeps exact rules for the root,
the home directory and `$HOME`; the catastrophic literals a rule cannot express exactly
(`/*`, `./*`) are refused by `block-dangerous.sh`. `evals/permission_rules.py` is a
reference matcher for the documented semantics; `hook-checks/test_root_delete_deny.py`
shows the two instruments together.

## The commit policy, by environment

| environment | commit | push |
|---|---|---|
| attended, the owner's machine | refused — the commit is the owner's review checkpoint | `permissions.ask` prompts; force push denied |
| unattended (supervisor run) | allowed on `unattended/*` only | ask → parked by `park-ask-gated.py` |
| cloud session (`CLAUDE_CODE_REMOTE=true`) | allowed on the session's own non-protected branch **only** when `CLOUD_COMMIT_POLICY="session-branch"` in `.claude/project.env`; ships `off` | `permissions.ask`; force push denied |

The cloud rule is a switch and not a default because the shape of a cloud session has not
been observed from the inside. Run `bash .claude/unattended/env-probe.sh` there, read the
`git_branch`, `git_remotes`, `settings_*` and `session_kind` lines, and flip the key only
on that evidence. The probe reports environment variables by name and prints values for an
allow-list of non-secret ones only.
