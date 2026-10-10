# Feedback for the engine

What the work learned that belongs in the engine's own repository.

## 2026-10-06 — When a fix selects one item out of several (the last request, the newest file), the suite 

When a fix selects one item out of several (the last request, the newest file), the suite needs a case that holds at least two of them: with one item present, 'last' and 'first' are the same thing and a wrong selection passes (bugfix 002-overseer-bash-edit, BLOCK #4).

From: lesson #14509695 (overseer, -, 2026-10-06).

## 2026-10-09 — A test must put the code against the inputs that break its assumption, not only the ones i

A test must put the code against the inputs that break its assumption, not only the ones it was built for. Five times on 2026-10-06..08 a fix was proved only with friendly inputs: a link that leads somewhere but none to itself (004, 005), a SubagentStop envelope from an agent that called no tool (001), a file written by Edit but none by Bash (002), symlink loops tried under Python 3.12 only, not 3.13 (006). When a call is swapped for one with other exceptions, or a premise is assumed, write the case that would make it false first.

From: lesson #7ac596ba (agent, 004-symlink-loop-traceback, 2026-10-06).

## 2026-10-09 — A path a model writes is judged by the path rules only after it is resolved to the file it

A path a model writes is judged by the path rules only after it is resolved to the file it names (relative to the project root, links and .. resolved): a validator that compares the written string lets an absolute path or a link walk around the rule (fix 003).

From: lesson #23830893 (agent, 003-validator-absolute-path, 2026-10-06).

## 2026-10-09 — A test that pins which day is «today» must use a date far from the real clock: with BOARD_

A test that pins which day is «today» must use a date far from the real clock: with BOARD_TODAY=2026-10-09 (the container's own date) the mutant «BOARD_TODAY ignored» survived board 106's case.

From: lesson #4254a86f (agent, -, 2026-10-09).

## 2026-10-09 — Hook coverage measured on suites that run COPIES of the hooks (a sandbox, a synthetic repo

Hook coverage measured on suites that run COPIES of the hooks (a sandbox, a synthetic repository, an old tag) says nothing about the hook files in the tree: measure the copies' origin or the coverage is a false zero (086).

From: lesson #99bdf08b (agent, 086-hook-coverage-golden-gaps, 2026-10-08).

## 2026-10-09 — Goals documents: propose a «Поки що не робимо» line with its condition for coming back, no

Goals documents: propose a «Поки що не робимо» line with its condition for coming back, not a standing prohibition — the owner's goals change, and a line without a return condition is never revisited (052).

From: lesson #a1b2c3d4 (analyst, 052-engine-goals-document, 2026-10-05).

## 2026-10-09 — Goals documents: check the repository's boundary first — an isolated outside project that 

Goals documents: check the repository's boundary first — an isolated outside project that lives beside the code (Decana) is not the project's goal and stays out of the document (052).

From: lesson #e5f6a7b8 (analyst, 052-engine-goals-document, 2026-10-05).

## 2026-10-10 — When a check reads a project setting, test its empty value against the readers that alread

When a check reads a project setting, test its empty value against the readers that already exist: an empty CODE_EXTENSIONS means «every file» to the gates and to the Stop hook (overseer_stop._is_code_path), and the first mode.py check-close read it as «no code» — failing open in a documented configuration (board 098, BLOCK 1). Two siblings from the same audit: a check's own crash must not share an exit code with its «missing» (Python exits 1 on an uncaught exception), and a range of a task's commits must cover every stay of the task in doing/, not the newest one.

From: lesson #7ced8025 (overseer, -, 2026-10-10).

## 2026-10-10 — The delete guard has no way through for a removal the owner ordered on the task board: boa

The delete guard has no way through for a removal the owner ordered on the task board: board 732 (remove the second opinion, the owner's «так» in 720) could not delete evals/run_second_opinion_evals.py, whose two network functions no test touched, and the owner's word reaches the guard only as delete_guard.py confirm (needs a simplifier finding with tool evidence) or a sealed slice contract (none in соло). A grant read from an answered question in tasks/blocked/ (the runner already checks the owner's answers there) would let an ordered removal through without a hollow test.

From: lesson #6e0a38a1 (gate, -, 2026-10-10).

## 2026-10-10 — Bug 007 (board 747): the hooks promise Python 3.11+, but the suites and the Stop gate run 

Bug 007 (board 747): the hooks promise Python 3.11+, but the suites and the Stop gate run under python3 only (3.13 on the cloud server), where Path.resolve() no longer raises on a symlink loop; the guard's loop case broke on 3.12 unseen, and its regression test is red only under python3.12. A code path that differs between Python versions needs its case run under the oldest supported interpreter too — for example the suite starting the hook under each python3.1x found on PATH.

From: lesson #b4933b7b (agent, 007-testing-guard-resolve-loop, 2026-10-10).
