# Tasks for the owner's hands

Files here are complete proposals the engine prepared but may not apply itself:
`protect-paths.sh` refuses `.claude/settings.json`, `.claude/settings.local.json` and
`.claude/constitution.md` to any agent, on purpose. Each proposal comes with the test that
checks exactly it and the one command that applies it.

## `settings.json` — the shared layer after the split (package 3b, S1/S4)

What changed against the live `.claude/settings.json`, and why:

- **Removed, moved to the personal layer `user/settings.json`:** `permissions.defaultMode`
  (there as `auto`, legal at the user level only), `permissions.additionalDirectories` (the
  owner's home directories and `/tmp/claude/`), `WebFetch` and `WebSearch` from
  `permissions.allow`. These are one person's choices; a project that installs the engine
  should not inherit another person's home directories. At the user level they apply in
  every directory, which is where they were meant to apply.
- **Removed, not moved:** the four model variables under `env` (`ANTHROPIC_DEFAULT_*_MODEL`,
  `CLAUDE_CODE_SUBAGENT_MODEL`). Pinning a model id freezes an old model, and
  `CLAUDE_CODE_SUBAGENT_MODEL` is not documented (fix round, item 4).
- **Kept:** the `allow` / `ask` / `deny` lists, every hook, `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`.
- List keys merge across levels and scalars fall through to the user level, so the split
  itself changes nothing in effect (`evals/settings_parity.py`: 13 of 13 identical on
  2026-10-02 against the real `~/.claude/settings.json`). The fix round then changed two
  things ON PURPOSE — `defaultMode` to `auto` and the model variables gone — and
  `tests/test_settings_proposal.py` lists each such difference from the frozen
  "before" (`effective-before-split.json`) with its reason.

Apply, from the repository root:

```bash
cp docs/tasks/settings.json .claude/settings.json && python3 tests/test_settings_proposal.py
```

The test passes both before and after applying: it compares the proposal plus the personal
layer against the frozen "before", and once the live file equals the proposal it says so.
Restart Claude Code afterwards: settings are read at session start.

Then install the personal layer into your home settings (dry-run first; a backup is written
next to the file before it changes, and a second run changes nothing):

```bash
python3 engine.py install --personal --ref <this branch or tag> --dry-run
python3 engine.py install --personal --ref <this branch or tag>
```

### The deny list after S4 — what changed and why

Claude Code's `*` in a Bash rule matches any text (code.claude.com/docs/en/permissions), so
`rm -rf /` followed by `*` also refused `rm -rf /tmp/claude/scratch`, and `./` followed by
`*` refused `rm -rf ./build`. `block-dangerous.sh` already refuses the catastrophic forms
with patterns that tell `/` from `/tmp/...` and `./*` from `./build`, so the list now says:

| was | is | the catastrophic literal is refused by |
|---|---|---|
| `Bash(rm -rf /` + `*)` | `Bash(rm -rf /)` (exact) | the hook, for `rm -rf /*` |
| `Bash(rm -r /` + `*)` | `Bash(rm -r /)` (exact) | the list (exact) |
| `Bash(rm -rf ./` + `*)` | removed | the hook, for `rm -rf ./*` |
| `Bash(rm -fr *)` (every `rm -fr`) | the same rules as `-rf`, spelled `-fr` | both, symmetrically |

`tests/test_root_delete_deny.py` shows the result with the deny list and the hook
together: `rm -rf /`, `rm -rf /*`, `rm -rf ~`, `rm -rf $HOME` and their `-fr` twins
refused; a temporary directory by its absolute path, `./build`, `.venv` let through. The
reference matcher is `evals/permission_rules.py`.

## `settings.json` — unwire the retired `approve-project-data.py` (package 3c, item 5)

Package 3c moved everything the agent produces out of `.claude/` into `.engine/`, which
Claude Code does not protect. `approve-project-data.py` approved writes to project-owned
paths UNDER `.claude/`; none exist there any more, so the hook is deleted and the proposal
drops its `PermissionRequest` handler — nothing else in the hooks block changes
(`tests/test_settings_proposal.py` asserts exactly that). The live file still carries
the handler from F8; until it is applied, Claude Code reports the missing script once per
Edit/Write/MultiEdit permission request. Apply, from the repository root, then restart:

```bash
cp docs/tasks/settings.json .claude/settings.json && python3 tests/test_settings_proposal.py
```

## `settings.json` — the stuck counter's wiring (package memory, board 008)

Everything of the lesson queue rides on hooks that are already wired (the Stop gate collects and
feeds the stuck counter, the overseer hook queues `OVERSEER_BLOCK` and asks for the review after a
PASS, the SessionStart hook `env-check.sh` carries the digest). One thing needs a new entry in
`.claude/settings.json`, which an agent may not edit: the stuck counter on **Bash results**
(`PostToolUse` matched `Edit|Write|MultiEdit` only; a failed Bash call arrives as
`PostToolUseFailure`). Without it the counter still sees repeated gate failures (post-write lint,
Stop blocks) — only a command that fails three times in a row goes unnoticed.

The proposal carries both groups: `lesson_queue.py stuck` on `PostToolUse` and on
`PostToolUseFailure`, matcher `Bash`, timeout 5 s. `tests/test_settings_proposal.py` lists them
as the intended difference from the state before the split (the owner's decision of
2026-10-03) and allows no other. Apply, from the repository root, then restart Claude Code:

```bash
cp docs/tasks/settings.json .claude/settings.json && python3 tests/test_settings_proposal.py
```

If your Claude Code version has no `PostToolUseFailure` event the `PostToolUse` group alone still
counts non-zero exit codes it can see; the unknown event is ignored.

## `settings.json` — the overseer as a separate agent (board 015 / 018)

Every audit is done by the agent `overseer` in a fresh context, and its verdict is written by a
script. That script, `.claude/hooks/overseer_verdict.py`, works through two handlers the proposal
adds — and through nothing else:

- `PreToolUse`, matcher `Agent|Task|Edit|Write|MultiEdit|NotebookEdit`: `overseer_verdict.py guard`.
  Starts the agent `overseer` only for the pending audit request and only with the prompt
  `OVERSEER_REQUEST <id>`; inside that agent refuses every editing tool. For every other call it
  decides nothing.
- `SubagentStop`, matcher `overseer`: `overseer_verdict.py record`. Checks the agent's answer
  (schema, the tree's fingerprint, the contract's sha256, the gate's open escalation) and writes
  the ledger entry.

Until this is applied the Stop hook keeps the former protocol — the session audits itself and
its `OVERSEER_PASS` continues — so nothing is left without an audit in between;
`python3 .claude/hooks/overseer_verdict.py status` says which protocol is in force. Once applied,
`OVERSEER_PASS` typed by the builder is refused. `tests/test_settings_proposal.py` lists the two
handlers as the intended difference and allows no other; `tests/test_overseer_fresh.py` shows every
protection with its negative case. Apply, from the repository root, then restart Claude Code:

```bash
cp docs/tasks/settings.json .claude/settings.json && python3 tests/test_settings_proposal.py
```

## `complexity-thresholds.md` — the default complexity limits (board 010)

The simplifier's signals and the complexity budget measure new and worsened functions against
`COMPLEXITY_MAX_CYCLOMATIC` and `COMPLEXITY_MAX_NESTING` in `.claude/project.env`. The proposal
holds the numbers calibrated on this repository's own functions and the one command that
applies them; `tests/test_complexity_budget.py` checks the command.

No change of `.claude/settings.json` came with the simplifier: its signals ride on the Stop
gate, and `complexity_budget.py hook` was wired already.

## One way to apply, and who may take it

`docs/tasks/settings.json` is the only place a change of the shared settings is proposed, and
the `cp` above the only way it is applied — there is no merge script and no fragment beside it
(`apply-lesson-hooks.py` wrote the live file directly, which left this proposal behind and its
test red). The owner types the command, or answers `так` on the task board under a question
that offers it: `board-runner.sh` then runs exactly this through
`.claude/unattended/owner_action.py`, for exactly the proposal the question named (its sha256
is in the offer), puts the previous file back if the test goes red, and commits the applied
file. No agent can: `protect-paths.sh` refuses the file, and `owner_action.py` refuses inside a
Claude Code session.
