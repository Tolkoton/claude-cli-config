# Board 725 — the closing turn (2026-10-12), as the builder states it

Task: tasks/doing/725-open-item-eval-runners-failed-session-as-result.md (mode соло). The work was made and committed in
an earlier session of this task (commit 6a0d334, base f15497f):
- `evals/run_analyst_evals.py`, `evals/run_manager_evals.py`, `evals/run_tester_evals.py`,
  `evals/run_simplifier_evals.py`: a session the API refused (`is_error`, `api_error_status` 401) was already an error
  row with no score; what changed is around it — the results file carries `"status"` (`complete`, `partial`,
  `no-results`; `status()` in `run_simplifier_evals.py`), the summary counts such sessions in `errors` and keeps them out
  of every denominator, and `run_simplifier_evals.py` exits 1 unless the file is `complete`.
- `evals/compare_audits.py`: a scenario only one file has, with no valid session in that file, stays «only after» /
  «only before» with exit 0, and the `Result:` line now names it as not measured.
- tests: the new suite `tests/test_eval_runners_failed_session.py` (in `tests/fast-suites.txt`), three cases in
  `tests/test_audit_no_session.py`, changed expectations in `tests/test_simplifier_evals.py`,
  `tests/test_tester_evals.py`, `tests/test_tester_property_evals.py`; `evals/README.md`.
- `evals/run_second_opinion_evals.py`, named by the task, no longer exists (removed by board 732).

That session had two audits. The first (request 20261012T054046Z-c44b55) was a BLOCK #1 on the exit status of
`run_simplifier_evals.py`; it was fixed before the commit. The second (request 20261012T054646Z-7acbd2) named no failing
check and was recorded as BLOCK 2 of 3 for one reason only: the gate escalation 2026-10-12T01:56:46Z of another task
(slice `numbers-class-table`, tests/test_task_class_table.py) was open. The task waited in tasks/blocked/ with that
question. The owner answered «закрито»; `.claude/state/gate/escalations.json` now lists that escalation under `closed`
and `open` is empty. The task says what to do then: claim the unit again, a new overseer judges it.

What this turn changed in working code: nothing. Since 6a0d334 later tasks of this branch changed
`evals/compare_audits.py`, `evals/run_simplifier_evals.py`, `evals/README.md` and `tests/test_simplifier_evals.py`
(`git diff --stat 6a0d334 HEAD -- evals tests`); none of that is this turn's.

What I ran in this turn, on the tree as it is now (HEAD ca2a191, Python 3.12.13), and what it printed:
- `python3 tests/test_eval_runners_failed_session.py` → `PASS 40   FAIL 0`.
- `python3 tests/test_audit_no_session.py` → `PASS 31   FAIL 0`.
- `python3 tests/test_simplifier_evals.py` → `PASS 322   FAIL 0`; `python3 tests/test_tester_evals.py` →
  `PASS 49   FAIL 0`; `python3 tests/test_tester_property_evals.py` → `PASS 71   FAIL 0`.
- Five mutants, each applied alone in a detached worktree of HEAD (/tmp/b725-wt, removed afterwards; baseline there
  40/0 and 31/0), the suite named run on each:
  1. `run_simplifier_evals.py`: `return exit_code(report["summary"])` without the status condition →
     `tests/test_eval_runners_failed_session.py` `PASS 38   FAIL 2` («the exit status is not 0: a run with a refused
     session does not end green  rc=0», «a run its ceiling stopped after one session of two is `partial`, exit status not
     0  rc=0»).
  2. `status()` returns `"complete"` always → `PASS 26   FAIL 14` («the file says `no-results`, never `complete`
     complete», …).
  3. `run_analyst_evals.py`: `after_total` counts error rows again → `PASS 39   FAIL 1` («analyst: «after» is 1 good of
     1 measured, 1 error — not 1 of 2»).
  4. `run_tester_evals.py`: `scored = list(runs)` → `PASS 36   FAIL 4` («tester: arm a caught «1 of 1», arm b «0 of 0»,
     2 errors — a refused session is in no denominator», …).
  5. `compare_audits.py`: `if alone:` → `if False:` → `tests/test_audit_no_session.py` `PASS 29   FAIL 2` («still «only
     after» and exit 0 — and the result line names the scenario as not measured in the after file», «the same the other
     way round: «only before», named in the result line»).
  A first attempt at the mutants, in a copy made with `git archive` (not a git repository), is not evidence: the runners
  refused to start there (`engine ref 'HEAD' does not name a commit of this repository`) on every mutant alike.
- By hand, a `claude` shim that answers the 401 result, a tasks directory with one task in doing/ (/tmp/b725-demo-Oydr):
  `env -u CLAUDE_UNATTENDED_SESSION CLAUDECODE=1 BOARD_STATE_DIR=… python3 evals/run_simplifier_evals.py --tasks-dir … --claude …/claude --out …/s.json --runs 2`
  → exit 1; the file: `status` `no-results`, `summary.errors` 2, `summary.scored` 0.
- `bash tests/run_all.sh`, once → `PASS: 98 suites green`, exit 0.

Not run in this turn: ruff and mypy by hand (they run inside `tests/test_engine_lint.py`, one of the 98 suites); no
session of Claude was started by any eval script — every runner ran on a shim.

The two test gaps the first audit opened — tasks/todo/1715-… (a run cut by `--max-usd` is `partial`, for the analyst,
manager and tester runners, through the CLI) and tasks/todo/1716-… (one session answered and one refused: `partial`,
errors 1, exit status not 0, for all four runners through the CLI) — were written into the suite in the same session,
after that audit: the loop over `RUNNERS` in `tests/test_eval_runners_failed_session.py` runs both cases for each of the
four runners. Mutants 1 and 2 above make them red. The two tasks stay in todo/ for the board to close; this turn does
not touch them.

Decisions I made alone (from the first session, unchanged): two older tests that fixed the old denominators with an
error row now expect the new ones; `compare_audits.py` does not change its exit status for a one-sided scenario; the four
runners, unlike `run_audit_scenarios.py`, do not stop at the first refused login and have no `--resume`; `--rescore` of
`run_simplifier_evals.py` is left alone.

=== UNIT 1 COMPLETE ===
