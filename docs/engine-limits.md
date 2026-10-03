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
  hook into `~/.claude/`: the installer is `engine.py` alone (the claude-autonomy skill that once
  copied hooks into a home directory is retired), the personal
  layer (`user/settings.json`) must not wire hooks, and `engine.py install --personal`
  refuses one that does. `tests/test_no_home_hook_copies.py` pins all three;
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

## The boundary: `.claude/` is the engine's, `.engine/` is the agent's

`.claude/` holds what **defines and constrains** the agent — settings, hooks, skills, agents,
commands, the constitution, the ownership map, the unattended harness, `project.env`, and all
machine state under `.claude/state/`. Claude Code protects it: every write an agent tool
makes there is shown to a human or to the classifier, and that is the point. `.engine/` holds
what the agent **produces** while working — the overseer's records, slice contracts,
architecture, premises, spikes, `PROGRESS.md` — and is not protected; a ledger entry needs
no permission prompt. The limits:

- machine state is written by hooks and scripts, never by agent tools, so it raises no
  prompt although it lives under `.claude/`; an agent that writes `.claude/state/` by hand
  is doing something the design did not intend;
- `project.env` is project-owned and lives under `.claude/` on purpose: it is the gates'
  switchboard (`TEST_CMD=true` would pass every gate), so it is **never approved
  automatically** — a person edits it at setup time and answers the prompt;
- a project built before package 3c has its records at the old paths; `engine.py update`
  moves them by an explicit table and reports, without touching, a file that exists in both
  places (`docs/TEMPLATE-SETUP.md`, "Keeping the engine up to date");
- the old `approve-project-data.py` hook is gone with the move; a project that still wires
  it sees Claude Code report the missing script until `docs/tasks/settings.json` is applied.

## The deny list's `*`

A `*` in a `Bash(...)` rule matches any text, so a rule like `Bash(rm -rf /` + `*)`
refuses every absolute path, not only the root. The list keeps exact rules for the root,
the home directory and `$HOME`; the catastrophic literals a rule cannot express exactly
(`/*`, `./*`) are refused by `block-dangerous.sh`. `evals/permission_rules.py` is a
reference matcher for the documented semantics; `tests/test_root_delete_deny.py`
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

## What the overseer is shown of a gate exemption, and what closes an escalation

The bypass guard accepts a `gate-allow` by the shape of its reason; `gate_allows.py` lays every
such exemption before the overseer, who judges it (check #4). What that rests on:

- **The collector reads three kinds of file**: `.py` (comment tokens), the lint / type
  configuration files the guard watches, and slice contracts. Those are the only places the
  guard honours a marker, so a marker anywhere else exempts nothing and is not listed. A project
  whose checks are not Python's (`LINT_CMD` for another language) has suppressions the guard
  itself does not see; neither does the collector.
- **Judged means shown at an audit request and passed.** Both records live in
  `.claude/state/overseer/`. Machine state is protected from the agent's edit tools, not from a
  script the agent writes; an agent that rewrites it is doing something no rule permits, and it
  shows in the transcript. A by-hand audit ("run overseer") records nothing, so its exemptions
  are listed again at the next hook-requested audit — the safe side.
- **On the main branch with nothing judged yet the base is HEAD**, so there a commit would hide
  an exemption; the commit policy refuses an agent's commit on that branch, which is what keeps
  this closed.
- **The judgement is a model's.** The script guarantees the overseer was shown the exemption;
  it does not guarantee the verdict. Audit scenario 11 measures how often a weak reason is
  blocked.
- **An open escalation is closed by `gate.py --close-escalation`**, which refuses when
  `CLAUDECODE` is set — every shell the agent's tools start has it. An agent that clears the
  variable on purpose can run the command; that is a deliberate, visible act, not a routine edit
  of the park queue, which is what closed the question before.
- **The lock is keyed on files, so it is wide.** The slice's name is the agent's to write
  (`.engine/PROGRESS.md`), the diff is not. An escalation therefore holds every PASS while the
  files the gate blocked on are in the range no accepted PASS has covered — in practice all work
  on the branch until the owner closes it or the escalated changes are set aside uncommitted. The
  owner's "for this slice" is met in the strict direction: the slice cannot pass, and neither can
  anything stacked on its unanswered files.
- **The collector sees what the guard sees.** `.sh`, `.pyi`, `setup.cfg`, a `conftest.py`
  `collect_ignore`: the bypass guard does not watch them, so no gate-allow can exist there to
  hide. That is a limit of the gate (package 7), unchanged here.
- **`needs_audit.py` knows paths, not words.** A hook that changes the sentence it shows the
  model is reported as `MAYBE`; whether an audit is due is then a reading of the diff.
