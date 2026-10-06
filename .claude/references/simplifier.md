# The simplifier — when it runs and what its findings may do

Read this when a signal calls the simplifier, when you hold its findings, or when you change
`simplify_signals.py`, `simplifier.py` or `.claude/agents/simplifier.md`.

Programs written by language models grow faster than the behaviour they add. The simplifier is
there against that growth; what it saves is a side effect. Three parts, strictly apart:

| Part | What it is | May it judge? | May it change files? |
|---|---|---|---|
| signals | `simplify_signals.py` — measured facts with file and line | no | no |
| agent | `.claude/agents/simplifier.md` — model `fable`, fresh context, blind, Read / Grep / Glob only | yes | no |
| validator and routing | `simplifier.py` — decides what a finding may do | no | only the owner's report, the queue, the ledger |

## It runs only on a signal

1. **A complexity budget exceeded** — `complexity_budget.py` says so at the end of the turn
   (`.claude/references/complexity-budget.md`). Lens `budget`.
2. **Sharp growth against the project's own history** — a `trend` signal of the full scope:
   a total (lines, functions above the limit, dead code, duplication, unused dependencies)
   more than 20 % over the median of the last five recorded runs. Lens `code`.
3. **The step between design levels** — after the architecture artifacts, before features and
   slices are cut (`/master-architect`, `/feature-architect`). Lenses `requirements` and
   `architecture`.
4. **The nightly cleanup** — `python3 .claude/hooks/simplifier.py nightly`: the full signals,
   one line of history, the reversal rate. It says whether the simplifier is called. No cron:
   the board runner puts a cleanup task on the board when it has nothing else to take, not more
   than once a day (`board.py cleanup-task`; `CLEANUP_EVERY_DAYS` in `.claude/project.env`, `0` —
   never), and that task runs this command and one pass of the simplifier when it is called.

No signal, no simplifier: it is never part of an ordinary turn. The nightly cleanup may also
look at the standing instructions (lens `instructions`: CLAUDE.md, rules, skills, agents, commands, and the
goals document `.engine/goals.md` — it has no size limit, so this lens is what keeps it short). A finding about
the goals document is never applied: the path is protected, the finding goes to the owner as a question, and a
line leaves the document only through an amendment the owner approves (`.claude/references/business-analysis.md`).

## One run

```bash
python3 .claude/hooks/simplifier.py request --lens code --paths src > request.txt   # signals inside
# start the `simplifier` subagent with request.txt as its whole prompt; save the answer
python3 .claude/hooks/simplifier.py validate .engine/simplifier/answer.json --request request.txt   # what was lowered or rejected
python3 .claude/hooks/simplifier.py route .engine/simplifier/answer.json --request request.txt --title "code, nightly"
```

The agent's answer is a JSON list of findings and nothing else. The validator rejects a finding
that breaks the schema and lowers one that claims more than it may: a protected path is never
`auto_remove`; code no test protects is never above `flag_only`; `auto_remove` needs a checked
fence, tool evidence and a reversal risk that is not high; every evidence item cites a signal
that was given, a line that exists, or says `judgement`. Nothing is ever raised. A path is judged as
the project sees it: an absolute path, `./`, `..` or a link is first rewritten relative to the
root — so a protected file is protected however it was written — and a target or a cited line
outside the project is rejected.

## The second opinion (off unless `SECOND_OPINION="on"`)

A different model — Gemini — looks at each validated finding before it is routed:

```bash
python3 .claude/hooks/simplifier.py validate answer.json --request request.txt --out valid.json
python3 .claude/hooks/second_opinion.py review valid.json --out reviewed.json
python3 .claude/hooks/simplifier.py route reviewed.json --request request.txt --title "code, nightly"
```

`review` sends one request per finding: the claim (target, category, claim), the target's code,
the files the claim names, and the lines where a name from the target occurs. It does not send
the simplifier's evidence, action, risk or test-safety — the judge sees the artifact, not the
author's reasoning — and never a protected path, `SIMPLIFY_EXCLUDE`, the simplifier's own
records or a file outside the project, however the path is written. The answer is `agree`, `disagree` or `unsure`, a reason, and lines cited as `path:line`;
a cited line that was not sent is marked unverified. Whatever fails — no key, a timeout, a broken
answer, the pass limit `SECOND_OPINION_MAX_USD` — is `no_opinion`, and the pass goes on.

`route` then lowers, and only lowers:

| The simplifier | The second model | The finding becomes |
|---|---|---|
| `auto_remove` | agree | `auto_remove` (the builder's three conditions below still hold) |
| `auto_remove` | anything else, or no answer | `confirm` — the owner decides, both views side by side |
| `confirm` | disagree, citing a line that was sent | `flag_only`, noted "the models disagree" |
| `confirm` | disagree without such a line, unsure, no answer | `confirm`, with a note |
| `flag_only` | anything | `flag_only`; the view is recorded |

While the switch is on, a findings file that skipped `review` is treated as "no answer": nothing
in it is removed automatically. There is no debate round and no third model: the owner is the
arbiter. The second model adds no findings of its own and is not asked about a budget overrun
(`accept`). Findings the models disagree on stand first in the report.

- **The key** is the environment variable `GEMINI_API_KEY_SIMPLIFIER` and nothing else — a
  paid-tier key of its own with a spending limit in the Google console. It is sent in a header,
  cut out of error texts, and never written to a file. For a board runner under systemd:
  `EnvironmentFile=` pointing outside the repository (the owner's step).
- **The record** is `.engine/simplifier/second-opinion.jsonl`: finding, model, verdict, reason,
  cited lines, tokens, cost, the hashes of request and response. `second_opinion.py cost` adds
  it up. The model and its prices are in `.claude/project.env`; reread the prices before use.
- **Measured live:** `simplifier.py decide <id> так|ні` records the owner's decision on a
  `confirm` finding; `simplifier.py reversals` then shows the removals the second model agreed
  with apart, and how its verdicts compare with the owner's decisions.
- **Measured before switching on:** `python3 evals/run_second_opinion_evals.py --runs 3` — 33
  findings with a known truth, put to Gemini and, as the control, to a fresh Claude with the
  same request. Paid, like the eval below. The owner's thresholds (board 012): at least half of
  the false findings caught, an alarm on at most one correct finding in ten, noticeably more
  caught than the control. Not passed — the switch stays off.

## What happens to a finding

- `confirm`, `flag_only` — `route` writes them to `.engine/simplifier/report.md` for the owner
  and adds them to the lesson queue. Nothing is removed.
- `auto_remove` — the builder removes it, one finding per commit, only when ALL hold:
  the target is outside the protected zones (the validator already checked); a test covers
  what is removed — name it; after the removal the full suite is green (`TEST_CMD_FULL`).
  The commit message ends with the trailer `Simplifier-Finding: <id>`:

  ```bash
  git add <files> && bash .claude/unattended/commit_checkpoint.sh --staged simplify \
    "$(printf 'simplify: <what went>\n\nSimplifier-Finding: F-1a2b3c4d')"
  ```

  Any of the three missing: do not remove; the finding is a `confirm` for the owner. A removal
  undone later carries `Simplifier-Reverts: <id>` (or is a plain `git revert`).

## The reversal rate

"If nothing ever has to be put back, we are removing too little." `simplifier.py reversals`
counts, over the last N removals, the ones that came back: reverted, undone by trailer, or the
removed lines are in the file again. The corridor is 5–20 %, the aim about 10 %. Outside it —
and with ten removals at least — `--record` leaves a note for the owner in the report: bolder
below, more careful above. The agent's definition is not tuned by an agent (Art. 7).

## Measuring the agent

`python3 evals/run_simplifier_evals.py --runs 3` — a copy of the reference project with six
kinds of planted excess and four traps (things that look unneeded and are not). Recall,
precision, traps touched; a touched trap is the failure that matters. Paid: it starts real
sessions, so it runs only when a task allows it (`tasks/README.md`).
