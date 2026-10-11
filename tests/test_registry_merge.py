#!/usr/bin/env python3
"""A registry file merges without a conflict, and its reader survives what the merge leaves (board 104).

A registry is a file different tasks append independent lines to, where the order of the lines
means nothing. Half of all merge conflicts in the board's history were one such file,
tests/fast-suites.txt (board 083), so .gitattributes gives it `merge=union`: both sides of a
conflict are kept. What union can leave behind — the same line twice, another order, an empty
line, a line the other branch deleted — is the reader's to survive. This suite takes the REAL
.gitattributes and the REAL tests/run_all.sh into synthetic repositories:

  - two branches add different suites: the merge and the rebase are clean, both lines are there,
    `run_all.sh --fast` runs each suite once;
  - two branches add the same suite: it runs once, also when union leaves its line twice;
  - a list with a duplicate, an empty line and a comment between: every suite once, in the order
    of its first line;
  - the negative cases: a file outside the list conflicts as before, and so does the registry
    itself without the attribute; a line that union brought back for a deleted suite is refused
    by name (exit 2), never run and never skipped in silence;
  - in this repository the attribute is on the registry and on nothing else that was weighed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = "tests/fast-suites.txt"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("ENGINE_HEALTH_DIR", "ENGINE_TEST_JOBS") and not k.startswith("GIT_")}
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, env=env, check=False)


def suite(repo: Path, name: str) -> None:
    """A suite that leaves one line in runs.log every time it runs."""
    (repo / "tests" / f"test_{name}.py").write_text(
        f"from pathlib import Path\nwith (Path(__file__).parent / 'runs.log').open('a') as log:\n    log.write('{name}\\n')\nprint('PASS 1')\n")


def project(attributes: bool = True) -> Path:
    """A repository with the real run_all.sh, a registry of two suites and a file outside the list."""
    repo = Path(tempfile.mkdtemp(prefix="registry-"))
    (repo / "tests").mkdir()
    shutil.copy(ROOT / "tests/run_all.sh", repo / "tests/run_all.sh")
    if attributes:
        shutil.copy(ROOT / ".gitattributes", repo / ".gitattributes")
    for name in ("one", "two"):
        suite(repo, name)
    (repo / REGISTRY).write_text("# the gate's subset\ntest_one.py\ntest_two.py\n")
    (repo / "notes.txt").write_text("# notes\nfirst\n")
    (repo / ".gitignore").write_text(".claude/state/\ntests/runs.log\n")
    sh(repo, "git", "init", "-q", "-b", "main")
    for key, value in (("user.name", "t"), ("user.email", "t@example.invalid")):
        sh(repo, "git", "config", key, value)
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "-m", "base")
    return repo


def branch(repo: Path, name: str, lines: str, *suites: str, file: str = REGISTRY) -> None:
    """A branch from main that appends `lines` to `file` and adds the named suites."""
    sh(repo, "git", "switch", "-q", "main")
    sh(repo, "git", "switch", "-q", "-c", name)
    with (repo / file).open("a") as handle:
        handle.write(lines)
    for one in suites:
        suite(repo, one)
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "-m", name)


def fast(repo: Path) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run the fast subset; what it printed and the suites that really ran, sorted."""
    (repo / "tests/runs.log").unlink(missing_ok=True)
    r = sh(repo, "bash", "tests/run_all.sh", "--fast")
    log = repo / "tests/runs.log"
    return r, sorted(log.read_text().split()) if log.is_file() else []


def names(repo: Path) -> list[str]:
    return [line for line in (repo / REGISTRY).read_text().splitlines() if line.startswith("test_")]


print("two branches add different suites to the registry")
repo = project()
branch(repo, "a", "# Board 1: test_a is in.\ntest_a.py\n", "a")
branch(repo, "b", "# Board 2: test_b is in.\ntest_b.py\n", "b")
r = sh(repo, "git", "merge", "-q", "a", "-m", "merge")
check("the merge is clean: exit 0 and nothing unmerged", r.returncode == 0 and sh(repo, "git", "status", "--porcelain").stdout == "", r.stdout + r.stderr)
text = (repo / REGISTRY).read_text()
check("both lines are there, each once, with their comments and no conflict marker", sorted(names(repo)) == ["test_a.py", "test_b.py", "test_one.py", "test_two.py"]
      and "# Board 1" in text and "# Board 2" in text and "<<<<" not in text and "====" not in text, text)
r, ran = fast(repo)
check("run_all.sh --fast runs both new suites and both old ones, each once", r.returncode == 0 and ran == ["a", "b", "one", "two"]
      and "PASS: 4 suites green (fast subset)" in r.stdout, (ran, r.stdout + r.stderr))
sh(repo, "git", "switch", "-q", "b")
sh(repo, "git", "reset", "-q", "--hard", "HEAD~1")   # b as it was before the merge
r = sh(repo, "git", "rebase", "-q", "a")
check("a rebase is clean too: the same four lines", r.returncode == 0 and sorted(names(repo)) == ["test_a.py", "test_b.py", "test_one.py", "test_two.py"], r.stdout + r.stderr + (repo / REGISTRY).read_text())
shutil.rmtree(repo, ignore_errors=True)

print("two branches add the same suite")
repo = project()
branch(repo, "a", "test_same.py\n", "same")
branch(repo, "b", "test_same.py\n", "same")
r = sh(repo, "git", "merge", "-q", "a", "-m", "merge")
r2, ran = fast(repo)
check("the same line alone: clean merge, the suite runs once", r.returncode == 0 and r2.returncode == 0 and ran == ["one", "same", "two"], (ran, r.stdout + r.stderr + r2.stdout + r2.stderr))
shutil.rmtree(repo, ignore_errors=True)
repo = project()
branch(repo, "a", "test_same.py\ntest_a.py\n", "same", "a")
branch(repo, "b", "test_b.py\ntest_same.py\n", "same", "b")
r = sh(repo, "git", "merge", "-q", "a", "-m", "merge")
check("the same line beside different ones: clean merge, and union left the line twice (the case the reader must survive)", r.returncode == 0
      and names(repo).count("test_same.py") == 2, (repo / REGISTRY).read_text() + r.stderr)
r, ran = fast(repo)
check("…the suite runs once, and the run counts five suites, not six", r.returncode == 0 and ran == ["a", "b", "one", "same", "two"]
      and "PASS: 5 suites green (fast subset)" in r.stdout and r.stdout.count("tests/test_same.py") == 1, (ran, r.stdout + r.stderr))
r = sh(repo, "bash", "tests/run_all.sh", "--fast", "--list")
check("…and --list names it once", r.stdout.split().count("tests/test_same.py") == 1 and len(r.stdout.split()) == 5, r.stdout)
shutil.rmtree(repo, ignore_errors=True)

print("the reader on what a merge can leave: a duplicate, an empty line, another order")
repo = project()
suite(repo, "three")
(repo / REGISTRY).write_text("test_two.py\n\n# a note between\ntest_three.py   # with a reason\n\n\ntest_two.py\ntest_one.py\ntest_three.py\n")
r = sh(repo, "bash", "tests/run_all.sh", "--fast", "--list")
check("every suite once, in the order of its first line", r.returncode == 0 and r.stdout.split() == ["tests/test_two.py", "tests/test_three.py", "tests/test_one.py"], r.stdout + r.stderr)
r, ran = fast(repo)
check("…and each runs once", r.returncode == 0 and ran == ["one", "three", "two"] and "PASS: 3 suites green (fast subset)" in r.stdout, (ran, r.stdout + r.stderr))
(repo / REGISTRY).write_text("test_one.py\ntest_one_more.py\n")
suite(repo, "one_more")
r, ran = fast(repo)
check("the negative case: a suite whose name only contains another's is not its duplicate", r.returncode == 0 and ran == ["one", "one_more"], (ran, r.stdout + r.stderr))
shutil.rmtree(repo, ignore_errors=True)

print("the negative cases: outside the list a conflict stays a conflict")
repo = project()
branch(repo, "a", "from a\n", file="notes.txt")
branch(repo, "b", "from b\n", file="notes.txt")
r = sh(repo, "git", "merge", "-q", "a", "-m", "merge")
check("a file outside the list conflicts as before", r.returncode != 0 and sh(repo, "git", "diff", "--name-only", "--diff-filter=U").stdout.split() == ["notes.txt"]
      and "<<<<<<<" in (repo / "notes.txt").read_text(), r.stdout + r.stderr)
shutil.rmtree(repo, ignore_errors=True)
repo = project(attributes=False)
branch(repo, "a", "test_a.py\n", "a")
branch(repo, "b", "test_b.py\n", "b")
r = sh(repo, "git", "merge", "-q", "a", "-m", "merge")
check("the registry itself conflicts without the attribute: the clean merges above are the attribute's work", r.returncode != 0
      and sh(repo, "git", "diff", "--name-only", "--diff-filter=U").stdout.split() == [REGISTRY], r.stdout + r.stderr)
shutil.rmtree(repo, ignore_errors=True)

print("the negative case: a line union brought back for a deleted suite")
repo = project()
sh(repo, "git", "switch", "-q", "-c", "a")
(repo / REGISTRY).write_text("# the gate's subset\ntest_one.py\n")
sh(repo, "git", "rm", "-q", "tests/test_two.py")
sh(repo, "git", "commit", "-q", "-am", "a: test_two is gone")
branch(repo, "b", "test_b.py\n", "b")
r = sh(repo, "git", "merge", "-q", "a", "-m", "merge")
check("the merge is clean, and the deleted suite's line is back", r.returncode == 0 and "test_two.py" in names(repo) and not (repo / "tests/test_two.py").exists(),
      (repo / REGISTRY).read_text() + r.stderr)
r, ran = fast(repo)
check("run_all.sh --fast refuses by name (exit 2) and runs nothing", r.returncode == 2 and "names a missing suite: test_two.py" in r.stderr and ran == [], (ran, r.stdout + r.stderr))
shutil.rmtree(repo, ignore_errors=True)

print("this repository: the attribute is on the registry, and on nothing else that was weighed")


def driver(path: str) -> str:
    return sh(ROOT, "git", "check-attr", "merge", "--", path).stdout.strip().rpartition(": ")[2]


check("tests/fast-suites.txt merges by union", driver(REGISTRY) == "union", driver(REGISTRY))
OUT = ("tests/hook-env-exempt.txt", ".claude/ownership.txt", ".gitignore", ".gitattributes", "AGENTS.md", "docs/engine-limits.md", "evals/README.md",
       ".claude/project.env", ".engine/rules.md", ".engine/engine-feedback.md", ".engine/overseer/ledger.md", ".engine/lesson-queue.md",
       "tasks/ANOMALIES.md", "tests/run_all.sh", "engine.py")
left = {path: driver(path) for path in OUT if driver(path) != "unspecified"}
check("the files left out on purpose, the journals and the code have no merge driver", left == {}, left)
listed = [line.split()[0] for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines() if "merge=union" in line and not line.lstrip().startswith("#")]
check("…and .gitattributes gives union to that one file by its full path, not by a pattern", listed == [REGISTRY], listed)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
