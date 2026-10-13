#!/usr/bin/env python3
"""The Stop gate on a freshly installed engine, before the install is committed (board 786).

`engine.py install` writes the engine's own files into the project and never commits. Until the
owner's first commit they are all untracked, and the gate used to read them as the turn's own
work: the engine's justified-elsewhere `# noqa` lines, the seeded project.env and the shipped
ruff.toml blocked the smoke check of docs/TEMPLATE-SETUP.md (step 6) and the first session, and
a lesson candidate about the engine's own hook landed in the project's first commit.

The install here is real: this repository's working tree (tracked files as they are now, so the
code under test is the code being changed) is committed into a throwaway engine, and that
engine installs itself into an empty project. Nothing outside temporary directories is touched.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0
SMOKE = "echo '{\"stop_hook_active\":false}' | bash .claude/hooks/verify-on-stop.sh"
NOQA = "# " + "noqa"


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:900]}")


def sh(cwd: Path, *cmd: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return sh(cwd, "git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args)


def engine_copy(where: Path) -> Path:
    """This repository as it is in the working tree (tracked and new files), committed as one engine."""
    eng = where / "engine"
    eng.mkdir()
    for rel in sh(ROOT, "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout.split("\0"):
        if rel and (ROOT / rel).is_file():
            (eng / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, eng / rel)
    git(eng, "init", "-q", "-b", "main")
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "the engine under test")
    return eng


def smoke(project: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """Step 6 of docs/TEMPLATE-SETUP.md, as the owner types it in the project's root."""
    proc = sh(project, "bash", "-c", SMOKE, env=hook_env(str(project)))
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        payload = {"_malformed": proc.stdout}
    return proc, payload


def blocks(project: Path) -> list[str]:
    path = project / ".claude/state/gate/last-report.json"
    if not path.is_file():
        return []
    return [f"{f['rule']} {f['file']}" for f in json.loads(path.read_text())["findings"] if f["severity"] == "block"]


def report_text(project: Path) -> str:
    path = project / ".claude/state/gate/last-report.json"
    return path.read_text() if path.is_file() else ""


def lesson_text(project: Path) -> str:
    return "".join(p.read_text() for p in sorted((project / ".engine/journal").rglob("*.md")))


with tempfile.TemporaryDirectory(prefix="fresh-install-gate-") as tmp:
    tmp_path = Path(tmp)
    eng = engine_copy(tmp_path)
    install_env = {**os.environ, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}

    def fresh(name: str) -> Path:
        project = tmp_path / name
        project.mkdir()
        git(project, "init", "-q", "-b", "main")
        done = sh(project, sys.executable, str(eng / "engine.py"), "install", str(project), "--ref", "HEAD", env=install_env)
        assert done.returncode == 0, done.stdout + done.stderr
        return project

    print("a fresh install, nothing committed")
    p = fresh("fresh")
    lock = json.loads((p / ".claude/engine-lock.json").read_text())
    check("the lock records the blob every seeded file started from",
          set(lock.get("seeds", {})) >= {".claude/project.env", ".engine/rules.md"}, sorted(lock.get("seeds", {})))
    proc, payload = smoke(p)
    check("the smoke check of step 6 does not block", proc.returncode == 0 and payload.get("decision") != "block",
          (proc.returncode, blocks(p), proc.stderr))
    check("no block finding names a file of the install", blocks(p) == [], blocks(p))
    check("no lesson candidate about the engine's own files", "bypass/" not in lesson_text(p), lesson_text(p))

    print("the same install, and a turn that changes what was installed")
    hook = p / ".claude/hooks/journal.py"
    hook.write_text(hook.read_text() + f"\nimport os  {NOQA}\n")
    proc, payload = smoke(p)
    check("a suppression added to an engine file blocks", "bypass/noqa .claude/hooks/journal.py" in blocks(p), blocks(p))
    check("... and only that file is blamed for a suppression",
          [b for b in blocks(p) if b.startswith("bypass/noqa")] == ["bypass/noqa .claude/hooks/journal.py"], blocks(p))
    check("... as a block decision", payload.get("decision") == "block", proc.stdout[:300])

    p = fresh("env")
    env_file = p / ".claude/project.env"
    env_file.write_text(env_file.read_text().replace('CODE_EXTENSIONS="py"', 'CODE_EXTENSIONS="md"'))
    smoke(p)
    check("a seeded project.env changed before the first commit blocks",
          blocks(p) == ["bypass/config .claude/project.env"], blocks(p))

    check("... and the block names the key that changed", "CODE_EXTENSIONS" in report_text(p), report_text(p))

    print("step 2 before the first commit: project.env configured, the gate's scope left alone")
    p = fresh("configured")
    env_file = p / ".claude/project.env"
    env_file.write_text(env_file.read_text() + 'SOURCE_DIRS="app"\n')
    proc, payload = smoke(p)
    check("SOURCE_DIRS set in the seeded project.env: no block, CODE_EXTENSIONS was not changed",
          blocks(p) == [] and payload.get("decision") != "block", (blocks(p), report_text(p)))
    env_file.write_text(env_file.read_text().replace('LINT_CMD=""', 'LINT_CMD="npm run lint"'))
    smoke(p)
    check("a check command set there too: no finding names a key nobody changed",
          "CODE_EXTENSIONS" not in report_text(p), report_text(p))
    copy = p / ".claude/state/install/seeds/.claude/project.env"
    copy.write_text(env_file.read_text().replace('CODE_EXTENSIONS="py"', 'CODE_EXTENSIONS="md"'))
    env_file.write_text(copy.read_text())
    smoke(p)
    check("a seed copy that is not what the lock recorded is not believed",
          blocks(p) == ["bypass/config .claude/project.env"] and "CODE_EXTENSIONS" in report_text(p), report_text(p))

    p = fresh("ruff")
    (p / ".claude/ruff.toml").write_text((p / ".claude/ruff.toml").read_text() + 'ignore = ["E501"]\n')
    smoke(p)
    check("the shipped ruff.toml changed before the first commit blocks",
          blocks(p) == ["bypass/config .claude/ruff.toml"], blocks(p))

    p = fresh("guarded")
    (p / ".claude/constitution.md").write_text((p / ".claude/constitution.md").read_text() + "\nArticle 9.\n")
    (p / ".engine/rules.md").write_text((p / ".engine/rules.md").read_text() + "\n- a rule nobody approved\n")
    smoke(p)
    check("a guarded file changed before the first commit blocks, the untouched ones do not",
          blocks(p) == ["protected/changed .claude/constitution.md", "protected/changed .engine/rules.md"], blocks(p))

    p = fresh("lockless")
    (p / ".claude/engine-lock.json").unlink()
    smoke(p)
    check("without the lock nothing is taken on trust", any(b.startswith("bypass/") for b in blocks(p)), blocks(p))

    p = fresh("badlock")
    (p / ".claude/engine-lock.json").write_text("{ not json")
    proc, payload = smoke(p)
    check("an unreadable lock is no lock, and no crash",
          any(b.startswith("bypass/noqa") for b in blocks(p)) and "crashed" not in str(payload.get("reason", "")), blocks(p))

    print("staged, at the pre-commit layer")
    p = fresh("staged")
    git(p, "add", "-A")
    sh(p, sys.executable, ".claude/hooks/gate.py", "--layer", "pre_commit", env=hook_env(str(p)))
    check("the staged install: no bypass block", [b for b in blocks(p) if b.startswith("bypass/")] == [], blocks(p))
    hook = p / ".claude/hooks/journal.py"
    hook.write_text(hook.read_text() + f"\nimport os  {NOQA}\n")
    git(p, "add", "-A")
    sh(p, sys.executable, ".claude/hooks/gate.py", "--layer", "pre_commit", env=hook_env(str(p)))
    check("a staged suppression in an engine file blocks",
          [b for b in blocks(p) if b.startswith("bypass/")] == ["bypass/noqa .claude/hooks/journal.py"], blocks(p))

    print("after the install is committed, the lock excuses nothing")
    p = fresh("committed")
    seed_env = (p / ".claude/project.env").read_text()
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "install the engine")
    proc, payload = smoke(p)
    check("the committed install: the gate is silent", proc.returncode == 0 and not proc.stdout.strip(), proc.stdout[:300])
    (p / ".claude/project.env").write_text(seed_env.replace('CODE_EXTENSIONS="py"', 'CODE_EXTENSIONS="py ts"'))
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "the project's own extensions")
    (p / ".claude/project.env").write_text(seed_env)
    smoke(p)
    check("putting a tracked project.env back to its seed is still a change of the gate's scope",
          blocks(p) == ["bypass/config .claude/project.env"], blocks(p))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
