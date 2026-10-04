#!/usr/bin/env python3
"""engine.py puts the overseer's two handlers into every project it installs or updates (board 033).

The audit is done by the agent `overseer` and recorded by `overseer_verdict.py`, which works only
through two handlers in the project's `.claude/settings.json`. The Stop hook has no other way to
audit, so a project whose settings lack them audits nothing. Three roads lead to a project:

- a fresh install — the settings file arrives with the handlers;
- an update of a project that never touched its settings — the file is replaced;
- an update of a project that edited its settings — the file is the project's now and is not
  replaced; engine.py ADDS the handlers it lacks, leaves everything else in it as it was, and says
  exactly what it added. A file it cannot read as JSON is left alone and the report carries the
  exact text to add by hand.

A synthetic engine with two versions (v1 without the handlers, v2 with them) keeps every
expectation exact; the last group does the same from a real old version of this repository
(v0.11.0, before the overseer was a separate agent) to HEAD and asks the shipped script itself.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
SETTINGS = ".claude/settings.json"
OLD_REAL = "v0.11.0"
PASS = FAIL = 0

GUARD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" guard'
RECORD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" record'
GUARD_MATCHER = "Agent|Task|Edit|Write|MultiEdit|NotebookEdit"
BASH_GROUP = {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash .claude/hooks/a.sh", "timeout": 10}]}
V1: dict[str, Any] = {"permissions": {"allow": ["Read"]}, "hooks": {"PreToolUse": [BASH_GROUP]}}
V2: dict[str, Any] = {
    "permissions": {"allow": ["Read"]},
    "hooks": {
        "PreToolUse": [BASH_GROUP, {"matcher": GUARD_MATCHER, "hooks": [{"type": "command", "command": GUARD, "timeout": 15}]}],
        "SubagentStop": [{"matcher": "overseer", "hooks": [{"type": "command", "command": RECORD, "timeout": 30}]}],
    },
}
MAP = "machine  .claude/settings.local.json\nmachine  .claude/state/\nengine   .claude/**\nproject  **\n"


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail[:900]}")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=cwd, capture_output=True, text=True, check=True).stdout


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def dumped(data: object) -> str:
    return json.dumps(data, indent=2) + "\n"


def handlers(project: Path, name: str = SETTINGS) -> list[str]:
    """`event|matcher|command` of every handler in the project's settings that calls the verdict script."""
    data = json.loads((project / name).read_text(encoding="utf-8"))
    return sorted(f"{event}|{group.get('matcher', '')}|{hook['command']}"
                  for event, groups in data.get("hooks", {}).items() for group in groups
                  for hook in group["hooks"] if "overseer_verdict.py" in hook["command"])


BOTH = sorted([f"PreToolUse|{GUARD_MATCHER}|{GUARD}", f"SubagentStop|overseer|{RECORD}"])

with tempfile.TemporaryDirectory(prefix="settings-wiring-test-") as tmp:
    tmp_path = Path(tmp)
    env = {**os.environ, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}
    eng = tmp_path / "engine"
    eng.mkdir()
    git(eng, "init", "-q", "-b", "main")
    write(eng / ".claude/ownership.txt", MAP)
    write(eng / ".claude/hooks/a.sh", "echo a\n")
    write(eng / SETTINGS, dumped(V1))
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v1")
    git(eng, "tag", "v1.0.0")
    write(eng / SETTINGS, dumped(V2))
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v2")
    git(eng, "tag", "v2.0.0")
    shutil.copy2(ENGINE_PY, eng / "engine.py")

    def engine(*args: str, script: Path = eng / "engine.py") -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, env=env, check=False)

    def project(name: str, ref: str | None = "v1.0.0") -> Path:
        p = tmp_path / name
        p.mkdir()
        git(p, "init", "-q", "-b", "main")
        if ref:
            done = engine("install", str(p), "--ref", ref)
            assert done.returncode == 0, done.stdout + done.stderr
        return p

    print("1. A new project and an untouched one get the engine's settings file")
    p = project("fresh", None)
    r = engine("install", str(p), "--ref", "v2.0.0")
    check("install: the handlers arrive with the settings file", r.returncode == 0 and handlers(p) == BOTH, r.stdout + r.stderr)
    check("install: nothing is reported as added by hand", "wire" not in r.stdout, r.stdout)
    p = project("untouched")
    check("negative — the old version has no handler", handlers(p) == [])
    r = engine("update", str(p), "--ref", "v2.0.0")
    check("update, untouched settings: the file is replaced and carries both", r.returncode == 0 and handlers(p) == BOTH
          and f"update  {SETTINGS}" in r.stdout and "wire" not in r.stdout, r.stdout + r.stderr)

    print("2. A project with its own settings keeps them and gains exactly the two handlers")
    p = project("edited")
    mine = json.loads(dumped(V1))
    mine["permissions"]["allow"].append("Bash(make:*)")
    mine["env"] = {"MINE": "1"}
    mine["hooks"]["PreToolUse"].append({"matcher": "Write", "hooks": [{"type": "command", "command": "bash mine.sh"}]})
    write(p / SETTINGS, dumped(mine))
    before = (p / SETTINGS).read_text()
    r = engine("update", str(p), "--ref", "v2.0.0", "--dry-run")
    check("dry run: says what it would add", f"wire    {SETTINGS}" in r.stdout and "guard" in r.stdout and "record" in r.stdout, r.stdout)
    check("dry run: writes nothing", (p / SETTINGS).read_text() == before)
    r = engine("update", str(p), "--ref", "v2.0.0")
    after = json.loads((p / SETTINGS).read_text())
    check("update: both handlers are in the project's file", handlers(p) == BOTH, r.stdout + r.stderr)
    expected = json.loads(dumped(mine))
    expected["hooks"]["PreToolUse"].append(V2["hooks"]["PreToolUse"][1])
    expected["hooks"]["SubagentStop"] = V2["hooks"]["SubagentStop"]
    check("update: everything else in the file is as the project wrote it", after == expected, json.dumps(after))
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("  wire")), "")
    check("update: the report names each handler added — event, matcher, command",
          f"PreToolUse [{GUARD_MATCHER}] {GUARD}" in line and f"SubagentStop [overseer] {RECORD}" in line, r.stdout)
    check("update: the file is still the project's — kept, exit 1", f"keep    {SETTINGS}" in r.stdout and r.returncode == 1, r.stdout)
    wired = (p / SETTINGS).read_text()
    r = engine("update", str(p), "--ref", "v2.0.0")
    check("a second update adds nothing and changes nothing", "wire" not in r.stdout and (p / SETTINGS).read_text() == wired, r.stdout)

    print("3. Only what is missing is added")
    p = project("half")
    half = json.loads(dumped(mine))
    half["hooks"]["SubagentStop"] = [{"matcher": "overseer", "hooks": [{"type": "command", "command": "python3 .claude/hooks/overseer_verdict.py record"}]}]
    write(p / SETTINGS, dumped(half))
    r = engine("update", str(p), "--ref", "v2.0.0")
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("  wire")), "")
    got = json.loads((p / SETTINGS).read_text())
    check("the project's own record handler is not doubled", len(got["hooks"]["SubagentStop"]) == 1 and "record" not in line, r.stdout)
    check("the missing guard is added", f"PreToolUse|{GUARD_MATCHER}|{GUARD}" in handlers(p) and "guard" in line, r.stdout)
    p = project("local")
    write(p / SETTINGS, dumped(mine))
    write(p / ".claude/settings.local.json", dumped({"hooks": V2["hooks"]}))
    r = engine("update", str(p), "--ref", "v2.0.0")
    check("handlers wired in settings.local.json are not added a second time (they would fire twice)",
          "wire" not in r.stdout and handlers(p) == [], r.stdout)
    p = project("downgrade", "v2.0.0")
    write(p / SETTINGS, dumped(mine))
    r = engine("update", str(p), "--ref", "v1.0.0")
    check("negative — a ref without the handlers adds nothing", "wire" not in r.stdout and handlers(p) == [], r.stdout)

    print("4. A settings file engine.py cannot read is left alone, with the exact text to add")
    for name, text, why in (("broken", '{"permissions": {"allow": ["Read"],}}\n', "not valid JSON"),
                            ("list", '{"mine": true, "hooks": []}\n', "`hooks` is not an object")):
        p = project(name)
        write(p / SETTINGS, text)
        r = engine("update", str(p), "--ref", "v2.0.0")
        note = next((ln for ln in r.stdout.splitlines() if ln.startswith("  note") and SETTINGS in ln), "")
        check(f"{name}: the file is untouched", (p / SETTINGS).read_text() == text and "wire" not in r.stdout, r.stdout)
        check(f"{name}: the report says why ({why}) and that nothing is audited until it is fixed",
              why in note and "NOT added" in note and "no unit is audited" in note, r.stdout)
        snippet = note[note.find("{"):]
        try:
            to_add = json.loads(snippet)
        except ValueError:
            to_add = None
        check(f"{name}: the report carries the handlers as JSON ready to paste", to_add == {
            "PreToolUse": [V2["hooks"]["PreToolUse"][1]], "SubagentStop": V2["hooks"]["SubagentStop"]}, note)
        check(f"{name}: exit 1 — the update needs a person", r.returncode == 1, str(r.returncode))

    print(f"5. The real engine: a project installed from {OLD_REAL}, its settings edited, updated to HEAD")
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"{OLD_REAL}^{{commit}}"], capture_output=True, check=False).returncode != 0:
        print(f"  skip  the tag {OLD_REAL} is not in this clone")
    else:
        p = tmp_path / "real"
        p.mkdir()
        git(p, "init", "-q", "-b", "main")
        r = engine("install", str(p), "--ref", OLD_REAL, script=ENGINE_PY)
        check("the old version installs and has no handler", r.returncode == 0 and handlers(p) == [], r.stdout[-400:] + r.stderr)
        data = json.loads((p / SETTINGS).read_text())
        data.setdefault("permissions", {}).setdefault("allow", []).append("Bash(make:*)")
        write(p / SETTINGS, dumped(data))
        r = engine("update", str(p), "--ref", "HEAD", script=ENGINE_PY)
        check("update to HEAD: the edited file gains both handlers", len(handlers(p)) == 2 and f"wire    {SETTINGS}" in r.stdout, r.stdout[-900:] + r.stderr)
        check("update to HEAD: the project's own rule is still there", "Bash(make:*)" in json.loads((p / SETTINGS).read_text())["permissions"]["allow"])
        said = subprocess.run([sys.executable, str(p / ".claude/hooks/overseer_verdict.py"), "status"], capture_output=True, text=True,
                              env={**env, "CLAUDE_PROJECT_DIR": str(p)}, cwd=p, check=False).stdout
        check("the shipped script agrees: wired", "wired in settings: yes" in said, said)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
