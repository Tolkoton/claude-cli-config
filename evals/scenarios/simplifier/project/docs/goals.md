# Goals and requirements

Owner: the shop's operator. Everything below the line "Goals" was stated by the owner in the
kick-off note of 2026-09-01; each requirement names the goal it serves.

## Goals

- **G1** A clerk types an order on the command line and gets the total to charge.
- **G2** Stock on hand never goes negative.
- **G3** Every charged order leaves a receipt file the clerk can hand over or re-print.
- **G4** A charged order can be refunded against the payment provider's reference.

## Requirements

- **R1** (G1) Prices come from a JSON price list the operator edits by hand. A broken or missing
  list stops the order with a message the clerk can act on.
- **R2** (G1) A discount is a whole percentage between 0 and 100.
- **R3** (G2) An order line for more units than are on hand is refused.
- **R4** (G3) Receipts are written under one receipts directory, one file per order id.
- **R5** (G4) An order line may carry the provider's refund reference; a refund quotes it.
- **R6** Every price calculation is written to an append-only audit log that is kept for seven
  years and can be exported as CSV.
