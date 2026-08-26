# Before the session

Three blocks. The first is a blocking gate run **the day before**. The second takes ten
minutes the hour before. The third is the last ninety seconds.

---

## T-1 DAY: the runner gate — BLOCKING, not advisory

**Run these two commands. Both must succeed. If either fails, you have a job to do today,
not a discovery to make during the session.**

```bash
python3 -m pytest --version
python3 -c "import fastapi; print(fastapi.__version__)"
```

This is a gate rather than a suggestion because it is the largest untested path in the
whole profile. Both dry runs of this skill were forced onto stdlib `unittest` — **FastAPI
was never once exercised end-to-end.** The failure it guards against is specific: you
reach T+15, discover the runner is missing, and spend the back half of the session
installing packages on a shared screen instead of building.

### If they fail: installing a runner when `pip` is unavailable

Do not assume `pip install` will work. On the machine this skill was developed on it does
not, twice over:

- **There is no pip at all.** `python3 -m ensurepip` returns `No module named ensurepip`,
  and no `pip`/`pip3` is on `PATH`.
- **`pip install` is denied by permission rules.** It sits in the `ask` list of the
  project's `settings.json`, and the request was refused during development. Claude cannot
  install it for you.

So install it yourself, outside the agent, by one of these. In order of preference:

```bash
# 1. uv — one binary, no root, brings its own Python and resolver. Best option.
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && uv pip install fastapi httpx pytest uvicorn
#    then run tests as:  uv run pytest

# 2. System package manager — needs sudo, which Claude is hard-blocked from.
sudo apt install python3-pip python3-venv
python3 -m venv .venv && .venv/bin/pip install fastapi httpx pytest uvicorn

# 3. Bootstrap pip by hand, if neither of the above is available.
curl -sS -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
python3 -m venv --without-pip .venv && .venv/bin/python /tmp/get-pip.py
.venv/bin/pip install fastapi httpx pytest uvicorn
```

Inside a Claude Code session, prefix any of these with `!` to run it in your own shell.

`httpx` is not optional padding — FastAPI's `TestClient` imports it, and finding that out
at T+15 costs the unit.

### If you cannot get a runner installed: choose the fallback NOW

Not at T+15. Write the choice down and say it in the session's first ledger entry.

| Available | Fallback | Test command |
|---|---|---|
| Bare Python 3 | `unittest` + an injected HTTP client, no framework | `python3 -m unittest -v` |
| Node | `node --test` (built in since 18) | `node --test` |
| Go | stdlib `testing` | `go test ./...` |
| Nothing but a shell | Assertions in `if` blocks with a non-zero exit | `bash check.sh` |

The stdlib fallback is a real option, not a defeat — both dry runs used it and the seam
shape was identical. What matters is that the choice is made in advance, in the open,
rather than discovered mid-session.

---

## T-60: prepare

### Warm the authentication

Expired credentials mid-demo is the worst available failure — it is unrecoverable on
camera and it looks like your fault.

```bash
claude --version          # binary present, on PATH
timeout 60 claude -p "Reply with exactly: OK"
```

Both must succeed. If the second prompts for login, log in now, then run it again until it
returns clean. Do this even if you used Claude an hour ago.

### Burn the first invocation

First-call latency is real and it is entirely avoidable. It must land here, not in the
session.

```bash
cd /tmp && mkdir -p live-warmup && cd live-warmup
timeout 120 claude -p "Write a one-line Python function that adds two numbers."
```

Run it **twice**. The second run is the latency you will actually see. If the second run is
slower than about fifteen seconds, plan on the critic being skipped and say so up front
rather than discovering it at T+7.

Then, in the session's own working directory, make one trivial edit through the tool and
undo it — this warms the permission prompts too, so the first real edit does not stop for
an approval dialog.

### Confirm the runner gate still holds

The install work happened yesterday, at the T-1 DAY gate. Re-run its two commands here to
confirm nothing changed — a different shell, a different virtualenv, or a machine you did
not expect to be on will all break it silently:

```bash
python3 -m pytest --version
python3 -c "import fastapi; print(fastapi.__version__)"
```

If you are on a stack other than Python, confirm the equivalent: `npx vitest --version`,
`go version`, `cargo --version`. If the gate now fails and there is no time to fix it, the
fallback table at the T-1 DAY gate is the answer — pick from it now, not at T+15.

### Confirm the skill is actually deployed on THIS machine

`live-build` lives in the `claude-cli-config` repo and reaches `~/.claude/skills/` through
a symlink. On a machine where that repo is not cloned, or where `install.sh` has not run,
**the skill does not exist** and nothing will say so until you invoke it.

```bash
readlink -f ~/.claude/skills/live-build     # must resolve to the repo path
cd /tmp && claude -p "List the exact names of every skill available to you." | grep live-build
```

The second command must be run from **outside** the repo — that is the whole property
being checked. If it prints nothing, run `./install.sh` from the repo root and re-check.

### Pick the repo and the branch

- A **throwaway** repo, or a branch you can delete. The skill has none of the hard guards
  the full system has: nothing here blocks `rm -rf`, a stray `git commit`, or a write to a
  secrets file. That protection is procedural now, and this is the procedure.
- `git status` clean before starting, so the diff at the end is only the session's work.

### Decide the permission mode

Decide before the clock, not during. Approval dialogs are dead air and they read as
hesitation. If the repo is genuinely throwaway, run in a mode that does not stop for
routine edits. Know which mode you chose and be able to say why in one sentence — it is a
reasonable thing to be asked.

### Open two panes

| Left | Right |
|---|---|
| The session | `LIVE-LEDGER.md`, auto-refreshing |

The ledger is the artifact being evaluated. It should be visible without anyone asking to
see it. If a second pane is not possible, the `tee` in the stamp command prints every entry
into the transcript anyway — but the pane is better.

### Re-read one page

`ARCHITECTURE.md`. Specifically the enforcement-versus-instruction section, the
devil's-advocate replacement, and "what the dry runs did and did not validate". Those are
the three places a good interviewer will push, and all three have answers that only work
if delivered without hesitation. The third is the one where the honest answer — that the
time discipline has never actually been tested under time pressure — is stronger than any
defence of it.

---

## T-2: the last ninety seconds

```
□  Notifications off — OS Do Not Disturb, Slack, mail, phone face down
□  Calendar alerts silenced (they fire mid-sentence and steal the screen)
□  Terminal font large enough to read on a shared screen — 16pt+, high contrast
□  Cleared scrollback (`clear`) — start from a blank screen
□  Second pane open on LIVE-LEDGER.md
□  Water within reach
□  `rm -f /tmp/live-build-*` — clear any stale clock from a rehearsal
```

That last one matters: a leftover clock file from a practice run makes every timestamp in
the session wrong, and wrong timestamps are worse than none.

---

## What to say while the model works

Dead air is the thing being avoided. Every waiting window has something specific worth
saying, and none of it is narration of what is on screen.

**During planning (T+0 → T+5)** — say what you are deliberately *not* building and why.
Scope discipline is the easiest thing to demonstrate and the least often shown:

> "I'm boxing planning at five minutes. Rate limiting, auth and caching are out — I'd
> rather have one path that genuinely works than three that half-work."

**During the critic window (T+5 → T+7)** — the strongest two minutes available. Explain the
mechanism, because it is the part that is actually interesting:

> "That's a separate process reviewing the plan with a hard two-minute timeout — it can't
> see my reasoning, only the plan, which is what stops it agreeing with me. If it doesn't
> come back in two minutes I proceed without it and the ledger records that I did."

**While a unit builds** — the reasoning behind the decision that is about to be stamped,
before it lands. Then the ledger line confirms what you already said, instead of
duplicating it.

**While tests run** — say what the test would catch, not that you are running tests:

> "This one fails if the timeout path returns a 200 with an empty body, which is the
> mistake I'd expect here."

**When something breaks** — this is a good moment, not a bad one. Read the actual error out
loud, say what it tells you, then fix. Watching someone read an error carefully is more
convincing than watching a clean run.

**At the close** — name the largest gap before being asked:

> "The external call is faked in every test. Nothing here proves the real API behaves the
> way I assumed — in a real build that's a smoke test against the sandbox, and it's the
> first thing I'd add."

**Never say:** "let me just...", "it should work", "I'm not sure why that happened", or
anything narrating what is visibly on screen.
