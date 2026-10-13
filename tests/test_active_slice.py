#!/usr/bin/env python3
"""The active slice of a pipeline task (board 789): nobody marks a slice IN PROGRESS there, so
the scripts name it themselves — the last slice testing.py opened under the session's board task.

  * the audit request of a project with a sealed contract and a task in the mode «конвеєр» names
    the slice and the sha256 of its contract, and two slices of one task have two unit keys;
  * the same reading is the complexity budget's contract and the testing gate's slice;
  * negative, each beside the case that passes: no row, a row of another task, a row without a
    task (written before 789), a parked slice, a contract that is gone, no task in doing/;
  * a card IN PROGRESS in .engine/PROGRESS.md still wins, whatever it names.

Run:   python3 tests/test_active_slice.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import complexity_budget
import gate
import testing
from hook_env import hook_env

WIRED = json.dumps({"hooks": {"SubagentStop": [{"matcher": "overseer", "hooks": [
    {"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py" record'}]}]}})
TASK = "010-todo-cli"
CLAIM = "Implemented add.\n\n    $ pytest -q\n    6 passed\n\n=== UNIT 1 COMPLETE ===\n"

failures: list[str] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"   [{str(detail)[:300]}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def contract(slug: str) -> str:
    return f"# Slice {slug} — planning artifact\n\n## Goal\nThe command {slug}.\n\n## Seam\n`src/todo.py`\n"


class Project:
    """A project as the pipeline leaves it before the builder's first line: sealed contracts, a task in doing/."""

    def __init__(self, task: str | None = TASK) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="active-slice-")).resolve() / "project"
        for rel, text in ((".gitignore", ".claude/state/\n"), (".claude/settings.json", WIRED), ("src/todo.py", "def add():\n    return 1\n"),
                          (".engine/slices/add-cmd.md", contract("add-cmd")), (".engine/slices/list-cmd.md", contract("list-cmd")),
                          (".engine/PROGRESS.md", "# PROGRESS\n\n## Slice older — DONE (overseer PASS)\nContract: `.engine/slices/older.md`\n")):
            self.write(rel, text)
        if task:
            self.write(f"tasks/doing/{task}.md", f"# {task[:3]} — the todo CLI\n\nРежим: конвеєр\n\n## Що зробити\nThe CLI.\n")
        for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        for slug in ("add-cmd", "list-cmd"):
            self.run("contract_fingerprint.py", "seal", f".engine/slices/{slug}.md")

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(HOOKS / script), *args], capture_output=True, text=True, cwd=self.root,
                              env=hook_env(str(self.root), CLAUDE_UNATTENDED_SESSION="1"), check=False)

    def open(self, slug: str) -> subprocess.CompletedProcess[str]:
        """What the builder does before any code of a slice (slice-builder, Step 2a)."""
        return self.run("testing.py", "request", slug, "--point", "a")

    def decide(self, slug: str, point: str) -> None:
        testing.append_row(self.root, {"type": "decision", "slice": slug, "point": point, "decision": "builder", "request": "none"}, "decided", [])
        shutil.rmtree(self.root / ".claude/state/testing/requests", ignore_errors=True)
        (self.root / ".claude/state/testing/pending.json").unlink(missing_ok=True)

    def audit(self) -> dict[str, object]:
        """The request package of a unit claimed now, as `overseer_verdict.py request` writes it."""
        shutil.rmtree(self.root / ".claude/state/overseer", ignore_errors=True)
        self.write("turn.md", CLAIM)
        done = self.run("overseer_verdict.py", "request", "--turn-file", "turn.md")
        found = sorted((self.root / ".claude/state/overseer/requests").glob("*/request.json"))
        if not found:
            return {"error": done.stdout + done.stderr}
        loaded: dict[str, object] = json.loads(found[-1].read_text(encoding="utf-8"))
        return loaded


def sha(project: Project, slug: str) -> str:
    return hashlib.sha256((project.root / f".engine/slices/{slug}.md").read_bytes()).hexdigest()


print("board 789: the audit request of a pipeline task names the slice and its contract")
p = Project()
check("negative — before any slice opens there is no active slice", gate.active_slice(p.root) is None, gate.active_slice(p.root))
opened = p.open("add-cmd")
check("the builder opens the slice with testing.py (point a)", opened.returncode == 0 and "TESTING_REQUEST" in opened.stdout, opened.stdout + opened.stderr)
row = testing.last(p.root, "add-cmd", "opened") or {}
check("the row of the opening names the board task", row.get("task") == TASK, row)
first = p.audit()
check("the audit request names the slice", first.get("slice") == "add-cmd", first)
check("… and the sha256 of its sealed contract",
      first.get("contract") == {"path": ".engine/slices/add-cmd.md", "sha256": sha(p, "add-cmd")}, first.get("contract"))
check("… and the unit key starts with the slice", first.get("unit_key") == f"add-cmd|{TASK}|unit 1", first.get("unit_key"))
check("the Stop hook's reading of a changed contract has its contract", gate.active_slice(p.root) == "add-cmd")
check("the complexity budget measures that contract",
      complexity_budget.active_contract(p.root) == p.root / ".engine/slices/add-cmd.md", complexity_budget.active_contract(p.root))
(p.root / ".engine/PROGRESS.md").rename(p.root / ".engine/PROGRESS.away")
check("… and both read it in a project that has no .engine/PROGRESS.md yet",
      gate.active_slice(p.root) == "add-cmd" and complexity_budget.active_contract(p.root) == p.root / ".engine/slices/add-cmd.md")
(p.root / ".engine/PROGRESS.away").rename(p.root / ".engine/PROGRESS.md")
said = testing.audit_block(p.root, gate.active_slice(p.root)) or ""
check("the testing gate holds the audit of that slice until point (a) is decided", "no decision of the testing manager at point (a)" in said, said)

print("the second slice of the same task")
p.decide("add-cmd", "a")
check("a decided point (a) lets the audit through", testing.audit_block(p.root, gate.active_slice(p.root)) is None)
p.decide("add-cmd", "b")
check("after point (b) the slice is still the active one (its audit may follow)", gate.active_slice(p.root) == "add-cmd")
opened = p.open("list-cmd")
check("the next slice opens", opened.returncode == 0, opened.stdout + opened.stderr)
second = p.audit()
check("its audit request names the second slice and its contract",
      second.get("slice") == "list-cmd" and second.get("contract") == {"path": ".engine/slices/list-cmd.md", "sha256": sha(p, "list-cmd")}, second)
check("two slices of one task have two unit keys (the count of three BLOCKs is not shared)",
      second.get("unit_key") == f"list-cmd|{TASK}|unit 1" and second.get("unit_key") != first.get("unit_key"), second.get("unit_key"))

print("negative: what does not make a slice active")
testing.append_row(p.root, {"type": "parked", "slice": "list-cmd"}, "parked", [])
check("a parked slice is not active, and the one before it does not come back", gate.active_slice(p.root) is None, gate.active_slice(p.root))

p = Project()
p.open("add-cmd")
(p.root / f"tasks/doing/{TASK}.md").rename(p.root / "tasks/doing/011-other.md")
check("a slice opened under another task is not this task's", gate.active_slice(p.root) is None, gate.active_slice(p.root))
(p.root / "tasks/doing/011-other.md").rename(p.root / f"tasks/doing/{TASK}.md")
check("… and is again when its task is back in doing/", gate.active_slice(p.root) == "add-cmd", gate.active_slice(p.root))
(p.root / f"tasks/doing/{TASK}.md").unlink()
check("with no task in doing/ nothing is active", gate.active_slice(p.root) is None, gate.active_slice(p.root))
unknown = p.audit()
check("… and the audit request says so as before", unknown.get("slice") == "unknown" and unknown.get("contract") is None, unknown)

p = Project()
testing.append_row(p.root, {"type": "opened", "slice": "add-cmd", "base": "HEAD"}, "opened", [])
check("a row without a task (written before 789) names no active slice", gate.active_slice(p.root) is None, gate.active_slice(p.root))
testing.append_row(p.root, {"type": "opened", "slice": "list-cmd", "base": "HEAD", "task": TASK}, "opened", [])
check("positive — the same row with the task does", gate.active_slice(p.root) == "list-cmd", gate.active_slice(p.root))
(p.root / ".engine/slices/list-cmd.md").unlink()
check("a slice whose contract is gone is not active", gate.active_slice(p.root) is None, gate.active_slice(p.root))

p = Project(task=None)
opened = p.open("add-cmd")
check("without a board task the slice opens as before", opened.returncode == 0 and (testing.last(p.root, "add-cmd", "opened") or {}).get("task") == "", opened.stdout + opened.stderr)
check("… and nothing is active: the card IN PROGRESS is the only way there", gate.active_slice(p.root) is None, gate.active_slice(p.root))

print("a card IN PROGRESS still wins")
p = Project()
p.open("add-cmd")
p.write(".engine/PROGRESS.md", "# PROGRESS\n\n## Slice list-cmd — IN PROGRESS\nContract: `.engine/slices/list-cmd.md`\n")
check("the slice of the card, not of the row", gate.active_slice(p.root) == "list-cmd", gate.active_slice(p.root))
check("… for the budget too", complexity_budget.active_contract(p.root) == p.root / ".engine/slices/list-cmd.md")
p.write(".engine/PROGRESS.md", "# PROGRESS\n\n## Bugfix 003-y — DONE\n- Surprises: the smoke was in progress for an hour.\n")
check("the words «in progress» in the body of a finished bug fix's entry mark nothing: the row is read", gate.active_slice(p.root) == "add-cmd", gate.active_slice(p.root))
p.write(".engine/bugs/007-x.md", "# Bug 007\n")
p.write(".engine/PROGRESS.md", "# PROGRESS\n\n## Bugfix 007-x — IN PROGRESS\nBug record: `.engine/bugs/007-x.md`\n")
check("a bug record IN PROGRESS is the work in hand: no slice is active", gate.active_slice(p.root) is None, gate.active_slice(p.root))
check("… and the budget measures the bug record", complexity_budget.active_contract(p.root) == p.root / ".engine/bugs/007-x.md")

print(f"\n{'PASS' if not failures else 'FAIL'}: {len(failures)} failed" + "".join(f"\n  - {name}" for name in failures))
sys.exit(1 if failures else 0)
