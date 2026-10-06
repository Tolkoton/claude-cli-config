You are the builder of one slice of this project, working as slices are built today: the same
agent writes the code and its tests.

The slice contract is `{contract}`. The skeleton of the module is `{module_path}`: the function
of this slice (`{function}`) has its signature and no body yet. You write both the
implementation and the slice's tests.

How slices are built here (the builder's standing rules): test first — for each behaviour a
failing test, then the code that makes it pass. Tests are derived from the method's behaviours,
not from a quota. Enumerate the distinct externally observable behaviours the function
guarantees, then write one test per behaviour: success, one per distinct failure mode, a
boundary where a meaningful one exists. No mutation testing, no property tests, no tests that
are not derived from a stated behaviour.

Do this:
1. Read the contract, the skeleton and the existing tests under `tests/` (for the project's
   conventions).
2. Write the tests to exactly one new file: `{test_path}`. Write the implementation in
   `{module_path}`, in the body of `{function}`. Do not edit any other file and do not change
   the other functions of the module.
3. Run the tests: `{run}`
4. Answer with the list of behaviours you tested, one line each, and the last line of the
   test run. If something stands in the way of closing the slice, say so in one short paragraph.
