# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-03 | parked | S4b | S4b: permission to launch `.claude/unattended/supervisor.sh`, which spawns `claude` subprocesses in a self-restarting loop. The auto-mode classifier denies it. #ccb98aa5
- 2026-10-03 | parked | S3 | S3: S3 has no DAG node to plan from — there is no feature artifact defining it, and no S2 to inherit an edge from. #9d8c37a8
- 2026-10-03 | parked | engine-package-3b-/-S7-apply-shared-settings | engine-package-3b / S7 apply-shared-settings: copying docs/tasks/settings.json over .claude/settings.json — protect-paths.sh refuses that path to any agent, by design (D-23). #46dd65c3
- 2026-10-03 | parked | engine-package-3b-/-S8-apply-personal | engine-package-3b / S8 apply-personal: a real write under ~/.claude — the run may only dry-run there (plan, step 9). #50754466
- 2026-10-03 | parked | engine-package-3b-/-S9-cloud-probe | engine-package-3b / S9 cloud-probe: facts only a real cloud session can produce (which branch it checks out, the remote, whether CLAUDE_CODE_REMOTE is set as documented, which settings files are prese #6b868763
- 2026-10-03 | parked | engine-package-3b-finish-/-F8-wire-approve-project-data | engine-package-3b-finish / F8 wire-approve-project-data: adding the PermissionRequest handler for approve-project-data.py to .claude/settings.json — protect-paths.sh refuses that path to any agent, by #923e5a04
- 2026-10-03 | parked | engine-package-3c-/-C8b-post-move-audit-run | engine-package-3c / C8b post-move audit run: money. The plan caps both audit runs at $60; spent so far: $8.93 (contaminated pre-move run) + $27.92 (valid pre-move run) + about $25 (post-move attempt t #44f078d9
- 2026-10-03 | parked | engine-package-3c-/-C9-apply-settings | engine-package-3c / C9 apply-settings: applying docs/tasks/settings.json (the approve-project-data handler removed) to .claude/settings.json — protect-paths.sh refuses that path to any agent, by desig #e3ddd563
- 2026-10-03 | parked | engine-package-2b-/-N1-night-program | engine-package-2b / N1 night program: the file ~/engine-night/night-1.md, which the owner named as the program to run after the report; it does not exist on this machine. #d4a20bf6
- 2026-10-03 | parked | B-wiring-stuck-bash | B-wiring-stuck-bash: `.claude/settings.json` is owner-only (protect-paths.sh) and the stuck counter on Bash results needs a PostToolUse / PostToolUseFailure entry for `Bash` #85035483
- 2026-10-03 | escalation | - | CAPABILITY_GRANT harness self-repair #ce3ba4a1
- 2026-10-03 | escalation | - | PRODUCT_DECISION commits during an overnight run — CLOSED #ba8b2e15
- 2026-10-03 | escalation | - | FINDING Write(...) deny rules are inert #5362a4ad
- 2026-10-03 | escalation | - | FINDING decana dry run exits 1 for a reason outside this round #053967a2
- 2026-10-03 | escalation | - | FINDING SOURCE_DIRS with a multi-segment entry was inert on absolute paths #de33f5e2
- 2026-10-03 | escalation | - | FINDING item 9's "45 mypy findings" were 9 #91b75629
- 2026-10-03 | escalation | - | FINDING a suite can be green by hand and red from the Stop gate #d92e8dfa
- 2026-10-03 | escalation | - | FINDING decana carries the old rules inline, partly edited #d0ea75d8
- 2026-10-03 | parked | N0.3-full-audit | N0.3-full-audit: the headless Claude Code sessions of the audit are not logged in on this machine (`claude auth status` → loggedIn false; every run ended "Not logged in · Please run /login"); a creden #563e9aa9
