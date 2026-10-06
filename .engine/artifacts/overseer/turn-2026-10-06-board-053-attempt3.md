Attempt 3 for unit 1 of board task 053, after the overseer's second BLOCK #4 (request 20261006T220848Z-79d458). The fix is commit `f5ea10c` on `unattended/work`, on top of `3a6f912`; the task is not yet moved to `done/`.

**What the second BLOCK named and what changed** (`.claude/unattended/board.py`, `paid_leave` and the `PAID_*` expressions above `ATTENDED`)
- **A refusal after «так» was seen only as the word «ні».** Now a negation anywhere in the line takes the leave back: «ні», «не», «без», «нема…», «ніко…», «нія…», «ніде», «ніщо», «нічого», «жодн…», «заборон…», «відмов…», «нет», «no», «not», «none», «never», «don't», «nothing». «так, але не для audit-у», «так, але без audit-у», «так, тільки не audit», «так не можна», «так? не впевнений» are all no leave, for the audit guard too.
- **A refusal that named a sum was leave.** A bare sum is no longer leave. The sum counts only as a limit: one of «ліміт…», «до», «не більше», «не понад», «запобіжник…» directly before a dollar sum above zero. The negation check runs on the whole line; only «не більше», «не понад» and «не бюджет» (the owner's own wording in task 063) are excused as a limit's words. «заборонено, навіть 5 доларів», «ніколи, навіть за 5 доларів», «ніяких прогонів дорожчих за 5 доларів», «never, 5 USD», «витрачено 3 долари», «відмова 5 доларів», «1e3 доларів» are no leave.
- **Claims no test held.** «так» must be the line's first word (`match`, word boundary): «мабуть, так не варто», «також…», «такий…» are no leave and are tested. Each negation word has its own check («так, <word> audit»).
- **Mutants.** 52 mutants of the rule, each run against `tests/test_owner_terms.py`: 0 survive. They include the three the overseer found (PAID_NO cut down to «ні»; «так» anywhere; «так» as a prefix), PAID_NO without each single word, each limit word removed, the excused words removed one by one and widened to any «не X», the zero-sum check removed or weakened, max or first sum instead of the smallest, any sum as leave, each of the three wordings disabled, first of two lines, whole text instead of header, the audit guard ignoring the line. The script is `/tmp/t053/mutate.py` (it mutates a copy of the tree in `/tmp/t053/mut`); it is a one-off and is not in the repository.
- **README.** `tasks/README.md` (both copies) and `.claude/references/unattended.md` state the three wordings, that a negation anywhere refuses, and tell the owner to write a restriction affirmatively («так, лише прогони simplifier-а») or as a point of «Що зробити».

**Verification**
- `python3 tests/test_owner_terms.py` — PASS 186, FAIL 0. `python3 tests/test_paid_run_gate.py` — PASS 30, FAIL 0.
- The same two files on a worktree of `3a6f912` (the commit of the second BLOCK): PASS 136 FAIL 50, and PASS 27 FAIL 3.
- `bash tests/run_all.sh` — `PASS: 74 suites green`, run to its end after the last edit of code and tests.
- Every «Платні прогони:» line the owner has on the board today is still leave, with the ceiling it names: tasks 057, 058, 059 (no ceiling), 062 (5), 063 (50), the fixture of 010 (30). These lines are cases of the test.
- No paid run was started.

**Residuals, stated plainly**
- The list of negations is a list. A refusal that uses none of its words AND one of the three wordings of leave is still leave — for example «так, хоча краще утриматися». A refusal without a wording of leave («утримаюсь») is refused, because leave is recognised, not assumed.
- A limit word directly before a sum is leave without «так»: «до 5 доларів» opens paid runs up to 5 dollars. That is how tasks written before this board carry their leave (062, 063), and it is kept on purpose.
- An affirmative restriction after «так» («так, лише прогони simplifier-а») is leave for every paid-run script, the audit included: the scripts do not read which runs were meant. The README says to put a restriction the scripts must honour into «Що зробити»; the agent reads it there.
- The decisions made alone and the «not done» list of the first claim are unchanged.

=== UNIT 1 COMPLETE ===
