The overseer's BLOCK on `ed205b6` (request 20261007T103525Z-fec0db) had two findings; both are fixed in `8d28537`.

1. A dollar sum in the `Платні прогони:` line is no longer dropped when the line is not leave. `board.paid_ceiling` now returns the smallest dollar sum written in the header's `Платні прогони:` line(s) (`Task.paid_sum`), so a run opened by `Аудит потрібен: так` or by `--owner-approved` beside «до 5 доларів» is capped at 5 dollars. I chose "the sum binds" over "the run is refused": `Аудит потрібен: так` is the owner's separate leave, and the documents already promise that a sum written there is a ceiling. `tasks/README.md`, its template copy and `.claude/references/unattended.md` say so.
2. `tasks/README.md:23-24` and the template copy no longer advise «після так можна дописати, які саме прогони»; they say that only a dollar sum may follow «так». The check in `tests/test_owner_terms.py` that pins the READMEs now fails on the old sentence.

Also held now: the single words «також», «таки», «Такий.» and «так5 доларів» refuse (the two surviving mutants the overseer named).

Known residuals, all on the safe side and not changed: «так, 1,000 доларів» reads as a ceiling of 1 dollar; «так, - 5 доларів» reads as a ceiling of 5; a task file with CRLF line endings refuses «так».

Verification:
- `python3 tests/test_owner_terms.py` — PASS 176, FAIL 0. With the READMEs of `ed205b6` restored: 2 FAIL (the two README checks). With `board.py` of `ed205b6`: the suite stops with `AttributeError: 'Task' object has no attribute 'paid_sum'` at the first new check, so its count of red checks there is not known.
- `python3 tests/test_paid_run_gate.py` — PASS 42, FAIL 0. With `board.py` of `ed205b6`: PASS 38, FAIL 4 (the four new checks of the ceiling).
- `bash tests/run_all.sh` — 81 suites green, run on the tree that was then committed.

=== UNIT 1 COMPLETE ===
