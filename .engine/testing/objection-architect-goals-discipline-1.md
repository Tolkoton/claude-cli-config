# Objection package — architect-goals-discipline, round 1

- Test file: `tests/test_architect_goals.py`, line 228: `def load_engine():  # noqa: ANN201`.
- Contract line: none — the helper is not a behaviour of the contract; it loads `engine.py` for
  `test_ownership_line_seeds_docs_infra_first` («`.claude/ownership.txt`: `project  docs/infra.md  seed=…`»).
- Why: the Stop gate's bypass guard refuses a new `noqa` in the diff («the gate is passed by silencing it, not by
  fixing the code»). The cause can be fixed: annotate the return type (`-> types.ModuleType`, `import types`) and
  drop the `noqa`. No check changes; the test's behaviour is the same. The builder may not edit a sealed test.
- Asked: correct the line (verdict `test_wrong` for the lint form only), keep every check as it is.
