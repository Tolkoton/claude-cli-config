# Board 740 — the closing turn (2026-10-12), as the builder states it

Task: tasks/doing/740-open-item-board-start-attended-separate-clone.md (mode соло). The work was made and committed in
an earlier session of this task (commit 0b8298a):
- `.claude/unattended/board.py`: `cmd_next` takes `board.in_hand(attended)` (line 475) and `cmd_start` takes
  `board.in_hand(read(source).attended)` (line 504) where both took `board.files("doing") if attended else
  board.in_hand()`. The owner's session (`--attended`) now looks at the attended tasks of doing/ only: the runner's task
  there neither stops it nor is offered to it. In `start` the side is the task's, not the flag's: an ordinary task
  started with `--attended` beside the runner's task is still refused. The module text (lines 133–136) says so.
- `tests/test_board.py`: eight checks under «The owner's session in a separate clone sees the runner's task in doing/
  (board 740)» (`git show 0b8298a -- tests/test_board.py | grep -c '^+check('` prints 8), three of them negative (an
  ordinary task with `--attended` beside the runner's is refused; a second attended task is refused and the refusal
  names the attended one, not the runner's; two attended tasks in doing/ make `next --attended` exit 2). The note the
  first session left in the task file says «дев'ять нових перевірок»: that count was wrong, it is eight; the figures
  `PASS 312 FAIL 6` and `PASS 318 FAIL 0` in the same note are right.
- `tasks/README.md` and `templates/project/tasks/README.md` («Задачі з присутнім власником», step 1): in a separate
  clone there is no need to wait for the runner to stop.

That session had one audit (request 20261012T073304Z-d26b7d). It named no failing check and was recorded as BLOCK 1 of 3
for one reason only: the gate escalation 2026-10-12T01:56:46Z of another task (slice `numbers-class-table`,
tests/test_task_class_table.py) was open. The task waited in tasks/blocked/ with that question. The owner answered
«закрито»; `.claude/state/gate/escalations.json` now lists that escalation under `closed` (closed_utc
2026-10-12T10:01:41Z) and `open` is empty. The task says what to do then: claim the unit again, a new overseer judges it.

What this turn changed in working code: nothing. `git diff --stat 0b8298a HEAD -- .claude/unattended/board.py
tests/test_board.py tasks/README.md templates/project/tasks/README.md` prints nothing, and `git log --oneline
0b8298a..HEAD` over the same four paths prints nothing: the files are as 0b8298a left them.

What I ran in this turn, on the tree as it is now (HEAD 40cd748, Python 3.12.13), and what it printed:
- `python3 tests/test_board.py` → `PASS 318   FAIL 0`.
- RED, in a detached worktree of HEAD (/tmp/b740-wt, removed afterwards; baseline there `PASS 318   FAIL 0`), one
  change of `.claude/unattended/board.py` at a time, the file restored after each:
  - the whole file as it was before the task (`git show 0b8298a^:.claude/unattended/board.py`) → `PASS 312   FAIL 6`:
    «only the runner's task in doing/, todo/ empty: `next --attended` does not offer it (exit 3)», «the runner's task in
    doing/ is not in the way: `next --attended` offers the attended 714», «…and `start --attended` puts 714 beside the
    runner's task», «…and the owner's session only its own», «…the negative case: a second attended task is refused, and
    the refusal names the attended one, not the runner's», «…two attended tasks in doing/ are refused (exit 2)». The
    two other new checks are green on the old code too: «…the negative case: `start --attended` of an ORDINARY task
    beside the runner's is refused…» (the old code refused beside any task) and «…the runner still sees only its own
    task». Each of the two is red under the next change.
  - line 504, the side taken from the flag (`board.in_hand(attended)`) → `PASS 316   FAIL 2`: «…the negative case:
    `start --attended` of an ORDINARY task beside the runner's is refused…» (exit 0) and «…the runner still sees only
    its own task» (exit 2: doing/ holds 013-runners.md and 715-ordinary.md).
  - line 475, `cmd_next` as before the task (`board.files("doing") if attended else board.in_hand()`) → `PASS 314
    FAIL 4`: the two `next --attended` checks with only the runner's task in doing/, «…and the owner's session only its
    own», «…two attended tasks in doing/ are refused (exit 2)».
- `bash tests/run_all.sh`, once to the end → `PASS: 98 suites green`, exit 0 (`.claude/state/health/tests-full.json`:
  commit 40cd748, dirty false, recorded 2026-10-12T22:31:10Z, 687.9 seconds). A first start of the same command in this
  turn was stopped by the tool's ten-minute limit before it printed a result; it is not evidence of anything and I
  count only the second run.

Not run in this turn: ruff and mypy by hand (they run inside `tests/test_engine_lint.py`, one of the 98 suites); a live
run in two real clones with a runner on a server — the checks drive `board.py` through its command line on a temporary
board, which is the same code a second clone runs.

The test gap the first audit opened — tasks/todo/1724-… (with only an attended task in doing/, `start --attended` of an
ordinary task is allowed and stands beside it) — is not written in this task: it is a task on the board and stays in
todo/; this turn does not touch it.

Decisions I made alone (from the first session, unchanged): (a) in `start` the side of the task is the task's own line
«Потрібна присутність власника», not the flag `--attended` — otherwise an ordinary task started with the flag would
stand beside the runner's and the runner would see two of its own; (b) `next --attended` no longer prints an ordinary
task lying in doing/ — a plain `next` shows it.

=== UNIT 1 COMPLETE ===
