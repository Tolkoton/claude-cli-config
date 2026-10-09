"""The engine's pinned tool versions, for a suite that builds a command or a stand-in with them.

    from tool_pins import tool_versions, VERSIONS, spec

    VERSIONS["ruff"]          # "0.17.0"
    spec("pytest")            # "pytest==9.1.1", for `uvx --with`
    tool_versions.command("mypy")

The versions live in .claude/hooks/tool_versions.py (board 107); this only loads that module, so
a suite names the one place and no copy of a version.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_MODULE = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "tool_versions.py"
_spec = importlib.util.spec_from_file_location("tool_versions", _MODULE)
assert _spec is not None and _spec.loader is not None
tool_versions: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool_versions)

VERSIONS: dict[str, str] = tool_versions.VERSIONS
spec = tool_versions.spec
