#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Stop hook: auto-trigger an overseer 12-check audit on unit completion.

Redesign of the abandoned bash `overseer-on-stop.sh`. The bash hook reconstructed
the last assistant message by parsing the transcript JSONL named in the Stop
envelope — but the transcript is flushed asynchronously, so the hook raced the
writer and read a stale or empty turn (anthropics/claude-code#15813).

Claude Code now ships the finished turn's text directly on the Stop envelope as
`last_assistant_message` (field probe PASS, 2026-05-22 — see
.engine/artifacts/spikes/auto-overseer-redesign-2026-05-22.md). This hook reads that
field for the *completion text* and consults the transcript only for the
*structural tool-use signal*, which is a stable historical record by the time
Stop fires.

TRIGGER — both signals required:
  1. text sentinel: `=== UNIT N COMPLETE ===` on its own line in the message.
  2. tool signal:   in the current turn, an Edit/Write/MultiEdit on a code
                    path (configured via SOURCE_DIRS / CODE_EXTENSIONS in
                    .claude/project.env) AND a Bash verification command
                    (configured via CHECK_CMDS, or built-in broad default).

RECURSION GUARDS — per-branch, by design:
  - Audit-request branch    — `.claude/state/overseer/.last_audit_sha` SHA of last message
                              that requested an audit; same-message re-fire
                              is silent.
  - PASS / CONTINUE branch  — `.claude/state/overseer/.last_continue_sha` SHA of last
                              OVERSEER_PASS message that produced a CONTINUE
                              injection; same-message re-fire is silent.
  - Halt markers (BLOCK / ESCALATE / ADR_REQUIRED / SLICE_AWAITING_OWNER /
    SLICE_COMPLETE) silent-pass — owner takes over.

  An earlier `stop_hook_active`-based "Guard 1" was removed because it
  short-circuited BEFORE the per-branch SHA guards on hook-initiated turns
  (audit-PASS turns and CONTINUE-driven UNIT turns both arrive with
  `stop_hook_active=true`), making both injection branches unreachable in
  the autonomous loop. The per-branch SHAs handle recursion safety for the
  branches they cover.

PHASE GUARD: `.claude/state/overseer/state` containing `plan` suppresses the audit — the
developer is designing, not completing units of work.

Output: `{"decision":"block","reason":...}` on stdout (exit 0) injects the audit
request and continues the turn; empty stdout (exit 0) passes the turn through.

Invoked by Claude Code as `python3 .claude/hooks/overseer_stop.py` (see
.claude/settings.json Stop hooks). The `uv run` shebang only applies when the
file is executed directly; either way it needs no third-party dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

# `=== UNIT 7 COMPLETE ===` on its own line; surrounding horizontal space is
# tolerated so the sentinel survives minor formatting.
UNIT_DONE_RE = re.compile(r"^[ \t]*=== UNIT \d+ COMPLETE ===[ \t]*$", re.MULTILINE)
# An overseer verdict already emitted this turn — recursion guard 3.
#
# ANCHORED TO LINE START, deliberately, exactly as UNIT_DONE_RE above is.
# Before this, `re.compile(r"OVERSEER_PASS\b")` matched the token ANYWHERE in
# the message, including inside prose and code spans. Any turn that documented,
# reviewed, or taught the protocol therefore entered the autonomous continue
# loop — and this repo is the protocol's own template, so those turns are
# routine here. Observed 2026-08-27: a turn that only *described* the markers
# consumed .last_continue_sha and injected a continue instruction against a
# slice that did not exist.
#
# SKILL.md's "Verdict format" section already requires a marker to be "on its
# own line", so this makes the hook enforce what the contract always stated.
# Leading horizontal space is tolerated, matching UNIT_DONE_RE.
_MARKER_PREFIX = r"^[ \t]*OVERSEER_"

# Halt markers — owner takes over, hook silent-passes
HALT_MARKER_RE = re.compile(
    _MARKER_PREFIX + r"(?:BLOCK|ESCALATE|ADR_REQUIRED|SLICE_AWAITING_OWNER|SLICE_COMPLETE)\b",
    re.MULTILINE,
)
# Pass marker — hook re-injects "continue to next unit" (taskmaster pattern)
PASS_MARKER_RE = re.compile(_MARKER_PREFIX + r"PASS\b", re.MULTILINE)
# File-mutating tools — the other half of the tool signal.
EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})

# Built-in broad default: covers Python, JS/TS, Go, Rust, Swift stacks.
_DEFAULT_CHECK_CMDS = "pytest ruff mypy npm jest vitest go cargo swift"


def _get_project_dir() -> Path:
    """Resolve the project root: CLAUDE_PROJECT_DIR → git → CWD.
    Never returns a relative path — always .resolve()d."""
    env_val = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env_val:
        return Path(env_val).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path.cwd()


def _load_project_env(project_dir: Path) -> dict[str, str]:
    """Parse .claude/project.env as KEY="value" or KEY=value lines.
    Prints a stderr warning when the file is absent; returns {} on any error."""
    env_path = project_dir / ".claude" / "project.env"
    result: dict[str, str] = {}
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        print(
            f"⚠ overseer_stop: .claude/project.env not found at {env_path} — "
            "using built-in defaults. See docs/TEMPLATE-SETUP.md.",
            file=sys.stderr,
        )
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        # Strip surrounding quotes (single or double).
        value = raw.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


def _split_list(raw: str) -> list[str]:
    """Split a config list value on commas and/or whitespace, so ".ts,.tsx",
    "ts tsx", and ".ts .tsx" all yield the same tokens. Empty tokens dropped."""
    return [tok for tok in re.split(r"[,\s]+", raw.strip()) if tok]


def _build_check_cmd_re(cfg: dict[str, str]) -> re.Pattern[str]:
    """Build the check-command regex from project config.
    Falls back to the built-in broad default when CHECK_CMDS is empty or
    does not parse into any usable name."""
    raw = cfg.get("CHECK_CMDS", "").strip()
    names = _split_list(raw) if raw else []
    if raw and not names:
        print(
            f"⚠ overseer_stop: CHECK_CMDS='{raw}' did not parse into any usable "
            "command name — falling back to built-in defaults.",
            file=sys.stderr,
        )
    if not names:
        names = _DEFAULT_CHECK_CMDS.split()
    pattern = "|".join(re.escape(n) for n in names)
    return re.compile(rf"\b(?:{pattern})\b")


def _build_source_dirs(cfg: dict[str, str]) -> list[str]:
    """Return the configured source dirs, normalized with trailing slash.
    Empty list means "match any directory" (use CODE_EXTENSIONS fallback)."""
    raw = cfg.get("SOURCE_DIRS", "").strip()
    if not raw:
        return []
    dirs = [tok.rstrip("/") + "/" for tok in _split_list(raw) if tok.rstrip("/")]
    if not dirs:
        print(
            f"⚠ overseer_stop: SOURCE_DIRS='{raw}' did not parse into any usable "
            "directory. Treating as unset — any code-extension match counts.",
            file=sys.stderr,
        )
    return dirs


def _build_code_extensions(cfg: dict[str, str]) -> frozenset[str]:
    """Return the set of code file extensions (without dot).
    Empty set means "match all files"."""
    raw = cfg.get("CODE_EXTENSIONS", "").strip()
    if not raw:
        return frozenset()
    exts = frozenset(
        tok.lstrip(".").lower() for tok in _split_list(raw) if tok.lstrip(".")
    )
    if not exts:
        print(
            f"⚠ overseer_stop: CODE_EXTENSIONS='{raw}' did not parse into any "
            "usable extension. Treating as unset — all edited files count.",
            file=sys.stderr,
        )
    return exts


def _is_code_path(
    file_path: str,
    source_dirs: list[str],
    code_extensions: frozenset[str],
) -> bool:
    """True if the path counts as a code edit for the overseer trigger.

    Decision tree:
    1. If source_dirs is configured: the path must lie under one of them.
    2. If source_dirs is empty: path must match code_extensions (if configured).
    3. If both are empty: any edit counts.

    A source dir (normalized to a trailing slash by _build_source_dirs) matches when
    "/<dir>/" occurs in "/<path>": that covers the relative form (src/foo.py), the absolute
    form Claude Code actually sends (/work/proj/src/foo.py) and a multi-segment entry
    (backend/src, .claude/hooks) alike, and never a look-alike prefix (src2/, srcfoo/).
    Until package 3c's fix round the multi-segment case matched relative paths only, so the
    documented monorepo example was inert in a real session.
    """
    normalized = "/" + file_path.replace("\\", "/").lstrip("/")

    if source_dirs:
        return any(("/" + d) in normalized for d in source_dirs)

    if code_extensions:
        suffix = Path(normalized).suffix.lstrip(".").lower()
        return suffix in code_extensions

    # No constraints configured — any edit counts.
    return True


CONTINUE_REASON = (
    "OVERSEER_PASS recorded. Proceed with the next unit per the active slice plan in .engine/slices/. "
    "Do the next pending UNIT's work (code edits + verification commands), then emit `=== UNIT N COMPLETE ===` on its own line. "
    "If the slice has no more code units (only smoke / G4 owner-driven steps remain), or if you are uncertain what UNIT N is, "
    "emit `OVERSEER_SLICE_AWAITING_OWNER: <reason>` on its own line to halt and request owner input. "
    "If the slice's last code unit is complete and smoke / G4 are next, emit `OVERSEER_SLICE_AWAITING_OWNER: smoke and G4 are owner-driven; awaiting owner walkthrough.`"
)

AUDIT_REASON = (
    "OVERSEER_REQUEST (auto-triggered by the Stop hook on a unit-completion "
    "claim). Before yielding control to the owner:\n"
    "1. Read .claude/skills/overseer/SKILL.md and apply the full 12-check "
    "checklist to the work since your last audit.\n"
    "2. Append the prescribed entry to .engine/overseer/ledger.md before replying.\n"
    "3. Output a verdict on its own line, exactly one of: OVERSEER_PASS | "
    "OVERSEER_BLOCK: #N <reason> | OVERSEER_ESCALATE: <JSON> | "
    "OVERSEER_ADR_REQUIRED: <ADR>. Emitting any OVERSEER_ verdict marker is "
    "what stops this hook re-firing on the next turn."
)
MAX_UNATTENDED_CONTINUES = 25

UNATTENDED_CONTINUE_REASON = (
    "UNATTENDED_CONTINUE. The run is still live ({detail}), so ending the turn "
    "is not one of the three legitimate stops (human-only input; falsified "
    "premise; empty unblocked queue).\n"
    "Do NOT stop to wait for a background task, to report progress, or to let "
    "the owner redirect — unattended, a checkpoint redirects nobody and costs "
    "the whole run.\n"
    "Continue now: take the next unblocked item. If the only thing in flight is "
    "a supervisor session editing the repo, do work that does not race it — "
    "verify a hook's negative case, extend tests/, re-check "
    ".engine/overseer/parked.md, or update .engine/PROGRESS.md.\n"
    "To stop for real, emit an OVERSEER_ halt marker naming which of the three "
    "reasons applies."
)

def _lesson_review(project_dir: Path, message: str) -> str:
    """Package B: after a verdict, feed the lesson queue and (on a PASS) ask for the review.

    An OVERSEER_BLOCK verdict becomes a queue candidate; when the queue is not empty a PASS adds
    the triage request to the "continue" text. Best effort — a problem here never changes the
    verdict handling."""
    try:
        import lesson_queue

        lesson_queue.add_from_verdict(project_dir, message)
        if PASS_MARKER_RE.search(message):
            lesson_queue.collect(project_dir)
            request = lesson_queue.review_request(project_dir, track=True)
            return f"\n\n{request}" if request else ""
    except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    return ""


PASS_REFUSED_REASON = (
    "OVERSEER_PASS_REFUSED. The Stop gate has an open escalation ({scope}; parked {stamp} in "
    ".engine/overseer/parked.md): it blocked several turns in a row, was not satisfied, and handed "
    "the question to a human. Until the owner closes it (`python3 .claude/hooks/gate.py "
    "--close-escalation {stamp}`, refused inside a Claude Code session), a PASS is not accepted for "
    "any work that still holds the escalated files — the gate's finding is unanswered, whatever "
    "the audit found.\n"
    "Do NOT proceed to the next unit of this work, do NOT run that command and do NOT mark the "
    "parked entry yourself. Append a superseding ledger entry for this unit (`— OVERSEER_BLOCK`, "
    "Trigger: gate escalation {stamp} open). Other work can pass only once the escalated files "
    "are out of the unjudged range: set those changes aside uncommitted (`git stash push -- "
    "<files>`) and take the next unblocked item; or — if nothing else can move — end the turn with "
    "`OVERSEER_SLICE_AWAITING_OWNER: gate escalation {stamp} open` on its own line."
)
GATE_OPEN_NOTICE = (
    "\n\nGATE ESCALATION OPEN ({scope}; parked {stamp} in .engine/overseer/parked.md). "
    "OVERSEER_PASS will not be accepted for this work until the owner closes it: audit as usual, "
    "but the verdict cannot be PASS."
)
COLLECTOR_FAILED_NOTICE = (
    "\n\nGATE-ALLOW REVIEW — the collector failed ({error}), so this request does NOT show the "
    "gate exemptions the diff adds. Run `python3 .claude/hooks/gate_allows.py` yourself, or read "
    "the diff for `gate-allow:` markers, and judge every reason before the verdict (check #4)."
)
NO_SLICE = "(none)"


def _open_gate_escalation(project_dir: Path) -> tuple[str, str] | None:
    """(timestamp, scope text) of the Stop gate's open escalation that covers the work a verdict
    would now speak for, or None.

    Package costs. When gate.py gives up after GATE_MAX_BLOCKS blocks in a row it records the
    escalation in .claude/state/gate/escalations.json (and parks an entry for the human). Machine
    state, not the park queue: the queue is the agent's own file, and its template tells the agent
    to mark entries RESUMED. Only `gate.py --close-escalation`, which refuses inside a Claude Code
    session, takes an escalation out of `open`.

    Covers — by FILES, never by the slice's name: the active slice is whatever .engine/PROGRESS.md
    says, and the agent writes that file. An escalation holds while any file the gate blocked on
    is still in the range no accepted PASS has covered (changed since the last one, committed or
    not). An escalation that recorded no file holds for everything. The slice is named in the
    message only."""
    try:
        data = json.loads(
            (project_dir / ".claude" / "state" / "gate" / "escalations.json").read_text(encoding="utf-8")
        )
        entries = [e for e in data.get("open", []) if isinstance(e, dict)]
    except (OSError, ValueError, AttributeError):
        return None
    if not entries:
        return None
    unit: set[str] | None = None
    for entry in entries:
        stamp, raised_in = str(entry.get("stamp", "?")), str(entry.get("slice", NO_SLICE))
        where = f"raised in slice `{raised_in}`" if raised_in != NO_SLICE else "raised outside any slice"
        files = {str(f) for f in entry.get("files") or []}
        if not files:
            return stamp, f"{where}, on no particular file — it covers all work"
        if unit is None:
            try:
                import gate_allows

                unit = gate_allows.unit_files(project_dir)
            except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):
                unit = set(files)  # cannot tell the range: the lock holds rather than opens
        if files & unit:
            return stamp, f"{where}, on " + ", ".join(sorted(files & unit)[:5])
    return None


def _note_refusal(project_dir: Path, stamp: str, message: str) -> None:
    """Keep the refusal where the next reader looks: beside the escalation. Best effort."""
    try:
        import gate

        data = gate.read_escalations(project_dir)
        data["refusals"].append({"stamp": stamp, "utc": gate.utc_now(), "message_sha": _message_digest(message)[:16]})
        data["refusals"] = data["refusals"][-200:]
        gate.write_json(project_dir / gate.ESCALATIONS_REL, data)
    except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):
        pass


def _gate_allow_review(project_dir: Path) -> str:
    """Package costs: the gate exemptions no accepted PASS has seen yet, for the overseer to judge.

    Empty when there are none, so the request text is unchanged for every turn that silenced
    nothing. A collector that fails says so in the request: silence there would read as "none"."""
    try:
        import gate_allows

        listing = gate_allows.render(gate_allows.record_request(project_dir))
    except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return COLLECTOR_FAILED_NOTICE.format(error=f"{type(exc).__name__}: {exc}"[:160])
    return f"\n\n{listing}" if listing else ""


def _settle_request(project_dir: Path, accepted: bool) -> None:
    """What the last audit request showed becomes "judged" only through an accepted PASS; any
    other verdict — a halt marker, a refused PASS — judged nothing and drops the request."""
    try:
        import gate_allows

        if accepted:
            gate_allows.record_pass(project_dir)
        else:
            gate_allows.drop_request(project_dir)
    except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):
        pass


DRY_RUN_REASON = (
    "DRY-RUN: would have blocked — the overseer Stop hook is wired and live. "
    "No real unit-completion was evaluated; this is a smoke-test injection."
)


def _run_has_work(project_dir: Path) -> str | None:
    """Describe live unattended work, or None if there is none.

    Returns None for a session SPAWNED BY the supervisor. Those must be allowed
    to end: a session that finishes a node writes 'unit-done' and exits so the
    supervisor can spawn a fresh one, and a session that dies must leave
    'working' behind so the supervisor detects the death and restarts it.
    Blocking their Stop would break both mechanisms. This branch exists for the
    ORCHESTRATING session only.
    """
    if os.environ.get("CLAUDE_UNATTENDED_SESSION"):
        return None
    try:
        mode = (project_dir / ".claude" / "state" / "overseer" / "mode").read_text(
            encoding="utf-8"
        )
    except OSError:
        return None
    if "unattended" not in mode.lower():
        return None

    state_path = project_dir / ".claude" / "state" / "unattended" / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        status = str(state.get("status", ""))
        if status in ("working", "unit-done"):
            node = state.get("node") or "?"
            return f"supervisor state is {status!r} on node {node}"
    except (OSError, json.JSONDecodeError, ValueError, AttributeError):
        pass

    dag_path = project_dir / ".engine" / "architecture" / "feature-dag.json"
    try:
        nodes = json.loads(dag_path.read_text(encoding="utf-8")).get("nodes", [])
        done = {n["id"] for n in nodes if n.get("status") == "done"}
        for node in nodes:
            if node.get("status") in ("done", "parked"):
                continue
            if all(dep in done for dep in node.get("deps", [])):
                return f"DAG node {node.get('id')!r} is ready and unblocked"
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError):
        pass
    return None


def _continue_count_file(project_dir: Path) -> Path:
    return project_dir / ".claude" / "state" / "overseer" / ".continue_count"


def _read_continue_count(project_dir: Path) -> int:
    try:
        return int(_continue_count_file(project_dir).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _write_continue_count(project_dir: Path, value: int) -> None:
    path = _continue_count_file(project_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{value}\n", encoding="utf-8")
    except OSError:
        pass


def _stop_or_continue(project_dir: Path) -> NoReturn:
    """The former plain `_passthrough()` for turns with nothing to audit.

    Unattended with work still live, ending the turn is not a legitimate stop,
    so block and re-inject. Bounded by MAX_UNATTENDED_CONTINUES so a genuinely
    wedged loop cannot spin forever.
    """
    detail = _run_has_work(project_dir)
    if detail is None:
        _write_continue_count(project_dir, 0)
        _passthrough()
    count = _read_continue_count(project_dir)
    if count >= MAX_UNATTENDED_CONTINUES:
        _write_continue_count(project_dir, 0)
        _passthrough()
    _write_continue_count(project_dir, count + 1)
    _emit_block(UNATTENDED_CONTINUE_REASON.format(detail=detail))


def _emit_block(reason: str) -> NoReturn:
    """Print the block decision and exit 0 — Claude injects `reason` and
    continues the turn."""
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


def _passthrough() -> NoReturn:
    """Exit silently with no decision — the turn ends normally."""
    sys.exit(0)


def _read_envelope() -> dict[str, object]:
    """Parse the Stop envelope from stdin. A malformed or non-object payload
    degrades to an empty envelope, never a crash — a hook must not break a
    turn over bad input."""
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items()}


def _str_field(envelope: dict[str, object], key: str) -> str:
    """Read a string field from the envelope, or `""` if absent / wrong type."""
    value = envelope.get(key)
    return value if isinstance(value, str) else ""


def _is_turn_boundary(record: dict[str, object]) -> bool:
    """True if `record` is a genuine user message — `message.content` is a bare
    string. Tool-result records are `type:user` too but carry a list body, so
    they return False and the reverse scan treats them as transparent."""
    message = record.get("message")
    if not isinstance(message, dict):
        return False
    return isinstance(message.get("content"), str)


def _has_tool_signal(
    transcript_path: str,
    source_dirs: list[str],
    code_extensions: frozenset[str],
    check_cmd_re: re.Pattern[str],
) -> bool:
    """True if the current turn contains BOTH a code-file Edit/Write/MultiEdit
    AND a Bash verification command, as configured in .claude/project.env.

    The transcript is walked in reverse; the current turn is the run of records
    after the most recent genuine user message. Claude Code writes one content
    block per JSONL record, so a turn spans several assistant records.
    """
    if not transcript_path:
        return False
    path = Path(transcript_path)
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False

    saw_code_edit = False
    saw_check_cmd = False
    for raw_line in reversed(lines):
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(record, dict):
            continue
        record_type = record.get("type")
        if record_type == "user":
            if _is_turn_boundary(record):
                break  # start of the current turn — stop scanning.
            continue  # tool-result record — transparent.
        if record_type != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            tool_input = block.get("input")
            if not isinstance(tool_input, dict):
                continue
            if name in EDIT_TOOLS:
                file_path = tool_input.get("file_path")
                if isinstance(file_path, str) and _is_code_path(
                    file_path, source_dirs, code_extensions
                ):
                    saw_code_edit = True
            elif name == "Bash":
                command = tool_input.get("command")
                if isinstance(command, str) and check_cmd_re.search(command):
                    saw_check_cmd = True
        if saw_code_edit and saw_check_cmd:
            return True
    return saw_code_edit and saw_check_cmd


def _phase_is_plan(project_dir: Path) -> bool:
    """True if `.claude/state/overseer/state` exists and names the planning phase."""
    try:
        content = (project_dir / ".claude" / "state" / "overseer" / "state").read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
    return "plan" in content.lower()


def _audit_sha_file(project_dir: Path) -> Path:
    return project_dir / ".claude" / "state" / "overseer" / ".last_audit_sha"


def _message_digest(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def _already_audited(project_dir: Path, message: str) -> bool:
    """True if an audit was already requested for this exact message text."""
    try:
        recorded = _audit_sha_file(project_dir).read_text(encoding="utf-8")
    except OSError:
        return False
    return recorded.strip() == _message_digest(message)


def _record_audit(project_dir: Path, message: str) -> None:
    """Persist this message's digest so the SHA guard suppresses a re-fire."""
    sha_file = _audit_sha_file(project_dir)
    sha_file.parent.mkdir(parents=True, exist_ok=True)
    sha_file.parent.mkdir(parents=True, exist_ok=True)
    sha_file.write_text(_message_digest(message) + "\n", encoding="utf-8")


def _same_continue_message(project_dir: Path, message: str) -> bool:
    """The PASS branch's recursion guard: True when this exact message already got its answer
    (continue, or refused); otherwise records it and returns False."""
    sha_file = project_dir / ".claude" / "state" / "overseer" / ".last_continue_sha"
    digest = _message_digest(message)
    try:
        if sha_file.read_text(encoding="utf-8").strip() == digest:
            return True
    except OSError:
        pass
    try:
        sha_file.parent.mkdir(parents=True, exist_ok=True)
        sha_file.write_text(digest + "\n", encoding="utf-8")
    except OSError:
        pass
    return False


CONTRACT_RE = re.compile(r"\.engine/slices/([\w.-]+)\.md")
SLICE_HEADING_RE = re.compile(r"^##\s+Slice\s+([\w.-]+)", re.MULTILINE)
CONTRACT_CHANGED_REASON = (
    "CONTRACT CHANGED AFTER APPROVAL — no audit was run. The active slice contract {contract} "
    "no longer matches the fingerprint sealed when the planner-critic loop approved it "
    "({fingerprint}). An audit against a moved goalpost proves nothing, so this turn is "
    "ESCALATED instead: append an entry to .engine/overseer/escalations.md naming the "
    "contract, what changed (git diff it), and who changed it; then either restore the "
    "approved contract, or have the OWNER delete the fingerprint and re-plan the slice with "
    "/plan-slice. Do not delete the fingerprint yourself. End the turn with OVERSEER_ESCALATE: "
    '{{"reason": "contract changed after approval", "contract": "{contract}"}}.'
)


def _active_contract(project_dir: Path) -> Path | None:
    """The contract of the slice .engine/PROGRESS.md marks IN PROGRESS — the convention
    complexity_budget.py reads too: a `.engine/slices/<slug>.md` path in that block, else
    the slug from its `## Slice <slug>` heading."""
    progress = project_dir / ".engine" / "PROGRESS.md"
    try:
        text = progress.read_text(encoding="utf-8")
    except OSError:
        return None
    for block in re.split(r"(?=^## )", text, flags=re.MULTILINE):
        if "IN PROGRESS" not in block.upper():
            continue
        named = CONTRACT_RE.search(block)
        heading = SLICE_HEADING_RE.search(block)
        slug = named.group(1) if named else (heading.group(1) if heading else None)
        if slug:
            return project_dir / ".engine" / "slices" / f"{slug}.md"
    return None


def _contract_changed(project_dir: Path) -> tuple[Path, Path] | None:
    """(contract, fingerprint) when the active contract no longer matches its sealed
    fingerprint; None when it matches, has no fingerprint, or there is no active slice."""
    contract = _active_contract(project_dir)
    if contract is None or not contract.is_file():
        return None
    fingerprint = project_dir / ".claude" / "state" / "contracts" / f"{contract.stem}.sha256"
    if not fingerprint.is_file():
        return None
    try:
        recorded = fingerprint.read_text(encoding="utf-8").split()[0]
    except (OSError, IndexError):
        return None
    actual = hashlib.sha256(contract.read_bytes()).hexdigest()
    return None if recorded == actual else (contract, fingerprint)


def main() -> NoReturn:
    # NOTE — `stop_hook_active`-based Guard 1 was removed (see module
    # docstring "RECURSION GUARDS"). It preempted the per-branch SHA
    # idempotency on every hook-initiated turn — making both injection
    # branches (audit-request, PASS→CONTINUE) unreachable in the
    # autonomous loop. Per-branch SHAs at `.claude/state/overseer/.last_audit_sha`
    # and `.claude/state/overseer/.last_continue_sha` are the design's intended
    # recursion guards and are sufficient.
    dry_run = "--dry-run" in sys.argv[1:]
    envelope = _read_envelope()

    if dry_run:
        _emit_block(DRY_RUN_REASON)

    message = _str_field(envelope, "last_assistant_message")

    # Package costs: a PASS is not accepted while the Stop gate's escalation for this slice is
    # open. Decided BEFORE the lesson review — a refused PASS closes no unit, so it triggers no
    # triage. Enforced here, not only asked for in the skill text: the verdict is a model's.
    if PASS_MARKER_RE.search(message) and not HALT_MARKER_RE.search(message):
        escalation = _open_gate_escalation(_get_project_dir())
        if escalation is not None:
            if _same_continue_message(_get_project_dir(), message):
                _passthrough()
            _note_refusal(_get_project_dir(), escalation[0], message)
            _settle_request(_get_project_dir(), accepted=False)
            _emit_block(PASS_REFUSED_REASON.format(stamp=escalation[0], scope=escalation[1]))

    lesson_text = _lesson_review(_get_project_dir(), message)

    # Halt markers — owner takes over, hook silent-passes.
    if HALT_MARKER_RE.search(message):
        _settle_request(_get_project_dir(), accepted=False)
        _passthrough()

    # PASS marker — re-inject "continue to next unit" (taskmaster pattern: keep blocking until slice done)
    if PASS_MARKER_RE.search(message):
        if _same_continue_message(_get_project_dir(), message):
            _passthrough()
        _settle_request(_get_project_dir(), accepted=True)
        print(json.dumps({"decision": "block", "reason": CONTINUE_REASON + lesson_text}))
        sys.exit(0)

    project_dir = _get_project_dir()

    # Phase guard: the developer is planning, not completing units of work.
    if _phase_is_plan(project_dir):
        _passthrough()

    # Guard 2: this exact message already requested an audit.
    if _already_audited(project_dir, message):
        _stop_or_continue(project_dir)

    # Sentinel pre-check — short-circuit before loading config (avoids noisy
    # project.env warning on every turn that has no unit-completion claim).
    if not UNIT_DONE_RE.search(message):
        _stop_or_continue(project_dir)

    # Load project config — only reached when the sentinel is present.
    # Prints a stderr warning if project.env is absent.
    cfg = _load_project_env(project_dir)
    source_dirs = _build_source_dirs(cfg)
    code_extensions = _build_code_extensions(cfg)
    check_cmd_re = _build_check_cmd_re(cfg)

    # Two-signal trigger — sentinel already confirmed above; check tool signal.
    tool_signal = _has_tool_signal(
        _str_field(envelope, "transcript_path"),
        source_dirs,
        code_extensions,
        check_cmd_re,
    )
    if not tool_signal:
        _stop_or_continue(project_dir)

    # Package 3c: the contract the audit would judge against must be the one that was
    # approved. Changed since sealing → escalate, never audit (recorded like an audit so the
    # same message does not fire twice).
    changed = _contract_changed(project_dir)
    if changed is not None:
        contract, fingerprint = changed
        _record_audit(project_dir, message)
        _emit_block(
            CONTRACT_CHANGED_REASON.format(
                contract=contract.relative_to(project_dir).as_posix(),
                fingerprint=fingerprint.relative_to(project_dir).as_posix(),
            )
        )

    _record_audit(project_dir, message)
    request = AUDIT_REASON + _gate_allow_review(project_dir)
    escalation = _open_gate_escalation(project_dir)
    if escalation is not None:
        request += GATE_OPEN_NOTICE.format(stamp=escalation[0], scope=escalation[1])
    _emit_block(request)


if __name__ == "__main__":
    main()
