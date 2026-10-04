# Slice reorder-flag — planning artifact

## Goal
The buyer sees which items have run low without reading the whole stock list: one function that
says whether an item should be ordered again. Target: the function is used by the nightly stock
report; no item that should be reordered is left out of it.

## Premise verified
- `StockItem.on_hand` is the only stock figure the project keeps — `src/refproj/inventory.py`, read 2026-10-04.

## Out of scope (deliberately)
- How much to order — a later slice, needs supplier lead times.
- Reservations not yet taken off the shelf — `on_hand` is already net of them.

## Seam (contract)
- Signature: `needs_reorder(item: StockItem, reorder_point: int) -> bool` in `refproj.inventory`.
- Returns: `True` when `item.on_hand` has reached `reorder_point` or dropped under it, `False`
  while there is more on the shelf than that. A reorder point of 0 means "order when the shelf
  is empty".
- Errors: a negative `reorder_point` raises `ValueError` whose message contains `reorder point`.
- Dependencies (injected): none; a pure function.
- Does NOT do: no quantity to order, no change to the item.

## Decisions (with WHY)
- Q1: the reorder point is an argument, not a field of `StockItem` — chosen because the point
  differs per season and the item record should not change with it. Rejected: a field on the
  item, because every caller of `StockItem(...)` would have to supply it.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: the item is not changed** — test approach: compare the item before and after the
  call; rules out a helper that "reserves" stock as a side effect.

## Exit criterion
`tests/test_reorder_flag_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Order quantity — why later: needs lead times — revisit trigger: the supplier slice.
