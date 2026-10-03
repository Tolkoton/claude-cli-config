# Releasing the engine

A release is three refs pointing at one commit: a version tag `vMAJOR.MINOR.PATCH`, `main` and
`stable`. `stable` is the saved reliable state: it moves only when the owner approves a release,
so it always names the last approved version. Projects install from the newest `v*` tag
(`engine.py install`, `update`); `stable` is the same commit under a name that does not change.

A release is the owner's act. The agent prepares the work on an `unattended/*` branch and never
releases: `engine.py release` refuses without `--owner-approved`, and inside a Claude Code
session the flag does not count.

## The order

1. **Read what is being released.** The reports in `tasks/done/*/report.md` since the last tag,
   and `git log <last tag>..<branch>`.
2. **Check out the commit to release**, in your own terminal — the work branch
   (`git switch unattended/work`) or `main` after you merged it. The work tree must be clean:
   nothing edited, nothing untracked.
3. **Release:**

   ```bash
   python3 engine.py release v0.12.0 --owner-approved
   ```

   The command, in this order, and stopping at the first thing that is not right:

   | Step | What it checks or does |
   |---|---|
   | version | `vMAJOR.MINOR.PATCH`; the tag exists neither here nor on the remote; newer than every released version |
   | clean | `git status --porcelain` is empty |
   | fast-forward | after `git fetch`, every existing `main` and `stable` — local and on the remote — is an ancestor of HEAD |
   | tests | `bash tests/run_all.sh` (every suite) exits 0 |
   | golden set | `evals/run_hook_scenarios.py --engine-ref HEAD --compare <baseline>` reports identical behaviour |
   | clean again | the checks left nothing behind and HEAD did not move |
   | tag | an annotated tag on HEAD (`--message TEXT` sets its message; default `engine <version>`) |
   | push | one atomic, non-forced push: the tag, `HEAD → main`, `HEAD → stable` |
   | local | the local `main` and `stable` are moved to HEAD; the branch you are on stays checked out |

   Before the tag step the only thing written is what `git fetch` brings. If the remote refuses
   the push, the local tag is deleted again: a refused release leaves no tag and no branch
   moved, here or there.
   Exit status: 0 released, 2 refused (the message says why).
4. **Update the projects:** `python3 engine.py update --all` (see `docs/TEMPLATE-SETUP.md`).

## Options

- `--baseline FILE` — the golden-set results to compare with. Default: the
  `evals/baseline/*/results-*.json` file committed last, which is what the plans call "the
  newest baseline" — of this environment's folder (`python3 evals/environment.py`) when it has
  one; otherwise the newest of any, and the release says the comparison is cross-environment. A change that adds or alters hook scenarios must record a new baseline
  before it can be released; otherwise the golden set differs and the release stops.
- `--remote NAME` — default `origin`.
- `--message TEXT` — the tag's message.

## What it never does

- It never forces. `main` or `stable` that hold a commit HEAD does not have stop the release;
  bring those commits into the branch first.
- It never moves a tag. A version that exists is refused; release the next one.
- It never commits, merges or switches branches.
- It runs no paid check. The overseer audit (`evals/run_audit_scenarios.py --tier full`) before
  a tag stays a separate, deliberate run — see `evals/README.md`.

## Limits

The owner check is a seat belt, not a lock: `CLAUDECODE` is set in every shell an agent's tools
start, and an agent that clears it has made a deliberate act visible in the transcript. The
remote's own branch protection is the lock. `tests/test_release.py` exercises every row of the
table above on a synthetic repository with a bare repository on disk as its remote.
