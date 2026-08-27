# PROGRESS

Half of the supervisor's liveness signal (`last_life()` takes the newer of this
file's mtime and the heartbeat), so it is not decoration: while it was absent,
`mtime()` returned 0 and stall detection rested on the heartbeat alone.

## Feature: harness-hardening (2026-08-27)

| Node | What it settled |
|---|---|
| S1 | Verdict markers anchored so prose cannot trigger the continue loop |
| S2 | AGENTS.md filled — it loads into every session, placeholders included |
| S3 | format-on-edit / verify-on-stop defects found and patched (22/0, 5/0) |
| S4a | `session-claude.sh` proven on the real path |
| S4b | Supervisor proven crossing a node boundary with real sessions |
| S5 | `project.env` writable under protect-paths without widening the deny list |
| S6 | Supervisor mutual exclusion + the orphaned-grandchild fix |
| S7 | Evasion gaps in `block-dangerous.sh` closed; its mirror defect documented |

## What running it for real cost, and bought

Two prior proofs passed and the harness still could not run unattended. Three
defects were reachable only by running the production path:

- **D-19** every real session was handed the literal `{NODE}` and never learned
  which node it was building. Bash closes a parameter expansion on the
  placeholder's own brace inside `${VAR:-default}`. Both earlier proofs exported
  `SESSION_PROMPT` explicitly, so the one path every production run takes was the
  one path never exercised.
- **D-20** the Stop hook's only continuation branch required an `OVERSEER_PASS`,
  which required an audit, which required an edit under `SOURCE_DIRS="src"` — and
  this repo deliberately has no `src/`. The autonomous loop was structurally dead
  here while reading as fully configured.
- **S6** a SIGTERM to a session wrapper orphaned its headless child, which kept
  editing the repo while the supervisor believed the node was free.

The pattern in all three: a fixture replaced exactly the component whose real
behaviour was wrong.

## The one manual step left

Commits onto `unattended/<date>` are implemented, tested 11/11, and enforced by
the hook -- but still blocked by one line the AI deliberately cannot reach. In
`.claude/settings.json`, `permissions.deny` contains:

    "Bash(git commit*)"

Deny beats allow, so nothing in `settings.local.json` can override it, and D-23
made `settings.json` unwritable by the AI on purpose. Replace that entry with the
branch-scoped pair:

    "Bash(git commit*)"        ->  remove
    add to permissions.ask:        "Bash(git commit:*)"   # optional, prompts when attended

or simply delete the deny line and rely on `block-dangerous.sh`, which refuses a
commit on every branch except `unattended/*` and fails closed when the branch
cannot be read.

Recommended: delete the deny line. The hook is the tighter control of the two --
it is branch-aware, and it already covers the compound and `-C` forms that the
glob `git commit*` never did.

## Open for next slice

- **`block-dangerous.sh` still matches inside quoted literals and heredoc
  bodies**, so documenting a dangerous command is blocked as if running it. Left
  unfixed deliberately (see the hook header): separating a real invocation from a
  quoted mention needs shell parsing, and the shortcut of stripping heredoc
  bodies opens a real hole, because a heredoc fed to a shell executes. For a deny
  control a false positive is a nuisance and a false negative is a breach.
- `ruff` and `mypy` are absent on this machine; `uvx` is the workaround S3 used.
- `.claude/overseer/.continue_count` is shared between the orchestrator and any
  spawned session. Harmless today because spawned sessions leave that branch
  early, but it is a shared mutable path.
- The `.claude/` sensitive-path classifier blocks a spawned session from writing
  its own fixes. Session S3 could find and prove four defects but not apply them;
  it staged a patch instead and parked. That is the right shape, but it means an
  overnight run repairs nothing without a human or an orchestrator with rights.
- One hunk of that staged patch was a regression (a command substitution whose
  stdout was redirected away, emptying the value). Review patches from unattended
  sessions before applying: they are proven against copies, not against intent.
