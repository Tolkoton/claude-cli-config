The overseer's BLOCK on `8d28537` (request 20261007T113357Z-b3ef1b): a sum written currency-first («до $5», «USD 5») beside `Аудит потрібен: так` or `--owner-approved` was still dropped, and «до .5 долара» was read as 5. Fixed in the commit that follows `8d28537` on `unattended/work` (HEAD).

What I did, and the alternative I rejected. The overseer offered two ways: make the sum pattern read the currency mark on either side, or make a non-leave line stop the run. I rejected the first: it is one more list of spellings («5 dollars», «п'ять доларів», «5 дол.» would be the next findings), and this unit has been blocked five times on lists. I took the second and made it total: there is no sum reader outside leave any more (`PAID_SUM` and `Task.paid_sum` are gone). A `Платні прогони:` line that is neither leave («так», or «так» and one dollar sum) nor a plain «ні» (also empty, «—», «-») sets `Task.paid_unread`, and `board.line_unread(tasks)` then refuses EVERY paid run of that task — the audit opened by `Аудит потрібен: так`, and a run with `--owner-approved` in the owner's own terminal — with the wordings to write instead. It is asked first by both guards (`evals/run_audit_scenarios.py` `paid_run_refusal`, `evals/run_simplifier_evals.py` `paid_run_refusal`, which the other four runners reuse) and by `board.audit_refusal`. The only ceiling is the sum after «так», read by the leave pattern; «так, до .5 долара» and «так, до $5» are not leave, so they stop the run.

This reverses my decision of the previous attempt («the sum binds a run another word opened»): a line that is not leave now stops the run instead of capping it. It matches the owner's answer in the task: a task written the old way stops once with a question.

Cost of the choice: `--owner-approved` beside a task whose line says e.g. «скільки потрібно» now stops until the line is rewritten; the message says how.

Known residuals: «так, 1,000 доларів» reads as a ceiling of 1 dollar and «так, - 5 доларів» as 5 (both lower or equal to what was written — safe side); a task file with CRLF line endings refuses «так» (safe side). A sum written in the task's body, outside the header line, is not a ceiling — as before, and as the README says (the line is read in the header only).

Verification:
- `python3 tests/test_owner_terms.py` — PASS 210, FAIL 0. With `board.py` of `8d28537`: the suite stops with `AttributeError: 'Task' object has no attribute 'paid_unread'` at the first new check, so its count of red checks there is not known.
- `python3 tests/test_paid_run_gate.py` — PASS 58, FAIL 0; it runs `evals/run_audit_scenarios.py` end to end for «до $5», «$5», «USD 5», «до 5 dollars», «до .5 долара», «п'ять доларів», «скільки потрібно» beside `Аудит потрібен: так` and beside `--owner-approved`. With `board.py` and the two runners of `8d28537`: PASS 40, FAIL 18.
- `bash tests/run_all.sh` — 81 suites green, on the tree then committed.

=== UNIT 1 COMPLETE ===
