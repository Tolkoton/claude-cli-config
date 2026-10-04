# Slice average-price — planning artifact

## Goal
The weekly report shows the average price of what was sold. One function computes it; the
report must never show an average that was not computed from at least one sale.

## Premise verified
- `refproj.pricing.total` treats an empty basket as costing nothing and returns `0.00` — read
  2026-10-04. That is right for a sum and is why this slice says what it does about an average.

## Out of scope (deliberately)
- Weighted averages (by quantity) — the report lists one price per sale.
- The report itself.

## Seam (contract)
- Signature: `average(prices: Iterable[Decimal]) -> Decimal` in `refproj.pricing`.
- Returns: the arithmetic mean of `prices`, rounded half up to cents like the rest of the module.
  Any iterable is accepted, a generator included.
- Errors: `prices` with nothing in it has no average — `ValueError` whose message contains
  `no prices`. The caller decides what the report shows then.
- Dependencies (injected): none; a pure function.
- Does NOT do: no weighting, no filtering of zero prices.

## Decisions (with WHY)
- Q1: one pass over the iterable into a list — chosen because a generator can be read once and
  both the sum and the count are needed. Rejected: `itertools.tee`, because it buys nothing here.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: a generator, not only a list** — test approach: pass a generator expression; rules
  out an implementation that iterates twice and silently averages nothing the second time.

## Exit criterion
`tests/test_average_price_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Weighted average — why later: no quantity in the report's rows yet — revisit trigger: the report slice.
