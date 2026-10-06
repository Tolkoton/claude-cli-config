#!/usr/bin/env python3
"""Commits are legal on unattended/<date> and nowhere else; an ordinary push is the ask rule's.

Owner-ratified 2026-08-27. The checkpoint is kept where it does work -- nothing reaches
main without a human -- while a long run gets a committed base to build on.

Package 3b adds the environment table (docs/plan/package-3b.md): a CLOUD session
(CLAUDE_CODE_REMOTE=true) may commit on its own non-protected branch, but ONLY when
CLOUD_COMMIT_POLICY in .claude/project.env says session-branch. The switch ships off.

The fix round (docs/plan/package-3b-finish.md, owner decision of 2026-10-01) takes PUSH out
of the hook: the protected-branch block names `commit` only. What stands between the agent
and a push is the settings file — `Bash(git push:*)` in permissions.ask prompts, and the
force forms are denied — so this test pins the LIVE .claude/settings.json (S7 is applied;
the live file is the contract) and the proposal in docs/tasks/settings.json for exactly
those three rules.

Board 017 (owner decision) put the dangerous forms of a push back into the hook: forced, the
deletion of a remote branch, and a push into main or stable. One case here pins the last of
them; every form is in tests/test_push_hardening.py.

Every hook case runs against a REAL throwaway git repo with a real branch checked out,
because the hook reads the branch with `git branch --show-current`; faking it would test
the test.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude/hooks/block-dangerous.sh"
SETTINGS = (ROOT / ".claude/settings.json", ROOT / "docs/tasks/settings.json")
FORCE_PUSH = "git push " + "--force"  # split so the hook under test does not block THIS file being written
PUSH_RULE = "Bash(git push:*)"
FORCE_RULES = ("Bash(git push " + "--force*)", "Bash(git push -f *)")


def repo_on(branch: str) -> str:
    root = Path(tempfile.mkdtemp())

    def run(*a: str) -> None:
        subprocess.run(a, cwd=root, capture_output=True, text=True, check=False)

    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    (root / "f.txt").write_text("x")
    run("git", "add", "f.txt")
    run("git", "commit", "-qm", "init")
    if branch != "main":
        run("git", "switch", "-qc", branch)
    else:
        run("git", "branch", "-M", "main")
    return str(root)


def with_cloud_policy(root: str, value: str) -> str:
    """The same repo with CLOUD_COMMIT_POLICY set in .claude/project.env (the switch)."""
    env_file = Path(root) / ".claude" / "project.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f'SOURCE_DIRS="src"\nCLOUD_COMMIT_POLICY="{value}"\n')
    return root


def run_hook(cmd: str, project_dir: str, cloud: bool = False) -> subprocess.CompletedProcess[str]:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "CLAUDE_PROJECT_DIR": project_dir}
    if cloud:
        env["CLAUDE_CODE_REMOTE"] = "true"  # what a cloud session sets (code.claude.com/docs/en/env-vars)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def blocked(cmd: str, project_dir: str, cloud: bool = False) -> bool:
    return run_hook(cmd, project_dir, cloud).returncode == 2


UNATT = repo_on("unattended/2026-08-27")
MAIN = repo_on("main")
FEAT = repo_on("feat/something")
SUFFIXED = repo_on("unattended/2026-10-02-package-3b")
CLOUD_OFF = repo_on("claude/session-abc")  # no project.env at all
CLOUD_OFF_EXPLICIT = with_cloud_policy(repo_on("claude/session-abc"), "off")
CLOUD_ON = with_cloud_policy(repo_on("claude/session-abc"), "session-branch")
CLOUD_ON_MAIN = with_cloud_policy(repo_on("main"), "session-branch")

CASES = [
    # (name, command, project_dir, cloud?, must_block)
    ("commit on unattended/<date>", "git commit -m x", UNATT, False, False),
    ("compound commit on unattended", "cd . && git commit -m x", UNATT, False, False),
    ("commit -C form on unattended", "git -C . commit -m x", UNATT, False, False),
    ("commit on main", "git commit -m x", MAIN, False, True),
    ("compound commit on main", "cd . && git commit -m x", MAIN, False, True),
    ("commit -C form on main", "git -C . commit -m x", MAIN, False, True),
    ("commit on an ordinary feature branch", "git commit -m x", FEAT, False, True),
    ("push into main: refused by the hook itself (board 017)", "git push origin main", MAIN, False, True),
    ("push on a feature branch: allowed by the hook", "git push origin feat/x", FEAT, False, False),
    ("force-push blocked everywhere, unattended included", FORCE_PUSH, UNATT, False, True),
    ("ordinary staging on main", "git add .", MAIN, False, False),
    ("status on unattended", "git status", UNATT, False, False),
    ("commit on a suffixed unattended branch", "git commit -m x", SUFFIXED, False, False),
    # --- by environment: the cloud switch ---------------------------------------------------
    ("local, session branch, switch on: refused (not a cloud session)", "git commit -m x", CLOUD_ON, False, True),
    ("cloud, no project.env: refused (switch defaults to off)", "git commit -m x", CLOUD_OFF, True, True),
    ("cloud, switch explicitly off: refused", "git commit -m x", CLOUD_OFF_EXPLICIT, True, True),
    ("cloud, switch on, session branch: allowed", "git commit -m x", CLOUD_ON, True, False),
    ("cloud, switch on, compound form: allowed", "cd . && git commit -m x", CLOUD_ON, True, False),
    ("cloud, switch on, on main: still refused (protected)", "git commit -m x", CLOUD_ON_MAIN, True, True),
    ("cloud, switch on: force push still blocked", FORCE_PUSH, CLOUD_ON, True, True),
    ("cloud, unattended branch: allowed regardless of the switch", "git commit -m x", UNATT, True, False),
]

fails = []
for name, cmd, root, cloud, must_block in CASES:
    got = blocked(cmd, root, cloud=cloud)
    ok = got == must_block
    verdict = "BLOCK" if got else "allow"
    print(f"  {'ok  ' if ok else 'FAIL'} {name:68} -> {verdict}")
    if not ok:
        fails.append(f"{name}: expected {'BLOCK' if must_block else 'allow'}, got {verdict}")

# --- the block message names the subcommand, not the second word of the command ------------
r = run_hook("git -C . commit -m x", MAIN)
ok = "direct git commit on protected branch" in r.stderr
print(f"  {'ok  ' if ok else 'FAIL'} {'block message names the subcommand (commit), not the second word (-C)':68} -> {r.stderr.splitlines()[0] if r.stderr else ''}")
if not ok:
    fails.append(f"message does not name the subcommand: {r.stderr!r}")

# --- push is governed by the settings file: ask prompts, force forms denied ------------------
for path in SETTINGS:
    perms = json.loads(path.read_text(encoding="utf-8"))["permissions"]
    checks = [
        (f"{path.name}: {PUSH_RULE} is in ask", PUSH_RULE in perms["ask"]),
        (f"{path.name}: the force-push forms are in deny", all(rule in perms["deny"] for rule in FORCE_RULES)),
        (f"{path.name}: no push rule in allow", not any("git push" in rule for rule in perms["allow"])),
    ]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        if not ok:
            fails.append(name)

print()
if fails:
    print(f"FAIL ({len(fails)}):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
total = len(CASES) + 1 + 3 * len(SETTINGS)
print(f"PASS {total}/{total} commit-policy cases")
