#!/usr/bin/env python3
"""PermissionRequest hook for Edit/Write/MultiEdit: approve writes to the PROJECT'S OWN DATA
under .claude/ — the ledger, the parked queue, the premise log, slice contracts, the feature
DAG, spikes — and decide nothing about anything else.

WHY. With `permissions.defaultMode` in the owner's personal layer rather than the shared
settings file, a session that does not have `acceptEdits` (a cloud session reads no user
settings; a machine without the personal layer) is asked before every write. Most of what
an agent writes under .claude/ is the engine's bookkeeping, and asking a human to approve
every ledger entry is the kind of prompt that makes autonomy impossible while protecting
nothing. The files that DO need protecting — settings.json, settings.local.json,
constitution.md, the hooks, the skills — are owned by `engine` or `machine` in
.claude/ownership.txt, never by `project`, so the owner column is the boundary this hook
enforces: ONLY a path whose owner is `project` is approved. protect-paths.sh still runs
first (PreToolUse) and refuses its protected paths regardless.

ONE PROJECT FILE IS NEVER APPROVED: .claude/project.env. It is project-owned, but it is not
bookkeeping — it is the switchboard of the gates: TEST_CMD, LINT_CMD and TYPECHECK_CMD say
what verify-on-stop runs, SOURCE_DIRS and CODE_EXTENSIONS what it looks at, COMPLEXITY_GATE
and CLOUD_COMMIT_POLICY turn a gate on or off. An unprompted write there could make every
gate pass (`TEST_CMD=true`) with no human seeing it. A person edits it at setup time, rarely,
so the normal prompt is the right price. (Owner review of package 3b, 2026-10-02.)

WHAT COUNTS. The target path is resolved with every symlink and `..` followed
(`Path.resolve()`); it must land inside the real `$CLAUDE_PROJECT_DIR/.claude/` directory,
and its path relative to the project root must match a `project` rule in
`.claude/ownership.txt` (first matching rule wins, as engine.py reads the same file). A path
outside, a symlink that leads outside, a path the map calls `engine`/`machine`/`user`, a
missing or unreadable map, a tool other than the three, an event other than
PermissionRequest: the hook prints nothing and exits 0 — "no decision", and Claude Code's
normal flow continues. It never denies and never fails open.

Model: auto-approve-web.py (the same output shape). The ownership matcher is a copy of
engine.py's compile_pattern/parse rules because engine.py is not shipped into projects.

Standard library only. Exit 0 always.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

TOOLS = ("Edit", "Write", "MultiEdit")
OWNERSHIP = ".claude/ownership.txt"
# Project-owned, but it configures the gates themselves — see the module docstring.
GATE_CONFIG = frozenset({".claude/project.env"})
OWNERS = ("engine", "project", "machine", "user")


def log(msg: str) -> None:
    print(f"[approve-project-data] {msg}", file=sys.stderr)


def compile_pattern(pattern: str) -> re.Pattern[str] | None:
    """engine.py's anchored glob: `*` inside one directory, `**` across, trailing `/` = subtree."""
    if pattern.startswith(("/", "!")) or "\\" in pattern:
        return None
    subtree = pattern.endswith("/")
    body = pattern.rstrip("/")
    out: list[str] = []
    i = 0
    while i < len(body):
        if body.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif body.startswith("**", i):
            out.append(".*")
            i += 2
        elif body[i] == "*":
            out.append("[^/]*")
            i += 1
        elif body[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(body[i]))
            i += 1
    return re.compile(r"\A" + "".join(out) + (r"/.*" if subtree else "") + r"\Z")


def owner_rules(project: Path) -> list[tuple[str, re.Pattern[str]]] | None:
    try:
        text = (project / OWNERSHIP).read_text(encoding="utf-8")
    except OSError:
        return None
    rules: list[tuple[str, re.Pattern[str]]] = []
    for raw in text.splitlines():
        fields = raw.split("#", 1)[0].split()
        if len(fields) not in (2, 3) or fields[0] not in OWNERS:
            continue
        regex = compile_pattern(fields[1])
        if regex is not None:
            rules.append((fields[0], regex))
    return rules or None


def owner_of(rules: list[tuple[str, re.Pattern[str]]], rel: str) -> str | None:
    for owner, regex in rules:
        if regex.match(rel):
            return owner
    return None


def project_root() -> Path | None:
    given = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if not given:
        return None
    root = Path(given)
    return root.resolve() if root.is_dir() else None


def is_project_data(target: str, project: Path, rules: list[tuple[str, re.Pattern[str]]]) -> bool:
    """True only for a path that resolves inside <project>/.claude/ and is `project`-owned."""
    path = Path(target)
    if not path.is_absolute():
        path = project / path
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False
    claude_dir = (project / ".claude").resolve()
    if claude_dir not in resolved.parents:
        return False
    rel = resolved.relative_to(project.resolve()).as_posix()
    if rel in GATE_CONFIG:
        return False
    return owner_of(rules, rel) == "project"


def decide(data: dict[str, Any]) -> dict[str, Any] | None:
    if data.get("hook_event_name") != "PermissionRequest":
        return None
    if data.get("tool_name") not in TOOLS:
        return None
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    target = tool_input.get("file_path") or tool_input.get("path")
    if not isinstance(target, str) or not target:
        return None
    project = project_root()
    if project is None:
        return None
    rules = owner_rules(project)
    if rules is None:
        return None
    if not is_project_data(target, project, rules):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        }
    }


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError) as exc:
        log(f"could not read the request ({exc}); deciding nothing")
        return 0
    if not isinstance(data, dict):
        return 0
    result = decide(data)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
