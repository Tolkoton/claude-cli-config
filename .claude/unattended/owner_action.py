#!/usr/bin/env python3
"""The actions board-runner.sh may take on the owner's word — and it takes no other (board 008).

    owner_action.py [--root DIR] apply-settings <sha256>

`apply-settings` is the one way the shared settings change: the proposal docs/tasks/settings.json
is copied over .claude/settings.json and tests/test_settings_proposal.py is run — the command
the owner would type, `cp docs/tasks/settings.json .claude/settings.json && python3
tests/test_settings_proposal.py`. `<sha256>` is the proposal the owner said «так» to (the agent
wrote it under its question, board.py `action-line`); a proposal that changed since is not the
one that was approved and is not applied. A red test puts the previous file back.

An agent may not edit .claude/settings.json (protect-paths.sh) and may not get there through
this script either: it refuses inside a Claude Code session, as gate.py --close-escalation does.
A hook sees the command an agent types, never one run from a script, so the check is here.

Exit 0: applied (or the live file already was the proposal). 1: the test went red, the previous
file is back. 2: refused — inside a session, or not an action of the list. 3: stale — the
proposal is missing or is not the one the sha256 names.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

PROPOSAL = "docs/tasks/settings.json"
LIVE = ".claude/settings.json"
TEST = "tests/test_settings_proposal.py"
EXIT_FAILED, EXIT_REFUSED, EXIT_STALE = 1, 2, 3


def apply_settings(root: Path, approved: str) -> int:
    proposal, live, test = root / PROPOSAL, root / LIVE, root / TEST
    if not (proposal.is_file() and live.is_file() and test.is_file()):
        print(f"owner-action: apply-settings needs {PROPOSAL}, {LIVE} and {TEST}; one is missing", file=sys.stderr)
        return EXIT_STALE
    wanted = proposal.read_bytes()
    found = hashlib.sha256(wanted).hexdigest()
    if found != approved:
        print(f"owner-action: {PROPOSAL} is {found}, the owner approved {approved or '(no sha256)'}; not applied", file=sys.stderr)
        return EXIT_STALE
    before = live.read_bytes()
    live.write_bytes(wanted)
    ran = subprocess.run([sys.executable, str(test)], cwd=root, capture_output=True, text=True, check=False)
    print(ran.stdout[-2000:] + ran.stderr[-2000:])
    if ran.returncode != 0:
        live.write_bytes(before)
        print(f"owner-action: {TEST} failed after the copy (exit {ran.returncode}); the previous {LIVE} is back", file=sys.stderr)
        return EXIT_FAILED
    print(f"owner-action: {PROPOSAL} ({found}) applied to {LIVE}; {TEST} passes")
    return 0


ACTIONS = {"apply-settings": apply_settings}


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
