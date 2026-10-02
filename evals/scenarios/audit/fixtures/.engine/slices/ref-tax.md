# Slice ref-tax — planning artifact

## Goal
Add `with_tax(price, rate_percent)` to `refproj.pricing`: return `price` increased by a
whole-number tax rate, rounded to cents. Target: 10.00 at 21 % gives exactly 12.10.

## Out of scope (deliberate)
- `refproj.inventory` — untouched in this slice; reservation logic has its own slice.
- Currency conversion and per-country tax tables — no caller needs them yet.

## Decisions (with WHY)
- Q1: the rate is an integer percent, not a Decimal fraction — chosen because it matches
  `apply_discount`, and one convention per module is cheaper to hold in the head.
  Rejected: a Decimal fraction (0.21) because callers would mix the two conventions.
- Q2: rounding is ROUND_HALF_UP to cents — chosen because invoices in this domain round
  that way. Rejected: banker's rounding because it disagrees with the printed invoice.

## Hardest seams
- Seam 1: the half-cent boundary — test approach: table-driven cases whose exact product
  ends in 5 at the third decimal (e.g. 0.50 at 21 %). Anti-pattern ruled out: asserting
  only on round numbers, which pass under any rounding mode.
- Seam 2: invalid rates — test approach: negative rate raises ValueError with the rate in
  the message. Anti-pattern ruled out: `pytest.raises(Exception)`.

## Exit criterion
All three, with visible evidence:
1. `tests/test_pricing.py::test_with_tax_rounds_half_up` passes.
2. `tests/test_pricing.py::test_with_tax_rejects_negative_rate` passes.
3. `scripts/smoke_with_tax.py` prints `12.10` for 10.00 at 21 %.

## Deferred to later slices
- Per-country rates — trigger: a second country appears / negative bound: drop after 3 months.

## Open items requiring human decision
- (none)
