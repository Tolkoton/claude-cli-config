#!/usr/bin/env python3
"""The hook copies the `claude-autonomy` skill installs must equal the live hooks.

The skill copies `.claude/skills/claude-autonomy/scripts/*.sh` into a project's (or the
home folder's) `.claude/hooks/`. Those copies had drifted 50-190 lines behind the live
hooks, and that is not hypothetical: a machine set up through the skill was measured with
evals/ running path protection that lost every deny to malformed JSON, and a commit check
that a compound command walked past — both fixed in the live hooks long before.

Byte equality, no exceptions: a copy that is "almost" current is the failure mode.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / ".claude" / "hooks"
COPIES = ROOT / ".claude" / "skills" / "claude-autonomy" / "scripts"

stale = []
checked = 0
for copy in sorted(COPIES.glob("*.sh")):
    live = LIVE / copy.name
    checked += 1
    if not live.is_file():
        stale.append(f"{copy.name}: the skill ships a hook that no longer exists in .claude/hooks/")
    elif live.read_bytes() != copy.read_bytes():
        stale.append(f"{copy.name}: differs from the live hook — run: cp {live.relative_to(ROOT)} {copy.relative_to(ROOT)}")

if not checked:
    print("FAIL: no hook copies found — has the skill moved?")
    sys.exit(1)
if stale:
    print("FAIL: claude-autonomy would install stale hooks:")
    for line in stale:
        print(f"  - {line}")
    sys.exit(1)
print(f"PASS: {checked} hook copies identical to the live hooks")
