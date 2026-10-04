#!/usr/bin/env python3
"""The settings-proposal mechanism reaches every project engine.py installs or updates (board 038).

An agent may not edit `.claude/settings.json`; it proposes the whole file in
`docs/tasks/settings.json`, and the owner's «так» has the board runner apply it through
`owner_action.py`. In a project that needs three things, and this suite shows each on a
synthetic project:

- the proposal file — the project's own, created once as a copy of the project's OWN live
  settings (so nothing is proposed), on a fresh install and on an update from a version that
  did not have it; identical to the live file it follows that file through an update, different
  from it it is never touched;
- the check — `.claude/unattended/settings_check.py`, the engine's, shipped like any engine file;
- the action — `owner_action.py apply-settings <sha256>` works there as in the engine's own
  repository, without a test of the project's own.

The synthetic engine has three versions: v1 before the mechanism, v2 with it, v3 with changed
settings. Its `.claude/unattended/` is this repository's working tree, so the scripts under test
are the ones being changed. Nothing outside temporary directories is touched.
"""

import hashlib
import importlib.util
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
PROPOSAL = "docs/tasks/settings.json"
CHECK = ".claude/unattended/settings_check.py"
ACTION = ".claude/unattended/owner_action.py"
LOCK = ".claude/engine-lock.json"
PASS = FAIL = 0

GUARD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" guard'
RECORD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" record'
BASH_GROUP = {"matcher": "Bash", "hooks": [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/a.sh"'}]}
V1: dict[str, Any] = {"permissions": {"allow": ["Read"]}, "hooks": {"PreToolUse": [BASH_GROUP]}}
V2: dict[str, Any] = {
    "permissions": {"allow": ["Read"]},
    "hooks": {
        "PreToolUse": [BASH_GROUP, {"matcher": "Agent|Task", "hooks": [{"type": "command", "command": GUARD}]}],
        "SubagentStop": [{"matcher": "overseer", "hooks": [{"type": "command", "command": RECORD}]}],
    },
}
V3: dict[str, Any] = {**V2, "env": {"CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "12"}}
MAP_V1 = "machine  .claude/settings.local.json\nmachine  .claude/state/\nengine   .claude/**\nproject  **\n"
MAP_V2 = MAP_V1.replace("project  **", f"project  {PROPOSAL}\nproject  **")


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


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def digest(project: Path) -> dict[str, bytes]:
    return {str(p.relative_to(project)): p.read_bytes() for p in sorted(project.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(project).parts}


with tempfile.TemporaryDirectory(prefix="settings-proposal-install-") as tmp:
    tmp_path = Path(tmp)
    env = {**{k: v for k, v in os.environ.items() if k != "CLAUDECODE"}, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}
    eng = tmp_path / "engine"
    eng.mkdir()
    git(eng, "init", "-q", "-b", "main")
    write(eng / ".claude/ownership.txt", MAP_V1)
    write(eng / ".claude/hooks/a.sh", "echo a\n")
    write(eng / SETTINGS, dumped(V1))
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v1: before the proposal mechanism")
    git(eng, "tag", "v1.0.0")
    write(eng / ".claude/ownership.txt", MAP_V2)
    write(eng / ".claude/hooks/overseer_verdict.py", "import sys\nsys.exit(0)\n")
    (eng / ".claude/unattended").mkdir(parents=True)
    for source in sorted((ROOT / ".claude/unattended").iterdir()):
        if source.is_file() and source.suffix in (".py", ".sh"):
            shutil.copy2(source, eng / ".claude/unattended" / source.name)
    write(eng / SETTINGS, dumped(V2))
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v2: the proposal mechanism")
    git(eng, "tag", "v2.0.0")
    write(eng / SETTINGS, dumped(V3))
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v3: the settings change")
    git(eng, "tag", "v3.0.0")
    shutil.copy2(ENGINE_PY, eng / "engine.py")

    def engine(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(eng / "engine.py"), *args], capture_output=True, text=True, env=env, check=False)

    def project(name: str, ref: str | None) -> Path:
        p = tmp_path / name
        p.mkdir()
        git(p, "init", "-q", "-b", "main")
        if ref:
            done = engine("install", str(p), "--ref", ref)
            assert done.returncode == 0, done.stdout + done.stderr
        return p

    def run(p: Path, script: str, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        """A script of the PROJECT's own copy, as the project would run it."""
        return subprocess.run([sys.executable, str(p / script), *args], cwd=p, capture_output=True, text=True, env={**env, **extra}, check=False)

    def offered(p: Path) -> str:
        """The sha256 an agent's question would name — from the project's own board.py."""
        line = run(p, ".claude/unattended/board.py", "action-line", "apply-settings").stdout.strip()
        return line.split()[-1]

    print("1. A fresh install: the proposal, the check and the action arrive")
    p = project("fresh", None)
    r = engine("install", str(p), "--ref", "v2.0.0")
    check("install exits 0 and reports the proposal as seeded", r.returncode == 0 and f"seed    {PROPOSAL}" in r.stdout, r.stdout + r.stderr)
    check("the proposal is the project's live settings, byte for byte", (p / PROPOSAL).is_file() and (p / PROPOSAL).read_bytes() == (p / SETTINGS).read_bytes())
    check("the check and the action ship as engine files", (p / CHECK).is_file() and (p / ACTION).is_file()
          and CHECK in json.loads(text(p / LOCK))["files"] and ACTION in json.loads(text(p / LOCK))["files"])
    check("the lock knows the proposal as seeded, not as an engine file", PROPOSAL in json.loads(text(p / LOCK))["seeded"]
          and PROPOSAL not in json.loads(text(p / LOCK))["files"])
    r = run(p, CHECK)
    check("the project's check passes: the live file is the proposal", r.returncode == 0 and "is the proposal; nothing to apply" in r.stdout, r.stdout + r.stderr)
    before = digest(p)
    r = engine("update", str(p), "--ref", "v2.0.0")
    check("a second run changes nothing", r.returncode == 0 and digest(p) == before and PROPOSAL not in r.stdout, r.stdout)

    print("2. An update from a version without the mechanism")
    p = project("old", "v1.0.0")
    check("negative — the old version installs neither the proposal nor the check", not (p / PROPOSAL).exists() and not (p / CHECK).exists())
    before = digest(p)
    r = engine("update", str(p), "--ref", "v2.0.0", "--dry-run")
    check("a dry run names the seed and writes nothing", f"seed    {PROPOSAL}" in r.stdout and digest(p) == before, r.stdout)
    r = engine("update", str(p), "--ref", "v2.0.0")
    check("update: the settings are replaced and the proposal is the NEW live file", r.returncode == 0 and json.loads(text(p / SETTINGS)) == V2
          and (p / PROPOSAL).read_bytes() == (p / SETTINGS).read_bytes(), r.stdout + r.stderr)
    check("update: the check arrived", (p / CHECK).is_file() and run(p, CHECK).returncode == 0)

    p = project("old-edited", "v1.0.0")
    mine = json.loads(dumped(V1))
    mine["permissions"]["allow"].append("Bash(make:*)")
    write(p / SETTINGS, dumped(mine))
    r = engine("update", str(p), "--ref", "v2.0.0")
    live = json.loads(text(p / SETTINGS))
    check("a project with its own settings keeps them (the overseer wired in)", r.returncode == 1 and "Bash(make:*)" in live["permissions"]["allow"]
          and "wire" in r.stdout and "SubagentStop" in live["hooks"], r.stdout + r.stderr)
    check("…and its proposal is a copy of ITS file, not of the engine's", (p / PROPOSAL).read_bytes() == (p / SETTINGS).read_bytes()
          and json.loads(text(p / PROPOSAL)) != V2)
    check("…so the check passes there too", run(p, CHECK).returncode == 0, run(p, CHECK).stderr)

    print("3. Later updates: an idle proposal follows the live file, a pending one is never touched")
    p = project("idle", "v2.0.0")
    r = engine("update", str(p), "--ref", "v3.0.0")
    check("idle (identical to the live file): it follows the update", r.returncode == 0 and f"follow  {PROPOSAL}" in r.stdout
          and json.loads(text(p / SETTINGS)) == V3 and (p / PROPOSAL).read_bytes() == (p / SETTINGS).read_bytes(), r.stdout + r.stderr)
    p = project("pending", "v2.0.0")
    pending = json.loads(dumped(V2))
    pending["permissions"]["allow"].append("Bash(pytest:*)")
    write(p / PROPOSAL, dumped(pending))
    r = engine("update", str(p), "--ref", "v3.0.0")
    check("pending (differs from the live file): left byte for byte", r.returncode == 0 and text(p / PROPOSAL) == dumped(pending)
          and "follow" not in r.stdout and json.loads(text(p / SETTINGS)) == V3, r.stdout + r.stderr)
    check("…and the report says the live file moved under it", f"note    {PROPOSAL} differs from {SETTINGS}" in r.stdout and "undoes the update" in r.stdout, r.stdout)
    p = project("deleted", "v2.0.0")
    (p / PROPOSAL).unlink()
    r = engine("update", str(p), "--ref", "v3.0.0")
    check("a proposal the project deleted is not created again", r.returncode == 0 and not (p / PROPOSAL).exists() and PROPOSAL not in r.stdout, r.stdout)

    print("4. The demonstration: a proposal → the owner's «так» (the runner's call) → applied")
    p = project("demo", "v2.0.0")
    old_live = text(p / SETTINGS)
    wanted = json.loads(dumped(V2))
    wanted["permissions"]["allow"].append("Bash(pytest:*)")
    write(p / PROPOSAL, dumped(wanted))
    r = run(p, CHECK)
    check("the check: sound, and it names what differs", r.returncode == 0 and "differs from .claude/settings.json in: permissions.allow" in r.stdout, r.stdout + r.stderr)
    r = run(p, CHECK, "--applied")
    check("negative — `--applied` is red while the live file is not the proposal", r.returncode == 1 and "is not applied" in r.stderr, r.stdout + r.stderr)
    sha = offered(p)
    check("board.py offers the action with the proposal's sha256", sha == hashlib.sha256((p / PROPOSAL).read_bytes()).hexdigest(), sha)
    r = run(p, ACTION, "apply-settings", sha, CLAUDECODE="1")
    check("inside a Claude Code session the action is refused: the live file is untouched", r.returncode == 2 and text(p / SETTINGS) == old_live, r.stdout + r.stderr)
    r = run(p, ACTION, "apply-settings", "0" * 64)
    check("another sha256 than the proposal's: stale, untouched", r.returncode == 3 and text(p / SETTINGS) == old_live, r.stdout + r.stderr)
    r = run(p, ACTION, "apply-settings", sha)
    check("the owner's «так»: applied — the live file is the proposal", r.returncode == 0 and text(p / SETTINGS) == dumped(wanted)
          and "applied to .claude/settings.json" in r.stdout, r.stdout + r.stderr)
    check("…with no test of the project's own (the project has no tests/)", not (p / "tests").exists())
    check("…and `--applied` is green now", run(p, CHECK, "--applied").returncode == 0)

    print("5. A proposal the check refuses is never copied")
    applied = text(p / SETTINGS)

    def refused(name: str, proposal: str, needle: str) -> None:
        write(p / PROPOSAL, proposal)
        r = run(p, ACTION, "apply-settings", offered(p))
        check(name, r.returncode == 1 and text(p / SETTINGS) == applied and needle in r.stdout + r.stderr, r.stdout + r.stderr)

    unwired = json.loads(dumped(wanted))
    del unwired["hooks"]["SubagentStop"]
    refused("it drops the overseer's handler", dumped(unwired), "drops the overseer's handler `overseer_verdict.py record`")
    ghost = json.loads(dumped(wanted))
    ghost["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/ghost.sh"'}]}]
    refused("a handler runs a script the project does not have", dumped(ghost), ".claude/hooks/ghost.sh, which this project does not have")
    refused("it is not JSON", "{not json\n", "is not a JSON object")
    refused("its hooks are not Claude Code's shape", '{"hooks": {"Stop": {}}}\n', "`hooks.Stop` is not a list")

    print("6. A project's own test, when it keeps one, still decides")
    write(p / "tests/test_settings_proposal.py", "import sys\nsys.exit(1)\n")
    good = json.loads(dumped(wanted))
    good["permissions"]["allow"].append("Bash(ruff:*)")
    write(p / PROPOSAL, dumped(good))
    r = run(p, ACTION, "apply-settings", offered(p))
    check("red after the copy: the previous file is back", r.returncode == 1 and text(p / SETTINGS) == applied and "the previous" in r.stderr, r.stdout + r.stderr)
    write(p / "tests/test_settings_proposal.py", "import sys\nsys.exit(0)\n")
    r = run(p, ACTION, "apply-settings", offered(p))
    check("green: applied", r.returncode == 0 and text(p / SETTINGS) == dumped(good), r.stdout + r.stderr)

print("7. This repository's ownership map")
spec = importlib.util.spec_from_file_location("engine_module", ENGINE_PY)
assert spec is not None and spec.loader is not None
engine_module = importlib.util.module_from_spec(spec)
sys.modules["engine_module"] = engine_module
spec.loader.exec_module(engine_module)

rules = engine_module.parse_ownership(text(ROOT / ".claude/ownership.txt"))
check("the proposal is the project's, named by a rule of its own", engine_module.owner_of(rules, PROPOSAL) == "project"
      and any(r.pattern == PROPOSAL and r.seed is None for r in rules))
check("the check and the action are the engine's", engine_module.owner_of(rules, CHECK) == "engine" and engine_module.owner_of(rules, ACTION) == "engine")
check("here the live file is the proposal and the shipped check says so",
      subprocess.run([sys.executable, str(ROOT / CHECK), "--applied"], capture_output=True, text=True, check=False).returncode == 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
