#!/usr/bin/env python3
"""Sealed goals hand off to the architect without a command from the owner (board 205).

Against a temporary project:

  - attended: the first `goals.py seal` of a new project prints `NEXT: /master-architect`, and
    `/business-analyst` tells the agent to start the skill itself in the same session on that line;
  - no hand-off when the architecture has begun (the traceability matrix or a map exists), on a
    second `seal` of the same document, on the owner's re-seal of a changed document and after
    an amendment (`amend`): there `.engine/goals/to-review.md` is the architects' work;
  - unattended: `board.py architect-task` puts `NNN-master-architect.md` into todo/ with
    `Потрібна присутність власника: так` — only when the goals are sealed, the architecture has
    not begun and no such task lies in any column; `board.py next` never offers it.
  (The runner calls it after `seal-goals` applied and never after `amend-goals`: tests/test_board_runner.py, board 205.)

Run:   python3 tests/test_goals_handoff.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOALS = ROOT / ".claude/hooks/goals.py"
BOARD = ROOT / ".claude/unattended/board.py"
OWNER_ACTION = ROOT / ".claude/unattended/owner_action.py"
COMMAND = ROOT / ".claude/commands/business-analyst.md"
NEXT = "NEXT: /master-architect"
PASS = FAIL = 0

DOCUMENT = """# Цілі проєкту крамниця
Версія: 1

## Ядро
- G1 — «щоб покупець усе робив сам»

## Цілі
- G1. Покупець оформлює замовлення сам.

## Не-цілі
- N1. Не робимо мобільного застосунку.

## Зміни
- v1 — перша версія.
"""


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def run(script: Path, root: Path, *args: str, session: bool = False, unattended: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    env["CLAUDE_PROJECT_DIR"] = str(root)
    if session:
        env["CLAUDECODE"] = "1"
    if unattended:
        env["CLAUDE_UNATTENDED_SESSION"] = "1"
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env, check=False)


def project(tmp: str) -> Path:
    root = Path(tmp)
    (root / ".engine/goals").mkdir(parents=True)
    (root / ".engine/goals.md").write_text(DOCUMENT, encoding="utf-8")
    for column in ("todo", "doing", "blocked", "done", "proposed"):
        (root / "tasks" / column).mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def out(proc: subprocess.CompletedProcess[str]) -> str:
    return f"rc={proc.returncode} {proc.stdout} {proc.stderr}"


def todo(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "tasks/todo").glob("*.md"))


print("attended: the first seal of a new project hands off to the architect")
with tempfile.TemporaryDirectory() as tmp:
    root = project(tmp)
    r = run(GOALS, root, "seal", session=True)
    check("the first seal, attended, in a new project: sealed and `NEXT: /master-architect`", r.returncode == 0 and NEXT in r.stdout, out(r))
    check("…the line says the approvals stay the owner's", "«Читання цілей»" in r.stdout and "approvals stay the owner's" in r.stdout, out(r))
    r = run(GOALS, root, "seal", session=True)
    check("the same document sealed again: no second hand-off", r.returncode == 0 and NEXT not in r.stdout, out(r))
    text = COMMAND.read_text(encoding="utf-8")
    check("/business-analyst starts the skill itself on that line, in the same session, without a command from the owner",
          f"`{NEXT}`" in text and "start `/master-architect` yourself in this session" in text and "`master-architect`" in text, "")
    check("…and it says only the start is automatic", "Only the start is automatic" in text, "")

print("the architecture has begun: no hand-off")
for rel in (".engine/architecture/traceability.md", ".engine/architecture/domain-map.md", ".engine/architecture/architecture-map.md"):
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("# begun\n", encoding="utf-8")
        r = run(GOALS, root, "seal", session=True)
        check(f"{rel} exists: sealed, no `NEXT`", r.returncode == 0 and NEXT not in r.stdout, out(r))

print("a change to the sealed document: no hand-off")
with tempfile.TemporaryDirectory() as tmp:
    root = project(tmp)
    run(GOALS, root, "seal", session=True)
    (root / ".engine/goals.md").write_text(DOCUMENT + "- G2. Ще одна.\n", encoding="utf-8")
    r = run(GOALS, root, "seal", "--owner-approved")
    check("the owner's re-seal of a changed document in their terminal: no `NEXT`", r.returncode == 0 and NEXT not in r.stdout, out(r))
    proposed = root / ".engine/goals/proposed.md"
    proposed.write_text((DOCUMENT + "- G2. Ще одна.\n- G3. Третя.\n").replace("Версія: 1", "Версія: 2")
                        .replace("- v1 — перша версія.", "- v1 — перша версія.\n- v2 — G3."), encoding="utf-8")
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", hashlib.sha256(proposed.read_bytes()).hexdigest())
    check("an amendment on the owner's «так»: applied, no `NEXT`", r.returncode == 0 and NEXT not in r.stdout + r.stderr, out(r))

print("unattended: the architecture task on the board")
with tempfile.TemporaryDirectory() as tmp:
    root = project(tmp)
    r = run(BOARD, root, "--root", str(root), "architect-task")
    check("goals not sealed: no task", r.returncode == 0 and not r.stdout.strip() and todo(root) == [], out(r))
    sha = hashlib.sha256((root / ".engine/goals.md").read_bytes()).hexdigest()
    r = run(OWNER_ACTION, root, "--root", str(root), "seal-goals", sha)
    check("seal-goals on the owner's «так»: sealed", r.returncode == 0, out(r))
    r = run(BOARD, root, "--root", str(root), "architect-task")
    names = todo(root)
    task = (root / "tasks/todo" / names[0]).read_text(encoding="utf-8") if names else ""
    check("sealed, a new project: NNN-master-architect.md in todo/, a number of the runner's class",
          r.returncode == 0 and len(names) == 1 and names[0].endswith("-master-architect.md") and names[0].startswith("4"), out(r) + str(names))
    check("…with the owner present, and no audit", "\nПотрібна присутність власника: так\n" in task and "\nАудит потрібен: ні\n" in task, task)
    check("…it runs /master-architect from «Читання цілей», approvals the owner's", "`/master-architect`" in task and "«Читання цілей»" in task
          and "Art. 5" in task, task)
    r = run(BOARD, root, "--root", str(root), "check")
    check("the board finds nothing wrong with it", r.returncode == 0 and "ПОМИЛКА" not in r.stdout, out(r))
    r = run(BOARD, root, "--root", str(root), "next")
    check("the runner's `next` does not offer it", "master-architect" not in r.stdout, out(r))
    r = run(BOARD, root, "--root", str(root), "next", "--attended")
    check("…the owner's attended session does", "master-architect" in r.stdout, out(r))
    r = run(BOARD, root, "--root", str(root), "architect-task")
    check("asked again: one already in todo/, nothing placed", not r.stdout.strip() and todo(root) == names, out(r))
    for name in names:
        (root / "tasks/done" / name.removesuffix(".md")).mkdir()
        (root / "tasks/todo" / name).rename(root / "tasks/done" / name.removesuffix(".md") / "task.md")
    r = run(BOARD, root, "--root", str(root), "architect-task")
    check("…one in done/: nothing placed either", not r.stdout.strip() and todo(root) == [], out(r))

with tempfile.TemporaryDirectory() as tmp:
    root = project(tmp)
    run(OWNER_ACTION, root, "--root", str(root), "seal-goals", hashlib.sha256((root / ".engine/goals.md").read_bytes()).hexdigest())
    (root / ".engine/architecture").mkdir(parents=True)
    (root / ".engine/architecture/traceability.md").write_text("# begun\n", encoding="utf-8")
    r = run(BOARD, root, "--root", str(root), "architect-task")
    check("sealed, but the architecture has begun: no task", r.returncode == 0 and not r.stdout.strip() and todo(root) == [], out(r))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
