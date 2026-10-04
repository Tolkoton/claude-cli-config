# Slice sales-tax — planning artifact

## Goal
Prices shown to the customer include sales tax, computed the way the invoice software of the
accountant computes it, so that the shop's totals and the accountant's totals agree to the cent.

## Premise verified
- The accountant's software rounds a tax-inclusive amount to cents with ties going to the even
  cent — its manual, section "Rounding", read 2026-10-04; three invoices recomputed by hand.
- The rest of `refproj.pricing` rounds half up (`apply_discount`, `total`) — read 2026-10-04.

## Out of scope (deliberately)
- Tax per region — one rate is passed in.
- Changing how `apply_discount` and `total` round — they stay as they are.

## Seam (contract)
- Signature: `add_tax(price: Decimal, rate_percent: Decimal) -> Decimal` in `refproj.pricing`.
- Returns: `price * (100 + rate_percent) / 100`, rounded to cents as the accountant's software
  does it (see Premise verified). A rate of 0 returns the price, in cents.
- Errors: a negative `rate_percent` raises `ValueError` whose message contains `tax rate`.
- Dependencies (injected): none; a pure function.
- Does NOT do: no discount, no summing of a basket.

## Decisions (with WHY)
- Q1: the rate is a `Decimal` percent (`Decimal("7.5")`), not a float — chosen because the
  module is exact decimals throughout. Rejected: a fraction (`0.075`), because the tax office
  publishes percents and a transcription slip of two places is silent.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: exact decimals in, exact decimals out** — test approach: compare with `Decimal`
  literals written by hand, never with a value computed by the same formula in the test.

## Exit criterion
`tests/test_sales_tax_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Regional rates — why later: one shop, one region today — revisit trigger: a second region.
