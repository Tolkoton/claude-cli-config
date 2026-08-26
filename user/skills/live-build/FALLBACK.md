# Abandon the skill, keep the session

Read the box. Do the four lines. Keep talking.

---

## Say this

> "I'm dropping the process scaffolding and just building — the ledger is on screen up to
> here."

Then keep coding. Nothing breaks.

---

## Do this

```bash
rm -f /tmp/live-build-*                    # clock + critic scratch. Keeps LIVE-LEDGER.md.
```

That is the whole cleanup. One command.

- **Keep `LIVE-LEDGER.md`.** It is the artifact. It is valid as-is, half-written, with no
  closing entry. Never delete it mid-session to "tidy up".
- **Delete it only if asked:** `rm LIVE-LEDGER.md`.
- **Nothing else exists.** The skill writes no config, no hooks, no `.claude/` directory,
  no dotfiles, no partial state. Code and tests written so far are ordinary files and stay.

---

## Nothing is half-written

| Thing | State if you stop right now |
|---|---|
| `LIVE-LEDGER.md` | Complete through the last stamp. No trailer required. |
| Code and tests | Ordinary files. Run and pass or fail on their own. |
| `/tmp/live-build-*` | Scratch. Deleting it is harmless at any moment. |
| The repo | Untouched apart from the files just written. No commits, no staging, no config. |
| A background critic process | Dies on its own within 120 seconds. Ignore it. |

---

## When to bail

- The clock command errored and elapsed times are wrong → bail, keep coding. The clock is
  worth nothing if it is lying.
- The critic hung or the `claude` binary is missing → **don't bail**, just skip it. Stamp
  one line: `Did: skipped, no reviewer available.` Everything else works without it.
- The interviewer wants to drive, or wants a direction the phases don't fit → bail. Their
  session.
- You are behind and the process is the reason → bail. Shipping beats stamping.
- The interviewer says "don't stop, just keep going" → **drop the phase-boundary hold
  only.** Say "I'll run straight through" and keep the stamps. The hold is for your
  narration; if they don't want it, it has no other purpose. Everything else stands.

---

## Half-bail: keep the ledger, drop the rest

Usually the right move. Stop announcing phases, stop the audits, keep writing one entry per
decision with the same command:

```bash
E=$(( $(date -u +%s) - $(cat /tmp/live-build-t0) )); printf '\n### T+%02d:%02d — %s\n%s\n' $((E/60)) $((E%60)) "HEADLINE" "BODY" | tee -a LIVE-LEDGER.md
```

The ledger is the part being evaluated. It survives everything else being dropped.

---

## Don't

- Don't apologise for the process on the way out. One sentence, then build.
- Don't retro-fill missed stamps. A gap is honest; a fabricated timestamp is not.
- Don't restart the skill mid-session. Bailing is one-way.
