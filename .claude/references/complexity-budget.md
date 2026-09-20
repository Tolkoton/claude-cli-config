# Complexity budget — how to set one

Read this when `/plan-slice` reaches the budget step (only when `.claude/project.env` has
`COMPLEXITY_GATE` set to `warn` or `block`).

The budget is agreed BEFORE the code exists. It is the smallest shape of change that can
satisfy the slice's exit criterion — not a forecast of what will probably get written.

## The section to add to the slice contract

```
## Complexity budget
base_commit: <output of `git rev-parse HEAD` right now>
max_new_files: 1
max_net_new_lines: 80
max_new_public_symbols: 2
max_new_abstractions: 0
max_new_dependencies: 0
max_cyclomatic_per_function: 10
max_nesting_depth: 3
justification: none
```

Plain `key: value` lines, whole numbers. A misspelt key is an error, not a missing limit.

## How to choose the numbers

1. Write down, in one or two sentences, the simplest change that meets the exit criterion:
   which existing file it goes into, which function it adds. Count from that.
2. **New files:** 0 if the behaviour belongs in a file that exists. A new file needs a reason
   the existing layout cannot absorb it.
3. **Net new lines** count production code only. Tests are measured and reported but never
   limited: a test adds lines and removes risk. Deleting code pays lines back.
4. **New public symbols:** the names the exit criterion itself mentions, no more.
5. **New abstractions** (a base class, a Protocol, an abstract method): 0 unless TWO users
   exist today. Name both in `justification`. "We will need it later" is not a user.
6. **New dependencies:** 0. Anything else names the dependency and the reason in
   `justification`, and the owner sees it when approving the contract.
7. **Complexity 10, nesting 3** are the defaults. They apply only to functions this slice
   adds or makes worse; old complexity in a file you touch is not charged to the slice.

## After writing the section

Run `python3 .claude/hooks/complexity_budget.py validate <contract path>` and fix what it
reports. Show the owner the budget together with the rest of the contract.

## During the slice

`python3 .claude/hooks/complexity_budget.py check` prints the current usage at any time.
If the gate blocks: make the change smaller. If the budget itself turns out wrong, stop and
tell the owner which limit and why. Do not edit the numbers — the limits the slice began with
stay in force, and a raised number is reported, not honoured.
