## Invariants (rules that hold for every input in the stated domain)
- **I1** — nothing on the shelf is ever negative: after any sequence of `hold` and `release`
  calls, refused ones included, `on_hand >= 0` and `held >= 0`.
  - Domain: any starting shelf with `on_hand >= 0` and `held >= 0`; any sequence of `hold` and
    `release` calls with any integer quantities.
  - Source: Goal, "the shop never shows a negative number of units, free or put aside".
  - Broken by: a `hold` that does not compare the quantity with `on_hand`.
  - Check: generative.
