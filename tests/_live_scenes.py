"""A copy of the audit scenarios with some scenes put back into LIVE form (prompt A relayed by a
session, prompt B in the same session), for the suites that test the runner's live-scene
bookkeeping: the crash at prompt A, the refused echo, the cost of two sessions.

Since board 018 every real scene is a recorded turn — the audit is done by a separate agent, so
a live relay adds nothing — but the runner still supports live scenes and these suites keep that
path checked.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

SCENARIOS = Path(__file__).resolve().parent.parent / "evals" / "scenarios" / "audit"
TURN_RE = re.compile(r"^## Builder turn[^\n]*\n\n```\n(.*?)\n```\n\n## Prompt B[^\n]*\n\n```\n.*?\n```\n", re.MULTILINE | re.DOTALL)
LIVE_FORM = ("## Prompt A — first message of a fresh session\n\n```\nReply with exactly the text between the markers and "
             "nothing else. Do not use any tools.\n-----BEGIN-----\n{turn}\n-----END-----\n```\n\n"
             "## Prompt B — second message\n\n```\nRun overseer on the last turn.\n```\n")


def live_copy(work: Path, ids: list[str]) -> Path:
    copy = work / "scenarios-live"
    shutil.copytree(SCENARIOS, copy)
    expected = json.loads((copy / "expected.json").read_text(encoding="utf-8"))
    for sid in ids:
        path = copy / f"{sid}.md"
        text = path.read_text(encoding="utf-8")
        found = TURN_RE.search(text)
        assert found, f"{sid}: no recorded turn to put back into live form"
        path.write_text(text[:found.start()] + LIVE_FORM.format(turn=found.group(1)) + text[found.end():], encoding="utf-8")
        del expected[sid]["turn_fixture"]
    (copy / "expected.json").write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return copy
