#!/usr/bin/env python3
"""Does the Stop hook actually keep the orchestrator going?"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Resolved from this file, not hard-coded: on any machine but the author's the old absolute
# path did not exist, the two MUST-BLOCK cases failed, and the six must-pass cases passed
# vacuously — a hook that is never found never blocks.
HOOK = str(Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "overseer_stop.py")

def run(mode: str | None, status: str | None, msg: str = "ordinary turn, no sentinel", env: dict[str, str] | None = None, count: int | None = None) -> str:
    root = Path(tempfile.mkdtemp())
    (root/".claude/state/overseer").mkdir(parents=True)
    (root/".claude/state/unattended").mkdir(parents=True)
    (root/".engine/overseer").mkdir(parents=True)
    if mode: (root/".claude/state/overseer/mode").write_text(mode)
    if status: (root/".claude/state/unattended/state.json").write_text(json.dumps({"status":status,"node":"S3"}))
    if count is not None: (root/".claude/state/overseer/.continue_count").write_text(str(count))
    e = dict(os.environ); e["CLAUDE_PROJECT_DIR"]=str(root); e.pop("CLAUDE_UNATTENDED_SESSION",None)
    if env: e.update(env)
    r = subprocess.run([sys.executable,HOOK],input=json.dumps({"last_assistant_message":msg}),
                       capture_output=True,text=True,env=e, check=False)
    return r.stdout.strip()

CASES: list[tuple[str, dict[str, Any], bool]] = [
    ("unattended + session working -> MUST BLOCK",      {"mode": "unattended", "status": "working"},      True),
    ("unattended + unit-done       -> MUST BLOCK",      {"mode": "unattended", "status": "unit-done"},    True),
    ("unattended + finished        -> must pass",       {"mode": "unattended", "status": "finished"},     False),
    ("unattended + parked          -> must pass",       {"mode": "unattended", "status": "parked"},       False),
    ("ATTENDED  + session working  -> must pass",       {"mode": "attended", "status": "working"},        False),
    ("no mode file + working       -> must pass",       {"mode": None, "status": "working"},              False),
    ("spawned session (env set)    -> must pass",       {"mode": "unattended", "status": "working", "env": {"CLAUDE_UNATTENDED_SESSION":"1"}},    False),
    ("continue budget exhausted    -> must pass",       {"mode": "unattended", "status": "working", "count": 25},                                 False),
]
fails=[]
for name,kw,should_block in CASES:
    out = run(**kw)
    blocked = '"decision": "block"' in out or '"decision":"block"' in out
    ok = blocked == should_block
    print(f"  {'ok ' if ok else 'FAIL'} {name:44} -> {'BLOCK' if blocked else 'pass'}")
    if not ok: fails.append(name)

if fails:
    print(f"\nFAIL ({len(fails)})"); sys.exit(1)
print(f"\nPASS: {len(CASES)}/{len(CASES)}")
