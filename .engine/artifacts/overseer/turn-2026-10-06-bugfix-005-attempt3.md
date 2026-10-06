Bug 005 (board 718), third claim, after the second overseer's BLOCK (request 20261006T082744Z-dfacc8). No working code changed since that audit; the record and the board did. Nothing is committed and the task is still in `tasks/doing/`.

What the second audit asked for, and what was done:

- **The scope of the search is now stated, and the sentence about completeness is gone.** Section 4 of `.engine/bugs/005-resolve-loop-other-scripts.md` says this fix covers `.claude/hooks/*.py`, `.claude/unattended/*.py` and `engine.py` (27 `resolve()` lines at the base commit, 26 in the tree with the fix, each named), and that it does not cover the rest.
- **The search over everything the repository ships outside `tests/` was run** (`git ls-files --cached --others --exclude-standard | grep -v ^tests/`, lines with `resolve(`, `realpath` or `readlink -f`). Every hit outside the scope is listed in section 4 by file and line. None of them is fixed here.
- **They became one board task**, `tasks/todo/719-open-item-718-resolve-loop-outside-hooks.md`: it names each line, says which two the audit reproduced (`.claude/skills/documentation/scripts/doc_audit.py:152`, `evals/run_audit_scenarios.py:649`) and which are read only (`evals/run_simplifier_evals.py:84`, `evals/environment.py:78`, `evals/run_hook_scenarios.py:115,210,356`), and which are a root rather than a path inside it.
- **Python 3.13 is corrected from the documentation**, not from memory: a non-strict `resolve()` raises nothing on a loop from 3.13, and `RuntimeError` before it (https://docs.python.org/3.13/library/pathlib.html, quoted in section 4). The earlier words «an OSError, still raised» were wrong.

Unchanged from the second claim: six places fixed in the scope — `bugfix.py` `test_files`, `goals.py` `cmd_check`, `lesson_queue.py` `context_lines` (imports and CLAUDE.md itself), `board.py` `cmd_start` and `audit-allowed --tasks-dir`.

Verification, run in this turn after the last change:

- `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/005-resolve-loop-other-scripts.md --test tests/test_<suite>.py …` — PROVED for `test_bugfix.py`, `test_goals.py`, `test_lesson_queue.py` and `test_board.py` against `98fc93e`.
- `python3 .claude/hooks/complexity_budget.py check` — within budget: 0 new files, +11 lines of working code, tests +39.
- `bash tests/run_all.sh --fast` — 32 suites green.

Still owed after the audit: section 7 of the record, the full `bash tests/run_all.sh` once, `report.md`, the move to `tasks/done/`, and the commit.

=== UNIT 1 COMPLETE ===
