# Slice stock-transfer — planning artifact

## Goal
Stock moves between two shelves of the same article (shop floor and back room) in one call, and
a refused move tells the clerk the real reason, so that a clerk who picked the wrong article is
not sent to count the shelf.

## Premise verified
- `reserve` already refuses a non-positive quantity and a quantity above `on_hand`, with the
  messages `quantity must be positive` and `only N of SKU on hand` — `src/refproj/inventory.py`,
  read 2026-10-04.

## Out of scope (deliberately)
- Transfers between different articles (conversion) — refused here.
- A log of transfers.

## Seam (contract)
- Signature: `transfer(source: StockItem, target: StockItem, quantity: int) -> tuple[StockItem, StockItem]`
  in `refproj.inventory`.
- Returns: `(source, target)` as they are after the move: `quantity` units fewer on `source`,
  as many more on `target`; SKUs and unit prices unchanged; the arguments themselves untouched.
- Errors: all are `ValueError`; when several apply, the first in this list is the one reported.
  1. `source.sku != target.sku` — the message contains `different SKUs`.
  2. `quantity <= 0` — the message contains `quantity must be positive`.
  3. `quantity > source.on_hand` — the message contains `only`.
- Dependencies (injected): none; a pure function.
- Does NOT do: no partial move, no conversion between articles.

## Decisions (with WHY)
- Q1: return both items as a tuple — chosen because `StockItem` is frozen and the caller needs
  both new values. Rejected: mutate in place, because the dataclass is frozen on purpose.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: nothing is lost or made** — test approach: the sum of `on_hand` over both items is
  the same before and after; rules out a move that takes from one shelf and forgets the other.

## Exit criterion
`tests/test_stock_transfer_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Transfer log — why later: no storage yet — revisit trigger: the audit-trail feature.
