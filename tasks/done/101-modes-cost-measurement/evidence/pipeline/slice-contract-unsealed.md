# Slice split-evenly-fn — planning artifact

Driven by the feature `.engine/architecture/feature/split-evenly.md` (slice S1, the tracer bullet
and the only slice). The frame below is supplied by that artifact and by the owner's task
`tasks/doing/010-split-evenly.md`; nobody was asked.

## Goal
`refproj.pricing` gets the pure function `split_evenly(amount: Decimal, parts: int) -> list[Decimal]`:
it divides a money amount into `parts` shares to the cent so that the shares add up to exactly
`amount`, differ by at most one cent, and the larger shares come first. Measurable signal:
`split_evenly(Decimal("10.00"), 3)` returns shares that print as `3.34`, `3.33`, `3.33`; the
tests named under «Exit criterion» are green; `ruff check`, `mypy` and `pytest` are green on the project.

## Premise verified
- PR-split-01 (`.engine/premises/premise-log.md`) — a finite `Decimal` with no fraction of a cent
  converts to an exact integer number of cents through `Decimal.as_integer_ratio()`, integer
  `divmod` splits it with no rounding, and integer cents convert back to an exact two-decimal
  `Decimal` through `Decimal((0, Decimal(cents).as_tuple().digits, -2))`, in any `decimal`
  context of the caller and with no limit set by the context's precision — evidence: runtime
  checks with the project's interpreter recorded in the feature artifact («Premises verified»),
  repeated independently by the feature critic's two rounds (33-digit amount; `prec=3` context)
  and by the Phase-2 critic of this contract (5002-digit shares exact, also under `prec=3`) — 2026-10-11.
  What is NOT claimed: amounts the interpreter cannot hold as an integer in memory or in
  reasonable time (`Decimal("1E+999999999999999999")`), see «Seam».
- No external system: no network, no file system, no third-party library; only the standard
  library's `decimal` (Python ≥ 3.12, `pyproject.toml`).

## Out of scope (deliberately)
- Currencies whose smallest unit is not 0.01 — no `unit` parameter; nobody asked.
- Weighted or proportional splits, or any rule for who gets the extra cents other than «the first shares».
- Negative amounts (splitting a refund) — the task says `ValueError`.
- Any caller: `refproj.inventory` and the existing functions of `refproj.pricing` are not changed.
- A runtime check of the type of `parts` or `amount` — the annotations under `mypy --strict` are the contract.

## Seam (contract)
- Signature: `def split_evenly(amount: Decimal, parts: int) -> list[Decimal]` in `src/refproj/pricing.py`.
- Returns: a new list of exactly `parts` shares. Every share is a non-negative `Decimal` with
  exactly two decimal places (exponent `-2`, positive sign — `Decimal("0.00")`, never `-0.00`),
  whatever the exponent of `amount` (`Decimal("10")`, `Decimal("1E+2")` and `Decimal("10.00")` are
  all lawful). With `cents` = the amount in cents, `base, extra = divmod(cents, parts)`: the first
  `extra` shares are `base + 1` cents, the remaining `parts - extra` shares are `base` cents.
- Errors: raises `ValueError`, with a message that names the offending value (as `apply_discount`
  does), when
  - E1. `parts < 1`;
  - E2. `amount` is not finite (`NaN`, `sNaN`, `Infinity`, `-Infinity`);
  - E3. `amount < 0`;
  - E4. `amount` is not a whole number of cents (`Decimal("10.005")`).
  A refusal never surfaces as another exception type — in particular not as
  `decimal.InvalidOperation` or `OverflowError`. When several refusals apply at once, which one's
  message is shown is not part of the contract, and neither is the wording of a message: the
  contract is the type `ValueError` and that the offending value appears in the text.
  A lawful amount is never refused: `Decimal("10.000")` is a whole number of cents and is split
  like `Decimal("10.00")`.
- Lawful edge inputs: `amount == 0` (and `Decimal("-0.00")`, which is not less than zero) →
  `parts` shares of `Decimal("0.00")`; `parts == 1` → one share numerically equal to `amount`;
  more parts than cents (`Decimal("0.01")` by 3) → `0.01, 0.00, 0.00`; an amount with more
  digits than the caller's `decimal` context holds (beyond the default 28 too) → exact shares.
- Outside the contract — resource exhaustion: the function converts `amount` to an integer
  number of cents and builds a list of `parts` shares, so an amount with an astronomically large
  exponent of either sign (`Decimal("1E+999999999999999999")`; `Decimal("1E-100000000")`, whose
  integer ratio has a denominator of a hundred million digits) or an astronomically large `parts`
  costs memory and time in proportion and may end in `MemoryError` or not end in reasonable
  time. For such inputs neither exact shares nor the refusal E4 is guaranteed. No size cap is
  introduced (a cap would be a threshold and a new refusal — the owner's to set).
- Dependencies (injected): none — a pure function; it reads no clock, no randomness, no global
  state, and its result does not depend on the caller's `decimal` context.
- Does NOT do: round a non-cent amount; accept a negative amount; take a currency unit; check
  argument types at runtime; mutate or cache anything.

## Decisions (with WHY)
- Q1: integer-cent arithmetic — `as_integer_ratio()` in, integer `divmod`, and
  `Decimal((0, Decimal(cents).as_tuple().digits, -2))` out — chosen because every step is exact
  by construction and independent of the caller's context (`Decimal(int)` and the tuple
  constructor do not round), so «the sum always equals `amount`» holds without a limit set by
  precision. Its cost grows with the magnitude of the exponent of `amount`, of either sign
  (probed: `Decimal("1E-10000000")` needs 7.5 s to reach its refusal) — accepted, see «Seam»,
  outside the contract; a pre-check on `amount.as_tuple()` that would refuse such an amount
  cheaply was not taken: more code for inputs no money amount has. The module constant `CENT` is deliberately not used in this function: using it means
  `quantize` or `*`, which are context arithmetic. Rejected:
  (a) `(amount / parts).quantize(CENT, ROUND_DOWN)` plus handing out the leftover cents — the
  idiom the module's other functions use and the shortest to read, but `/`, `*` and `quantize`
  round or raise `InvalidOperation` once the amount exceeds the context's precision (probed: a
  31-digit amount raises `InvalidOperation`);
  (b) the same idiom inside `decimal.localcontext()` with `prec` widened to the amount's digit
  count — exact, and reads like `apply_discount`, but the precision must be computed per call and
  the result still depends on the traps and `Emax` of the copied context;
  (c) `int(amount * 100)` — rounds on the way in, and truncates a half-cent silently (`10.005` → 1000);
  (d) building the digit tuple from `str(cents)` — the most natural way to write «tuple
  constructor out», but CPython refuses integer-to-string conversion above 4300 digits with a
  `ValueError` (probed: a 4301-digit amount), which would refuse a lawful amount while every
  `pytest.raises(ValueError)` test stayed green.
- Q2: an amount that is not a whole number of cents → `ValueError` (E4) — chosen because for such
  an amount «shares to the cent» and «sum equals `amount`» cannot both hold; an amount that is
  not finite → `ValueError` (E2) — because `NaN` and `Infinity` have no number of cents at all.
  Rejected: round the amount to cents first — friendlier to a caller holding `10.005`, but the
  returned shares would no longer add up to what was passed, the one thing the owner asked to be
  exact. Logged AUTONOMOUS (two-way door) in `.engine/overseer/escalations.md`.
- Q3: finiteness is checked before the sign — chosen because `Decimal("NaN") < 0` raises
  `decimal.InvalidOperation`, which is not a `ValueError`. Rejected: rely on the sign comparison
  alone — one check fewer, but leaks an exception type the task does not name.
- Q4: no runtime type check of `parts` (`True`, `2.5`) — chosen because the project is `mypy --strict`
  and its other functions (`apply_discount(percent: int)`, `reserve(quantity: int)`) check values,
  not types. Rejected: `isinstance(parts, int)` guard — would give a clean refusal to an untyped
  caller, but adds a refusal nobody asked for and a convention the module does not have.
- Q5: the function lives in `src/refproj/pricing.py`, its tests in `tests/test_pricing.py` — chosen
  because the task names `refproj.pricing` and the project keeps one test file per module.
  Rejected: a new module `refproj/splitting.py` — would isolate the new code, but contradicts the
  owner's «у `refproj.pricing`».
- Q6: every share has exactly two decimal places, also when `amount` has none or more exponent
  (`Decimal("10")`) — chosen because the result is money to the cent and a caller printing it sees
  `3.34`, `0.00`. Rejected: keep the exponent of `amount` — «closest to the input», but `Decimal("10")`
  by 3 has no representation with exponent 0.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: `Decimal` equality ignores the exponent** — `Decimal("3.34") == Decimal("3.340")` and
  `Decimal("0") == Decimal("0.00")`, so a list `==` assertion passes for shares with the wrong
  number of decimal places; `Decimal("-0.00") >= 0` and `Decimal("-0.00") == Decimal("0.00")`,
  so a comparison passes for a share with the wrong sign. Test approach: the rules of I3 are
  asserted on the representation — `share.as_tuple().exponent == -2` and `share.as_tuple().sign == 0`
  (and the printed form for the 10.00-by-3 example) — on amounts whose own exponent is not -2:
  coarser (`Decimal("10")`, `Decimal("1E+2")`, `Decimal("0")`), finer and still a whole number of
  cents (`Decimal("10.000")`, which must be accepted, as `Decimal("10.005")` must be refused), and
  negative zero (`Decimal("-0.00")`) — each split by 3, and `Decimal("10")` and `Decimal("-0.00")`
  also with `parts == 1` (one share printing `10.00`, resp. `0.00`): `[amount]` returned as it
  came satisfies the sum, the count and the order, and only the representation shows the
  shortcut. Anti-pattern ruled out: representation properties (sign,
  exponent) checked by comparison, which cannot tell them apart.
- In every seam below and above, an amount with no `parts` named is split by 3 — never by a
  divisor that leaves no remainder, which would make the remainder path vacuous for that input.
- **Seam 2: the sum is checked with arithmetic that itself rounds** — `sum()` of shares runs in
  the caller's context; for an amount beyond 28 digits it rounds, and a test could pass or fail
  for the wrong reason. Test approach: the conservation rule is asserted on several amounts
  including one of more than 28 significant digits (`Decimal("1" + "0" * 30 + ".01")`), summing
  inside `decimal.localcontext()` with a precision wide enough to hold the amount; and once with
  the function *called* under a narrow context (`prec=3`) on an amount with more significant
  digits than that precision (`Decimal("12345.67")` by 3 → `4115.23, 4115.22, 4115.22`), the sum
  being taken outside the narrow context — on `10.00` such a test would be vacuous. The sum is
  asserted on amounts whose exponent is not -2 as well, since «any exponent» is in I1's domain
  and a wrong scaling of a coarse exponent keeps sign and exponent of the shares right:
  `Decimal("10")`, `Decimal("1E+2")`, `Decimal("10.000")`; one coarse-exponent amount beyond 28
  digits (`Decimal("1E+30")`, summed under a wide `localcontext`); one coarse-exponent amount
  called under the narrow context (`Decimal("10")` under `prec=3`). And once on an amount of
  more than 4300 digits (`Decimal("1" + "0" * 4400 + ".01")`, summed under a `localcontext` wide
  enough): 4300 is CPython's limit for integer-to-string conversion, the trap of Q1 (d) — an
  interpreter fact, not a product number. Anti-pattern ruled out: the single happy example (10.00 by 3) standing for «always».
- **Seam 3: the remainder is more than one cent, or there are more parts than cents** — 10.00 by 3
  has a remainder of exactly one cent, so an implementation that gives the whole remainder to the
  first share passes it. Test approach: examples with remainder ≥ 2 (`Decimal("0.05")` by 3 →
  `0.02, 0.02, 0.01`; `Decimal("100.00")` by 7) and with `parts > cents` (`Decimal("0.01")` by 3),
  asserting `len(shares) == parts`, max − min ≤ one cent and non-increasing order. Anti-pattern ruled out: a remainder
  rule proved on the one remainder that cannot distinguish the implementations.
- **Seam 4: a refusal that surfaces as the wrong exception** — `NaN` compared with `<` raises
  `InvalidOperation`; `Infinity` passes a sign check and fails later in conversion with
  `OverflowError`/`ValueError` by accident. Test approach: `pytest.raises(ValueError)` separately
  for `NaN`, `sNaN`, `Infinity`, `-Infinity`, plus the two refusals the task names (`parts` 0 and
  −1; a negative amount) and the non-cent amounts — `Decimal("10.005")` and `Decimal("0.125")`,
  whose reduced ratio 1/8 has a denominator below 100 and slips past a check written as
  «denominator > 100» — each with `match=` on the offending value (escaped; for `parts == 0`
  the type carries the weight, a lone `0` matches almost any message). The refusal E4 is also
  held to inputs where context arithmetic rounds the fraction away — `Decimal("10.005")` and
  `Decimal("12345.675")` by 3 called under `prec=3`, and `Decimal("1" + "0" * 30 + ".005")` by 3
  under the default context — each `pytest.raises(ValueError)`: a cent check written as
  `amount * 100 == (amount * 100).to_integral_value()` refuses the short amounts and silently
  accepts these. Anti-pattern ruled out: a refusal proved only where the rounding check and the
  exact check agree.
  `InvalidOperation` is an `ArithmeticError`, not a `ValueError`, so `pytest.raises(ValueError)`
  does tell them apart. Of the four non-finite cases only `Infinity` proves that finiteness is
  checked at all (`NaN` and `sNaN` reach a `ValueError` by accident inside `as_integer_ratio()`,
  `-Infinity` through the sign check), and `NaN`/`sNaN` are what pins the order of Q3 when the
  sign is compared first — none of the four may be dropped as redundant. Anti-pattern ruled out:
  one «invalid input» test standing for every refusal.

First RED of the slice: the example test in `tests/test_pricing.py`, failing against the
skeleton on `NotImplementedError` (or, before the skeleton, on `ImportError: cannot import name 'split_evenly'`).

## Invariants (rules that hold for every input in the stated domain)
- **I1** — The sum of the shares equals `amount` exactly.
  - Domain: every finite `amount ≥ 0` that is a whole number of cents — of any exponent (coarser
    or finer than -2) and with any number of digits the interpreter can hold as an integer (see
    «Seam», outside the contract), zero and negative zero included — with every `parts ≥ 1`, under any `decimal` context of the caller.
  - Source: the task, «Що зробити»: «щоб сума частин точно дорівнювала `amount`»; «Готово, коли»: «сума частин завжди дорівнює `amount`» (feature AC2, D-D).
  - Broken by: rounding each share independently (3.33 × 3 = 9.99); context arithmetic that rounds a long amount; dropping the remainder.
- **I2** — There are exactly `parts` shares, the largest and the smallest differ by at most one cent, and no share is larger than the one before it.
  - Domain: the same as I1.
  - Source: the task, «Що зробити»: «ділить суму на `parts` частин … частини відрізняються щонайбільше на один цент, більші йдуть першими» (feature AC3).
  - Broken by: giving the whole remainder to the first share; putting the extra cents on the last shares; returning `parts + 1` shares with a separate remainder.
- **I3** — Every share is non-negative and has exactly two decimal places.
  - Domain: the same as I1.
  - Source: the task, «Що зробити»: «із точністю до цента»; feature artifact, Build parameters D-B and D-C; this contract's «Seam», Returns.
  - Broken by: returning shares with the exponent of `amount` (`Decimal("3")`), `-0.00` for negative zero, or unquantized quotients (`3.333…`).

## Exit criterion
The slice is done when all of the following are observed in one run on the final code:
- `tests/test_pricing.py` contains, and `pytest` passes, at least: the example test (10.00 by 3 →
  shares printing `3.34`, `3.33`, `3.33`), `test_I1_…`, `test_I2_…`, `test_I3_…`, and one test per
  refusal E1 (`parts` 0 and −1), E2 (`NaN`, `sNaN`, `Infinity`, `-Infinity`), E3 (negative amount),
  E4 (`10.005`, `0.125`; `10.005` and `12345.675` called under `prec=3`; `1…0.005` with 30 zeros
  under the default context), each refusal asserting `ValueError` with `match=` on the offending value;
- each `test_I<n>_…` runs on the inputs «Hardest seams» names: I1 — the sum asserted on amounts
  of exponent -2 and not -2 (`10`, `1E+2`, `10.000`), on amounts of more than 28 digits
  (`1…0.01` with 30 zeros; `1E+30`), on an amount of more than 4300 digits, and on calls under
  `prec=3` (`12345.67`; `10`); I2 — remainder ≥ 2 and `parts > cents`;
  I3 — amounts whose exponent is not -2 (`10`, `1E+2`, `0`, `10.000`) and `-0.00`, by 3, and
  `10` and `-0.00` with `parts == 1`; an amount with no `parts` named is split by 3;
- the shares differ by at most one cent, observed by `test_I2_…` — the number is the owner's, from the task's «Що зробити» (threshold owner-ratified);
- `.venv/bin/ruff check .`, `.venv/bin/mypy` and the full `.venv/bin/python -m pytest` are green on the project (the four pre-existing pricing tests and three inventory tests included);
- the smoke `PYTHONPATH=src .venv/bin/python scripts/smoke_test_split_evenly_fn.py`, run against
  the real module, prints the shares of 10.00 by 3 and exits 0; it exits non-zero unless their
  printed form is `3.34`, `3.33`, `3.33` (compared as strings — equality cannot tell `3.34` from
  `3.340`). No external system is involved, so the smoke is asserted programmatically and is not
  parked. It is linted by ruff; the project's mypy scope (`src`, `tests`) does not include it.

## Deferred to later slices
- A caller of `split_evenly` — why later: the task builds the function only — revisit trigger: a
  task that names the caller. Cost it inherits: shares of an amount with more digits than the
  caller's `decimal` context must be added up under a context wide enough for the amount, and not
  through the module's `total()`, whose `quantize` raises `InvalidOperation` on them.
- A `unit` parameter for currencies with another smallest unit (also listed under «Out of scope»:
  there as the boundary of this slice, here as the debt) — why later: nobody asked — revisit
  trigger: the first task that names a non-cent currency. Cost: the exponent `-2` is fixed in
  the output constructor and in I3, so the parameter rewrites I3 and its test; a keyword with a
  default keeps the signature compatible.
- Not a slice debt, a project-level option for the owner (named in the task's report): property-based
  testing of I1–I3. No such library is installed and adding a package is ask-gated; slices never
  add exhaustive property tests. Revisit trigger: the owner adds a library to the dev dependencies.

## Open items requiring human decision (if any)
- **PARKED — the planning loop did not converge; this contract is NOT sealed.** Phases 3 and 4
  each received `CRITIC_REVISE` four times (Phase 2 passed in round 3, Phase 5 in round 1), which
  is the circuit breaker of `/plan-slice`. It was not an oscillation between two positions: every
  round a fresh critic built one more wrong implementation that passed all the named test inputs,
  always in the same region — amounts or contexts beyond what the `decimal` context holds exactly
  (round 1: `-0.00`, `10.000`; round 2: non-cent exponents, the 4300-digit limit; round 3:
  `parts == 1`; round 4: the refusal E4 under a narrow context and beyond 28 digits). The fix for
  round 4 is written into «Hardest seams» (Seam 4) and «Exit criterion» above but no critic has
  judged it, and the cold-reader audit has not run.
  - Position 1 (this draft, feature decision D-D): the split is exact for an amount of any size
    under any caller context; the contract and the tests reach into that region. The feature
    critic BLOCKED a plan that left it undefined (a silently wrong sum against the owner's «завжди»).
  - Position 2 (the simplifier, both lenses, `.engine/simplifier/report.md` F-40d97f9b, F-2ed4bd33):
    D-D is a requirement nobody asked for; say nothing about amounts beyond the default
    28-digit context, as `total` and `apply_discount` do, and the contract and tests shrink to
    ordinary money amounts.
  - Question for the owner: in the task file, `tasks/blocked/010-split-evenly.md`. Recommended:
    position 2 for the promise and the tests, keeping the integer-cent implementation (it costs
    the same few lines and is exact anyway) — because four rounds of real findings in a region
    no money amount of this project reaches is the cost of D-D made visible.

## Critic notes (non-blocking)
- Phase 2: the wording of error messages is observable (Hyrum) — the contract fixes only the type and that the value appears.
- Phase 3: the 10.00-by-3 example cannot tell the right implementation from «whole remainder to the first share» or from the quantize idiom; the discrimination rests on the inputs of `test_I1`/`test_I2`.
- Phase 4: `scripts/` does not exist yet; `ruff check .` covers it once the file exists (only `.claude` is excluded).
- Phase 5: PASS on the first round.

## Revisions during planning
- **Phase 2 — challenge:** "with `str(cents)` as the digit source a lawful 4301-digit amount raises `ValueError` … and `Decimal("1E+999999999999999999")` … hangs in `as_integer_ratio()`" → **revised:** Q1 names the digit path `Decimal(cents).as_tuple().digits` and rejects `str(cents)`; the Seam carves resource exhaustion out of the contract with no numeric cap; the premise no longer says «at any size» → **reason:** the universal claims were false as written.
- **Phase 3 — challenge:** "a probed wrong implementation (shares carry the sign of `amount`; refusal on `exponent < -2`) passes every check the draft names" → **revised:** Seam 1 asserts the sign on the representation for `Decimal("-0.00")` and adds the lawful `Decimal("10.000")` → **reason:** two members of the declared domain had no test input.
- **Phase 4 — challenge:** "`python: command not found`, rc=127" → **revised:** every command of the exit criterion names `.venv/bin/…` → **reason:** the criterion's command could not be run as written.
- **Phase 2, round 2 — challenge:** "a non-cent amount with a large negative exponent … `Decimal("1E-100000000")` does not return within 30 s" → **revised:** the resource-exhaustion carve-out covers exponents of either sign and says E4 is not guaranteed there → **reason:** the carve-out covered one direction only.
- **Phase 3, round 2 — challenge:** "the sum is asserted only on exponent -2 amounts … two probed wrong implementations pass all 23 named checks" → **revised:** Seam 2 and the exit criterion name the sum assertion on `10`, `1E+2`, `10.000`, `1E+30`, and `10` under `prec=3` → **reason:** part of I1's domain had no input checking the sum.
- **Phase 4, round 2 — challenge:** "the `str(cents)` digit path rejected in Q1(d) passes every input the criterion names" → **revised:** I1 runs once on an amount of more than 4300 digits → **reason:** the criterion did not discriminate the wrong implementation the contract itself names.
- **Phases 3 and 4, round 3 — challenge:** "the probed wrong implementation `if parts == 1: return [amount]` passes every named check yet returns `[Decimal('10')]`, `[Decimal('10.000')]`, `[Decimal('-0.00')]`" → **revised:** Seam 1 and the I3 line of the exit criterion name `parts` (3 by default) and add `parts == 1` on `Decimal("10")` and `Decimal("-0.00")`; E4 gains the input `Decimal("0.125")` → **reason:** a lawful edge the Seam lists by name had no test input.
