#!/usr/bin/env python3
"""The DAG supervisor is retired: unattended work goes through the task board only (board 039).

Three things are held here:

- the supervisor's files are gone from the engine, and what the board uses is still there;
- no working file of this repository points at `supervisor.sh` (closed records — the board's
  done tasks, the engine's own ledgers and plans, recorded baselines — keep their history);
- `engine.py update` takes the retired files out of a project that was installed from a version
  which shipped them (the real v0.11.0), leaves in place one the project had edited and says so,
  and touches neither the project's own files nor the machine state the supervisor left behind.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
OLD_REAL = "v0.11.0"
UNATTENDED = ".claude/unattended/"
RETIRED = ("supervisor.sh", "runstate.py", "session-claude.sh", "session-sim.sh", "watch.sh", "rotate.sh",
           "config.sh", "claude-unattended.service", "recheck_parked.py")
KEPT = ("board-runner.sh", "board.py", "board_state.py", "board_review.py", "owner_action.py", "settings_check.py",
        "commit_checkpoint.sh", "env-probe.sh", "README.md")
# Closed records: they say what was true when they were written.
HISTORY = ("tasks/", ".engine/", "docs/plan/", "evals/baseline/")
PASS = FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail[:900]}")


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), capture_output=True, text=True, cwd=cwd, check=False)


print("1. The engine itself")
for name in RETIRED:
    check(f"{name} is gone", not (ROOT / UNATTENDED / name).exists())
for name in KEPT:
    check(f"{name} is still there", (ROOT / UNATTENDED / name).is_file())
check("the feature DAG is untouched: /feature-architect still plans into it", (ROOT / ".engine/architecture/feature-dag.json").is_file())

print("2. No working file points at the supervisor")
tracked = run("git", "ls-files", "-z").stdout.split("\0")
me = Path(__file__).resolve().relative_to(ROOT).as_posix()
live = []
for rel in tracked:
    if not rel or rel == me or rel.startswith(HISTORY) or not (ROOT / rel).is_file():
        continue
    text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    if any(word in text for word in ("supervisor.sh", "runstate.py", "session-claude", "session-sim", "recheck_parked")):
        live.append(rel)
check("no tracked working file names a retired script", not live, str(live))

print(f"3. A project installed from {OLD_REAL}, updated to HEAD")
if run("git", "rev-parse", "-q", "--verify", f"{OLD_REAL}^{{commit}}").returncode != 0:
    print(f"  skip  the tag {OLD_REAL} is not in this clone")
elif run("git", "cat-file", "-e", f"HEAD:{UNATTENDED}supervisor.sh").returncode == 0:
    print("  skip  HEAD still ships the supervisor: the removal is not committed yet")
else:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "project"
        p.mkdir()
        run("git", "init", "-q", "-b", "main", cwd=p)
        r = run(sys.executable, str(ENGINE_PY), "install", str(p), "--ref", OLD_REAL)
        check("the old version installs, supervisor and all", r.returncode == 0 and all((p / UNATTENDED / n).is_file() for n in RETIRED), r.stdout[-400:] + r.stderr)
        edited = p / UNATTENDED / "config.sh"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nCOST_CAP_USD=5.00   # this project's own cap\n", encoding="utf-8")
        own = {"src/app.py": "print('the project')\n", "tasks/todo/010-mine.md": "# 010 — the project's task\n",
               ".claude/state/unattended/state.json": '{"status": "finished"}\n'}
        for rel, text in own.items():
            (p / rel).parent.mkdir(parents=True, exist_ok=True)
            (p / rel).write_text(text, encoding="utf-8")
        r = run(sys.executable, str(ENGINE_PY), "update", str(p), "--ref", "HEAD")
        out = r.stdout + r.stderr
        gone = [n for n in RETIRED if n != "config.sh"]
        check("every untouched retired file is removed", not [n for n in gone if (p / UNATTENDED / n).exists()], out[-900:])
        check("…and the report names each as retired", all(f"remove  {UNATTENDED}{n}" in out for n in gone), out[-900:])
        check("the one the project edited stays, and the report says why",
              "this project's own cap" in edited.read_text(encoding="utf-8") and "retired by the engine but edited in the project" in out, out[-900:])
        check("the board's files arrived", all((p / UNATTENDED / n).is_file() for n in KEPT), out[-900:])
        check("the project's own files and the old run's state are as they were",
              all((p / rel).read_text(encoding="utf-8") == text for rel, text in own.items()))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
