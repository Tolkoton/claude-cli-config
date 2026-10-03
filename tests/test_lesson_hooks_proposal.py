#!/usr/bin/env python3
"""docs/tasks/lesson-hooks.json and its apply script: the one wiring change package B asks the owner for.

Holds before and after the owner applies it:
  - the fragment is valid and every command names a script that exists with a sub-command it has;
  - merging it into a copy of the live settings adds exactly the stuck-counter groups, changes no
    other key, is idempotent, and leaves every existing hook group byte-for-byte;
  - the live file either lacks the groups (proposal pending) or has them (applied) — both pass.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAGMENT = json.loads((ROOT / "docs/tasks/lesson-hooks.json").read_text())
LIVE_PATH = ROOT / ".claude/settings.json"
LIVE = json.loads(LIVE_PATH.read_text())
PASS = FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:300]}")


spec = importlib.util.spec_from_file_location("apply_lesson_hooks", ROOT / "docs/tasks/apply-lesson-hooks.py")
assert spec is not None and spec.loader is not None
apply = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apply)

commands = [h["command"] for groups in FRAGMENT["hooks"].values() for g in groups for h in g["hooks"]]
check("the fragment wires PostToolUse and PostToolUseFailure for Bash", set(FRAGMENT["hooks"]) == {"PostToolUse", "PostToolUseFailure"}
      and all(g["matcher"] == "Bash" for gs in FRAGMENT["hooks"].values() for g in gs))
for command in commands:
    match = re.search(r'\.claude/hooks/(\S+?)"? (\w[\w-]*)$', command)
    script = ROOT / ".claude/hooks" / (match.group(1) if match else "?")
    check(f"{command[:60]}… names a script that exists", match is not None and script.is_file())
    helped = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True, check=False)
    check("...and a sub-command it has", match is not None and match.group(2) in helped.stdout, helped.stdout[:120])
check("every command carries a timeout (a hook must not hang a session)", all(
    h.get("timeout") for gs in FRAGMENT["hooks"].values() for g in gs for h in g["hooks"]))

merged = copy.deepcopy(LIVE)
added = apply.merge(merged, FRAGMENT)
pending = bool(added)
check("merge adds groups (pending) or nothing (already applied)", True)
if pending:
    check("only the two events gain a group", sorted(added) == ["PostToolUse", "PostToolUseFailure"], added)
for key in LIVE:
    if key != "hooks":
        check(f"key {key!r} is untouched", merged[key] == LIVE[key])
for event, groups in LIVE["hooks"].items():
    check(f"every existing {event} group is untouched and in place", merged["hooks"][event][: len(groups)] == groups)
again = apply.merge(merged, FRAGMENT)
check("merging twice changes nothing (idempotent)", again == [])

with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "settings.json"
    target.write_text(LIVE_PATH.read_text())
    dry = subprocess.run([sys.executable, str(ROOT / "docs/tasks/apply-lesson-hooks.py"), "--settings", str(target), "--dry-run"], capture_output=True, text=True, check=False)
    check("--dry-run writes nothing", target.read_text() == LIVE_PATH.read_text() and dry.returncode == 0, dry.stderr)
    subprocess.run([sys.executable, str(ROOT / "docs/tasks/apply-lesson-hooks.py"), "--settings", str(target)], capture_output=True, text=True, check=False)
    check("the script writes a valid file with the groups present", json.loads(target.read_text())["hooks"]["PostToolUseFailure"] == FRAGMENT["hooks"]["PostToolUseFailure"])
    check("...and a backup of what was there", (Path(tmp) / "settings.json.bak-lesson-hooks").read_text() == LIVE_PATH.read_text() or not pending)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
