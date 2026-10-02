#!/usr/bin/env python3
"""approve-project-data.py approves a write ONLY to a `project`-owned path under the
session repository's .claude/, and decides nothing about anything else.

Every path class, against a temporary project carrying this repository's real
.claude/ownership.txt:

- project-owned data under .claude/ (ledger, parked, premise log, slice contract, feature DAG,
  spike): APPROVED; project.env is NOT, it switches the gates — relative and absolute spellings;
- engine-owned (settings.json, a hook, a skill, constitution.md), machine-owned
  (settings.local.json, overseer/mode), outside .claude/ (src/app.py, CLAUDE.md): NO decision;
- `..` that escapes .claude/, `..` that stays inside, a symlink under .claude/overseer/ that
  points outside the project, a symlinked directory that points outside, a path through a
  symlinked .claude/ itself: NO decision except where the RESOLVED path is still project data;
- a tool other than Edit/Write/MultiEdit, an event other than PermissionRequest, a missing
  CLAUDE_PROJECT_DIR, a project without an ownership map, malformed stdin: NO decision, exit 0.

"No decision" is exit 0 with empty stdout; "approved" is the documented PermissionRequest
shape with behavior allow. The hook never emits deny.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude/hooks/approve-project-data.py"
ALLOW = {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}


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


def run(envelope: Any, project: Path | None, raw: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"]}
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw if raw is not None else json.dumps(envelope),
        capture_output=True, text=True, env=env, check=False, timeout=30,
    )


def envelope(path: str, tool: str = "Edit", event: str = "PermissionRequest") -> dict[str, Any]:
    return {"hook_event_name": event, "tool_name": tool, "tool_input": {"file_path": path}}


def approved(r: subprocess.CompletedProcess[str]) -> bool:
    return r.returncode == 0 and r.stdout.strip() != "" and json.loads(r.stdout) == ALLOW


def no_decision(r: subprocess.CompletedProcess[str]) -> bool:
    return r.returncode == 0 and r.stdout.strip() == ""


def main() -> int:
    t = Checks()
    with tempfile.TemporaryDirectory(prefix="approve-project-data-") as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "proj"
        (project / ".claude/overseer").mkdir(parents=True)
        (project / ".claude/hooks").mkdir()
        (project / "src").mkdir()
        (project / ".claude/ownership.txt").write_bytes((ROOT / ".claude/ownership.txt").read_bytes())
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("x")
        os.symlink(outside / "secret.md", project / ".claude/overseer/link-out.md")
        os.symlink(outside, project / ".claude/overseer/dir-out")
        linked_project = tmp_path / "linked-proj"
        os.symlink(project, linked_project)

        print("approved — project-owned data under .claude/:")
        for rel in (
            ".claude/overseer/ledger.md", ".claude/overseer/parked.md", ".claude/overseer/escalations.md",
            ".claude/overseer/slice/checkout.md", ".claude/premises/premise-log.md",
            ".claude/architecture/feature-dag.json", ".claude/artifacts/spikes/x/notes.md",
        ):
            t.check(f"{rel} (absolute)", approved(run(envelope(str(project / rel)), project)))
        t.check(".claude/overseer/ledger.md (relative to the project)", approved(run(envelope(".claude/overseer/ledger.md"), project)))
        t.check("Write tool", approved(run(envelope(str(project / ".claude/overseer/ledger.md"), tool="Write"), project)))
        t.check("MultiEdit tool", approved(run(envelope(str(project / ".claude/overseer/ledger.md"), tool="MultiEdit"), project)))
        t.check("`..` that stays inside .claude/ and lands on project data", approved(run(envelope(str(project / ".claude/hooks/../overseer/ledger.md")), project)))

        print("no decision — engine, machine, user, outside:")
        for rel in (
            ".claude/settings.json", ".claude/settings.local.json", ".claude/constitution.md",
            ".claude/hooks/block-dangerous.sh", ".claude/skills/overseer/SKILL.md", ".claude/ownership.txt",
            ".claude/overseer/mode", ".claude/overseer/_template.md", ".claude/engine-lock.json",
            "src/app.py", "CLAUDE.md", ".env", "user/settings.json",
        ):
            t.check(f"{rel}", no_decision(run(envelope(str(project / rel)), project)))

        print("no decision — project-owned, but the gates' switchboard:")
        t.check(".claude/project.env (TEST_CMD=true would pass every gate)", no_decision(run(envelope(str(project / ".claude/project.env")), project)))
        t.check(".claude/project.env spelled relative to the project", no_decision(run(envelope(".claude/project.env"), project)))

        print("no decision — escapes:")
        t.check("`..` out of .claude/ to the project root", no_decision(run(envelope(str(project / ".claude/overseer/../../CLAUDE.md")), project)))
        t.check("`..` out of the project entirely", no_decision(run(envelope(str(project / ".claude/../../outside/secret.md")), project)))
        t.check("a symlink under .claude/overseer/ that points outside the project", no_decision(run(envelope(str(project / ".claude/overseer/link-out.md")), project)))
        t.check("a file through a symlinked directory that points outside", no_decision(run(envelope(str(project / ".claude/overseer/dir-out/anything.md")), project)))
        t.check("a project-data path spelled through a symlink to the project resolves and IS approved", approved(run(envelope(str(linked_project / ".claude/overseer/ledger.md")), project)))
        t.check("the same path with CLAUDE_PROJECT_DIR set to the symlink is approved too", approved(run(envelope(str(linked_project / ".claude/overseer/ledger.md")), linked_project)))
        t.check("a path in a DIFFERENT project's .claude/", no_decision(run(envelope(str(outside / ".claude/overseer/ledger.md")), project)))

        print("no decision — not this hook's business:")
        t.check("Bash tool", no_decision(run(envelope(str(project / ".claude/overseer/ledger.md"), tool="Bash"), project)))
        t.check("Read tool", no_decision(run(envelope(str(project / ".claude/overseer/ledger.md"), tool="Read"), project)))
        t.check("PreToolUse event", no_decision(run(envelope(str(project / ".claude/overseer/ledger.md"), event="PreToolUse"), project)))
        t.check("no CLAUDE_PROJECT_DIR", no_decision(run(envelope(str(project / ".claude/overseer/ledger.md")), None)))
        bare = tmp_path / "bare"
        (bare / ".claude/overseer").mkdir(parents=True)
        t.check("a project without an ownership map", no_decision(run(envelope(str(bare / ".claude/overseer/ledger.md")), bare)))
        t.check("malformed stdin", no_decision(run(None, project, raw="{not json")))
        t.check("empty file_path", no_decision(run(envelope(""), project)))
        t.check("never a deny anywhere above (the hook has no deny path)", "deny" not in HOOK.read_text(encoding="utf-8").split('"behavior"')[1][:40])

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
