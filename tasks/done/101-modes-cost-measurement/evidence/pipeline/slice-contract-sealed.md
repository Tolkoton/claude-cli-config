# Slice split-evenly-fn — planning artifact

Driven by the feature `.engine/architecture/feature/split-evenly.md` (slice S1, the tracer bullet
and the only slice). The frame below is supplied by that artifact and by the owner's task
`tasks/doing/010-split-evenly.md`, including the owner's answer «а» to the question of that task
(2026-10-11): the promise covers ordinary money amounts only.

## Goal
`refproj.pricing` gets the pure function `split_evenly(amount: Decimal, parts: int) -> list[Decimal]`:
it divides a money amount into `parts` shares to the cent so that the shares add up to exactly
`amount`, differ by at most one cent, and the larger shares come first. Measurable signal:
`split_evenly(Decimal("10.00"), 3)` returns shares that print as `3.34`, `3.33`, `3.33`; the
tests named under «Exit criterion» are green; `ruff check`, `mypy` and `pytest` are green on the project.

## Covered inputs (the owner's decision D-D — everything below speaks about these only)
- `amount` is a `Decimal` that is either not finite (`NaN`, `sNaN`, `Infinity`, `-Infinity`) or
  an **ordinary amount**: finite, with at most 28 significant digits (what the default `decimal`
  context holds exactly), with an exponent not below -28, and with an absolute value below
  `10**26` (so the amount in cents has at most 28 digits as well).
- `parts` is an `int` of any sign; when it is positive, a list of `parts` shares is one the
  caller can hold in memory.
- The call is made under the default `decimal` context (`prec=28`, the default rounding and traps).
- About any other input or context this contract says nothing: no result is promised, no refusal
  is promised, and no test is written. This is the owner's choice (answer «а»), the same region
  in which `total` and `apply_discount` work. The numbers 28 and `10**26` are the owner's
  «до 28 значущих цифр»; the exponent bound is the same number applied to the exponent.

## Premise verified
- PR-split-01 (`.engine/premises/premise-log.md`) — for an ordinary amount under the default
  context: `Decimal.as_integer_ratio()` gives numerator and denominator exactly, the amount is a
  whole number of cents exactly when the denominator divides 100, integer `divmod` splits the
  cents with no rounding, and `Decimal(cents) * Decimal("0.01")` is the exact two-decimal
  `Decimal` (exponent -2, positive sign, `0.00` for zero) — evidence: runtime check with the
  project's interpreter, 2026-10-11: `Decimal(334) * CENT` → `3.34`, `Decimal(0) * CENT` → `0.00`,
  `Decimal(10**28 - 1) * CENT` → `99999999999999999999999999.99` (exponent -2); ratios of
  `10`, `1E+2`, `10.000`, `-0.00`, `0` have denominator 1, of `10.005` — 200, of `0.125` — 8, of
  `1E-28` — `10**28`; `is_finite()` is `False` for all four non-finite values;
  `99999999999999999999999999.99` by 3 gives three equal shares whose `sum()` equals the amount.
- No external system: no network, no file system, no third-party library; only the standard
  library's `decimal` (Python ≥ 3.12, `pyproject.toml`).

## Out of scope (deliberately)
- Amounts and `decimal` contexts outside «Covered inputs» — the owner's answer «а».
- Currencies whose smallest unit is not 0.01 — no `unit` parameter; nobody asked.
- Weighted or proportional splits, or any rule for who gets the extra cents other than «the first shares».
- Negative amounts (splitting a refund) — the task says `ValueError`.
- Any caller: `refproj.inventory` and the existing functions of `refproj.pricing` are not changed.
- A runtime check of the type of `parts` or `amount` — the annotations under `mypy --strict` are the contract.

## Seam (contract)
- Signature: `def split_evenly(amount: Decimal, parts: int) -> list[Decimal]` in `src/refproj/pricing.py`.
- Returns: a new list of exactly `parts` shares. Every share is a non-negative `Decimal` with
  exactly two decimal places (exponent `-2`, positive sign — `Decimal("0.00")`, never `-0.00`),
  whatever the exponent of `amount` (`Decimal("10")`, `Decimal("1E+2")`, `Decimal("10.000")` and
  `Decimal("10.00")` are all lawful). With `cents` = the amount in cents,
  `base, extra = divmod(cents, parts)`: the first `extra` shares are `base + 1` cents, the
  remaining `parts - extra` shares are `base` cents.
- Errors: raises `ValueError`, with a message in which the offending value appears (as
  `apply_discount` does), when
  - E1. `parts < 1`;
  - E2. `amount` is not finite (`NaN`, `sNaN`, `Infinity`, `-Infinity`);
  - E3. `amount < 0`;
  - E4. `amount` is not a whole number of cents (`Decimal("10.005")`).
  A refusal never surfaces as another exception type — in particular not as
  `decimal.InvalidOperation` or `OverflowError`. When several refusals apply at once, which one's message is shown
  is not part of the contract, and neither is the wording of a message: the contract is the type
  `ValueError` and that the offending value appears in the text.
  A lawful amount is never refused: `Decimal("10.000")` is a whole number of cents and is split
  like `Decimal("10.00")`.
- Lawful edge inputs: `amount == 0` (and `Decimal("-0.00")`, which is not less than zero) →
  `parts` shares of `Decimal("0.00")`; `parts == 1` → one share numerically equal to `amount`,
  with two decimal places like any other; more parts than cents (`Decimal("0.01")` by 3) →
  `0.01, 0.00, 0.00`.
- Dependencies (injected): none — a pure function; it reads no clock, no randomness, no global state.
- Does NOT do: round a non-cent amount; accept a negative amount; take a currency unit; check
  argument types at runtime; mutate or cache anything; promise anything outside «Covered inputs».

## Decisions (with WHY)
- Q1: integer-cent arithmetic — `numerator, denominator = amount.as_integer_ratio()`, refusal E4
  when `100 % denominator != 0`, `cents = numerator * (100 // denominator)`, integer `divmod`,
  and each share built as `Decimal(share_cents) * CENT` — chosen because on the covered inputs
  every step is exact, the cent check is an exact integer test instead of a comparison of
  rounded values, and the owner was told in the task's question that the integer-cent
  implementation stays. Rejected:
  (a) `(amount / parts).quantize(CENT, ROUND_DOWN)` plus handing out the leftover cents — the
  idiom the module's other functions use and the shortest to read, but the leftover has to be
  computed back from rounded shares (`amount - share * parts`), two more context operations to
  reason about for the same number of lines;
  (b) `int(amount * 100)` — one line, but it truncates a half-cent silently (`10.005` → 1000),
  so E4 would need a second, separate check anyway;
  (c) the exact tuple constructor `Decimal((0, digits, -2))` on the way out, from the previous
  draft — independent of the context, but that independence is exactly what the owner's answer
  «а» took out of the promise, and `Decimal(cents) * CENT` reads like the rest of the module.
- Q2: an amount that is not a whole number of cents → `ValueError` (E4) — chosen because for such
  an amount «shares to the cent» and «sum equals `amount`» cannot both hold; an amount that is
  not finite → `ValueError` (E2) — because `NaN` and `Infinity` have no number of cents at all.
  Rejected: round the amount to cents first — friendlier to a caller holding `10.005`, but the
  returned shares would no longer add up to what was passed, the one thing the owner asked to be
  exact. Logged AUTONOMOUS (two-way door) in `.engine/overseer/escalations.md`; named for the
  owner in the task's question, which the owner answered without objecting.
- Q3: finiteness is checked before the sign — chosen because `Decimal("NaN") < 0` raises
  `decimal.InvalidOperation`, which is not a `ValueError`. Rejected: rely on the sign comparison
  alone — one check fewer, but leaks an exception type the task does not name.
- Q4: no runtime type check of `parts` (`True`, `2.5`) — chosen because the project is `mypy --strict`
  and its other functions (`apply_discount(percent: int)`, `reserve(quantity: int)`) check values,
  not types. Rejected: `isinstance(parts, int)` guard — would give a clean refusal to an untyped
  caller, but adds a refusal nobody asked for and a convention the module does not have.
- Q5: the function lives in `src/refproj/pricing.py`, its tests under `tests/` — in the
  independent tester's own sealed file(s) when the testing manager assigns the contract tests to
  the tester, in `tests/test_pricing.py` when it assigns them to the builder — chosen
  because the task names `refproj.pricing` and the project keeps its tests per module under `tests/`.
  Rejected: a new module `refproj/splitting.py` — would isolate the new code, but contradicts the
  owner's «у `refproj.pricing`».
- Q6: every share has exactly two decimal places, also when `amount` has another exponent
  (`Decimal("10")`) — chosen because the result is money to the cent and a caller printing it sees
  `3.34`, `0.00`. Rejected: keep the exponent of `amount` — «closest to the input», but `Decimal("10")`
  by 3 has no representation with exponent 0.
- Q7: no guard at the edge of «Covered inputs» (no `ValueError` above 28 digits) — chosen because
  the owner rejected exactly that as option (в). Rejected: the guard — a clean refusal instead
  of silence, but a third refusal the owner declined.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- In every seam below, an amount with no `parts` named is split by 3, and the 28-digit amount
  always has its `parts` named (2): by 3 it leaves no remainder, which would make the remainder
  path vacuous for it. Zero and negative zero are the exception — no divisor leaves a remainder there.
- **Seam 1: `Decimal` equality ignores the exponent and the sign of zero** —
  `Decimal("3.34") == Decimal("3.340")`, `Decimal("0") == Decimal("0.00")` and
  `Decimal("-0.00") == Decimal("0.00")`, so a list `==` assertion passes for shares with the
  wrong number of decimal places or the wrong sign. Test approach: the rules of I3 are asserted
  on the representation — `share.as_tuple().exponent == -2` and `share.as_tuple().sign == 0`
  (and the printed form for the 10.00-by-3 example) — on amounts whose own exponent is not -2:
  coarser (`Decimal("10")`, `Decimal("1E+2")`, `Decimal("0")`), finer and still a whole number of
  cents (`Decimal("10.000")`, which must be accepted), and negative zero (`Decimal("-0.00")`) —
  each split by 3, and `Decimal("10")` and `Decimal("-0.00")` also with `parts == 1` (one share
  printing `10.00`, resp. `0.00`): `[amount]` returned as it came satisfies the sum, the count
  and the order, and only the representation shows the shortcut. Anti-pattern ruled out:
  representation properties checked by comparison, which cannot tell them apart.
- **Seam 2: the one happy example standing for «always»** — 10.00 by 3 is one point of the
  domain; a wrong scaling of a coarse exponent keeps sign and exponent of the shares right and
  only the sum shows it. Test approach: the sum is asserted with plain `sum(shares) == amount`
  (exact for ordinary amounts under the default context) on amounts of exponent -2
  (`Decimal("10.00")`, `Decimal("0.05")`, `Decimal("100.00")` by 7, `Decimal("0.01")`), of another
  exponent (`Decimal("10")`, `Decimal("1E+2")`, `Decimal("10.000")`), on zero and negative zero,
  on `parts == 1`, and on the largest ordinary amount of cents
  (`Decimal("99999999999999999999999999.99")`, 28 digits) with `parts == 2` — remainder one cent;
  the count, the spread and the order of I2 are asserted on this split as well. It is the input
  that tells the integer-cent path from the quantize idiom Q1 rejects as (a): there the quotient
  is rounded to 28 digits before `quantize`, and the sum comes out wrong only at this edge and
  only with a remainder (probed by the Phase-3 critic: by 2 it fails, by 3 and by 7 it does
  not). Anti-pattern ruled out: conservation proved on the single input the task happens to
  name, or at the edge of the domain only on a split with no remainder.
- **Seam 3: the remainder is more than one cent, or there are more parts than cents** — 10.00 by 3
  has a remainder of exactly one cent, so an implementation that gives the whole remainder to the
  first share passes it. Test approach: examples with remainder ≥ 2 (`Decimal("0.05")` by 3 →
  `0.02, 0.02, 0.01`; `Decimal("100.00")` by 7) and with `parts > cents` (`Decimal("0.01")` by 3
  → `0.01, 0.00, 0.00`), asserting `len(shares) == parts`, max − min ≤ one cent and
  non-increasing order. Anti-pattern ruled out: a remainder rule proved on the one remainder
  that cannot distinguish the implementations.
- **Seam 4: a refusal that surfaces as the wrong exception, or not at all** — `NaN` compared with
  `<` raises `InvalidOperation`; `Infinity` passes a sign check and fails later in conversion by
  accident. Test approach: `pytest.raises(ValueError)` separately for `NaN`, `sNaN`, `Infinity`,
  `-Infinity`, for `parts` 0 and −1, for a negative amount (`Decimal("-0.01")`), and for the
  non-cent amounts `Decimal("10.005")` and `Decimal("0.125")` (whose reduced ratio 1/8 has a
  denominator below 100 and slips past a check written as «denominator > 100») — each with
  `match=` on the offending value (escaped; for `parts == 0` the type carries the weight, a lone
  `0` matches almost any message). `InvalidOperation` is an `ArithmeticError`, not a
  `ValueError`, so `pytest.raises(ValueError)` does tell them apart. Of the four non-finite
  cases none may be dropped as redundant: `Infinity` is what proves finiteness is checked at
  all, `NaN`/`sNaN` are what pins the order of Q3. Anti-pattern ruled out: one «invalid input»
  test standing for every refusal.

First RED of the slice: the example test (in the file the testing manager's decision assigns, see «Exit criterion»), failing against the
skeleton on `NotImplementedError` (or, before the skeleton, on `ImportError: cannot import name 'split_evenly'`).

## Invariants (rules that hold for every input in the stated domain)
- **I1** — The sum of the shares equals `amount` exactly.
  - Domain: every ordinary amount («Covered inputs») that is `≥ 0` and a whole number of cents — of any exponent it may have, zero and negative zero included — with every `parts ≥ 1`, called under the default `decimal` context.
  - Source: the task, «Що зробити»: «щоб сума частин точно дорівнювала `amount`»; «Готово, коли»: «сума частин завжди дорівнює `amount`» (feature AC2); the domain — the owner's answer «а» (feature D-D).
  - Broken by: rounding each share independently (3.33 × 3 = 9.99); dropping the remainder; scaling a coarse exponent wrongly.
- **I2** — There are exactly `parts` shares, the largest and the smallest differ by at most one cent, and no share is larger than the one before it.
  - Domain: the same as I1.
  - Source: the task, «Що зробити»: «ділить суму на `parts` частин … частини відрізняються щонайбільше на один цент, більші йдуть першими» (feature AC3).
  - Broken by: giving the whole remainder to the first share; putting the extra cents on the last shares; returning `parts + 1` shares with a separate remainder.
- **I3** — Every share is non-negative and has exactly two decimal places.
  - Domain: the same as I1.
  - Source: the task, «Що зробити»: «із точністю до цента»; feature artifact, Build parameters D-B and D-C; this contract's «Seam», Returns.
  - Broken by: returning shares with the exponent of `amount` (`Decimal("3")`), `-0.00` for negative zero, `[amount]` as it came for `parts == 1`, or unquantized quotients (`3.333…`).

## Exit criterion
The slice is done when all of the following are observed in one run on the final code:
- the project's tests under `tests/` contain, and `pytest` passes, at least — in the file(s) the
  testing manager's decision assigns (the tester's sealed files, or `tests/test_pricing.py` only
  if the manager assigns the contract tests to the builder): the example test (10.00 by 3 →
  shares printing `3.34`, `3.33`, `3.33`), `test_I1_…`, `test_I2_…`, `test_I3_…`, and one test per
  refusal E1 (`parts` 0 and −1), E2 (`NaN`, `sNaN`, `Infinity`, `-Infinity`), E3 (`-0.01`),
  E4 (`10.005`, `0.125`), each refusal asserting `ValueError` with `match=` on the offending value
  (for `parts == 0` the type alone carries the weight), the other argument being lawful;
- each `test_I<n>_…` runs on at least the inputs «Hardest seams» names: I1 — the sum on `10.00`, `0.05`,
  `100.00` by 7, `0.01`, `10`, `1E+2`, `10.000`, `0`, `-0.00`, `10` with `parts == 1`, and
  `99999999999999999999999999.99` by 2; I2 — remainder ≥ 2 (`0.05` by 3, `100.00` by 7),
  `parts > cents` (`0.01` by 3) and `99999999999999999999999999.99` by 2; I3 — `10`, `1E+2`, `0`, `10.000` and `-0.00` by 3, and `10` and
  `-0.00` with `parts == 1`; an amount with no `parts` named is split by 3;
- the shares differ by at most one cent, observed by `test_I2_…` — the number is the owner's, from the task's «Що зробити» (threshold owner-ratified);
- `.venv/bin/ruff check .`, `.venv/bin/mypy` and the full `.venv/bin/python -m pytest` are green on the project (the four pre-existing pricing tests and the inventory tests included);
- the smoke `PYTHONPATH=src .venv/bin/python scripts/smoke_test_split_evenly_fn.py`, run against
  the real module, prints the shares of 10.00 by 3 and exits 0; it exits non-zero unless their
  printed form is `3.34`, `3.33`, `3.33` (compared as strings — equality cannot tell `3.34` from
  `3.340`). No external system is involved, so the smoke is asserted programmatically and is not
  parked. It is linted by ruff; the project's mypy scope (`src`, `tests`) does not include it.

## Deferred to later slices
- A caller of `split_evenly` — why later: the task builds the function only — revisit trigger: a
  task that names the caller. Cost it inherits: the caller must keep its amounts inside
  «Covered inputs»; beyond them nothing is promised.
- A `unit` parameter for currencies with another smallest unit (also listed under «Out of scope»:
  there as the boundary of this slice, here as the debt) — why later: nobody asked — revisit
  trigger: the first task that names a non-cent currency. Cost: `CENT` and the exponent `-2` are
  fixed in the function and in I3, so the parameter rewrites I3 and its test; a keyword with a
  default keeps the signature compatible.
- A defined behaviour beyond «Covered inputs» (exact split or a refusal) — why later: the owner
  chose silence (answer «а») — revisit trigger: a task that names amounts above 28 digits or a
  caller with a non-default `decimal` context. Cost: until then such a call may return shares
  whose sum is not `amount`, with no exception (probed: a 33-digit amount by 3) — the caller's
  obligation named in the first item is the only guard.
- Not a slice debt, a project-level option for the owner (named in the task's report): property-based
  testing of I1–I3. No such library is installed and adding a package is ask-gated. Revisit
  trigger: the owner adds a library to the dev dependencies.

## Open items requiring human decision (if any)
- None. The design fork of the first planning attempt (D-D) was put to the owner in the task
  file and answered «а»; this contract is written to that answer.

## Critic notes (non-blocking)
- The wording of error messages is observable (Hyrum) — the contract fixes only the type and that the value appears.
- The 10.00-by-3 example cannot tell the right implementation from «whole remainder to the first share»; the discrimination rests on the inputs of `test_I1`/`test_I2`.
- `scripts/` does not exist yet; `ruff check .` covers it once the file exists (only `.claude` is excluded).

## Revisions during planning
- **First attempt (before the owner's answer), phases 2–4:** four critic rounds on phases 3 and 4
  each found one more wrong implementation in the region the old D-D opened (amounts beyond the
  default context's precision, narrow contexts, the 4300-digit integer-to-string limit). The
  findings that lie inside «Covered inputs» are kept as test inputs above (`-0.00`, `10.000`,
  coarse exponents with the sum asserted, `parts == 1`, `0.125`); those outside it left the
  contract together with the promise, by the owner's answer «а». The full list is in git history
  of this file (commit e3bb0c1).
- **Phase 3 — challenge:** "`Decimal("99999999999999999999999999.99")` by 3 has remainder 0, so the rejected quantize implementation (Q1 alternative a) passes every named input yet breaks I1 inside «Covered inputs» (same amount by 2: sum ≠ amount)" → **revised:** the 28-digit amount is split by 2 and carries I1 and I2; the first bullet of «Hardest seams» no longer claims every input leaves a remainder → **reason:** the only input at the edge of the domain exercised no remainder path.
- **Phase 4 — challenge:** "pins the done-evidence to an existing file, while … the tester writes contract tests «in new test files of their own (never the builder's files)»" → **revised:** the exit criterion, Q5 and the «First RED» line name the tests by name under `tests/`, in the file(s) the testing manager's decision assigns → **reason:** as written the criterion was unobservable or forced the builder to duplicate sealed tests.
