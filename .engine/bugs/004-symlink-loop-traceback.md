# Bug 004-symlink-loop-traceback

type: bugfix
status: fixed
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «ціль, посилання в доказах або названий у твердженні шлях, що вказує на петлю символьних посилань усередині проєкту (loop -> loop), піднімає RuntimeError із _project_ref … simplifier.validate і second_opinion.may_send тоді падають із traceback, хоча старий код таку знахідку просто відхиляв» (tasks/doing/716-open-item-708-symlink-loop-traceback.md; found by the overseer in audit 20261006T041920Z-f8021c).
- Expected: a target or an evidence reference that is a symlink loop is rejected like any other path that is not a file of the repository, with the validator's ordinary error; `may_send` answers «do not send» for it. No traceback.
- Where the expected is written: `.claude/hooks/simplifier.py:129-130` (the docstring of `_project_ref`: "None: not a reference, or it leads outside the project" — it answers, it does not raise); `simplifier.py:24` ("a file:line that exists") and the validator's error text "is not a file of this repository"; `second_opinion.py:106` ("never a file outside the project"); the task 716, «Що зробити»: «ціль і ref на петлю посилань відхиляються як „не файл цього репозиторію“, may_send для неї повертає „не надсилати“».
- Actual: `RuntimeError: Symlink loop from '<path>'` leaves `_project_ref`; `simplifier.validate` and `second_opinion.may_send` (and through it `review`) end in a traceback. Nothing is accepted and nothing is sent — it fails to the safe side — but the whole answer of the agent is lost with the one finding.
- Where it was seen: Python 3.12.13 on this server; the overseer's audit of bug 003 (`.engine/bugs/003-validator-absolute-path.md`, section 7, note 1). The loop has to lie in the repository already: the simplifier agent has no tool to create one.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: a fresh repository `/tmp/b716/proj` (`src/a.py`, `.claude/project.env`, `src/loop -> loop`, `src/link.py -> ../../out/o.py` outside it); `python3 /tmp/b716/repro.py` calls `simplifier.validate(root, [finding], set())` with the target, then an evidence reference, on the loop, and `second_opinion.may_send(root, {}, …)` on the loop and on the link that leads outside.
- Output:
  ```
  target loop -> TRACEBACK RuntimeError Symlink loop from '/tmp/b716/proj/src/loop'
  ref loop -> TRACEBACK RuntimeError Symlink loop from '/tmp/b716/proj/src/loop'
  may_send loop -> TRACEBACK RuntimeError Symlink loop from '/tmp/b716/proj/src/loop'
  may_send link out -> False
  ```
  The first three are the bug; the fourth is the side effect of record 003 the task asks to hold by a test, and it already behaves as specified.
- Result: reproduced

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
- Test: `tests/test_simplifier.py`, section «PATH-*», the two cases marked «board 716» — at the level of the validator's function (`simplifier.validate`): a target, and an evidence reference, that is a link to itself. The neighbouring module the task names: `tests/test_second_opinion.py`, the four cases marked «board 716» — `may_send` on the loop, `review` of a finding whose target is the loop, and two that hold the side effect of record 003 (below).
- Command that runs it: `python3 tests/test_simplifier.py`; `python3 tests/test_second_opinion.py`
- It fails with: `FAIL a target that is a symlink loop is rejected, not a traceback (board 716)` — detail `{'traceback': 'RuntimeError("Symlink loop from \'…/src/demo/loop.py\'")'}`, the symptom of section 1 (the test catches the exception only to print it as a FAIL instead of ending the suite); the same for the evidence reference. In the second suite: `FAIL a symlink loop is not sent, and is no traceback (board 716)` and `FAIL a target that is a symlink loop gets no request (board 716)`, both with the same `RuntimeError`.
- Not red, and said so: the two side-effect cases — «a link the claim names that leads outside the project is not sent» and «a git grep hit on a link that leads outside the project is not sent» — pass on the code as it is, because record 003 already made `may_send` judge the resolved path; the task asks for them as the missing test of that side effect, not as a bug. What they are worth is shown by a mutant in section 5, not by the proof of section 6. `git grep` in a working tree never reads a link (checked in `/tmp/b716/proj`: no hit on a word that stands only in the link's target), so the grep case feeds `collect` such a hit through a wrapped `budget.git`; the route that really reaches a link is the claim naming it.
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — both suites already reach the code.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/simplifier.py:132` — `(root / match["path"]).resolve()` inside `_project_ref`; the exception passes the `except (OSError, ValueError)` of line 133 and leaves through `_project_paths` → `validate`, `reference_exists`, and `second_opinion.may_send`.
- Why it happened: the `except` lists what `Path.resolve()` was believed to raise — `OSError` for the file system, `ValueError` from `relative_to` — but up to Python 3.12 a non-strict `resolve()` reports a symlink loop as a bare `RuntimeError`, which is neither (3.13 changed it to an `OSError`). Fix 003 replaced a plain `is_file()` (false for a loop, so the finding was rejected) with `resolve()` and nobody put a loop against it: the cases of 003 had links that lead somewhere.
- Same places: searched `grep -n "resolve()" .claude/hooks/*.py .claude/unattended/*.py engine.py`, dropped the `Path(__file__)` and project-root lines, and read every hit that resolves a path somebody gave.
  - `second_opinion.py:107` (`may_send`) — not a separate place: it calls `_project_ref`, and is fixed with it; it gets its own cases.
  - `bugfix.py:116` (`test_files`, the `--test` argument), `goals.py:350` (a path argument of the decision check), `lesson_queue.py:463` (an `@import` of CLAUDE.md when the budget of the context is counted), `board.py:417` (the task file given to `start`) — the same fact about `resolve()`, with no `try` at all around it: a loop there is a traceback where the script has a written refusal (confirmed for `bugfix.test_files(root, ["src/loop"])` → `RuntimeError: Symlink loop`). Their paths come from the operator's or the agent's own command line and from the project's own files, not from a model's answer, each needs its own failing test, and four more files do not fit a fix of one line — a new task on the board (section 5 names it), not touched here.

## 5. Fix
- What changed:
  - `.claude/hooks/simplifier.py:133` — the `except` of `_project_ref` also catches `RuntimeError`, with a comment saying why (a symlink loop, up to Python 3.12). The function then answers None, which its docstring already promises for a path that is not a file of the project, and every caller already handles None: the validator rejects with its ordinary error, `may_send` answers False.
  - `tests/test_simplifier.py` — two cases «board 716» in section «PATH-*»; `tests/test_second_opinion.py` — four cases «board 716».
- The reproduction of section 2 with the fix:
  ```
  target loop -> ["target 'src/loop' is not a file of this repository (path[:line] or path::symbol)"]
  ref loop -> ["evidence cites 'src/loop:1', which does not exist"]
  may_send loop -> False
  may_send link out -> False
  ```
- Mutants, in a temporary copy: the fix taken out → the two cases of the validator and the two loop cases of the second opinion fail (that is the proof of section 6). `may_send` judging the path as written (`rel = path`) → both side-effect cases fail («a link the claim names that leads outside the project is not sent», «a git grep hit on a link that leads outside the project is not sent»), with the five cases of board 708 and the two loop cases — so the two cases that were green from the start do hold the side effect of record 003.
- Budget: `python3 .claude/hooks/complexity_budget.py check` → within budget: 0 new files, +0 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies (tests +34).
- The neighbours of section 4 became a task: `tasks/todo/718-open-item-716-resolve-loop-other-scripts.md`.
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 11cfe891860b3105e403e93fb17c813b47dbf7a9
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Command: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/004-symlink-loop-traceback.md --test tests/test_simplifier.py --cmd "python3 tests/test_simplifier.py" --expect "FAIL a target that is a symlink loop is rejected, not a traceback (board 716)"`

````
PROVED: tests/test_simplifier.py fails on 11cfe89 and passes on the working tree; the failure shows «FAIL a target that is a symlink loop is rejected, not a traceback (board 716)»
  command: python3 tests/test_simplifier.py
  the fix: .claude/hooks/simplifier.py, .engine/bugs/004-symlink-loop-traceback.md, tests/test_second_opinion.py
  before the fix: exit 1
    |   ok   --last narrows the window
    |   ok   a removed repeat whose twin stayed in the file has not come back
    |   ok   the repeat written again has come back
    | AGENT-*   the definition matches what the validator enforces
    |   ok   model fable, tools Read, Grep and Glob only
    |   ok   the definition names every one of: dead_code, premature_abstraction, defensive_for_impossible…
    |   ok   the definition names every one of: none, characterization_exists, mutation_verified…
    |   ok   the definition names every one of: flag_only, confirm, auto_remove…
    |   ok   the definition names every one of: low, medium, high…
    |   ok   the definition names every one of: target, claim, traceability…
    |   ok   the definition names every one of: signal, read, grep…
    |   ok   the example in the definition is itself a valid answer
    |   ok   the request for the agent carries the lens and the signals
    | 
    | PASS 84   FAIL 2
  with the fix: exit 0
    |   ok   --last narrows the window
    |   ok   a removed repeat whose twin stayed in the file has not come back
    |   ok   the repeat written again has come back
    | AGENT-*   the definition matches what the validator enforces
    |   ok   model fable, tools Read, Grep and Glob only
    |   ok   the definition names every one of: dead_code, premature_abstraction, defensive_for_impossible…
    |   ok   the definition names every one of: none, characterization_exists, mutation_verified…
    |   ok   the definition names every one of: flag_only, confirm, auto_remove…
    |   ok   the definition names every one of: low, medium, high…
    |   ok   the definition names every one of: target, claim, traceability…
    |   ok   the definition names every one of: signal, read, grep…
    |   ok   the example in the definition is itself a valid answer
    |   ok   the request for the agent carries the lens and the signals
    | 
    | PASS 86   FAIL 0
````

The second opinion, the same way: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/004-symlink-loop-traceback.md --test tests/test_second_opinion.py --cmd "python3 tests/test_second_opinion.py" --expect "FAIL a symlink loop is not sent, and is no traceback (board 716)"`

````
PROVED: tests/test_second_opinion.py fails on 11cfe89 and passes on the working tree; the failure shows «FAIL a symlink loop is not sent, and is no traceback (board 716)»
  command: python3 tests/test_second_opinion.py
  the fix: .claude/hooks/simplifier.py, .engine/bugs/004-symlink-loop-traceback.md, tests/test_simplifier.py
  before the fix: exit 1
    | LIVE-*    the owner's decisions, the reversal split, the cost
    |   ok   decide records the owner's «ні» with the second model's verdict next to it
    |   ok   decide refuses anything but так or ні, and a thing that is no finding id
    |   ok   reversals shows how the second model compares with the owner
    |   ok   with no decision on record the line is absent
    |   ok   a removal the second model agreed with is counted apart
    |   ok   …and one it never saw is not
    |   ok   cost adds up what the record holds
    |   ok   cost on an empty record says so
    | SEED-*    other projects start with it switched off
    |   ok   the seed of a new project says SECOND_OPINION="off" and warns that code is sent to Google
    |   ok   a project.env without the key at all is off
    |   ok   the hook names no other source of the key
    | 
    | PASS 77   FAIL 2
  with the fix: exit 0
    | LIVE-*    the owner's decisions, the reversal split, the cost
    |   ok   decide records the owner's «ні» with the second model's verdict next to it
    |   ok   decide refuses anything but так or ні, and a thing that is no finding id
    |   ok   reversals shows how the second model compares with the owner
    |   ok   with no decision on record the line is absent
    |   ok   a removal the second model agreed with is counted apart
    |   ok   …and one it never saw is not
    |   ok   cost adds up what the record holds
    |   ok   cost on an empty record says so
    | SEED-*    other projects start with it switched off
    |   ok   the seed of a new project says SECOND_OPINION="off" and warns that code is sent to Google
    |   ok   a project.env without the key at all is off
    |   ok   the hook names no other source of the key
    | 
    | PASS 79   FAIL 0
````

## 7. Gate and overseer
- Gate: `bash tests/run_all.sh --fast` — 32 suites green after the fix. `ruff` and `mypy` are not installed on this server; `python3 -m py_compile .claude/hooks/simplifier.py` passes. The full set, once, after the audit and on the same code: `bash tests/run_all.sh` — `PASS: 70 suites green` (2026-10-06).
- Overseer: PASS — request 20261006T072639Z-e1ad95 (attempt 1, raised by the Stop hook), entry in `.engine/overseer/ledger.md`. It ran both proofs, the budget and the fast subset again and the `rel = path` mutant itself. Its notes, kept: (1) the `git grep` side-effect case holds `may_send` on a hit that cannot occur today — the hit is injected (said in section 3); (2) in the validator's suite the two cases cannot tell «`_project_ref` answers None» from «a later check rejects the loop» — under a mutant that returns the loop as written the validator's output is the same, and only the second-opinion cases pin the None; (3) on Python 3.13 a loop is an `OSError`, so the new cases would be green there without the fix: the proof holds for 3.12 and earlier, which this server runs.
- The regression test stays in the suite: `tests/test_simplifier.py`, section «PATH-*», and `tests/test_second_opinion.py` — the cases marked «board 716» (both run by `bash tests/run_all.sh`).

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: a test was missing — fix 003 replaced `is_file()` with `Path.resolve()`, a call that fails in another way, and its cases had only links that lead somewhere; no case put a link to itself against it.
- Queued: `#7ac596ba added`
