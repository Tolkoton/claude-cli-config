# Slice shelf-value — planning artifact

## Goal
The accountant asks what the stock of one article is worth. One function answers for one item,
so that the report does not repeat the arithmetic. Target: the stock report shows a value per
article.

## Premise verified
- `reserved_value(item, quantity)` already gives the value of `quantity` units at the item's
  unit price, rounded to cents, and `0.00` for no units — `src/refproj/inventory.py` and
  `src/refproj/pricing.py`, read 2026-10-07.

## Out of scope (deliberately)
- The value of the whole warehouse — the report sums the items itself.
- Purchase price and margin.

## Seam (contract)
- Signature: `shelf_value(item: StockItem) -> Decimal` in `refproj.inventory`.
- Returns: the value of everything of `item` that is on the shelf — what
  `reserved_value(item, item.on_hand)` gives. An item with 4 on hand at `2.50` is worth `10.00`;
  an item with nothing on hand is worth `0.00`.
- Errors: none of its own.
- Dependencies (injected): none; it calls `reserved_value`.
- Does NOT do: no change to the item, no arithmetic of its own.

## Decisions (with WHY)
- Q1: a function of its own instead of asking every caller to write
  `reserved_value(item, item.on_hand)` — chosen because the report and the export both need it.
  Rejected: a property on `StockItem`, because the item record should not depend on pricing.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: the item is not changed** — test approach: compare the item before and after the call.

## Exit criterion
`tests/test_shelf_value_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Warehouse total — why later: needs the list of all items — revisit trigger: the report slice.
