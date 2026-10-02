# Tasks for the owner's hands

Files here are complete proposals the engine prepared but may not apply itself:
`protect-paths.sh` refuses `.claude/settings.json`, `.claude/settings.local.json` and
`.claude/constitution.md` to any agent, on purpose. Each proposal comes with the test that
checks exactly it and the one command that applies it.

## `settings.json` — the shared layer after the split (package 3b, S1/S4)

What changed against the live `.claude/settings.json`, and why:

- **Removed, moved to the personal layer `user/settings.json`:** `permissions.defaultMode`
  (`acceptEdits`), `permissions.additionalDirectories` (the owner's home directories and
  `/tmp/claude/`), `WebFetch` and `WebSearch` from `permissions.allow`, and the four model
  variables under `env` (`ANTHROPIC_DEFAULT_*_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`). These
  are one person's choices; a project that installs the engine should not inherit another
  person's home directories or model aliases. At the user level they apply in every
  directory, which is where they were meant to apply.
- **Kept:** the `allow` / `ask` / `deny` lists, every hook, `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`.
- Nothing is lost on the owner's machine: list keys merge across levels and scalars fall
  through to the user level, so `evals/settings_parity.py` shows the effective settings
  identical before and after (13 of 13 on 2026-10-02, against the real
  `~/.claude/settings.json`). The frozen "before" is `effective-before-split.json`.

Apply, from the repository root:

```bash
cp docs/tasks/settings.json .claude/settings.json && python3 hook-checks/test_settings_proposal.py
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

`hook-checks/test_root_delete_deny.py` shows the result with the deny list and the hook
together: `rm -rf /`, `rm -rf /*`, `rm -rf ~`, `rm -rf $HOME` and their `-fr` twins
refused; a temporary directory by its absolute path, `./build`, `.venv` let through. The
reference matcher is `evals/permission_rules.py`.
