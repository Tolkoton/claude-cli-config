# Template setup guide

This repo is a reusable Claude Code configuration template. Copy it into any project
and follow these steps. The whole setup takes about 15 minutes.

---

## What you get

- **Slice flow**: design (master-architect) → build (slice-builder) → audit (overseer).
- **Memory lifecycle**: self-learning-orchestrator distils lessons across sessions.
- **6 hooks**: block dangerous commands, protect sensitive paths, format on edit,
  verify on stop, auto-approve web fetches, trigger overseer audit on completion.
- **Critic agents**: slice-planner-critic, feature-critic, master-critic — adversarial
  review before implementation begins.

---

## Step 1 — Copy the template

```bash
# From the template repo root:
cp -r .claude /path/to/your-project/
cp CLAUDE.md AGENTS.md /path/to/your-project/   # if they don't exist yet
```

Do **not** copy `docs/` — it's template documentation, not project documentation.

---

## Step 2 — Fill in project-specific values

Open `.claude/settings.json` and verify the hook paths are correct (they should be
relative, starting with `.claude/hooks/`). No other changes needed here.

### What to fill in if your project is NOT Python

The hooks default to Python tooling. If your project uses a different language:

| What to change | Where |
|---|---|
| `src/` trigger for overseer audit | `.claude/hooks/overseer_stop.py`, line ~78: `CHECK_PATH_RE` |
| Lint / typecheck / test commands | `.claude/hooks/verify-on-stop.sh`, lines 40–57 |
| File extension for auto-format | `.claude/hooks/format-on-edit.sh`, the `case` block |
| ORM migration paths to protect | `.claude/hooks/protect-paths.sh`, the `PROTECTED` array |

> **Tip:** a future version of this template will centralise these in `.claude/project.env`.
> For now, edit each hook directly — they are short and clearly commented.

### If your project has no code at all (config-only, docs-only)

The verify and format hooks are safe to leave — they check for `pyproject.toml`
before running and silently skip if it is absent. The overseer audit will simply
never fire (it requires edits under `src/`), which is fine for a config repo.

---

## Step 3 — Write your CLAUDE.md

`CLAUDE.md` at the repo root is the standing policy every agent reads. The template
ships with a generic version. Update it with:

- Your project name and one-line purpose.
- Any `alembic/` or `migrations/` paths that should be write-protected (add them to
  `.claude/hooks/protect-paths.sh` under the `PROTECTED` array).
- Anything domain-specific that every agent should know by default.

The format is already established — follow the existing structure.

---

## Step 4 — Write your AGENTS.md

`AGENTS.md` is loaded via `@AGENTS.md` at the start of every conversation. It tells
agents who they are and what the project is. Minimal content:

```markdown
# Agents guide — <project name>

## Project in one sentence
<What the project does.>

## Active agents
- slice-builder (build layer)
- overseer (audit layer)
- self-learning-orchestrator (memory layer)

## Pipeline
Slice flow: master-architect → slice-builder → overseer.
```

---

## Step 5 — Smoke-test the hooks

Run these in the project root to confirm the hooks are wired correctly:

```bash
# 1. Overseer dry-run (should print a BLOCK — that's expected)
python3 .claude/hooks/overseer_stop.py --dry-run

# 2. Protect-paths dry-run (should exit 0 for a safe path)
echo '{"tool_name":"Edit","tool_input":{"file_path":"src/main.py"}}' \
  | python3 .claude/hooks/protect-paths.sh 2>/dev/null; echo "exit: $?"

# 3. Block-dangerous dry-run (should block 'git commit')
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' \
  | bash .claude/hooks/block-dangerous.sh 2>/dev/null; echo "exit: $?"
```

If hook 1 outputs `OVERSEER_BLOCK`, and hooks 2–3 exit as expected, the wiring works.

---

## Step 6 — First session orientation

Start Claude Code in the project root. In the first message, say:

> "New project. Read CLAUDE.md, AGENTS.md, and .claude/README.md. Summarise
> the active agents and what the first thing to do is."

This forces the agent to load the policy and map before doing anything else.

---

## What happens if you skip a step?

| Skipped step | Consequence |
|---|---|
| Step 2 (hook language config) | verify-on-stop silently passes; overseer audit never fires; no real CI enforcement |
| Step 3 (CLAUDE.md) | Agents use the generic template policy — safe but not project-aware |
| Step 4 (AGENTS.md) | Agents lack project context; slice-planner-critic may misfire on scope |
| Step 5 (smoke test) | You discover broken hooks in production, not during setup |
| Step 6 (orientation) | Agent starts with no context; first actions may be off-target |

---

## Directory reference (after setup)

```
.claude/
  hooks/          — 6 enforcement hooks (wired in settings.json)
  skills/         — vendored skills: overseer, slice-builder, master-architect,
                    feature-architect, self-learning-orchestrator, documentation,
                    claude-autonomy
  agents/         — critic subagents: slice-planner-critic, feature-critic,
                    master-critic, critic-core
  commands/       — project commands: plan-slice, master-architect, feature-architect
  overseer/       — audit ledger, escalations, slice contracts
  architecture/   — design artifacts from master-architect (created on first use)
  artifacts/      — spikes, notes (created on first use)
  premises/       — premise log (created on first use)
  references/     — reference materials for agents (ADR format, C4, etc.)
  README.md       — agentic system map (read this before adding a new agent)
  settings.json   — hook wiring and permissions
  constitution.md — load-bearing rules every agent must follow

CLAUDE.md         — standing policy (every agent reads this)
AGENTS.md         — agent roster and project context (loaded via @AGENTS.md)
PROGRESS.md       — slice completion history (created by slice-builder)
```

---

## Keeping the template up to date

The skills in `.claude/skills/` are vendored copies. They do not auto-update.
To pick up improvements from the template repo:

```bash
# Pull the latest template into a temp location
git clone <template-repo> /tmp/claude-template

# Diff and selectively copy updated skills
diff -r /tmp/claude-template/.claude/skills .claude/skills
# Copy specific files you want to update
```

Treat updates as deliberate decisions — inspect the diff, don't blindly overwrite.
