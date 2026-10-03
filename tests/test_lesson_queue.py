#!/usr/bin/env python3
"""Event-driven self-learning (package B): the queue, the collectors, the review, the promotion
path, the session-start digest, the clean-up proposal and the stuck counter — and the hooks that
carry them (the Stop gate, the overseer hook, the SessionStart hook).

Deterministic: a throwaway directory per case, no model, no network.

Run:   python3 tests/test_lesson_queue.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LQ = ROOT / ".claude/hooks/lesson_queue.py"
GATE = ROOT / ".claude/hooks/gate.py"
OVERSEER = ROOT / ".claude/hooks/overseer_stop.py"
ENVCHECK = ROOT / ".claude/hooks/env-check.sh"
PASS = FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:500]}")


def project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="lessons-"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / "CLAUDE.md").write_text("@.engine/rules.md\n")
    (root / ".engine").mkdir()
    (root / ".engine/rules.md").write_text("# Rules approved from lessons\n")
    return root


def run(root: Path, script: Path, *args: str, stdin: Any = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env,
                          input=json.dumps(stdin) if stdin is not None else "", check=False)


def lq(root: Path, *args: str, stdin: Any = None) -> subprocess.CompletedProcess[str]:
    return run(root, LQ, *args, stdin=stdin)


def queue(root: Path) -> list[str]:
    p = root / ".engine/lesson-queue.md"
    return [ln for ln in p.read_text().splitlines() if ln.startswith("- ")] if p.exists() else []


def ids(root: Path) -> list[str]:
    return [ln.rsplit("#", 1)[1] for ln in queue(root)]


# ---------------------------------------------------------------- the queue
print("the queue: one line per candidate, once")
r = project()
added = lq(r, "add", "--source", "agent", "--slice", "s1", "the cache key ignores the locale | so tests pass in CI only")
check("add writes one line: date | source | slice | essence #id",
      len(queue(r)) == 1 and queue(r)[0].startswith(f"- {datetime.now(UTC):%Y-%m-%d} | agent | s1 | the cache key"), queue(r))
check("a '|' in the essence cannot break the line format", queue(r)[0].count(" | ") == 3, queue(r))
lq(r, "add", "--source", "agent", "--slice", "s2", "The cache key ignores the locale / so tests pass in CI only")
check("the same lesson is not added twice (case, spacing and the slice do not matter)", len(queue(r)) == 1, queue(r))
lq(r, "add", "--source", "agent", "--slice", "s1", "run 12 failed after 340 ms")
lq(r, "add", "--source", "agent", "--slice", "s1", "run 99 failed after 5 ms")
check("numbers do not make a duplicate a new lesson", len(queue(r)) == 2, queue(r))
check("an empty essence is refused", "not added" in lq(r, "add", "--source", "agent", "   ").stdout)
check("an unknown source is refused by the parser", lq(r, "add", "--source", "mood", "x").returncode == 2)
discard = ids(r)[0]
lq(r, "resolve", discard, "--to", "discard")
check("a resolved candidate leaves the queue", discard not in ids(r) and len(queue(r)) == 1, queue(r))
added = lq(r, "add", "--source", "agent", "--slice", "s1", "The cache key ignores the locale / so tests pass in CI only")
check("...and does not come back when the same lesson is added again (seen ids are kept)", len(queue(r)) == 1 and "not added" in added.stdout, queue(r))
check("the file says it is never loaded into the persistent context", "persistent context" in (r / ".engine/lesson-queue.md").read_text())

# ---------------------------------------------------------------- the collectors
print("the collectors: gate, parked, escalation, overseer — no model")
r = project()
(r / ".claude/state/gate").mkdir(parents=True)
report = {"layer": "stop", "result": "block", "findings": [
    {"file": "mod.py", "line": 3, "rule": "typecheck", "severity": "block", "message": "bad type"},
    {"file": "mod.py", "line": 9, "rule": "lint", "severity": "warn", "message": "a warning"}]}
(r / ".claude/state/gate/last-report.json").write_text(json.dumps(report))
lq(r, "collect")
check("a Stop block of the gate becomes a candidate (blocking findings only)",
      len(queue(r)) == 1 and "| gate |" in queue(r)[0] and "typecheck mod.py:3: bad type" in queue(r)[0], queue(r))
lq(r, "collect")
check("collecting again adds nothing", len(queue(r)) == 1)
report["result"] = "pass"
(r / ".claude/state/gate/last-report.json").write_text(json.dumps(report))
(r / ".engine/overseer").mkdir(parents=True)
(r / ".engine/overseer/parked.md").write_text(
    "# Parked\n\n## 2026-10-03T01:00:00Z — S5 — PARKED\n- Blocked on: the owner's cloud session\n- Class: human-input\n\n"
    "## 2026-10-03T02:00:00Z — S5 — RESUMED\n- Blocked on: the owner's cloud session\n")
(r / ".engine/overseer/escalations.md").write_text(
    "## 2026-10-03T01:00:00Z — AUTONOMOUS — some-decision\n- Decision: taken\n\n"
    "## 2026-10-03T01:05:00Z — FINDING — the hook swallowed stderr\n- Decision: it needs 2>&1\n\n"
    "## 2026-10-03T01:10:00Z — ESCALATE — a one-way door\n- Why not escalated: n/a\n")
lq(r, "collect")
joined = "\n".join(queue(r))
check("a PARKED entry is collected, its RESUMED twin is not", "| parked | S5 |" in joined and joined.count("| parked |") == 1, joined)
check("escalation entries are collected, AUTONOMOUS decisions are not",
      "FINDING the hook swallowed stderr" in joined and "ESCALATE a one-way door" in joined and "some-decision" not in joined, joined)
lq(r, "collect")
check("a second scan of every source adds no duplicate", len(queue(r)) == 4, queue(r))
before = len(queue(r))
lq(r, "resolve", ids(r)[-1], "--to", "discard")
lq(r, "collect")
check("a triaged candidate is not re-collected from its source", len(queue(r)) == before - 1, queue(r))
spec = importlib.util.spec_from_file_location("lesson_queue", LQ)
assert spec is not None and spec.loader is not None
lesson_queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson_queue)

check("OVERSEER_BLOCK on its own line is a candidate", lesson_queue.add_from_verdict(r, "audit done\nOVERSEER_BLOCK: #1 the RED was never shown\n") == 1)
check("a mention in prose is not", lesson_queue.add_from_verdict(r, "the marker is OVERSEER_BLOCK: #1 x in a sentence") == 0)
check("the candidate carries the overseer source", any("| overseer |" in ln for ln in queue(r)), queue(r))

# ---------------------------------------------------------------- the review
print("the review: files each candidate, never into the persistent context")
r = project()
check("an empty queue asks for nothing", lq(r, "review-request").stdout.strip() == "")
lq(r, "add", "--source", "agent", "--slice", "s1", "ruff's --force-exclude is needed for explicit paths")
lq(r, "add", "--source", "agent", "--slice", "s1", "a second lesson to file")
lq(r, "add", "--source", "agent", "--slice", "s1", "a third lesson for the engine")
lq(r, "add", "--source", "agent", "--slice", "s1", "a fourth, to discard")
a, b, c, d = ids(r)
text = lq(r, "review-request").stdout
check("a non-empty queue produces the triage request with every id", "LESSON_REVIEW_REQUESTED" in text and all(i in text for i in (a, b, c, d)), text)
claude_before = (r / "CLAUDE.md").read_text()
bad = lq(r, "resolve", a, "--to", "memory", "--text", "ruff needs --force-exclude", "--cite", "2026-10-01 s1")
check("memory needs two ledger citations (the file's own rule)", bad.returncode == 1 and a in ids(r), bad.stderr)
ok = lq(r, "resolve", a, "--to", "memory", "--text", "ruff needs --force-exclude for explicit paths", "--cite", "2026-10-01 s1", "2026-10-02 s2")
mem = (r / ".engine/overseer/MEMORY.md").read_text()
check("memory with two citations is written, cited, and leaves the queue",
      ok.returncode == 0 and "Cited: 2026-10-01 s1; 2026-10-02 s2" in mem and a not in ids(r), mem)
check("a rule needs --why", lq(r, "resolve", b, "--to", "rule", "--text", "pass --force-exclude").returncode == 1)
lq(r, "resolve", b, "--to", "rule", "--text", "Pass --force-exclude to ruff for explicit paths.", "--why", "else engine files are judged by project rules")
props = (r / ".engine/rule-proposals.md").read_text()
check("a rule becomes a PROPOSAL, status PROPOSED", f"## RP-{b} —" in props and "PROPOSED" in props and b not in ids(r), props)
lq(r, "resolve", c, "--to", "engine", "--text", "the gate report could list the exact re-run command")
check("engine feedback goes to .engine/engine-feedback.md", "exact re-run command" in (r / ".engine/engine-feedback.md").read_text() and c not in ids(r))
lq(r, "resolve", d, "--to", "discard")
check("the queue is empty after the triage and asks for nothing more", ids(r) == [] and lq(r, "review-request").stdout.strip() == "")
check("a missing id is an error", lq(r, "resolve", "deadbeef", "--to", "discard").returncode == 1)
check("nothing in the persistent context changed: CLAUDE.md and .engine/rules.md are untouched",
      (r / "CLAUDE.md").read_text() == claude_before and (r / ".engine/rules.md").read_text() == "# Rules approved from lessons\n")

print("the promotion path: only an overseer PASS, only inside the budget")
p = lq(r, "promote", b)
check("promote refuses without an overseer entry in the ledger", p.returncode == 1 and "ledger" in p.stderr, p.stderr)
(r / ".engine/overseer/ledger.md").write_text(f"## 2026-10-03T03:00:00Z — rule-proposal {b} — REVIEWED\n- Verdict: OVERSEER_PASS\n")
p = lq(r, "promote", b)
rules = (r / ".engine/rules.md").read_text()
check("with the overseer's PASS the rule lands in .engine/rules.md", p.returncode == 0 and f"(RP-{b}," in rules and "Pass --force-exclude" in rules, p.stderr + rules)
check("the proposal is marked APPROVED", f"## RP-{b} — {datetime.now(UTC):%Y-%m-%d} — APPROVED" in (r / ".engine/rule-proposals.md").read_text())
check("a second promote is refused", lq(r, "promote", b).returncode == 1)
(r / ".engine/rule-proposals.md").write_text((r / ".engine/rule-proposals.md").read_text()
    + "\n## RP-aaaaaaaa — 2026-10-03 — PROPOSED\n- Rule: A rule that does not fit.\n- Why: x\n")
(r / ".engine/overseer/ledger.md").write_text((r / ".engine/overseer/ledger.md").read_text() + "\n## x — rule-proposal aaaaaaaa — R\n- OVERSEER_PASS\n")
(r / "CLAUDE.md").write_text("@.engine/rules.md\n" + "filler\n" * 199)
full = lq(r, "promote", "aaaaaaaa")
check("promotion that would pass 200 lines of persistent context is refused and leaves the file as it was",
      full.returncode == 1 and "A rule that does not fit" not in (r / ".engine/rules.md").read_text(), full.stderr)
(r / "CLAUDE.md").write_text("@.engine/rules.md\n")
(r / ".engine/rule-proposals.md").write_text((r / ".engine/rule-proposals.md").read_text()
    + "\n## RP-bbbbbbbb — 2026-10-03 — PROPOSED\n- Rule: A rule the overseer blocked.\n- Why: y\n")
(r / ".engine/overseer/ledger.md").write_text((r / ".engine/overseer/ledger.md").read_text()
    + "\n## y — rule-proposal bbbbbbbb — BLOCKED\n- Verdict: OVERSEER_BLOCK: #3 not a standing rule\n")
check("a ledger entry that names the proposal but holds no PASS does not approve it",
      lq(r, "promote", "bbbbbbbb").returncode == 1 and "A rule the overseer blocked" not in (r / ".engine/rules.md").read_text())

# ---------------------------------------------------------------- session start
print("session start: a bounded digest, and the clean-up proposal")
r = project()
check("nothing to say: silent", lq(r, "session-start").stdout.strip() == "")
(r / ".engine/overseer").mkdir(parents=True)
(r / ".engine/overseer/MEMORY.md").write_text("# m\n\n## 2026-08-27 — A passing test proves nothing\n\nbody\n\n## 2026-09-01 — Second pattern\n")
lq(r, "add", "--source", "agent", "--slice", "s", "one candidate")
out = lq(r, "session-start").stdout
check("the digest names the memory headings and the queue", "A passing test proves nothing" in out and "Lesson queue: 1 candidate" in out, out)
check("the digest is short and never the memory file itself", len(out) <= 1200 and "body" not in out, len(out))
check("a young queue: no clean-up proposed", "CLEAN-UP" not in out)
for i in range(31):
    lq(r, "add", "--source", "agent", "--slice", "s", f"filler lesson {'x' * i} word{i}a{'b' * i}")
out = lq(r, "session-start").stdout
check("over 30 entries: the clean-up protocol is proposed", "MEMORY CLEAN-UP DUE" in out and "over 30" in out, out)
check("the digest stays bounded with a long queue", len(out) <= 1200, len(out))
r2 = project()
(r2 / ".engine/overseer").mkdir(parents=True)
(r2 / ".engine/overseer/MEMORY.md").write_text("## 2026-08-27 — A pattern\n")
state = r2 / ".claude/state/lessons"
state.mkdir(parents=True)
(state / "cleanup.json").write_text(json.dumps({"last_utc": (datetime.now(UTC) - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")}))
out = lq(r2, "session-start").stdout
check("over 14 days since the last clean-up: proposed", "MEMORY CLEAN-UP DUE" in out and "15 days" in out, out)
lq(r2, "cleanup-done")
check("cleanup-done restarts the clock", "CLEAN-UP" not in lq(r2, "session-start").stdout)
(state / "cleanup.json").write_text(json.dumps({"last_utc": (datetime.now(UTC) - timedelta(days=13)).strftime("%Y-%m-%dT%H:%M:%SZ")}))
check("13 days: not yet", "CLEAN-UP" not in lq(r2, "session-start").stdout)
(r / ".claude").mkdir(exist_ok=True)
(r / ".claude/hooks").symlink_to(ROOT / ".claude/hooks")
env_run = subprocess.run(["bash", str(ENVCHECK)], cwd=r, capture_output=True, text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(r)), check=False)
check("the SessionStart hook (env-check.sh) carries the digest", "## lessons" in env_run.stdout and env_run.returncode == 0, env_run.stdout[:200])
quiet = project()
(quiet / ".claude").mkdir()
(quiet / ".claude/hooks").symlink_to(ROOT / ".claude/hooks")
env_empty = subprocess.run(["bash", str(ENVCHECK)], cwd=quiet, capture_output=True, text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(quiet)), check=False)
check("...and stays silent when there is nothing to say", env_empty.stdout.strip() == "" and env_empty.returncode == 0, env_empty.stdout[:200])

# ---------------------------------------------------------------- stuck
print("stuck: three identical failures, never blocks, a success resets")
r = project()
fail = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "tool_input": {"command": "pytest -x"}, "error": "AssertionError: 3 != 4"}


def stuck(env: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    p = lq(r, "stuck", stdin=env)
    return p, json.loads(p.stdout) if p.stdout.strip() else {}


p1, o1 = stuck(fail)
p2, o2 = stuck(dict(fail, error="AssertionError: 5 != 6"))
check("the first and second identical failure say nothing (numbers are normalised)", o1 == {} and o2 == {} and p1.returncode == 0)
p3, o3 = stuck(fail)
ctx = o3.get("hookSpecificOutput", {}).get("additionalContext", "")
check("the third gives the stuck protocol as additionalContext", "STUCK PROTOCOL" in ctx and "3 times" in ctx and o3["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure", p3.stdout)
check("it never blocks: exit 0 and no decision", p3.returncode == 0 and "decision" not in o3, p3.stdout)
check("it names the protocol file", "stuck-protocol.md" in ctx)
p4, o4 = stuck(fail)
check("after speaking the counter restarts: the fourth is quiet", o4 == {})
stuck(fail)
stuck(dict(fail, error="ImportError: no module named x"))
p, o = stuck(fail)
check("a different failure in between ends the streak (the next identical one is the first again)", o == {})
stuck(fail)
ok_env = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "pytest"}, "tool_response": {"stdout": "ok", "stderr": "", "exit_code": 0}}
stuck(ok_env)
stuck(fail)
p, o = stuck(fail)
check("a success resets the counter (fail, fail, success, fail, fail is not three)", o == {})
bash_fail = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "make"}, "tool_response": {"stderr": "make: *** boom", "exit_code": 2}}
stuck(bash_fail)
stuck(bash_fail)
p, o = stuck(bash_fail)
check("a PostToolUse Bash result with a non-zero exit code counts as a failure too", "STUCK PROTOCOL" in json.dumps(o), p.stdout)
check("garbage on stdin is a quiet no-op", lq(r, "stuck", stdin=None).returncode == 0)

# ---------------------------------------------------------------- the hooks that carry it
print("the hooks that carry it: Stop gate, overseer hook")
r = project()
env_file = r / ".claude/project.env"
env_file.parent.mkdir(parents=True, exist_ok=True)
lint = r / "lint.sh"
lint.write_text("#!/usr/bin/env bash\necho 'mod.py:1:1: E999 broken'\nexit 1\n")
env_file.write_text(f'CODE_EXTENSIONS="py"\nLINT_CMD="bash {lint}"\n')
(r / "mod.py").write_text("x = 1\n")
subprocess.run(["git", "add", "-A"], cwd=r, check=True)
subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "i"], cwd=r, check=True)
(r / "mod.py").write_text("x = 2\n")
stop = run(r, GATE, "--layer", "stop", "--hook", stdin={"stop_hook_active": False, "session_id": "s"})
check("the Stop gate blocks (precondition)", json.loads(stop.stdout).get("decision") == "block", stop.stdout)
check("...and the block reached the lesson queue without a model", any("| gate |" in ln and "E999 broken" in ln for ln in queue(r)), queue(r))
first = list(queue(r))
run(r, GATE, "--layer", "stop", "--hook", stdin={"stop_hook_active": True, "session_id": "s"})
check("the same block again does not duplicate the candidate", queue(r) == first, queue(r))

(r / ".claude/state/lessons/stuck.json").unlink()
for i in range(3):
    last = run(r, GATE, "--layer", "stop", "--hook", stdin={"stop_hook_active": i > 0, "session_id": "t"})
check("the gate hands the stuck protocol over on the third identical block (in the reason or the escalation)",
      "STUCK PROTOCOL" in last.stdout, last.stdout[:300])

r = project()
(r / ".engine/overseer").mkdir(parents=True)
(r / ".claude").mkdir(exist_ok=True)
plain = run(r, OVERSEER, stdin={"last_assistant_message": "work done\nOVERSEER_PASS\n"})
reason_plain = json.loads(plain.stdout)["reason"]
check("PASS with an empty queue: the continue text is exactly what it always was", "LESSON_REVIEW" not in reason_plain and reason_plain.startswith("OVERSEER_PASS recorded."), reason_plain[:120])
lq(r, "add", "--source", "agent", "--slice", "s", "something non-obvious")
(r / ".claude/state/overseer").mkdir(parents=True, exist_ok=True)
for f in (r / ".claude/state/overseer").glob(".last_continue_sha"):
    f.unlink()
withq = run(r, OVERSEER, stdin={"last_assistant_message": "work done again\nOVERSEER_PASS\n"})
reason = json.loads(withq.stdout)["reason"]
check("PASS with a non-empty queue appends the triage request to the continue text",
      reason.startswith("OVERSEER_PASS recorded.") and "LESSON_REVIEW_REQUESTED" in reason and ids(r)[0] in reason, reason[-300:])
run(r, OVERSEER, stdin={"last_assistant_message": "audit\nOVERSEER_BLOCK: #5 scope drifted from the contract\n"})
check("an OVERSEER_BLOCK verdict is queued by the overseer hook", any("| overseer |" in ln and "scope drifted" in ln for ln in queue(r)), queue(r))
check("a verdict turn that is not a PASS gets no review request", "LESSON_REVIEW" not in (run(r, OVERSEER, stdin={"last_assistant_message": "OVERSEER_BLOCK: #6 another\n"}).stdout))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
