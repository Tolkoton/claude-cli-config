# Goals and requirements

Owner: the shop's operator. The goals were stated by the owner in the kick-off note of
2026-09-01. Each requirement names the goal it serves and where it came from: `owner` — the
kick-off note or a later answer of the owner; `planning` — written down while a slice was
planned.

## Goals

- **G1** A clerk types an order on the command line and gets the total to charge.
- **G2** Stock on hand never goes negative.
- **G3** Every charged order leaves a receipt file the clerk can hand over or re-print.
- **G4** A charged order can be refunded against the payment provider's reference.
- **G5** The accountant's monthly import takes every charged order without retyping.
- **G6** At closing the operator reads the day's takings and VAT from one file.

## Requirements

- **R1** (G1, owner) Prices come from a JSON price list the operator edits by hand. A broken or
  missing list stops the order with a message the clerk can act on.
- **R2** (G1, owner) A list exported from the old till — rows of `sku` and `price` instead of
  one mapping — keeps loading: two of the three shops have not re-exported theirs.
- **R3** (G1, owner) A discount is a whole percentage between 0 and 100.
- **R4** (G2, owner) An order line for more units than are on hand is refused.
- **R5** (G3, owner) Receipts are written under one receipts directory, one file per order id.
- **R6** (G3, planning) The order id is typed by the clerk; whatever is typed, nothing is
  written outside the receipts directory.
- **R7** (G3, planning) A receipt can also be rendered as a PDF and e-mailed to the customer.
- **R8** (G4, owner) An order line may carry the provider's refund reference; a refund quotes it.
- **R9** (G4, owner) A refund needs the manager's PIN.
- **R10** (G5, owner) Beside each receipt lies a JSON record in the format of
  `docs/receipt-export.md`.
- **R11** (G6, owner) Each charged order is one line of `receipts/journal.jsonl`: order id, total,
  VAT. An order whose command was repeated — the printer jammed, the window was closed — is
  there once.
- **R12** (G6, owner) Both tills write the one journal: the receipts directory is a share on the
  back-office machine (`docs/operations.md`).
- **R13** (G6, owner) The VAT of an order is the sum of its lines' VAT, each rounded to the cent —
  the way the tax office recomputes a receipt. Rounding the order's total once gives another
  cent on some orders.
