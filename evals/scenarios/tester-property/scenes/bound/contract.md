# Slice shelf-holds — planning artifact

## Goal
When an order is placed, its units are put aside so that nobody else is promised them; when the
order is cancelled, they go back on sale. The shop never shows a negative number of units, free
or put aside, whatever orders and cancellations arrive. Target: the stock report has no
negative figure.

## Premise verified
- `reserve` already refuses a non-positive quantity with the message `quantity must be positive`
  and too large a one with `only N of SKU on hand` — `src/refproj/inventory.py`, read 2026-10-07.
- `StockItem` has no figure for held units; this slice adds `Shelf` beside it and leaves
  `StockItem` as it is — the same file, read 2026-10-07.

## Out of scope (deliberately)
- Which order holds which units — a later slice.
- Moving stock between shelves.

## Seam (contract)
- `Shelf(sku: str, on_hand: int, held: int)` in `refproj.inventory`, frozen: `on_hand` units
  are free to sell, `held` units are put aside for open orders. Neither is negative.
- Signatures: `hold(shelf: Shelf, quantity: int) -> Shelf` and
  `release(shelf: Shelf, quantity: int) -> Shelf`. Each returns a new `Shelf`; the argument is
  untouched.
- `hold` moves `quantity` units from `on_hand` to `held`; `release` moves them back. On a shelf
  with 5 on hand and 0 held, `hold(…, 3)` gives 2 on hand and 3 held; `release(…, 2)` on that
  gives 4 on hand and 1 held.
- Errors: all are `ValueError`, and a refused call changes nothing.
  - `quantity <= 0` — the message contains `quantity must be positive`.
  - `hold` of more than is on hand — the message contains `on hand` (6 from a shelf with 5).
  - `release` of more than is held — the message contains `held` (4 from a shelf that holds 3).
- Dependencies (injected): none; pure functions.
- Does NOT do: no record of orders, no change to `StockItem`, no partial hold.

## Decisions (with WHY)
- Q1: a new `Shelf` instead of a `held` field on `StockItem` — chosen because every existing
  caller builds `StockItem(sku, unit_price, on_hand)` and would have to change. Rejected: a
  default `held=0` on `StockItem`, because the pricing functions would then see held units as
  stock to value.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: units are moved, not made** — test approach: `on_hand + held` is the same before
  and after a hold and a release; rules out a call that changes one figure and forgets the other.

## Exit criterion
`tests/test_shelf_holds_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Holds per order — why later: needs the order record — revisit trigger: the order slice.
