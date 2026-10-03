#!/usr/bin/env python3
"""What the board runner remembers about each task, in .claude/state/board/costs.json.

board-runner.sh is a shell loop; everything it must remember across attempts — and across its
own restarts — is kept here, per task: when the task was started (set once, so the twelve-hour
limit is the task's and not the process's), the conversation to continue, how many attempts in
a row made no commit, and what every attempt reported as its cost.

    board_state.py <state-dir> begin  <task>                 make the entry (keeps an existing one)
    board_state.py <state-dir> retry  <task>                 a fresh clock and a fresh count
    board_state.py <state-dir> record <task> <output> <0|1>  book one attempt; 1 = it made a commit.
                                                             prints `limit` when the session only
                                                             answered with a usage-limit notice
    board_state.py <state-dir> get    <task> <field> [cap]   age_sec | session | idle | cost | attempts
                                                             | left (cap minus cost, two decimals)
    board_state.py <state-dir> finish <task> <outcome>       done | blocked: close the entry
    board_state.py <state-dir> report                        one line per task and the total

COST. `total_cost_usd` of a continued conversation is taken to be that conversation's running
total (premise PR-board-02: seen in the operator's log, not provable without a paid call), so a
task costs the sum, over its conversations, of the highest figure each one reported. Every
attempt's raw figure is stored next to its session id: the other reading can be recomputed.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JsonObj = dict[str, Any]
STAMP = "%Y-%m-%dT%H:%M:%SZ"
# The same notice evals/run_audit_scenarios.py looks for. A session that hit the limit answers
# with a short notice and does nothing else; a long reply that merely talks about limits is work.
USAGE_LIMIT = re.compile(r"hit your (?:session|usage|weekly|daily|monthly|\w+) limit|usage limit (?:reached|exceeded)", re.IGNORECASE)
NOTICE_MAX_CHARS = 400


def now() -> str:
    return datetime.now(UTC).strftime(STAMP)


def load(path: Path) -> JsonObj:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"tasks": {}}
    return data if isinstance(data, dict) and isinstance(data.get("tasks"), dict) else {"tasks": {}}


def save(path: Path, data: JsonObj) -> None:
    data["total_cost_usd"] = round(sum(float(t.get("cost_usd", 0.0)) for t in data["tasks"].values()), 4)
    data["updated_utc"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_suffix(".tmp")
    scratch.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    scratch.replace(path)


def entry(data: JsonObj, task: str) -> JsonObj:
    found: JsonObj = data["tasks"].setdefault(task, {})
    found.setdefault("started_utc", now())
    found.setdefault("session_id", "")
    found.setdefault("attempts_without_commit", 0)
    found.setdefault("cost_usd", 0.0)
    found.setdefault("attempts", [])
    return found


def read_output(path: Path) -> tuple[JsonObj | None, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, ""
    try:
        payload = json.loads(text)
    except ValueError:
        return None, text
    return (payload if isinstance(payload, dict) else None), text


def is_limit_notice(payload: JsonObj | None, text: str) -> bool:
    if payload is None:
        return bool(USAGE_LIMIT.search(text[:2000]))
    reply = str(payload.get("result") or "")
    return len(reply) <= NOTICE_MAX_CHARS and bool(USAGE_LIMIT.search(reply))


def cost_of(attempts: list[JsonObj]) -> float:
    highest: dict[str, float] = {}
    for index, attempt in enumerate(attempts):
        key = str(attempt.get("session_id") or f"(no session {index})")
        highest[key] = max(highest.get(key, 0.0), float(attempt.get("reported_usd", 0.0)))
    return round(sum(highest.values()), 4)


def record(found: JsonObj, output: Path, committed: bool) -> bool:
    payload, text = read_output(output)
    limit = is_limit_notice(payload, text)
    reported = (payload or {}).get("total_cost_usd", 0.0)
    session = str((payload or {}).get("session_id") or "")
    found["attempts"].append({
        "utc": now(), "session_id": session, "committed": committed, "limit": limit,
        "reported_usd": float(reported) if isinstance(reported, (int, float)) else 0.0,
        "output": output.name,
    })
    # No session id in the output (not JSON, or an error before a session existed): the next
    # attempt starts a fresh conversation rather than resuming one that may not exist.
    found["session_id"] = session
    found["cost_usd"] = cost_of(found["attempts"])
    if committed:
        found["attempts_without_commit"] = 0
    elif not limit:
        found["attempts_without_commit"] = int(found["attempts_without_commit"]) + 1
    return limit


def get(found: JsonObj, field: str, cap: str) -> str:
    if field == "age_sec":
        started = datetime.strptime(str(found["started_utc"]), STAMP).replace(tzinfo=UTC)
        return str(int((datetime.now(UTC) - started).total_seconds()))
    if field == "session":
        return str(found["session_id"])
    if field == "idle":
        return str(int(found["attempts_without_commit"]))
    if field == "cost":
        return f"{float(found['cost_usd']):.4f}"
    if field == "attempts":
        return str(len(found["attempts"]))
    if field == "left":
        return f"{max(0.0, float(cap) - float(found['cost_usd'])):.2f}"
    raise SystemExit(f"board_state: unknown field {field!r}")


def report(data: JsonObj) -> list[str]:
    lines = []
    for name, found in sorted(data["tasks"].items()):
        lines.append(f"{name}: {float(found.get('cost_usd', 0.0)):.2f} USD, {len(found.get('attempts', []))} attempt(s), "
                     f"{found.get('outcome', 'in work')}")
    lines.append(f"total: {float(data.get('total_cost_usd', 0.0)):.2f} USD")
    return lines


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    path, command, rest = Path(argv[1]) / "costs.json", argv[2], argv[3:]
    data = load(path)
    if command == "report":
        save(path, data)
        print("\n".join(report(data)))
        return 0
    if not rest:
        print(f"board_state: {command} needs a task", file=sys.stderr)
        return 2
    if command == "retry":
        old = data["tasks"].get(rest[0], {})
        data["tasks"][rest[0]] = {"cost_usd": old.get("cost_usd", 0.0), "attempts": old.get("attempts", [])}
    found = entry(data, rest[0])
    if command in ("begin", "retry"):
        pass
    elif command == "record" and len(rest) == 3:
        if record(found, Path(rest[1]), rest[2] == "1"):
            print("limit")
    elif command == "get" and len(rest) >= 2:
        print(get(found, rest[1], rest[2] if len(rest) > 2 else "0"))
        return 0
    elif command == "finish" and len(rest) == 2:
        found["outcome"], found["finished_utc"] = rest[1], now()
    else:
        print(f"board_state: cannot {command} {' '.join(rest)}", file=sys.stderr)
        return 2
    save(path, data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
