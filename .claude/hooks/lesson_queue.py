#!/usr/bin/env python3
"""lesson_queue.py — event-driven self-learning: the queue, its collectors, the review, the stuck counter.

    python3 .claude/hooks/lesson_queue.py add --source agent --slice S "what was non-obvious"
    python3 .claude/hooks/lesson_queue.py collect          # scan the sources, add new candidates
    python3 .claude/hooks/lesson_queue.py list
    python3 .claude/hooks/lesson_queue.py review-request   # the triage request, or nothing
    python3 .claude/hooks/lesson_queue.py resolve ID --to memory|rule|engine|discard [--text T] [--cite C C] [--why W]
    python3 .claude/hooks/lesson_queue.py promote ID       # an overseer-approved proposal -> .engine/rules.md
    python3 .claude/hooks/lesson_queue.py session-start    # hook: a bounded digest, a cleanup proposal
    python3 .claude/hooks/lesson_queue.py cleanup-done
    python3 .claude/hooks/lesson_queue.py stuck            # hook (PostToolUse / PostToolUseFailure): the stuck counter

THE QUEUE. `.engine/lesson-queue.md`, one line per candidate:
    - <date UTC> | <source> | <slice> | <essence> #<id>
source is one of gate, overseer, parked, escalation, agent. A candidate is added once: the id is a
hash of source + the normalised essence, and every id ever seen is kept in machine state
(`.claude/state/lessons/seen.json`), so a candidate that was triaged and removed does not come back
when its source is scanned again. No model is involved in collecting.

THE COLLECTORS (`collect`, called by the Stop gate and the overseer hook): the blocking findings of
`.claude/state/gate/last-report.json`, the PARKED entries of `.engine/overseer/parked.md`, the
non-AUTONOMOUS entries of `.engine/overseer/escalations.md`; the overseer hook adds an
`OVERSEER_BLOCK:` verdict itself (`add_from_verdict`). The agent adds a line when it finds a
non-obvious cause (the rule is in the self-learning-orchestrator skill, not in the persistent context).

THE REVIEW. After an overseer verdict of PASS, `review_request()` is appended to the hook's
"continue" text when the queue is not empty: file each candidate with `resolve` — into the project
memory (`.engine/overseer/MEMORY.md`, which demands two ledger citations), a rule proposal
(`.engine/rule-proposals.md`), feedback for the engine (`.engine/engine-feedback.md`) or discard it.
A resolved candidate leaves the queue.

NEVER INTO THE PERSISTENT CONTEXT AUTOMATICALLY. Nothing here writes CLAUDE.md or `.claude/`.
A proposal becomes a rule only through `promote`, which needs an overseer entry in the ledger that
names it (`rule-proposal <id>`) with OVERSEER_PASS, and refuses when the persistent context would
pass 200 lines. The rule lands in `.engine/rules.md`, which CLAUDE.md imports.

STUCK. The same failure three times in a row (the key is the failure's normalised fingerprint) makes
`stuck` answer with the stuck protocol as additionalContext; a success resets the counter. It never
blocks. The Stop gate and the post-write lint feed the same counter (`note_failure` / `note_success`).

Standard library only; Python 3.11+. Hooks never fail the session: every hook entry exits 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SOURCES = ("gate", "overseer", "parked", "escalation", "agent")
QUEUE_REL = Path(".engine/lesson-queue.md")
MEMORY_REL = Path(".engine/overseer/MEMORY.md")
PROPOSALS_REL = Path(".engine/rule-proposals.md")
FEEDBACK_REL = Path(".engine/engine-feedback.md")
RULES_REL = Path(".engine/rules.md")
LEDGER_REL = Path(".engine/overseer/ledger.md")
STATE_REL = Path(".claude/state/lessons")
GATE_REPORT_REL = Path(".claude/state/gate/last-report.json")
CLEANUP_DAYS = 14
CLEANUP_ENTRIES = 30
DIGEST_LIMIT = 1200
ESSENCE_LIMIT = 200
STUCK_AT = 3
BUDGET = 200
QUEUE_HEADER = (
    "# Lesson queue\n\n"
    "One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks "
    "(gate, overseer, parked, escalation) and by the agent. Triaged with "
    "`python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a "
    "resolved line is removed. Never loaded into the persistent context.\n\n"
)
LINE_RE = re.compile(
    r"^- (?P<date>\d{4}-\d{2}-\d{2}) \| (?P<source>\w+) \| (?P<slice>[^|]*?) \| (?P<essence>.*) #(?P<id>[0-9a-f]{8})$"
)
STUCK_TEXT = (
    "STUCK PROTOCOL: the same failure has now happened {n} times in a row ({what}). Stop retrying the "
    "same fix. Write down what you tried and what actually happens, re-read project memory "
    "(`.engine/overseer/MEMORY.md`), and change the hypothesis, not the wording of the attempt — see "
    ".claude/skills/self-learning-orchestrator/triggers/stuck-protocol.md. If the cause was not "
    "obvious, add it to the lesson queue: `python3 .claude/hooks/lesson_queue.py add --source agent "
    "--slice <slice> \"<cause>\"`. This message never blocks."
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", text.lower())).strip()


def item_id(source: str, essence: str) -> str:
    return hashlib.sha256(f"{source}|{normalise(essence)}".encode()).hexdigest()[:8]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------ state


def state_file(root: Path, name: str) -> Path:
    return root / STATE_REL / name


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def seen_ids(root: Path) -> list[str]:
    ids = load_json(state_file(root, "seen.json")).get("ids", [])
    return [i for i in ids if isinstance(i, str)]


def remember(root: Path, ident: str) -> None:
    ids = seen_ids(root)
    if ident not in ids:
        ids.append(ident)
    write(state_file(root, "seen.json"), json.dumps({"ids": ids[-2000:]}) + "\n")


# ------------------------------------------------------------------ the queue


def entries(root: Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for line in read(root / QUEUE_REL).splitlines():
        match = LINE_RE.match(line)
        if match:
            found.append(match.groupdict())
    return found


def current_slice(root: Path) -> str:
    progress = read(root / ".engine" / "PROGRESS.md")
    for line in progress.splitlines():
        if re.search(r"IN PROGRESS", line, re.IGNORECASE):
            match = re.search(r"[Ss]lice\s+`?([\w.-]+)`?", line)
            if match:
                return match.group(1)
    slices = sorted((root / ".engine" / "slices").glob("*.md"), key=lambda p: p.stat().st_mtime)
    return slices[-1].stem if slices else "-"


def clean_essence(text: str) -> str:
    one = re.sub(r"\s+", " ", text.replace("|", "/").replace("#", "no.")).strip()
    return one[:ESSENCE_LIMIT]


def add(root: Path, source: str, slice_name: str, essence: str) -> str | None:
    """Append one candidate. Returns its id, or None when it is empty or already known."""
    essence = clean_essence(essence)
    if source not in SOURCES or not essence:
        return None
    ident = item_id(source, essence)
    if ident in seen_ids(root) or any(e["id"] == ident for e in entries(root)):
        return None
    text = read(root / QUEUE_REL) or QUEUE_HEADER
    if not text.endswith("\n"):
        text += "\n"
    slice_name = re.sub(r"[|\s]+", "-", slice_name.strip()) or "-"
    write(root / QUEUE_REL, text + f"- {today()} | {source} | {slice_name} | {essence} #{ident}\n")
    remember(root, ident)
    return ident


def collect_gate(root: Path, slice_name: str) -> int:
    report = load_json(root / GATE_REPORT_REL)
    if report.get("layer") != "stop" or report.get("result") not in ("block", "escalated"):
        return 0
    added = 0
    for finding in [f for f in report.get("findings", []) if f.get("severity") == "block"][:3]:
        where = f" {finding.get('file')}:{finding.get('line')}" if finding.get("line") else (
            f" {finding.get('file')}" if finding.get("file") else "")
        if add(root, "gate", slice_name, f"{finding.get('rule')}{where}: {finding.get('message', '')}"):
            added += 1
    return added


def blocks(text: str, header: re.Pattern[str]) -> list[tuple[re.Match[str], str]]:
    heads = list(header.finditer(text))
    return [(m, text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)])
            for i, m in enumerate(heads)]


def bullet(body: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


def collect_parked(root: Path, slice_name: str) -> int:
    header = re.compile(r"^## (?P<ts>\S+) — (?P<item>.+?) — PARKED[ \t]*$", re.MULTILINE)
    added = 0
    for match, body in blocks(read(root / ".engine/overseer/parked.md"), header):
        if add(root, "parked", match["item"], f"{match['item']}: {bullet(body, 'Blocked on') or 'parked'}"):
            added += 1
    return added


def collect_escalations(root: Path, slice_name: str) -> int:
    header = re.compile(r"^## (?P<ts>\S+) — (?P<kind>[A-Z_]+)(?: \([^)]*\))? — (?P<title>.+?)[ \t]*$", re.MULTILINE)
    added = 0
    for match, body in blocks(read(root / ".engine/overseer/escalations.md"), header):
        if match["kind"] == "AUTONOMOUS":
            continue
        detail = bullet(body, "Decision") or bullet(body, "Why not escalated")
        if add(root, "escalation", slice_name, f"{match['kind']} {match['title']}" + (f": {detail}" if detail else "")):
            added += 1
    return added


def collect(root: Path) -> int:
    """Scan every automatic source. No model, no network; safe to call on every Stop."""
    slice_name = current_slice(root)
    return (collect_gate(root, slice_name) + collect_parked(root, slice_name)
            + collect_escalations(root, slice_name))


VERDICT_BLOCK_RE = re.compile(r"^[ \t]*OVERSEER_BLOCK:\s*(?P<why>.+?)[ \t]*$", re.MULTILINE)


def add_from_verdict(root: Path, message: str) -> int:
    """An OVERSEER_BLOCK verdict on its own line becomes a candidate."""
    match = VERDICT_BLOCK_RE.search(message)
    if not match:
        return 0
    return 1 if add(root, "overseer", current_slice(root), f"BLOCK {match['why']}") else 0


# ------------------------------------------------------------------ the review


def review_request(root: Path) -> str:
    queue = entries(root)
    if not queue:
        return ""
    shown = "\n".join(f"  #{e['id']}  {e['date']}  [{e['source']}] {e['slice']}: {e['essence'][:110]}" for e in queue[:12])
    more = f"\n  … and {len(queue) - 12} more (`lesson_queue.py list`)" if len(queue) > 12 else ""
    return (
        f"LESSON_REVIEW_REQUESTED — {len(queue)} candidate(s) in .engine/lesson-queue.md. Triage them now, "
        "briefly, before the next unit (a candidate with no lasting value: discard it):\n"
        f"{shown}{more}\n"
        "For each: `python3 .claude/hooks/lesson_queue.py resolve <id> --to <where> ...` with where = "
        "memory (project memory; needs --text and two --cite ledger entries), rule (a proposal for a standing "
        "rule; needs --text and --why), engine (feedback for the engine's own repository; --text) or "
        "discard. A resolved candidate leaves the queue. A rule proposal reaches the persistent context only "
        "after the overseer passes it (`promote`); never edit CLAUDE.md for it."
    )


def remove_line(root: Path, ident: str) -> None:
    kept = [ln for ln in read(root / QUEUE_REL).splitlines() if not ln.endswith(f"#{ident}")]
    write(root / QUEUE_REL, "\n".join(kept) + "\n")


def append(path: Path, text: str, header: str = "") -> None:
    existing = read(path) or header
    if existing and not existing.endswith("\n"):
        existing += "\n"
    write(path, existing + text)


def resolve(root: Path, ident: str, to: str, text: str, cite: list[str], why: str) -> tuple[bool, str]:
    found = [e for e in entries(root) if e["id"] == ident]
    if not found:
        return False, f"no candidate #{ident} in the queue"
    entry = found[0]
    origin = f"lesson #{ident} ({entry['source']}, {entry['slice']}, {entry['date']})"
    if to == "memory":
        if not text or len(cite) < 2:
            return False, "memory needs --text and at least two --cite ledger entries (date + slice): the file's citation-or-prune rule"
        append(root / MEMORY_REL, f"\n## {today()} — {text.splitlines()[0][:90]}\n\n{text}\n\nCited: {'; '.join(cite)}. Origin: {origin}.\n")
    elif to == "rule":
        if not text or not why:
            return False, "a rule proposal needs --text (the rule, imperative, one line) and --why"
        append(root / PROPOSALS_REL, f"\n## RP-{ident} — {today()} — PROPOSED\n- Rule: {text.splitlines()[0]}\n- Why: {why}\n- From: {origin}\n"
               "- Status: PROPOSED (the overseer reviews it; `lesson_queue.py promote` needs its PASS in the ledger)\n",
               "# Rule proposals\n\nCandidates for the standing rules. Never loaded into the persistent context; "
               "approved ones are promoted into `.engine/rules.md`.\n")
    elif to == "engine":
        if not text:
            return False, "engine feedback needs --text"
        append(root / FEEDBACK_REL, f"\n## {today()} — {text.splitlines()[0][:90]}\n\n{text}\n\nFrom: {origin}.\n",
               "# Feedback for the engine\n\nWhat the work learned that belongs in the engine's own repository.\n")
    elif to != "discard":
        return False, "--to must be memory, rule, engine or discard"
    remove_line(root, ident)
    return True, f"#{ident} -> {to}"


def context_lines(root: Path) -> int:
    """Lines of CLAUDE.md and everything it imports (the persistent context), as the budget test counts."""
    imports = re.compile(r"(?:(?<=\s)|^)@([^\s`]+)", re.MULTILINE)
    fence = re.compile(r"^```.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
    span = re.compile(r"`[^`\n]*`")
    seen: list[Path] = []

    def walk(path: Path, hops: int) -> None:
        if path in seen or not path.is_file():
            return
        seen.append(path)
        if hops >= 4:
            return
        for token in imports.findall(span.sub("", fence.sub("", read(path)))):
            target = Path(token.rstrip(".,;:)")).expanduser()
            walk((target if target.is_absolute() else path.parent / target).resolve(), hops + 1)

    walk((root / "CLAUDE.md").resolve(), 0)
    return sum(len(read(p).splitlines()) for p in seen)


def promote(root: Path, ident: str) -> tuple[bool, str]:
    proposals = read(root / PROPOSALS_REL)
    header = re.compile(rf"^## RP-{ident} — (?P<date>\S+) — (?P<state>\w+)[ \t]*$", re.MULTILINE)
    match = header.search(proposals)
    if not match:
        return False, f"no proposal RP-{ident} in {PROPOSALS_REL}"
    if match["state"] != "PROPOSED":
        return False, f"RP-{ident} is already {match['state']}"
    body = proposals[match.end():].split("\n## ", 1)[0]
    rule = bullet(body, "Rule")
    passed = any(re.search(rf"rule-proposal {ident}\b", chunk) and "OVERSEER_PASS" in chunk
                 for chunk in re.split(r"(?m)^(?=## )", read(root / LEDGER_REL)))
    if not passed:
        return False, f"the ledger has no overseer entry naming `rule-proposal {ident}` with OVERSEER_PASS — the overseer reviews proposals first"
    rules_path = root / RULES_REL
    before = read(rules_path) or "# Rules approved from lessons\n\nPromoted by `lesson_queue.py promote` after an overseer PASS. Each line is a standing rule.\n\n"
    new_text = before.rstrip("\n") + f"\n- {rule} (RP-{ident}, {today()})\n"
    original = read(rules_path)
    write(rules_path, new_text)
    if context_lines(root) > BUDGET:
        if original:
            write(rules_path, original)
        else:
            rules_path.unlink()
        return False, f"promoting would take the persistent context past {BUDGET} lines — trim .engine/rules.md first"
    write(root / PROPOSALS_REL, proposals.replace(match.group(0), f"## RP-{ident} — {match['date']} — APPROVED", 1))
    return True, f"RP-{ident} promoted into {RULES_REL}"


# ------------------------------------------------------------------ session start


def last_cleanup(root: Path) -> datetime | None:
    stamp = load_json(state_file(root, "cleanup.json")).get("last_utc")
    try:
        return datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def mark_cleanup(root: Path) -> None:
    write(state_file(root, "cleanup.json"), json.dumps({"last_utc": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")}) + "\n")


def cleanup_due(root: Path) -> str:
    """The reason to propose the clean-up protocol, or "". The first call only starts the clock."""
    count = len(entries(root))
    if count > CLEANUP_ENTRIES:
        return f"{count} candidates in the queue (over {CLEANUP_ENTRIES})"
    last = last_cleanup(root)
    if last is None:
        mark_cleanup(root)
        return ""
    age = (utc_now() - last).days
    has_material = count or re.search(r"^## \d{4}-", read(root / MEMORY_REL), re.MULTILINE)
    if age > CLEANUP_DAYS and has_material:
        return f"{age} days since the last clean-up (over {CLEANUP_DAYS})"
    return ""


def digest(root: Path) -> str:
    lines: list[str] = []
    queue = entries(root)
    memory = [ln[3:].strip() for ln in read(root / MEMORY_REL).splitlines() if re.match(r"^## \d{4}-\d{2}-\d{2}", ln)]
    proposals = len(re.findall(r"^## RP-\w+ — \S+ — PROPOSED", read(root / PROPOSALS_REL), re.MULTILINE))
    if memory:
        lines.append("Project memory (.engine/overseer/MEMORY.md), latest: " + " · ".join(m[:70] for m in memory[-4:]))
    if queue:
        lines.append(f"Lesson queue: {len(queue)} candidate(s), oldest {queue[0]['date']} (.engine/lesson-queue.md).")
    if proposals:
        lines.append(f"{proposals} rule proposal(s) wait for the overseer (.engine/rule-proposals.md).")
    due = cleanup_due(root)
    if due:
        lines.append(
            f"MEMORY CLEAN-UP DUE ({due}): run the clean-up protocol — triage the whole queue, prune uncited or "
            "stale entries of .engine/overseer/MEMORY.md and .engine/rules.md (.claude/skills/self-learning-orchestrator/"
            "triggers/periodic-maintenance.md), then `python3 .claude/hooks/lesson_queue.py cleanup-done`."
        )
    if not lines:
        return ""
    text = "## lessons\n" + "\n".join(f"- {ln}" for ln in lines)
    return text if len(text) <= DIGEST_LIMIT else text[: DIGEST_LIMIT - 1] + "…"


# ------------------------------------------------------------------ stuck


def failure_key(text: str) -> str:
    return hashlib.sha256(normalise(text)[:300].encode()).hexdigest()[:12]


def note_failure(root: Path, text: str) -> str:
    """Count an identical failure in a row. Returns the stuck protocol text on the third one."""
    key = failure_key(text)
    state = load_json(state_file(root, "stuck.json"))
    count = int(state.get("count", 0)) + 1 if state.get("key") == key else 1
    if count >= STUCK_AT:
        write(state_file(root, "stuck.json"), json.dumps({"key": key, "count": 0}) + "\n")
        return STUCK_TEXT.format(n=count, what=clean_essence(text)[:90])
    write(state_file(root, "stuck.json"), json.dumps({"key": key, "count": count}) + "\n")
    return ""


def note_success(root: Path) -> None:
    if load_json(state_file(root, "stuck.json")).get("count"):
        write(state_file(root, "stuck.json"), json.dumps({"key": "", "count": 0}) + "\n")


def tool_failure_text(envelope: dict[str, Any]) -> str | None:
    """The failure's text for a PostToolUse / PostToolUseFailure envelope; None for a success."""
    event = str(envelope.get("hook_event_name", ""))
    response = envelope.get("tool_response")
    tool = str(envelope.get("tool_name", ""))
    detail = ""
    if isinstance(response, dict):
        detail = str(response.get("error") or response.get("stderr") or "")
        failed = bool(response.get("is_error")) or response.get("exit_code") not in (None, 0) or (
            bool(response.get("error")))
    else:
        detail = str(response or "")
        failed = False
    if event == "PostToolUseFailure":
        failed = True
        detail = detail or str(envelope.get("error", ""))
    if not failed:
        return None
    command = ""
    tool_input = envelope.get("tool_input")
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or tool_input.get("file_path") or "")
    return f"{tool} {command[:80]} :: {detail[:160]}"


def run_stuck(root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    failure = tool_failure_text(envelope)
    if failure is None:
        note_success(root)
        return {}
    protocol = note_failure(root, failure)
    if not protocol:
        return {}
    event = str(envelope.get("hook_event_name") or "PostToolUse")
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": protocol}}


# ------------------------------------------------------------------ command line


def project_root() -> Path:
    import os
    import subprocess

    given = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if given and Path(given).is_dir():
        return Path(given)
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    return Path(top.stdout.strip()) if top.returncode == 0 and top.stdout.strip() else Path.cwd()


def read_envelope() -> dict[str, Any]:
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("--source", default="agent", choices=SOURCES)
    p_add.add_argument("--slice", default="")
    p_add.add_argument("text", nargs="+")
    for name in ("collect", "list", "review-request", "session-start", "cleanup-done", "stuck"):
        sub.add_parser(name)
    p_res = sub.add_parser("resolve")
    p_res.add_argument("id")
    p_res.add_argument("--to", required=True, choices=("memory", "rule", "engine", "discard"))
    p_res.add_argument("--text", default="")
    p_res.add_argument("--cite", nargs="*", default=[])
    p_res.add_argument("--why", default="")
    p_pro = sub.add_parser("promote")
    p_pro.add_argument("id")
    args = parser.parse_args(argv)
    root = project_root()
    hook_commands = ("session-start", "stuck", "collect")
    try:
        if args.command == "add":
            ident = add(root, args.source, args.slice or current_slice(root), " ".join(args.text))
            print(f"#{ident} added" if ident else "not added (empty, or already known)")
        elif args.command == "collect":
            print(f"{collect(root)} new candidate(s)")
        elif args.command == "list":
            for e in entries(root):
                print(f"#{e['id']} {e['date']} [{e['source']}] {e['slice']}: {e['essence']}")
        elif args.command == "review-request":
            text = review_request(root)
            if text:
                print(text)
        elif args.command == "resolve":
            done, message = resolve(root, args.id.lstrip("#"), args.to, args.text, args.cite, args.why)
            print(message, file=sys.stdout if done else sys.stderr)
            return 0 if done else 1
        elif args.command == "promote":
            done, message = promote(root, args.id.lstrip("#"))
            print(message, file=sys.stdout if done else sys.stderr)
            return 0 if done else 1
        elif args.command == "session-start":
            text = digest(root)
            if text:
                print(text)
        elif args.command == "cleanup-done":
            mark_cleanup(root)
            print("clean-up recorded")
        elif args.command == "stuck":
            output = run_stuck(root, read_envelope())
            if output:
                print(json.dumps(output, ensure_ascii=False))
    except OSError as exc:
        print(f"lesson_queue: {exc}", file=sys.stderr)
        return 0 if args.command in hook_commands else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
