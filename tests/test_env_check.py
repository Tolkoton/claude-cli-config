#!/usr/bin/env python3
"""env-check.sh: silent on a complete machine, specific on an incomplete one, never failing."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "env-check.sh"
PASS = FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


def path_with(*tools: str) -> str:
    d = Path(tempfile.mkdtemp(prefix="envcheck-"))
    for tool in tools:
        src = shutil.which(tool)
        if src:
            os.symlink(src, d / tool)
    return str(d)


def run(project: Path, path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOK)], capture_output=True, text=True,
        env={"PATH": path, "CLAUDE_PROJECT_DIR": str(project), "HOME": os.environ.get("HOME", "/")}, check=False)


bash = shutil.which("bash")
assert bash, "bash is required to run this test"

plain = Path(tempfile.mkdtemp(prefix="envcheck-plain-"))          # no pyproject.toml
uvproj = Path(tempfile.mkdtemp(prefix="envcheck-uv-"))
(uvproj / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
(uvproj / "uv.lock").write_text("")
bare = Path(tempfile.mkdtemp(prefix="envcheck-bare-"))            # configured, no lock file
(bare / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")

full = path_with("bash", "git", "grep", "python3", "jq", "uv")
res = run(plain, full)
check("complete machine, plain project: silent", res.returncode == 0 and res.stdout == "", res.stdout[:80])

res = run(uvproj, path_with("bash", "git", "grep", "python3", "jq"))
check("uv.lock but no uv: names uv", res.returncode == 0 and "- uv " in res.stdout, res.stdout[:80])

res = run(plain, path_with("bash", "git", "grep", "jq"))
check("no python3: names the three Python hooks", "overseer_stop.py" in res.stdout, res.stdout[:80])
check("no python3 but jq present: does NOT claim the deny hooks refuse", "REFUSE" not in res.stdout)

res = run(plain, path_with("bash", "git", "grep"))
check("neither jq nor python3: says the deny hooks will refuse", "REFUSE" in res.stdout, res.stdout[:80])

res = run(plain, path_with("bash", "git", "grep", "python3"))
check("python3 without jq: silent (the hooks fall back, nothing is lost that matters)",
      res.stdout == "", res.stdout[:80])

res = run(bare, path_with("bash", "git", "grep", "python3", "jq"))
check("ruff/mypy configured, no lock file, not on PATH: names both",
      "- ruff " in res.stdout and "- mypy " in res.stdout, res.stdout[:80])

res = run(plain, path_with("bash", "grep", "python3", "jq"))
check("no git: says so and still exits 0", res.returncode == 0 and "- git " in res.stdout, res.stdout[:80])

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
