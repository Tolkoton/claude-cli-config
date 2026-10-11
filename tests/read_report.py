#!/usr/bin/env python3
"""A fake agent's reading of its task's report (board 100), for the suites whose fake agent closes a task.

    python3 tests/read_report.py <task>      run in the project; the report is tasks/done/<task>/report.md

A task that changed no working code closes only with a PASS of the reader on its report
(`mode.py check-close`), so a fake agent that follows the board's manual has its report read before
it moves the task. This goes through the REAL .claude/hooks/reader.py, as a session would: the
request, the guard before the Agent tool, the reader's answer recorded — a PASS. Exit 0 when the
PASS is in the reader's journal, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

READER = Path(__file__).resolve().parent.parent / ".claude/hooks/reader.py"


def reader(args: list[str], envelope: dict[str, object] | None = None) -> str:
    return subprocess.run([sys.executable, str(READER), *args], capture_output=True, text=True, check=False,
                          input=json.dumps(envelope) if envelope else "").stdout


def main(stem: str) -> int:
    rid = reader(["request", stem, "--report"]).rsplit("READER_REQUEST ", 1)[-1].strip()
    reader(["guard"], {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"subagent_type": "reader", "prompt": f"READER_REQUEST {rid}"}})
    reply = {"verdict": "PASS", "reason": "every reference says what the report ascribes to it", "evidence": [f"tasks/done/{stem}/report.md:1"]}
    reader(["record"], {"hook_event_name": "SubagentStop", "agent_type": "reader", "agent_id": "fake", "last_assistant_message": json.dumps(reply)})
    ledger = Path(".engine/reader/ledger.md")
    return 0 if ledger.is_file() and f"— {stem} — READER_PASS" in ledger.read_text(encoding="utf-8") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
