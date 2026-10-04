# Project profile — <project name>

<!-- The template of `.engine/onboard/profile.md`. `/onboard` copies it there and fills it; write it
in the owner's language. Read on demand by the maintenance commands, the architects and their
critics — it is not imported into CLAUDE.md. Every claim below cites what it rests on
(`file:line`, a commit, a command that was run); a claim with nothing to cite is not written.
Delete these comments as the sections fill. -->

Status: **draft — not confirmed by the owner** <!-- after step 4: "confirmed by the owner, <date>" -->
Surveyed at commit: `<sha>` · Fresh reader: <not yet | date, N references checked, M corrected>

## 1. Map

<!-- Languages; what is in which directory (code, tests, generated, vendored); the entry points;
how the parts connect. "This is how it is" — never "this was decided". -->

| Path | What it is | Evidence |
|---|---|---|

Hot places (change most often and are the largest or most tangled):

| Path | Changes | Size | Tests beside it |
|---|---|---|---|

## 2. Commands

<!-- Every command found, whether it works or not. Only the rows with status "ran" may go into
`.claude/project.env`. -->

| Purpose | Command | Found in | Status (ran / not run) | Exit, duration | What fails, or why not run |
|---|---|---|---|---|---|

## 3. Rules

<!-- Every candidate, confirmed or not. Source is one of: written / seen in the code / seen in the
history. "Seen in the code" lists the files that keep the habit AND those that do not. Verdict is
the owner's: yes / no / the corrected text verbatim / waits for the owner. -->

| # | Rule | Source | Evidence | Owner's verdict | In AGENTS.md |
|---|---|---|---|---|---|

Guesses (no source strong enough to offer as a rule):

- …

## 4. Risk zones

| Zone | Paths | Why |
|---|---|---|
| Covered by tests | | |
| No tests | | |
| Do not touch (the owner's words) | | |

Secrets and credentials: where they are, by path only — never opened, never quoted.

## 5. Not read

<!-- Exactly what was not opened. Nothing in this profile is a claim about these paths. -->

- …

## 6. Open questions for the owner

1. …
