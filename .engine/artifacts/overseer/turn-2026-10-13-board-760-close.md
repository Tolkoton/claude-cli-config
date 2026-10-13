# Board 760 — the closing turn (2026-10-13), as the builder states it

Task: tasks/doing/760-open-item-test-gap-with-format-cmd-true-a-one-line.md (mode соло). The work was made and committed
in an earlier session of this task (commit c65a11e, one file, `tests/test_format_on_edit.py`, 9 insertions, 3 deletions):
- `UNFORMATTED` (the files whose one line is edited in OFF-1, OFF-2 and OFF-3) gained `tool.toml` and `prices.yaml` — the
  two extensions of the built-in prettier handler that no check held.
- OFF-1 (the engine's own project.env, `FORMAT_CMD="true"`) and OFF-2 (`CODE_EXTENSIONS="ts"`, `FORMAT_CMD="true"`) now
  demand for these two files as well: no formatter call in the shim log and numstat `1 1`.
- OFF-3 (control, the seed project.env with `FORMAT_CMD` empty) now demands a `prettier …/tool.toml` line and a
  `prettier …/prices.yaml` line in the shim log and a diff that grew for both, so the new checks are not vacuous.

No hook code was changed: the test found no defect. The off switch in `.claude/hooks/gate.py` (`format_file`, line 1226,
`if fmt.strip() == "true": return True`) returns before the extension is looked at.

That session had one audit (request 20261012T095814Z-b1e185). It named no failing check and was recorded as BLOCK 1 of 3
for one reason only: the gate escalation 2026-10-12T01:56:46Z of another task (slice `numbers-class-table`,
tests/test_task_class_table.py) was open. The task waited in tasks/blocked/ with that question. The owner answered
«закрито»; `.claude/state/gate/escalations.json` now lists that escalation under `closed` (closed_utc
2026-10-12T10:01:41Z) and `open` is empty. The task's question says what to do then: claim the unit again, a new overseer
judges it.

What this turn changed in working code: nothing. `git log --oneline c65a11e..HEAD -- tests/test_format_on_edit.py` and
`git diff --stat c65a11e HEAD -- tests/test_format_on_edit.py` print nothing: the file is as c65a11e left it.
`.claude/hooks/gate.py` was changed since by board 724 (commit 8a3b3f5); the off switch moved from line 1205 to line 1226,
its text is the same.

What I ran in this turn, on the tree as it is now (HEAD be0ab01), and what it printed:
- GREEN: `python3 tests/test_format_on_edit.py` → exit 0, `PASS 29   FAIL 0`; OFF-3 prints `ok   the built-in handlers
  ran and the diffs grew: OFF-1 and OFF-2 are not vacuous`.
- RED, in a detached worktree of HEAD (/tmp/b760-wt, removed afterwards; baseline there `PASS 29   FAIL 0`, exit 0): line
  1226 of `.claude/hooks/gate.py` narrowed to `if fmt.strip() == "true" and ext in ("md", "yml", "json", "py"):` (the
  per-handler off switch the task describes; one line changed) → `python3 tests/test_format_on_edit.py` exit 1,
  `PASS 26   FAIL 3`:
  - OFF-1 `FAIL the engine formats nothing (FORMAT_CMD="true", board 749)` — expected `''`, actual
    `prettier --write --log-level silent /tmp/foe-…/tool.toml` and `prettier --write --log-level silent /tmp/foe-…/prices.yaml`;
  - OFF-1 `FAIL a one-line edit must stay a one-line diff` — `tool.toml` and `prices.yaml` are `more`, the other four `1 1`;
  - OFF-2 `FAIL the off switch covers the built-in handlers` — the same two prettier calls, the same two `more`;
  - OFF-3 stays `ok`.
- The gap was real: on the same mutant the test as it was before c65a11e (`git show c65a11e^:tests/test_format_on_edit.py`
  written over the file in the worktree) → exit 0, `PASS 29   FAIL 0`.
- After `git checkout -- .` in the worktree: `PASS 29   FAIL 0` again.
- `bash tests/run_all.sh`, once → `PASS: 99 suites green`, exit 0 (`.claude/state/health/tests-full.json`: commit
  be0ab01, dirty false, recorded 2026-10-13T03:37:11Z, 1105.3 seconds). The fast subset was not run separately in this
  turn: its suites are among the 99; the first session ran it (`PASS: 45 suites green (fast subset)`).

Not run in this turn: a real prettier. The test uses PATH shims that record their argv and append a line to the file, as
the rest of the suite does; that a real prettier would rewrite the engine's own `.toml` and `.yaml` files is the first
audit's statement, not something this turn measured.

Decisions I made alone (from the first session, unchanged): no separate case OFF-4 — the two files joined the shared
set `UNFORMATTED`, so the same three cases (OFF-1, OFF-2 and the control OFF-3) hold the new extensions too.

=== UNIT 1 COMPLETE ===
