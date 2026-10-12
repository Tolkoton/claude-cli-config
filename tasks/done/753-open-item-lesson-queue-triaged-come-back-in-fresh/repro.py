#!/usr/bin/env python3
"""Board 753: a candidate that stands in the queue from git, triaged in a fresh clone, must not come back.

    python3 repro.py [<engine root>]      # default: the repository this file lies in

Works on a throwaway directory; the engine root only names whose lesson_queue.py is run.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
LQ = ENGINE / ".claude/hooks/lesson_queue.py"
PARKED = "## 2026-10-03T03:00:00Z — S6 — PARKED\n- Blocked on: a credential\n"


def lq(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(root)}
    return subprocess.run([sys.executable, str(LQ), *args], cwd=root, capture_output=True, text=True, env=env, check=False).stdout


def queue(root: Path) -> list[str]:
    return sorted(set(re.findall(r"#([0-9a-f]{8})\b", lq(root, "list"))))


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="r753-"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / ".engine/overseer").mkdir(parents=True)
    (root / "tasks/blocked").mkdir(parents=True)
    (root / ".engine/overseer/parked.md").write_text(PARKED, encoding="utf-8")
    (root / ".engine/overseer/escalations.md").write_text("## 2026-10-03T00:50:00Z — FINDING — open one\n- Decision: x\n", encoding="utf-8")
    # machine A: seeded before the two sources appeared, so its collect queues them
    (root / ".claude/state/lessons").mkdir(parents=True)
    (root / ".claude/state/lessons/seen.json").write_text('{"ids": ["seeded"]}\n', encoding="utf-8")
    lq(root, "collect")
    print("machine A, queued:", queue(root))
    shutil.rmtree(root / ".claude/state")   # the fresh clone: the queue came with git, the machine state did not
    lq(root, "collect")
    print("fresh clone, after the first collect (seeding):", queue(root))
    for ident in queue(root):
        print("  ", lq(root, "resolve", ident, "--to", "discard").strip())
    print("after resolve --to discard:", queue(root))
    lq(root, "collect")
    back = queue(root)
    print("after the next collect:", back, "<- must be empty")
    (root / ".engine/overseer/parked.md").write_text(PARKED + "\n## 2026-10-04T03:00:00Z — S7 — PARKED\n- Blocked on: a new thing\n", encoding="utf-8")
    lq(root, "collect")
    new = queue(root)
    print("after a NEW parked entry and collect:", new, "<- must hold one")
    ok = not back and len(new) == 1
    print("RESULT:", "the triaged candidates stayed out, the new one was queued" if ok else "THE BUG: triaged candidates came back")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
