#!/usr/bin/env python3
"""recheck_parked.py reads an item's auto-resume tokens from its `Unblocks when:` line only.

It once resumed a parked owner item because the entry's Evidence line MENTIONED the `file:`
token syntax (package 3b, S7). A mention is not a condition. Pinned against a temporary
parked.md and DAG, with the script pointed at them through its environment.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/unattended/recheck_parked.py"

HEADER = "# Parked queue\n\n## Parked items\n"
ENTRY = """
## 2026-10-02T00:00:00Z — {item} — PARKED
- Blocked on: something
- Class: human-input
- Evidence: {evidence}
- Unblocks when: {unblocks}
- Continued with: other work
"""


class Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ok   {name}")
        else:
            self.failed += 1
            print(f"  FAIL {name}  {detail[:400]}")


def main() -> int:
    t = Checks()
    src = SCRIPT.read_text(encoding="utf-8")
    t.check("the script anchors its token search on the Unblocks when: line", "Unblocks when:" in src and "UNBLOCKS_RE" in src)

    with tempfile.TemporaryDirectory(prefix="recheck-parked-") as tmp:
        tmp_path = Path(tmp)
        existing = tmp_path / "exists.txt"
        existing.write_text("x", encoding="utf-8")
        parked = tmp_path / "parked.md"
        parked.write_text(
            HEADER
            + ENTRY.format(item="mention-only", evidence=f"the token file:{existing} is only mentioned here", unblocks="a human decides; no token")
            + ENTRY.format(item="real-token", evidence="nothing", unblocks=f"file:{existing} appears")
            + ENTRY.format(item="unmet-token", evidence="nothing", unblocks=f"file:{tmp_path / 'never.txt'} appears")
            + ENTRY.format(item="token-in-wrong-line", evidence=f"file:{existing}", unblocks="the owner runs the command"),
            encoding="utf-8",
        )
        # find how the script locates parked.md: it reads PARKED relative to the repo; run a copy next to a fake tree
        fake = tmp_path / "repo"
        (fake / ".claude/unattended").mkdir(parents=True)
        (fake / ".engine/overseer").mkdir(parents=True)
        (fake / ".claude/unattended/recheck_parked.py").write_text(src, encoding="utf-8")
        (fake / ".engine/overseer/parked.md").write_text(parked.read_text(encoding="utf-8"), encoding="utf-8")
        (fake / ".engine/architecture").mkdir()
        (fake / ".engine/architecture/feature-dag.json").write_text('{"feature": "x", "nodes": []}', encoding="utf-8")
        r = subprocess.run([sys.executable, str(fake / ".claude/unattended/recheck_parked.py")], capture_output=True, text=True, check=False, env={**os.environ}, cwd=fake)
        out = r.stdout
        after = (fake / ".engine/overseer/parked.md").read_text(encoding="utf-8")
        t.check("exit 0", r.returncode == 0, r.stderr)
        t.check("a token mentioned in Evidence does NOT resume the item", "— mention-only — PARKED" in after, out)
        t.check("a token on another line does NOT resume the item", "— token-in-wrong-line — PARKED" in after, out)
        t.check("a met token on the Unblocks line DOES resume the item", "— real-token — RESUMED" in after, out)
        t.check("an unmet token on the Unblocks line leaves the item parked", "— unmet-token — PARKED" in after, out)
        t.check("the summary counts one resume", "1 resumed" in out, out)

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
