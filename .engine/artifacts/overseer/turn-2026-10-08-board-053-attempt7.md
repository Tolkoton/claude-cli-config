Board 053, unit 1, after the overseer's sixth BLOCK (request 20261007T121629Z-59f1fb) and the owner's answer to question 2 in the task: «Ще один audit overseer-а. Якщо пройде — закрий.»

The sixth BLOCK said: the behaviour is right for all six paid runners, but the three lines of `evals/run_simplifier_evals.py` `paid_run_refusal` that ask `board.line_unread` first — the guard `run_simplifier_evals`, `run_manager_evals`, `run_second_opinion_evals`, `run_analyst_evals` and `run_tester_evals` all use — were held by no test: they could be deleted, or moved below the `owner_approved and not in_session` return, with every suite green.

The fix is a test only, committed in `90932b1` (no engine code changed since `3591655`, which the sixth audit read): `tests/test_simplifier_evals.py` has 11 new checks. For each of «до $5», «USD 5», «п'ять доларів», «скільки потрібно», «так, до 5 доларів на audit» in the `Платні прогони:` line: `paid_run_refusal(board, True, False)` (the owner's flag in the owner's terminal) refuses and names the line and the task file; `paid_run_refusal(board, False, True)` refuses. And beside a plain «ні» the owner's flag in the owner's terminal still passes.

Nothing in the tree was changed in this session except one entry in `tasks/ANOMALIES.md` (the uncommitted `.engine/goals.md` and `.engine/goals/proposed.md` in the working tree are the runner's action for board 082, found at the start of the session, not this unit's).

Verification, all run in this session at HEAD `0c70d05`:
- `python3 tests/test_simplifier_evals.py` — PASS 245, FAIL 0.
- RED on both mutants the sixth BLOCK named, each on a local clone of HEAD in /tmp: the three `line_unread` lines deleted — PASS 240, FAIL 5; the three lines moved below the `owner_approved and not in_session` return — PASS 240, FAIL 5. The five red checks are the «--owner-approved in the owner's terminal is refused too» ones, one per wording.
- `python3 tests/test_owner_terms.py` — PASS 210, FAIL 0. `python3 tests/test_paid_run_gate.py` — PASS 58, FAIL 0.
- `bash tests/run_all.sh` — PASS: 82 suites green, exit 0.

Not held by a test of its own: that the four runners which reuse the guard (`run_analyst_evals`, `run_manager_evals`, `run_tester_evals` through `analyst.paid.paid_run_refusal`, `run_second_opinion_evals` through `fixture.paid_run_refusal`) call it before starting a session with these wordings — `tests/test_analyst_evals.py` checks the shared function through `evals.paid` for «так», «ні» and the ceiling, not for an unread line. Known residuals, unchanged and on the safe side: «так, 1,000 доларів» reads as a ceiling of 1 dollar, «так, - 5 доларів» as 5; a task file with CRLF line endings refuses «так».

=== UNIT 1 COMPLETE ===
