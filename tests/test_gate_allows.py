#!/usr/bin/env python3
"""gate_allows.py and its two carriers: the overseer sees every new gate exemption.

Package costs, item 1. Deterministic: throwaway git repositories, the real gate.py,
overseer_stop.py and overseer_verdict.py (the overseer agent's answer is fed to the verdict
script as its SubagentStop envelope), no model, no network.

  1. the collector lists the gate-allow markers a diff ADDS — in code comments, in config
     files, in a slice contract — and nothing that merely mentions the word;
  2. the overseer hook puts that list into the audit request package, and nothing when there
     is none;
  3. "new" means not yet judged: a checkpoint commit hides nothing, an accepted PASS moves the
     base, a suppression that rides on a sealed contract's grant is listed where it is used;
  4. while the Stop gate has an open escalation for the work, the overseer's PASS is recorded
     as a BLOCK — and only the owner's command, run outside a Claude Code session, closes it.

Run:   python3 tests/test_gate_allows.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           check=True).stdout.strip())
HOOKS = ROOT / ".claude" / "hooks"
COLLECTOR = HOOKS / "gate_allows.py"
GATE = HOOKS / "gate.py"
OVERSEER = HOOKS / "overseer_stop.py"
VERDICT_SCRIPT = HOOKS / "overseer_verdict.py"
# The overseer's two handlers: without them the Stop hook makes no request (board 033).
WIRED = json.dumps({"hooks": {
    "PreToolUse": [{"matcher": "Agent|Task", "hooks": [{"type": "command", "command": "python3 .claude/hooks/overseer_verdict.py guard"}]}],
    "SubagentStop": [{"matcher": "overseer", "hooks": [{"type": "command", "command": "python3 .claude/hooks/overseer_verdict.py record"}]}]}}) + "\n"
PASS = 0
FAIL = 0

# Built, never written as one literal: this file must stay clean under the guard it tests, and
# the collector run on this repository must not list this file's own strings.
TI = "# type" + ": ignore"
NQ = "# no" + "qa"
GA = "gate" + "-allow:"
SKIP = "pytest.mark" + ".skip"


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str = "c") -> str:
    sh(root, "git", "add", "-A")
    sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message, "--allow-empty")
    return sh(root, "git", "rev-parse", "HEAD").stdout.strip()


def new_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="gate-allows-"))
    sh(root, "git", "init", "-q", "-b", "main")
    (root / ".claude").mkdir()
    # LINT/TYPECHECK/TEST "true": the gate runs, finds nothing, and only the bypass guard speaks.
    (root / ".claude" / "project.env").write_text(
        'CODE_EXTENSIONS="py"\nLINT_CMD="true"\nTYPECHECK_CMD="true"\nTEST_CMD="true"\n')
    (root / ".claude" / "settings.json").write_text(WIRED)
    (root / ".gitignore").write_text(".claude/state/\n_transcript.jsonl\n")
    (root / ".engine" / "overseer").mkdir(parents=True)
    (root / "mod.py").write_text("x = 1\ny = 2\n")
    commit(root, "init")
    return root


def run(script: Path, root: Path, *args: str, stdin: Any = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    env.pop("CLAUDE_UNATTENDED_SESSION", None)
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True,
                          env=env, input=json.dumps(stdin) if stdin is not None else "", check=False)


def collected(root: Path, *args: str) -> list[dict[str, Any]]:
    proc = run(COLLECTOR, root, "--json", *args)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return [{"_unparseable": proc.stdout + proc.stderr}]
    return list(data["allows"])


def keys(items: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [(i.get("file"), i.get("line"), i.get("source"), i.get("what")) for i in items]


# ---------------------------------------------------------------- 1. the collector
print("collector: code")
r = new_repo()
check("a clean diff has no exemption", collected(r) == [], collected(r))
(r / "mod.py").write_text(
    f"x = 1  {TI}  # {GA} the vendored stub ships no types\n"
    f"# {GA} generated table, long lines are the data\n"
    f"y = 2  {NQ}: E501\n"
    f'DOC = "a string that says {GA} nothing at all here"\n'
    f"z = 3  {NQ}  # {GA}\n"
)
got = collected(r)
check("same-line marker: file, line, kind", ("mod.py", 1, "code", "type-ignore") in keys(got), got)
check("marker on the comment line above: attributed to the suppression below it",
      ("mod.py", 2, "code", "noqa") in keys(got), got)
check("a STRING that mentions the marker is not an exemption", all(i["line"] != 4 for i in got), got)
missing = [i for i in got if i["line"] == 5]
check("a marker with NO reason is listed, flagged missing",
      len(missing) == 1 and missing[0]["reason"] == "" and missing[0]["reason_ok"] is False, got)
check("a reason the gate accepts is flagged ok, verbatim",
      got[0]["reason"] == "the vendored stub ships no types" and got[0]["reason_ok"] is True, got[0])
check("exactly three exemptions, in file order", [i["line"] for i in got] == [1, 2, 5], got)

print("collector: only what the diff ADDS")
base = commit(r, "the exemptions are history now")
check("committed markers are not new against HEAD", collected(r) == [], collected(r))
(r / "mod.py").write_text((r / "mod.py").read_text() + f"w = 4  {TI}  # {GA} short one\n")
got = collected(r)
check("one added line, one exemption", keys(got) == [("mod.py", 6, "code", "type-ignore")], got)
check("a reason under the gate's minimum is flagged not ok", got[0]["reason_ok"] is False, got)
(r / "new.py").write_text(f"import os  {NQ}: F401  # {GA} re-exported for the plugin loader\n")
check("an untracked file counts whole", ("new.py", 1, "code", "noqa") in keys(collected(r)), collected(r))
commit(r, "unit 2")
check("--base reaches back over a checkpoint commit",
      len(collected(r, "--base", base)) == 2 and collected(r) == [], collected(r, "--base", base))
bad = run(COLLECTOR, r, "--json", "--base", "no-such-ref")
check("an unknown base is said, exit 2", bad.returncode == 2 and "no-such-ref" in bad.stderr, (bad.returncode, bad.stderr))

print("collector: skip marks, config, contract")
r = new_repo()
(r / "test_mod.py").write_text(
    "import pytest\n\n\n"
    f"@{SKIP}(reason='later')  # {GA} temporarily disabled for now\n"
    "def test_a() -> None:\n    assert True\n")
(r / ".claude" / "project.env").write_text(
    'CODE_EXTENSIONS="py"\nLINT_CMD="true"\nTYPECHECK_CMD="true"\n'
    f'# {GA} the suite needs the network on this machine\nTEST_CMD="true --offline"\n')
(r / ".engine" / "slices").mkdir(parents=True)
(r / ".engine" / "slices" / "tax.md").write_text(
    f"# Slice tax\n\n{GA} type-ignore — the vendored stub has no types\n\nProse about {GA[:-1]} rules.\n")
got = collected(r)
check("a skip mark's exemption is attributed to the skip", ("test_mod.py", 4, "code", "skip") in keys(got), got)
check("a config file's added marker is listed as config", (".claude/project.env", 4, "config", "config") in keys(got), got)
check("a contract's line is listed with the kind it grants",
      (".engine/slices/tax.md", 3, "contract", "type-ignore") in keys(got), got)
check("prose without the colon form is not listed", len(got) == 3, got)
text = run(COLLECTOR, r).stdout
check("the text form names every exemption and asks for a judgement",
      "GATE-ALLOW REVIEW" in text and "test_mod.py:4" in text and "temporarily disabled for now" in text
      and ".engine/slices/tax.md:3" in text and "#4" in text, text)
check("the text form of nothing is nothing", run(COLLECTOR, new_repo()).stdout == "", "")

print("collector: the slice's own base")
r = new_repo()
(r / "mod.py").write_text(f"x = 1  {TI}  # {GA} the vendored stub ships no types\n")
first = commit(r, "unit 1 of the slice")
start = sh(r, "git", "rev-parse", "HEAD~1").stdout.strip()
(r / ".engine" / "slices").mkdir(parents=True)
(r / ".engine" / "slices" / "tax.md").write_text(f"# Slice tax\n\n## Complexity budget\nbase_commit: {start}\n")
(r / ".engine" / "PROGRESS.md").write_text("# PROGRESS\n\n## Slice tax — IN PROGRESS\n")
check("the active contract's base_commit is the base: an earlier unit's exemption is listed",
      ("mod.py", 1, "code", "type-ignore") in keys(collected(r)), collected(r))
(r / ".engine" / "PROGRESS.md").write_text("# PROGRESS\n\n## Slice tax — DONE\n")
check("no active slice: the base is HEAD", all(i["file"] != "mod.py" for i in collected(r)), collected(r))
check("this repository's own tree parses (no crash on real files)", run(COLLECTOR, ROOT, "--json").returncode == 0,
      run(COLLECTOR, ROOT, "--json").stderr)
del first


# ---------------------------------------------------------------- 2. the overseer hook carries the list
def transcript(root: Path, edited: str = "mod.py") -> Path:
    records = [
        {"type": "user", "message": {"role": "user", "content": "finish unit 1"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t0", "name": "Edit",
             "input": {"file_path": str(root / edited), "old_string": "a", "new_string": "b"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "uv run pytest -q"}}]}},
    ]
    path = root / "_transcript.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in records) + "\n")
    return path


def overseer(root: Path, message: str, hook: Path = OVERSEER) -> str:
    """What the Stop hook says to this message."""
    proc = run(hook, root, stdin={"hook_event_name": "Stop", "last_assistant_message": message,
                                  "transcript_path": str(transcript(root))})
    if not proc.stdout.strip():
        return ""
    return str(json.loads(proc.stdout).get("reason", ""))


CLAIMS = 0
GOOD = {"verdict": "PASS", "check": None, "reason": "every claim has its evidence", "evidence": ["mod.py:1"], "category": "none"}
BLOCKED = {"verdict": "BLOCK", "check": 4, "reason": "masked gap — the exemption at mod.py:1", "evidence": ["mod.py:1"], "category": "none"}


def claim(root: Path, hook: Path = OVERSEER) -> str:
    """A unit-completion claim. Returns what the builder is told, then what the request package
    shows the overseer about the gate: the exemptions to judge and the open escalation."""
    global CLAIMS
    CLAIMS += 1
    said = overseer(root, f"Did the work, claim {CLAIMS}.\n\n=== UNIT 1 COMPLETE ===\n", hook)
    try:
        rid = json.loads((root / ".claude/state/overseer/pending.json").read_text())["id"]
        request = json.loads((root / ".claude/state/overseer/requests" / rid / "request.json").read_text())
    except (OSError, ValueError, KeyError):
        return said
    return "\n\n".join(x for x in (said, str(request.get("gate_allows", "")), str(request.get("gate_escalation", ""))) if x)


def answer(root: Path, reply: dict[str, Any] = GOOD, during: Any = None) -> str:
    """The overseer agent is launched for the pending request and answers (`during` runs while it
    audits); returns what the Stop hook then tells the builder."""
    rid = json.loads((root / ".claude/state/overseer/pending.json").read_text())["id"]
    run(VERDICT_SCRIPT, root, "guard", stdin={"hook_event_name": "PreToolUse", "tool_name": "Agent",
                                              "tool_input": {"subagent_type": "overseer", "prompt": f"OVERSEER_REQUEST {rid}"}})
    if during is not None:
        during()
    run(VERDICT_SCRIPT, root, "record", stdin={"hook_event_name": "SubagentStop", "agent_type": "overseer", "agent_id": "a1",
                                               "last_assistant_message": "```json\n" + json.dumps(reply) + "\n```"})
    return overseer(root, f"The overseer answered request {rid}.")


def audited(root: Path) -> str:
    """A claim the overseer answers with PASS: what the Stop hook says after the verdict."""
    claim(root)
    return answer(root)


def last_verdict(root: Path) -> dict[str, Any]:
    lines = (root / ".claude/state/overseer/verdicts.jsonl").read_text().splitlines()
    return dict(json.loads(lines[-1]))


VERDICT = "State files read.\n\nOVERSEER_PASS\n"
print("overseer hook: the audit request")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
plain = claim(r)
check("no new exemption: the request is the plain OVERSEER_REQUEST",
      plain.startswith("OVERSEER_REQUEST") and "GATE-ALLOW" not in plain, plain)
check("negative — a project without the overseer's handlers gets no request, and is told why",
      (r / ".claude/settings.json").write_text("{}\n") is not None and (r / ".claude/state/overseer/pending.json").unlink() is None
      and claim(r).startswith("OVERSEER NOT WIRED") and not (r / ".claude/state/overseer/pending.json").exists(), "")
r2 = new_repo()
(r2 / "mod.py").write_text(f"x = 3  {TI}  # {GA} needed to make mypy pass\n")
gate_proc = run(GATE, r2, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
check("the tracer's first half: the Stop gate ALONE lets a weak but well-formed reason through",
      gate_proc.stdout.strip() == "", gate_proc.stdout)
asked = claim(r2)
check("the tracer's second half: the request shows the overseer the file, the line and the reason",
      "GATE-ALLOW REVIEW" in asked and "mod.py:1" in asked and "needed to make mypy pass" in asked, asked)
check("it tells the overseer what a weak reason costs", "OVERSEER_BLOCK" in asked.split("GATE-ALLOW REVIEW")[1], asked)

# ---------------------------------------------------------------- 2b. a checkpoint commit hides nothing
print("not yet judged: commits, accepted PASS, contract grants")
r = new_repo()
sh(r, "git", "switch", "-q", "-c", "unattended/x")
(r / "mod.py").write_text(f"x = 3  {TI}  # {GA} needed to make mypy pass\n")
commit(r, "checkpoint before the claim")
(r / "other.py").write_text(f"k = 1  {NQ}  # {GA} generated file, kept as is\n")
asked = claim(r)
check("an exemption COMMITTED before the unit is claimed is still shown (base is not HEAD)",
      "GATE-ALLOW REVIEW" in asked and "mod.py:1" in asked and "other.py:1" in asked, asked)
check("PASS accepted", answer(r).startswith("OVERSEER_PASS recorded"), "")
judged = json.loads((r / ".claude/state/overseer/gate-allows-judged.json").read_text())
check("the accepted PASS records its commit and what it judged",
      judged["commit"] == sh(r, "git", "rev-parse", "HEAD").stdout.strip() and len(judged["judged"]) == 2, judged)
(r / "other.py").write_text((r / "other.py").read_text() + f"m = 2  {TI}  # {GA} the stub lies about this type\n")
got = collected(r)
check("after the PASS only the exemption nobody judged is new", keys(got) == [("other.py", 2, "code", "type-ignore")], got)
check("--all also shows the judged one still in the diff", [i["line"] for i in collected(r, "--all")] == [1, 2], collected(r, "--all"))
r3 = new_repo()
sh(r3, "git", "switch", "-q", "-c", "unattended/y")
(r3 / "mod.py").write_text(f"x = 3  {TI}  # {GA} needed to make mypy pass\n")
commit(r3, "checkpoint")
refusing = r3 / ".claude/state/gate"
refusing.mkdir(parents=True)
(refusing / "escalations.json").write_text(json.dumps({"open": [{"stamp": "S", "slice": "(none)", "files": []}]}))
refused = audited(r3)
check("a REFUSED pass judges nothing: the exemption stays new",
      refused.startswith("OVERSEER_BLOCK") and not (r3 / ".claude/state/overseer/gate-allows-judged.json").exists()
      and len(collected(r3)) == 1, (refused, collected(r3)))

r = new_repo()
contract_text = f"# Slice tax\n\n{GA} type-ignore — the vendored stub has no types\n"
(r / ".engine" / "slices").mkdir(parents=True)
(r / ".engine" / "slices" / "tax.md").write_text(contract_text)
(r / ".claude/state/contracts").mkdir(parents=True)
(r / ".claude/state/contracts/tax.sha256").write_text(hashlib.sha256(contract_text.encode()).hexdigest() + "  tax.md\n")
commit(r, "the sealed contract is history")
(r / "mod.py").write_text(f"x = 1  {TI}\ny = 2\n")
gate_proc = run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
got = collected(r)
check("a suppression that passes on a SEALED contract's grant is listed where it is used, with the contract's reason",
      gate_proc.stdout.strip() == "" and len(got) == 1 and got[0]["source"] == "contract" and got[0]["line"] == 1
      and got[0]["what"].startswith("type-ignore") and "tax.md" in got[0]["what"]
      and got[0]["reason"] == "the vendored stub has no types", (gate_proc.stdout, got))

r = new_repo()
contract_text = f"# Slice layout\n\n{GA} PROJECT_MARKER — tooling arrives in the next slice\n"
(r / ".engine" / "slices").mkdir(parents=True)
(r / ".engine" / "slices" / "layout.md").write_text(contract_text)
(r / ".claude/state/contracts").mkdir(parents=True)
(r / ".claude/state/contracts/layout.sha256").write_text(hashlib.sha256(contract_text.encode()).hexdigest() + "  layout.md\n")
commit(r, "the sealed contract is history")
check("no change of the key: the contract's grant alone is not an exemption in use", collected(r) == [], collected(r))
env_file = r / ".claude" / "project.env"
env_file.write_text(env_file.read_text() + 'PROJECT_MARKER="absent.toml"\n')
gate_proc = run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
got = collected(r)
check("board 025: a PROJECT_MARKER change that passes on the contract's grant is shown to the overseer",
      gate_proc.stdout.strip() == "" and len(got) == 1 and got[0]["source"] == "contract"
      and got[0]["file"] == ".claude/project.env" and got[0]["what"].startswith("PROJECT_MARKER change")
      and "layout.md" in got[0]["what"] and got[0]["reason"] == "tooling arrives in the next slice", (gate_proc.stdout, got))

print("judged means shown AND passed")
WEAK = f"x = 3  {TI}  # {GA} needed to make mypy pass\n"
r = new_repo()
(r / "mod.py").write_text(WEAK)
said = overseer(r, VERDICT)
check("a PASS typed by the builder is refused and judges nothing",
      said.startswith("OVERSEER_PASS IGNORED") and len(collected(r)) == 1
      and not (r / ".claude/state/overseer/gate-allows-judged.json").exists(), (said, collected(r)))
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
check("the request shows no exemption", "GATE-ALLOW" not in claim(r), "")
(r / "mod.py").write_text(WEAK)
said = answer(r)
check("an exemption added AFTER the request is not judged by the PASS that follows",
      said.startswith("OVERSEER_PASS recorded") and keys(collected(r)) == [("mod.py", 1, "code", "type-ignore")], (said, collected(r)))
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
claim(r)
said = answer(r, during=lambda: (r / "mod.py").write_text(WEAK))
check("...and one added WHILE the overseer audits makes the verdict INVALID: nothing continues, nothing is judged",
      last_verdict(r)["verdict"] == "INVALID" and "OVERSEER_PASS recorded" not in said
      and keys(collected(r)) == [("mod.py", 1, "code", "type-ignore")], (said, collected(r)))
r = new_repo()
(r / "mod.py").write_text(WEAK)
check("shown and passed: judged", audited(r).startswith("OVERSEER_PASS recorded") and collected(r) == [], collected(r))
(r / "mod.py").write_text(WEAK + f"y = 4  {TI}  # {GA} needed to make mypy pass\n")
got = collected(r)
check("a SECOND suppression reusing the accepted reason is new", [(i["line"], i["ordinal"]) for i in got] == [(2, 2)], got)
r = new_repo()
(r / "mod.py").write_text(WEAK)
claim(r)
check("the request is pending until the verdict", (r / ".claude/state/overseer/gate-allows-pending.json").exists(), "")
said = answer(r, BLOCKED)
check("a BLOCK drops the pending request and judges nothing",
      said.startswith("OVERSEER_BLOCK") and not (r / ".claude/state/overseer/gate-allows-pending.json").exists()
      and len(collected(r)) == 1, (said, collected(r)))
claim(r)
overseer(r, "OVERSEER_SLICE_AWAITING_OWNER: nothing can move\n")
check("a halt marker ends the request: nothing pending, nothing judged",
      not (r / ".claude/state/overseer/gate-allows-pending.json").exists() and len(collected(r)) == 1, collected(r))
run(COLLECTOR, r)
check("running the collector by hand records nothing", not (r / ".claude/state/overseer/gate-allows-pending.json").exists(), "")

print("overseer hook: a collector that cannot run says so")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
(r / ".claude/state/overseer").mkdir(parents=True)
(r / ".claude/state/overseer/gate-allows-judged.json").write_text(json.dumps({"commit": "HEAD", "judged": 7}))
asked = claim(r)
check("corrupt collector state is read as no state: the plain request", asked.startswith("OVERSEER_REQUEST") and "GATE-ALLOW" not in asked, asked)
broken = Path(tempfile.mkdtemp(prefix="gate-allows-hooks-"))
for name in ("overseer_stop.py", "overseer_verdict.py", "gate.py", "lesson_queue.py"):
    shutil.copy(HOOKS / name, broken / name)
(broken / "gate_allows.py").write_text("def render(allows: object) -> str:\n    return ''\n\n\n"
    "def record_request(*a: object, **k: object) -> list[object]:\n    raise OSError('disk went away')\n")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
asked = claim(r, broken / "overseer_stop.py")
check("a collector that raises: the request is still made, and says the list is missing",
      asked.startswith("OVERSEER_REQUEST") and "the collector failed" in asked and "disk went away" in asked
      and "gate_allows.py" in asked, asked)

# ---------------------------------------------------------------- 3. PASS while the gate's question is open

def escalate(root: Path, session: str = "s1") -> str:
    """Make the real gate give up on the first block and return the escalation's stamp."""
    env_file = root / ".claude" / "project.env"
    if "GATE_MAX_BLOCKS" not in env_file.read_text():
        env_file.write_text('CODE_EXTENSIONS="py"\nLINT_CMD="false"\nGATE_MAX_BLOCKS="1"\n')
        commit(root, "env")
    (root / "mod.py").write_text((root / "mod.py").read_text() + "q = 9\n")
    run(GATE, root, "--layer", "stop", "--hook", stdin={"session_id": session})
    state = json.loads((root / ".claude/state/gate/escalations.json").read_text())
    return str(state["open"][-1]["stamp"])


def in_slice(root: Path, slug: str | None) -> None:
    progress = root / ".engine" / "PROGRESS.md"
    if slug:
        progress.write_text(f"# PROGRESS\n\n## Slice {slug} — IN PROGRESS\n")
    else:
        progress.unlink(missing_ok=True)


def close(root: Path, stamp: str, inside_claude: bool) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    env.pop("CLAUDECODE", None)
    if inside_claude:
        env["CLAUDECODE"] = "1"
    return subprocess.run([sys.executable, str(GATE), "--close-escalation", stamp], cwd=root,
                          capture_output=True, text=True, env=env, check=False)


def locked(said: str, root: Path) -> bool:
    """The overseer's PASS was recorded as a BLOCK because the gate's escalation is open (the third
    such BLOCK in a row also parks the unit, which locks no less)."""
    blocks = [json.loads(line) for line in (root / ".claude/state/overseer/verdicts.jsonl").read_text().splitlines()]
    blocks = [row for row in blocks if row["verdict"] == "BLOCK"]
    return said.startswith("OVERSEER_BLOCK") and "gate escalation" in said and "gate escalation" in str(blocks[-1]["reason"])


print("the overseer's PASS and the gate's open escalation")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
check("no escalation: PASS continues to the next unit", audited(r).startswith("OVERSEER_PASS recorded"), "")
r = new_repo()
in_slice(r, "tax")
commit(r, "the slice is declared")
stamp = escalate(r)
parked = (r / ".engine/overseer/parked.md").read_text()
check("the gate's PARKED entry names the slice and the owner's command",
      f"## {stamp} — gate stop layer — PARKED" in parked and "- Slice: tax\n" in parked
      and f"--close-escalation {stamp}" in parked, parked)
warned = claim(r)
check("the audit request says in advance that PASS will not be accepted",
      warned.startswith("OVERSEER_REQUEST") and "OVERSEER_PASS will not be accepted" in warned and stamp in warned, warned)
refused = answer(r)
check("an open escalation for the active slice: the PASS is recorded as BLOCK, naming the escalation",
      locked(refused, r) and stamp in refused and stamp in str(last_verdict(r)["reason"]), (refused, last_verdict(r)))
check("...and nothing tells the session to proceed with the next unit", "OVERSEER_PASS recorded" not in refused, refused)
(r / ".engine/overseer/parked.md").write_text(parked.replace("— PARKED", "— RESUMED"))
check("the AGENT marking the parked entry RESUMED opens nothing", locked(audited(r), r), last_verdict(r))
(r / ".engine/overseer/parked.md").write_text(parked)
denied = close(r, stamp, inside_claude=True)
said = audited(r)
check("the close command is refused inside a Claude Code session",
      denied.returncode == 2 and "CLAUDECODE" in denied.stderr and locked(said, r), (denied.returncode, denied.stderr, said, last_verdict(r)))
in_slice(r, "other")
check("declaring ANOTHER slice active in PROGRESS.md (the agent's own file) opens nothing", locked(audited(r), r), last_verdict(r))
in_slice(r, None)
check("...nor does dropping the slice", locked(audited(r), r), last_verdict(r))
in_slice(r, "tax")
sh(r, "git", "stash", "push", "-q", "--", "mod.py")
(r / "other.py").write_text("k = 1\n")
check("the escalated file set aside (stash): other work passes", audited(r).startswith("OVERSEER_PASS recorded"), last_verdict(r))
sh(r, "git", "stash", "pop", "-q")
check("...and back in the tree it is locked again", locked(audited(r), r), last_verdict(r))
wrong = close(r, "2020-01-01T00:00:00Z", inside_claude=False)
check("closing an unknown stamp closes nothing and says which are open", wrong.returncode == 1 and stamp in wrong.stderr, wrong.stderr)
done = close(r, stamp, inside_claude=False)
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("the owner's command closes it in the state; board 037: the log is history — its entry is left as it was written",
      done.returncode == 0 and state["open"] == [] and state["closed"][0]["stamp"] == stamp
      and f"## {stamp} — gate stop layer — PARKED" in (r / ".engine/overseer/parked.md").read_text()
      and "RESUMED" not in (r / ".engine/overseer/parked.md").read_text(), (done.stderr, state))
check("...and PASS is accepted again", audited(r).startswith("OVERSEER_PASS recorded"), last_verdict(r))

print("an escalation outside any slice covers its files")
r = new_repo()
(r / ".claude" / "project.env").write_text(
    'CODE_EXTENSIONS="py"\nLINT_CMD="echo mod.py:1:1: E999 broken; false"\nGATE_MAX_BLOCKS="1"\n')
commit(r, "env")
sh(r, "git", "switch", "-q", "-c", "unattended/z")
stamp = escalate(r)
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("no slice: the escalation records (none) and the file the gate blocked on",
      state["open"][0]["slice"] == "(none)" and state["open"][0]["files"] == ["mod.py"], state)
said = audited(r)
check("a PASS over a range that holds that file is refused, and names it", locked(said, r) and "mod.py" in said, said)
commit(r, "checkpoint: the diff against HEAD is empty now")
check("...also after a checkpoint commit", locked(audited(r), r), last_verdict(r))
in_slice(r, "tax")
check("a slice declared meanwhile does not unlock the escalated file", locked(audited(r), r), last_verdict(r))
r = new_repo()
(r / ".claude/state/gate").mkdir(parents=True)
(r / ".claude/state/gate/escalations.json").write_text(json.dumps({"open": [{"stamp": "S1", "slice": "tax", "files": ["gone.py"]}]}))
(r / "mod.py").write_text("x = 4\n")
check("an escalation whose files are not in the unjudged range locks nothing (no false lock)",
      audited(r).startswith("OVERSEER_PASS recorded"), last_verdict(r))
r = new_repo()
(r / ".claude/state/gate").mkdir(parents=True)
(r / ".claude/state/gate/escalations.json").write_text("{not json")
check("unreadable escalation state locks nothing and breaks nothing",
      audited(r).startswith("OVERSEER_PASS recorded"), last_verdict(r))
r = new_repo()
(r / ".engine/overseer/parked.md").write_text("# Parked\n\n## 2026-09-01T00:00:00Z — gate stop layer — PARKED\n- Class: human-input\n")
check("a parked gate entry from before this package (no state) locks nothing",
      audited(r).startswith("OVERSEER_PASS recorded"), last_verdict(r))


print("the gate's escalation on the task board (board 005)")
r = new_repo()
stamp = escalate(r)
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("no tasks/ in the project: no task, no tasks/ directory, the escalation as before",
      not (r / "tasks").exists() and "task" not in state["open"][-1] and "«так»" not in (r / ".engine/overseer/parked.md").read_text(), state)
r = new_repo()
(r / "tasks" / "blocked").mkdir(parents=True)
(r / "mod.py").write_text("x = 1\ny = 2\nq = 9\n")
(r / ".claude" / "project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="false"\nGATE_MAX_BLOCKS="1"\n')
commit(r, "env")
(r / "mod.py").write_text("x = 1\ny = 2\nq = 10\n")
proc = run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
stamp = str(state["open"][-1]["stamp"])
asked = sorted((r / "tasks/blocked").glob("*.md"))
question = asked[0].read_text(encoding="utf-8") if asked else ""
check("a board in the project: the escalation is a task in tasks/blocked/",
      len(asked) == 1 and asked[0].name.startswith("900-gate-escalation-") and f"Ескалація gates: {stamp}" in question, asked)
check("...it names the file the gate blocked on and asks «Закрити ескалацію?» and offers «так» with an empty answer line",
      "mod.py" in question and "`так`" in question and "1. Закрити ескалацію?" in question and question.rstrip().endswith("Відповідь:"), question)
check("...the escalation state names the task", state["open"][-1].get("task") == f"tasks/blocked/{asked[0].name}" if asked else False, state)
parked = r / ".engine/overseer/parked.md"
check("...board 037: with the question on the board nothing is written to the log parked.md",
      bool(asked) and (not parked.exists() or "gate stop layer" not in parked.read_text()), parked.read_text() if parked.exists() else "")
message = str(json.loads(proc.stdout or "{}").get("systemMessage", ""))
check("...the session is told where the owner is asked, and not to answer it itself",
      message.startswith("GATE ESCALATION") and "tasks/blocked/900-gate-escalation-" in message and "leave its answer line empty" in message, message)
check("the gate itself still closes nothing inside a session", close(r, stamp, inside_claude=True).returncode == 2
      and len(json.loads((r / ".claude/state/gate/escalations.json").read_text())["open"]) == 1)
lonely = Path(tempfile.mkdtemp(prefix="gate-allows-noboard-")) / "hooks"
lonely.mkdir()
for name in ("gate.py", "delete_guard.py", "test_touch.py", "lesson_queue.py"):  # the gate and the modules it cannot run without
    shutil.copy(HOOKS / name, lonely / name)
r = new_repo()
(r / "tasks" / "blocked").mkdir(parents=True)
(r / ".claude" / "project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="false"\nGATE_MAX_BLOCKS="1"\n')
commit(r, "env")
(r / "mod.py").write_text("x = 1\ny = 2\nq = 9\n")
proc = run(lonely / "gate.py", r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("board.py missing beside the hooks: the escalation is still recorded and parked, and the gate says so",
      len(state["open"]) == 1 and "PARKED" in (r / ".engine/overseer/parked.md").read_text()
      and "not put on the task board" in proc.stderr and "GATE ESCALATION" in proc.stdout, proc.stderr)


print("no board file while a rebase or a merge is in progress (board 065)")


def boarded() -> Path:
    root = new_repo()
    (root / "tasks" / "blocked").mkdir(parents=True)
    (root / "tasks" / "blocked" / ".gitkeep").touch()
    (root / ".claude" / "project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="false"\nGATE_MAX_BLOCKS="1"\n')
    commit(root, "board")
    return root


def in_progress(root: Path, marker: str, on: bool) -> None:
    """Put or remove what git leaves in its directory while a rebase or a merge is under way."""
    path = root / sh(root, "git", "rev-parse", "--git-path", marker).stdout.strip()
    if not on:
        path.unlink() if path.is_file() else path.rmdir()
    elif marker == "MERGE_HEAD":
        path.write_text(sh(root, "git", "rev-parse", "HEAD").stdout)
    else:
        path.mkdir()


def questions(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "tasks/blocked").glob("*.md"))


def journal(root: Path) -> str:
    path = root / "tasks/ANOMALIES.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


for marker, word in (("rebase-merge", "rebase"), ("rebase-apply", "rebase"), ("MERGE_HEAD", "merge")):
    r = boarded()
    in_progress(r, marker, True)
    (r / "mod.py").write_text("x = 1\ny = 2\nq = 9\n")
    proc = run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
    state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
    entry = state["open"][-1] if state["open"] else {}
    message = str(json.loads(proc.stdout or "{}").get("systemMessage", ""))
    check(f"{marker}: the escalation is open, and no file is written to tasks/blocked/",
          len(state["open"]) == 1 and questions(r) == [] and "task" not in entry and entry.get("waiting", {}).get("for") == word, (state, questions(r)))
    check(f"{marker}: the escalation is in the anomaly journal, which says why the owner is not asked yet",
          str(entry.get("stamp")) in journal(r) and f"триває {word}" in journal(r) and "tasks/blocked/" not in journal(r), journal(r))
    check(f"{marker}: nothing goes to the log parked.md, and the session is told the question comes later",
          not (r / ".engine/overseer/parked.md").exists() and message.startswith("GATE ESCALATION") and word in message and "tasks/blocked/" not in message, message)
    (r / "mod.py").write_text("x = 1\ny = 2\n")
    run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
    check(f"{marker}: a later turn that is still inside the {word} asks nothing either", questions(r) == [], questions(r))
    in_progress(r, marker, False)
    proc = run(GATE, r, "--ask-waiting") if marker == "rebase-apply" else run(GATE, r, "--layer", "stop", "--hook", stdin={"session_id": "s2"})
    state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
    entry = state["open"][-1]
    asked = questions(r)
    text = (r / "tasks/blocked" / asked[0]).read_text(encoding="utf-8") if asked else ""
    check(f"{marker} gone: the question is asked — one file, the escalation's own stamp, the file and the count the gate blocked on",
          len(asked) == 1 and asked[0].startswith("900-gate-escalation-") and f"Ескалація gates: {entry['stamp']}" in text
          and "mod.py" in text and "1 раз" in text and "last-report.json" in text, (asked, text, proc.stderr))
    check(f"{marker} gone: the state names the task and waits no more; the journal says the question is asked",
          bool(asked) and entry.get("task") == f"tasks/blocked/{asked[0]}" and "waiting" not in entry and f"`tasks/blocked/{asked[0]}`" in journal(r), (entry, journal(r)))
    run(GATE, r, "--ask-waiting")
    check(f"{marker} gone: asked once", questions(r) == asked and journal(r).count("питання власникові поставлено") == 1, journal(r))
r = boarded()
first = escalate(r)
in_progress(r, "rebase-merge", True)
sh(r, "git", "stash", "-u")   # as a rebase does: the first question is not in the working tree
time.sleep(1.1)   # a stamp is a second: two escalations within one would be one escalation
second = escalate(r)
in_progress(r, "rebase-merge", False)
sh(r, "git", "stash", "pop")
run(GATE, r, "--ask-waiting")
check("the case of 2026-10-07 — a second escalation during a rebase that hid the first question: two questions, two numbers",
      first != second and [name[:3] for name in questions(r)] == ["900", "901"], questions(r))
r = new_repo()
in_progress(r, "rebase-merge", True)
escalate(r)
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("negative — no board in the project: a rebase changes nothing, the escalation is parked in the log as before",
      "waiting" not in state["open"][-1] and "PARKED" in (r / ".engine/overseer/parked.md").read_text() and not (r / "tasks").exists(), state)
check("--ask-waiting with nothing waiting: exit 0, nothing written", run(GATE, r, "--ask-waiting").returncode == 0 and not (r / "tasks").exists())

print()
print(f"{'PASS' if FAIL == 0 else 'FAIL'}: {PASS}/{PASS + FAIL}")
sys.exit(0 if FAIL == 0 else 1)
