# Rule proposals

Candidates for the standing rules. Never loaded into the persistent context; the ones the owner approves are promoted into `.engine/rules.md`.

## RP-d92e8dfa — 2026-10-04 — PROPOSED
- Rule: A suite that runs a hook pins CLAUDE_PROJECT_DIR to its own sandbox: inherited, the Stop gate hands it this repository, and the suite answers differently from the gate than by hand.
- Why: The Stop gate runs TEST_CMD with CLAUDE_PROJECT_DIR naming this project. tests/test_deny_gaps.py let block-dangerous.sh read this repository's branch through it, so on an unattended/* branch its commit cases came back ALLOWED — green by hand, red from the gate (2026-10-02, package 3c fix, X7). test_deny_hooks.py had needed the same pin before it. Nothing checks a new suite for it: 24 test files mention the variable and each pins it by hand.
- From: lesson #d92e8dfa (escalation, -, 2026-10-03)
- Status: PROPOSED (the owner decides: the question is in tasks/blocked/; only the owner's «так» lets `lesson_queue.py promote` through)
