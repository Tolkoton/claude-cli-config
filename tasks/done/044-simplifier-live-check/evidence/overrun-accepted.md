# Complexity overruns of slice order-quote-s2-discount-stock

The contract is sealed; what the simplifier accepted over its budget is recorded here.

## 2026-10-05T21:32:24Z — overrun accepted
  - max_net_new_lines: 9 used, 4 allowed (production code, net of deletions)
  - max_new_public_symbols: 1 used, 0 allowed (src/refproj/orders.py:OutOfStock)
- Reason: Criterion 3 of board task 010 requires the new public class OutOfStock(ValueError) with a sku field (1 public name; 3 lines + 2 blank lines), the stock check is 3 lines and the discounted total 1; the owner's split puts all of it in slice 2. The simplifier (budget lens, blind) found nothing to remove. This is the simplifier's verdict, not the owner's ratification: the owner's figures (4 lines, 0 names) stay as written and the disagreement with criterion 3 is put to the owner on the board (key order-quote-s2-budget).
- Simplifier's verdict: answer-budget-s2.json (sha256 37517e5f3dc6…), 0 flag_only finding(s), none above
