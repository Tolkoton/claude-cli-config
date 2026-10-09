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
