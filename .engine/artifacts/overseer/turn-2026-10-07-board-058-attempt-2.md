Board task 058, unit 1, attempt 2 — after the overseer's BLOCK #4 (request 20261007T005437Z-a386fa). Everything is staged, nothing committed; the task is still in `tasks/doing/`. The first attempt's turn is `.engine/artifacts/overseer/turn-2026-10-07-board-058.md`.

**What the BLOCK found, and what was done about each point**

1. *«у межах шуму» was decided by float rounding.* True: 1 − 2/3 is larger in floats than 2/3 − 1/3, so with a noise measured between 2/3 and 1/3 a step from 3/3 to 2/3 read WORSE beside "diff −0.33, noise 0.33". Fix in `evals/compare_audits.py`: `rate()` returns an exact `Fraction`, `spread()` and the comparison work in fractions, and a noise or threshold read back from the record (kept there as a decimal) goes through `exact()` (`Fraction(x).limit_denominator(10_000)`). The record file itself did not change (threshold 0.0).
   Tests: for the noise measured three ways — 2/3 against 1/3, 1/3 against 0/3, 3/3 against 2/3 — each of the three one-session steps (3/3→2/3, 2/3→1/3, 1/3→0/3) is «у межах шуму» in both directions and fails nothing, and two sessions of three are still WORSE (12 checks); the same through two `--noise` files given by hand, on the scene they moved on and on a scene they do not have (1 check).
   RED: run against the code the overseer blocked (`/tmp/ca.orig`), the new suite gave 46 passed, 4 failed — «noise measured as 2/3 against 1/3: 3/3 → 2/3 …» and «noise measured as 1/3 against 0/3: 3/3 → 2/3 …» with `{'steady': 'WORSE'} {'steady': 'better'}`; the other two failures of that run were mistakes in my own new checks (a wrong string condition; a `--noise` case that expected the fallback on a scene both noise files have), corrected before the GREEN.
2. *Refusals with no check.* Added: another `model`, `setting_sources`, `runs_per_scenario` each refuse (exit 2, no record, the field named); `--measure-noise` together with `--before/--after` is refused; a file that is not a noise record named by `--noise-record` is refused and no table is printed; the header's «the noise record is another environment's» line, with its negative.
3. *`spread()` counting a scene with a run that has no valid session; `distinct_verdicts` counting ERROR.* Checks added: a scene one run lost entirely has noise n/a (null in the record), never 0; a scene with lost sessions among valid ones still reads «always BLOCK#4».
4. One thing more, found while fixing: two files recorded in different environments were measured together and the record said "a + b". Now refused (exit 2, both environments named), with a check; `recorded_in_all()` is gone.

`evals/README.md` says the rates are compared as exact fractions and why, and that the measurement needs one environment. The test file's header lists the new cases.

**Verification (this turn)**

- `python3 tests/test_audit_noise.py`: 51 passed, 0 failed.
- Eleven mutants of `evals/compare_audits.py`, one per point above, each against the suite before the environment check was added (50 checks then): `model` dropped from the list — 3 failed; `setting_sources` — 2; `runs_per_scenario` — 1; `spread()` allowing a run with no valid session — 1; `distinct_verdicts` counting ERROR — 1; the other-environment line removed — 1; `load_record` without validation — 1; `--measure-noise` with `--before/--after` accepted — 1; `rate()` back to a float — 9; `exact()` without `limit_denominator` — 15; `>=` in place of `>` — 16. None survives. The file was restored from the copy afterwards (51/0 above is on the restored file).
- `bash tests/run_all.sh`: `PASS: 75 suites green`, exit 0 (after the last edit of code; only the README was re-wrapped before it started).
- Not run again: the two paid audits. Their files and the record `audit-noise.json` are as in attempt 1.

**Not done / limits**

- The environment refusal (point 4) was not mutated separately; its check is one case (linux-test-1 with macos-14).
- With the threshold 0.00 the label still fires on no scene of this repository today; it is held by synthetic result files only.
- The two survivors the overseer called equivalent (bound = threshold only; fallback from the defined bounds) were left as they are.

Still to do after the audit: `report.md`, the move to `tasks/done/058-audit-noise-measurement/`, the commit.

Suggested commit message: `board 058: the audit noise measured (two full audits of cdda02e, 72 sessions, threshold 0.00); compare_audits.py reads the noise record, compares in exact fractions and marks «у межах шуму»`

=== UNIT 1 COMPLETE ===
