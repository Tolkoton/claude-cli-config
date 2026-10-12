# Board 726 — the closing turn (2026-10-12), as the builder states it

Task: tasks/doing/726-open-item-058-noise-three-files.md (mode соло). The work was made and committed in an earlier
session of this task (commit 8cbe66c, base dd9b7e5):
- `evals/compare_audits.py`: `spread()` takes the noise of a scene over the runs that hold a valid session for it —
  `max(known) - min(known) if len(known) > 1 else None`; before, one run without a valid session made the noise `None`
  (`… and len(known) == len(rates)`), against the function's own docstring. The docstring, the module docstring and the
  sentence under the report of `--measure-noise` now state that one rule, and the report names a scene measured from
  fewer runs than were given (`holed` (2 of 3 runs)).
- `evals/README.md`: the same rule in the paragraph on `--measure-noise`.
- `tests/test_audit_noise.py`: a three-file case (3/3, 2/3, every session lost → noise 0.33, counted in the threshold,
  the scene named as moved and as «2 of 3 runs»; one run with a valid session → n/a; a comparison by that record reads a
  one-session step on the holed scene as «у межах шуму»).

That session had one audit (request 20261012T061608Z-287b1c). It named no failing check and was recorded as BLOCK 1 of 3
for one reason only: the gate escalation 2026-10-12T01:56:46Z of another task (slice `numbers-class-table`,
tests/test_task_class_table.py) was open. The task waited in tasks/blocked/ with that question. The owner answered
«закрито»; `.claude/state/gate/escalations.json` now lists that escalation under `closed` (closed_utc
2026-10-12T10:01:41Z) and `open` is empty. The task says what to do then: claim the unit again, a new overseer judges it.

What this turn changed in working code: nothing. Since 8cbe66c one later task of this branch (730, commit e8b168c)
changed one line of `evals/README.md` (`git diff --stat 8cbe66c HEAD -- evals/README.md evals/compare_audits.py
tests/test_audit_noise.py` → `evals/README.md | 2 +-`); `evals/compare_audits.py` and `tests/test_audit_noise.py` are as
8cbe66c left them.

What I ran in this turn, on the tree as it is now (HEAD d74f2cc, Python 3.12.13), and what it printed:
- `python3 tests/test_audit_noise.py` → `56 passed, 0 failed`.
- RED, in a detached worktree of HEAD (/tmp/b726-wt, removed afterwards; baseline there `56 passed, 0 failed`): the one
  line of `spread()` put back as it was before the task
  (`return max(known) - min(known) if len(known) > 1 and len(known) == len(rates) else None`, `git diff --stat` →
  `evals/compare_audits.py | 2 +-`), then `python3 tests/test_audit_noise.py` → `52 passed, 4 failed`.
- `bash tests/run_all.sh`, once → `PASS: 98 suites green`, exit 0.

Not run in this turn: ruff and mypy by hand (they run inside `tests/test_engine_lint.py`, one of the 98 suites); no
session of Claude was started by any eval script — the suite works on small result files it writes itself.

The two test gaps the first audit opened — tasks/todo/1717-… (a holed scene whose holding runs agree: noise 0.0, not
null, and still named «2 of 3 runs») and tasks/todo/1718-… (a scene absent from one file altogether, no row) — are not
written in this task: they are tasks on the board and stay in todo/; this turn does not touch them.

Decisions I made alone (from the first session, unchanged): the rule chosen is the one the task recommended; the line
«N of M runs» was added to the report so that a noise measured from fewer runs than were given is visible; `--noise` by
hand still takes exactly two files, so the three-file rule is reachable only through `--measure-noise` — that limit is
left alone.

=== UNIT 1 COMPLETE ===
