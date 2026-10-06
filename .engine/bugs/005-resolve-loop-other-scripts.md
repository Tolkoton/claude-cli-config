# Bug 005-resolve-loop-other-scripts

type: bugfix
status: reproduced
<!-- status: reproduced → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «Чотири місця зводять поданий шлях через resolve() без жодного try … Наслідок — traceback замість написаної відмови скрипта; нічого не псується» (tasks/doing/718-open-item-716-resolve-loop-other-scripts.md; found by the search for the same places of bug 004, `.engine/bugs/004-symlink-loop-traceback.md` section 4).
- Expected: a given path that is a symlink loop (`loop -> loop`) gets the ordinary refusal each script already has for a path that is not a file; no traceback.
  - `bugfix.py prove|pins --test <loop>` → exit 2, `the test file <name> is not a file of this project`.
  - `goals.py check <absolute loop>` → exit 3, `REFUSED: <path>: no such file`.
  - `lesson_queue.py promote`, counting the context: an `@import` that is a loop is not a file and adds no lines; the count goes on.
  - `board.py start <loop>` → exit 2, `<given> is not a task file in tasks/todo/`.
- Where the expected is written: `.claude/hooks/bugfix.py:113,118` (the docstring "each must be a file of the working tree" and the refusal); `.claude/hooks/goals.py:351-352` (`no such file`); `.claude/hooks/lesson_queue.py:455` (`if path in seen or not path.is_file(): return` — what is not a file is not counted) with `tests/test_context_budget.py:63-64`, the count it says it repeats; `.claude/unattended/board.py:418-419` (the refusal); the task 718, «Що зробити»: «шлях-петля дає звичайну відмову цього скрипта, а не traceback».
- Added by the first audit (section 7), the same symptom in two more places: `board.py audit-allowed --tasks-dir <loop>` — expected the ordinary `paid audit not allowed: no task of this session is in …/doing/` (`.claude/unattended/board.py:905`), as for a directory that does not exist; and the context count over a CLAUDE.md that is itself a loop — expected 0 lines, as for a missing CLAUDE.md (`lesson_queue.py:455`).
- Actual: `RuntimeError: Symlink loop from '<path>'` leaves `Path.resolve()`; each of the four commands ends in a traceback with exit 1. Nothing is written or moved before it — it fails to the safe side.
- Where it was seen: Python 3.12.13 on this server. The loop has to lie in the repository already; the paths come from the operator's or the agent's own command line and from the project's own CLAUDE.md, not from a model's answer.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: a fresh repository `/tmp/b718-Jb3k` with `tests/loop.py -> loop.py`, `tasks/todo/005-loop.md -> 005-loop.md`, `loop.md -> loop.md` and a CLAUDE.md that says `@loop.md`; then `python3 .claude/hooks/bugfix.py --root . prove --test tests/loop.py --cmd true`, `python3 .claude/unattended/board.py --root . start tasks/todo/005-loop.md`, and `lesson_queue.context_lines(root)` called from `python3 -c`. The fourth, `goals.py check <absolute path of docs/adr/loop.md>`, needs a sealed goals document, so it was reproduced by the scene of `tests/test_goals.py` (section 3) — its output is the same line.
- Output (the last line of each traceback):
  ```
  == bugfix
  RuntimeError: Symlink loop from '/tmp/b718-Jb3k/tests/loop.py'
  == board
  RuntimeError: Symlink loop from '/tmp/b718-Jb3k/tasks/todo/005-loop.md'
  == lesson
  RuntimeError: Symlink loop from '/tmp/b718-Jb3k/loop.md'
  == goals (python3 tests/test_goals.py)
  FAIL refused: an absolute path that is a symlink loop — no such file, not a traceback (board 718)   … line 1252, in resolve … RuntimeError: Symlink loop from '…/docs/adr/loop.md'
  ```
- Result: reproduced

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
One case per place, each through the command the user types (the level where the traceback is seen):
- `tests/test_bugfix.py`, section «prove» — «a --test path that is a symlink loop is refused, not a traceback (board 718)», with a negative next to it (a path that does not exist is refused the same way; green from the start).
- `tests/test_goals.py`, section «check: citations» — «refused: an absolute path that is a symlink loop — no such file, not a traceback (board 718)», with a negative (an absolute path to a real decision is still checked; green from the start). Only an absolute argument reaches `resolve()` there, so the case gives one.
- `tests/test_lesson_queue.py` — «an @import that is a symlink loop counts as no file: the budget still refuses, no traceback (board 718)»: CLAUDE.md of 200 lines whose first import is the loop, `promote` must still answer with the refusal about 200 lines.
- `tests/test_board.py` — «start of a symlink loop (relative|absolute) is refused, not a traceback (board 718)», two cases: the line has two `resolve()` calls, one for each kind of argument.
- Added after the first audit (section 7), each red before its fix: `tests/test_board.py`, section «audit-allowed» — «--tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 718)» (`PASS 266   FAIL 1`); `tests/test_lesson_queue.py` — «a CLAUDE.md that is a symlink loop counts as no file, like a missing one: 0 lines, no traceback (board 718)», at the level of `context_lines` itself (`PASS 100   FAIL 1`): through `promote` a count of 0 would let the promotion through and change the scene for the cases after it. Both failed with the tail of the same traceback (`line 1252, in resolve`).
- The negative of the goals suite was made to need resolving (the path is given as `…/docs/adr/../adr/0001-cache.md` and must be answered as `docs/adr/0001-cache.md`): the first audit showed the earlier one passed with no resolving at all.
- Commands: `python3 tests/test_bugfix.py`; `python3 tests/test_goals.py`; `python3 tests/test_lesson_queue.py`; `python3 tests/test_board.py`
- They fail with (before the fix; the detail of each is the tail of the traceback, ending in `RuntimeError: Symlink loop from …`):
  ```
  FAIL a --test path that is a symlink loop is refused, not a traceback (board 718)      PASS 76   FAIL 1
  FAIL start of a symlink loop (relative) is refused, not a traceback (board 718)
  FAIL start of a symlink loop (absolute) is refused, not a traceback (board 718)        PASS 264   FAIL 2
  FAIL refused: an absolute path that is a symlink loop — no such file, not a traceback (board 718)   PASS 86   FAIL 1
  FAIL an @import that is a symlink loop counts as no file: the budget still refuses, no traceback (board 718)   PASS 99   FAIL 1
  ```
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — every suite already reaches its command.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/bugfix.py:116` (`test_files`), `.claude/hooks/goals.py:350` (`cmd_check`), `.claude/hooks/lesson_queue.py:463` (`context_lines.walk`), `.claude/unattended/board.py:417` (`cmd_start`) — a `Path.resolve()` of a given path, outside any `try`.
- Why it happened: each place treats `resolve()` as a call that cannot fail and leaves the judgement to the `is_file()` on the next line — true for a missing file, a directory, a link that leads outside. But up to Python 3.12 a non-strict `resolve()` reports a symlink loop as a bare `RuntimeError` (from 3.13 it raises nothing there — the documentation of pathlib, `Path.resolve`: «Changed in version 3.13: Symlink loops are treated like other errors: OSError is raised in strict mode, and no exception is raised in non-strict mode. In previous versions, RuntimeError is raised no matter the value of strict.» — https://docs.python.org/3.13/library/pathlib.html; so `except RuntimeError` is the whole of what a non-strict `resolve()` can raise on a loop, and on 3.13 the new cases are green without the fix), so the script never gets to the line that holds its refusal. `is_file()` itself answers False for a loop (ELOOP is among the errors pathlib ignores there).
- Same places — two searches, and what each covers.
  - The scope of THIS fix is the engine's hooks, the board scripts and the installer: `grep -n "resolve()" .claude/hooks/*.py .claude/unattended/*.py engine.py | grep -v __file__` — 27 lines at the base commit, 26 in the tree with the fix (one of them a docstring, `overseer_stop.py:107`), every one read and named below; outside the four of the task the line numbers are those of the tree at the first audit. The first version of this section took the list of record 004 on trust («exactly these four»), and the first audit reproduced two more inside this scope.
  - The second version called that list «the whole search», and the second audit (section 7) reproduced the same cause OUTSIDE the scope. The search over everything the repository ships — `git ls-files --cached --others --exclude-standard | grep -v ^tests/`, lines with `resolve(`, `realpath` or `readlink -f`, Markdown and the records under `.engine/`, `tasks/`, `docs/` dropped — adds these, and none of them is fixed here: `.claude/skills/documentation/scripts/doc_audit.py:54,152`; `evals/environment.py:78`; `evals/run_audit_scenarios.py:387,649,709`; `evals/run_gate_evals.py:168`; `evals/run_hook_scenarios.py:115,116,210,211,216,349,356`; `evals/run_simplifier_evals.py:84`; and `evals/scenarios/simplifier/project/src/refproj/receipts.py:9,10` with its test — the code of a reference project the simplifier is measured on, a fixture, not the engine's code. (`engine.py:444…1461` and `lesson_queue.py:415,747` match `resolve(` as the name of their own functions, not a path.) No shell script resolves a path this way. They became one board task, `tasks/todo/719-open-item-718-resolve-loop-outside-hooks.md`, which names each line, says which two the audit reproduced (`doc_audit.py:152`, `run_audit_scenarios.py:649`) and which are read only: seven more places with seven more red-first cases, in four more files and with no suite at all yet for `doc_audit.py` (`grep -rl doc_audit tests` finds nothing; the paid-run refusal has `tests/test_paid_run_gate.py`), are a second fix, not the tail of this one.
  - Fixed here, each with its failing case: the four of the task — `bugfix.py:116`, `goals.py:350`, `lesson_queue.py:463`, `board.py:417` (line numbers of the base commit) — and the two the audit found: `board.py:1214` (`audit-allowed --tasks-dir <loop>`: a path given on the command line; a missing directory gets `paid audit not allowed: no task of this session is in …/doing/`, a loop got the traceback) and `lesson_queue.py:469` (`context_lines` on a CLAUDE.md that is itself a loop: a missing CLAUDE.md counts 0, a loop raised).
  - Already answered: `simplifier.py:132` (record 004); `contract_fingerprint.py:114` — line 111 refuses what is not a file before the `resolve()` (`is_file()` is False for a loop; the audit probed it: `no such contract`).
  - The project root itself, not a path inside it — left alone: `bugfix.py:120,122` (`root.resolve()`), `contract_fingerprint.py:37,39`, `goals.py:254,256`, `overseer_stop.py:110,117`, `park-ask-gated.py:87,94`, `overseer_verdict.py:101,105` (`CLAUDE_PROJECT_DIR` or git's top level), `board.py:1129`, `settings_check.py:110`, `owner_action.py:289` (`--root`), `engine.py:625,626` (the project and the engine's own directory). A root that is a link to itself is a project that does not exist: no script has a written answer for it, and git has none either.
  - `board.py:421` — `(board.tasks / "todo").resolve()`, the board's own column, not a given path: with `tasks/todo` a link to itself every command of the board fails, and the board has no written answer for a board without its columns. Left alone.
  - Outside working code: `tests/test_context_budget.py:68,75` — the count `context_lines` repeats, a test over this repository's own CLAUDE.md; a loop there fails that suite loudly, which is what a test is for. Not touched.

## 5. Fix
- What changed:
  - `.claude/hooks/bugfix.py` (`test_files`) — `resolve()` in a `try`; on `RuntimeError` the path stays as written, and the `is_file()` of the next line (False for a loop) gives the refusal already there.
  - `.claude/unattended/board.py` (`cmd_start`) — the same: on `RuntimeError` the source is `root / given`, which is not a file, so the refusal already there answers. (`main`, `audit-allowed`) — `--tasks-dir` goes through `os.path.realpath` instead of `resolve()` (`os` was already imported): a loop is then a directory with no `doing/`, and `audit_refusal` gives its ordinary «no task of this session».
  - `.claude/hooks/lesson_queue.py` (`context_lines.walk`) — `walk` now resolves the path it is given itself, in a `try`, and returns on a loop like on anything that is not a file; its two callers (CLAUDE.md, each import) pass the path unresolved. One `try` for both places, and it holds only the `resolve()`, not the recursion.
  - `.claude/hooks/goals.py` (`cmd_check`) — the two `path.resolve()` of the line became one `os.path.realpath(path)` (which does not raise on a loop; `os` was already imported), so `(root / rel).is_file()` below answers «no such file». Not a `try` like the other three: a `try` there took `cmd_check` from 15 to 16 branches and the budget script refused it (`max_cyclomatic_per_function: 13 allowed, exceeded by .claude/hooks/goals.py:cmd_check = 16`); this form adds none. For a path that is not a loop `realpath` and a non-strict `resolve()` give the same answer — the negative case «an absolute path to a decision of the project is still checked» holds that.
  - `tests/test_bugfix.py`, `tests/test_goals.py`, `tests/test_lesson_queue.py`, `tests/test_board.py` — the cases of section 3.
- The reproduction of section 2 with the fix (same repository):
  ```
  bugfix.py: the test file tests/loop.py is not a file of this project
  board: tasks/todo/005-loop.md is not a task file in tasks/todo/
  context_lines -> 2
  ```
  And the two of the audit, in the same repository: `board.py --root . audit-allowed --tasks-dir loop.md` → `paid audit not allowed: no task of this session is in /tmp/b718-Jb3k/loop.md/doing/`; with `CLAUDE.md -> CLAUDE.md`, `context_lines` → `0`.
- Mutant, working tree restored after it: `real = path` in `goals.py` (no resolving) → `FAIL negative — an absolute path to a decision of the project is still resolved and checked` — the equivalence of `realpath` with the `resolve()` it replaced is now held by a case, not by reading.
- Budget: `python3 .claude/hooks/complexity_budget.py check` → `Complexity budget: within budget` — production: 0 new files, +11 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies; tests: +39 lines.
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 98fc93eda0f57d44db4b87726970da129b5b6d3f
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Four proofs, one per place. The first runs its suite with a private `TMPDIR`: `tests/test_bugfix.py` has a case «the temporary copies are removed» that looks for any `bugfix-prove-*` in the temporary directory, and inside a proof the copy of the proof itself is there — with the plain command the answer was `REFUSED: the test still fails on the code with the fix` for that case alone (`PASS 76   FAIL 1`, `FAIL the temporary copies are removed   [PosixPath('/tmp/bugfix-prove-jpzkwtgb')]`). That is the suite meeting its own tool, not this bug; the private directory keeps the two apart and changes nothing else.

Run again after the second fix, on the tree as it is staged; the lesson-queue and board proofs now expect the cases added after the first audit (the earlier cases of the same suites are in the same run: each suite goes from FAIL to `FAIL 0`).

`python3 .claude/hooks/bugfix.py prove --record .engine/bugs/005-resolve-loop-other-scripts.md --test tests/test_bugfix.py --cmd "TMPDIR=$(mktemp -d) python3 tests/test_bugfix.py" --expect "FAIL a --test path that is a symlink loop is refused, not a traceback (board 718)"`

````
PROVED: tests/test_bugfix.py fails on 98fc93e and passes on the working tree; the failure shows «FAIL a --test path that is a symlink loop is refused, not a traceback (board 718)»
  command: TMPDIR=$(mktemp -d) python3 tests/test_bugfix.py
  the fix: .claude/hooks/bugfix.py, .claude/hooks/goals.py, .claude/hooks/lesson_queue.py, .claude/unattended/board.py, .engine/bugs/005-resolve-loop-other-scripts.md, .engine/lesson-queue.md, .engine/overseer/ledger.md, tests/test_board.py, tests/test_goals.py, tests/test_lesson_queue.py
  before the fix: exit 1
    |   ok   the cause: where it showed, why it happened, the same places
    |   ok   the budget section is the ready small budget: 0 files, 40 lines, 0 names, 0 abstractions, 0 dependencies
    |   ok   the template says the 40 is a signal, not a ceiling
    |   ok   the lesson: the four answers
    |   ok   the template and the script ship with the engine; a bug record is the project's
    | the overseer and the documents
    |   ok   the overseer: a bug record named in PROGRESS.md is the contract of the work
    |   ok   the overseer reruns the proof instead of believing the pasted one
    |   ok   hooks.md has the script's row
    |   ok   the delete guard's first way through names the script
    |   ok   the limits say what the proof does not give
    |   ok   the engine's AGENTS.md names the command
    |   ok   the budget reference says a bug record carries a budget too
    | 
    | PASS 76   FAIL 1
  with the fix: exit 0
    |   ok   the cause: where it showed, why it happened, the same places
    |   ok   the budget section is the ready small budget: 0 files, 40 lines, 0 names, 0 abstractions, 0 dependencies
    |   ok   the template says the 40 is a signal, not a ceiling
    |   ok   the lesson: the four answers
    |   ok   the template and the script ship with the engine; a bug record is the project's
    | the overseer and the documents
    |   ok   the overseer: a bug record named in PROGRESS.md is the contract of the work
    |   ok   the overseer reruns the proof instead of believing the pasted one
    |   ok   hooks.md has the script's row
    |   ok   the delete guard's first way through names the script
    |   ok   the limits say what the proof does not give
    |   ok   the engine's AGENTS.md names the command
    |   ok   the budget reference says a bug record carries a budget too
    | 
    | PASS 77   FAIL 0
````

`python3 .claude/hooks/bugfix.py prove --record .engine/bugs/005-resolve-loop-other-scripts.md --test tests/test_goals.py --cmd "python3 tests/test_goals.py" --expect "FAIL refused: an absolute path that is a symlink loop — no such file, not a traceback (board 718)"`

````
PROVED: tests/test_goals.py fails on 98fc93e and passes on the working tree; the failure shows «FAIL refused: an absolute path that is a symlink loop — no such file, not a traceback (board 718)»
  command: python3 tests/test_goals.py
  the fix: .claude/hooks/bugfix.py, .claude/hooks/goals.py, .claude/hooks/lesson_queue.py, .claude/unattended/board.py, .engine/bugs/005-resolve-loop-other-scripts.md, .engine/lesson-queue.md, .engine/overseer/ledger.md, tests/test_board.py, tests/test_bugfix.py, tests/test_lesson_queue.py
  before the fix: exit 1
    |   ok   no sign of an e-mail address
    |   ok   no sign of a link
    |   ok   no sign of a phone number
    |   ok   no sign of a sum of money
    |   ok   the check catches an e-mail address
    |   ok   the check catches a link
    |   ok   the check catches a phone number
    |   ok   the check catches a sum of money
    |   ok   the reference says where its lines come from
    |   ok   the seed has every section and no line of its own
    |   ok   the goals document is the project's, seeded once
    |   ok   a simplifier finding about the goals document is protected and never automatic
    |   ok   …while the same finding about another record may be automatic
    | 
    | PASS 86   FAIL 1
  with the fix: exit 0
    |   ok   no sign of an e-mail address
    |   ok   no sign of a link
    |   ok   no sign of a phone number
    |   ok   no sign of a sum of money
    |   ok   the check catches an e-mail address
    |   ok   the check catches a link
    |   ok   the check catches a phone number
    |   ok   the check catches a sum of money
    |   ok   the reference says where its lines come from
    |   ok   the seed has every section and no line of its own
    |   ok   the goals document is the project's, seeded once
    |   ok   a simplifier finding about the goals document is protected and never automatic
    |   ok   …while the same finding about another record may be automatic
    | 
    | PASS 87   FAIL 0
````

`python3 .claude/hooks/bugfix.py prove --record .engine/bugs/005-resolve-loop-other-scripts.md --test tests/test_lesson_queue.py --cmd "python3 tests/test_lesson_queue.py" --expect "FAIL a CLAUDE.md that is a symlink loop counts as no file, like a missing one: 0 lines, no traceback (board 718)"`

````
PROVED: tests/test_lesson_queue.py fails on 98fc93e and passes on the working tree; the failure shows «FAIL a CLAUDE.md that is a symlink loop counts as no file, like a missing one: 0 lines, no traceback (board 718)»
  command: python3 tests/test_lesson_queue.py
  the fix: .claude/hooks/bugfix.py, .claude/hooks/goals.py, .claude/hooks/lesson_queue.py, .claude/unattended/board.py, .engine/bugs/005-resolve-loop-other-scripts.md, .engine/lesson-queue.md, .engine/overseer/ledger.md, tests/test_board.py, tests/test_bugfix.py, tests/test_goals.py
  before the fix: exit 1
    |   ok   the negative case: two failures write nothing
    |   ok   the third writes one entry under the task in doing/: what, what was done, and that a hook wrote it
    |   ok   a project without a board: the protocol is still given and no tasks/ directory appears
    | the hooks that carry it: Stop gate, overseer hook
    |   ok   the Stop gate blocks (precondition)
    |   ok   ...and the block reached the lesson queue without a model
    |   ok   the same block again does not duplicate the candidate
    |   ok   the gate hands the stuck protocol over on the third identical block (in the reason or the escalation)
    |   ok   negative — a PASS typed by the builder closes no unit: no continue, no review request
    |   ok   PASS with an empty queue: the continue text is exactly what it always was
    |   ok   PASS with a non-empty queue appends the triage request to the continue text
    |   ok   an OVERSEER_BLOCK verdict is queued when it is recorded
    |   ok   a verdict that is not a PASS gets no review request
    | 
    | PASS 99   FAIL 2
  with the fix: exit 0
    |   ok   the negative case: two failures write nothing
    |   ok   the third writes one entry under the task in doing/: what, what was done, and that a hook wrote it
    |   ok   a project without a board: the protocol is still given and no tasks/ directory appears
    | the hooks that carry it: Stop gate, overseer hook
    |   ok   the Stop gate blocks (precondition)
    |   ok   ...and the block reached the lesson queue without a model
    |   ok   the same block again does not duplicate the candidate
    |   ok   the gate hands the stuck protocol over on the third identical block (in the reason or the escalation)
    |   ok   negative — a PASS typed by the builder closes no unit: no continue, no review request
    |   ok   PASS with an empty queue: the continue text is exactly what it always was
    |   ok   PASS with a non-empty queue appends the triage request to the continue text
    |   ok   an OVERSEER_BLOCK verdict is queued when it is recorded
    |   ok   a verdict that is not a PASS gets no review request
    | 
    | PASS 101   FAIL 0
````

`python3 .claude/hooks/bugfix.py prove --record .engine/bugs/005-resolve-loop-other-scripts.md --test tests/test_board.py --cmd "python3 tests/test_board.py" --expect "FAIL --tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 718)"`

````
PROVED: tests/test_board.py fails on 98fc93e and passes on the working tree; the failure shows «FAIL --tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 718)»
  command: python3 tests/test_board.py
  the fix: .claude/hooks/bugfix.py, .claude/hooks/goals.py, .claude/hooks/lesson_queue.py, .claude/unattended/board.py, .engine/bugs/005-resolve-loop-other-scripts.md, .engine/lesson-queue.md, .engine/overseer/ledger.md, tests/test_bugfix.py, tests/test_goals.py, tests/test_lesson_queue.py
  before the fix: exit 1
    |   ok   the answer 'так, але коротше': an instruction for the agent, nothing for the runner
    |   ok   the answer 'ні, перепиши': an instruction for the agent, nothing for the runner
    |   ok   the answer 'такий текст не годиться': an instruction for the agent, nothing for the runner
    |   ok   the answer 'закрити': an instruction for the agent, nothing for the runner
    |   ok   an answer that is an instruction goes back to todo/ like any answered task
    |   ok   «так»: owner-actions lists promote-rule with the sha256 of the rule; unblock leaves it to the runner
    |   ok   …action-done applied: straight to done/ with the runner's report, the offer replaced, the answer kept
    |   ok   «ні»: owner-actions lists reject-rule with the sha256 of the rule; unblock leaves it to the runner
    |   ok   …action-done applied: straight to done/ with the runner's report, the offer replaced, the answer kept
    |   ok   action-done failed: the task stays for the agent with the reason, and the same «так» promotes nothing
    |   ok   action-done stale: the task stays for the agent with the reason, and the same «так» promotes nothing
    |   ok   action-reject wipes «ні» written on the server as well, and keeps the offer
    |   ok   reject-rule cannot be offered by hand: it is only the owner's «ні» under a rule question
    | 
    | PASS 264   FAIL 3
  with the fix: exit 0
    |   ok   the answer 'так, але коротше': an instruction for the agent, nothing for the runner
    |   ok   the answer 'ні, перепиши': an instruction for the agent, nothing for the runner
    |   ok   the answer 'такий текст не годиться': an instruction for the agent, nothing for the runner
    |   ok   the answer 'закрити': an instruction for the agent, nothing for the runner
    |   ok   an answer that is an instruction goes back to todo/ like any answered task
    |   ok   «так»: owner-actions lists promote-rule with the sha256 of the rule; unblock leaves it to the runner
    |   ok   …action-done applied: straight to done/ with the runner's report, the offer replaced, the answer kept
    |   ok   «ні»: owner-actions lists reject-rule with the sha256 of the rule; unblock leaves it to the runner
    |   ok   …action-done applied: straight to done/ with the runner's report, the offer replaced, the answer kept
    |   ok   action-done failed: the task stays for the agent with the reason, and the same «так» promotes nothing
    |   ok   action-done stale: the task stays for the agent with the reason, and the same «так» promotes nothing
    |   ok   action-reject wipes «ні» written on the server as well, and keeps the offer
    |   ok   reject-rule cannot be offered by hand: it is only the owner's «ні» under a rule question
    | 
    | PASS 267   FAIL 0
````

## 7. Gate and overseer
- Gate: <the result of the turn-end checks — no worse than it was>
- Overseer: <the verdict and its ledger entry>
- The regression test stays in the suite: <path::name>

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: a test was missing — every one of the four had a case for a path that does not exist and none for a link to itself, the one input where `resolve()` raises before the script reaches its refusal.
- Queued: `#4a47fe08 added`
