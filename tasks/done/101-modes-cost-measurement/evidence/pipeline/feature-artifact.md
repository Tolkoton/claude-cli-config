# Feature split-evenly — decomposition

Source of the frame: the board task `tasks/doing/010-split-evenly.md` (the owner's text, mode
`конвеєр`). The session is unattended: items the owner would have ratified in the interactive
round are marked `PROVISIONAL — owner ratification pending`.

## Goal
`refproj.pricing` gets a pure function `split_evenly(amount: Decimal, parts: int) -> list[Decimal]`
that divides a money amount into `parts` shares to the cent, so that the shares add up to exactly
`amount`, differ from each other by at most one cent, and the larger shares come first.

## Acceptance criteria (owner-ratified)
Taken verbatim in meaning from the task's «Що зробити» and «Готово, коли» — the owner's own text:
- AC1. `split_evenly(Decimal("10.00"), 3)` returns `[Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]`.
- AC2. The sum of the shares always equals `amount`.
- AC3. The shares differ by at most one cent; larger shares come first.
- AC4. `parts` less than one → `ValueError`; `amount` less than zero → `ValueError`. Both are tested.
- AC5. The function is typed; the project's lint (`ruff check`), type-check (`mypy`, strict) and
  tests (`pytest`) are green.

No approved goals document exists (`goals.py status`: `.engine/goals.md` is an unfilled template,
not in force), so the criteria cite the task, not G/D lines.

## Build parameters (owner-authorized, from Phase 1e)
- Budgets/thresholds: none. The only number in the feature is «one cent», and it is the owner's (task text).
- Policies: errors are `ValueError` with a message that names the offending value, as
  `apply_discount` already does; no logging; money is `decimal.Decimal`, the cent is
  the module's existing constant `CENT`; pure functions, no I/O, no injected dependencies.
- Risk tolerance: auto-spike = yes; proceed on a PASSing spike = yes (the engine's default; `PROVISIONAL — owner ratification pending`, moot here: no spike is needed).
- Autonomy: build all slices automatically; interrupt only on the critical set.
  `PROVISIONAL — owner ratification pending` (unattended run started by the board runner; cost to
  reverse: revert one function and its tests).
- Principles that bear on the slices: none recorded — there is no approved goals document.
- Decisions the task left open, taken by the architect (two-way doors, each reversible by editing
  one function and its tests):
  - D-A. An `amount` that is not a whole number of cents (`Decimal("10.005")`) or is not finite
    (`NaN`, `Infinity`) → `ValueError`. Why: for such an amount «shares to the cent» and «the sum
    equals `amount` exactly» cannot both hold, and silently rounding would break AC2. Rejected:
    round `amount` to cents first (hides a lost half-cent from the caller). The finiteness check
    comes before the sign check: `Decimal("NaN") < 0` raises `decimal.InvalidOperation`, which is
    not a `ValueError`. Logged AUTONOMOUS in `.engine/overseer/escalations.md` (two-way door).
  - D-B. Every share is returned with exactly two decimal places (`Decimal("3.34")`,
    `Decimal("0.00")`), whatever the exponent of `amount` (`Decimal("10")` → `3.34, 3.33, 3.33`).
  - D-C. `amount == 0` is lawful: `parts` shares of `Decimal("0.00")`; negative zero
    (`Decimal("-0.00")`, which is not less than zero) gives the same positive `Decimal("0.00")` shares.
    `parts == 1` returns one share equal to `amount`, with two decimal places like any other share.
  - D-D. No limit on the size of `amount`, and no dependence on the caller's `decimal` context:
    the result is exact for every finite non-negative whole-cent `Decimal`, a 30-digit one
    included. The function therefore uses no context-rounded operation (`*`, `/`, `quantize`,
    `scaleb`): cents come in through `Decimal.as_integer_ratio()` and go out through the exact
    `Decimal((0, digits, -2))` constructor. «Any size» means: not limited by the context's
    precision; an amount too large for the interpreter to hold as an integer (an astronomically
    large exponent) is resource exhaustion, outside the contract (slice contract, «Seam»). Rejected: `ValueError` above 28 significant digits
    (a third refusal the owner did not ask for, with a limit that moves with the caller's context).
    A caller that adds up shares of more digits than its own context holds must widen that
    context itself — the test of AC2 on such an amount sums under `decimal.localcontext`.

## Premises verified
- PR-split-01 — «A finite `Decimal` with no fraction of a cent converts to an exact integer number
  of cents, and integer `divmod` on it gives base share and remainder with no rounding» —
  evidence: runtime check in this session with the project's interpreter
  (`Decimal('10.00').as_integer_ratio() == (10, 1)`, `Decimal('10.005').as_integer_ratio() == (2001, 200)`,
  `divmod(1000, 3) == (333, 1)`, `sum([3.34, 3.33, 3.33]) == Decimal('10')` → True) — 2026-10-11 — premise-log row PR-split-01.
  The way back is verified too: for `Decimal("1" + "0"*30 + ".01")` split by 3, shares built with
  `Decimal((0, digits, -2))` came out as `…333.34, …333.34, …333.33` and their sum under a
  100-digit `localcontext` equalled the amount (same session, same interpreter; the feature
  critic's round 1 probed the same path on a 33-digit amount).
- No external system, no other component: the function is consumed by nothing in this feature.

## Out of scope (deliberately)
- Currencies whose smallest unit is not 0.01 (no `unit` parameter).
- Weighted or proportional splits; choosing who gets the extra cents by any rule other than «first».
- Negative amounts (refund splitting) — the task says `ValueError`.
- Any caller: `inventory` and the rest of `refproj` are not changed; nothing uses `split_evenly` yet.

## Звірка з цілями
- служить: — (затвердженого документа цілей немає; критерії посилаються на текст задачі 010)
- вибір між варіантами розв'язав: принципів немає, вибір технічний
- не-цілі й обмеження: не записані

## Slices (the DAG)
- **S1 split-evenly-fn** — delivers: `split_evenly` in `src/refproj/pricing.py` with its tests in
  `tests/test_pricing.py` (AC1–AC5, D-A…D-D) · contract out: `split_evenly(amount: Decimal, parts: int) -> list[Decimal]`,
  a list of exactly `parts` non-negative two-decimal `Decimal`s in non-increasing order · depends on: — · **TRACER BULLET (build first)**

One slice, one block. The feature is one pure function with one validation step and one
arithmetic step: a second slice (for example «validation» apart from «allocation») would have no
behaviour of its own that a test could observe through the public function.

## Inter-slice contracts
- None: the DAG has one node and no edge.

## Integration exit criterion
S1 is the whole chain. Proof: `tests/test_pricing.py` green under `pytest`; `ruff check` and
`mypy` green on the project; and the smoke `scripts/smoke_test_split_evenly_fn.py`, run against
the real module (`PYTHONPATH=src .venv/bin/python scripts/smoke_test_split_evenly_fn.py`), prints the shares of 10.00 by 3 and exits non-zero unless
they are 3.34, 3.33, 3.33. The rules themselves are tested once, in `tests/`; the smoke repeats
none of them. (The project's mypy scope is `src` and `tests`: the smoke script is linted by ruff
and not type-checked.)

## Deferred to later features
- A `unit` parameter for other currencies — why later: nobody asked — revisit trigger: the first non-cent currency in the project.
- A caller of `split_evenly` (for example splitting a basket total between payers) — why later: not in the task — revisit trigger: a task that names the caller.

## Open items requiring human decision (if any)
- None. D-A is a two-way door decided by the architect and logged AUTONOMOUS in
  `.engine/overseer/escalations.md`; the task's report names it for the owner.

## Appendix — critic notes (round 1)
- `parts=True` is an `int` and yields one share; harmless, the slice planner may pin or ignore it.
- A one-slice feature is slice-planner sized; it is kept at feature level because the owner's task line is `Режим: конвеєр`.

## Appendix — critic notes (round 2, PASS) — for the slice planner
- A non-integral `parts` at runtime (`2.5`): say «the type is the contract, no runtime check» or pin it.
- `Decimal("3.34") == Decimal("3.340")`: an `==` assertion does not pin D-B; the test must check the exponent or the string.
- D-B, D-C and D-D are architect choices too: the task's report names all four, not only D-A.
- The slice contract states how the smoke imports `refproj` (`PYTHONPATH=src`), so the exit command is reproducible.

## Appendix — simplifier (before the slices were cut)
- Smoke as a second test suite plus an extra mypy run (requirements lens) — applied: the smoke
  only prints and checks 10.00 by 3.
- D-D «exact at any size, in any context» called an invented requirement by both lenses — not
  applied: the feature critic's round 1 BLOCKED the plan that left large amounts undefined (the
  probed result there was a silently wrong sum, against the owner's «завжди»), and the exact path
  costs the same few lines as the rounded one. The finding stays in `.engine/simplifier/report.md`
  for the owner; the choice is logged AUTONOMOUS in `.engine/overseer/escalations.md`.
