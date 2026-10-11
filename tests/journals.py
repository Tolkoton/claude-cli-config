"""The four journals read whole, for a suite (board 739).

    from journals import journal_text
    journal_text(root, "anomalies")      # tasks/ANOMALIES.md and every session's file, by time
    open_lessons(root)                   # the lesson candidates no resolution line closes, one a line

Every writer of the overseer's ledger, the parked log, the anomaly journal and the lesson queue adds to
its own session's file, `.engine/journal/<journal>/<session>.md`; a suite reads what the engine's
readers read (.claude/hooks/journal.py `text`), never the shared file alone.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_MODULE = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "journal.py"
_spec = importlib.util.spec_from_file_location("journal", _MODULE)
assert _spec is not None and _spec.loader is not None
journal: Any = sys.modules.get("journal") or importlib.util.module_from_spec(_spec)
if "journal" not in sys.modules:
    sys.modules["journal"] = journal   # its dataclass looks itself up there
    _spec.loader.exec_module(journal)


def journal_text(root: str | Path, name: str) -> str:
    return str(journal.text(Path(root), name))


def open_lessons(root: str | Path) -> str:
    """The lesson queue as the agent sees it: the candidates without a `resolved:` line."""
    return "".join(line + "\n" for line in journal.open_candidates(journal.lesson_lines(Path(root))))
