
## Invariants
The contract has a section «Invariants»: rules that hold for every input of a stated domain,
each with a number (I1, I2…) — or the word "None" with the reason.
- For every invariant whose «Check» is `generative`, one property test with its number in the
  name (`test_I1_…`), written with Hypothesis: the library draws the inputs. The run command
  above brings Hypothesis with it; it is not installed in the project and you install nothing.
  The strategy covers exactly the invariant's «Domain»: you do not narrow it, and you do not
  suppress the library's health checks. Property tests go nowhere else: every other behaviour
  gets an example test.
- You do not add invariants of your own: a rule you think is missing, or a domain that reads
  two ways, is a question to the contract. Where the section says "None", you write no
  invariant test.
