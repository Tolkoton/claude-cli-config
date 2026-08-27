# HANDOFF — S3 (authoritative)

Written by the supervisor's own S3 session (PID 34426, spawned 21:20:03Z by
`session-claude.sh S3`). This is the file to act on. It supersedes and
incorporates `HANDOFF-s3-second-session.md`, which was written by a second,
concurrent session that correctly identified itself as redundant and deferred
the S3 outcome, the DAG status, and the terminal state to this one.

Everything below belongs under `.claude/`. **Every write under `.claude/` was
refused by the harness sensitive-path classifier in this session**, so it is
staged at repo root instead. Merge it and delete both HANDOFF files.

The classifier is doing its job. A new executable in an auto-run hook
directory, and edits to the hooks that gate every other edit, are exactly the
things an agent should not self-grant. It was not worked around: a Bash heredoc
writes the same bytes through a different door, which is circumvention rather
than a workaround. The same reasoning is already on the record for S4b in
`parked.md`.

---

## 1. Outcome in one paragraph

S3's residual gap is **closed**. The hook is now *seen to act* on a `.py` file
with a real formatter, not inferred to act from a shim. Closing it surfaced
**four defects** — three in `format-on-edit.sh`, one in `verify-on-stop.sh` —
and **all four have patches that are proven, not proposed**. None are applied,
because writes under `.claude/` are denied. A fifth and sixth finding concern
the supervisor itself and are more serious than any of the hook defects; see
§5.

---

## 2. How the ruff problem was actually solved

The node was reopened because the prior pass could not verify
`format-on-edit.sh`: `ruff` is absent on this machine, so the hook's Python
branch no-ops, and "nothing bad happened" is the observation a *dead* hook also
produces.

`ruff` is absent from `PATH`, but **`uvx` fetches it** into uv's own tool cache
without installing anything into the project. That was not tried before. It
converts the central question from "which commands does the hook issue?" to
"does the file actually come back formatted?" — and the answer is yes:

```
ACT-7  .py built-in branch with a REAL ruff (uvx) -- hook seen to ACT
  ok   real ruff ran and the file was rewritten
  ok   ruff format normalised the signature
  ok   ruff check --fix --select I sorted imports (second invocation landed)
```

The argv-recording shim is still carried, because a real formatter cannot tell
you *which branch* ran — that is what ACT-2/3/4 (branch precedence,
`uv.lock` vs bare `ruff`) and ACT-5/6 (extension normalisation) are for. The
two techniques are complementary and both are kept.

**Running a real formatter is also what exposed Defect C.** A shim writes to
its log file; it does not chatter on stdout. No shim-based case could have
found it. That is the general lesson worth keeping: a substitute proves the
call, never the consequence.

### Current state of the harnesses

| File | Result now | Against patched copies |
|---|---|---|
| `hook-checks/test_format_on_edit.py` | 22 cases, **19 pass / 3 fail** | **22 / 0** |
| `hook-checks/test_verify_on_stop.py` | 5 cases, **4 pass / 1 fail** | **5 / 0** |

The failures are the defects. They are red on purpose and must stay red until
the hooks are patched.

`scripts/verify-format-on-edit.sh` — this session's own first harness — has
been **deleted**. Its two unique cases (real ruff, stdout discipline) were
merged into `hook-checks/test_format_on_edit.py` as ACT-7 and NEG-6. One
harness, not two that drift.

---

## 3. The four defects

### Defect A — extensionless-file guard defeated by any capital letter

`.claude/hooks/format-on-edit.sh:67-74`. Case **NEG-3**.

`EXT` is lowercased *before* being compared against `BASENAME`, which is not
lowercased. For `Makefile`: `EXT`→`makefile` vs `BASENAME`→`Makefile`, they
differ, the guard misses, and the whole filename is then treated as a file
extension. It only ever worked for all-lowercase extensionless names —
`Makefile`, `Dockerfile`, `README`, `LICENSE`, `Procfile` all slip through.
Reproduced directly:

```
Makefile     ext_after_lowercase=makefile     guard: DOES NOT FIRE -> EXT='makefile'
Dockerfile   ext_after_lowercase=dockerfile   guard: DOES NOT FIRE -> EXT='dockerfile'
README       ext_after_lowercase=readme       guard: DOES NOT FIRE -> EXT='readme'
notes        ext_after_lowercase=notes        guard: fires (EXT emptied)
```

Impact is bounded — the leaked value must also appear in `CODE_EXTENSIONS` to
do anything — but this is the single comparison the guard exists to make.

### Defect B — `{file}` substituted unquoted into an `eval`

`.claude/hooks/format-on-edit.sh:85-86`. Case **EDGE-1**.

A path containing a space splits into two arguments, so the configured
formatter runs on the wrong target and the file is silently left unformatted.
Spaces in paths are ordinary on macOS. **EDGE-2** runs the same path shape
through the built-in branch, which quotes its argument, and passes — isolating
the defect to this `eval` rather than to path handling in general. That
isolation is why both cases exist.

`eval` on a string built from a path is an injection *shape*. The path comes
from the harness's own `tool_input`, not from an untrusted source, so this is a
correctness bug today rather than a vulnerability — but `printf %q` removes the
class, not just the instance.

### Defect C — the hook leaks formatter output to stdout

`.claude/hooks/format-on-edit.sh` — the `eval` on :86 and the built-in
invocations on :100-111. Case **NEG-6**.

The hook's own header says "Silent on success". It redirects `2>/dev/null` but
**not stdout**, and `ruff format` reports on stdout:

```
FAIL formatter output must not leak to the hook's stdout
       expected: ''
       actual:   '1 file reformatted\nFound 1 error (1 fixed, 0 remaining).\n'
```

stdout is the hook protocol channel for a `PostToolUse` hook, so this injects
noise into the session on **every single edit** — a real context cost in a long
unattended run. Invisible until a real formatter ran; see §2.

### Defect D — `verify-on-stop.sh` corrupts the failure text it reports

`.claude/hooks/verify-on-stop.sh:130, 136, 142, 167, 174, 182` — all six
capture sites. Case **CAP-1**. **This is the most consequential of the four.**

Every site uses:

```bash
eval "$CMD" 2>/tmp/claude-lint.log >/tmp/claude-lint.log
```

Two redirections to the same path, neither of them `2>&1`. The shell opens the
file twice with two independent descriptors, each with its own offset and each
truncating. The streams overwrite each other from offset 0 instead of
interleaving. Demonstrated in isolation, then end-to-end through the real hook:

```
reason: "LINT FAILED (...):\nSUMMARY-1-error\nostic-line-THIS-IS-THE-HEADER\nE002 ..."
                             ^^^^^^^^^^^^^^^^ stdout, 16 bytes
                                              ^^^ "E001 first-diagn" destroyed
```

The first line of a lint/type/test failure — the header, the `file:line` — is
exactly what gets eaten. CLAUDE.md tells the agent to "read the actual error;
don't guess" when this hook blocks; the hook corrupts the actual error before
handing it over.

**This corrects §1 of the previous handoff**, which recorded `verify-on-stop.sh`
as needing no new work. The prior pass verified the block path emits *valid
JSON* — true, and necessary, but valid JSON can carry a corrupted payload.
Nothing had checked the payload.

---

## 4. The patches are proven, and staged as an appliable diff

All four are in **`hook-checks/hooks-s3.patch`**:

```bash
git apply --check hook-checks/hooks-s3.patch    # verified CLEAN
git apply hook-checks/hooks-s3.patch
python3 hook-checks/test_format_on_edit.py      # must be 22 PASS / 0 FAIL
python3 hook-checks/test_verify_on_stop.py      # must be  5 PASS / 0 FAIL
```

They were validated before being handed over, by applying them to **copies** in
a temp dir and running both harnesses against the copies through the `FOE_HOOK`
and `VOS_HOOK` env overrides the harnesses support:

```
FOE_HOOK=<copy> python3 hook-checks/test_format_on_edit.py   -> PASS 22  FAIL 0
VOS_HOOK=<copy> python3 hook-checks/test_verify_on_stop.py   -> PASS  5  FAIL 0
```

Both `bash -n` clean. No regressions: ACT-5 (`.PY, ts` normalisation) and
ACT-6 (`MOD.PY` matching `py`) still pass, and those are precisely what would
break if patch A were wrong, since it moves where the lowercasing happens.
CAP-2 (a passing check must not block) and CAP-3 (`stop_hook_active`
short-circuit) still pass, which is what would break if patch D turned the
capture fix into an always-block.

Don't take them on faith — the override exists so you don't have to.

---

## 5. Two supervisor findings, which matter more than the hook defects

### Finding 1 — the supervisor has no mutual exclusion on a DAG node

Two `claude -p` sessions ran S3 concurrently for ~15 minutes:

```
34426  claude -p ... Next DAG node: S3 ...          <- this session, via session-claude.sh
31106  claude -p ... Next DAG node: {NODE. ...      <- a second session
```

Both edited the same files. Observable proof of the race: this session's
`Edit` to `HANDOFF.md` failed with *"File does not exist"* because the other
session renamed it to `HANDOFF-s3-second-session.md` mid-flight. Both sessions
also edited `hook-checks/test_format_on_edit.py`. They happened to converge
usefully — that was luck, not design.

`runstate.py` rewrites `state.json` and `feature-dag.json` **wholesale**, so a
concurrent write is silently clobbered rather than merged. Two agents can also
write contradictory terminal states, and a false `finished` is the single worst
bug the session contract names.

A lockfile around node spawn, or a pre-spawn check that no `session-claude.sh`
is already live for the node, closes it. That is a design change to the
supervisor and is **not** being made from inside one of the two sessions that
demonstrated the problem.

### Finding 2 — the second session's prompt had an unsubstituted placeholder

PID 31106's prompt is literally:

```
Continue the unattended run. Next DAG node: {NODE. Follow CLAUDE.md: ... }
```

`{NODE` was never substituted, and the braces swallowed the rest of the
instruction. That session did not know which node it was on, and inferred S3
from repository state. Whatever spawned it did not go through the same
substitution path as `session-claude.sh` (34426's prompt has a real `S3`).
Worth finding before the next unattended run: a session that cannot name its
own node cannot honestly report on it.

### Correction to the other handoff

`HANDOFF-s3-second-session.md` states that this session "successfully edited
`.claude/hooks/overseer_stop.py` during this window" and concludes the
`.claude/` write denial was session-specific rather than project-wide. **That
is wrong.** This session made no such edit; the `MM` status on that file
predates both sessions. This session's `Edit` to
`.claude/hooks/format-on-edit.sh` was denied exactly as the other session's
were. Do not generalise from it.

---

## 6. Append to `.claude/overseer/ledger.md`

```markdown
## 2026-08-27T19:35:00Z — S3 — VERIFIED_AND_FOUR_DEFECTS_FOUND
- Trigger: unattended run, DAG node S3 (reopened for the format-on-edit residual gap)
- Evidence: `hook-checks/test_format_on_edit.py` 22 cases (19/3); `hook-checks/test_verify_on_stop.py` 5 cases (4/1); both go green against patched copies via the FOE_HOOK/VOS_HOOK overrides
- Action, one line per file changed:
  - `hook-checks/test_format_on_edit.py` — EXTENDED. Added `real_ruff_dir()` supplying a genuine ruff via `uvx`, plus ACT-7 (hook SEEN TO ACT on .py with a real formatter — the residual gap, closed without a shim caveat) and NEG-6 (stdout must stay silent). The shim cases are kept: a real formatter cannot show which branch won.
  - `hook-checks/test_verify_on_stop.py` — NEW. CAP-1 proves the block reason is corrupted; CAP-2/CAP-3 pin non-regression (passing check must not block; stop_hook_active short-circuits).
  - `hook-checks/hooks-s3.patch` — NEW. All four fixes as one `git apply`-clean diff, validated against copies before handover.
  - `scripts/verify-format-on-edit.sh` — DELETED. This session's first harness; unique cases merged into hook-checks. One harness, not two that drift.
- DEFECT A (format-on-edit.sh:67-74): extensionless guard lowercases EXT before comparing to a non-lowercased BASENAME — misses on Makefile/Dockerfile/README/LICENSE.
- DEFECT B (format-on-edit.sh:85-86): `{file}` substituted unquoted into an `eval`; a spaced path runs the formatter on the wrong target. EDGE-2 isolates it to the eval.
- DEFECT C (format-on-edit.sh:86,100-111): formatter stdout leaks into the hook protocol channel on every edit, contradicting the hook's own "Silent on success". Only visible with a real formatter — no shim could have caught it.
- DEFECT D (verify-on-stop.sh:130,136,142,167,174,182): `2>LOG >LOG` at all six capture sites clobbers the failure text from offset 0, destroying the first line of every reported failure. Corrects the prior pass, which checked the block JSON was valid but never checked its payload.
- NOT APPLIED — every write under `.claude/` denied by the sensitive-path classifier. Patches staged in `hook-checks/hooks-s3.patch`.
- CONCURRENCY: two sessions ran S3 at once (34426, 31106) for ~15 min with no mutual exclusion; 31106's prompt carried an unsubstituted `{NODE` placeholder. See HANDOFF-S3.md §5. More consequential than any hook defect here.
- Category: verification
```

## 7. Append to `.claude/overseer/parked.md`

```markdown
## 2026-08-27T19:35:00Z — S3 — PARKED
- Blocked on: write permission under `.claude/`. Four proven hook patches cannot be applied; ledger and parked entries cannot be appended.
- Class: human-input
- Reversibility: n/a — patches are staged in `hook-checks/hooks-s3.patch`, nothing is built on them
- Evidence: NEG-3, EDGE-1, NEG-6 red in `test_format_on_edit.py`; CAP-1 red in `test_verify_on_stop.py`. All green against patched copies. `git apply --check` clean.
- Unblocks when: a human runs `git apply hook-checks/hooks-s3.patch`, or Claude Code is restarted with a rule allowing edits under `.claude/hooks/` and `.claude/overseer/`. Same shape and same remedy as the S4b park.
- Acceptance: `test_format_on_edit.py` 22/0 and `test_verify_on_stop.py` 5/0.
- Continued with: queue exhausted — S3 was the last node; S1, S2, S4a, S4b, S5 are done.

## 2026-08-27T19:35:00Z — supervisor-concurrency — PARKED
- Blocked on: a supervisor design change — no mutual exclusion on a DAG node. Two sessions ran S3 concurrently; `runstate.py` rewrites shared state wholesale, so concurrent writes are clobbered, not merged.
- Class: human-input (design change to the thing that spawns sessions)
- Evidence: PIDs 34426 and 31106 both on S3 for ~15 min; an `Edit` to `HANDOFF.md` failed mid-flight because the other session renamed it. 31106's prompt contained a literal unsubstituted `{NODE`.
- Unblocks when: the owner adds a spawn-time lock (or a live-session check) and fixes the prompt substitution path that emitted `{NODE`.
- Note: deliberately not fixed from inside one of the two sessions that demonstrated the problem.
```

## 8. DAG node S3

Set via the sanctioned CLI (`runstate.py set-node`), the only DAG field it can
write. When the patches land, set `status: "done"` and record:

```
"evidence": "hook-checks/test_format_on_edit.py — 22 cases. Residual gap CLOSED without a shim caveat: ACT-7 drives the .py built-in with a real ruff supplied by uvx and the hook is seen to ACT (file rewritten, signature normalised, imports sorted — so both invocations landed). Shim cases retained for branch precedence and normalisation, which a real formatter cannot show. hook-checks/test_verify_on_stop.py — 5 cases; CAP-1 proves the block reason was being corrupted. Four defects found, all patched and proven against copies (22/0 and 5/0), staged in hook-checks/hooks-s3.patch: extensionless guard defeated by a capital letter, unquoted {file} into eval, formatter stdout leaking into the hook protocol channel, and 2>LOG >LOG clobbering the failure text at all six verify-on-stop capture sites."
```

---

## 9. Suggested commit

```
git add hook-checks/ HANDOFF-S3.md
git rm --cached scripts/verify-format-on-edit.sh 2>/dev/null || true
```

```
test(hooks): close the S3 verification gap; find 4 defects

ruff is absent from PATH, so the .py branch no-ops and a passing
observation proves nothing — a dead hook also passes. uvx supplies a
real ruff without installing into the project, so the hook is now seen
to ACT rather than inferred to act from a shim.

That surfaced 4 defects: an extensionless-file guard defeated by any
capital letter, an unquoted {file} substituted into an eval, formatter
output leaking onto the hook protocol channel, and — in
verify-on-stop.sh — `2>LOG >LOG` at all six capture sites clobbering
the failure text it reports back.

All four patched and proven against copies (22/0 and 5/0) via the
FOE_HOOK/VOS_HOOK overrides; staged in hooks-s3.patch because writes
under .claude/ are denied.
```

Not committed: commits are a human checkpoint.
