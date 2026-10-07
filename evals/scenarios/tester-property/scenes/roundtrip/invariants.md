## Invariants (rules that hold for every input in the stated domain)
- **I1** — a printed price reads back as the same price: `parse_price(format_price(p)) == p`.
  - Domain: every price from 0.00 to 9,999,999.99 in whole cents.
  - Source: Goal, "what the shop prints, the import reads back"; Seam, the line on `parse_price`.
  - Broken by: a parser that does not take the comma out and refuses `1,234.50`.
  - Check: generative.
