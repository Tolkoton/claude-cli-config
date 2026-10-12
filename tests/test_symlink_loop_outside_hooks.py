#!/usr/bin/env python3
"""A path that is a symlink loop gets the script's written answer, not a traceback (board 719).

Fix 005 covered the hooks, the board scripts and the installer; these are the same places outside
them — `.engine/bugs/008-resolve-loop-outside-hooks.md`:
  - doc_audit.py: a Markdown link to a loop is a broken link, like a link to a missing file;
  - evals/run_audit_scenarios.py --tasks-dir <loop>: the refusal «no task of this session»;
  - evals/environment.py: a loop outside evals/baseline/ lies in no environment's folder;
  - evals/run_hook_scenarios.py: a setup step that writes through a loop and a project_dir that
    is a loop are the runner's `sandbox error`; --hooks-dir <loop> ships no hook (`absent`).
Up to Python 3.12 `Path.resolve()` raises RuntimeError on a loop, from 3.13 it raises nothing: the
cases hold on both. Every loop case has its negative next to it. No session and no real sandbox:
the hook runner gets a synthetic one (a git repository with SANDBOX-INFO.json and one hook).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
DOC_AUDIT = ROOT / ".claude/skills/documentation/scripts/doc_audit.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[-600:]}")


work = Path(tempfile.mkdtemp(prefix="loop-outside-hooks-"))
loop = work / "loop"
loop.symlink_to("loop")
ENV = {k: v for k, v in hook_env(work).items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}


def run(*argv: object, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True, cwd=cwd, env=ENV, check=False)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, text=True, check=True)


def shown(r: subprocess.CompletedProcess[str]) -> str:
    return f"rc={r.returncode} {r.stdout[-300:]} {r.stderr[-300:]}"


print("doc_audit.py: a Markdown link to a symlink loop")
docs = work / "docs-repo"
docs.mkdir()
git(docs, "init", "-q")
(docs / "loop.txt").symlink_to("loop.txt")
(docs / "real.txt").write_text("x\n", encoding="utf-8")
(docs / "README.md").write_text("# R\n\n[a](loop.txt)\n[b](missing.txt)\n[c](sub/../real.txt)\n", encoding="utf-8")
r = run(DOC_AUDIT, "--root", docs)
check("a link to a symlink loop is a broken link, not a traceback (board 719)",
      r.returncode == 1 and "README.md:3 - broken link to 'loop.txt'" in r.stdout and "Traceback" not in r.stderr, shown(r))
check("negative: a link to a missing file is a broken link", "README.md:4 - broken link to 'missing.txt'" in r.stdout, shown(r))
check("negative: a link through `..` to a real file is still resolved and found", "README.md:5" not in r.stdout, shown(r))

print("run_audit_scenarios.py: --tasks-dir that is a symlink loop")
REFUSAL = "refusing to start paid sessions: no task of this session is in"
r = run(EVALS / "run_audit_scenarios.py", "--only", "no-such-scenario-zz", "--tasks-dir", loop)
check("--tasks-dir that is a symlink loop holds no task: refused, not a traceback (board 719)",
      r.returncode == 2 and REFUSAL in r.stderr and "Traceback" not in r.stderr, shown(r))
r = run(EVALS / "run_audit_scenarios.py", "--only", "no-such-scenario-zz", "--tasks-dir", work / "none")
check("negative: a --tasks-dir that does not exist is refused the same way", r.returncode == 2 and REFUSAL in r.stderr, shown(r))
r = run(EVALS / "run_audit_scenarios.py", "--only", "no-such-scenario-zz", "--tasks-dir", ROOT / "tests/fixtures/x/../board-audit-yes")
check("negative: a board that says «так», given through `..`, is still resolved and let past the gate",
      r.returncode == 2 and "refusing to start paid sessions" not in r.stderr and "Traceback" not in r.stderr, shown(r))  # its next check stops it

print("environment.py: the folder of a path that is a symlink loop")
spec = importlib.util.spec_from_file_location("environment", EVALS / "environment.py")
assert spec and spec.loader
environment: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)
here = environment.environment_name()
try:
    folder: object = environment.baseline_folder(loop)
except RuntimeError as exc:
    folder = f"{type(exc).__name__}: {exc}"
check("a symlink loop outside evals/baseline/ lies in no environment's folder, no exception (board 719)", folder is None, folder)
check("negative: a missing path outside evals/baseline/ lies in none either", environment.baseline_folder(work / "none") is None)
check("negative: a path into this environment's folder, given through `..`, is still resolved",
      environment.baseline_folder(EVALS / "baseline" / "x" / ".." / here / "r.json") == here)
r = run(EVALS / "run_hook_scenarios.py", "--engine-ref", "HEAD", "--out", loop, "--sandbox", work)
check("a runner given --out <loop> gets past the argument (it stops at its next refusal), no traceback",
      r.returncode == 2 and "give exactly one of --sandbox and --engine-ref" in r.stderr and "Traceback" not in r.stderr, shown(r))

print("run_hook_scenarios.py: a loop inside the sandbox, and --hooks-dir")
sandbox = work / "sandbox"
(sandbox / ".claude" / "hooks").mkdir(parents=True)
(sandbox / "sub").mkdir()
(sandbox / "sub" / "keep").write_text("", encoding="utf-8")
(sandbox / ".claude" / "hooks" / "h.sh").write_text("exit 0\n", encoding="utf-8")
(sandbox / "SANDBOX-INFO.json").write_text("{}\n", encoding="utf-8")
(sandbox / "lp").symlink_to("lp")
git(sandbox, "init", "-q", "-b", "main")
git(sandbox, "add", "-A")
git(sandbox, "commit", "-q", "-m", "sandbox")


def scenarios(name: str, scenario: dict[str, Any]) -> Path:
    folder = work / f"scenarios-{name}"
    folder.mkdir()
    (folder / "a.json").write_text(json.dumps({"hook": "h.sh", "scenarios": [{"id": name, "expect": "allow", "input": {}, **scenario}]}),
                                   encoding="utf-8")
    return folder


def hooks(name: str, scenario: dict[str, Any], *extra: object) -> subprocess.CompletedProcess[str]:
    return run(EVALS / "run_hook_scenarios.py", "--sandbox", sandbox, "--scenarios", scenarios(name, scenario), *extra)


def sandbox_error(r: subprocess.CompletedProcess[str]) -> bool:
    return r.returncode == 2 and "sandbox error:" in r.stderr and "Traceback" not in r.stderr


r = hooks("write-loop", {"setup": [{"write": {"path": "lp/x.txt", "content": "x"}}]})
check("a setup step that writes through a symlink loop is a sandbox error, not a traceback (board 719)", sandbox_error(r), shown(r))
r = hooks("write-outside", {"setup": [{"write": {"path": "../x.txt", "content": "x"}}]})
check("negative: a setup step that writes outside the sandbox is a sandbox error",
      sandbox_error(r) and "setup writes outside the sandbox" in r.stderr and not (work / "x.txt").exists(), shown(r))
r = hooks("write-inside", {"setup": [{"write": {"path": "new/dir/../x.txt", "content": "x"}}], "check_file": "new/x.txt",
                           "expect_file_changed": False})
check("negative: a setup step that writes inside the sandbox, through a new directory and `..`, runs", r.returncode == 0 and "ok   write-inside" in r.stdout, shown(r))
r = hooks("dir-loop", {"project_dir": "lp"})
check("a project_dir that is a symlink loop is a sandbox error, not a traceback (board 719)", sandbox_error(r), shown(r))
r = hooks("dir-outside", {"project_dir": ".."})
check("negative: a project_dir outside the sandbox is a sandbox error", sandbox_error(r) and "project_dir escapes the sandbox" in r.stderr, shown(r))
r = hooks("dir-inside", {"project_dir": "sub/../sub"})
check("negative: a project_dir inside the sandbox, through `..`, runs", r.returncode == 0 and "ok   dir-inside" in r.stdout, shown(r))
r = hooks("hooks-loop", {"expect": "absent"}, "--hooks-dir", loop)
check("--hooks-dir that is a symlink loop ships no hook: absent, not a traceback (board 719)",
      r.returncode == 0 and "ok   hooks-loop" in r.stdout and "absent" in r.stdout and "Traceback" not in r.stderr, shown(r))
r = hooks("hooks-none", {"expect": "absent"}, "--hooks-dir", work / "none")
check("negative: a --hooks-dir that does not exist ships none either", r.returncode == 0 and "absent" in r.stdout, shown(r))
r = hooks("hooks-real", {}, "--hooks-dir", sandbox / "sub" / ".." / ".claude" / "hooks", "--out", work / "out.json")
recorded = json.loads((work / "out.json").read_text(encoding="utf-8"))["hooks_dir"] if (work / "out.json").is_file() else None
check("negative: a --hooks-dir given through `..` is still resolved (the record names it so) and its hook runs",
      r.returncode == 0 and "ok   hooks-real" in r.stdout and "allow" in r.stdout and recorded == "<SANDBOX>/.claude/hooks", f"{recorded} {shown(r)}")

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
