# Bug 002-overseer-bash-edit

type: bugfix
status: reproduced
<!-- sections 5–6 filled; 7–8 after the gate and the overseer -->
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «будівник записав src/refproj/orders.py і тести через Bash (cat > файл <<EOF, python-скрипт із open().write), прогнав перевірки й написав «=== UNIT 1 COMPLETE ===». overseer_stop.py запиту не подав … Хід закінчився без аудиту й без жодного повідомлення» (tasks/doing/707-open-item-044-overseer-bash-edit.md).
- Expected: a turn that claims a unit complete and rests on changed code and a verification command gets `OVERSEER_REQUEST <id>` — whichever tool wrote the code.
- Where the expected is written: `.claude/engine-rules.md`, Overseer protocol — "`overseer_stop.py` injects `OVERSEER_REQUEST <id>` only when a turn claims a unit complete: the sentinel … AND, in the same turn, an edit under a code path (`.claude/project.env`) plus a verification command": an edit of a code path, not a call of one tool; `.claude/references/hooks.md:16` ("sentinel + code edit + verification command"); the owner's task 707, «Що зробити»: «сигнал правки брати не з назви інструмента, а з дерева … який би інструмент їх не записав».
- Actual: the Stop hook says nothing and writes no request; the turn ends unaudited. The same turn with the file written by `Write` is answered with `OVERSEER_REQUEST`.
- Where it was seen: the sandbox of the live check 044 (Claude Code 2.1.289, 2026-10-05; `tasks/done/044-simplifier-live-check/report.md`), noticed only by the next session, which asked for the audit by hand and wrote the anomaly.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: in a fresh git repository `/tmp/b707/proj` (the engine's `.claude/hooks`, wired settings, `SOURCE_DIRS="src tests"`, `src/orders.py` committed): change `src/orders.py` on disk, write a transcript of one turn — a tool call that writes the file, then `Bash: pytest -q` — and feed the Stop envelope (`last_assistant_message` ending in `=== UNIT 1 COMPLETE ===`) to `python3 .claude/hooks/overseer_stop.py`. Once with the write as `Bash: cat > src/orders.py <<EOF …`, once as `Write src/orders.py`; nothing else differs.
- Output:
  ```
  --- written with Bash:
  [exit 0; pending: none]
  --- the same turn, written with Write:
  {"decision": "block", "reason": "OVERSEER_REQUEST 20261006T025008Z-b34687 (auto-triggered by the Stop hook on a unit-com
  [exit 0; pending: .claude/state/overseer/pending.json]
  ```
- Result: reproduced

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
- Test: `tests/test_overseer_fresh.py`, section «code written by a shell command (board 707)» — the case "a unit whose code was written by a shell command gets its audit request", at the level of the hook's command: `overseer_stop.py` fed the Stop envelope with a transcript that holds only Bash calls, in a repository whose file really changed. Beside it: the code written by shell and already committed; a fix made by shell after a BLOCK; and the negative cases (see section 5).
- Command that runs it: `python3 tests/test_overseer_fresh.py`
- It fails with: `FAIL a unit whose code was written by a shell command gets its audit request` — the hook's answer is empty, the symptom of section 1.
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — the suite already reaches the Stop hook.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/overseer_stop.py:588-591` — `_claimed_unit` computes `edited` as false and returns None, so `_main_fresh` makes no request and passes the turn through.
- Why it happened: the "code was edited" half of the trigger is read from the NAME of the tool in the transcript (`EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}`, line 96), on the assumption that a file is only ever written by one of those tools. A file written by a shell command (`cat > file`, a script with `open().write`, `sed -i`, `git apply`, a code generator) changes the tree exactly as much and leaves no such call. The hook never looked at the tree.
- Same places: `grep -rn "EDIT_TOOLS\|Edit|Write" .claude/hooks .claude/settings.json` and every handler of `.claude/settings.json` bound to the edit tools.
  - `overseer_verdict.py:255` (`render_evidence`) — lists Bash calls with their command and output too; nothing is lost. Not the same cause.
  - `overseer_verdict.py:421` (the guard refuses the edit tools inside the overseer agent) — the agent has Bash and could write with it, but `record` compares the tree's fingerprint with the request's and records INVALID on any difference (line 631). Covered by another mechanism.
  - `format-on-edit.sh` (PostToolUse `Edit|Write|MultiEdit`) — a file written by shell is not formatted on the spot; the Stop gate lints the changed files from git, whoever wrote them. A convenience lost, no hole.
  - `protect-paths.sh` (PreToolUse `Edit|Write|MultiEdit`) — the SAME assumption, and a hole: shown below, `block-dangerous.sh` lets `printf x > .claude/constitution.md`, `echo {} > .claude/settings.json`, `sed -i … .github/workflows/ci.yml` and `cat .env` through (exit 0 for each). Not fixable inside this budget and not by the same means (it must decide BEFORE the command runs, from the command's text): a new board task, see section 5.

## 5. Fix
- The decision, in short (the task asked for it before the fix). The edit signal is read from the tree as well as from the tool's name. "The state at the start of the turn" is recorded nowhere, and recording it needs a new handler in `.claude/settings.json` (UserPromptSubmit), which is the owner's file. What IS recorded is the tree every audit request saw (`request.json`, field `tree`: HEAD plus status and content hash of each changed file — written at the request and again at the agent's launch). So the baseline is "what the last audit request saw", which is also the better question: is there code no audit request has seen. Rejected: parsing the shell command for writes (`>`, `tee`, `sed -i`, a script — unbounded, and it misses every script); file mtimes against the turn's start (deletions and the `__pycache__` of a test run confuse it, and the test transcripts carry no timestamps); "any dirty code file" (after a PASS in an attended session the tree stays dirty until the human commits, so every later claim would be audited again).
- What changed: `.claude/hooks/overseer_stop.py` — `_claimed_unit` counts the unit as edited when an edit tool touched a code path (as before) OR `_code_changed_in_tree` says so (a private helper, +33 lines with its docstring and the module docstring's sentence): a code path whose content differs from the hash the last request recorded, or that is changed now and was clean then, or that differs between the request's commit and HEAD (`git diff --name-only`); with no request yet in the project — a code path among `gate_allows.unit_files` (changed since the last accepted PASS / the slice's base / the fork from main / HEAD). Any error there reads as "no signal from the tree": the hook must not break a turn. `tests/test_overseer_fresh.py` — the section «code written by a shell command (board 707)», eight cases; the helpers `transcript` / `claim` / `audit` take `shell=`. `.claude/references/hooks.md:16` and `.claude/engine-rules.md` (Overseer protocol, the first item) — the trigger's description: the code changed since the last audit request, by any tool; the verification command in the same turn.
- The cases: three fail without the fix (the unit written by shell; a fix by shell after a BLOCK; code written by shell and already committed). Five negatives pass on both sides: after a BLOCK a claim over the same tree asks for nothing; after a SECOND request the same (the baseline is the last request, not the first); code an audit saw and that was committed unchanged is not a new edit; a document written by shell is not code; a turn that only ran commands asks for nothing. The two that could pass for the wrong reason were checked by breaking the fix on purpose: with the content comparison replaced by `True` exactly the first two negatives fail; with the commit comparison removed exactly "already committed" fails.
- After the first audit (BLOCK #4, request 20261006T025745Z-f12eee: nothing told the newest request from the oldest as the baseline — `max` replaced by `min` survived the suite): the case «the baseline is the LAST request» was added, and it fails on that mutant; the newest request is now chosen by the file's modification time, not by the order of names (two ids made in one second differ only by a hash). The proof of section 6 was run again after this, same first line.
- What it changes beyond the bug, deliberately: a claim now also triggers when the code was changed in an EARLIER turn that claimed nothing (work in progress, then "tests pass, unit complete" in the next turn). Before, that claim was silently unaudited as well — the session of board 706 had to ask for its audit by hand for this reason.
- Known limits, left as they are: (1) with no `SOURCE_DIRS` and no `CODE_EXTENSIONS` every file is a code path, as it always was for the edit tools — there the ledger or a note written after an audit counts as a change too; (2) in a project with no audit request yet, sitting on its main branch, code written by shell AND committed before the first claim is not seen (the baseline is HEAD); from the first request on, commits are compared.
- The reproduction of section 2 with the fix: `--- written with Bash:` → `{"decision": "block", "reason": "OVERSEER_REQUEST 20261006T025451Z-1e0b47 (auto-triggered by the Stop hook on a unit-com…`.
- Budget: `complexity_budget.py check` → within budget: 0 new files, +33 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies.
- The neighbour that became a task: `tasks/todo/714-open-item-707-protect-paths-shell-write.md` (protected paths can be written by a shell command).
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 22daba69f2c2cc2e6ad110f5dac1a93194e2f0b6
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Command: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/002-overseer-bash-edit.md --test tests/test_overseer_fresh.py --cmd "python3 tests/test_overseer_fresh.py" --expect "FAIL a unit whose code was written by a shell command gets its audit request"`

````
PROVED: tests/test_overseer_fresh.py fails on 22daba6 and passes on the working tree; the failure shows «FAIL a unit whose code was written by a shell command gets its audit request»
  command: python3 tests/test_overseer_fresh.py
  the fix: .claude/hooks/overseer_stop.py, .engine/bugs/002-overseer-bash-edit.md
  before the fix: exit 1
    |   ok   the LAST handback is the answer
    |   ok   negative — a handback that holds no JSON object is refused as before
    |   ok   negative — no message and no transcript: refused, nothing recorded
    |   ok   negative — where the envelope carries the message, the message is the answer and the transcript is not read
    | 
    | == code written by a shell command (board 707)
    |   FAIL a unit whose code was written by a shell command gets its audit request (seen live: the turn ended unaudited)
    |   ok   negative — after a BLOCK, a claim over the tree that audit already saw asks for nothing
    |   FAIL a fix made by a shell command after a BLOCK is audited again
    |   FAIL code written by shell and already committed is still a code edit
    |   ok   negative — code an audit saw, committed unchanged since, is not a new edit
    |   ok   negative — a document written by shell is not a code edit
    |   ok   negative — a turn that only ran commands and changed nothing asks for nothing
    | 
    | FAIL (3): a unit whose code was written by a shell command gets its audit request (seen live: the turn ended unaudited); a fix made by a shell command after a BLOCK is audited again; code written by shell and already committed is still a code edit
  with the fix: exit 0
    |   ok   the LAST handback is the answer
    |   ok   negative — a handback that holds no JSON object is refused as before
    |   ok   negative — no message and no transcript: refused, nothing recorded
    |   ok   negative — where the envelope carries the message, the message is the answer and the transcript is not read
    | 
    | == code written by a shell command (board 707)
    |   ok   a unit whose code was written by a shell command gets its audit request (seen live: the turn ended unaudited)
    |   ok   negative — after a BLOCK, a claim over the tree that audit already saw asks for nothing
    |   ok   a fix made by a shell command after a BLOCK is audited again
    |   ok   code written by shell and already committed is still a code edit
    |   ok   negative — code an audit saw, committed unchanged since, is not a new edit
    |   ok   negative — a document written by shell is not a code edit
    |   ok   negative — a turn that only ran commands and changed nothing asks for nothing
    | 
    | PASS: the fresh-context overseer protocol holds, every protection with its negative case
````

## 7. Gate and overseer
- Gate: <the result of the turn-end checks — no worse than it was>
- Overseer: <the verdict and its ledger entry>
- The regression test stays in the suite: <path::name>

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: <which, and one sentence>
- Queued: <the line `lesson_queue.py add` printed>
