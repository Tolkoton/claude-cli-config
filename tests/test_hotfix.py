#!/usr/bin/env python3
"""/hotfix — the urgent fix that leaves a debt (board 075): the hard limit, the debt, the three-debts question.

WHY. Urgency lifts the ceremony, not the checks. What is put off — the test before the code, the
record of the cause, the search for the same places — becomes a debt a script writes down, and
the size of an urgent fix is a hard limit: over it the turn is blocked, the simplifier is not
asked. Without the limit "urgent" quietly becomes the ordinary way to work.

Deterministic: every scene runs the real hotfix.py and complexity_budget.py in a throwaway git
repository. The blocks come first: the limit is shown to BLOCK before it is shown to pass.

SCENES
  - 31 new lines — blocked; three files — blocked; a new file, a new public name, a new
    dependency — blocked; code deleted outside the functions being fixed — blocked; with the gate
    switched off, on a re-entered stop, with a simplifier's acceptance, with the card edited to
    say `bugfix` or 300 lines — still blocked; the text of the block is the approved one;
  - inside the limit — the turn ends, the debt line and the follow-up task are written;
  - the agent cannot declare the work urgent: no owner's words, or a task that does not say it;
  - three open debts — the fourth starts with a question for the owner;
  - `debt` refuses a card without its way back, and a card with no fix; `close` needs the full fix.
The command and the card are prose a model follows; what is free to check is their structure.

Run:   python3 tests/test_hotfix.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
HOTFIX = HOOKS / "hotfix.py"
BUDGET = HOOKS / "complexity_budget.py"
BLOCK_TEXT = "не термінове виправлення — або зменш, або `/bugfix`"
PASS = FAIL = 0


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = load("engine", ROOT / "engine.py")
board = load("board", ROOT / ".claude/unattended/board.py")


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def text(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(doc: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}.*?\n(.*?)(?=^## |\Z)", doc, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def flat(body: str) -> str:
    return " ".join(body.split())


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str) -> str:
    sh(root, "git", "add", "-A")
    done = sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    assert done.returncode == 0, done.stderr
    return sh(root, "git", "rev-parse", "HEAD").stdout.strip()


CALC = "RATE = 5\nLIMIT = 9\n\n\ndef add(a, b):\n    total = a - b\n    checked = total\n    return checked\n\n\ndef double(a):\n    return a * 2\n"
OTHER = "def one():\n    return 1\n"
TASK = "# 010 — Вхід падає\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Що зробити\n{body}\n\n## Готово, коли\n- працює\n\n## Питання до власника\n{questions}"
URGENT = "Це термінове виправлення: `/hotfix`. Вхід падає з помилкою 500."
TODAY = datetime.now(UTC).date()
roots: list[Path] = []


def fresh(gate: str = "off", task_body: str = URGENT, questions: str = "", ignore_state: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="hotfix-"))
    roots.append(root)
    for rel, body in (("app/calc.py", CALC), ("app/other.py", OTHER), ("app/third.py", OTHER.replace("one", "three")),
                      ("tests/test_calc.py", "assert True\n"), ("pyproject.toml", '[project]\nname = "demo"\nversion = "0"\ndependencies = []\n'),
                      (".claude/project.env", f'SOURCE_DIRS="app"\nCOMPLEXITY_GATE="{gate}"\n'), (".gitignore", ".claude/state/\n" if ignore_state else "*.pyc\n"),
                      ("tasks/doing/010-urgent.md", TASK.format(body=task_body, questions=questions)),
                      ("tasks/todo/.gitkeep", ""), ("tasks/blocked/.gitkeep", ""), ("tasks/done/004-old/task.md", "# 004\n")):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    sh(root, "git", "init", "-q", "-b", "main")
    commit(root, "base")
    return root


def run(root: Path, script: Path, *args: str, unattended: bool = False, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_UNATTENDED_SESSION"}
    env["CLAUDE_PROJECT_DIR"] = str(root)
    if unattended:
        env["CLAUDE_UNATTENDED_SESSION"] = "1"
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, check=False, env=env, input=stdin)


def out(r: subprocess.CompletedProcess[str]) -> str:
    return f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"


def start(root: Path, name: str = "login-500", *more: str, unattended: bool = False) -> subprocess.CompletedProcess[str]:
    return run(root, HOTFIX, "start", "--name", name, *(more or ("--task", "tasks/doing/010-urgent.md")), unattended=unattended)


def started(gate: str = "off", ignore_state: bool = True) -> tuple[Path, Path]:
    """A project with an urgent fix begun: the card exists, its way back is written."""
    root = fresh(gate, ignore_state=ignore_state)
    r = start(root)
    assert r.returncode == 0, out(r)
    card = next((root / ".engine/bugs").glob("*.md"))
    card.write_text(card.read_text(encoding="utf-8").replace("- Roll back: <", "- Roll back: `git revert HEAD` <")
                    .replace("- Symptom: <", "- Symptom: the login page answers 500 <"), encoding="utf-8")
    return root, card


def hook(root: Path, reentered: bool = False) -> tuple[str, str]:
    r = run(root, BUDGET, "hook", stdin=json.dumps({"hook_event_name": "Stop", "stop_hook_active": reentered}))
    if not r.stdout.strip():
        return ("allow" if r.returncode == 0 else f"exit {r.returncode}"), r.stderr
    payload = json.loads(r.stdout)
    return ("block", payload["reason"]) if payload.get("decision") == "block" else ("warn", str(payload))


def grow(root: Path, rel: str, lines: int, marker: str = "    return a * 2\n") -> None:
    """`lines` new lines inside an existing function: no new file, no new name."""
    path = root / rel
    body = path.read_text(encoding="utf-8")
    path.write_text(body.replace(marker, "".join(f"    _v{i} = {i}\n" for i in range(lines)) + marker, 1), encoding="utf-8")


def edit(root: Path, rel: str, old: str, new: str) -> None:
    path = root / rel
    body = path.read_text(encoding="utf-8")
    assert old in body, (rel, old)
    path.write_text(body.replace(old, new, 1), encoding="utf-8")


def debts(root: Path) -> list[str]:
    path = root / ".engine/debt.md"
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("- ")] if path.is_file() else []


def followups(root: Path) -> list[Path]:
    return sorted((root / "tasks/todo").glob("*-hotfix-followup-*.md"))


try:
    # --- the hard limit: every block before the pass ------------------------------------------------
    print("the hard limit blocks")
    root, card = started()
    grow(root, "app/calc.py", 31)
    decision, said = hook(root)
    check("31 new lines — the turn is blocked, though COMPLEXITY_GATE is off", decision == "block" and "max_added_lines: 31 used, 30 allowed" in said, said)
    check("…with the approved text, and without a call for the simplifier", BLOCK_TEXT in said and "simplifier.py request" not in said, said)
    decision, said = hook(root, reentered=True)
    check("…and blocked again on the stop that follows the block: the limit does not let go after one refusal", decision == "block", said)
    r = run(root, BUDGET, "check")
    check("`complexity_budget.py check` says the same and exits 1", r.returncode == 1 and "HOTFIX LIMIT EXCEEDED" in r.stdout and BLOCK_TEXT in r.stdout, out(r))
    r = run(root, HOTFIX, "debt", "--record", str(card.relative_to(root)))
    check("`hotfix.py debt` refuses: a fix over the limit leaves no debt, it is not an urgent fix",
          r.returncode == 1 and "REFUSED" in r.stdout and BLOCK_TEXT in r.stdout and not debts(root) and not followups(root), out(r))
    accepted = root / ".claude/state/simplifier" / f"accepted-{card.stem}.json"
    accepted.parent.mkdir(parents=True, exist_ok=True)
    base = sh(root, "git", "rev-parse", "HEAD").stdout.strip()
    accepted.write_text(json.dumps({"base_commit": base, "entries": [{"over": {"max_added_lines": 99}, "reason": "it was needed"}]}), encoding="utf-8")
    decision, said = hook(root)
    check("a simplifier's acceptance does not lift a hard limit", decision == "block" and "max_added_lines" in said, said)
    r = run(root, HOOKS / "simplifier.py", "accept", "--reason", "the fix needed every line", "--verdict", "verdict.json")
    check("…and `simplifier.py accept` refuses to record one for it", r.returncode == 1 and "hard" in r.stderr, out(r))
    card.write_text(card.read_text(encoding="utf-8").replace("max_added_lines: 30", "max_added_lines: 300"), encoding="utf-8")
    decision, said = hook(root)
    check("the card edited to allow 300 lines — 30 stays in force", decision == "block" and "30 allowed" in said, said)
    card.write_text(card.read_text(encoding="utf-8").replace("type: hotfix", "type: bugfix").replace("mode: hard\n", ""), encoding="utf-8")
    decision, said = hook(root)
    check("the card edited to say it is a bug fix with no hard mode — the limit it began with stays hard", decision == "block" and BLOCK_TEXT in said, said)

    root = fresh()
    head = sh(root, "git", "rev-parse", "HEAD").stdout.strip()
    (root / ".engine/bugs").mkdir(parents=True)
    (root / ".engine/bugs/001-by-hand.md").write_text(text(".claude/templates/hotfix-record.md").replace("<base_commit>", head)
                                                      .replace("max_added_lines: 30", "max_added_lines: 300"), encoding="utf-8")
    (root / ".engine/PROGRESS.md").write_text("## Hotfix 001-by-hand — IN PROGRESS\n- Record: `.engine/bugs/001-by-hand.md`\n", encoding="utf-8")
    grow(root, "app/calc.py", 31)
    decision, said = hook(root)
    check("a card written by hand that allows 300 lines from its first day — the ceiling is the script's, not the card's",
          decision == "block" and "max_added_lines: 31 used, 30 allowed" in said, said)

    root, card = started("warn")
    for rel, old in (("app/calc.py", "a * 2"), ("app/other.py", "return 1"), ("app/third.py", "return 1")):
        edit(root, rel, old, old.replace("2", "3").replace("1", "2"))
    decision, said = hook(root)
    check("three files, one line each — blocked (and in `warn` mode it is a block, not a warning)",
          decision == "block" and "max_changed_files: 3 used, 2 allowed" in said and BLOCK_TEXT in said, said)

    root, card = started()
    (root / "app/new.py").write_text("def _helper():\n    return 1\n", encoding="utf-8")
    decision, said = hook(root)
    check("a new file — blocked", decision == "block" and "max_new_files: 1 used, 0 allowed" in said, said)
    root, card = started()
    with open(root / "app/calc.py", "a", encoding="utf-8") as handle:
        handle.write("\n\ndef triple(a):\n    return a * 3\n")
    decision, said = hook(root)
    check("a new public name — blocked", decision == "block" and "max_new_public_symbols: 1 used, 0 allowed" in said, said)
    root, card = started()
    edit(root, "pyproject.toml", "dependencies = []", 'dependencies = ["requests"]')
    decision, said = hook(root)
    check("a new dependency — blocked", decision == "block" and "max_new_dependencies: 1 used, 0 allowed" in said, said)
    root, card = started()
    (root / "config.yaml").write_text("retries: 3\n", encoding="utf-8")
    decision, said = hook(root)
    check("a new file outside SOURCE_DIRS counts too: an urgent fix is measured whole", decision == "block" and "max_new_files" in said, said)

    print("no deletion outside the functions being fixed")
    root, card = started()
    edit(root, "app/calc.py", "a - b", "a + b")
    edit(root, "app/calc.py", "\n\ndef double(a):\n    return a * 2\n", "")
    decision, said = hook(root)
    check("another function deleted on the way — blocked, and it is named", decision == "block" and "deleted outside" in said and "double" in said, said)
    root, card = started()
    edit(root, "app/calc.py", "a - b", "a + b")
    edit(root, "app/calc.py", "LIMIT = 9\n", "")
    decision, said = hook(root)
    check("a module-level line deleted — blocked", decision == "block" and "deleted outside" in said and "app/calc.py:2" in said, said)
    root, card = started()
    edit(root, "app/calc.py", "a - b", "a + b")
    sh(root, "git", "rm", "-q", "app/third.py")
    decision, said = hook(root)
    check("a file deleted — blocked", decision == "block" and "deleted outside" in said and "app/third.py" in said, said)
    root, card = started()
    edit(root, "app/calc.py", "    total = a - b\n    checked = total\n    return checked\n", "    return a + b\n")
    edit(root, "app/calc.py", "RATE = 5", "RATE = 6")
    decision, said = hook(root)
    check("lines deleted inside the function being fixed, and a module-level line replaced — not a block", decision == "allow", said)

    # --- inside the limit ---------------------------------------------------------------------------
    print("inside the limit: the turn ends, the debt and the follow-up are written by the script")
    root, card = started(ignore_state=False)  # the hooks' own state files are not git-ignored here, and are not the fix
    r = run(root, HOTFIX, "debt", "--record", str(card.relative_to(root)))
    check("no fix at all — `debt` refuses: there is nothing to owe for", r.returncode == 1 and "REFUSED" in r.stdout and "no fix" in r.stdout and not debts(root), out(r))
    edit(root, "app/calc.py", "a - b", "a + b")
    grow(root, "app/calc.py", 14)
    grow(root, "app/other.py", 15, "    return 1\n")
    (root / "tests/test_calc.py").write_text("assert True\n" * 60, encoding="utf-8")
    decision, said = hook(root)
    check("30 new lines in two files (a test of any size beside them) — the turn ends", decision == "allow", said)
    decision, said = hook(root)
    check("…and again at the next stop: what the hook itself wrote under .claude/state/ is not counted as the fix", decision == "allow", said)
    r = run(root, BUDGET, "check")
    check("`check` reports the hotfix inside its limit", r.returncode == 0 and "within the limit" in r.stdout and "+30" in r.stdout, out(r))
    blank = card.read_text(encoding="utf-8")
    card.write_text(blank.replace("- Roll back: `git revert HEAD` <", "- Roll back: <"), encoding="utf-8")
    r = run(root, HOTFIX, "debt", "--record", str(card.relative_to(root)))
    check("the card does not say how to roll the fix back — `debt` refuses", r.returncode == 1 and "roll back" in r.stdout.lower() and not debts(root), out(r))
    card.write_text(blank, encoding="utf-8")
    fix = commit(root, "hotfix: login")
    r = run(root, HOTFIX, "debt", "--record", str(card.relative_to(root)))
    lines = debts(root)
    due = (TODAY + timedelta(days=7)).isoformat()
    check("`debt` writes one line into .engine/debt.md: what was put off, the commit, the date, the term of seven days",
          r.returncode == 0 and len(lines) == 1 and card.stem in lines[0] and "| open |" in lines[0] and f"recorded {TODAY.isoformat()}" in lines[0]
          and f"due {due}" in lines[0] and f"commit {fix[:7]}" in lines[0]
          and all(w in lines[0] for w in ("test before the code", "cause", "same places")), out(r) + str(lines))
    made = followups(root)
    check("…and the follow-up task in tasks/todo/: the next free number, the name of the card", len(made) == 1
          and made[0].name == f"011-hotfix-followup-{card.stem}.md" and made[0].name in lines[0], made)
    follow = made[0].read_text(encoding="utf-8") if made else ""
    parsed = board.parse(follow)
    check("the follow-up is an ordinary board task: a full /bugfix of the same place, the card, the commit, the term, how to close the debt",
          "/bugfix" in follow and f".engine/bugs/{card.stem}.md" in follow and fix[:7] in follow and due in follow and "hotfix.py close" in follow
          and not parsed.attended and not parsed.depends and "## Готово, коли" in follow, follow)
    (root / "tasks/doing/010-urgent.md").rename(root / "tasks/done/010-urgent.md")
    r2 = run(root, ROOT / ".claude/unattended/board.py", "--root", str(root), "next")
    check("…which the board offers like any other", made and made[0].name in r2.stdout, out(r2))
    noted = card.read_text(encoding="utf-8")
    check("the card carries the debt: its status, the line and the follow-up", re.search(r"^status: fixed, debt open", noted, re.MULTILINE) is not None
          and lines[0] in noted and made[0].name in noted, noted[-600:])
    r = run(root, HOTFIX, "debt", "--record", str(card.relative_to(root)))
    check("a second `debt` for the same card adds nothing", r.returncode == 0 and "ALREADY" in r.stdout and len(debts(root)) == 1 and len(followups(root)) == 1, out(r))
    r = run(root, HOTFIX, "list")
    check("`list` shows the open debt and its term", r.returncode == 0 and card.stem in r.stdout and due in r.stdout and "open: 1" in r.stdout, out(r))

    print("closing a debt")
    record = root / ".engine/bugs/002-login-500-full.md"
    record.write_text("# Bug 002\n\ntype: bugfix\nstatus: reproduced\n", encoding="utf-8")
    r = run(root, HOTFIX, "close", "--record", str(card.relative_to(root)), "--bugfix", str(record.relative_to(root)))
    check("`close` refuses while the full fix is not finished", r.returncode == 1 and "REFUSED" in r.stdout and "| open |" in debts(root)[0], out(r))
    kept = card.read_text(encoding="utf-8")
    card.write_text(re.sub(r"(?m)^status:.*$", "status: fixed", kept.replace("type: hotfix", "type: bugfix")), encoding="utf-8")
    r = run(root, HOTFIX, "close", "--record", str(card.relative_to(root)), "--bugfix", str(card.relative_to(root)))
    check("…and the urgent card cannot close its own debt, even edited to look like a full fix", r.returncode == 1 and "REFUSED" in r.stdout
          and "| open |" in debts(root)[0], out(r))
    card.write_text(kept, encoding="utf-8")
    record.write_text("# Bug 002\n\ntype: bugfix\nstatus: fixed\n", encoding="utf-8")
    r = run(root, HOTFIX, "close", "--record", str(card.relative_to(root)), "--bugfix", str(record.relative_to(root)))
    check("with a bug record of type bugfix and status fixed — closed, with the date and the record",
          r.returncode == 0 and f"| closed {TODAY.isoformat()} by .engine/bugs/{record.name} |" in debts(root)[0], out(r) + str(debts(root)))

    # --- who declares --------------------------------------------------------------------------------
    print("only the owner declares")
    root = fresh(task_body="Вхід падає з помилкою 500. Виправити.")
    r = start(root)
    check("a task that does not call the work urgent — refused: the agent does not name it urgent itself",
          r.returncode == 2 and "REFUSED" in r.stdout and not list((root / ".engine").glob("bugs/*")), out(r))
    r = run(root, HOTFIX, "start", "--name", "login-500")
    check("neither a task nor the owner's words — refused", r.returncode == 2 and not (root / ".engine/bugs").exists(), out(r))
    r = start(root, "login-500", "--declared", "it is urgent, fix it now", unattended=True)
    check("unattended, the owner's words \"from the session\" are refused: nobody is in the session", r.returncode == 2 and "unattended" in r.stdout, out(r))
    r = start(root, "login-500", "--declared", "it is urgent, fix it now")
    made = sorted((root / ".engine/bugs").glob("*.md"))
    body = made[0].read_text(encoding="utf-8") if made else ""
    check("attended, the owner's words are recorded in the card as they are", r.returncode == 0 and len(made) == 1
          and made[0].name == "001-login-500.md" and "it is urgent, fix it now" in body, out(r))
    head = sh(root, "git", "rev-parse", "HEAD").stdout.strip()
    check("the card: type hotfix, hard mode, the base commit, the limits of the approved design",
          re.search(r"^type: hotfix$", body, re.MULTILINE) is not None and f"base_commit: {head}" in body and "mode: hard" in body
          and all(f"{k}: {v}" in body for k, v in (("max_new_files", 0), ("max_changed_files", 2), ("max_added_lines", 30),
                                                    ("max_new_public_symbols", 0), ("max_new_dependencies", 0))), body)
    progress = (root / ".engine/PROGRESS.md").read_text(encoding="utf-8")
    check("…and .engine/PROGRESS.md marks it IN PROGRESS, so the limit is measured from the first change",
          "IN PROGRESS" in progress and ".engine/bugs/001-login-500.md" in progress, progress)
    r = start(root, "Login 500!", "--declared", "it is urgent, fix it now")
    check("a name that is not kebab-case is refused", r.returncode == 2 and len(list((root / ".engine/bugs").glob("*.md"))) == 1, out(r))

    # --- three open debts ------------------------------------------------------------------------------
    print("three open debts: the fourth starts with a question")

    def line(name: str, status: str = "open", due: str = "2999-01-01") -> str:
        return (f"- {name} | {status} | recorded 2026-01-01 | due {due} | commit abc1234 | deferred: the test before the code; "
                f"the record of the cause; the search for the same places | follow-up: tasks/todo/020-hotfix-followup-{name}.md\n")

    root = fresh()
    (root / ".engine").mkdir()
    (root / ".engine/debt.md").write_text("# Debts\n\n" + line("001-a") + line("002-b") + line("003-c", "closed 2026-01-05 by .engine/bugs/009-x.md"), encoding="utf-8")
    r = start(root)
    check("two open debts and a closed one — the urgent fix starts", r.returncode == 0 and (root / ".engine/bugs/001-login-500.md").is_file(), out(r))
    root = fresh()
    (root / ".engine").mkdir()
    (root / ".engine/debt.md").write_text("# Debts\n\n" + line("001-a") + line("002-b") + line("003-c"), encoding="utf-8")
    r = start(root)
    check("three open debts — no card: exit 3 and the question for the owner, with the three debts by name",
          r.returncode == 3 and "QUESTION FOR THE OWNER" in r.stdout and all(n in r.stdout for n in ("001-a", "002-b", "003-c"))
          and "Відповідь:" in r.stdout and not (root / ".engine/bugs").exists(), out(r))
    r = start(root, "login-500", "--task", "tasks/doing/010-urgent.md", "--owner-answer", "так, виправляй")
    check("an answer the task does not carry is refused: the answer is the owner's line, not the agent's", r.returncode == 2
          and "REFUSED" in r.stdout and not (root / ".engine/bugs").exists(), out(r))
    task = root / "tasks/doing/010-urgent.md"
    task.write_text(task.read_text(encoding="utf-8") + "1. Три борги відкрито. Починати четверте?\n   Відповідь: так, виправляй\n", encoding="utf-8")
    r = start(root, "login-500", "--task", "tasks/doing/010-urgent.md", "--owner-answer", "так, виправляй")
    made = sorted((root / ".engine/bugs").glob("*.md"))
    check("with the owner's answer in the task — it starts, and the card records the answer and the three debts",
          r.returncode == 0 and len(made) == 1 and "так, виправляй" in made[0].read_text(encoding="utf-8")
          and "3" in section(made[0].read_text(encoding="utf-8"), "1."), out(r))
finally:
    for path in roots:
        shutil.rmtree(path, ignore_errors=True)


# --- the command ----------------------------------------------------------------------------------------
print("the command")
command = text(".claude/commands/hotfix.md")
whole = flat(command)
check("the command exists, with a description", command.startswith("---\ndescription:"), command[:80])
heads = re.findall(r"^## (.+)$", command, re.MULTILINE)
check("its steps, in the approved order: who declares, roll back first, the card, the symptom, the fix inside the hard limit, the way back, "
      "the gate and the overseer, the debt", [h.split(".")[0] for h in heads if h[0].isdigit()] == ["1", "2", "3", "4", "5", "6", "7"]
      and heads[0].startswith("Only the owner") and "Roll back first" in heads[1], heads)
declares = flat(section(command, "Only the owner"))
check("only the owner declares it — a line in the task or words in the session; the agent never", "never" in declares and "task" in declares and "session" in declares, declares[:300])
first = flat(section(command, "1."))
check("the first step: is a revert simpler; `git revert` is prepared, not run", "git revert" in first and "prepare" in first and "not run" in first, first[:300])
check("three open debts start with a question for the owner", "three open debts" in whole and "exit 3" in whole and "tasks/blocked/" in whole)
limit = flat(section(command, "4."))
check("the hard limit: 30 lines, two files, no new file, dependency or public name, no deletion outside the functions being fixed",
      all(w in limit for w in ("30", "two files", "new file", "dependenc", "public name", "outside the functions")), limit[:500])
check("over the limit is a block, not a call for the simplifier, with the approved text", BLOCK_TEXT in command and "simplifier is not" in limit, limit[:500])
keeps = flat(section(command, "6."))
check("the gate, the bypass guard and the overseer stay, without exceptions", all(w in keeps for w in ("no worse", "bypass", "overseer", "no exception")), keeps[:400])
check("what is deferred is the test before the code, the cause and the search for the same places — and a script writes the debt",
      all(w in whole for w in ("test before the code", "cause", "same places", "hotfix.py debt", ".engine/debt.md", "seven days")))
never = flat(section(command, "What /hotfix never does"))
check("it does not deploy, does not push, does not touch migrations or the settings of the checks",
      all(w in never for w in ("deploy", "push", "migration", ".claude/project.env")), never[:400])
check("the command names only scripts and files that exist", all((ROOT / rel).is_file() for rel in
      (".claude/hooks/hotfix.py", ".claude/hooks/complexity_budget.py", ".claude/templates/hotfix-record.md", ".claude/commands/bugfix.md")))

print("the card, the ownership, the documents")
template = text(".claude/templates/hotfix-record.md")
check("the card says how to roll back exactly this fix", "- Roll back:" in section(template, "4."), section(template, "4.")[:200])
ownership = engine.parse_ownership(text(".claude/ownership.txt"))
check("the command, the script and the card template ship with the engine; the debt file is the project's",
      all(engine.owner_of(ownership, rel) == "engine" for rel in (".claude/commands/hotfix.md", ".claude/hooks/hotfix.py", ".claude/templates/hotfix-record.md"))
      and engine.owner_of(ownership, ".engine/debt.md") == "project")
overseer = flat(text(".claude/agents/overseer.md"))
check("the overseer: an urgent fix is audited too, and a deferred test is a debt only when the debt line exists",
      "type: hotfix" in overseer and ".engine/debt.md" in overseer, "")
check("hooks.md has the script's row", "| `hotfix.py` |" in text(".claude/references/hooks.md"))
check("the budget reference describes the hard mode", "mode: hard" in text(".claude/references/complexity-budget.md"))
check("the limits say what the hard limit and the debt do not give", "## The urgent fix (board 075)" in text("docs/engine-limits.md"))
check("the engine's AGENTS.md names the command", "`/hotfix`" in text("AGENTS.md"))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
