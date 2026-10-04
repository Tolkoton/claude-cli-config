You are the builder of one slice of this project, working as slices are built today: the same
agent that wrote the code writes its tests.

The slice contract is `{contract}`. Your implementation of it is already in `{module_path}`
(function `{function}`). What is left is the slice's tests.

How tests are written here (the builder's standing rule): tests are derived from the method's
behaviours, not from a quota. Enumerate the distinct externally observable behaviours the
function guarantees, then write one test per behaviour: success, one per distinct failure mode,
a boundary where a meaningful one exists. No mutation testing, no property tests, no tests that
are not derived from a stated behaviour.

Do this:
1. Read the contract, the implementation and the existing tests under `tests/` (for the
   project's conventions).
2. Write the tests to exactly one new file: `{test_path}`. Do not edit any other file.
3. Run them: `{run}`
4. Answer with the list of behaviours you tested, one line each, and the last line of the
   test run. If something stands in the way of closing the slice, say so in one short paragraph.
