# Bug 007-testing-guard-resolve-loop

type: bugfix
status: fixed
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «.claude/hooks/testing.py:951 (guard, PreToolUse hook для slice-tester): Path(target).resolve() без try. На Python 3.11 і 3.12 file_path, що є symlink loop, дає RuntimeError, тобто traceback у hook-у з exit 1. PreToolUse hook з exit 1 не блокує, тож guard пропускає цей виклик без рішення» (tasks/doing/747-open-item-602-testing-guard-resolve-loop.md, «Що сталося»; found by the search of fix 006, `.engine/bugs/006-py313-symlink-loop.md`, section 4).
- Expected: a Write or Edit of the tester whose `file_path` is a symlink loop gets the guard's own decision, as any other path does: outside the test files — the refusal «The tester writes test files only»; named as a test file — allowed, as a test file is. No traceback, exit 0.
- Where the expected is written: `.claude/hooks/testing.py:955` (the guard's rule: the tester writes test files only, anything else is refused); `.claude/agents/slice-tester.md:50` (the contract tests «in new test files of their own»); `.claude/hooks/testing.py:54` («Standard library only; Python 3.11+»); the task 747, «Що зробити»: «tester-ів Write/Edit у file_path-loop отримує звичайне рішення guard-а, а не traceback»; the same principle for the other scripts in records 005 and 006 («a symlink loop … gets the ordinary refusal each script already has … no traceback»).
- Actual: on Python 3.12 `RuntimeError: Symlink loop from '<path>'` leaves `Path.resolve()` at testing.py:953, the hook ends in a traceback with exit 1, and Claude Code lets the call through undecided. On Python 3.13 the same calls get the guard's decision.
- Where it was seen: this cloud server; `python3.12` (3.12.3) and `python3.13` (3.13.16) beside each other. Under `python3.11` (3.11.17) testing.py does not start at all: a `SyntaxError` (an f-string with a backslash, a 3.12 form) — that is task 748, not this bug.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: a fresh project in a temporary directory — `src/loop.py -> loop.py`, `src/loopdir -> loopdir`, `tests/test_loop.py -> test_loop.py` — and the tester's Write of each path (and of two plain paths) piped as the hook's envelope into `python$v .claude/hooks/testing.py guard`, for v in 3.11, 3.12, 3.13 (scratchpad script `b747/repro.sh`, run from the project root at the base commit).
- Output:
  ```
  python3.11 <every path> -> rc=1 SyntaxError: f-string expression part cannot include a backslash
  python3.12 src/loop.py -> rc=1 RuntimeError: Symlink loop from '/tmp/b747-hNu0/src/loop.py'
  python3.12 src/loopdir/x.py -> rc=1 RuntimeError: Symlink loop from '/tmp/b747-hNu0/src/loopdir/x.py'
  python3.12 tests/test_loop.py -> rc=1 RuntimeError: Symlink loop from '/tmp/b747-hNu0/tests/test_loop.py'
  python3.12 src/plain.py -> rc=0 {"hookSpecificOutput": {… "permissionDecision": "deny", "permissionDecisionReason": "The tester writes test fil…
  python3.12 tests/test_plain.py -> rc=0
  python3.13 src/loop.py -> rc=0 {… "permissionDecision": "deny" … "The tester writes test fil…
  python3.13 src/loopdir/x.py -> rc=0 {… "permissionDecision": "deny" …
  python3.13 tests/test_loop.py -> rc=0
  python3.13 src/plain.py -> rc=0 {… "permissionDecision": "deny" …
  python3.13 tests/test_plain.py -> rc=0
  ```
- Result: reproduced (Python 3.12: the three loops end in a traceback with exit 1; the plain paths and every path on 3.13 get the guard's decision).

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
- Test: `tests/test_testing.py`, section «guard», the two cases marked «bug 007» — at the level where the bug shows: the hook itself, `testing.py guard` fed the tester's Write envelope on stdin, as Claude Code runs it. A link to itself named as an implementation file (`src/loop.py`) must get the refusal «The tester writes test files only», and one named as a test file (`tests/test_loop.py`) must be allowed, as a test file is — each with exit 0 and no traceback.
- Command that runs it: `python3.12 tests/test_testing.py` (red only under Python 3.12 and older; under 3.13 `resolve()` does not raise on a loop, the cases are green at the base too).
- It fails with (Python 3.12.3, base commit eb7d167): `FAIL inside the tester: the symlink loop src/loop.py gets the decision its name gets (refused), no traceback (bug 007)` — detail `rc=1 ["RuntimeError: Symlink loop from '/tmp/testing-9xgbdxjx/src/loop.py'"]`; the same for `tests/test_loop.py`; `190 passed, 2 failed`. Under `python3` (3.13.16) at the base: `192 passed, 0 failed`.
- Tests written first to pin the present behaviour around the code: none — the guard's other cases of this section already pin it (an implementation file refused, the contract refused, a test file allowed).

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/testing.py:953` — the guard turns the tester's `file_path` into a path relative to the project with `Path(target).resolve()`, twice, with no `try`; the hook ends in a traceback with exit 1, and a PreToolUse hook that exits 1 decides nothing.
- Why it happened: up to Python 3.12 the non-strict `Path.resolve()` raises `RuntimeError` on a symlink loop (from 3.13 it returns the path); the line came with task 062 on the day of fix 005, which caught exactly this in four other scripts, and was not in 005's list.
- Same places: `grep -rn "\.resolve()" .claude/hooks/*.py .claude/unattended/*.py engine.py evals/*.py`, without `__file__` and the lines that already use `os.path.realpath`:
  - `.claude/hooks/testing.py:953` — this bug, fixed here.
  - `bugfix.py:117`, `lesson_queue.py:457`, `board.py:433` — already inside `try … except RuntimeError` (record 005); `simplifier.py:132` — `os.path.realpath()` and a `stat()` (record 006); `contract_fingerprint.py:114` — refuses what is not a file before the `resolve()` (records 005, 006). Unchanged.
  - The project root or a command-line root, not a path inside the project: `testing.py:129`, `bugfix.py:120,122`, `contract_fingerprint.py:37,39`, `goals.py:256,258`, `mode.py:492`, `overseer_stop.py:110,117,558`, `overseer_verdict.py:116,120`, `park-ask-gated.py:179,186`, `simplifier.py:138`, `board.py:436,1228`, `owner_action.py:289`, `settings_check.py:110`, `engine.py:625,626` — left alone, as in records 005 and 006.
  - `evals/environment.py:78`, `evals/hook_coverage.py`, `evals/run_audit_scenarios.py`, `evals/run_gate_evals.py`, `evals/run_hook_scenarios.py` — outside the hooks: task 719 (in `tasks/todo/`) is about exactly these; not touched here.

## 5. Fix
- What changed: `.claude/hooks/testing.py`, the guard — the tester's `file_path` goes through `os.path.realpath()` instead of `Path.resolve()`, as `goals.py` already does (`goals.py:350`): `realpath()` does not raise on a symlink loop on any supported version, and for every other path it gives what the non-strict `resolve()` gave. The loop then gets the decision its name gets: refused outside the test files, allowed as a test file (the write itself then fails with ELOOP, as before).
- Nothing else: no tidying on the way, no renaming, no new helper for later. `tests/test_testing.py`: the two regression cases of section 3.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: eb7d16763e9322a7a0e333ed439930c1abce0e69
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Command: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/007-testing-guard-resolve-loop.md --test tests/test_testing.py --cmd "python3.12 tests/test_testing.py" --expect "RuntimeError: Symlink loop"`

```
PROVED: tests/test_testing.py fails on eb7d167 and passes on the working tree; the failure shows «RuntimeError: Symlink loop»
  command: python3.12 tests/test_testing.py
  the fix: .claude/hooks/testing.py, .engine/bugs/007-testing-guard-resolve-loop.md
  before the fix: exit 1
    |   ok   the builder: rule 6 is unchanged — property tests stay out of a slice
    |   ok   .claude/project.env: no key of a property-based testing library (not built: board 064)
    |   ok   templates/project/.claude/project.env: no key of a property-based testing library (not built: board 064)
    |   ok   both definitions are started by the script's line only
    |   ok   .claude/skills/slice-builder/SKILL.md carries its part of the cycle
    |   ok   .claude/commands/plan-slice.md carries its part of the cycle
    |   ok   .claude/agents/slice-planner-critic.md carries its part of the cycle
    |   ok   .claude/commands/feature-architect.md carries its part of the cycle
    |   ok   .claude/agents/overseer.md carries its part of the cycle
    |   ok   the mark /plan-slice writes is the mark the script reads
    |   ok   the block label /feature-architect writes is the label the script reads
    |   ok   .claude/project.env: MUTATION_CMD is there and empty
    |   ok   templates/project/.claude/project.env: MUTATION_CMD is there and empty
    | 
    | 190 passed, 2 failed
  with the fix: exit 0
    |   ok   the builder: rule 6 is unchanged — property tests stay out of a slice
    |   ok   .claude/project.env: no key of a property-based testing library (not built: board 064)
    |   ok   templates/project/.claude/project.env: no key of a property-based testing library (not built: board 064)
    |   ok   both definitions are started by the script's line only
    |   ok   .claude/skills/slice-builder/SKILL.md carries its part of the cycle
    |   ok   .claude/commands/plan-slice.md carries its part of the cycle
    |   ok   .claude/agents/slice-planner-critic.md carries its part of the cycle
    |   ok   .claude/commands/feature-architect.md carries its part of the cycle
    |   ok   .claude/agents/overseer.md carries its part of the cycle
    |   ok   the mark /plan-slice writes is the mark the script reads
    |   ok   the block label /feature-architect writes is the label the script reads
    |   ok   .claude/project.env: MUTATION_CMD is there and empty
    |   ok   templates/project/.claude/project.env: MUTATION_CMD is there and empty
    | 
    | 192 passed, 0 failed
```

## 7. Gate and overseer
- Gate: `test_engine_lint` clean (ruff, mypy --strict); `bash tests/run_all.sh --fast` — 38 suites green; the turn-end gate passed with the fix staged.
- Overseer: PASS, request `20261010T113546Z-b1deb7` (entry in the ledger). It ran the proof again in a copy (PROVED), the RED on the base under python3.12 (190/2, both cases `RuntimeError: Symlink loop`), 192/0 under 3.12 and 3.13, and checked that section 4 was written before the fix. Its test gap — the cases are red only under python3.12, while the suites run under python3 (3.13) — is the open item `tasks/todo/768-open-item-test-gap-the-bug-007-guard-cases-also-ru.md`.
- The regression test stays in the suite: `tests/test_testing.py`, section «guard», the two cases «bug 007».

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.

**A test was missing.** The guard had no case for a `file_path` that is a symlink loop, and the suites run under the newest Python only (3.13 here), where `resolve()` no longer raises on a loop — so a hook that promises Python 3.11+ never met the case in which it breaks. Fix 005 caught the same call in four scripts the same day this line was written; its search did not reach the hooks added later. Queued as a lesson candidate.
