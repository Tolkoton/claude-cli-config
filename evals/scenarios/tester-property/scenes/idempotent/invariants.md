## Invariants (rules that hold for every input in the stated domain)
- **I1** — normalizing twice is the same as normalizing once:
  `normalize_sku(normalize_sku(t)) == normalize_sku(t)`.
  - Domain: every text of ASCII letters, digits, spaces, tabs, hyphens and underscores that has
    at least one letter or digit.
  - Source: Goal, "a normalized number must come out of it unchanged"; Seam, "Returns".
  - Broken by: an implementation that shortens a run of hyphens one pair at a time, so that
    `ab----12` needs a second pass.
  - Check: generative.
