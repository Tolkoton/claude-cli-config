#!/usr/bin/env python3
"""overseer_phase.py is the one sanctioned way to set the overseer's phase guard, and the
Stop hook really reads what it writes.

WHY. An agent must not write `.claude/state/` with its own tools (hook-and-script state; the
classifier refuses it). The script is named in the engine rules and used by /plan-slice and
/feature-architect instead of a direct write. This test shows the whole chain: `set plan`
makes overseer_stop._phase_is_plan() true, `clear` makes it false, `show` reports, a bad
argument exits 2, and the commands and rules name the script rather than the file write.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/hooks/overseer_phase.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:400]}")


def load_stop_hook() -> Any:
    spec = importlib.util.spec_from_file_location("overseer_stop", ROOT / ".claude/hooks/overseer_stop.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, check=False)


def main() -> int:
    hook = load_stop_hook()
    phase_is_plan = hook._phase_is_plan
    with tempfile.TemporaryDirectory(prefix="overseer-phase-") as tmp:
        root = Path(tmp)
        check("before anything: no phase, the hook audits", phase_is_plan(root) is False)
        r = run(root, "show")
        check("show with no file prints (none)", r.returncode == 0 and r.stdout.strip() == "(none)", r.stdout + r.stderr)
        r = run(root, "set", "plan")
        check("set plan exits 0 and names the file", r.returncode == 0 and ".claude/state/overseer/state" in r.stdout, r.stdout + r.stderr)
        check("the file holds the phase (mkdir -p on the way)", (root / ".claude/state/overseer/state").read_text(encoding="utf-8") == "plan\n")
        check("the Stop hook now stands down (_phase_is_plan is True)", phase_is_plan(root) is True)
        r = run(root, "show")
        check("show prints plan", r.stdout.strip() == "plan", r.stdout)
        r = run(root, "clear")
        check("clear exits 0 and removes the file", r.returncode == 0 and not (root / ".claude/state/overseer/state").exists(), r.stdout + r.stderr)
        check("the Stop hook audits again (_phase_is_plan is False)", phase_is_plan(root) is False)
        r = run(root, "clear")
        check("clear twice is fine", r.returncode == 0)
        r = run(root, "set", "build")
        check("only `set plan` is accepted (exit 2, usage on stderr)", r.returncode == 2 and "usage" in r.stderr, r.stdout + r.stderr)
        r = run(root)
        check("no argument: exit 2", r.returncode == 2)

    # The text the agent reads names the script, not a direct write of the state file.
    for rel in (".claude/commands/plan-slice.md", ".claude/commands/feature-architect.md", ".claude/engine-rules.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        check(f"{rel} names overseer_phase.py", "overseer_phase.py" in text)
    for rel in (".claude/commands/plan-slice.md", ".claude/commands/feature-architect.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        check(f"{rel} no longer tells the agent to write the state file itself",
              "Write `plan` into `.claude/state/overseer/state`" not in text and "remove `plan` from `.claude/state/overseer/state`" not in text)

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
