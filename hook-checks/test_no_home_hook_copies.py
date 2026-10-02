#!/usr/bin/env python3
"""Nothing the engine ships puts a hook under ~/.claude/, and no hook goes quiet because
another copy of it exists.

Claude Code runs the same hook handler once per event only when the two settings files
wire it with an IDENTICAL command string; a home-level copy wired as `~/.claude/hooks/x.sh`
next to the project's `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh` runs twice. The source of
such copies — the claude-autonomy skill's user scope — is retired (package 3c); engine.py
installs into projects only. Pinned here:

- no shipped script or installer writes under a home `.claude/hooks` (install.sh links
  skills only; engine.py's --personal merges a settings file that must not carry hooks);
- the personal layer wires no hooks and `engine.py install --personal` refuses one that does
  (pinned in test_personal_layer.py; re-asserted here on the file);
- no engine hook contains stand-down logic or its override;
- the retired skill is gone, and nothing points at it.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
FORBIDDEN = ("engine_stand_down", "ENGINE_HOOK_ALWAYS_RUN", "STOOD_DOWN")
HOME_HOOKS_WRITE = re.compile(r"~/\.claude/hooks|\$HOME/\.claude/hooks|CLAUDE_HOME[^\n]*hooks")


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
            print(f"  FAIL {name}  {detail[:500]}")


def main() -> int:
    t = Checks()
    for rel in ("install.sh", "engine.py"):
        # code only: a comment may recall the history (install.sh does), code may not do it
        code = "\n".join(l for l in (ROOT / rel).read_text(encoding="utf-8").splitlines() if not l.strip().startswith("#"))
        t.check(f"{rel} never writes under a home .claude/hooks", not HOME_HOOKS_WRITE.search(code))
    personal = json.loads((ROOT / "user/settings.json").read_text(encoding="utf-8"))
    t.check("user/settings.json wires no hooks", "hooks" not in personal)
    for f in sorted(p for p in HOOKS.iterdir() if p.suffix in (".sh", ".py")):
        text = f.read_text(encoding="utf-8")
        hits = [w for w in FORBIDDEN if w in text]
        t.check(f"no stand-down logic in {f.relative_to(ROOT)}", not hits, str(hits))
    t.check("the claude-autonomy skill is gone", not (ROOT / ".claude/skills/claude-autonomy").exists())
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")
    live = []
    for rel in tracked:
        if not rel or rel.startswith(("docs/plan/", "evals/baseline/", ".engine/architecture/archive/", ".engine/architecture/feature/engine-package-3")):
            continue
        if rel in (".engine/overseer/ledger.md", ".engine/overseer/escalations.md", ".engine/overseer/parked.md", ".engine/architecture/feature-dag.json", ".claude/unattended/unattended-decisions.md", "docs/engine-limits.md", ".claude/references/permission-philosophy.md", "hook-checks/test_no_home_hook_copies.py"):
            continue
        p = ROOT / rel
        if p.suffix in (".md", ".py", ".sh", ".json", ".txt") and p.is_file() and "claude-autonomy" in p.read_text(encoding="utf-8", errors="replace"):
            live.append(rel)
    t.check("no live file still points at the retired skill (closed records excepted)", not live, str(live))
    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
