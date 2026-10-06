Attempt 2 for unit 1 of board task 053, after the overseer's BLOCK #4 (request 20261006T211935Z-597605: the paid-run consent failed open). The fix is committed on `unattended/work` on top of `372a45d`; the task is not yet moved to `done/`.

**What the BLOCK named and what changed**
- **Fails open:** before, any `Платні прогони:` line that did not start with «ні» was leave. Now leave is recognised positively (`board.py`, `paid_leave`): the line begins with «так», or says «скільки потрібно» / «скільки треба» (the owner's tasks 057–059), or names a dollar sum above zero (the wording before this board, tasks 062 and 063). Everything else is no leave, including the word «ні» anywhere in the line, a line starting with «не» / «без» / «немає» / «no» / «not» / «none» (except «не більше N доларів»), and a zero sum.
- **Whole-file search:** the line is now read in the task's header only, as `Аудит потрібен:` is. A line in the body, in a report section or under «Питання до власника» opens nothing. Two such lines in the header are no leave.
- **README said the opposite of the code:** `tasks/README.md` (both copies) and `.claude/references/unattended.md` now state the three wordings of leave, that anything else refuses, and that the line is read at the top of the task only.
- **Missing negatives:** `tests/test_owner_terms.py` gained 26 negative checks: 20 refusals that do not begin with «ні» (among them «не треба», «заборонено», «поки ні», «not allowed», «?», «так чи ні?», «0 доларів»), a refusing header followed by a body line, a line under «Питання до власника», a body line with a sum, two header lines in either order.

**Verification**
- `python3 tests/test_owner_terms.py` — PASS 102, FAIL 0.
- The same test file on a worktree of `372a45d` (the blocked commit): PASS 79, FAIL 23 — the new negatives fail there for the reason the BLOCK named (`(True, None)` where no leave is expected).
- `bash tests/run_all.sh` — `PASS: 74 suites green`, run to the end after the last edit (about 25 minutes; `tests/test_board_runner.py` alone takes about 20).
- Correction to the first claim: on `159f8aa` the first version of the test showed 28 failed checks and then stopped with `AttributeError: 'Task' object has no attribute 'paid'`; the first turn did not mention the crash.
- No paid run was started.

**Still as in the first claim**
- The decisions made alone (the two extra wordings of leave beside «так»; the six-line check in `tests/test_board.py` raised to eight; «юніт», «ескалація», «догляд», «інтеграційні тести» left Ukrainian) and the list of what is not done are unchanged.
- One residual, stated plainly: a header line that names a positive dollar sum and no refusing word is leave even without «так» — that is how tasks written before this board carried their leave, and it is kept on purpose.

=== UNIT 1 COMPLETE ===
