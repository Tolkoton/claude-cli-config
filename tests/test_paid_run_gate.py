#!/usr/bin/env python3
"""A paid audit starts only when the owner said so (package board, item 4).

evals/run_audit_scenarios.py refuses, before anything else and before any session, unless
  - the one task in tasks/doing/ says «Аудит потрібен: так» or «Платні прогони: так» (board 053:
    the owner's leave for any paid run, no dollar number), or
  - the owner runs it by hand with --owner-approved — in their own terminal: inside a Claude
    Code session (CLAUDECODE set) the flag is refused, like gate.py --close-escalation.

No session is started here. A case that must get PAST the gate asks for a scenario that does
not exist, so the runner stops at its next check ("no scenario id contains"); a `claude` shim
that records every call shows that nothing ran in either direction.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals" / "run_audit_scenarios.py"
PASS = FAIL = 0
REFUSAL = "refusing to start paid sessions"
PAST_THE_GATE = "no scenario id contains"


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


work = Path(tempfile.mkdtemp(prefix="paid-gate-"))
shim = work / "claude"
shim.write_text(f"#!/usr/bin/env bash\necho called >> {work}/calls\necho '1.0.0 (shim)'\n")
shim.chmod(0o755)


def board(*doing: tuple[str, str]) -> Path:
    tasks = Path(tempfile.mkdtemp(prefix="paid-gate-board-", dir=work)) / "tasks"
    for column in ("todo", "doing", "blocked", "done"):
        (tasks / column).mkdir(parents=True)
    for name, audit in doing:
        # a name that says «owner» is the task of the owner's session (board 049)
        attended = "Потрібна присутність власника: так\n" if "owner" in name else ""
        (tasks / "doing" / name).write_text(f"# x\n\nЗалежить від: —\n{attended}Аудит потрібен: {audit}\n\n## Що зробити\n", encoding="utf-8")
    return tasks


def run(*args: str, in_session: bool = False, unattended: bool = False) -> subprocess.CompletedProcess[str]:
    # The suite itself may run inside an unattended session; a case says which kind it means.
    env = {k: v for k, v in hook_env(work).items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    if in_session:
        env["CLAUDECODE"] = "1"
    if unattended:
        env["CLAUDE_UNATTENDED_SESSION"] = "1"
    return subprocess.run([sys.executable, str(RUNNER), "--claude", str(shim), "--only", "no-such-scenario-zz", *args],
                          capture_output=True, text=True, env=env, check=False)


def refused(r: subprocess.CompletedProcess[str]) -> bool:
    return r.returncode == 2 and REFUSAL in r.stderr and PAST_THE_GATE not in r.stderr


def passed(r: subprocess.CompletedProcess[str]) -> bool:
    return REFUSAL not in r.stderr and PAST_THE_GATE in r.stderr


print("the task on the board decides")
r = run("--tasks-dir", str(board()))
check("no task in doing/: refused", refused(r), r.stderr)
check("the refusal names both ways through", "Аудит потрібен: так" in r.stderr and "--owner-approved" in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "ні"))))
check("the task says «ні»: refused, and the task is named", refused(r) and "001-a.md" in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "так"))))
check("the task says «так»: the runner goes on", passed(r), r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "так"))), in_session=True)
check("…inside a Claude Code session too: that is how a board task runs its audit", passed(r), r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "так"), ("002-b.md", "так"))))
check("two tasks in doing/: refused", refused(r), r.stderr)
paid = board(("001-a.md", "ні\nПлатні прогони: так"))
check("board 053 — «Аудит потрібен: ні» with «Платні прогони: так»: the runner goes on", passed(run("--tasks-dir", str(paid))))
paid = board(("001-a.md", "ні\nПлатні прогони: два повні audit-и — скільки потрібно"))
check("negative — a wording without «так» (the owner's answer on board 053: only «так» is leave): refused", refused(run("--tasks-dir", str(paid))))
r = run("--tasks-dir", str(board(("001-a.md", "ні\nПлатні прогони: ні"))))
check("negative — «Платні прогони: ні»: refused, and both lines are named", refused(r) and "«Платні прогони: так»" in r.stderr and "Аудит потрібен: так" in r.stderr, r.stderr)
for taken_back in ("так, але не для audit-у", "так, крім audit-у", "так, лише прогони simplifier-а", "до 5 доларів", "заборонено, навіть до 5 доларів", "не треба"):
    r = run("--tasks-dir", str(board(("001-a.md", f"ні\nПлатні прогони: {taken_back}"))))
    check(f"negative — «Платні прогони: {taken_back}»: the audit is refused", refused(r), r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "ні\n\n## Що зробити\n- …\n\n## Питання до власника\nПлатні прогони: так"))))
check("negative — «Платні прогони: так» below the header (under «Питання до власника»): the audit is refused", refused(r), r.stderr)
print("a sum in the task's line is the audit's ceiling too (the overseer's third BLOCK)")
CEILING = "cost ceiling $"
capped = str(board(("001-a.md", "ні\nПлатні прогони: так, до 5 доларів")))
r = run("--tasks-dir", capped)
check("«Платні прогони: так, до 5 доларів»: the runner goes on with a ceiling of 5 dollars", passed(r) and f"{CEILING}5.00" in r.stderr, r.stderr)
r = run("--tasks-dir", capped, "--max-cost", "3")
check("…a smaller --max-cost stands, and nothing is said about the task's sum", passed(r) and CEILING not in r.stderr, r.stderr)
r = run("--tasks-dir", capped, "--max-cost", "50")
check("…a larger --max-cost does not lift the owner's sum", passed(r) and f"{CEILING}5.00" in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "так\nПлатні прогони: так, не більше 12,5 $"))))
check("«Аудит потрібен: так» with a sum in the other line: the sum binds the audit", passed(r) and f"{CEILING}12.50" in r.stderr, r.stderr)
UNREAD = "is neither the owner's leave nor a plain «ні»"
for line in ("до 5 доларів", "до $5", "$5", "USD 5", "до 5 dollars", "до .5 долара", "так, до 5 доларів на audit", "п'ять доларів", "скільки потрібно"):
    r = run("--tasks-dir", str(board(("001-a.md", f"так\nПлатні прогони: {line}"))))
    check(f"negative — «Аудит потрібен: так» beside «Платні прогони: {line}» (the overseer's fourth and fifth BLOCKs): the audit stops, it does not go on uncapped",
          refused(r) and UNREAD in r.stderr and "«так, до N доларів»" in r.stderr and CEILING not in r.stderr, r.stderr)
    r = run("--tasks-dir", str(board(("001-a.md", f"ні\nПлатні прогони: {line}"))), "--owner-approved")
    check(f"negative — …and --owner-approved in the owner's terminal beside «{line}»: stops too", refused(r) and UNREAD in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "так\nПлатні прогони: ні"))))
check("«Аудит потрібен: так» beside «Платні прогони: ні» (no number): the audit goes on, no ceiling", passed(r) and CEILING not in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "ні\nПлатні прогони: ні"))), "--owner-approved")
check("--owner-approved beside a plain «ні»: the owner's flag stands", passed(r), r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "ні\nПлатні прогони: так"))))
check("negative — «Платні прогони: так» without a sum: no ceiling is invented", passed(r) and CEILING not in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "так"))))
check("negative — «Аудит потрібен: так» alone: no ceiling", passed(r) and CEILING not in r.stderr, r.stderr)
yes_in_todo = board()
(yes_in_todo / "todo" / "001-a.md").write_text("# x\n\nАудит потрібен: так\n", encoding="utf-8")
check("«так» in todo/ allows nothing", refused(run("--tasks-dir", str(yes_in_todo))))

print("two sides in doing/ (board 712): each session is judged by its own task")
both = (("001-owner.md", "ні"), ("002-runner.md", "так"))
r = run("--tasks-dir", str(board(*both)), in_session=True, unattended=True)
check("the agent alone, its task says «так», the owner's session's task lies beside it: the runner goes on", passed(r), r.stderr)
r = run("--tasks-dir", str(board(*both)), in_session=True)
check("…the same board in the owner's session: its task says «ні», refused, and that task is named", refused(r) and "001-owner.md" in r.stderr, r.stderr)
other = (("001-owner.md", "так"), ("002-runner.md", "ні"))
r = run("--tasks-dir", str(board(*other)), in_session=True, unattended=True)
check("negative — the agent alone, «так» only in the owner's session's task: refused, its own task is named",
      refused(r) and "002-runner.md" in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(*other)), in_session=True)
check("…the same board in the owner's session: the runner goes on", passed(r), r.stderr)
r = run("--tasks-dir", str(board(("001-owner.md", "так"))), in_session=True, unattended=True)
check("negative — the agent alone and only the owner's session's task in doing/: refused, it is nobody's word for the agent", refused(r), r.stderr)
r = run("--tasks-dir", str(board(("001-owner.md", "ні"), ("002-runner.md", "так"), ("003-runner.md", "так"))), in_session=True, unattended=True)
check("negative — two tasks of the agent's own side: refused as before", refused(r), r.stderr)
mode_board = board(*both)
(mode_board.parent / ".claude/state/overseer").mkdir(parents=True)
(mode_board.parent / ".claude/state/overseer/mode").write_text("unattended\n", encoding="utf-8")
r = run("--tasks-dir", str(mode_board), in_session=True)
check("the mode file says unattended as well as the runner's variable does", passed(r), r.stderr)

print("the owner's flag")
empty = str(board())
r = run("--tasks-dir", empty, "--owner-approved")
check("--owner-approved in the owner's own terminal: the runner goes on", passed(r), r.stderr)
r = run("--tasks-dir", empty, "--owner-approved", in_session=True)
check("--owner-approved inside a Claude Code session: refused", refused(r), r.stderr)
check("…and the refusal says why the flag did not count", "CLAUDECODE" in r.stderr, r.stderr)
r = run("--tasks-dir", str(board(("001-a.md", "ні"))), "--owner-approved")
check("the flag outranks a task that says «ні» (a manual run outside the board)", passed(r), r.stderr)

print("the gate comes first and nothing runs")
r = run("--tasks-dir", empty, "--engine-ref", "no-such-ref-zz")
check("refused before the engine ref is even resolved", refused(r) and "no-such-ref-zz" not in r.stderr, r.stderr)
check("the claude executable was never called, in any case above", not (work / "calls").exists())
r = run()
real_tasks = ROOT / "tasks"
real_doing = sorted(p.name for p in (real_tasks / "doing").glob("[0-9]*.md"))
sys.path.insert(0, str(ROOT / ".claude/unattended"))
import board as engine_board  # noqa: E402

in_hand = engine_board.parse((real_tasks / "doing" / real_doing[0]).read_text(encoding="utf-8")) if len(real_doing) == 1 else None
wants = in_hand is not None and (in_hand.audit or in_hand.paid)
check("without --tasks-dir the board is this repository's tasks/", passed(r) if wants else refused(r), (real_doing, r.stderr))
fixture = ROOT / "tests/fixtures/board-audit-yes"
check("the fixture board the other audit suites use says «так»", passed(run("--tasks-dir", str(fixture))))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
