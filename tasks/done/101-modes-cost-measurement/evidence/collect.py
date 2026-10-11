#!/usr/bin/env python3
"""Board 101: read what the three sandbox runs of run-modes.sh left and print the measured numbers.

    python3 tasks/done/101-modes-cost-measurement/evidence/collect.py <work-dir> [--json]

Per mode: the runner's costs.json (cost, attempts), every attempt's own result (duration, turns,
model usage) from .claude/state/board/logs/, and — from the transcripts Claude Code keeps under
~/.claude/projects/ for the sandbox directory — every subagent the session started, by agent type.
Nothing here is an estimate: a figure that a file does not hold is printed as `-`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

MODES = ("sketch", "sketch-question", "solo", "pipeline")


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def transcripts(box: Path) -> list[Path]:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(box))
    return sorted((Path.home() / ".claude" / "projects" / slug).glob("*.jsonl"))


def agents_started(paths: list[Path]) -> dict[str, dict[str, Any]]:
    """agent type -> how many were started and, from each one's result as the session got it,
    its seconds, tokens and model. The transcript holds no dollar figure per subagent."""
    found: dict[str, dict[str, Any]] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
                content = (row.get("message") or {}).get("content")
            except (ValueError, AttributeError):
                continue
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                    kind = str((block.get("input") or {}).get("subagent_type") or "general-purpose")
                    found.setdefault(kind, {"started": 0, "runs": []})["started"] += 1
            result = row.get("toolUseResult")
            if isinstance(result, dict) and "agentType" in result and "totalTokens" in result:
                found.setdefault(str(result["agentType"]), {"started": 0, "runs": []})["runs"].append({
                    "seconds": round(float(result.get("totalDurationMs", 0)) / 1000),
                    "tokens": result.get("totalTokens"),
                    "model": result.get("resolvedModel"),
                })
    return found


def measure(work: Path, mode: str) -> dict[str, Any]:
    box = work / mode
    state = box / ".claude" / "state" / "board"
    costs = (load(state / "costs.json") or {}).get("tasks", {})
    attempts = []
    for log in sorted(state.glob("logs/*.json"), key=lambda p: int(re.findall(r"-(\d+)\.json$", p.name)[0])):
        got = load(log) or {}
        attempts.append({
            "log": log.name,
            "total_cost_usd": got.get("total_cost_usd"),
            "duration_min": round(got["duration_ms"] / 60000, 1) if "duration_ms" in got else None,
            "num_turns": got.get("num_turns"),
            "models": {name: round(float(use.get("costUSD", 0.0)), 2) for name, use in (got.get("modelUsage") or {}).items()},
        })
    started = (work / f"{mode}.started").read_text().strip() if (work / f"{mode}.started").exists() else None
    ended = (work / f"{mode}.ended").read_text().strip() if (work / f"{mode}.ended").exists() else None
    return {
        "mode": mode,
        "status": (state / "status").read_text().strip() if (state / "status").exists() else None,
        "task_cost_usd": {name: found.get("cost_usd") for name, found in costs.items()},
        "attempts": attempts,
        "session_minutes": round(sum(a["duration_min"] or 0 for a in attempts), 1),
        "wall": [started, ended],
        "agents_started": agents_started(transcripts(box)),
        "task_ended_in": [str(p.relative_to(box)) for p in box.glob("tasks/*/010-split-evenly*") if p.parent.name != "todo"],
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    rows = [measure(Path(argv[1]), mode) for mode in MODES if (Path(argv[1]) / mode).is_dir()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
