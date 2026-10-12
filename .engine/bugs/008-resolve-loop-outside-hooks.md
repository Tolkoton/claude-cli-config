# Bug 008-resolve-loop-outside-hooks

type: bugfix
status: fixed
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «та сама причина — Path.resolve() на петлі символьних посилань піднімає RuntimeError до Python 3.12 включно — лишилась поза .claude/hooks, .claude/unattended та engine.py … Наслідок усюди — traceback замість написаної відмови; платний прогін не починається, нічого не псується» (tasks/doing/719-open-item-718-resolve-loop-outside-hooks.md, «Що сталося»; found by the second audit of fix 005, `.engine/bugs/005-resolve-loop-other-scripts.md`, section 4). The line numbers of the task are those of 2026-10-06; the ones below are of the base commit `1e28bc5`.
- Expected: a given path that is a symlink loop (`loop -> loop`) gets the answer each script already has for a path that leads nowhere; no traceback. Place by place:
  - `doc_audit.py`, a Markdown link to a loop → `ERROR <file>:<line> - broken link to '<target>'.`, exit 1, as for a link to a missing file.
  - `run_audit_scenarios.py --tasks-dir <loop>` → exit 2, `refusing to start paid sessions: no task of this session is in <loop>/doing/`, as for a directory that does not exist.
  - `environment.baseline_folder(<loop outside evals/baseline/>)` → `None` («None for any other path»), so `out_path` accepts it as it accepts any path outside the baseline.
  - `run_hook_scenarios.py`, a setup step that writes through a loop, and a `project_dir` that is a loop → the runner's written refusal `SandboxError` (`sandbox error: …`, exit 2), as for a path that leaves the sandbox.
  - `run_hook_scenarios.py --hooks-dir <loop>` → every scenario answers `absent`, as for a directory that does not exist.
- Where the expected is written: `.claude/skills/documentation/scripts/doc_audit.py:9` («Relative Markdown links that point to missing files») and `:153-155` (the error line); `evals/run_audit_scenarios.py:697-710` (`paid_run_refusal`) with `.claude/unattended/board.py:1496` (the same question already answered this way for `board.py audit-allowed --tasks-dir`, record 005); `evals/environment.py:76` (the docstring of `baseline_folder`); `evals/run_hook_scenarios.py:111-112` («Declarative setup only … a scenario file cannot do anything outside the sandbox»), `:117`, `:212` and `:392-394` (the two refusals and the line that prints them), `:21` and `:187-190` (`absent`); the task 719, «Що зробити»: «шлях-петля дає цю відмову, а не traceback»; record 005, section 1, the same principle for the hooks.
- Actual: `RuntimeError: Symlink loop from '<path>'` leaves `Path.resolve()`; the script ends in a traceback with exit 1. Nothing is written and no session is started before it.
- Where it was seen: Python 3.12.13 on this server (the overseer of fix 005 reproduced the first two on 2026-10-06). On Python 3.13 the non-strict `resolve()` raises nothing on a loop (records 005 and 006), so the same inputs go further there — see section 4.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: in a fresh directory `/tmp/b719-B5Zk` — `tl -> tl`; a git repository `docrepo/` with `loop.txt -> loop.txt` and a README.md that says `[a](loop.txt) [b](missing.md)`; a git repository `sb/` with `lp -> lp` and a hook `.claude/hooks/h.sh`. Then, from the engine's root (the last line of each output):
  - `python3 .claude/skills/documentation/scripts/doc_audit.py --root /tmp/b719-B5Zk/docrepo`
  - `python3 evals/run_audit_scenarios.py --tasks-dir /tmp/b719-B5Zk/tl`
  - `environment.out_path('/tmp/b719-B5Zk/tl')` from `python3 -`
  - `python3 evals/run_hook_scenarios.py --engine-ref HEAD --only zzz-none --hooks-dir /tmp/b719-B5Zk/tl`
  - `run_hook_scenarios.apply_setup(sb, [{"write": {"path": "lp/x.txt", "content": "x"}}])` and `run_hook_scenarios.run_scenario(sb, sb/'.claude/hooks', 'h.sh', {"id": "a", "project_dir": "lp"}, 5)`, the module loaded by path from `python3 -`
- Output:
  ```
  == doc_audit
  RuntimeError: Symlink loop from '/tmp/b719-B5Zk/docrepo/loop.txt'
  == run_audit_scenarios --tasks-dir
  RuntimeError: Symlink loop from '/tmp/b719-B5Zk/tl'
  == environment.out_path
  RuntimeError: Symlink loop from '/tmp/b719-B5Zk/tl'
  == run_hook_scenarios --hooks-dir
  RuntimeError: Symlink loop from '/tmp/b719-B5Zk/tl'
  == apply_setup / run_scenario
  setup write -> RuntimeError Symlink loop from '/tmp/b719-B5Zk/sb/lp/x.txt'
  project_dir -> RuntimeError Symlink loop from '/tmp/b719-B5Zk/sb/lp'
  ```
  The same inputs with a path that leads nowhere or outside, for comparison: `--tasks-dir /tmp/b719-B5Zk/none` → `refusing to start paid sessions: no task of this session is in /tmp/b719-B5Zk/none/doing/.`; `--hooks-dir /tmp/b719-B5Zk/none` → `PASS 0/0`, exit 0; `"path": "../x.txt"` → `SandboxError setup writes outside the sandbox: /tmp/b719-B5Zk/x.txt`; `"project_dir": ".."` → `SandboxError project_dir escapes the sandbox: /tmp/b719-B5Zk`; with `loop.txt` removed, doc_audit prints `ERROR README.md:3 - broken link to 'loop.txt'.`
- Result: reproduced — every place the task names that still exists. `evals/run_simplifier_evals.py:84` (`tasks_dir.resolve()`) is gone: since board 110 that script hands `tasks_dir` to `board_state.py`, which goes through `os.path.realpath` (`.claude/unattended/board_state.py:259,316`).

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
One suite, new: `tests/test_symlink_loop_outside_hooks.py` — one case per place, each through the command the user types (the `environment` one also in-process: `baseline_folder` is what the six runners' `--out` calls), every loop case with its negatives beside it:
- «a link to a symlink loop is a broken link, not a traceback (board 719)» — `doc_audit.py --root <repo>`; negatives: a link to a missing file is a broken link; a link through `..` to a real file is still resolved and found.
- «--tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 719)» — `run_audit_scenarios.py`; negatives: a directory that does not exist is refused the same way; the fixture board that says «так», given through `..`, is still resolved and let past the gate.
- «a symlink loop outside evals/baseline/ lies in no environment's folder, no exception (board 719)» and «a runner given --out <loop> gets past the argument …, no traceback»; negatives: a missing path lies in none; a path into this environment's folder through `..` is still resolved.
- «a setup step that writes through a symlink loop is a sandbox error, not a traceback (board 719)», «a project_dir that is a symlink loop is a sandbox error, not a traceback (board 719)», «--hooks-dir that is a symlink loop ships no hook: absent, not a traceback (board 719)» — `run_hook_scenarios.py --sandbox <synthetic> --scenarios <one file>`; negatives for each: the path outside the sandbox is the written refusal; the path inside, through `..`, runs; a `--hooks-dir` that does not exist is `absent`; one given through `..` is resolved (the `--out` record names it `<SANDBOX>/.claude/hooks`) and its hook runs.
- Command that runs it: `python3 tests/test_symlink_loop_outside_hooks.py` (0.9 s; in `tests/fast-suites.txt`).
- It fails with (before the fix, Python 3.12.13; the detail of each is the tail of the traceback, ending in `RuntimeError: Symlink loop from …`):
  ```
  FAIL a link to a symlink loop is a broken link, not a traceback (board 719)
  FAIL negative: a link to a missing file is a broken link          ← the same run of doc_audit: the traceback comes before any line of the report
  FAIL --tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 719)
  FAIL a symlink loop outside evals/baseline/ lies in no environment's folder, no exception (board 719)
  FAIL a runner given --out <loop> gets past the argument (it stops at its next refusal), no traceback
  FAIL a setup step that writes through a symlink loop is a sandbox error, not a traceback (board 719)
  FAIL a project_dir that is a symlink loop is a sandbox error, not a traceback (board 719)
  FAIL --hooks-dir that is a symlink loop ships no hook: absent, not a traceback (board 719)
  PASS 11   FAIL 8
  ```
  Under Python 3.13.12, before the fix, `PASS 17   FAIL 2`: the two cases of the second half of the cause (section 4) — `FileExistsError: [Errno 17] File exists: '…/sandbox/lp'` from the setup step and `OSError: [Errno 40] Too many levels of symbolic links: PosixPath('…/sandbox/lp')` from `subprocess.run`; the other six are green there without the fix, as record 005 says of its own.
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — every place is reached through its command. `doc_audit.py` had no suite at all; this one is its first.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/skills/documentation/scripts/doc_audit.py:152` (`check_links`); `evals/run_audit_scenarios.py:703` (`paid_run_refusal`); `evals/environment.py:78` (`baseline_folder`, inside a `try` that catches `ValueError` only); `evals/run_hook_scenarios.py:115` (`apply_setup`), `:210` (`run_scenario`), `:356` (`run_all`, `--hooks-dir`) — a `Path.resolve()` of a given path.
- Why it happened: each place treats `resolve()` as a call that cannot fail and leaves the judgement to the check after it (`exists()`, `audit_refusal`, `relative_to`, «is it inside the sandbox», `is_file()`). Up to Python 3.12 a non-strict `resolve()` reports a symlink loop as a bare `RuntimeError` (pathlib's documentation, quoted in record 005, section 4), so the script never reaches the line that holds its answer. Fix 005 covered the hooks, the board scripts and the installer and stopped there; these files lie outside that search.
- A second half of the same cause, in the two places of `apply_setup` and `run_scenario` only: the check after `resolve()` asks «is it inside the sandbox», and a loop inside the sandbox IS inside it. So with the `RuntimeError` gone — by a fix here, or by Python 3.13, where `resolve()` raises nothing — the loop walks on to the first call that uses it (`mkdir` of the parent: `FileExistsError`; `subprocess.run(cwd=…)`: `OSError`), again a traceback and not the `SandboxError` written for a path the setup may not use. The fix of these two therefore has to give the refusal itself, the same on every version; the other four have a check after them that already answers a loop (`exists()` and `is_file()` are False for it, `audit_refusal` finds no `doing/`, `relative_to` raises the `ValueError` that is caught).
- Same places — the search of the task, over everything the repository ships outside `tests/`: `git ls-files --cached --others --exclude-standard | grep -v '^tests/'`, lines with `resolve(`, `realpath` or `readlink -f`; Markdown and the records under `.engine/`, `tasks/`, `docs/` dropped; `Path(__file__).resolve()` (a script's own place) dropped; `resolve(` as the name of a function of its own dropped (`engine.py:730,1223,1257,1404,1572,1595`, `lesson_queue.py:788`, `shell_readonly.py:109,118,231`, `shell_paths.py:72` a word in a set, `overseer_stop.py:107` a docstring). No shell script resolves a path this way. Every other line, by what it is:
  - Fixed here, each with its failing case: `doc_audit.py:152`; `run_audit_scenarios.py:703`; `environment.py:78`; `run_hook_scenarios.py:115`, `:210`, `:356`.
  - Already answered (fixes 004–007 and board 110): `bugfix.py:117` (in a `try`), `goals.py:351`, `lesson_queue.py:494` (in a `try`), `simplifier.py:133`, `testing.py:954`, `board.py:490` (in a `try`), `board.py:1496`, `board_state.py:259,316`, `gate.py:378` (`os.path.realpath`, which does not raise); `contract_fingerprint.py:114` (line 111 refuses what is not a file first).
  - The root itself — the project, the sandbox, the scenarios' directory — not a path inside it; no script has a written answer for a root that is a link to itself, and the task says so («це корінь, а не шлях усередині нього: написаної відмови для нього немає»). Left alone: `doc_audit.py:54`; `run_audit_scenarios.py:402` (the sandbox the runner built), `:763` (`--scenarios-dir`); `run_gate_evals.py:168`; `run_hook_scenarios.py:116,211,216,349` (`sandbox.resolve()`); `hook_coverage.py:395` (`--root`); `bugfix.py:120,122`; `contract_fingerprint.py:37,39`; `goals.py:256,258`; `journal.py:299`; `mode.py:515`; `overseer_stop.py:110,117,559`; `overseer_verdict.py:121,125`; `park-ask-gated.py:179,186`; `simplifier.py:139`; `testing.py:129`; `board.py:493` (the board's own column), `:1411`; `owner_action.py:289`; `settings_check.py:110`; `engine.py:722,723`.
  - `hook_coverage.py:124` (`run --data <loop>`): the directory a run is to CREATE. Its one written refusal is for a directory that is not empty; a missing one is made. A loop there has no written answer (it cannot be made and is not «not empty»), and it is the tool's own working directory, like a root. Left alone. `hook_coverage.py:399`: line 396-397 refuses what holds no `py/` directory before the `resolve()` — a loop holds none.
  - Not the engine's code: `evals/scenarios/simplifier/project/src/refproj/receipts.py:9,10`, `evals/scenarios/simplifier-hard/…/receipts.py:17,18`, `evals/scenarios/simplifier-traps/…/receipts.py:18,19` with their `tests/test_counter.py:39` — the reference projects the simplifier is measured on; `evals/baseline/**/second-opinion-evals-2026-10.json` — recorded answers that quote them; `.engine/artifacts/` and `tasks/done/*/tools|evidence` — records of finished work.
  - Met on the way, another cause, not touched: in `doc_audit.py` a Markdown FILE that is itself a loop (`loop.md -> loop.md`) is found by `rglob("*.md")` and read — `OSError: [Errno 40] Too many levels of symbolic links` from `read_text` (`check_links`, the first reader). No `resolve()` is involved and no answer is written for it; it became a board item (section 5).

## 5. Fix
- What changed (seven lines of four files, +1 line net of working code besides the two `import os`):
  - `.claude/skills/documentation/scripts/doc_audit.py` (`check_links`) — the link goes through `os.path.realpath` instead of `resolve()`; `exists()` on the next line is False for a loop and gives «broken link». `import os`.
  - `evals/run_audit_scenarios.py` (`paid_run_refusal`) — `--tasks-dir` through `os.path.realpath` (`os` was imported): a loop is a directory with no `doing/`, and `audit_refusal` gives its ordinary «no task of this session» — the form `board.py:1496` has since fix 005.
  - `evals/environment.py` (`baseline_folder`) — the same; `relative_to` then raises the `ValueError` the `try` already catches, and the answer is `None`. `import os`.
  - `evals/run_hook_scenarios.py` — the three `resolve()` of a given path (`apply_setup`, `run_scenario`, `--hooks-dir` in `run_all`) became `os.path.realpath` (`os` was imported); and the `except SandboxError` of `run_all` became `except (SandboxError, OSError)` — the form the sibling runner already has (`evals/run_gate_evals.py:172`). That one line is the answer to the second half of the cause: a loop inside the sandbox passes «is it inside», the first call that uses it raises `OSError`, and the runner prints it as its `sandbox error: …` with exit 2 — on 3.12 and on 3.13 alike. `--hooks-dir <loop>` needs nothing more: `is_file()` of a hook under it is False, the scenario is `absent`.
  - Not the first form tried: a `try` round the write in `apply_setup` and an `if not project_dir.is_dir()` in `run_scenario`, each raising a `SandboxError` of its own text. The budget script refused it — `max_cyclomatic_per_function: 13 allowed, exceeded by evals/run_hook_scenarios.py:run_scenario = 23` (22 at the base commit) — and the form above adds no branch anywhere and three lines fewer.
  - `tests/test_symlink_loop_outside_hooks.py` (new), its line in `tests/fast-suites.txt`.
- What the wider `except` changes besides the loop: any other `OSError` raised while the scenarios run (a scenario file that cannot be read, a setup path through a regular file) is now `sandbox error: <the error>` with exit 2 where it was a traceback with exit 1. Nothing that ran before stops running; the results file is still not written after a refusal, as before.
- The reproduction of section 2 with the fix (the same directory; the last lines):
  ```
  == doc_audit                          ERROR README.md:3 - broken link to 'loop.txt'.          (exit 1)
  == run_audit_scenarios --tasks-dir    refusing to start paid sessions: no task of this session is in /tmp/b719-B5Zk/tl/doing/.   (exit 2)
  == environment.baseline_folder        None
  == run_hook_scenarios, setup write    sandbox error: [Errno 17] File exists: '/tmp/loop-outside-hooks-h6q2m3h1/sandbox/lp'       (exit 2)
  == run_hook_scenarios, project_dir    sandbox error: [Errno 40] Too many levels of symbolic links: PosixPath('/tmp/loop-outside-hooks-h6q2m3h1/sandbox/lp')   (exit 2)
  == run_hook_scenarios --hooks-dir     ok   hooks-loop   absent   (exit 0)
  ```
  (the two `sandbox error` lines are from the suite's own synthetic sandbox, run by hand with its scenario files.)
- Both versions: `python3 tests/test_symlink_loop_outside_hooks.py` → `PASS 19   FAIL 0` under 3.12.13 and under 3.13.12.
- Nothing else changed for a path that is not a loop — held by cases, not by reading. Mutants, in a temporary copy of the tree (`/tmp/b719-mut-*`), one at a time:
  - the path not resolved at all (`Path((…))` in place of `Path(os.path.realpath(…))`) — `doc_audit.py:153` → `FAIL negative: a link through `..` to a real file is still resolved and found`; `environment.py:79` → `FAIL negative: a path into this environment's folder, given through `..`, is still resolved`; `run_audit_scenarios.py:703` → `FAIL negative: a board that says «так», given through `..`, is still resolved and let past the gate`; `run_hook_scenarios.py:115` → `FAIL negative: a setup step that writes outside the sandbox is a sandbox error`; `:210` → `FAIL negative: a project_dir outside the sandbox is a sandbox error`; `:356` → `FAIL negative: a --hooks-dir given through `..` is still resolved (the record names it so) and its hook runs` (this last mutant survived the first version of the suite — `PASS 19   FAIL 0` — and the case got the check of the `--out` record because of it). Each `PASS 18   FAIL 1`.
  - `OSError` taken out of the `except` → the two loop cases of the sandbox fail (`PASS 17   FAIL 2`).
- The runner still measures what it measured: `python3 evals/run_hook_scenarios.py --engine-ref HEAD --hooks-dir .claude/hooks` → `PASS 281/281` (the whole shipped set, the working tree's hooks; with `--hooks-dir` it leaves no machine record). `tests/test_baseline_environments.py` `PASS 43   FAIL 0`, `tests/test_paid_run_gate.py` `PASS 33   FAIL 0`, `tests/test_health_record.py` `PASS 26   FAIL 0`.
- Budget: `python3 .claude/hooks/complexity_budget.py check` → `Complexity budget: within budget` — production: 0 new files, +1 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies; tests: +157 lines.
- Became a board task, not touched here: `tasks/todo/1706-open-item-719-doc-audit-markdown-file-loop.md` (a Markdown file that is itself a loop, section 4).
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 1e28bc5a08bb3360b5a79c5dd8a3c39da8bf4ca1
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.
The suite must not need a git checkout: the proof's copy is a `git archive`, not a repository. The first run answered `REFUSED: the test still fails on the code with the fix` for one negative alone (`PASS 18   FAIL 1`) — the case «a board that says «так» … let past the gate» waited for the runner's `no scenario id contains`, and in a copy without `.git` the runner stops one check earlier (`engine ref 'HEAD' does not name a commit of this repository`). The case now asks what it means — exit 2, no refusal of the gate, no traceback — and its mutant (section 5) still fails it.

`python3 .claude/hooks/bugfix.py prove --record .engine/bugs/008-resolve-loop-outside-hooks.md --test tests/test_symlink_loop_outside_hooks.py --cmd "python3 tests/test_symlink_loop_outside_hooks.py" --expect "FAIL a link to a symlink loop is a broken link, not a traceback (board 719)"`

````
PROVED: tests/test_symlink_loop_outside_hooks.py fails on 1e28bc5 and passes on the working tree; the failure shows «FAIL a link to a symlink loop is a broken link, not a traceback (board 719)»
  command: python3 tests/test_symlink_loop_outside_hooks.py
  the fix: .claude/skills/documentation/scripts/doc_audit.py, .engine/bugs/008-resolve-loop-outside-hooks.md, evals/environment.py, evals/run_audit_scenarios.py, evals/run_hook_scenarios.py, tasks/todo/1706-open-item-719-doc-audit-markdown-file-loop.md, tests/fast-suites.txt
  before the fix: exit 1
    |     raise RuntimeError("Symlink loop from %r" % e.filename)
    | RuntimeError: Symlink loop from '/tmp/loop-outside-hooks-cxl9trsd/sandbox/lp'
    | 
    |   ok   negative: a project_dir outside the sandbox is a sandbox error
    |   ok   negative: a project_dir inside the sandbox, through `..`, runs
    |   FAIL --hooks-dir that is a symlink loop ships no hook: absent, not a traceback (board 719)   rc=1  ine 1252, in resolve
    |     check_eloop(e)
    |   File "/home/lao/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/pathlib.py", line 1237, in check_eloop
    |     raise RuntimeError("Symlink loop from %r" % e.filename)
    | RuntimeError: Symlink loop from '/tmp/loop-outside-hooks-cxl9trsd/loop'
    | 
    |   ok   negative: a --hooks-dir that does not exist ships none either
    |   ok   negative: a --hooks-dir given through `..` is still resolved (the record names it so) and its hook runs
    | 
    | PASS 11   FAIL 8
  with the fix: exit 0
    |   ok   negative: a missing path outside evals/baseline/ lies in none either
    |   ok   negative: a path into this environment's folder, given through `..`, is still resolved
    |   ok   a runner given --out <loop> gets past the argument (it stops at its next refusal), no traceback
    | run_hook_scenarios.py: a loop inside the sandbox, and --hooks-dir
    |   ok   a setup step that writes through a symlink loop is a sandbox error, not a traceback (board 719)
    |   ok   negative: a setup step that writes outside the sandbox is a sandbox error
    |   ok   negative: a setup step that writes inside the sandbox, through a new directory and `..`, runs
    |   ok   a project_dir that is a symlink loop is a sandbox error, not a traceback (board 719)
    |   ok   negative: a project_dir outside the sandbox is a sandbox error
    |   ok   negative: a project_dir inside the sandbox, through `..`, runs
    |   ok   --hooks-dir that is a symlink loop ships no hook: absent, not a traceback (board 719)
    |   ok   negative: a --hooks-dir that does not exist ships none either
    |   ok   negative: a --hooks-dir given through `..` is still resolved (the record names it so) and its hook runs
    | 
    | PASS 19   FAIL 0
````

## 7. Gate and overseer
- Gate: `bash tests/run_all.sh --fast` → `PASS: 45 suites green (fast subset)`, the new suite among them (`ok tests/test_symlink_loop_outside_hooks.py PASS 19 FAIL 0`). `uvx --offline ruff check` over the four changed files and the new suite: `All checks passed!`; `uvx --offline mypy --strict` on `evals/environment.py`, `evals/run_hook_scenarios.py` and the suite: `Success: no issues found`. The full set is run once, at the end of the board task (its report).
- Overseer: request `20261012T021330Z-dabc22` — the audit found no failing check (it ran the proof again: `PROVED`, 11/8 on `1e28bc5`, 19/0 on the working tree; the suite 19/0 under 3.12.13 and 3.13.12; the fast subset 45 green; the shipped hook scenarios 281/281), and the ledger holds it as BLOCK 1 of 3: «gate escalation 2026-10-12T01:56:46Z open (raised in slice `numbers-class-table`, on tests/test_task_class_table.py) … a PASS is not accepted until the owner closes it». That escalation is another task's (`tasks/blocked/902-gate-escalation-20261012T015646Z.md`) and is the owner's to close; this fix touches none of its files. So the status above says `fixed` and NO overseer PASS is recorded for it yet: the board task 719 waits in `tasks/blocked/` with that question, and the unit is to be claimed again once the escalation is closed. The overseer could not run mutants of its own (its read-only hook refused the temporary copy): the mutant lines of section 5 are the builder's runs.
- Overseer, the second claim (2026-10-12, after the owner closed that escalation and answered «закрито» in the board task): request `20261012T103424Z-43b5b4` — PASS. It ran again on HEAD `35074b7`: the suite 19/0 under 3.12.13 and 3.13, the proof `PROVED` (11/8 on `1e28bc5`, 19/0 on the tree), the two loop cases by hand, `bash tests/run_all.sh` → `PASS: 98 suites green`, and three mutants of its own in a `git archive` copy (the `except` narrowed → 17/2; the link of `doc_audit.py` not resolved → 18/1; `run_audit_scenarios.py` back to `resolve()` → 18/1). Its strongest objection, not a block: the wider `except (SandboxError, OSError)` also labels an unrelated `OSError` as `sandbox error`, and no case pins that — section 5 says so in plain words.
- The regression test stays in the suite: `tests/test_symlink_loop_outside_hooks.py` — the eight cases of section 3 marked «board 719» or failing with them, and their negatives.

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: a test was missing — and behind it a search that was too narrow. None of the four files had a case for a path that leads nowhere (`doc_audit.py` had no suite at all), and fixes 004 and 005 searched for the same call only in the directories the first report named; the same traceback stayed in every file outside them until the second audit of 005 looked.
- Queued: `#075a8475 added` — «A fix for a cause that is a call (here Path.resolve() on a given path) is finished only when the search for the same call has covered every file the repository ships, not the directories the first report named: fixes 004 and 005 searched the hooks and the board scripts, and the same traceback stayed in doc_audit.py and three eval scripts, none of which had a case for a path that leads nowhere.»
