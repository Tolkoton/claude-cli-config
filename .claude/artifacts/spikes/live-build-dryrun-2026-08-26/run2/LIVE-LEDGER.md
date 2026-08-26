# Live build — webhook receiver

Started 22:09:44 UTC · 55-minute build budget · 3 units, the third droppable
Every entry is stamped with minutes elapsed since that start.

### T+00:35 — Plan frozen, then reviewed: I had the security ordering backwards
Building: a webhook receiver that rejects forged requests and queues genuine ones.
Contract: handle_webhook(signature, raw_body, secret, queue) -> (status, body). Genuine gets
202 and exactly one queue write; forged gets 401 and no queue write.
Riskiest piece: signature comparison and the order it happens in.
Not building: replay protection, retries, dead-letter handling, a real queue.

The review said: I had written that checking the signature before parsing the body was the
flaw. It is the opposite — checking first is what keeps attacker-controlled bytes out of
the parser, and parsing first would break genuine requests whenever key order or whitespace
differs from what was signed.
Did: kept the order as verify-then-parse and added a case I had missed — a real signature
over a body that is not valid JSON is a 400, not a 401. The sender is who they claim to be;
they just sent something malformed.
Cost: 16 seconds. The seam signature was unaffected, so nothing written during the review
had to be thrown away.

### T+00:57 — Units 1 and 2 done: signature checked, genuine requests queued
Does what we agreed: yes. Genuine request returns 202 and writes to the queue exactly once;
a forged one returns 401 and the queue stays empty.
Tests: 3 passed — python3 -m unittest -v
Anything unagreed: no. Two files, both in the plan.
Used constant-time comparison rather than ==, because a plain string compare on a digest
leaks how many leading characters were right.

### T+02:01 — Requirement changed: replays have to be rejected, so the timestamp must be signed too
Keeping: everything about how a forged request is refused, and the order the checks run in.
The verify-then-parse decision, the 400 for a malformed body from a real sender, and the
rule that nothing forged reaches the queue are all untouched — the change adds a check, it
does not move the ones already there.

Throwing away: the signature basis and the test helper that mirrors it. Two lines in
webhook.py and two in the test file. The signature now covers the timestamp joined to the
body, not the body alone. Every existing test had to be re-signed, which is the real cost —
not the new code.

Why the timestamp goes inside the signature rather than beside it: if it were only a header,
an attacker could take a captured request, swap in a current timestamp, and it would still
verify. There is a test for exactly that.

Cost: 38 seconds here, but that is with no one to explain it to. Budget four minutes live.
Paying for it by dropping unit 3 — the receiver will not be mounted on a running server this
session. It is exercised through its tests instead.

Note against my own rules: this session now has five tests and the limit I set was four. The
change introduced a risk class that did not exist when that limit was chosen, and replay
protection is worth two tests on its own. Raising a limit because the requirement moved is
legitimate; raising it because four felt tight would not be.

### T+02:10 — Done for this session
Built: a webhook receiver that refuses forged requests, refuses replayed ones, refuses
malformed ones from real senders, and queues everything else exactly once.
Proven by: 5 tests, all green (python3 -m unittest).
Not built: mounting it on a server — dropped to pay for the timestamp change. Also still
out: retries, dead-letter handling, a real queue.
Known gaps: the queue is a list in a test double, so nothing here proves delivery to real
infrastructure. The five-minute window is not configurable and the clock is passed in, so
whoever mounts this has to supply a real one — that is the next thing I would write.
