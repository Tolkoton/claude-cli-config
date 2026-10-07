## Invariants (rules that hold for every input in the stated domain)
- **I1** — the shares add up to the bill exactly: `sum(split_bill(amount, people)) == amount`.
  - Domain: every amount from 0.00 to 999,999.99 in whole cents; every number of people from 1 to 100.
  - Source: Goal, "the restaurant receives exactly the bill"; Seam, "Returns".
  - Broken by: an implementation that gives every guest `amount / people` rounded down and
    drops the cents that are left.
  - Check: generative.
