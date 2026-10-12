# Board 752 — the closing turn (2026-10-12), as the builder states it

Task: tasks/doing/752-open-item-overseer-stop-last-request-by-mtime.md (mode соло). The work was made and committed in an
earlier session of this task (commit 4814696):
- `.claude/hooks/overseer_verdict.py`: `last_request(root)` (line 316) picks the request written last from what the
  requests themselves say — key `(folder.name[:16], created_ns or 0, folder.name)`: the second in the id, then the field
  `created_ns` of `request.json`, then the whole id. `make_request` writes `created_ns: time.time_ns()` (line 437).
  A file's modification time is read nowhere.
- `.claude/hooks/overseer_stop.py`: `_code_changed_in_tree` takes its baseline from `ov.last_request(project_dir)`
  (line 621) instead of `max(requests/*/request.json, key=st_mtime_ns)`.
- `tests/test_overseer_fresh.py`, the block «board 752» (lines 691–725): an older request whose file was touched later;
  two requests with one mtime, in both id orders; two requests of one second with one mtime, the planted one on either
  side of the real one's hash (`-000000`, `-zzzzzz`); two real requests written within one second.

That session had one audit (request 20261012T082058Z-8c8a30). It named no failing check and was recorded as BLOCK 1 of 3
for one reason only: the gate escalation 2026-10-12T01:56:46Z of another task (slice `numbers-class-table`,
tests/test_task_class_table.py) was open. The task waited in tasks/blocked/ with that question. The owner answered
«закрито»; `.claude/state/gate/escalations.json` now lists that escalation under `closed` (closed_utc
2026-10-12T10:01:41Z) and `open` is empty. The task says what to do then: claim the unit again, a new overseer judges it.

What this turn changed in working code: nothing. Since 4814696 one other commit touched two of these files — c61466c
(board 757): the wording of a test-gap item in `overseer_verdict.open_test_gaps` and its test. `git diff 4814696 HEAD --
.claude/hooks/overseer_stop.py` prints nothing; the same diff over `overseer_verdict.py` shows only the hunks of
`open_test_gaps` (lines 650–668), none in `last_request` or `make_request`.

What I ran in this turn, on the tree as it is now (HEAD b5b5955, Python 3.12.13), and what it printed:
- `python3 tests/test_overseer_fresh.py` → exit 0, 134 `ok` lines, `PASS: the fresh-context overseer protocol holds,
  every protection with its negative case`.
- RED, in a clone of HEAD (/tmp/b752-wt; baseline there exit 0, the same PASS line), one change at a time, restored with
  `git checkout -- .` after each:
  - the Stop hook's own mtime choice back (`git diff 4814696^ 4814696 -- .claude/hooks/overseer_stop.py | git apply -R`:
    `last = max(…glob("*/request.json"), key=lambda f: f.stat().st_mtime_ns, default=None)`) → exit 1, `FAIL (4)`:
    «negative — an older request whose file was touched later is not the last one…», «…and with the ids the other way
    round the later id is the baseline again…», «negative — two requests of one second, one modification time: the one
    written earlier (…-000000) is not the last», the same for `…-zzzzzz`.
  - mtime as the key inside `last_request` (`max(folders, key=lambda f: (f / "request.json").stat().st_mtime_ns)`) →
    exit 1, `FAIL (3)`: the older request touched later; the ids the other way round; one second, `…-zzzzzz`.
  - `created_ns` dropped from the key (`return folder.name[:16], 0, folder.name`) → exit 1, `FAIL (1)`: one second,
    `…-zzzzzz`.
  - both hooks as they were before the task (the whole hook diff of 4814696 reversed) → exit 1, but by a crash, not by a
    check: `KeyError: 'created_ns'` in the test's `plant_request` (line 673), because the old `make_request` wrote no such
    field. I count this as «the suite does not pass on the old code», not as a red check.
- `bash tests/run_all.sh`, once → `PASS: 98 suites green`, exit 0 (`.claude/state/health/tests-full.json`: commit
  b5b5955, dirty false, recorded 2026-10-12T23:02:28Z, 705.1 seconds). The fast subset was not run separately: its
  suites are among the 98.

The counts differ from the ones the first session wrote in the task (mtime in `last_request` — four red, `created_ns`
dropped — two): today three and one. I did not find out why by experiment. My reading, not verified: with equal mtimes
the mtime key leaves the choice to the order `glob` returns, and with `created_ns` dropped two real requests of one
second are ordered by the random hash in the id — so one check in each mutant is red or green by chance. Each mutant
was run once.

Known and not fixed here: no test covers requests WITHOUT the field `created_ns` (every request written before this
task). The first audit named it as a test gap and tried the code by hand (the `isinstance` check falls back to 0). It
is a task on the board, tasks/todo/1726-open-item-test-gap-with-two-requests-on-disk-whose.md, and stays in todo/; this
turn does not touch it.

Decisions I made alone (from the first session, unchanged): (a) the id alone is not enough — its time is exact to a
second and a hash follows, so `created_ns` was added and the id's format left alone; (b) a request without the field
counts as 0, and inside one second the id decides; (c) a damaged `request.json` of the last request reads as empty, and
the signal takes the fallback path (files no accepted PASS has seen) instead of saying «nothing changed».

=== UNIT 1 COMPLETE ===
