#!/usr/bin/env python3
"""session-claude.sh starts the headless session with an explicit permission mode.

Since package 3b `defaultMode` lives in the owner's personal layer (~/.claude/settings.json),
which a project does not carry and a cloud session does not read. An unattended session must
not depend on it, so the launcher passes `--permission-mode acceptEdits` itself.

The launcher is run for real against a copy of .claude/unattended/ in a temporary project,
with a shim `claude` first on PATH that records its argv and answers like the CLI's
--output-format json would (the repository's rule for a tool the test must not really run:
a shim that records argv shows the script issuing the right command). The static check on
the live file is kept too, so the assertion survives a refactor of the shim.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNATTENDED = ROOT / ".claude/unattended"
SHIM = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$CLAUDE_SHIM_ARGV"
printf '{"total_cost_usd": 0.0, "result": "shim"}\\n'
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
            print(f"  FAIL {name}  {detail[:500]}")


def main() -> int:
    t = Checks()
    text = (UNATTENDED / "session-claude.sh").read_text(encoding="utf-8")
    t.check("static: the launch line passes --permission-mode acceptEdits", "--permission-mode acceptEdits" in text)
    t.check("static: --dangerously-skip-permissions is still not used", "--dangerously-skip-permissions is NOT used" in text and "\n  --dangerously-skip-permissions" not in text)

    with tempfile.TemporaryDirectory(prefix="session-launch-") as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        shutil.copytree(UNATTENDED, project / ".claude/unattended", ignore=shutil.ignore_patterns("logs", "archive", "*.json", "heartbeat", "*.log", "__pycache__"))
        (project / ".claude/unattended/logs").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        shim_dir = tmp_path / "bin"
        shim_dir.mkdir()
        (shim_dir / "claude").write_text(SHIM, encoding="utf-8")
        (shim_dir / "claude").chmod(0o755)
        argv_file = tmp_path / "argv.txt"
        env = {
            "PATH": f"{shim_dir}:{os.environ['PATH']}",
            "HOME": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(project),
            "CLAUDE_SHIM_ARGV": str(argv_file),
        }
        r = subprocess.run(
            ["bash", str(project / ".claude/unattended/session-claude.sh"), "N1", "say hello"],
            capture_output=True, text=True, env=env, check=False, timeout=60,
        )
        t.check("the launcher ran the shim and exited 0", r.returncode == 0 and argv_file.is_file(), r.stdout + r.stderr)
        argv = argv_file.read_text(encoding="utf-8").splitlines() if argv_file.is_file() else []
        t.check("argv: -p <prompt>", "-p" in argv and argv[argv.index("-p") + 1] == "say hello" if "-p" in argv else False, str(argv))
        t.check(
            "argv: --permission-mode acceptEdits, as two consecutive words",
            "--permission-mode" in argv and argv[argv.index("--permission-mode") + 1] == "acceptEdits" if "--permission-mode" in argv else False,
            str(argv),
        )
        t.check("argv: --output-format json kept", "--output-format" in argv and argv[argv.index("--output-format") + 1] == "json" if "--output-format" in argv else False, str(argv))
        t.check("argv: no --dangerously-skip-permissions", "--dangerously-skip-permissions" not in argv)
        state = project / ".claude/unattended/state.json"
        t.check("the session contract still holds: cost recorded from the shim's JSON", (project / ".claude/unattended/cost.json").is_file() or state.is_file() or "cost=" in r.stdout, r.stdout)
        shim_log = json.loads((project / ".claude/unattended/logs/last-session.json").read_text(encoding="utf-8"))
        t.check("the shim's answer landed where the real CLI's would", shim_log.get("result") == "shim")

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
