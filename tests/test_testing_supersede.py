#!/usr/bin/env python3
"""A new sealed contract supersedes sealed tests of another slice, parked or not (board 304).

The scene of thinkhow 202: the owner took a button away; three sealed tests of an older slice
demanded it; that slice had used both its rounds of dispute and was parked, so the conflict went
to the owner. Shown here, each rule refusing first:
  * `--tester supersede` is refused without `--by`, with the slice itself as `--by`, with an
    unsealed new contract, for a slice with no sealed tests;
  * the tester's `superseded` without a line of the new contract word for word is refused;
  * a parked old slice: the tester of the new contract rules on its tests with a counter of its
    own, rewrites them, they are sealed anew (a removed file leaves the seal), the slice is
    unparked and its open item `testing-parked-<slug>` moves to done/ — no question to the owner;
  * the old slice's own counter stays: a third objection of its own parks it again, as before;
  * two rounds of the new contract, the third parks the NEW slice;
  * an answered open item is the owner's: `close-item` leaves it alone.

Run:   python3 tests/test_testing_supersede.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPT = HOOKS / "testing.py"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import testing
from hook_env import hook_env

PASS = FAIL = 0
OLD = """# Slice web — planning artifact

## Seam (contract)
- Signature: `page() -> str` in `src/web.py`
- Returns: the page, with a button «Завершити сесію»

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- none

## Exit criterion
The tests pass.
"""
NEW = """# Slice no-end — planning artifact

## Seam (contract)
- Signature: `page() -> str` in `src/web.py`
- Changes: the page has no button «Завершити сесію» any more

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- none

## Exit criterion
The tests pass.
"""
NEW_LINE = "- Changes: the page has no button «Завершити сесію» any more"
OLD_TESTS = ("import unittest\nfrom src.web import page\n\n\nclass T(unittest.TestCase):\n"
             "    def test_button(self):\n        self.assertIn('Завершити сесію', page())\n")
NEW_TESTS = ("import unittest\nfrom src.web import page\n\n\nclass T(unittest.TestCase):\n"
             "    def test_button(self):\n        self.assertNotIn('Завершити сесію', page())\n")


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:900]}")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args], capture_output=True, text=True, check=True)


def write(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")


def cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=hook_env(repo), capture_output=True, text=True, check=False)


def board(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(repo / ".claude/unattended/board.py"), *args], cwd=repo, env=hook_env(repo),
                          capture_output=True, text=True, check=False)


def answer(repo: Path, obj: object) -> subprocess.CompletedProcess[str]:
    path = repo / "answer.txt"
    path.write_text("```json\n" + json.dumps(obj, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return cli(repo, "record", "--answer", str(path))


def new_repo(seal_new: bool = True) -> Path:
    """A project with a board, the slice `web` parked after its own two rounds, and the new contract `no-end`."""
    repo = Path(tempfile.mkdtemp(prefix="supersede-"))
    for part in ("hooks", "unattended"):
        shutil.copytree(ROOT / ".claude" / part, repo / ".claude" / part, ignore=shutil.ignore_patterns("__pycache__"))
    for column in ("todo", "doing", "blocked", "done", "proposed"):
        (repo / "tasks" / column).mkdir(parents=True)
    write(repo, "src/__init__.py", "")
    write(repo, "src/web.py", "def page() -> str:\n    return '<button>Завершити сесію</button>'\n")
    write(repo, "tests/__init__.py", "")
    write(repo, ".claude/project.env", 'CODE_EXTENSIONS="py"\nMUTATION_CMD=""\n')
    write(repo, ".gitignore", ".claude/state/\n__pycache__/\n")
    write(repo, ".engine/slices/web.md", OLD)
    write(repo, ".engine/slices/no-end.md", NEW)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    for slug in ("web", "no-end") if seal_new else ("web",):
        subprocess.run([sys.executable, str(HOOKS / "contract_fingerprint.py"), "seal", f".engine/slices/{slug}.md"], env=hook_env(repo),
                       capture_output=True, text=True, check=True)
    write(repo, "tests/test_web.py", OLD_TESTS)
    write(repo, "tests/test_web_extra.py", OLD_TESTS.replace("test_button", "test_button_twice"))
    testing.seal_files(repo, "web", ["tests/test_web.py", "tests/test_web_extra.py"], {})
    for n in (1, 2):
        testing.append_row(repo, {"type": "round", "slice": "web", "round": n, "items": [{"test": f"other_{n}", "verdict": "test_right"}]}, "t", [])
    package = repo / "objection.md"
    package.write_text("tests.test_web.T.test_button: the owner took the button away\n", encoding="utf-8")
    cli(repo, "request", "web", "--tester", "objection", "--package", str(package))
    return repo


def items(*pairs: tuple[str, str, str]) -> list[dict[str, Any]]:
    return [{"test": t, "verdict": v, "reason": "the new contract", **({"contract_line": line} if line else {})} for t, v, line in pairs]


print("the scene of thinkhow 202 — a parked slice, its tests changed by a new contract")
r = new_repo()
item = r / "tasks/blocked" / next((p.name for p in (r / "tasks/blocked").iterdir()), "none")
check("before: two rounds of its own, the third objection parked `web` and asked the owner",
      testing.is_parked(r, "web") and item.is_file() and "Відкритий пункт: testing-parked-web" in item.read_text(encoding="utf-8"), list((r / "tasks/blocked").iterdir()))
package = r / "supersede.md"
package.write_text(f"tests.test_web.T.test_button and tests.test_web_extra.T.test_button_twice demand the button; {NEW_LINE}\n", encoding="utf-8")

out = cli(r, "request", "web", "--tester", "supersede", "--package", str(package))
check("negative — without `--by` the request is refused (exit 2)", out.returncode == 2 and "--by" in out.stderr, out.stderr)
out = cli(r, "request", "web", "--tester", "supersede", "--by", "web", "--package", str(package))
check("negative — a slice does not supersede its own tests: that is an objection", out.returncode == 1 and "objection" in out.stderr, out.stderr)
check("negative — a slice with no sealed tests: nothing to supersede",
      cli(r, "request", "no-end", "--tester", "supersede", "--by", "web", "--package", str(package)).returncode == 1)
unsealed = new_repo(seal_new=False)
out = cli(unsealed, "request", "web", "--tester", "supersede", "--by", "no-end", "--package", str(package))
check("negative — an unsealed new contract changes nothing sealed", out.returncode == 1 and "not sealed" in out.stderr, out.stderr)

out = cli(r, "request", "web", "--tester", "supersede", "--by", "no-end", "--package", str(package))
request = testing.read_json(r / ".claude/state/testing/requests" / out.stdout.strip().split()[-1] / "request.json")
check("the parked slice is not refused: the tester of the new contract is asked, round 1 of its own counter",
      out.returncode == 0 and out.stdout.startswith("TESTING_REQUEST") and request["round"] == 1 and request["by"] == "no-end"
      and request["parked"] and request["new_contract"] == ".engine/slices/no-end.md", out.stdout + out.stderr)
write(r, "tests/test_web.py", NEW_TESTS)
(r / "tests/test_web_extra.py").unlink()
both = items(("tests.test_web.T.test_button", "superseded", NEW_LINE), ("tests.test_web_extra.T.test_button_twice", "superseded", ""))
refused = testing.record_objection(r, request, {"mode": "supersede", "slice": "web", "by": "other", "items": both})
check("negative — an answer for another new contract is refused", len(refused) == 1 and "`by` must repeat the request" in refused[0], refused)
out = answer(r, {"mode": "supersede", "slice": "web", "by": "no-end", "items": both})
check("negative — `superseded` without a line of the new contract word for word is refused",
      out.returncode == 1 and "contract_line" in out.stderr and "test_button_twice" in out.stderr, out.stderr)
out = answer(r, {"mode": "supersede", "slice": "web", "by": "no-end",
                 "items": items(("tests.test_web.T.test_button", "superseded", NEW_LINE), ("tests.test_web_extra.T.test_button_twice", "superseded", NEW_LINE))})
ledger = (r / ".engine/testing/ledger.md").read_text(encoding="utf-8")
check("the tester's ruling is recorded: round 1 of the new contract, both tests superseded", out.returncode == 0
      and "the new contract no-end over its tests, round 1 of 2" in ledger and ledger.count("SUPERSEDED by the new contract") == 2, out.stderr + ledger)
check("the rewritten test is sealed anew and the removed file leaves the seal", cli(r, "check", "web").returncode == 0
      and sorted(testing.read_json(r / ".claude/state/testing/seals/web.json")["files"]) == ["tests/test_web.py"], cli(r, "check", "web").stderr)
done = r / "tasks/done" / item.stem
check("the slice is unparked and its open item is in done/ with the reason — the owner was not asked",
      not testing.is_parked(r, "web") and not item.exists() and (done / "task.md").is_file()
      and "slice contract no-end" in (done / "report.md").read_text(encoding="utf-8") and "UNPARKED" in ledger
      and not list((r / "tasks/blocked").iterdir()), list((r / "tasks/done").iterdir()))
check("its own counter stays at two, and the new contract's round tells nothing of its code (O4)",
      len(testing.rounds_of(r, "web")) == 2 and len(testing.rounds_of(r, "web", "no-end")) == 1
      and testing.history(r, "web")["dispute_outcomes"] == ["test_right", "test_right"], testing.history(r, "web"))
check("`status` shows the slice no longer parked", "PARKED" not in cli(r, "status", "web").stdout, cli(r, "status", "web").stdout)

print("the third round in the same slice, with no new contract, parks it as before")
out = cli(r, "request", "web", "--tester", "objection", "--package", str(r / "objection.md"))
check("an objection of its own after the unpark: the third round parks `web` again (exit 3)",
      out.returncode == 3 and "PARKED" in out.stderr and testing.is_parked(r, "web"), out.stderr)

print("the new contract's own counter: two rounds, the third parks the new slice")
r = new_repo()
for n in (1, 2):
    cli(r, "request", "web", "--tester", "supersede", "--by", "no-end", "--package", str(package))
    out = answer(r, {"mode": "supersede", "slice": "web", "by": "no-end",
                     "items": items(("tests.test_web.T.test_button", "contract_ambiguous", ""))})
    check(f"round {n}: «the new contract is ambiguous» is recorded and unparks nothing", out.returncode == 0 and testing.is_parked(r, "web"), out.stderr)
out = cli(r, "request", "web", "--tester", "supersede", "--by", "no-end", "--package", str(package))
check("the third round of the new contract is not held: the NEW slice is parked with both rounds (exit 3)",
      out.returncode == 3 and testing.is_parked(r, "no-end") and len(testing.rounds_of(r, "web")) == 2
      and (testing.last(r, "no-end", "parked") or {}).get("rounds", [""])[0].startswith("round 1: tests.test_web.T.test_button"), out.stderr)
check("…and a parked new slice asks its tester nothing more",
      cli(r, "request", "web", "--tester", "supersede", "--by", "no-end", "--package", str(package)).returncode == 3)

print("`close-item` — an answered item is the owner's")
r = new_repo()
item = next((r / "tasks/blocked").iterdir())
item.write_text(item.read_text(encoding="utf-8").replace("Відповідь:", "Відповідь: тест правий"), encoding="utf-8")
out = board(r, "close-item", "--key", "testing-parked-web", "--why", "x")
check("negative — the owner answered: nothing is closed (exit 1), the item stays in blocked/", out.returncode == 1 and item.is_file(), out.stdout + out.stderr)
item.write_text(item.read_text(encoding="utf-8").replace("Відповідь: тест правий", "Відповідь:"), encoding="utf-8")
out = board(r, "close-item", "--key", "testing-parked-web", "--why", "новий контракт")
check("unanswered: done/NNN-name/ with task.md and report.md", out.returncode == 0 and (r / "tasks/done" / item.stem / "report.md").is_file(), out.stdout + out.stderr)
check("a key nobody carries: exit 1", board(r, "close-item", "--key", "nothing", "--why", "x").returncode == 1)

tester_text = (ROOT / ".claude/agents/slice-tester.md").read_text(encoding="utf-8")
check("the tester's definition has the mode `supersede` with its answer", "## Mode `supersede`" in tester_text and '"by": "<the new slice>"' in tester_text)
builder_text = (ROOT / ".claude/skills/slice-builder/SKILL.md").read_text(encoding="utf-8")
check("the builder is told the way", "--tester supersede --by" in builder_text)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
