# Bug 003-validator-absolute-path

type: bugfix
status: fixed
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «знахідка з target «<корінь проєкту>/.claude/settings.json:3» і proposed_action auto_remove проходить validate без змін (protected лишається false, дію не знижено), тоді як той самий файл відносним шляхом стає protected і знижується до confirm … приймається і файл поза проєктом (/etc/passwd:1 проходить як чинна ціль)» (tasks/doing/708-open-item-044-validator-absolute-path.md).
- Expected: a finding on a protected file is never `auto_remove`, and its `protected` is recomputed by the validator — whatever way the agent wrote the path; a target or an evidence reference that is not a file of this repository is rejected.
- Where the expected is written: `.claude/hooks/simplifier.py:21` ("a protected path is never auto_remove (and `protected` is recomputed here)") and `:24` ("a file:line that exists"); `.claude/references/simplifier.md:47` ("a protected path is never …"); the validator's own error text, `simplifier.py:147` ("is not a file of this repository"); `.claude/agents/simplifier.md:94`; `second_opinion.py:16` ("Never sent: protected paths, SIMPLIFY_EXCLUDE, …"); the owner's task 708, «Що зробити»: «зводити target і ref до шляху відносно кореня проєкту …; шлях поза проєктом — відхиляти знахідку».
- Actual: the protection holds only for the one spelling `dir/file` relative to the root. An absolute path, `./dir/file`, `dir/../other/file` or a link names the same file and passes as unprotected `auto_remove`; a file outside the project passes as a valid target and as valid evidence.
- Where it was seen: the live check 044 (2026-10-05, `tasks/done/044-simplifier-live-check/report.md`): the simplifier agent wrote absolute targets (lens architecture) and absolute evidence refs (lens requirements), and the validator accepted them.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: a fresh repository `/tmp/b708/proj` (`.claude/settings.json`, `src/a.py`, `.claude/project.env`), a file `/tmp/b708/outside.txt` beside it; `python3 /tmp/b708/repro.py` calls `simplifier.validate(root, [finding], set())` with the same `auto_remove` finding (`protected: false`, evidence `grep src/a.py:1`) and seven spellings of the target or the evidence ref.
- Output:
  ```
  relative     accepted target=.claude/settings.json:3 protected=True action=confirm
  absolute     accepted target=/tmp/b708/proj/.claude/settings.json:3 protected=False action=auto_remove
  ./           accepted target=./.claude/settings.json:3 protected=False action=auto_remove
  src/../      accepted target=src/../.claude/settings.json:3 protected=False action=auto_remove
  outside abs  accepted target=/etc/passwd:1 protected=False action=auto_remove
  outside ../  accepted target=../outside.txt:1 protected=False action=auto_remove
  ref outside  accepted target=src/a.py:1 protected=False action=auto_remove
  ```
  Only the first line is the specified behaviour; the task named the absolute path, and `./` and `src/../` turned out to be the same hole.
- Result: reproduced

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
- Test: `tests/test_simplifier.py`, section «PATH-*» — at the level of the validator's function (`simplifier.validate`) and, the last case, of the command (`simplifier.py validate FILE`). Fourteen cases; all fourteen fail on the code as it is, the two negatives among them (they assert that the accepted finding is recorded with its path relative to the root).
- Command that runs it: `python3 tests/test_simplifier.py`
- It fails with: `FAIL a protected file written as <root>/.claude/constitution.md is lowered like the relative path` — the finding comes back `'protected': False … 'proposed_action': 'auto_remove'`, the symptom of section 1; and `FAIL a target outside the project (<outside>/note.py) is rejected`.
- The neighbour's test (section 4): `tests/test_second_opinion.py`, section «SEND-*», the six cases marked «board 708»; `python3 tests/test_second_opinion.py` — five fail (`FAIL a target written as <root>/secrets/tool.py:1 gets no request`, … `FAIL a file the claim names by an absolute or dotted path is not sent when it is protected, excluded or outside`), the negative passes on both sides.
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — both suites already reach the code.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/simplifier.py:174` (`lowered`) — `is_protected(env, rel)` answers false for the protected file, so `protected` is not set and the action is not capped; and `simplifier.py:121` (`reference_exists`) — `(root / path).is_file()` is true for a file outside the project.
- Why it happened: the path the agent wrote is used as text, on the assumption that the agent always writes it one way — relative to the root, with no `.` or `..`. The protected zones are globs anchored at the root (`.claude/settings*.json`, `secrets/**`) and are matched against that text by `re.fullmatch`, so any other spelling of the same file misses them; and joining `root / path` does not keep the result inside the root (an absolute path replaces the root, `..` climbs out of it, a link leads anywhere). Nothing ever resolved the path to the file it names.
- Same places: searched `grep -n "REF_RE\|is_protected\|glob_match\|root /\|EXCLUDE" .claude/hooks/simplifier.py .claude/hooks/second_opinion.py .claude/hooks/simplify_signals.py` and read every hit that takes a path from a finding.
  - `second_opinion.py:292-297` (`review`) — the SAME cause, and the worse consequence: `may_send(env, <the target's path as written>)` matches the same globs and the `SIMPLIFY_EXCLUDE` prefixes against the text, so a target spelled another way is read and SENT to the outside model. It normally receives what the validator wrote, but reads any file given to it and does not validate again. Fixed here, with its own failing cases.
  - `second_opinion.py:164-165` (`collect`, "the files the claim names") — the SAME cause: a path found in the free text of the claim goes through `(root / p).is_file() and may_send(env, p)`; the claim is not checked by the validator at all, so `<root>/secrets/tool.py`, `src/../vendor/gen.py` or a file outside the project named in a claim is sent whole. Fixed here, with its own failing case.
  - `simplifier.py` — `is_code(env, rel)` in `lowered` reads only the suffix; `route`, `accept`, `decide`, `reversals` print or hash the target and open nothing by it. They get the normalised target once the validator writes it. Not separate places.
  - `simplify_signals.py:79-86` (`production_files`) — its paths are not the model's: the file list is `git ls-files` (always relative to the root, never outside it), `SIMPLIFY_EXCLUDE` and `--paths` are the owner's configuration and the operator's argument, compared as prefixes with those git paths; a scope written absolutely matches nothing rather than too much. Not the same cause, left alone.

## 5. Fix
- The decision, in short: the path is resolved once, at the door. `validate` rewrites the target and every `read`/`grep` reference of a finding to the path as the project sees it — relative to the root, with `.`, `..` and links resolved (`Path.resolve()` + `relative_to(root)`), the `:line`, `:line-line` or `::symbol` kept — BEFORE the schema check and the lowering, so every rule after it (protected zones, `SIMPLIFIER_PROTECTED`, the finding's id, the report, the second opinion) sees one spelling. A path that leads outside the project is left as written and rejected by `reference_exists` with the error the validator already had ("is not a file of this repository"). Rejected instead: refusing every non-canonical spelling (the live check showed the agent does write absolute paths — valid findings would be lost for a matter of form, and the owner's task says to normalise); normalising inside `is_protected` (it has no root, and the outside-the-project hole is in another function).
- What changed:
  - `.claude/hooks/simplifier.py` — two private helpers, `_project_ref` (one reference → its project spelling, or None) and `_project_paths` (a finding with its target and references rewritten); `validate` passes every item through the second, `reference_exists` reads the reference through the first; one item added to the module docstring's list of validator rules.
  - `.claude/hooks/second_opinion.py` — `may_send` takes the root and judges the path through `_project_ref`: None (outside the project, not a path) is never sent, and the globs and `SIMPLIFY_EXCLUDE` prefixes are matched against the project spelling. Its three callers pass `root`. This covers both neighbours of section 4 (the target of a findings file that did not come from the validator; a file named in the claim's text) and, as a side effect, a `git grep` hit on a link that leads outside.
  - `.claude/references/simplifier.md` — the validator's and the second opinion's paragraphs say it.
  - `tests/test_simplifier.py` (section «PATH-*», 14 cases) and `tests/test_second_opinion.py` (6 cases marked «board 708»).
- The cases. Protected file lowered like the relative path when written: absolutely, absolutely with a line, as `./…`, as `src/../…`, through a link inside the project; `SIMPLIFIER_PROTECTED` for an absolute path. Rejected: an absolute path outside, the same with a line, `../<outside>/…`, a link inside the project that leads outside; an evidence reference outside. Negatives: an absolute path to an ordinary file stays `auto_remove`, is recorded relative with its line range, its evidence reference too, and gets the same id as the relative spelling; `path::symbol` keeps its symbol. Through the command: `simplifier.py validate` on a file with one absolute protected target and one outside target — `1 valid, 1 rejected, 1 lowered`. Second opinion: four spellings of a protected or outside target get no request; a claim naming a protected, an excluded and an outside file sends none of the three; negative — an ordinary file the claim names absolutely is still shown.
- Mutants, in a temporary copy (each must fail the suite; all seven do): `resolve()` replaced by a textual `abspath` → the two link cases fail; no normalising of `..` at all → 4 + 2 fail; `reference_exists` reading the raw reference → 6 fail; `validate` not rewriting → 9 fail; evidence not rewritten → the negative fails; the `:line` suffix dropped → 6 fail (two of them cases that existed before); `may_send` judging the text → 5 fail.
- The reproduction of section 2 with the fix:
  ```
  relative     accepted target=.claude/settings.json:3 protected=True action=confirm
  absolute     accepted target=.claude/settings.json:3 protected=True action=confirm
  ./           accepted target=.claude/settings.json:3 protected=True action=confirm
  src/../      accepted target=.claude/settings.json:3 protected=True action=confirm
  outside abs  REJECTED ["target '/etc/passwd:1' is not a file of this repository (path[:line] or path::symbol)"]
  outside ../  REJECTED ["target '../outside.txt:1' is not a file of this repository (path[:line] or path::symbol)"]
  ref outside  REJECTED ["evidence cites '/etc/passwd:1', which does not exist"]
  ```
- What it changes beyond the bug, deliberately: (1) an accepted finding is recorded with the normalised target, so the id of a finding written absolutely is now the id of the same finding written relatively (one finding, one id — `decisions.jsonl` and the removal trailers key on it); ids of findings that were always written relatively do not change. (2) A link inside the project is judged as the file it leads to: a link to a protected file is protected, a link out of the project is not a file of the repository.
- Budget: `complexity_budget.py check` → within budget: 0 new files, +27 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies. The first version of the neighbour's fix put the check into `second_opinion.collect` and the budget refused it (cyclomatic 30 → 32, over the limit of 13, a function that was over before); it was moved into `may_send`, where the decision belongs, and `collect` is unchanged apart from the argument. `second_opinion.py` calls the private `simplifier._project_ref`: the budget allows no new public name, and the two modules already share `REF_RE`, `is_protected` and `glob_match`.
- Known limits, left as they are: a symlink loop named as a path is a traceback, not a rejection (found by the overseer, section 7; task 716). `may_send`'s signature changed (`root` first) — it has no caller outside `second_opinion.py` (`grep -rn may_send`). `simplify_signals.py` is untouched (section 4).
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 24719d73dc1560be331845c84d0ff4c4a6b8e6af
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Command: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/003-validator-absolute-path.md --test tests/test_simplifier.py --cmd "python3 tests/test_simplifier.py" --expect "FAIL a protected file written as <root>/.claude/constitution.md is lowered like the relative path"`

````
PROVED: tests/test_simplifier.py fails on 24719d7 and passes on the working tree; the failure shows «FAIL a protected file written as <root>/.claude/constitution.md is lowered like the relative path»
  command: python3 tests/test_simplifier.py
  the fix: .claude/hooks/second_opinion.py, .claude/hooks/simplifier.py, .claude/references/simplifier.md, .engine/bugs/003-validator-absolute-path.md, tests/test_second_opinion.py
  before the fix: exit 1
    |   ok   --last narrows the window
    |   ok   a removed repeat whose twin stayed in the file has not come back
    |   ok   the repeat written again has come back
    | AGENT-*   the definition matches what the validator enforces
    |   ok   model fable, tools Read, Grep and Glob only
    |   ok   the definition names every one of: dead_code, premature_abstraction, defensive_for_impossible…
    |   ok   the definition names every one of: none, characterization_exists, mutation_verified…
    |   ok   the definition names every one of: flag_only, confirm, auto_remove…
    |   ok   the definition names every one of: low, medium, high…
    |   ok   the definition names every one of: target, claim, traceability…
    |   ok   the definition names every one of: signal, read, grep…
    |   ok   the example in the definition is itself a valid answer
    |   ok   the request for the agent carries the lens and the signals
    | 
    | PASS 60   FAIL 14
  with the fix: exit 0
    |   ok   --last narrows the window
    |   ok   a removed repeat whose twin stayed in the file has not come back
    |   ok   the repeat written again has come back
    | AGENT-*   the definition matches what the validator enforces
    |   ok   model fable, tools Read, Grep and Glob only
    |   ok   the definition names every one of: dead_code, premature_abstraction, defensive_for_impossible…
    |   ok   the definition names every one of: none, characterization_exists, mutation_verified…
    |   ok   the definition names every one of: flag_only, confirm, auto_remove…
    |   ok   the definition names every one of: low, medium, high…
    |   ok   the definition names every one of: target, claim, traceability…
    |   ok   the definition names every one of: signal, read, grep…
    |   ok   the example in the definition is itself a valid answer
    |   ok   the request for the agent carries the lens and the signals
    | 
    | PASS 74   FAIL 0
````

The neighbour (second opinion), the same way: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/003-validator-absolute-path.md --test tests/test_second_opinion.py --cmd "python3 tests/test_second_opinion.py" --expect "FAIL a target written as <root>/secrets/tool.py:1 gets no request"`

````
PROVED: tests/test_second_opinion.py fails on 24719d7 and passes on the working tree; the failure shows «FAIL a target written as <root>/secrets/tool.py:1 gets no request»
  command: python3 tests/test_second_opinion.py
  the fix: .claude/hooks/second_opinion.py, .claude/hooks/simplifier.py, .claude/references/simplifier.md, .engine/bugs/003-validator-absolute-path.md, tests/test_simplifier.py
  before the fix: exit 1
    | LIVE-*    the owner's decisions, the reversal split, the cost
    |   ok   decide records the owner's «ні» with the second model's verdict next to it
    |   ok   decide refuses anything but так or ні, and a thing that is no finding id
    |   ok   reversals shows how the second model compares with the owner
    |   ok   with no decision on record the line is absent
    |   ok   a removal the second model agreed with is counted apart
    |   ok   …and one it never saw is not
    |   ok   cost adds up what the record holds
    |   ok   cost on an empty record says so
    | SEED-*    other projects start with it switched off
    |   ok   the seed of a new project says SECOND_OPINION="off" and warns that code is sent to Google
    |   ok   a project.env without the key at all is off
    |   ok   the hook names no other source of the key
    | 
    | PASS 70   FAIL 5
  with the fix: exit 0
    | LIVE-*    the owner's decisions, the reversal split, the cost
    |   ok   decide records the owner's «ні» with the second model's verdict next to it
    |   ok   decide refuses anything but так or ні, and a thing that is no finding id
    |   ok   reversals shows how the second model compares with the owner
    |   ok   with no decision on record the line is absent
    |   ok   a removal the second model agreed with is counted apart
    |   ok   …and one it never saw is not
    |   ok   cost adds up what the record holds
    |   ok   cost on an empty record says so
    | SEED-*    other projects start with it switched off
    |   ok   the seed of a new project says SECOND_OPINION="off" and warns that code is sent to Google
    |   ok   a project.env without the key at all is off
    |   ok   the hook names no other source of the key
    | 
    | PASS 75   FAIL 0
````

## 7. Gate and overseer
- Gate: `bash tests/run_all.sh --fast` — 32 suites green after the last change of code (2026-10-06). `ruff` and `mypy` are not installed on this server; `python3 -m py_compile` of both changed modules passes. The full set, once: `bash tests/run_all.sh` — `PASS: 70 suites green` on the final code (machine record `.claude/state/health/tests-full.json`, 2026-10-06T04:08:02Z, 70 of 70, red: none).
- Overseer: PASS — request 20261006T041920Z-f8021c (attempt 1), entry in `.engine/overseer/ledger.md`. The Stop hook raised no request after the claim, so the request was made by hand from the claimed turn written out verbatim (`.engine/artifacts/overseer/turn-2026-10-06-708.md`; the anomaly is in `tasks/ANOMALIES.md`). The overseer ran both proofs and the full set again, killed eight mutants of its own and tried twenty spellings. Its two notes, kept: (1) a target, a reference or a claim-named path that is a symlink LOOP inside the project raises `RuntimeError` out of `_project_ref` on Python 3.12 (only `OSError` and `ValueError` are caught) — a traceback where the old code rejected; it fails closed, nothing is accepted or sent — a new task, `tasks/todo/716-open-item-708-symlink-loop-traceback.md`, not fixed here because the code had been audited; (2) the claimed turn said "nothing is committed yet" while the checkpoint `e6d05a6` was made before the request — true when the turn was written, stale when it was audited.
- The regression test stays in the suite: `tests/test_simplifier.py`, section «PATH-*», and `tests/test_second_opinion.py`, the cases marked «board 708» (both run by `bash tests/run_all.sh`).

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: a test was missing — every case of the validator wrote its path one way (relative to the root), so a rule matched against the text of a path was never put against another spelling of the same file, nor against a file outside the project.
- Queued: `#23830893 added`
