#!/usr/bin/env python3
"""Merge docs/tasks/lesson-hooks.json into .claude/settings.json — idempotently, nothing else touched.

    python3 docs/tasks/apply-lesson-hooks.py [--settings PATH] [--dry-run]

Appends each hook group of the fragment to the matching event list unless an identical group is
already there. Every other key, hook and permission is left byte-for-byte as it was (the file is
rewritten with the same two-space indent it already uses). A backup `<settings>.bak-lesson-hooks`
is written next to it before the first change. Restart Claude Code afterwards: settings are read
at session start.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FRAGMENT = ROOT / "docs" / "tasks" / "lesson-hooks.json"


def merge(settings: dict[str, object], fragment: dict[str, object]) -> list[str]:
    """Merge in place; returns the list of events that gained a group."""
    added: list[str] = []
    hooks = settings.setdefault("hooks", {})
    assert isinstance(hooks, dict)
    new_hooks = fragment["hooks"]
    assert isinstance(new_hooks, dict)
    for event, groups in new_hooks.items():
        current = hooks.setdefault(event, [])
        for group in groups:
            if group not in current:
                current.append(group)
                added.append(event)
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--settings", type=Path, default=ROOT / ".claude" / "settings.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = json.loads(args.settings.read_text(encoding="utf-8"))
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    added = merge(settings, fragment)
    if not added:
        print("already applied: nothing to change")
        return 0
    print(f"adds a hook group to: {', '.join(added)}")
    if args.dry_run:
        return 0
    shutil.copy2(args.settings, args.settings.with_name(args.settings.name + ".bak-lesson-hooks"))
    args.settings.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written {args.settings}; restart Claude Code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
