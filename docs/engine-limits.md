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
  nuisance, a false negative is a breach); the workaround is to write such text with the
  Edit/Write tool, or to run a script from a file instead of a heredoc.

## One hook, one run per event

Claude Code runs an identical hook handler defined in two settings files once. The same
script wired under two **different** command strings — a home-level `~/.claude/hooks/x.sh`
next to the project's `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh` — would run twice. Every
engine hook therefore stands down when it is not the project's own copy and the project
wires `hooks/<its name>`; it prints `STOOD_DOWN: <name> defers to <project copy>` on stderr
and exits 0. The limits:

- the decision reads files, never timing: the project's copy runs regardless of which copy
  Claude Code happens to start first;
- a stand-down is never silent — an allow is exit 0 with **empty** stderr. In an unattended
  run the session's stdout and stderr land in `.claude/unattended/logs/session-*.log`, so
  `grep STOOD_DOWN` there tells a stand-down from an allow after the fact;
- `ENGINE_HOOK_ALWAYS_RUN=1` makes a hook run anyway (the only override, and only in that
  direction). `evals/run_hook_scenarios.py --hooks-dir` sets it, otherwise a foreign hook
  directory measured against a sandbox would record nothing but stand-downs;
- a project that wires nothing leaves a home-level copy running: the global guard still
  works in a repository without the engine;
- the personal layer (`user/settings.json`) must not wire hooks, and `engine.py install
  --personal` refuses one that does.

## Settings levels

- Scalars such as `permissions.defaultMode` come from the highest level that sets them
  (local > project > user); list keys such as `permissions.allow` **merge** across levels.
  That is why the personal layer can carry `defaultMode`, the home directories, the blanket
  `WebFetch`/`WebSearch` allow and the model aliases without any project noticing a change:
  `evals/settings_parity.py` shows the effective settings identical before and after the
  split.
- A **cloud session** reads the shared `.claude/settings.json` (it is in the clone) and does
  **not** read `~/.claude/settings.json` or `.claude/settings.local.json`. The engine's
  hooks run there; the personal layer does not apply there. `CLAUDE_CODE_REMOTE` is
  `"true"` in a cloud session; `.claude/unattended/env-probe.sh` prints that and the other
  facts the commit policy decides on.

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
