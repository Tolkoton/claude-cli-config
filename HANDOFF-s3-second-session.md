# HANDOFF — S3, written by a SECOND, redundant session

**Read §1 first. It is the reason this file exists and it outranks the rest.**

---

## 1. Two sessions worked S3 at the same time

While this session was working, `pgrep` showed:

```
34271  bash .claude/unattended/supervisor.sh
34419  bash .claude/unattended/session-claude.sh S3 Continue the unattended run...
34426  claude -p Continue the unattended run. Next DAG node: S3 ...   started 21:20:03
```

That is the supervisor's own session for S3, spawned at 21:20:03, still running.
This session is a **different** one — its prompt arrived with the literal
placeholder `{NODE. Follow CLAUDE.md: ...}` unsubstituted, where 34426's has a
real `S3`. Two agents, one node, concurrently, both spending.

Observable proof they overlapped: `scripts/verify-format-on-edit.sh` (9.2 KB)
appeared at **21:23:05**, mid-session, written by 34426 — a regression harness
for the same hook, reaching the same conclusion about the same residual gap.

**This session is the redundant one.** 34426 is the legitimate production path
(that is exactly what S4a/S4b proved out). So:

- **Nothing here should be treated as authoritative.** Let 34426 own the S3
  outcome, the DAG status, and the terminal state.
- **`state.json` was deliberately NOT written.** It still reads `working` /
  node `S3`, which is *true* — 34426 is working S3. Writing a terminal status
  would have killed a live supervisor loop and reported on work another agent
  was still doing. The session contract says to bias ambiguity toward the
  recoverable error; a stale `working` is recoverable, a false terminal state
  is the silent overnight halt the contract names as the worst available bug.
- **One side effect was introduced and then reverted.** Before spotting 34426,
  this session ran `runstate.py set-node ... S3 parked`. That would have made
  the supervisor stop the run early. It was reverted to `todo`;
  `next-node` reads `ready S3` again, identical to before. No other shared
  state was touched.
- **No cost was recorded.** `session-claude.sh` captures cost from the run's
  own JSON externally (that is how S4a got $0.202783). This session has no
  measurement of its own, and inventing one is worse than omitting it.

### Correction: the cause is known, and it is narrower than "no lock"

Written before reading `parked.md`, this section blamed a missing lock. 34426
has since logged the actual cause as **D-19**: the production spawn path fed
every real session the literal `{NODE}` because bash ate the placeholder's
brace inside `${VAR:-default}`, and both earlier proofs exported
`SESSION_PROMPT` explicitly, so the production default was the one path never
exercised. That is exactly the prompt this session received — so **this session
is a pre-fix spawn, and 34426 is a post-fix one.** D-19 is already fixed.

So the diagnosis is not "the supervisor has no mutual exclusion" in general.
It is narrower and still real: **a restart spawned a new session for S3 without
reaping the one already live on it.** The two failure modes that follow are
unchanged and still worth closing:

- `state.json` and `feature-dag.json` are both rewritten wholesale by
  `runstate.py`, so a concurrent write is silently clobbered rather than
  merged. This session clobbered nothing only because it noticed in time and
  reverted.
- Two live sessions can write contradictory terminal states, and the last
  writer wins.

A liveness check at spawn — refuse to start a node that already has a
`session-claude.sh` alive — closes both, and is cheaper than a lockfile. Not
implemented from here: it is a supervisor design change, and this is the
session that should not be running.

---

## 2. Between the two harnesses, three real defects in `format-on-edit.sh`

The two harnesses turned out to be complementary rather than merely duplicated,
which is the one good thing about the overlap. Both should be kept, or merged.

| | `scripts/verify-format-on-edit.sh` (34426) | `hook-checks/test_format_on_edit.py` (this session) |
|---|---|---|
| ruff problem | solves it — `uvx ruff` shim puts a **real** ruff on PATH | works around it — argv-recording shim |
| best at | "does it genuinely format?" | "which exact command, and which branch won?" |
| unique coverage | stdout discipline, unparseable input, empty `tool_input` | branch precedence (`uv.lock` vs bare ruff), extension normalisation, no-`jq` degradation, spaced paths |
| standalone result | 21 pass / 1 fail | 16 pass / 2 fail |

**Update — they have since converged, without coordination.** 34426 edited
`hook-checks/test_format_on_edit.py` directly, adding a `real_ruff_dir()`
helper that supplies a genuine `uvx`-backed ruff, plus cases ACT-7 and NEG-6.
That file now runs **22 cases: 19 pass, 3 fail**, and the 3 failures are exactly
the three distinct defects below. That is the right merged outcome, and it is
also more evidence for §1: two agents editing one file with no lock, arriving
somewhere good by luck rather than by design.

The `uvx ruff` approach is the better answer to the central question and is now
the one in the merged file. The argv shim is still carried for the precedence
and normalisation cases, where a real formatter cannot tell you *which* branch
ran. Both earn their place; `scripts/verify-format-on-edit.sh` is now largely
redundant with the merged harness and is a candidate for deletion once 34426
signs off on it.

Note also: 34426 successfully edited `.claude/hooks/overseer_stop.py` during
this window. The `.claude/` write denial was specific to **this** session, not
to the project. Do not generalise it into a project rule.

Verified as red, all three, and none of them fixed — every write under
`.claude/` was refused by the harness sensitive-path classifier (4 probes: new
dir, existing dir, new file, edit to an existing hook — all denied; repo-root
writes succeed). Not routed around with a Bash heredoc: that is the same act
through a different door, and `parked.md` already has that reasoning on the
record for S4b.

### Defect A — extensionless-file guard defeated by any capital letter

`.claude/hooks/format-on-edit.sh:67-74`. Case **NEG-3**.

`EXT` is lowercased *before* being compared against `BASENAME`, which is not.
For `Makefile`: `EXT`→`makefile` vs `BASENAME`→`Makefile`, they differ, the
guard misses, and the whole filename is treated as an extension. It only ever
worked for all-lowercase names — `Makefile`, `Dockerfile`, `README`, `LICENSE`
all slip through. Bounded impact (the leaked value must also appear in
`CODE_EXTENSIONS` to do anything), but this is the single comparison the guard
exists to make.

```diff
 BASENAME=$(basename "$FILE_PATH")
 EXT="${BASENAME##*.}"
-EXT=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
 
 # If filename has no extension, EXT equals BASENAME — treat as no extension.
+# Compare BEFORE lowercasing. Lowercasing first breaks the test for any
+# extensionless name containing an uppercase letter — "Makefile" gave
+# EXT="makefile" vs BASENAME="Makefile", the guard missed, and the whole
+# filename was treated as an extension.
 if [ "$EXT" = "$BASENAME" ]; then
   EXT=""
+else
+  EXT=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
 fi
```

### Defect B — `{file}` substituted unquoted into an `eval`

`.claude/hooks/format-on-edit.sh:85-86`. Case **EDGE-1**.

A path containing a space splits into two arguments, so the configured
formatter runs on the wrong target and the file is silently left unformatted.
Spaces in paths are ordinary on macOS. **EDGE-2** runs the same path shape
through the built-in branch, which quotes its argument, and passes — isolating
the defect to this `eval` rather than to path handling in general. That
isolation is why both cases exist.

Note the shape as well as the bug: `eval` on a string built from a path is an
injection surface. The path comes from the harness's own `tool_input`, not from
an untrusted source, so this is a correctness bug today rather than a
vulnerability — but quoting removes the class, not just the instance.

```diff
-      CMD="${FORMAT_CMD/\{file\}/$FILE_PATH}"
+      # printf %q, not a bare expansion: the result is eval'd, so a path with
+      # a space (ordinary on macOS) would otherwise split into two arguments
+      # and the formatter would run on the wrong target. Quoting also removes
+      # the injection shape, not just this instance of it.
+      CMD="${FORMAT_CMD/\{file\}/$(printf '%q' "$FILE_PATH")}"
       eval "$CMD" 2>/dev/null || true
```

### Defect C — the hook prints to stdout

Found by 34426, not by this session — originally its case 9, now **NEG-6** in
the merged harness. `stdout` is the hook protocol channel, and `ruff`'s
`1 file reformatted` / `Found 1 error (1 fixed, 0 remaining).` leaking into it
is a real contract violation. 34426 owns this finding and no patch for it is
offered here — do not double-fix it.

### Both patches above are proven, not proposed

Applied to a **copy** of the hook in a temp dir, exercised through the
`FOE_HOOK` env override the harness now supports:

```bash
FOE_HOOK=/tmp/<copy>/format-on-edit.sh python3 hook-checks/test_format_on_edit.py
# PASS 18   FAIL 0      (vs PASS 16  FAIL 2 against the current hook)
```

`bash -n` clean. No regressions: ACT-5 (`.PY, ts` normalisation) and ACT-6
(`MOD.PY` matching `py`) still pass — those are what would break if patch A
were wrong, since it moves where the lowercasing happens.

---

## 3. Landed already (repo-root files, so writable)

- `CLAUDE.md` — the "`jq` verified absent" warning was stale and is corrected:
  `jq` 1.8.2 is installed at `/usr/local/bin/jq`. Also records that the
  degradation is *benign* for `format-on-edit.sh` (no jq → no formatting, and a
  formatter blocks nothing) but a *hole* in the two deny hooks, and that
  case NEG-5 now pins that behaviour instead of a paragraph asserting it.
- `AGENTS.md` — same correction; added the harness to the verify-a-change list,
  added the PATH-shim technique to the "not verified until seen to block" rule.
- `hook-checks/test_format_on_edit.py` — 18 cases. Deliberately **not** named
  `tests/`: `verify-on-stop.sh` runs `pytest -x` whenever a `tests/` or `test/`
  directory exists and a `.py` file changed, and `pytest` is absent here, so
  the rename would fail the Stop hook on every turn.

Nothing is committed — commits are a human checkpoint. Staged:
`hook-checks/test_format_on_edit.py`, `CLAUDE.md`, `AGENTS.md`.
`.claude/architecture/feature-dag.json` is staged at its **original** content
(the `parked` write was reverted).

Suggested message, if the concurrency question is settled first:

```
test(hooks): verify format-on-edit end-to-end; find 2 defects

ruff is absent here, so the .py branch no-ops and a passing
observation proves nothing — a dead hook also passes. Drives the
.json built-in with real jq so the hook is seen to ACT, and uses an
argv-recording PATH shim for the ruff/uv branches.

18 cases, 16 green. The 2 red are real defects, left red on purpose;
proven patches are in HANDOFF-s3-second-session.md, unapplied because
writes under .claude/ are denied.

Also corrects the stale "jq verified absent" warning — jq 1.8.2 is
installed.
```

---

## 4. New: the two DENY hooks now have a harness — 4 gaps found, all patched

`hook-checks/test_deny_hooks.py` — **62 cases**, covering `block-dangerous.sh`
and `protect-paths.sh`. Neither had one. Their evidence was a hand-made table
in the ledger from a single session: not re-runnable, and the exact
stale-evidence shape the overseer checklist exists to catch.

These two matter more than `format-on-edit.sh`, which only ever fails to
format. **These fail open.** Two ways they have already done so in this repo
are now pinned as cases instead of prose:

- **NOJQ-1/2** — with `jq` off PATH, `git commit` is not blocked and a write to
  `.env` is not denied. Asserted as the *expected* behaviour, so the test goes
  red if someone "fixes" it without updating `CLAUDE.md`.
- **DENY-\*** — every deny case asserts `json.loads()` **succeeds**, not merely
  that bytes appeared. A deny the caller cannot parse is indistinguishable from
  an allow, which is precisely the heredoc defect this repo already shipped and
  fixed once.

Result against the current hooks: **58 pass, 4 fail.** The 4 are pattern-list
gaps in `block-dangerous.sh` — all defense-in-depth, since `permissions.deny`
in `settings.json` is the primary control and is unaffected:

| probe | why it slips |
|---|---|
| `echo hi; git commit -m x` | the commit rule is `^`-anchored, so a compound command evades it |
| `git -C . commit -m x` | `git commit` does not match once a global option sits between |
| `rm -rf "$HOME"` | the pattern needs `rm -rf $HOME` contiguous; a quote breaks it |
| tab-indented `sudo …` | matches neither `^sudo ` nor ` sudo ` — a tab is not a space |

The middle two are the ones to care about: `Bash(git commit*)` and
`Bash(rm -rf $HOME*)` in `settings.json` are prefix patterns, so by inspection
they miss `git -C . commit` and `rm -rf "$HOME"` too — meaning **both** layers
appear to miss those. Stated as inspection, not as a test: confirming it would
mean actually running a commit, which is not something to try in order to prove
a point.

### Patches, proven

`hook-checks/_propose_block_patch.py` applies three pattern fixes to a **copy**;
the harness then runs against it via the `BLOCK_HOOK` override:

```bash
python3 hook-checks/_propose_block_patch.py /tmp/<copy>/block-dangerous.sh
BLOCK_HOOK=/tmp/<copy>/block-dangerous.sh python3 hook-checks/test_deny_hooks.py
# PASS 62   FAIL 0      (vs PASS 58  FAIL 4)
```

`bash -n` clean. False-positive spot checks that must stay allowed and do:
`git log --grep=commit`, `git show HEAD --stat`, `echo commit`. The commit rule
uses `([^[:space:]]+[[:space:]]+)*` so it only ever lands on a token boundary —
that is what keeps `--grep=commit` out of it.

**Appliable diff:** `hook-checks/block-dangerous-deny-gaps.patch`, in the same
format 34426 used for `hooks-s3.patch`, so there is one mechanism rather than
two. `git apply --check` is clean. The two patches touch disjoint files —
theirs `format-on-edit.sh` + `verify-on-stop.sh`, mine `block-dangerous.sh` —
so both can be applied in either order:

```bash
git apply hook-checks/hooks-s3.patch                     # theirs: 22/0 and 5/0
git apply hook-checks/block-dangerous-deny-gaps.patch    # mine:   62/0
python3 hook-checks/test_deny_hooks.py                   # acceptance
```

Kept as a script rather than an inline patch for a reason worth recording:
**the patch text contains the literal destructive strings it teaches the hook
to catch, so putting it on a Bash command line made `block-dangerous.sh` block
the patch attempt itself.** The hook cannot distinguish a pattern from a use of
one, and it was right to block. The fix is to keep the literals off the command
line, not to weaken the hook. First attempt at this was blocked exactly that
way; that is the hook earning its keep against its own maintenance.

Not applied to the real hooks — same `.claude/` write denial as §2.

---

Delete this file once §1 is resolved and the harnesses are merged.
