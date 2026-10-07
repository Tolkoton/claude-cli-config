Unit done and committed as `ed205b6`: the paid-run guard now takes only «так» at the start of the `Платні прогони:` line as leave, with an optional dollar sum after it as the ceiling; anything else in the line refuses, and the list of negations is gone from `board.py`.

Verification: `bash tests/run_all.sh` — 81 suites green; `python3 tests/test_owner_terms.py` — PASS 158, FAIL 0 (29 of these fail on the previous guard); `python3 tests/test_paid_run_gate.py` — PASS 38, FAIL 0 (4 fail on the previous guard).

The task is not closed yet: the owner asked for an overseer audit of this unit, and the report and the move to `done/` follow its verdict.

=== UNIT 1 COMPLETE ===
