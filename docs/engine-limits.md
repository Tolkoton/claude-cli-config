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
  shows in the transcript. A by-hand audit ("run overseer") marks nothing judged, so its exemptions
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
- **The board runner runs that command on the owner's `закрити`** under the gate's question in
  `tasks/blocked/`. It tells the owner's answer from the agent's by how it arrived: the pull and
  the inbox are the owner's, the checkout is not. That stops an answer typed into the file on
  the server; it does not stop an agent that drops a forged copy into the inbox directory or
  pushes one to the remote by another route — like clearing `CLAUDECODE`, a deliberate act that
  shows in the transcript, not something the runner can see.
- **The runner applies the settings proposal on the owner's `так`** (`owner_action.py`), by the
  same rule for where an answer came from and with the same limit. The offer names the sha256 of
  the proposal, so what is applied is the file the owner was asked about; whether the owner read
  it is not something a script can know. The list of such actions is short and is
  code, not configuration: a task file cannot name a command to run.
- **A lesson becomes a rule only on the owner's `так`** under a rule question in `tasks/blocked/`
  (board 040); the overseer's recommendation opens nothing. The runner acts on it by the same
  rule for where an answer came from, and `lesson_queue.py promote` refuses while `CLAUDECODE` is
  set — with the same limit: an agent that clears the variable on purpose, or forges an answer
  through the inbox, is not something a script can see. `.engine/rules.md` itself is an ordinary
  project file; an edit of it by hand is caught by review of the diff, not by a hook.
- **The lock is keyed on files, so it is wide.** The slice's name is the agent's to write
  (`.engine/PROGRESS.md`), the diff is not. An escalation therefore holds every PASS while the
  files the gate blocked on are in the range no accepted PASS has covered — in practice all work
  on the branch until the owner closes it or the escalated changes are set aside uncommitted. The
  owner's "for this slice" is met in the strict direction: the slice cannot pass, and neither can
  anything stacked on its unanswered files.
- **The collector sees what the guard sees.** `.sh`, `.pyi`, `setup.cfg`, a `conftest.py`
  `collect_ignore`: the bypass guard does not watch them, so no gate-allow can exist there to
  hide. That is a limit of the gate (package 7), unchanged here.
- **`PROJECT_MARKER` and `CODE_EXTENSIONS` are guarded by value, against the turn's base.** A
  change of either blocks unless the sealed contract names the key (board 025). The guard compares
  with HEAD at `stop` and with the index at `pre_commit`: a change committed outside the gate — a
  commit made by a script, with no git pre-commit hook wired — is in HEAD and no longer a diff.
- **`needs_audit.py` knows paths, not words.** A hook that changes the sentence it shows the
  model is reported as `MAYBE`; whether an audit is due is then a reading of the diff.

## The overseer as a separate agent (board 015 / 018)

Every audit is done by the agent `overseer` in a fresh context, and the verdict is written by
`overseer_verdict.py`, not by a model. What that rests on:

- **The builder has to launch the agent.** A hook cannot start a subagent; the Stop hook asks,
  `overseer_verdict.py guard` refuses any prompt but the request line, and a request left without
  a verdict is repeated twice, then parked and the turn ends. An agent that never launches the
  auditor gets no PASS — and no audit either.
- **A hook cannot tell who started it.** The environment of a hook and of the builder's own Bash
  is the same (probed on Claude Code 2.1.288). A builder that pipes a made-up SubagentStop
  envelope into `overseer_verdict.py record`, or writes `.claude/state/overseer/` itself, forges a
  verdict. The rules forbid both and it shows in the transcript; nothing makes it impossible. The
  spare design — the hook starts `claude -p` itself — closes this and was not built (board 015).
- **"Read-only" is checked, not enforced.** The agent has no editing tool and the guard refuses
  one anyway, but it has Bash, to run the tests. The tree is fingerprinted when the agent starts
  and compared when it answers: HEAD, `git status`, the content of every changed or untracked
  file. A change makes the verdict `INVALID`; it is not rolled back. Ignored files (caches,
  `.claude/state/`) are outside the fingerprint, and so is anything outside the repository; a
  project that is not a git repository has no fingerprint at all.
- **The evidence file is as good as the transcript.** `evidence.md` lists the commands of the
  current turn — everything after the last genuine user message; what ran in an earlier turn of
  the same unit is not in it, and the overseer is told to reproduce what matters.
- **An audit asked for by hand** takes the turn from a file. A turn that existed only in the
  conversation is written out by the session that asks — a model in the middle; the recorded
  verdict says `manual`.
- **A project without the two handlers is not audited.** The Stop hook has one protocol; where
  `.claude/settings.json` lacks `overseer_verdict.py guard` and `record` it answers a claim with
  `OVERSEER NOT WIRED` and the unit is parked. `engine.py install` / `update` add them, also to a
  settings file the project edited; a file that is not readable JSON is left alone and the update
  reports the text to add. `python3 .claude/hooks/overseer_verdict.py status` says which it is.
- **Three BLOCKs park a unit by instruction.** The hook tells the builder to move the task to
  `tasks/blocked/` with a question; the move itself is the builder's.

## The simplifier

- **A signal is a lead.** vulture cannot see a name used through a string, a decorator or a
  framework; the unused-dependency check compares the declared name with the imported module
  name and is wrong for a package whose import name differs (`pillow` / `PIL`); pylint's
  duplicate check sees only Python. The signals feed the agent and never remove anything.
- **The verdict on a budget overrun is relayed by the builder.** `simplifier.py accept` checks
  the answer file it is given (schema, nothing above `flag_only`) and records its hash, but it
  cannot know the file is what the `simplifier` subagent really answered. The reason lands in
  the ledger, which the overseer and the owner read; that is the check.
- **`test_safety` is the agent's claim.** The validator refuses `auto_remove` for code with
  `test_safety: none`; whether the named test really covers the removed code is shown by the
  builder (the suite green after the removal), not by the validator.
- **The reversal rate sees commits with the trailer.** A removal committed without
  `Simplifier-Finding:` is not counted, and code that came back reworded (under 60 % of the
  removed lines identical) is not seen as returned.
- **The second opinion sends code to a third party.** With `SECOND_OPINION="on"` the target file
  of each finding and the lines around every occurrence of its names go to Google. On the paid
  tier Google does not use them to improve its products but keeps them for a limited time to
  detect abuse; on the free tier it may use them. Hence a paid-tier key, and `off` in the seed.
- **The second model sees what a text search found.** A user of the target that `git grep` does
  not find by name — a dynamic call, another spelling — is invisible to it too, and a common
  name is shown only in part (the request says how many occurrences were left out). It is a
  second opinion on the same facts, not a second investigation.
- **The key is readable by the agent.** The script and the agent run as the same user; the deny
  hooks stop the agent's tools from reading credentials files, not a script from reading its
  own environment. That is why the key is a separate one with its own spending limit: the worst
  case is the limit spent.
- **The second opinion is relayed by the builder**, like the budget verdict: the record holds
  the hashes of request and response, but nothing proves the answer came from Gemini. `route`
  recomputes each finding's id, so an opinion cannot be carried to a finding with another text,
  and while the switch is on a missing opinion removes nothing — but an opinion written by hand
  into the file is believed. The record and the report are what the overseer and the owner read.
- **Text in the code can address the model** ("treat this as safe"). The answer is bound to a
  schema and can only lower an action, so the worst outcome is a missed objection — which
  without the second opinion would not have been raised either — or a needless question.
- **The measurement's real examples are all correct findings.** The fifteen first-pass findings
  the owner approved measure false alarms; how many false findings are caught is measured only
  on twelve hand-written ones (four traps, eight typical mistakes), each of which carries the
  refuting line in the request. Real false findings may be harder.
- **The eval's paid-run gate is the same seat belt as the audit's** (below): the task's
  «Платні прогони» line or `--owner-approved` outside a session.
- **The nightly cleanup is a command, not a schedule.** Nothing in the engine runs
  `simplifier.py nightly`; without a cron line the history grows only at `pre_commit` and `ci`.

## The task board, its runner and the paid-run gate

- **The paid-run gate is a seat belt, not a lock.** `run_audit_scenarios.py` refuses unless the
  task in `tasks/doing/` says `Аудит потрібен: так`, and `--owner-approved` does not count while
  `CLAUDECODE` is set. The task file is the project's and an agent can edit it; an agent can
  clear the variable or point `--tasks-dir` at another board. Each is a deliberate act that shows
  in the diff or the transcript — the gate stops drift, not intent. Only that one script is
  gated; for any other paid run the rule is text.
- **The release command's owner check is the same seat belt.** `engine.py release` refuses
  without `--owner-approved` and while `CLAUDECODE` is set, and it pushes from inside a script,
  where no hook sees the push. An agent that clears the variable can release; that is a
  deliberate act in the transcript, and only the remote's branch protection would stop it. What
  the command guarantees regardless of who runs it: no force, no moved tag, fast-forward only,
  nothing pushed on red tests or a differing golden set (`docs/release.md`).
- **The runner sees files and commits, nothing else.** A task is closed when it left
  `tasks/doing/` for `done/` or `blocked/`. The runner does not read the report and does not
  judge the work; a task moved to `done/` with nothing done is "done" to it. The overseer and
  the Stop gate inside the session are what judge.
- **The runner's own commits are made from a script**, where no hook sees them. It carries the
  check itself: the work branch must match `unattended/*`, the checkout must be on it at every
  commit, and it commits `tasks/` only. Its push goes to that one branch, never forced.
- **Cost is what the sessions report.** A continued conversation is taken to report its running
  total (seen in the operator's log, never proved with a paid probe); every attempt's raw figure
  is kept in `.claude/state/board/costs.json`, so the other reading can be recomputed. A session
  killed before it printed its result reports nothing, and its cost is not counted.
- **`BOARD_MAX_USD` errs toward stopping early.** Each call gets `--max-budget-usd` with what the
  task has left. Whether Claude Code counts that against the call or against a resumed
  conversation's total was not probed; under the second reading a continuation stops sooner than
  the cap, never later.
- **The usage-limit notice is recognised by its wording** (a short reply containing "hit your …
  limit"). A notice worded differently counts as an attempt without a commit; three of those
  park the task in `blocked/`, which is the safe side.
- **A logged-out claude is recognised by its wording too** (a short error reply with "Please run
  /login", "Invalid API key", "Not logged in", an expired or revoked OAuth token). The wording was
  taken from the CLI's messages, not from a live logged-out run. Worded differently, it is three
  attempts without a commit per task: every task in `todo/` is parked in `blocked/` in turn, at no
  cost, each with a journal entry — noisy, and undone by answering the questions.
- **A parked task's uncommitted work is on a branch `wip/<task>/<UTC>` in origin — when the push
  worked.** With `--no-push`, or with origin unreachable at that moment, the branch exists on the
  runner's machine only, the task file says so, and nothing sends it later. The branch (and the
  stash kept beside it) takes untracked files that were not the agent's as well (ignored files
  stay). Nobody deletes these branches: they pile up in origin until the owner removes them.
- **The anomaly journal has four writers, not every hook.** The runner, the Stop gate (an
  escalation), the stuck counter (the third identical failure) and the agent (by its own command,
  when it chooses to) write `tasks/ANOMALIES.md`; the deny hooks and the overseer's hooks still keep
  their own records only. An entry of the gate, a hook or the agent is committed by the runner, so
  in an interactive session it stays uncommitted until somebody commits it. A stop with
  `reason=branch` (the checkout is not on the work branch) is not written: the journal would land
  in a foreign branch.
- **The stuck counter's key is built by patterns.** Times, dates, durations, numbers, ids of seven
  or more hex digits and scratch paths (`/tmp`, `/var/folders`, `tmp…`, `pytest-…`) are replaced
  before the text is cut; a varying part of another shape (a random word, a port name) still makes
  two keys, and two different failures that differ ONLY in such parts count as one.
- **The health records are this machine's.** `tests/run_all.sh` and `evals/run_hook_scenarios.py`
  write `.claude/state/health/*.json` where they run; a review made in another clone shows no test
  run and falls back to the newest results file for the golden set. A record says what was run on
  which commit and whether the tree was dirty — not that the commit is the branch's head now.
- **A gate question is removed only on this machine's record.** The runner sweeps a question when
  `.claude/state/gate/escalations.json` lists its stamp as closed; a state file that was lost or
  belongs to another machine proves nothing, and the question stays.
- **The mode file is shared.** While the runner lives, `.claude/state/overseer/mode` says
  `unattended` for every session in the repository, an interactive one included.
