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

### A protected path in a shell command

The paths `protect-paths.sh` refuses to Edit and Write (one list, `protected-path-list.sh`) are
refused to a shell command by `block-dangerous.sh` (board 714; before it `printf x >` into the
constitution and `cat` of an env file reached the shell). What is refused, and what is not seen:

- **A write to any protected path**: the target of `>` and `>>`, an argument of `tee`, `rm`, `mv`,
  `truncate`, `touch`, `chmod`; the last argument of `cp`, `ln`, `install`; the file of `sed -i`
  or `perl -i`; `dd of=`; the value of `--output` and of `curl -o`; `git rm` and `git mv`; in
  inline code the file of an `open()` with a writing mode, of `write_text()`,
  `writeFileSync()`, `os.replace()`, `shutil.copy()` into it. **Reading a guarded file passes**
  (`git diff -- <file>`, `grep`, `cat`, `cp` out of it), and so do `git checkout -- <file>` and
  `git restore <file>`: putting the committed text back is the remedy, not the breach. With
  another revision or a `--source` named it is a write and is refused. One file under `.git/`
  may be removed: a stale `index.lock`.
- **Any mention of a secret path**, reading included. A word is taken for a path when its form
  leaves no doubt (a dotfile named `.env` or `.env.<x>`, `secrets/`, `~/.ssh/`,
  `credentials.json`) or when a file of that name exists; `jq .key` and `process.env` match the
  list's `\.key$` and `\.env$` and are not files.
- **Not seen**: a path kept in a variable or put together from parts, `cd <dir>` and then the
  bare file name, a write made by a script the command only starts, `xargs`. The text of the
  command is all a PreToolUse hook has. The check holds against a careless command, not
  against one written to get round it — like everything in this section.
- **Refused though harmless**: a command whose *message* quotes such a write (a board item, a
  commit message), and a settings file written into a throwaway project under `/tmp` — the
  pattern is the path's tail, as it is for Edit. Put the text in a file, or build the
  throwaway project from a script.
- Without `python3` the hook cannot tell a read from a write: a command that names a protected
  path is then refused whole. Without the list file both hooks refuse every call.

### A dangerous push

Every push still meets the `ask` rule of the settings file. Three kinds are refused by
`block-dangerous.sh` itself, whatever the prompt would be answered (board 017, owner decision;
it takes back part of the decision of 2026-10-01, which left push to the settings file alone):

- **a forced push** — `--force`, `--force-with-lease`, `--force-if-includes`, `--mirror`, a
  short-flag cluster with `f` (`-f`, `-uf`), a refspec that starts with `+`;
- **the deletion of a remote branch** — `--delete`, a cluster with `d`, a refspec that starts
  with `:`;
- **a push into a protected branch** — a refspec whose destination is one (`main`, `HEAD:main`,
  `x:refs/heads/main`), `--all` and `--branches`, and a push that names no branch (or `HEAD`)
  while one of them is checked out. The branches are `main` and `stable`, or the ones
  `PUSH_PROTECTED_BRANCHES` in `.claude/project.env` names; the gate guards the key like
  `PROJECT_MARKER` (only a sealed slice contract that names it lets a change through). A release
  into such a branch is the operator's, outside Claude Code.

The push is found in any spelling: behind `git -C <dir>` or `git -c key=value`, with several
spaces or tabs, after a separator, with the flag anywhere before the next separator. What is
**not seen**, and accepted as such by the owner:

- a push made by a script the command only starts (`engine.py release`, the board runner);
- a remote, a refspec or a flag kept in a variable or produced by a substitution;
- a push into a protected branch through configuration, when the local branch has another
  name: an upstream set to `origin/main`, `push.default`, a `remote.<name>.push` refspec, a
  remote whose URL is another repository's `main`;
- an alias (`git config alias.p push`).

**Refused though harmless**: quotes are not parsed, so a command whose message quotes such a
push (a commit message, a board item) is refused too — put the text in a file. A branch that
merely carries the name elsewhere (`feat/main`, `main:feat/copy` with main as the source) passes.

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
  Unattended sessions do not depend on it: `board-runner.sh` passes
  `--permission-mode auto` itself.)
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
| attended, the owner's machine | refused — the commit is the owner's review checkpoint | `permissions.ask` prompts; the dangerous forms refused by the hook ("A dangerous push") |
| unattended (the board runner) | allowed on `unattended/*` only | ask → parked by `park-ask-gated.py`; the dangerous forms refused |
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
- **The board runner runs that command on the owner's `так`** under the gate's question in
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

## The delete guard (board 072)

The gate blocks a change that deletes working code no test touched (`.claude/references/gate.md`).
What that does not give:

- **Executed is not checked.** With `COVERAGE_CMD` the guard knows a test ran the lines, not that
  any test looked at what they returned. A test that calls a function and asserts nothing lets the
  function be deleted. That is the limit of every coverage figure.
- **Without `COVERAGE_CMD` the answer is coarse.** "The module has its test file" passes every
  function of that module, tested or not; "a test file mentions the name" is a word match, so a
  common name (`run`, `main`, `__init__`) is always "mentioned". The untested module — the usual
  state of code the engine did not build — is what this mode catches.
- **Names are known for Python only.** In any other language the unit is the file: a deleted file,
  or more than `DELETE_GUARD_LINES` removed lines in one file. A function deleted in fewer lines
  than that passes unseen.
- **Module-level code is not counted in Python.** Lines removed outside every function (a table,
  a constant, top-level statements) do not block; neither does a function shortened by fewer
  lines than the threshold. The threshold of 20 is a starting value, not yet calibrated.
- **A move is told by the name or by the text.** A function renamed in the same change reads as
  one deleted and one added; a function deleted while an unrelated one of the same name is added
  reads as moved. A removed line counts as moved when the same text is added anywhere in the change.
- **`COVERAGE_CMD` runs in a clean checkout of the old commit**, made with `git archive`: no
  virtual environment, no untracked or ignored file. A command that needs them must create them
  (`uv run …`), and it costs one more test run — two, when the change also edits tests — per
  distinct change that deletes something. When
  it leaves no readable `coverage.json` the guard warns and falls back to the coarse answer.
- **Only the diff.** Like the bypass guard, the guard compares with HEAD at `stop` and with the
  index at `pre_commit`: a deletion committed outside the gate is no longer a diff.
- **The owner's confirmation is machine state.** It holds on the machine where the owner ran
  `delete_guard.py confirm`, and — as for the snapshot — rests on `CLAUDECODE` and on
  `.claude/state/` being closed to the agent's edit tools. That a finding's tool evidence is
  true is not re-checked at confirmation: the validator checks that the signal existed.

## The bug-fix proof (board 074)

`bugfix.py prove` shows that a test fails on the code before a fix and passes on the code with it
(`.claude/commands/bugfix.md`, step 6). What that does not give:

- **Fails is not "fails because of this bug".** Without `--expect` any failure before the fix
  counts — an import error that the fix happens to remove passes. With `--expect` the script
  looks for that text in the output, and the text is chosen by the builder. Whether the test
  describes the bug of the record is the overseer's reading, not the script's.
- **A clean copy, not the project's environment.** Both runs happen in temporary copies: the
  base commit from `git archive`, and the files of the working tree git tracks or would track.
  No virtual environment, no ignored file, no `.git`. A command that needs them must create them
  (`uv run …`); a test that cannot run there cannot be proved by this script, and the record
  must say so rather than claim a proof.
- **One command, chosen by the builder.** `--cmd` should run the new test alone. A command that
  runs the whole suite fails before the fix for any old failure of the project, and the proof
  then says nothing about the new test.
- **Nothing forces the proof.** The command and the overseer's definition ask for it; no hook
  refuses a bug fix without one. An overseer that does not rerun the command sees only what the
  builder pasted.
- **A bug record is not sealed.** It is the report as well as the contract, so it changes while
  the work goes on; the fingerprint that protects a slice contract (`contract_fingerprint.py`)
  does not cover it, the audit request carries no contract hash for it, and a `gate-allow` line
  written in it grants nothing. Its budget is the exception: the limits seen first are kept in
  machine state, as for a slice.
- **The budget is measured only while `.engine/PROGRESS.md` marks the record IN PROGRESS**, and
  held at turn end only when `COMPLEXITY_GATE` is `warn` or `call`. With the gate off the
  measurement happens when the builder runs `complexity_budget.py check`, as the command says.
- **Three attempts are counted by the builder.** The record has room for three; nothing counts them.
- **`pins` shows a test passes, not that it looks at the code about to be deleted.** A test that
  asserts nothing about that code pins nothing and still prints `PINNED`.

## Regular care (board 076)

`/maintain` reports, the owner approves a list, the board runner updates (`.claude/commands/maintain.md`).
What that does not give:

- **"Read-only" is the project's word.** `DEPS_OUTDATED_CMD` and `DEPS_AUDIT_CMD` are run as written;
  the script cannot tell a command that reads from one that installs. The command file tells the
  agent to stop on one that plainly changes something; nothing enforces it.
- **The class of an update is read from two version numbers.** Patch, minor, major follow semver,
  with a `0.x` minor counted as major; a project that breaks things in a patch is not caught by
  the class — only by its tests, after the update, which is why every update is followed by the full gate.
- **An update is checked by what the project checks.** With thin tests a breaking update passes
  and is committed. A project whose gate runs no tests gets no update at all.
- **A roll-back restores the files git tracks.** The installed packages come back only through
  the project's `DEPS_RESTORE_CMD`; with it empty the result file says the environment may be newer
  than the files. Files the update command wrote into an ignored path are not removed.
- **The owner approves a list, not a diff.** The sha256 ties the answer to `updates.json`; what the
  update command then does with each name and version is the command's own.
- **The weekly task is weekly only while the runner runs.** `board.py maintain-task` is asked before
  every task; a runner that is not started places nothing, and the first start after a long
  pause places one task, not one per missed week.
- **Hot places and complexity are measured for Python only**, as the simplifier's signals are.

## The urgent fix (board 075)

`/hotfix` puts off the test before the code, the record of the cause and the search for the same
places, keeps the gate and the overseer, and holds the fix to a hard limit
(`.claude/commands/hotfix.md`). What that does not give:

- **"Only the owner declares" is a text check.** `hotfix.py start --task` looks for `/hotfix`,
  «термінове» or "urgent" in the task file; `--declared` records words the agent says the owner
  said, and is refused only in an unattended session. Who wrote the line in the task, and whether
  the quoted words were said, is the overseer's reading and the owner's, not the script's.
- **The three-debts answer is matched, not judged.** With `--task` the answer must stand on a
  «Відповідь:» line of the task; the script does not read whether it says "go on" or "close a
  debt first". An agent that runs `start` on a refusal is caught by the overseer, not by the script.
- **Nothing forces `/hotfix` to be used.** An agent that fixes urgently without the command
  leaves no card, so no hard limit and no debt; what it meets is the ordinary gate and the
  overseer, as any unit does.
- **The hard limit is held only while `.engine/PROGRESS.md` marks the card IN PROGRESS** and is
  the first such block; `hotfix.py debt` measures the card again whatever PROGRESS says. A card
  closed in PROGRESS before the turn ends is no longer measured at the stop.
- **A hard block has no escalation.** The budget hook blocks at every stop while the fix is over
  the limit; it does not count attempts and does not give up. The ways out are in the block's
  text: a smaller fix, or `/bugfix`.
- **"Deleted outside the functions being fixed" is exact only for Python.** There a deleted
  function, class method or file, and a module-level line removed and not replaced, are found by
  parsing. In another language the rule is coarser: no place of the change may remove more lines
  than it adds — which also refuses an honest shortening inside a function.
- **Lines are counted, not judged.** Thirty added lines in two files can still be the wrong fix;
  a long line is one line. A test is never counted, and no test is required.
- **The debt has a term, not a force.** After seven days the review shows the debt among the
  anomalies; nothing stops other work. The follow-up task is numbered after every ordinary task
  on the board, so it waits its turn unless the owner moves it.
- **`close` checks a record, not the work.** A bug record with `type: bugfix` and
  `status: fixed` closes the debt; that the record's proof is real is the overseer's audit of
  that `/bugfix`.
- **The way back is checked for presence only.** `debt` refuses a card whose `- Roll back:` line
  is empty; it does not try the command.

## The snapshot "as it was" (board 071)

With `.engine/baseline.json` the gate asks "no worse than it was" (`.claude/references/gate.md`).
What that does not give:

- **The Stop gate sees only the files the turn changed and the tests that map to them.** A test
  broken by an edit in another module, or a finding that appears in a file the turn did not touch,
  is seen only by the full run before a commit (`pre_commit`, `ci`). That was always so; in code
  the engine did not build, the links between modules are less known, so it weighs more there.
- **A count, not an identity.** Lint and types are compared as a number per (file, rule). Fix one
  finding and add another of the same rule in the same file, and the number — and the gate — does
  not move. A file that is renamed starts from zero: its old findings block until they are fixed
  or the owner records again.
- **A listed test is not watched.** A test on the list may fail for a new reason and nothing
  notices; a listed test that was fixed is guarded again only after `baseline.py tighten`. The
  full layers warn that a fixed entry is still listed; nothing runs `tighten` by itself.
- **Only what the output names.** Test names and findings are read from the commands' output in
  the formats `gate.md` lists. Another runner's format reads as "a failure that names nothing",
  which blocks as without a snapshot — the strict side, but then the snapshot gives that project
  nothing until its command prints those lines. A test command that stops at the first failure
  hides everything after an old failure; the gate warns and cannot see past it.
- **"Only the owner loosens" rests on two things a script can get around.** `record` refuses to
  loosen when `CLAUDECODE` is set, and its approval lives in `.claude/state/`, which the agent's
  edit tools may not write. As with every guard here (see "Hooks guard tool calls, not scripts"),
  a script the agent writes could unset the variable or write the approval; no rule permits it,
  and it shows in the transcript and in the committed diff of the snapshot, which the review
  lists by name.
- **Coverage is not measured**, and old failures are accepted, not excused: each stays in the
  review as a candidate for a task until someone fixes it.

## The overseer as a separate agent (board 015 / 018)

Every audit is done by the agent `overseer` in a fresh context, and the verdict is written by
`overseer_verdict.py`, not by a model. What that rests on:

- **The builder has to launch the agent.** A hook cannot start a subagent; the Stop hook asks,
  `overseer_verdict.py guard` refuses any prompt but the request line, and a request left without
  a verdict is repeated twice, then parked and the turn ends. An agent that never launches the
  auditor gets no PASS — and no audit either.
- **A verdict can be forged by the builder, and this is not closed** (board 032; the owner's
  decision of 2026-10-05). The builder's Bash and the hooks run as the same user with the same
  environment (probed on Claude Code 2.1.288) and the same rights on the disk, so a hook cannot
  tell who started it and a file cannot tell who wrote it. Two ways, both reproduced on the real
  hooks in a temporary project:
  1. a made-up SubagentStop envelope piped into `overseer_verdict.py record` — the ledger gets an
     `OVERSEER_PASS` although no auditor ran;
  2. a line appended to `.claude/state/overseer/verdicts.jsonl` — the next Stop hook answers
     "PASS recorded, proceed". The file is machine state, not on the list of protected paths;
     were it there, a write from inside a script would still pass every hook.

  The same rights reach the request package (`request.json`: the tree fingerprint, the count of
  PASSes in a row) and, in this repository, the auditor's own instructions (`.claude/agents/`).
  The rules forbid all of it and it shows in the transcript and in the diff; nothing makes it
  impossible. So the independence of the verdict rests on the builder not forging it — the
  guarantee holds against a mistaken or careless builder, not against one that sets out to
  deceive. Why it stays open: the owner counts such forgery a theoretical possibility, and the
  only thing that closes both ways is a boundary the operating system holds (a sandbox for the
  builder's commands, or an auditor under another system user), which costs every command of
  every session. The spare design — the hook starts `claude -p` itself — closes only the first
  way: the verdict would still be kept in a file the builder can write. The options, their price
  and the test of each are kept in `tasks/done/032-unforgeable-verdict-design/report.md`.
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

## The testing manager and the slice tester (board 062)

- **Where the tester's blindness is real, and where it is a rule.** On the first pass (mode
  `contract`, before the code) there is no implementation to read, and the script proves it: it
  runs every contract test itself and each must fail. In an objection, in a catch-up and in
  mode `block` the code lies in the tree, and the Agent tool cannot keep an agent from reading a
  file: there the blindness is a rule of the agent's definition and nothing more. `guard` keeps
  the tester from WRITING anything but test files; it cannot keep it from reading. A separate
  git worktree for such runs is deferred until the review after ten slices shows the rule is
  not enough.
- **Until the owner applies the proposal** (`docs/tasks/settings.json`, two handlers) nothing
  checks that the two agents were started with the script's line, and the answer is recorded
  by hand (`testing.py record --answer`): the builder carries the agent's answer to the script
  and could carry a different one. What holds without the handlers: the mandatory cases, the
  script's own RED run, the seal, and no audit request before the decision of point (a).
  `engine.py update` adds the overseer's two handlers to a settings file a project edited; it
  does not add these two — such a project applies the proposal itself.
- **"Not on an import" is a pattern.** A failing run counts as RED unless its output shows an
  import, syntax or collection error (`ImportError`, `ModuleNotFoundError`, `SyntaxError`,
  "collected 0 items", "Ran 0 tests", "Cannot find module" …). A runner that words such an error
  differently passes a test that never reached its body. The command that runs one test is the
  tester's (`run`, with `{test}`); the tests run in the working tree, not in a clean copy.
- **O8 is as exact as the delete guard.** With `COVERAGE_CMD` — the executed lines; without it
  — "the module has its test file, or a test file mentions its name", which a test that only
  imports the module satisfies. At point (a) it sees the files the contract's «Seam» names that
  already exist; a contract that names none gives "unknown", and O8 is decided at point (b) by
  the diff. In a project with no tests it fires on almost every slice — that is meant, and every
  firing stands in the owner's review.
- **The script reads marks, not meaning.** O3 fires on a line of «Exit criterion» that carries
  the mark `/plan-slice` writes (`(threshold owner-ratified)`, `PROVISIONAL — owner ratification
  pending`); a threshold written without the mark is invisible to the script, and the planner's
  critic is what checks the mark. A self-added behaviour is counted by the word `self-added` in
  `.engine/slices/<slug>*.md`. A slice is found in a feature artifact by its name: the slug
  equals the name in «Slices (the DAG)», or ends with it; a slice the artifact does not name
  stands alone as one block, without consumers.
- **A slice already in flight when this arrives** has a sealed contract and no decision of point
  (a): its next completion claim gets `TESTING NOT SETTLED` instead of an audit until the manager
  is asked once. A slice without a sealed contract is untouched.
- **A mutation run is whatever `MUTATION_CMD` prints.** The script records its duration, its
  exit code and its output; it does not parse survivors, and there is no score. How many
  survived and how many were handled is the number the builder records with `mutation-result`.

## The simplifier

- **A signal is a lead.** vulture cannot see a name used through a string, a decorator or a
  framework; the unused-dependency check compares the declared name with the imported module
  name and is wrong for a package whose import name differs (`pillow` / `PIL`); pylint's
  duplicate check sees only Python. The signals feed the agent and never remove anything.
- **A name only the tests use is not a dead-code signal.** vulture reads the tests and scripts as
  users of the production code (reporting production files only), so a library's public function
  is not "dead" for having no caller inside the library. The price: code kept alive by its tests
  alone is no longer flagged — finding it is the simplifier agent's judgement, not a signal.
- **The verdict on a budget overrun is relayed by the builder.** `simplifier.py accept` checks
  the answer file it is given (schema, nothing above `flag_only`) and records its hash, but it
  cannot know the file is what the `simplifier` subagent really answered. The reason lands in
  the ledger, which the overseer and the owner read; that is the check. The answer of the
  simplifier in general travels the same way: the builder saves it to a file and hands that file
  to `validate`, `route` and `accept`, and the request to the agent is not pinned to a fixed line
  as the overseer's is, so a builder can also add words to it. Recording the answer by a hook
  was designed with the overseer's boundary and put off with it (board 032).
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
  «Платні прогони: так» line (no dollar number; one written there is a ceiling) or `--owner-approved`
  outside a session. What stands against a loop is the runner's `BOARD_MAX_USD`, not the line.
- **The nightly cleanup runs in the board runner's free time, not on a clock** (board 045). The
  runner places the cleanup task only when it has nothing else to take, and not more than once a
  day; a board that is never idle, or a runner that is not started, runs no `simplifier.py nightly`,
  and the history then grows only at `pre_commit` and `ci`. A cleanup day without sharp growth
  still costs one agent session, which only records the signals.

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
