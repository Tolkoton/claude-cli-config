# Default complexity limits for this repository — a proposal (board 010)

The complexity budget measures a function a change adds or makes worse against two limits.
Until now they were the built-in 10 (cyclomatic complexity) and 3 (nesting depth), numbers
from nowhere. `complexity_budget.py calibrate` reads the functions the project already has and
proposes the 90th percentile — what nine functions in ten already keep to.

Measured on 2026-10-03 at `0ed18d0` (428 production functions under `.claude/hooks`,
`.claude/unattended` and `evals`, tests and scenario fixtures excluded):

| metric | p50 | p75 | p90 | p95 | max | proposed | functions already above it |
|---|---|---|---|---|---|---|---|
| COMPLEXITY_MAX_CYCLOMATIC | 4 | 7 | 13 | 17 | 88 | 13 | 40 |
| COMPLEXITY_MAX_NESTING | 1 | 2 | 3 | 4 | 11 | 3 | 29 |

What changes if you apply it: a new or worsened function of complexity 11–13 stops being a
signal; nesting stays at 3. Functions already above the limits are not charged to anyone until a
change makes them worse. Not applying it keeps 10 and 3.

Only the owner applies it: the command refuses inside an agent's session, and the gate's bypass
guard blocks a change of either key made by the work it judges. From the repository root, in
your own terminal:

```bash
python3 .claude/hooks/complexity_budget.py set-defaults 13 3 && python3 tests/test_complexity_budget.py
```

The test (`DEFAULT-*` cases) shows the keys being read, the refusal inside a session, and that a
second run replaces the values. To see fresh numbers first: `python3 .claude/hooks/complexity_budget.py calibrate`.
