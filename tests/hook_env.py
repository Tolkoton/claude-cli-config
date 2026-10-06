"""The environment a suite hands to a hook it runs: CLAUDE_PROJECT_DIR pinned to a sandbox.

    from hook_env import hook_env, main_repo

    subprocess.run(["bash", str(HOOK)], input=..., env=hook_env())             # a fresh empty directory
    subprocess.run(["bash", str(HOOK)], input=..., env=hook_env(main_repo()))  # a repository on `main`
    subprocess.run([...], env=hook_env(root, PATH=shims))                      # the suite's own project

WHY. The Stop gate runs TEST_CMD with CLAUDE_PROJECT_DIR naming this repository; by hand the
variable is unset. A suite that lets a hook inherit it answers differently from the gate than
by hand: on an unattended/* branch block-dangerous.sh ALLOWED the commit cases of
tests/test_deny_gaps.py (2026-10-02, package 3c fix, X7), and test_deny_hooks.py had needed
the same pin before it. hook_env() never returns the inherited value, so the mistake cannot be
made through it; tests/test_hook_env.py refuses a new suite that runs a hook without it.
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def sandbox_dir(prefix: str = "hook-env-") -> str:
    """A fresh empty directory, removed when the suite exits."""
    root = tempfile.mkdtemp(prefix=prefix)
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    return root


def main_repo(branch: str = "main") -> str:
    """A throwaway repository with one commit, checked out on `branch`: for a hook whose answer
    depends on the branch of CLAUDE_PROJECT_DIR (block-dangerous.sh's commit rule)."""
    root = sandbox_dir("hook-env-repo-")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    Path(root, "f.txt").write_text("x", encoding="utf-8")
    git("add", "f.txt")
    git("commit", "-qm", "init")
    git("branch", "-M", branch)
    return root


def hook_env(project: str | os.PathLike[str] | None = None, **extra: str) -> dict[str, str]:
    """The caller's environment with CLAUDE_PROJECT_DIR set to `project` — a fresh empty
    directory when none is given — and `extra` laid over it. The project is the suite's own
    sandbox, never the inherited value: `extra` may not carry the variable."""
    if "CLAUDE_PROJECT_DIR" in extra:
        raise ValueError("hook_env: pass the project as the first argument, not as CLAUDE_PROJECT_DIR=")
    return {**os.environ, **extra, "CLAUDE_PROJECT_DIR": str(project) if project is not None else sandbox_dir()}
