# Project profile — <project name>

<!-- The template of `.engine/onboard/profile.md`. `/onboard` copies it there and fills it; write it
in the owner's language. Read on demand by the maintenance commands, the architects and their
critics — it is not imported into CLAUDE.md. Every claim below cites what it rests on
(`file:line`, a commit, a command that was run); a claim with nothing to cite is not written.
Delete these comments as the sections fill. -->

Status: **draft — not confirmed by the owner** <!-- without the owner add: "steps 1–3 only";
after step 4: "confirmed by the owner, <date>". If no lint, type-check or test command could be
run, say so here, first. -->
Surveyed at commit: `<sha>` · Fresh reader: <not yet | date, N references checked, M corrected>

## 1. Map

<!-- Languages; what is in which directory (code, tests, generated, vendored); the entry points;
how the parts connect. "This is how it is" — never "this was decided". -->

| Path | What it is | Evidence |
|---|---|---|

Hot places (change most often and are the largest), over <how far back the history was read>:

| Path | Commits touching it | Lines | Read in full | A test file beside it |
|---|---|---|---|---|

Documents and their state (current / contradicts the code — an observation, not a fix):

| Document | State | Evidence |
|---|---|---|

Dependencies and runtimes: <manifests, lock files, the runtime versions they ask for; identifiers
of external accounts are not copied here>

## 2. Commands

<!-- Every command found, whether it works or not. Only the rows with status "ran" may go into
`.claude/project.env`. -->

| Purpose | Command | Found in | Status (ran / not run / variant) | Exit, duration | What fails, or why not run |
|---|---|---|---|---|---|

## 3. Rules

<!-- Every candidate, confirmed or not. Source is one or more of: written / seen in the code / seen
in the history. "Seen in the code" says what it is counted over and lists the files that keep the
habit AND those that do not; a count over files not read is marked "counted, not read". Verdict
is the owner's: yes / no / the corrected text verbatim / waits for the owner. -->

| # | Rule (and the part of the project it holds in) | Source | Evidence | Counter-evidence | Owner's verdict | Goes into AGENTS.md |
|---|---|---|---|---|---|---|

Guesses (no source strong enough to offer as a rule):

- …

## 4. Risk zones

| Zone | Paths | Why |
|---|---|---|
| Tests exist (a test file names it — or measured, say which) | | |
| No tests | | |
| Do not touch — candidates the survey saw (generated, vendored) | | |
| Do not touch — the owner's words | | |

Secrets and credentials: where they are, by path only — never opened, never quoted.

## 5. Not read

<!-- Three levels: read in full is in the map above; here — what was only searched, and what was
not opened. The only claim made about these paths is a count marked "counted, not read". -->

- Searched only: …
- Not opened: …

## 6. Open questions for the owner

1. …
