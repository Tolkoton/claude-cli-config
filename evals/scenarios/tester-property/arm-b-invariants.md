
## Invariants
The contract has a section «Invariants»: rules that hold for every input of a stated domain,
each with a number (I1, I2…) — or the word "None" with the reason.
- For every invariant, one test with its number in the name (`test_I1_…`). This project has no
  property-based testing library and you do not add one: check the invariant on inputs you
  choose by hand from its «Domain».
- You do not add invariants of your own: a rule you think is missing, or a domain that reads
  two ways, is a question to the contract. Where the section says "None", you write no
  invariant test.
