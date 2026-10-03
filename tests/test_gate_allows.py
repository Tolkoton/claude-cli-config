#!/usr/bin/env python3
"""gate_allows.py and its two carriers: the overseer sees every new gate exemption.

Package costs, item 1. Deterministic: throwaway git repositories, the real gate.py and
overseer_stop.py, no model, no network.

  1. the collector lists the gate-allow markers a diff ADDS — in code comments, in config
     files, in a slice contract — and nothing that merely mentions the word;
  2. the overseer hook puts that list into OVERSEER_REQUEST, and leaves the request
     byte-identical when there is none;
  3. "new" means not yet judged: a checkpoint commit hides nothing, an accepted PASS moves the
     base, a suppression that rides on a sealed contract's grant is listed where it is used;
  4. while the Stop gate has an open escalation for the work, the hook does not accept
     OVERSEER_PASS — and only the owner's command, run outside a Claude Code session, closes it.

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
from pathlib import Path
from typing import Any

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           check=True).stdout.strip())
HOOKS = ROOT / ".claude" / "hooks"
COLLECTOR = HOOKS / "gate_allows.py"
GATE = HOOKS / "gate.py"
OVERSEER = HOOKS / "overseer_stop.py"
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


def overseer(root: Path, message: str) -> str:
    proc = run(OVERSEER, root, stdin={"last_assistant_message": message, "transcript_path": str(transcript(root))})
    if not proc.stdout.strip():
        return ""
    return str(json.loads(proc.stdout).get("reason", ""))


UNIT = "Did the work.\n\n=== UNIT 1 COMPLETE ===\n"
VERDICT = "State files read.\n\nOVERSEER_PASS\n"
print("overseer hook: the audit request")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
plain = overseer(r, UNIT)
check("no new exemption: the request is the plain OVERSEER_REQUEST",
      plain.startswith("OVERSEER_REQUEST") and "GATE-ALLOW" not in plain, plain)
r2 = new_repo()
(r2 / "mod.py").write_text(f"x = 3  {TI}  # {GA} needed to make mypy pass\n")
gate_proc = run(GATE, r2, "--layer", "stop", "--hook", stdin={"session_id": "s1"})
check("the tracer's first half: the Stop gate ALONE lets a weak but well-formed reason through",
      gate_proc.stdout.strip() == "", gate_proc.stdout)
asked = overseer(r2, UNIT)
check("the tracer's second half: the request shows the overseer the file, the line and the reason",
      "GATE-ALLOW REVIEW" in asked and "mod.py:1" in asked and "needed to make mypy pass" in asked, asked)
check("the request with a list starts with the unchanged request text", asked.startswith(plain), (plain, asked))
check("it tells the overseer what a weak reason costs", "OVERSEER_BLOCK" in asked.split("GATE-ALLOW REVIEW")[1], asked)

# ---------------------------------------------------------------- 2b. a checkpoint commit hides nothing
print("not yet judged: commits, accepted PASS, contract grants")
r = new_repo()
sh(r, "git", "switch", "-q", "-c", "unattended/x")
(r / "mod.py").write_text(f"x = 3  {TI}  # {GA} needed to make mypy pass\n")
commit(r, "checkpoint before the claim")
(r / "other.py").write_text(f"k = 1  {NQ}  # {GA} generated file, kept as is\n")
asked = overseer(r, UNIT)
check("an exemption COMMITTED before the unit is claimed is still shown (base is not HEAD)",
      "GATE-ALLOW REVIEW" in asked and "mod.py:1" in asked and "other.py:1" in asked, asked)
check("PASS accepted", overseer(r, VERDICT).startswith("OVERSEER_PASS recorded"), "")
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
overseer(r3, VERDICT)
check("a REFUSED pass judges nothing: the exemption stays new",
      not (r3 / ".claude/state/overseer/gate-allows-judged.json").exists() and len(collected(r3)) == 1, collected(r3))

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

print("overseer hook: a collector that cannot run says so")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
(r / ".claude/state/overseer").mkdir(parents=True)
(r / ".claude/state/overseer/gate-allows-judged.json").write_text(json.dumps({"commit": "HEAD", "judged": 7}))
asked = overseer(r, UNIT)
check("corrupt collector state is read as no state: the plain request", asked.startswith("OVERSEER_REQUEST") and "GATE-ALLOW" not in asked, asked)
broken = Path(tempfile.mkdtemp(prefix="gate-allows-hooks-"))
for name in ("overseer_stop.py", "gate.py", "lesson_queue.py"):
    shutil.copy(HOOKS / name, broken / name)
(broken / "gate_allows.py").write_text("def render(allows: object) -> str:\n    return ''\n\n\n"
    "def collect(*a: object, **k: object) -> list[object]:\n    raise OSError('disk went away')\n")
r = new_repo()
(r / "mod.py").write_text("x = 3\n")
proc = run(broken / "overseer_stop.py", r, stdin={"last_assistant_message": UNIT, "transcript_path": str(transcript(r))})
asked = str(json.loads(proc.stdout or "{}").get("reason", ""))
check("a collector that raises: the request is still made, and says the list is missing",
      asked.startswith("OVERSEER_REQUEST") and "the collector failed" in asked and "disk went away" in asked
      and "gate_allows.py" in asked, asked or proc.stderr)

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


print("overseer hook: PASS and the gate's open escalation")
r = new_repo()
check("no escalation: PASS continues to the next unit", overseer(r, VERDICT).startswith("OVERSEER_PASS recorded"), "")
r = new_repo()
in_slice(r, "tax")
stamp = escalate(r)
parked = (r / ".engine/overseer/parked.md").read_text()
check("the gate's PARKED entry names the slice and the owner's command",
      f"## {stamp} — gate stop layer — PARKED" in parked and "- Slice: tax\n" in parked
      and f"--close-escalation {stamp}" in parked, parked)
refused = overseer(r, VERDICT)
check("an open escalation for the active slice: PASS is REFUSED",
      refused.startswith("OVERSEER_PASS_REFUSED") and "`tax`" in refused and stamp in refused, refused)
check("...and nothing tells the session to proceed with the next unit", "OVERSEER_PASS recorded" not in refused, refused)
check("the refusal is recorded beside the escalation",
      len(json.loads((r / ".claude/state/gate/escalations.json").read_text())["refusals"]) == 1, "")
check("the same message again is silent (no loop)", overseer(r, VERDICT) == "", "")
check("a reworded PASS is refused again", overseer(r, VERDICT + "\nreally.\n").startswith("OVERSEER_PASS_REFUSED"), "")
(r / ".engine/overseer/parked.md").write_text(parked.replace("— PARKED", "— RESUMED"))
check("the AGENT marking the parked entry RESUMED opens nothing",
      overseer(r, VERDICT + "\nresumed.\n").startswith("OVERSEER_PASS_REFUSED"), "")
(r / ".engine/overseer/parked.md").write_text(parked)
denied = close(r, stamp, inside_claude=True)
check("the close command is refused inside a Claude Code session",
      denied.returncode == 2 and "CLAUDECODE" in denied.stderr
      and overseer(r, VERDICT + "\nclosed?\n").startswith("OVERSEER_PASS_REFUSED"), (denied.returncode, denied.stderr))
check("a halt marker still passes through silently", overseer(r, "OVERSEER_BLOCK: #4 weak gate-allow\n") == "", "")
warned = overseer(r, UNIT)
check("the audit request says in advance that PASS will not be accepted",
      warned.startswith("OVERSEER_REQUEST") and "OVERSEER_PASS will not be accepted" in warned, warned)
in_slice(r, "other")
check("another slice is not locked by it", overseer(r, VERDICT + "\nother.\n").startswith("OVERSEER_PASS recorded"), "")
in_slice(r, "tax")
wrong = close(r, "2020-01-01T00:00:00Z", inside_claude=False)
check("closing an unknown stamp closes nothing and says which are open", wrong.returncode == 1 and stamp in wrong.stderr, wrong.stderr)
done = close(r, stamp, inside_claude=False)
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("the owner's command closes it: state, and the parked entry reads RESUMED",
      done.returncode == 0 and state["open"] == [] and state["closed"][0]["stamp"] == stamp
      and f"## {stamp} — gate stop layer — RESUMED" in (r / ".engine/overseer/parked.md").read_text(), (done.stderr, state))
check("...and PASS is accepted again", overseer(r, VERDICT + "\nafter close.\n").startswith("OVERSEER_PASS recorded"), "")

print("overseer hook: an escalation outside any slice covers its files")
r = new_repo()
(r / ".claude" / "project.env").write_text(
    'CODE_EXTENSIONS="py"\nLINT_CMD="echo mod.py:1:1: E999 broken; false"\nGATE_MAX_BLOCKS="1"\n')
commit(r, "env")
sh(r, "git", "switch", "-q", "-c", "unattended/z")
stamp = escalate(r)
state = json.loads((r / ".claude/state/gate/escalations.json").read_text())
check("no slice: the escalation records (none) and the file the gate blocked on",
      state["open"][0]["slice"] == "(none)" and state["open"][0]["files"] == ["mod.py"], state)
check("a PASS over a range that holds that file is refused, and names it",
      "mod.py" in overseer(r, VERDICT) and overseer(r, VERDICT + "\nx\n").startswith("OVERSEER_PASS_REFUSED"), "")
commit(r, "checkpoint: the diff against HEAD is empty now")
check("...also after a checkpoint commit", overseer(r, VERDICT + "\ny\n").startswith("OVERSEER_PASS_REFUSED"), "")
in_slice(r, "tax")
check("a slice that started meanwhile is not locked by the sliceless escalation",
      overseer(r, VERDICT + "\nz\n").startswith("OVERSEER_PASS recorded"), "")
r = new_repo()
(r / ".claude/state/gate").mkdir(parents=True)
(r / ".claude/state/gate/escalations.json").write_text("{not json")
check("unreadable escalation state locks nothing and breaks nothing",
      overseer(r, VERDICT).startswith("OVERSEER_PASS recorded"), "")
r = new_repo()
(r / ".engine/overseer/parked.md").write_text("# Parked\n\n## 2026-09-01T00:00:00Z — gate stop layer — PARKED\n- Class: human-input\n")
check("a parked gate entry from before this package (no state) locks nothing",
      overseer(r, VERDICT).startswith("OVERSEER_PASS recorded"), "")

print()
print(f"{'PASS' if FAIL == 0 else 'FAIL'}: {PASS}/{PASS + FAIL}")
sys.exit(0 if FAIL == 0 else 1)
