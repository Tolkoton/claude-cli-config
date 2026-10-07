# Running the tills

The operator's notes, 2026-09-20. Both tills run this program against one receipts directory,
a share on the back-office machine.

## Closing both tills at once

A wrong price list went out, or the payment provider is down: create an empty file `CLOSED` in
the receipts directory. Every till then refuses orders and refunds until the file is deleted.
The program never creates or deletes it — that is the operator's hand, from the back office.

## When the share stalls

The back-office machine's backup and its antivirus hold a file for a moment, a few times a day.
The program waits a little and tries again by itself before it says anything to the clerk. A
clerk who does see the journal message repeats the order.
