# Template setup guide

This repo is a reusable Claude Code configuration template. `engine.py` installs it into
any project with one command; the steps after that tailor it. The whole setup takes about
15 minutes.

---

## What you get

- **Slice flow**: design (master-architect) → build (slice-builder) → audit (overseer).
- **Memory lifecycle**: self-learning-orchestrator distils lessons across sessions.
- **9 hooks**: block dangerous commands (with the commit policy by environment), protect
  sensitive paths, format on edit, verify on stop, auto-approve web fetches, trigger the
  overseer audit on unit completion, park ask-gated commands when unattended, the
  complexity budget, and a session-start check of what the machine lacks. They are wired by
  the project's `settings.json` only — never from `~/.claude/` (`docs/engine-limits.md`).
- **Two directories**: `.claude/` holds what defines and constrains the agent and is
  protected by Claude Code; `.engine/` holds what the agent produces while working (the
  overseer's records, slice contracts, architecture, premises, spikes, `PROGRESS.md`) and
  is not. Machine state lives under `.claude/state/`, written by hooks and scripts only.
- **Critic agents**: slice-planner-critic, feature-critic, master-critic — adversarial
  review before implementation begins.

---

## Where it runs

Linux and macOS. On Windows the engine runs inside WSL2 (Ubuntu), where it behaves as on any
Linux; native Windows (Git Bash, PowerShell) is not supported. `docs/WINDOWS.md` sets a Windows
machine up from nothing, step by step. The machine needs `git`, `python3` and, preferably, `jq`;
the session-start check `env-check.sh` names what is missing and, under WSL, the two usual
traps — a project on a Windows disk (`/mnt/c/...`) and git rewriting line endings.

---

## Step 1 — Install the engine

```bash
python3 /path/to/claude-cli-config/engine.py install /path/to/your-project
```

That is the whole installation. Everything is read from one git tag of this repository
(the newest `v*`; `--ref <tag, branch or commit>` picks another), never from its working
tree, so the same command gives the same result on any machine. `.claude/ownership.txt`
decides what happens to each path:

- **engine** files are copied in, with their executable bits;
- **project** files are created once from a clean seed when the project lacks them —
  `CLAUDE.md` and `AGENTS.md` (from `templates/project/`), `.claude/project.env`, the
  overseer's ledger, audit, escalations, parked queue and memory, the premise log — and
  never overwritten after (one exception: the marked block in CLAUDE.md, Step 4);
- **machine** state is never copied; its patterns go into a marked block of the
  project's `.gitignore`.

The project gets `.claude/engine-lock.json`: the installed ref, its commit and the git blob
id of every engine file. Commit it with the rest — it is how a later update tells an
untouched engine file from one you changed. `engine.py` never commits; review the result
with `git status`.

`--dry-run` prints the plan and writes nothing. A project that already holds a copy made
by hand (`cp -r .claude`) is adopted by the same command: untouched engine files are
recognised against the engine's history and updated, edited ones are kept and reported.

---

## Step 2 — Configure `.claude/project.env`

This is the most important step. Open `.claude/project.env` and set the values for
your project's language and toolchain. Every hook reads this file at runtime.

### Full variable reference

| Variable | What it controls | Default when empty |
|---|---|---|
| `SOURCE_DIRS` | Dirs that count as "code" for overseer trigger | Any file matching `CODE_EXTENSIONS` |
| `CODE_EXTENSIONS` | File extensions that are "code files" (space-sep, no dot) | All changed files |
| `CHECK_CMDS` | Verification command names for overseer trigger (space-sep) | Built-in broad set: `pytest ruff mypy npm jest vitest go cargo swift` |
| `PROJECT_MARKER` | File that must exist before lint, types and tests run (the bypass guard runs without it) | Always verify |
| `LINT_CMD` | Lint command for verify-on-stop | Python auto-detect (ruff) |
| `TYPECHECK_CMD` | Type-check command for verify-on-stop | Python auto-detect (mypy) |
| `TEST_CMD` | Test command for verify-on-stop | Python auto-detect (pytest -x) |
| `FORMAT_CMD` | Format command for format-on-edit (`{file}` = file path) | Python auto-detect (ruff) |
| `PUSH_PROTECTED_BRANCHES` | Branches `block-dangerous.sh` refuses a push into (space- or comma-separated); a project that releases from `master` or `production` names them here | `main stable` |

### Behavior when a variable is not set

- **`SOURCE_DIRS` empty**: any code-file edit triggers the overseer (more permissive).
- **`CODE_EXTENSIONS` empty**: all changed files are treated as code — verification
  always runs, format-on-edit falls through to built-in handlers.
- **`CHECK_CMDS` empty**: the overseer's built-in broad set covers most stacks.
- **`PROJECT_MARKER` empty**: checks always run (don't skip on first clone).
- **`LINT_CMD` / `TYPECHECK_CMD` / `TEST_CMD` all empty**: Python auto-detect path.
  If your `CODE_EXTENSIONS` includes non-Python extensions (e.g. `ts`) but no
  check commands are set, the hook prints a **clear warning** and skips — no silent pass.
- **`FORMAT_CMD` empty**: built-in Python auto-detect (ruff/black) and generic
  handlers (json/md/yaml via prettier) remain active.
- **`FORMAT_CMD="true"`**: no file is formatted after an edit, whatever its extension — the
  built-in handlers included, so a formatter that merely happens to be installed never rewrites
  a whole file for a one-line edit (the engine's own setting, board 749).

### List format: `SOURCE_DIRS`, `CODE_EXTENSIONS`, `CHECK_CMDS`

These three accept space- **or** comma-separated values, with or without
leading dots on extensions — `"ts tsx"`, `"ts,tsx"`, and `".ts,.tsx"` all
parse identically. If a value doesn't parse into anything usable (e.g. it's
just punctuation), every hook prints an explicit warning and falls back to
the "unset" behavior for that variable — it never fails silently.

### Examples by stack

**Python (default, no changes needed if using ruff + mypy + pytest):**
```bash
SOURCE_DIRS="src"
CODE_EXTENSIONS="py"
PROJECT_MARKER="pyproject.toml"
# LINT_CMD / TYPECHECK_CMD / TEST_CMD — leave empty for auto-detect
```

**TypeScript / Node:**
```bash
SOURCE_DIRS="src"
CODE_EXTENSIONS="ts tsx"
PROJECT_MARKER="package.json"
LINT_CMD="npm run lint"
TYPECHECK_CMD="npx tsc --noEmit"
TEST_CMD="npm test"
FORMAT_CMD="npx prettier --write {file}"
```

**Go:**
```bash
SOURCE_DIRS="."
CODE_EXTENSIONS="go"
PROJECT_MARKER="go.mod"
LINT_CMD="golangci-lint run ./..."
TYPECHECK_CMD=""
TEST_CMD="go test ./..."
FORMAT_CMD="gofmt -w {file}"
```

**Monorepo (multiple source roots):**
```bash
SOURCE_DIRS="backend/src frontend/src"
CODE_EXTENSIONS="py ts tsx"
```

---

## Step 3 — Tailor `.claude/settings.json` and copy env overrides (optional)

### Shared and personal: what lives where

The engine's settings come in two layers, and the split is what lets one `settings.json`
ship into every project without carrying one person's preferences along:

| layer | file | holds | applies |
|---|---|---|---|
| **shared** | `.claude/settings.json` (engine file, ships into every project) | the `allow` / `ask` / `deny` lists, every hook, the engine's own `env` (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`) | in that project |
| **personal** | `user/settings.json` in the engine repository → merged into `~/.claude/settings.json` | `permissions.defaultMode` (`auto` — legal at the user level only), your `additionalDirectories`, a blanket `WebFetch`/`WebSearch` allow. No model variables: pinning a model id freezes an old model | in every directory on your machine |
| machine-local | `.claude/settings.local.json` (gitignored) | per-machine, per-project overrides | in that project, on that machine |

Nothing changes in effect: Claude Code merges list keys across levels and takes a scalar
from the highest level that sets it (user < project < local), so a `defaultMode` at the
user level is what the project sees unless the project sets its own.
`evals/settings_parity.py compare` shows the effective settings identical before and after
the split.

Install the personal layer with the engine itself — never by hand:

```bash
python3 /path/to/claude-cli-config/engine.py install --personal --dry-run   # the plan, nothing written
python3 /path/to/claude-cli-config/engine.py install --personal             # merge into ~/.claude/settings.json
```

Keys the layer names are set, lists gain only what they lack, every key the file already has
and the layer does not name is kept, a backup (`settings.json.engine-backup-<UTC>`) is
written next to the file before it changes, and a second run changes nothing. `--home DIR`
or `CLAUDE_CONFIG_DIR` names a different config directory. A layer that wires hooks is
refused: a hook wired at the user level **and** in a project would fire twice per event
(`docs/engine-limits.md`, "One hook, one run per event"). A cloud session does
not read the user level at all, so the personal layer never reaches it; that is correct, the
shared file carries everything a project needs.

Personal **skills** live in `user/skills/` and are deployed with `install.sh` (symlinks into
`~/.claude/skills`). Name a new one `my-<name>`: a personal skill that shares a name with an
engine skill or command would shadow it in every project, and `install.sh` refuses to deploy
such a set.

### The shared `ask` list

`.claude/settings.json`'s `ask` list ships with a neutral cross-language default:
git/gh/docker operations, plus the "add/remove a dependency" command for six
package managers (`uv`, `poetry`, `pip`, `pipx`, `npm`, `yarn`, `pnpm`, `cargo`,
`go`, `gem`, `bundle`). You don't have to edit this — unused entries are inert,
they only prompt if you actually run that command. Trim it if you want a
shorter approval list:

| Your stack | Safe to remove from `ask` |
|---|---|
| Python only | `cargo add/remove`, `go get/mod tidy`, `gem install`, `bundle add/remove` |
| JS/TS only | all `uv/poetry/pip/pipx`, `cargo`, `go`, `gem`, `bundle` entries |
| Go only | all `uv/poetry/pip/pipx`, `npm/yarn/pnpm`, `cargo`, `gem/bundle` entries |
| Rust only | all `uv/poetry/pip/pipx`, `npm/yarn/pnpm`, `go`, `gem/bundle` entries |

Trimming makes `settings.json` a file the project changed: from then on `engine.py update`
reports it instead of updating it (see *Keeping the engine up to date*).

Also copy the local-machine env override template:

```bash
cp /path/to/your-project/.claude/settings.local.json.example \
   /path/to/your-project/.claude/settings.local.json
```

Open it and keep only the section for your language (e.g. `_python` for
`PYTHONPYCACHEPREFIX`), moving its `env` block up to a real top-level `"env"`
key — the `_python`/`_javascript`/`_rust` wrapper keys are inert labels, not
real settings. Example for a Python project:

```json
{
  "env": {
    "PYTHONPYCACHEPREFIX": ".cache/pycache"
  }
}
```

`settings.local.json` is gitignored — it never leaves this machine.

---

## Step 4 — Write your `CLAUDE.md`

The install seeded `CLAUDE.md` from `templates/project/CLAUDE.md`: a marked block that imports
the engine's standing rules, an `@AGENTS.md` line, and a few placeholder lines for your
project. The block —

```
<!-- >>> engine: ... -->
@.claude/engine-rules.md
<!-- <<< engine -->
```

— is the engine's: `engine.py update` rewrites what is between the markers when the engine
changes the import, and never touches a byte outside them. Everything below the end marker is
yours. Replace the placeholders with your project's name, purpose, stack commands and the
conventions every agent must know by default. Keep it short: CLAUDE.md, AGENTS.md and
everything they import are loaded into every session, and the engine budgets 200 lines for
the lot (the rules file takes about 90). Detail that is rarely needed belongs in `docs/`.

Do not copy the rules into CLAUDE.md and do not edit `.claude/engine-rules.md`: the engine
owns that file and replaces it on update. `.claude/references/hooks.md` and
`.claude/references/unattended.md` are the long versions, read on demand.

**A project that installed an earlier engine** has the old rules inline in its CLAUDE.md.
`engine.py update` reports what to do: an unedited old copy is replaced by the seed with
`--reseed-pristine`; an edited copy is left alone, and the report names the import line to
add and the line ranges that now duplicate `.claude/engine-rules.md` — delete those and keep
your own text.

---

## Step 5 — Write your `AGENTS.md`

Seeded from `templates/project/AGENTS.md` and loaded through `@AGENTS.md`. Fill in the project
sentence, the key paths and the verification commands; keep the pipeline line. Minimal is
right — this file is in every session's context.

---

## Step 6 — Smoke-test the hooks

Run these in the project root to confirm the hooks are wired correctly:

```bash
# 1. Overseer dry-run — must print a BLOCK (that is expected)
python3 .claude/hooks/overseer_stop.py --dry-run <<< '{}'

# 2. Verify-on-stop — exit 0 expected. If you have staged code files it will
#    attempt your LINT_CMD/TEST_CMD; "command not found" is expected when
#    tools aren't installed globally — it means config was read correctly.
echo '{"stop_hook_active":false}' | bash .claude/hooks/verify-on-stop.sh; echo "exit: $?"

# 3. Block-dangerous — must exit non-zero (or print a block decision) for 'git commit'.
#    This tests the hook directly; in a live session `git commit` is also
#    hard-denied in settings.json's permissions.deny before the hook even runs.
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' \
  | bash .claude/hooks/block-dangerous.sh; echo "exit: $?"
```

If hook 1 prints `DRY-RUN: would have blocked`, hooks are wired. Adjust expectations
for hooks 2–3 based on your project state (hook 2 may exit 0 silently if no Python
files are tracked yet).

---

## Step 7 — First session orientation

Start Claude Code in the project root. In the first message, say:

> "New project. Read CLAUDE.md, AGENTS.md, and .claude/README.md. Summarise
> the active agents and what the first thing to do is."

This forces the agent to load the policy and map before doing anything else.

---

## Step 8 — An existing project: `/onboard`

Skip this for a project the engine builds from nothing. For a project that already has code,
steps 2 and 5 are not filled in by hand: the command `/onboard` does it with the owner, in an
interactive session, once.

```bash
cp tasks/TEMPLATE-onboard.md tasks/todo/NNN-onboard.md        # a task that needs the owner present
python3 .claude/unattended/board.py start --attended tasks/todo/NNN-onboard.md
# then, in Claude Code:  /onboard
```

What it does, in order: surveys the project read-only; **runs** every check command it found (a
command that was not run never reaches `project.env`); offers the project's rules as candidates,
each with its source — written, seen in the code, seen in the history; takes the owner's «yes»,
«no» or corrected text on each, and the do-not-touch zones; has a fresh reader check every
reference; then writes the files below. The owner takes the snapshot "as it was" in their own
terminal (`python3 .claude/hooks/baseline.py record`), so the gate asks "no worse than it was".

| File | What it holds |
|---|---|
| `.engine/onboard/profile.md` | the map, the commands with the evidence of their run, every rule with the owner's verdict and source, the risk zones, what was not read. Read on demand (template: `.claude/references/onboard-profile.md`) |
| `AGENTS.md` | only the rules without which any conversation would go wrong; the 200-line limit of the persistent context is the only limit |
| `.claude/project.env` | source dirs, extensions, the verified commands, `SIMPLIFIER_PROTECTED` |
| `.engine/premises/premise-log.md` | what could not be verified |

`/onboard` fixes nothing, installs nothing, reads no secrets and writes no decisions in hindsight.
Without the owner it does the survey, the command check and the candidates, and stops with
questions. A project installed before this command existed has no `tasks/TEMPLATE-onboard.md`
(seeds are copied once): take it from `templates/project/tasks/` of the engine.

---

## What happens if you skip a step?

| Skipped step | Consequence |
|---|---|
| Step 2 (project.env) | File ships with `SOURCE_DIRS="src"` and `CODE_EXTENSIONS="py"` pre-filled — overseer triggers on `src/` edits, verify-on-stop runs Python auto-detect. Non-Python stacks work if their check commands are in the built-in broad set (`npm jest vitest go cargo swift`); verification silently skips if no `pyproject.toml` found |
| Step 3 (settings.json / settings.local.json) | `ask` list stays broader than necessary (harmless, just extra prompts); no PYTHONPYCACHEPREFIX / CARGO_TARGET_DIR override — build caches may land inside tracked dirs |
| Step 4 (CLAUDE.md) | Agents use the generic template policy — safe but not project-aware |
| Step 5 (AGENTS.md) | Agents lack project context; slice-planner-critic may misfire on scope |
| Step 6 (smoke test) | You discover broken hooks in production, not during setup |
| Step 7 (orientation) | Agent starts with no context; first actions may be off-target |

---

## Directory reference (after setup)

```
.claude/
  project.env     — ← fill this in (Step 2)
  hooks/          — 9 enforcement hooks (wired in settings.json)
  skills/         — vendored skills: overseer, slice-builder, master-architect,
                    feature-architect, self-learning-orchestrator, documentation,
  agents/         — critic subagents: slice-planner-critic, feature-critic,
                    master-critic, critic-core
  commands/       — project commands: plan-slice, master-architect, feature-architect, onboard, bugfix, hotfix, maintain
  templates/      — slice-contract.md, the shape /plan-slice writes; bug-record.md, the shape /bugfix writes; hotfix-record.md, the card of /hotfix
  references/     — reference materials for agents (ADR format, C4, permission philosophy)
  unattended/     — the task board's runner and its helpers
  state/          — MACHINE STATE, written by hooks and scripts only; gitignored as one line
                    (overseer/ guards, mode and budgets; board/ status, costs, logs;
                    contracts/ the sealed fingerprints of approved slice contracts)
  README.md       — agentic system map (read this before adding a new agent)
  settings.json   — hook wiring and permissions
  settings.local.json.example — ← copy to settings.local.json, trim to your stack (Step 3)
  constitution.md — load-bearing rules every agent must follow
  ownership.txt   — who owns each path: engine, project, machine (read by engine.py)
  engine-lock.json — installed ref, commit and checksums (written by engine.py; commit it)

.engine/            — WHAT THE AGENT PRODUCES; not protected by Claude Code, that is the point
  overseer/       — ledger, audit, escalations, parked queue, MEMORY (seeded once)
  slices/         — slice contracts written by /plan-slice
  architecture/   — design artifacts and the feature DAG (created on first use)
  premises/       — premise log (seeded once)
  onboard/        — profile.md, the project's profile written by /onboard (existing projects only)
  bugs/           — bug records written by /bugfix, and the cards of urgent fixes (/hotfix): the contract and the report of each fix
  debt.md         — what urgent fixes put off: one line each, written and closed by hotfix.py, term seven days
  maintain/       — the reports of /maintain (<date>.md), the list the owner is asked about (updates.json),
                    what the runner's update did (update-result.md)
  artifacts/      — spikes, notes (created on first use)
  PROGRESS.md     — slice completion history (created by slice-builder; gitignored)

CLAUDE.md         — the marked block importing .claude/engine-rules.md, then your text
AGENTS.md         — agent roster and project context (loaded via @AGENTS.md)
```

---

## Keeping the engine up to date

How a new version comes to exist — the tag, `main` and `stable` — is `docs/release.md`.

```bash
git -C /path/to/claude-cli-config pull --tags                     # the new versions
python3 /path/to/claude-cli-config/engine.py status /path/to/your-project
python3 /path/to/claude-cli-config/engine.py update /path/to/your-project --dry-run
python3 /path/to/claude-cli-config/engine.py update /path/to/your-project
python3 /path/to/claude-cli-config/engine.py update --all         # every project `install` listed
```

An update replaces an engine file only while the project has not changed it, adds what is
new and removes what the engine retired. A file the project edited is **kept** and reported
(exit status 1); once you have merged what you need, `--take <path>` applies the engine's
version. Project files are never touched. `--reseed-pristine` replaces project files that
are still unedited copies of an older engine version with their clean seed — in a copy made
with `cp -r`, the overseer's ledger, audit, escalations and memory hold this repository's
own records, not the project's. The list for `--all` is
`~/.config/claude-engine/projects.txt`.

**A project built before package 3c** keeps its ledger, parked queue, slice contracts,
architecture, premises, spikes and `PROGRESS.md` where the old engine put them, under
`.claude/`. `engine.py update` (and `install` on a copy without a lock) MOVES them to
`.engine/` by the explicit table in `engine.py`, file by file, and prunes the emptied
directories; `--dry-run` lists every move first. A file that exists in both places is left
alone and reported (`keep … exists in both places`) — merge it by hand and run the update
again. The moves apply only when the ref you update to knows the new layout, so updating to
an older engine never half-migrates a project. Machine state at the old paths is not moved:
it is regenerated, and `.claude/state/` is where it lives now.

Machine-local tweaks belong in `.claude/settings.local.json`, which never ships and never
blocks an update. Personal preferences belong in the personal layer (Step 3), installed with
`engine.py install --personal`, which is as repeatable as a project install: a new engine
version with a changed `user/settings.json` is applied by running it again.

What the guarantees assume, and where they stop (one session, one repository; hooks guard
tool calls, not scripts; the deny list's `*`): `docs/engine-limits.md`.
