# Live build — repo star count endpoint

Started 22:04:33 UTC · 55-minute build budget · 3 units, the third droppable
Every entry is stamped with minutes elapsed since that start.

### T+00:13 — Standard library only, no package installs
Chose: plain unittest and urllib, with the HTTP client injected.
Instead of: installing FastAPI and pytest, which is the obvious choice for this task.
Because: the machine has no package installer at all, so installing would cost minutes of
silence with no guarantee of success. The seam is identical either way — a function that
takes a client and returns a status and a body — so the framework is a wrapper I can add
later, not a design decision.

### T+00:25 — Plan frozen
Building: an endpoint handler returning a GitHub repo's star count, and a clear error when GitHub cannot answer.
Contract: get_repo_stars(owner, name, client) -> (status, body). The HTTP client is passed in. Failures come back as a status, never as an exception.
Riskiest piece: mapping upstream outcomes to our status codes. Upstream 404 should surface as 404, but upstream 500 or a dead connection must become 502 — a naive version passes the upstream status straight through, which looks correct until GitHub has an outage.
Not building: auth, caching, rate limits, retries, real network calls in tests.
Units: 1 seam and happy path · 2 failure mapping · 3 mount on a real server (droppable)

### T+01:12 — Outside review of the plan: one blocking objection, and it was right
Said: the contract has no way to express a dead connection. Every path through it returns
an HTTP status, so there is nothing a fake client can return that means the request never
got an answer — which makes the failure I called riskiest untestable.
Did: changed the contract. A status of 0 now means the request never completed. Deleted
the 25 lines of signatures written while the review ran and rewrote them, rather than
patching around the gap.
Cost: 12 seconds of review, about a minute of rework. Finding this in unit 2 would have
meant rewriting unit 1's test on camera.

### T+01:41 — Units 1 and 2 done: star count, and what happens when GitHub does not answer
Does what we agreed: yes. get_repo_stars(owner, name, client) returns (status, body); a
dead connection and a GitHub 500 both come back as 502, and a 404 stays a 404.
Tests: 4 passed — python3 -m unittest -v
Anything unagreed: no. Two files, both in the plan: stars.py and test_stars.py.
Note: this used the whole test budget. Four tests was the ceiling and the failure mapping
needed three of them — one per upstream outcome that maps differently.

### T+02:11 — Done for this session
Built: GET /repos/<owner>/<name>/stars, backed by the GitHub API, with a 502 whenever
GitHub cannot answer and a 404 that means what a caller expects it to mean.
Proven by: 4 tests, all green (python3 -m unittest), plus a live call — astral-sh/ruff came
back with 49,319 stars, an unknown repo came back 404, an unrouted path came back 404.
Not built: auth, caching, rate limits, retries. Named as out of scope at the start and
still out.
Known gaps: the tests fake the HTTP client, so they prove the mapping logic and not that
GitHub's payload looks the way I assumed. The live call above is what covers that, and it
only worked because this endpoint needs no token — against an authenticated API there
would be nothing here proving the integration.
