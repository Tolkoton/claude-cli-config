# Bug 006-py313-symlink-loop

type: bugfix
status: fixed
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «з Python 3.13 Path.resolve() без strict на symlink loop нічого не кидає (зі strict=True кидає OSError з errno ELOOP), тоді як до 3.12 кидав RuntimeError, — тож код, що розпізнає loop за RuntimeError, на 3.13 вважає loop звичайним шляхом. Наслідок: під Python 3.13 швидкий набір тестів червоний — у tests/test_second_opinion.py падають дві перевірки board 716 про symlink loop» (tasks/doing/602-py313-symlink-loop.md, «Що зробити»). A continuation of `.engine/bugs/004-symlink-loop-traceback.md` and `.engine/bugs/005-resolve-loop-other-scripts.md`, both proved on Python 3.12.13.
- Expected: a reference that is a symlink loop — a link to itself, or a path through a directory that links to itself — gets `None` from `simplifier._project_ref` on every Python version the engine supports, so `second_opinion.may_send` answers «do not send» and `review` makes no request; every other path keeps the answer it had. The other places of fixes 004 and 005 give their written refusal for a loop on every supported version.
- Where the expected is written: `.claude/hooks/simplifier.py:128-129` (the docstring of `_project_ref`: "None: not a reference, or it leads outside the project"); record 004, section 1 («may_send answers «do not send» for it», from the task 716: «may_send для неї повертає „не надсилати“»); `tests/test_second_opinion.py:171,175` (the two cases «board 716» that are red); record 005, section 1, for the other places; the task 602: «зроби так, щоб symlink loop розпізнавався однаково на всіх версіях Python, які підтримує двигун, а поведінка для решти шляхів не змінилась». The supported versions: «Standard library only; Python 3.11+» (`.claude/hooks/simplifier.py:50`, the same line in `bugfix.py`, `lesson_queue.py`, `second_opinion.py` and the other hooks).
- Actual: on Python 3.13 `_project_ref(root, "src/loop.py:1")` answers `'src/loop.py:1'` — the loop as an ordinary path of the project; `may_send` answers `True`; `review` sends the request. `bash tests/run_all.sh --fast` is red: `FAIL tests/test_second_opinion.py PASS 77 FAIL 2`. On 3.11 and 3.12 the same calls answer `None` and `False`.
- Where it was seen: this cloud server, Python 3.13.16 (`/usr/bin/python3`, the interpreter the hooks and the Stop gate run); compared with 3.11.17 and 3.12.3, installed beside it. Record 004 (section 7, note 3) and record 005 (section 7, note 4) assumed «on Python 3.13 a loop is an `OSError`» — true for `resolve(strict=True)` only; the engine calls the non-strict form.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: a fresh project in a temporary directory — `src/a.py`, `src/loop.py -> loop.py`, `src/loopdir -> loopdir`, `src/link.py -> a.py` — and a script that calls `simplifier._project_ref` and `second_opinion.may_send` on each path; run under each interpreter: `for v in 3.11 3.12 3.13; do python$v repro.py; done`. Beside it, the fast subset at the base commit: `bash tests/run_all.sh --fast`.
- Output:
  ```
  3.11.17 / 3.12.3 (the same lines)
    _project_ref('src/loop.py:1'         ) -> None
    _project_ref('src/loopdir/b.py:1'    ) -> None
    _project_ref('src/../src/loop.py'    ) -> None
    _project_ref('src/missing.py:3'      ) -> 'src/missing.py:3'
    _project_ref('src/../src/missing.py' ) -> 'src/missing.py'
    _project_ref('src/link.py:1'         ) -> 'src/a.py:1'
    _project_ref('src/a.py'              ) -> 'src/a.py'
    may_send('src/loop.py'       ) -> False
    may_send('src/loopdir/b.py'  ) -> False
    may_send('src/a.py'          ) -> True
  3.13.16
    _project_ref('src/loop.py:1'         ) -> 'src/loop.py:1'
    _project_ref('src/loopdir/b.py:1'    ) -> 'src/loopdir/b.py:1'
    _project_ref('src/../src/loop.py'    ) -> 'src/loop.py'
    _project_ref('src/missing.py:3'      ) -> 'src/missing.py:3'
    _project_ref('src/../src/missing.py' ) -> 'src/missing.py'
    _project_ref('src/link.py:1'         ) -> 'src/a.py:1'
    _project_ref('src/a.py'              ) -> 'src/a.py'
    may_send('src/loop.py'       ) -> True
    may_send('src/loopdir/b.py'  ) -> True
    may_send('src/a.py'          ) -> True
  ```
  and from the fast subset: `FAIL tests/test_second_opinion.py PASS 77 FAIL 2` — `FAIL a symlink loop is not sent, and is no traceback (board 716)` (detail `True`) and `FAIL a target that is a symlink loop gets no request (board 716)`. The three loop lines differ between versions; the four other paths answer alike on all three.
- Result: reproduced

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
- Test: `tests/test_simplifier.py`, section «PATH-*», the five cases marked «board 602» — at the level of `simplifier._project_ref` itself, the function `second_opinion.may_send` hands every path to: four loops (a link to itself as `src/demo/loop.py` and `src/demo/loop.py:1`, a path through a directory that links to itself `src/demo/loopdir/x.py:1`, the loop written with `..`) must answer `None`, and a negative — a missing file written with `..` and a link inside the project keep the path they resolve to (`src/demo/missing.py:3`, `.claude/constitution.md`). Why this level and this suite: the validator's own output cannot tell «`_project_ref` answered None» from «a later check rejected the loop» (record 004, section 7, note 2 — the two «board 716» cases of this suite are green on 3.13 at the base), and the second opinion's cases that do pin it leave with task 732, which removes `second_opinion.py` and its suite; `_project_ref` and this suite stay.
- Command that runs it: `python3 tests/test_simplifier.py` (and the same under `python3.11` and `python3.12`).
- It fails with (Python 3.13.16, base commit):
  ```
  FAIL _project_ref answers None for the symlink loop src/demo/loop.py, on every Python version (board 602)
         src/demo/loop.py
  FAIL _project_ref answers None for the symlink loop src/demo/loop.py:1, on every Python version (board 602)
         src/demo/loop.py:1
  FAIL _project_ref answers None for the symlink loop src/demo/loopdir/x.py:1, on every Python version (board 602)
         src/demo/loopdir/x.py:1
  FAIL _project_ref answers None for the symlink loop src/../src/demo/loop.py, on every Python version (board 602)
         src/demo/loop.py
    ok   negative — a missing file and a link inside the project keep the path they resolve to (board 602)
  PASS 87   FAIL 4
  ```
  The detail under each FAIL is the symptom of section 1: the loop handed back as an ordinary path. Under 3.11.17 and 3.12.3 at the base the same five are `ok` (`PASS 91   FAIL 0`): there the `RuntimeError` of `resolve()` still gives `None`.
- Not red, and said so: the two red «board 716» cases of `tests/test_second_opinion.py` are the user-level view of the same bug; they stay as they are and go green with the fix.
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — the suite already reaches `_project_ref`.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/simplifier.py:132` — `(root / match["path"]).resolve()` in `_project_ref`; the `except (OSError, ValueError, RuntimeError)` of line 133 waits for a `RuntimeError` that 3.13 no longer raises, the loop goes on through `relative_to` and comes back as a reference of the project; `second_opinion.may_send` (`second_opinion.py:107`) then finds nothing against it and answers «send».
- Why it happened: fix 004 recognised a loop by an exception that is not the operating system's answer but `pathlib`'s. Up to Python 3.12 a non-strict `Path.resolve()` is `os.path.realpath()` followed by a `stat()` whose `ELOOP` it turns into `RuntimeError` (the source of 3.11.17 and 3.12.3, read with `inspect.getsource(pathlib.Path.resolve)`: `s = os.path.realpath(self, strict=strict)` … `if not strict: try: p.stat() except OSError as e: check_eloop(e)`); in 3.13 it is only `return self.with_segments(os.path.realpath(self, strict=strict))` — the `stat()` is gone (the documentation of pathlib, `Path.resolve`: «Changed in version 3.13: Symlink loops are treated like other errors: OSError is raised in strict mode, and no exception is raised in non-strict mode»), so a loop comes back like a path that does not exist. What does not change between versions is underneath: `os.path.realpath()` gives the same answer on 3.11, 3.12 and 3.13 for every kind of path (a loop, a path through a looping directory, a missing file, a link, a dangling link, a path through a file — probed on all three), and `os.stat()` of a loop fails with `ELOOP` on all three. Records 004 and 005 noted the 3.13 change but took it for «a loop is an `OSError` there» — true only of `resolve(strict=True)`, which the engine does not call — and their proofs ran on 3.12 only, where the version-dependent route is the one that works.
- Same places: `grep -n "resolve()" .claude/hooks/*.py .claude/unattended/*.py engine.py | grep -v __file__` (29 lines at the base commit) and `grep -n "RuntimeError\|realpath" .claude/hooks/*.py .claude/unattended/*.py engine.py`; every hit read. Each place of fixes 004 and 005 was also run under 3.11.17, 3.12.3 and 3.13.16 through its own suite.
  - `simplifier.py:132` (`_project_ref`) — this bug, fixed here. It is the only place where a loop has to be told apart from a missing path: a missing file keeps its resolved path (the validator rejects it later with its own error), a loop gets `None`.
  - `bugfix.py:116-118` (`test_files`), `lesson_queue.py:456-458` (`context_lines.walk`, which since 005 also covers the CLAUDE.md of `lesson_queue.py:469`), `board.py:447-449` (`cmd_start`) — the same reliance on `RuntimeError`, but none of them needs to tell a loop from a missing path: the `is_file()` on the next line answers False for a loop on every version and gives the written refusal. On 3.13 the loop passes `resolve()` and that line refuses it; on 3.11 and 3.12 the `except` does. The answer is the same on all three: their «board 718» cases are green under each interpreter (`test_bugfix` 77/0 and `test_board` 277/0 on all three, `test_lesson_queue` 101/0 and `test_goals` 87/0 on 3.12 and 3.13; on 3.11 these two stop on the `SyntaxError` named below, after every one of their «board 718» cases has printed `ok`). Not changed: the `except` is still needed on 3.11 and 3.12, and putting `os.path.realpath()` there instead would change no answer on any version — tidying, not a fix.
  - `goals.py:350` (`cmd_check`), `board.py:1321` (`audit-allowed --tasks-dir`) — already `os.path.realpath()` since 005, the same on every version; their cases green under each interpreter.
  - `contract_fingerprint.py:114` — line 111 refuses what is not a file before the `resolve()`; unchanged.
  - The project root, not a path inside it — left alone as in 005: `bugfix.py:120,122`, `contract_fingerprint.py:37,39`, `goals.py:254,256`, `overseer_stop.py:110,117`, `overseer_verdict.py:103,107`, `park-ask-gated.py:87,94`, `board.py:451` (the board's own `tasks/todo`), `board.py:1236`, `owner_action.py:289`, `settings_check.py:110`, `engine.py:625,626`; and two lines that are not in the list of 005 because they came with task 062 the same day: `testing.py:129` and `overseer_stop.py:558` (`project_dir.resolve()`), both the root.
  - New since the list of 005, and not this cause: `testing.py:951` (`guard`, the tester's `file_path`) — `Path(target).resolve()` with no `try`, the cause of record 005 (a traceback on 3.11 and 3.12, nothing on 3.13), not a loop told by `RuntimeError`; it needs its own failing case, which only a run under 3.12 can show. A new board task (section 5 names it), not touched here.
  - Outside the scope of fixes 004 and 005 — task 719 (`doc_audit.py`, `evals/…`): not touched; whether the same way suits it is said in the task's report.
  - Seen on the way and unrelated to loops: under Python 3.11 `.claude/hooks/testing.py:202` does not parse (`SyntaxError: f-string expression part cannot include a backslash` — allowed only from 3.12), so `test_goals`, `test_lesson_queue` and `test_contract_fingerprint` fail on 3.11 before they reach their loop cases, while the hooks say «Python 3.11+». A new board task, not touched here.

## 5. Fix
- What changed:
  - `.claude/hooks/simplifier.py` (`_project_ref`) — the path goes through `os.path.realpath()` and then a `stat()`; `ELOOP` from that `stat()` answers `None`. Those are the two steps `resolve()` was made of up to Python 3.12, done by hand, so the answer no longer depends on the version: every other path gets exactly what `resolve()` gave (the same `realpath()`; the `stat()` only looks for `ELOOP` and lets every other error through, as `pathlib` did). The docstring says a loop answers `None`. The `except` keeps `RuntimeError`, now for `root.resolve()` alone — a root that is itself a loop, up to 3.12 — so that case answers as before too; the comment says so. Two imports, `errno` and `os`, both standard library.
  - `tests/test_simplifier.py` — the five cases «board 602» of section 3, and `src/demo/loopdir` in the cleanup list of the section.
- The reproduction of section 2 with the fix — the same lines under 3.11.17, 3.12.3 and 3.13.16:
  ```
    _project_ref('src/loop.py:1'         ) -> None
    _project_ref('src/loopdir/b.py:1'    ) -> None
    _project_ref('src/../src/loop.py'    ) -> None
    _project_ref('src/missing.py:3'      ) -> 'src/missing.py:3'
    _project_ref('src/../src/missing.py' ) -> 'src/missing.py'
    _project_ref('src/link.py:1'         ) -> 'src/a.py:1'
    _project_ref('src/a.py'              ) -> 'src/a.py'
    may_send('src/loop.py'       ) -> False
    may_send('src/loopdir/b.py'  ) -> False
    may_send('src/a.py'          ) -> True
  ```
  With it, under each of the three: `tests/test_simplifier.py` `PASS 91   FAIL 0`, `tests/test_second_opinion.py` `PASS 79   FAIL 0` (its four «board 716» cases `ok`).
- Mutants, in a temporary copy of the tree:
  - the `stat()`/`ELOOP` check taken out (only `realpath()` left) → the four loop cases «board 602» and the two loop cases «board 716» of the second opinion fail under 3.11.17, 3.12.3 and 3.13.16 alike (`PASS 87   FAIL 4`, `PASS 77   FAIL 2` on each). This is what «the test checks 3.13 and the older versions the same way» means here: the recognition of a loop no longer comes from the interpreter, so losing it is red on every version, where at the base commit the same test was green on 3.11 and 3.12 and red on 3.13 only.
  - the `except RuntimeError` taken out of `bugfix.py`, `board.py` (`cmd_start`) and `lesson_queue.py` (`walk`), the places left unchanged (section 4) → their «board 718» cases fail under 3.12.3 (1, 2 and 2) and pass under 3.13.16 (0, 0, 0): on 3.13 there is nothing for that `except` to catch, and the `is_file()` after it refuses the loop. So for these three only a run under 3.11 or 3.12 can see a regression of the `except`; it was run here.
- Budget: `python3 .claude/hooks/complexity_budget.py check` → `Complexity budget: within budget` — production: 0 new files, +12 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies; tests: +7 lines.
- Became board tasks, not touched here: `tasks/todo/747-open-item-602-testing-guard-resolve-loop.md` (`testing.py:951`, section 4); `tasks/todo/748-open-item-602-python311-fstring.md` (`testing.py:202` does not parse under 3.11). Two findings about the cloud environment, met on the way: `tasks/todo/749-open-item-602-cloud-formatter-whole-file.md` (with `ruff` and `black` installed and `FORMAT_CMD` empty, format-on-edit reformats a whole `.py` file on every edit — the edits of this fix were therefore written by a script, and the diff is only the lines above) and `tasks/todo/750-open-item-602-cloud-shallow-clone.md` (a fresh cloud clone is shallow and two suites of the fast subset are red there).
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 6508a22a1d1877c3b2b160a860b3454026e8d713
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Run on Python 3.13.16, where the bug is. Under 3.11 and 3.12 the same proof would be `REFUSED` — the test passes there without the fix, because there is no bug there; what the test is worth on those versions is shown by the first mutant of section 5.

`python3 .claude/hooks/bugfix.py prove --record .engine/bugs/006-py313-symlink-loop.md --test tests/test_simplifier.py --cmd "python3 tests/test_simplifier.py" --expect "FAIL _project_ref answers None for the symlink loop src/demo/loop.py, on every Python version (board 602)"`

````
PROVED: tests/test_simplifier.py fails on 6508a22 and passes on the working tree; the failure shows «FAIL _project_ref answers None for the symlink loop src/demo/loop.py, on every Python version (board 602)»
  command: python3 tests/test_simplifier.py
  the fix: .claude/hooks/simplifier.py, .engine/bugs/006-py313-symlink-loop.md
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
    | PASS 87   FAIL 4
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
    | PASS 91   FAIL 0
````

The user-level view, the suite that leaves with task 732: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/006-py313-symlink-loop.md --test tests/test_second_opinion.py --cmd "python3 tests/test_second_opinion.py" --expect "FAIL a symlink loop is not sent, and is no traceback (board 716)"`

````
PROVED: tests/test_second_opinion.py fails on 6508a22 and passes on the working tree; the failure shows «FAIL a symlink loop is not sent, and is no traceback (board 716)»
  command: python3 tests/test_second_opinion.py
  the fix: .claude/hooks/simplifier.py, .engine/bugs/006-py313-symlink-loop.md, tests/test_simplifier.py
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
- Gate: `bash tests/run_all.sh --fast` under Python 3.13.16 — `PASS: 36 suites green (fast subset)`; before the fix `FAIL: 3 of 36 suites red` — `test_second_opinion.py` (this bug) and two suites that need the git history a fresh cloud clone lacks (`test_legacy_records_survive.py`, `test_analyst_evals.py`; green after `git fetch --unshallow --tags origin`, done with the owner's consent — task 750). `LINT_CMD` and `TYPECHECK_CMD` are empty in this repository; `python3.11/3.12/3.13 -m py_compile .claude/hooks/simplifier.py` passes, `ruff check --select F` on the two changed files: `All checks passed!`.
- Overseer: PASS — request 20261008T185204Z-6a4182 (attempt 1, raised by the Stop hook), entry in `.engine/overseer/ledger.md`. It ran again, in its own copies, `tests/test_simplifier.py` and `tests/test_second_opinion.py` under 3.11.17, 3.12.3 and 3.13.16, the fast subset, both proofs, the RED of section 3 against the base, and the budget; five mutants of its own (the `ELOOP` check removed, any `OSError` answering `None`, `lstat` instead of `stat`, `abspath` instead of `realpath`, `not exists()` answering `None`) were each caught on all three versions; a side-by-side run of the old and the new `_project_ref` on 22 references gave no difference on 3.11 and 3.12 and, on 3.13, differences only for the loops. Its notes, kept: (1) the negative case holds only two paths that are not loops (a missing file through `..`, a link inside the project); an answer of `None` for a path through a file (`ENOTDIR`) or for a dangling link would pass every «board 602» case — its own side-by-side run shows the fix keeps those answers, the suite does not hold them; (2) section 4 is headed «Written before the fix» and the record was rewritten after it, with sections 5–7 — only the test written before the fix and the RED that comes back exactly hold the order; (3) the proofs pasted in section 6 were run before the four board tasks existed, so their «the fix» line does not list them; the code they cover is unchanged and its own run prints PROVED; (4) the alternatives not taken are not named in section 5: `resolve(strict=True)` with an `ELOOP` catch (a missing file would then answer `None` — another path changing its answer) and a branch on `sys.version_info` (two mechanisms again, each tested only on its own versions); the choice taken rebuilds the two steps of `resolve()` up to 3.12 exactly.
- The regression test stays in the suite: `tests/test_simplifier.py`, section «PATH-*», the five cases marked «board 602» (run by `bash tests/run_all.sh` and its fast subset).

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: a test was missing — the loop cases of fixes 004 and 005 were proved only under the server's Python 3.12; nobody ran them under 3.13, whose changed `Path.resolve()` both records had noted but read as «an `OSError` there», so a loop told by `pathlib`'s `RuntimeError` instead of the operating system's `ELOOP` went unseen until a cloud session on 3.13 ran the suite.
- Queued: `#b05ba00c added`
