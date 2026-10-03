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
   one line of history, the reversal rate. It says whether the simplifier is called. Nothing
   in the engine schedules it; put the line in cron or a CI schedule.

No signal, no simplifier: it is never part of an ordinary turn.

## One run

```bash
python3 .claude/hooks/simplifier.py request --lens code --paths src > request.txt   # signals inside
# start the `simplifier` subagent with request.txt as its whole prompt; save the answer
python3 .claude/hooks/simplifier.py validate .engine/simplifier/answer.json            # see what was lowered or rejected
python3 .claude/hooks/simplifier.py route .engine/simplifier/answer.json --title "code, nightly"
```

The agent's answer is a JSON list of findings and nothing else. The validator rejects a finding
that breaks the schema and lowers one that claims more than it may: a protected path is never
`auto_remove`; code no test protects is never above `flag_only`; `auto_remove` needs a checked
fence, tool evidence and a reversal risk that is not high; every evidence item cites a signal
that was given, a line that exists, or says `judgement`. Nothing is ever raised.

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
