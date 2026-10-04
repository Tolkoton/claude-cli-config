#!/usr/bin/env python3
"""The actions board-runner.sh may take on the owner's word — and it takes no other (board 008).

    owner_action.py [--root DIR] apply-settings <sha256>
    owner_action.py [--root DIR] promote-rule <sha256>
    owner_action.py [--root DIR] reject-rule <sha256>
    owner_action.py [--root DIR] amend-goals <sha256>

`apply-settings` is the one way the shared settings change, in the engine's repository and in
every project it is installed into (board 038): settings_check.py, which ships with the engine,
judges the proposal docs/tasks/settings.json against the live file; a sound proposal is copied
over .claude/settings.json; and a project that keeps a test of its own in
tests/test_settings_proposal.py (the engine's repository does) has it run on the result.
`<sha256>` is the proposal the owner said «так» to (the agent wrote it under its question,
board.py `action-line`); a proposal that changed since is not the one that was approved and is
not applied. A refused proposal is never copied; a red test puts the previous file back.

`promote-rule` is the one way a lesson becomes a rule (board 040): the owner answered «так» under
a rule question, whose offer names the sha256 of the proposal's id and the exact rule text. The
PROPOSED proposal with that sha256 is promoted into .engine/rules.md by lesson_queue.promote,
which looks for the owner's answer itself; a proposal whose text changed since the question is
stale. `reject-rule` is the owner's «ні»: the proposal is marked REJECTED.

`amend-goals` is the one way an approved goals document changes without the owner's terminal
(board 051): the owner answered «так» under a question that offers the sha256 of the proposed
document `.engine/goals/proposed.md`. goals.py checks that it is a lawful amendment of the sealed
`.engine/goals.md` (no number dropped or reused, the version raised), puts it in its place, seals
it, and lists every decision that cited a changed line in `.engine/goals/to-review.md`.

An agent may not edit .claude/settings.json (protect-paths.sh) and may not get there through
this script either: it refuses inside a Claude Code session, as gate.py --close-escalation does.
A hook sees the command an agent types, never one run from a script, so the check is here.

Exit 0: applied (or the live file already was the proposal). 1: the check refused the proposal
(the live file untouched) or the test went red (the previous file is back). 2: refused — inside a session, or not an action of the list. 3: stale — the
proposal is missing or is not the one the sha256 names.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROPOSAL = "docs/tasks/settings.json"
LIVE = ".claude/settings.json"
CHECK = "settings_check.py"  # beside this file: it ships with the engine
TEST = "tests/test_settings_proposal.py"  # the project's own, when it keeps one
EXIT_FAILED, EXIT_REFUSED, EXIT_STALE = 1, 2, 3


def apply_settings(root: Path, approved: str) -> int:
    proposal, live, test = root / PROPOSAL, root / LIVE, root / TEST
    if not (proposal.is_file() and live.is_file()):
        print(f"owner-action: apply-settings needs {PROPOSAL} and {LIVE}; one is missing", file=sys.stderr)
        return EXIT_STALE
    wanted = proposal.read_bytes()
    found = hashlib.sha256(wanted).hexdigest()
    if found != approved:
        print(f"owner-action: {PROPOSAL} is {found}, the owner approved {approved or '(no sha256)'}; not applied", file=sys.stderr)
        return EXIT_STALE
    check = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / CHECK), "--root", str(root)], capture_output=True, text=True, check=False)
    print(check.stdout[-2000:] + check.stderr[-2000:])
    if check.returncode != 0:
        print(f"owner-action: {CHECK} refused the proposal (exit {check.returncode}); {LIVE} is untouched", file=sys.stderr)
        return EXIT_FAILED
    if not test.is_file():
        live.write_bytes(wanted)
        print(f"owner-action: {PROPOSAL} ({found}) applied to {LIVE}; {CHECK} passes")
        return 0
    before = live.read_bytes()
    live.write_bytes(wanted)
    ran = subprocess.run([sys.executable, str(test)], cwd=root, capture_output=True, text=True, check=False)
    print(ran.stdout[-2000:] + ran.stderr[-2000:])
    if ran.returncode != 0:
        live.write_bytes(before)
        print(f"owner-action: {TEST} failed after the copy (exit {ran.returncode}); the previous {LIVE} is back", file=sys.stderr)
        return EXIT_FAILED
    print(f"owner-action: {PROPOSAL} ({found}) applied to {LIVE}; {CHECK} and {TEST} pass")
    return 0


def lessons() -> Any:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
    import lesson_queue

    return lesson_queue


def promote_rule(root: Path, approved: str) -> int:
    queue = lessons()
    ident = queue.proposal_by_sha(root, approved)
    if ident is None:
        print(f"owner-action: no PROPOSED rule proposal has the sha256 {approved or '(none)'}; the owner approved another text", file=sys.stderr)
        return EXIT_STALE
    done, message = queue.promote(root, ident)
    print(f"owner-action: {message}", file=sys.stdout if done else sys.stderr)
    return 0 if done else EXIT_FAILED


def reject_rule(root: Path, declined: str) -> int:
    queue = lessons()
    ident = queue.proposal_by_sha(root, declined)
    if ident is None:
        print(f"owner-action: no PROPOSED rule proposal has the sha256 {declined or '(none)'}; nothing to close", file=sys.stderr)
        return EXIT_STALE
    done, message = queue.reject(root, ident, "ні (the owner's answer on the task board)")
    print(f"owner-action: {message}", file=sys.stdout if done else sys.stderr)
    return 0 if done else EXIT_FAILED


def amend_goals(root: Path, approved: str) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
    import goals

    return goals.amend(root, approved, in_session=False)  # main() has already refused a session


ACTIONS = {"apply-settings": apply_settings, "promote-rule": promote_rule, "reject-rule": reject_rule, "amend-goals": amend_goals}


def main() -> int:
    parser = argparse.ArgumentParser(description="The actions the board runner takes on the owner's word.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("action")
    parser.add_argument("argument", nargs="?", default="")
    args = parser.parse_args()
    if os.environ.get("CLAUDECODE"):
        print("owner-action: the owner's actions are refused inside a Claude Code session (CLAUDECODE is set). "
              "The board runner takes them, started from the owner's terminal or service.", file=sys.stderr)
        return EXIT_REFUSED
    if args.action not in ACTIONS:
        print(f"owner-action: '{args.action}' is not an allowed action ({', '.join(sorted(ACTIONS))})", file=sys.stderr)
        return EXIT_REFUSED
    return ACTIONS[args.action](args.root.resolve(), args.argument.strip("-"))


if __name__ == "__main__":
    sys.exit(main())
