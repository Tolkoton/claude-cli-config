# Slice split-bill — planning artifact

## Goal
A table pays one bill together. The waiter splits it between the guests in one call, and the
restaurant receives exactly the bill: not a cent more, not a cent less. Target: the day's
takings from split bills equal the sum of those bills.

## Premise verified
- Prices are `Decimal` in whole cents (`CENT`) — `src/refproj/pricing.py`, read 2026-10-07.

## Out of scope (deliberately)
- Unequal shares (who ate what) — a later slice.
- Tips.

## Seam (contract)
- Signature: `split_bill(amount: Decimal, people: int) -> list[Decimal]` in `refproj.pricing`.
- `amount` is the bill: 0.00 to 999,999.99 (`MAX_BILL`) in whole cents. `people` is the number
  of guests: 1 to 100 (`MAX_PEOPLE`).
- Returns: one share per guest, each in whole cents. The shares add up to `amount` exactly. No
  two shares differ by more than one cent, and the larger shares come first.
  `Decimal("100.00")` between 4 gives four times `25.00`; between 3 it gives
  `[33.34, 33.33, 33.33]`; `Decimal("77.00")` for 1 gives `[77.00]`; `Decimal("0.00")` between 2
  gives `[0.00, 0.00]`.
- Errors: `ValueError` — the message contains `people` when `people` is outside 1..100, and
  `amount` when the amount is outside the range or has a fraction of a cent.
- Dependencies (injected): none; a pure function.
- Does NOT do: no tip, no unequal shares, no rounding of the bill itself.

## Decisions (with WHY)
- Q1: the cents that do not divide go to the first guests, one each — chosen because it is
  predictable and nobody pays two cents more than a neighbour. Rejected: give the whole remainder to
  the last guest, because with many guests one of them would visibly pay more.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: the shares are cents, not fractions** — test approach: compare each share with its
  own value quantized to `0.01`; rules out a share like `33.3333`.

## Exit criterion
`tests/test_split_bill_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Unequal shares — why later: needs the order lines per guest — revisit trigger: the order slice.
