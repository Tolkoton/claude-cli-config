---
description: Get to know an existing project together with its owner. Surveys the code read-only, runs every check command it found for real, recovers the project's rules as candidates each with its source, takes the owner's verdict on every one, has a fresh reader verify every reference, and leaves the profile `.engine/onboard/profile.md`, `.claude/project.env`, a short AGENTS.md and the snapshot "as it was". Fixes nothing, installs nothing, writes no decisions in hindsight. Use once, after `engine.py install`, in a project that was not built with the engine. Needs the owner in the conversation; without the owner it does steps 1–3 and stops with questions.
---

You are running **/onboard**: the engine's first meeting with a project it did not build. The
rules of such a project live in its owner's head, not in its code — so this is a session with the
owner present, and everything you conclude alone is a *candidate* until the owner has said yes.

Speak the owner's language; with no owner present, write in the language of the project's own
documents. `$ARGUMENTS` may name a directory to start the survey from; empty means the whole project.

## What /onboard never does

- **It fixes nothing and tidies nothing.** No edit to the project's code, tests, configuration
  or documents other than the five files of step 6. A failing test, a lint finding, a dead file —
  each is written down, none is repaired.
- **It writes no decisions in hindsight.** No ADR, no "we chose X because…": the structure is
  recorded as "this is how it is", never as "this was decided". Why something is so is the
  owner's to say, in their words, or it stays an open question.
- **It installs nothing.** Not the engine (`engine.py install` did that before this command), not
  a package, not a tool. A command whose tool is absent is recorded as «not run», never repaired.
- **It reads no secrets.** `.env`, `secrets/`, credential and key files are not opened and never
  quoted; the profile says only that they exist and where. A script that loads such a file itself
  is not run. Identifiers of external accounts found in documents are not copied into the profile.
- **It never answers for the owner** and never infers a verdict from an earlier remark.

## Who is here

Unattended — `CLAUDE_UNATTENDED_SESSION=1`, or `.claude/state/overseer/mode` says `unattended` —
or the session has no way to ask (no interactive question, or whoever started it said so): do
**steps 1–3 only**, write the profile as a draft (its first line says so,
every candidate rule has the verdict «waits for the owner»), and stop with the questions of
step 4. They are written into the profile's «Open questions» section and printed; on the task
board they also go into the task's «Питання до власника» and the task to `blocked/`. Do not touch `.claude/project.env`, `AGENTS.md`, the snapshot
or the premise log, and do not act out the owner's part. Steps 4–8 are for a session the owner sits in.

## If the project already has agent files or an older engine

Its `AGENTS.md`, `CLAUDE.md`, progress journals and earlier engine records (also under the old
paths `.claude/overseer/`, `.claude/premises/`, `.claude/architecture/`) are documents to survey
and sources of *written* rules like any other. A rule that is the engine's own policy (commits,
hooks, the overseer) is not a candidate rule of the project. In step 6 an existing `AGENTS.md` or
`project.env` is not replaced: show the owner the difference and change only what they agree to.

## 1. Survey — read only

Create `.engine/onboard/profile.md` from `.claude/references/onboard-profile.md` and fill it as
you go; nothing else is written in this step.

- **Languages and layout**: what is in which directory, which directories are code, tests,
  generated, vendored.
- **How it is built, tested and checked** — from the CI files, Makefile/task runner, package
  manifests, pre-commit and linter configuration, an existing `project.env`, agent instruction
  files, setup and deploy documents, usage lines in script headers. Collect every command with
  the file and line that names it. These are *found* commands; step 2 decides which of them
  work. A family of deploy or provisioning commands in one document is one row.
- **Dependencies**: the manifests and lock files, the runtime versions they ask for.
- **A repository of several stacks** is mapped part by part; a command and a rule name the part
  they belong to.
- **Existing documents and decisions**: README, docs, ADRs, agent instruction files. Note which
  look current and which contradict the code — as an observation, not a fix.
- **History**: `git log` — which files change most often and are at the same time the largest
  (commits touching the file, and its lines: the places where work will most likely land);
  reverts; the same file fixed again and again. On a long history, say how far back you looked.
- **A large project is not read whole.** Read the hot places first — a hot source file is read
  in full before any rule about it is offered — and write in the profile's «Not read» section
  what you only searched and what you did not open. A count from a search over files you did not
  read is marked «counted, not read»; any other claim about an unread file is not made.

## 2. Check the commands — by running them

First check that each command's tool is there (`command -v`, `--version`). Then run every command
found in step 1, one at a time, each with a time limit (ten minutes unless the owner names
another; a timeout is recorded as «ran, timed out»), and record for each: the exact command, the
exit code, how long it took, and what failed (counts and names, not a pasted log).

- **A command that was not run does not go into `project.env`** — it would be an unverified
  premise about someone else's system (constitution, Article 1). It goes into the profile as
  «not run», with the reason: tool or runtime version absent, dependencies not installed, needs
  the network, a service or a credential, long-running or interactive, needs arguments the survey
  cannot supply, would change the sources or something outside the working tree (a throwaway
  directory under the system's temp directory does not count as outside).
- A runner that would create an environment or download packages on first use (`uv run`, `npx`,
  …) counts as tool absent when the environment is not there: running it would install.
- A variant of a found command (fewer arguments, another interpreter) may be run to learn
  something; it is recorded as a variant and does not go into `project.env`.
- **If none of lint, type-check and tests could be run**, say so in the first line of the profile
  and make it the first question: the meeting is not complete until the owner has prepared the
  environment, and steps 6–7 wait for it.
- Run nothing that deploys, publishes, migrates, pushes, or writes outside the project. If a
  command's effect is unclear, it is «not run» and a question for the owner.
- A command that runs and fails is still a verified command: the failures are what the snapshot
  of step 7 is for. Do not fix them.

## 3. Recover the rules — every candidate with its source

Write the candidate rules into the profile. Each names its source — one or more of three:

- **written** — a document, linter setting or CI step says it; cite `file:line`;
- **seen in the code** — a habit most files keep; give the count and what it is counted over
  (which directory, which kind of file), and list the files that keep it **and the files that do
  not** (up to ten by name, the rest as a number). Kept in one directory and not in another, it
  is a rule of that directory, or a guess;
- **seen in the history** — a reverted change, the same place fixed again and again; cite the commits.

A candidate with no source is not offered (Article 4). A guess is called a guess. A written rule
the code does not follow is offered as it is — with both the citation and the counter-evidence —
and the owner decides which of the two is the rule. A candidate is something a change could
break: one linter setting or one sentence of a document is not by itself a rule.

## 4. The owner decides

One candidate at a time (`AskUserQuestion` is right here): **yes**, **no**, or the owner's
corrected text, recorded verbatim next to the candidate. Then ask separately for the
**do-not-touch zones**: generated code, vendored code, what is about to be removed. They go into
the profile and into `SIMPLIFIER_PROTECTED`.

Ask too which of the confirmed rules a conversation cannot do without — only those go into
`AGENTS.md` (step 6).

## 5. A fresh reader checks every reference

Start one agent in a fresh context (`Agent`, no part of this conversation in its prompt) with
only the path of the profile and one job: for every `file:line`, commit and command the profile
cites, open it and say whether it says what the profile claims — «holds», «does not hold» (with
what it does say) or «could not check». It edits nothing. You have just read thousands of lines
and see order where there may be none (Article 6); the reader has not.

Correct or remove every reference that does not hold. A rule whose source fell away goes back to
the owner as a question; it does not stay confirmed.

## 6. What stays after the meeting

| File | What goes into it |
|---|---|
| `.engine/onboard/profile.md` | the map; the commands with the evidence of their run; **every** rule with the owner's verdict and its source; the risk zones (tested / untested / do not touch); what was not read |
| `AGENTS.md` | written with the skill `documentation` (its bootstrap workflow): the project in one sentence, the key paths, and only the rules without which any conversation would go wrong. The rest is read from the profile on demand |
| `.claude/project.env` | `SOURCE_DIRS`, `CODE_EXTENSIONS`, the check commands — only those step 2 ran; `SIMPLIFIER_PROTECTED` from step 4 |
| `.engine/baseline.json` | step 7 |
| `.engine/premises/premise-log.md` | step 8 |

There is no number of rules for `AGENTS.md`: the persistent context has one limit — CLAUDE.md,
AGENTS.md and what they import stay under 200 lines — and the simplifier (lens `instructions`)
looks at what is extra. Show the owner the three files before writing them.

## 7. The snapshot "as it was"

The project's checks fail today in ways nobody will fix today; the snapshot lets the gate ask
"no worse than it was". **The owner takes it, in their own terminal**:

```bash
python3 .claude/hooks/baseline.py record
```

Inside this session `record` prints what it measured and refuses to write — use that to show the
owner what would be recorded, then wait for them to run it. `python3 .claude/hooks/baseline.py show`
confirms it. Then print `python3 .claude/hooks/complexity_budget.py calibrate`: it proposes
complexity limits from the project's own code, and applying them is the owner's choice.

## 8. Open questions and unverified premises

Everything about the project that could not be checked — a command not run, a rule the owner
was unsure of, a part not read, a behaviour assumed from a document — goes into
`.engine/premises/premise-log.md` as an unverified premise, with what would verify it (Article 8).
Close with: the files written, the questions left open, the commands the owner still has to run.
