#!/usr/bin/env python3
"""The overseer agent changes nothing: the perimeter hooks refuse it (board 055).

Until board 055 the ban lived in overseer_verdict.py's guard and covered the editing tools only;
the agent's Bash wrote freely, and only the tree's fingerprint noticed, after the fact. Now:

  - protect-paths.sh refuses Edit, Write, MultiEdit and NotebookEdit inside the agent
    (`agent_type` in the hook envelope), whatever the path;
  - block-dangerous.sh hands the agent's shell command to shell_readonly.py: a write anywhere but
    a temporary directory is refused, in every form — a redirection, tee, rm, cp, an in-place
    sed, inline code, a git command that changes the repository, a formatter;
  - the negative cases: the agent runs tests and linters, reads git, and does anything inside a
    copy under /tmp; a builder — no `agent_type`, or another agent's — is judged as before;
  - overseer_verdict.py's guard no longer answers an edit (the duplicate is gone) and still
    refuses the agent a start of another agent.

Every hook case runs the real hook. Run: python3 tests/test_overseer_readonly.py   Exit: 0 green, 1 otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import hook_env, main_repo

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
P = main_repo("feat/x")   # it lives under /tmp, like every sandbox: the audited tree is never "temporary" for that
INSIDE = {"agent_type": "overseer", "agent_id": "a1"}
SECRET = "cat .e" + "nv"   # split, so that the hook under test does not refuse a shell command that handles THIS file
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def shell(cmd: str, who: dict[str, str], cwd: str = P, **env: str) -> subprocess.CompletedProcess[str]:
    envelope = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd} | who
    return subprocess.run(["bash", str(HOOKS / "block-dangerous.sh")], input=json.dumps(envelope), capture_output=True, text=True,
                          env=hook_env(P, **({"HOME": "/home/u", "TMPDIR": ""} | env)), cwd=P, check=False)


def edit_denied(tool: str, tool_input: dict[str, str], who: dict[str, str]) -> bool:
    done = subprocess.run(["bash", str(HOOKS / "protect-paths.sh")], input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input} | who),
                          capture_output=True, text=True, env=hook_env(P), check=False)
    return '"deny"' in done.stdout and "read-only" in done.stdout


WRITES = [
    "echo x > src/pricing.py", "echo x >> README.md", "printf x > ./notes.txt", f"echo x > {P}/src/a.py", "cat a b > merged.txt",
    "pytest -q > report.txt 2>&1", "echo x | tee src/pricing.py", "pytest | tee -a out.log", "sed -i s/a/b/ src/pricing.py",
    "sed -i -e s/a/b/ src/pricing.py", "perl -pi -e s/a/b/ src/pricing.py", "rm src/pricing.py", "rm -rf build", "mv a.py b.py",
    "cp /tmp/x src/pricing.py", "cp -r /tmp/fixed/. .", "touch src/new.py", "truncate -s 0 src/pricing.py", "chmod +x run.sh",
    "mkdir -p src/new && touch src/new/a.py", "dd if=/dev/zero of=blob bs=1 count=1", "curl -o data.json https://example.com/x",
    "python3 -c 'open(\"src/pricing.py\",\"w\").write(\"x\")'", "python3 -c 'from pathlib import Path; Path(\"src/a.py\").write_text(\"x\")'",
    "python3 - <<'PY'\nfrom pathlib import Path\nPath('tests/test_a.py').write_text('x')\nPY",
    "node -e 'require(\"fs\").writeFileSync(\"src/a.js\",\"x\")'", "bash -c 'echo x > src/a.py'", "sh -c \"rm src/a.py\"",
    "git stash", "git stash push -m wip", "git checkout -- src/pricing.py", "git checkout HEAD~1 -- src/pricing.py", "git restore src/pricing.py",
    "git reset --hard HEAD", "git add -A", "git commit -m x", "git apply /tmp/fix.patch", "git clean -fd", "git merge main",
    "git -C . stash", "git tag v9", "git branch -D feat/x", "git switch main", "git worktree add ~/copy", "git clone . ~/copy",
    "ruff format src/", "ruff check --fix src/", "black src/", "prettier --write src/a.js", "eslint --fix src/",
    "cd /tmp/copy && cd - && rm a.py", "cd src && rm pricing.py", "echo x > $OUT/a.py", "echo x > ~/notes.md",
    "echo x > ~/engine-ops/tasks-inbox/001-x.md", "ls; echo done > .claude/state/overseer/verdicts.jsonl",
    "cp -r . /tmp/copy && rm src/a.py", "echo x > /tmp/../etc/passwd",
]
READS = [
    "pytest -q", "python3 tests/test_board.py 2>&1 | tail -5", "bash tests/run_all.sh --fast", "uv run pytest -x -q tests/test_pricing.py",
    "ruff check src/", "ruff format --check src/", "black --check src/", "mypy src/", "git status", "git diff", "git diff HEAD~1 -- src/",
    "git log --oneline -5", "git show HEAD:src/pricing.py", "git stash list", "git branch --show-current", "git branch -a", "git tag -l",
    "git remote -v", "git apply --check /tmp/fix.patch", "git worktree list", "git config --get user.name", "git rev-parse HEAD",
    "cat src/pricing.py", "grep -rn 'a > b' src/", "grep -n '=>' src/a.js", "awk '$1 > 5' data.txt", "python3 -c 'print(1 > 0)'",
    "python3 -c \"import json; print(json.load(open('.claude/state/x.json')))\"", "python3 -c 'print(open(\"src/a.py\").read())'",
    "sed -n 1,20p src/pricing.py", "wc -l src/*.py", "ls -la", "find . -name '*.py' | head", "diff -u a.py b.py",
    "pytest -q > /tmp/report.txt 2>&1", "pytest -q 2>/dev/null", "pytest -q 2>&1", "git diff > /tmp/change.patch", "echo x | tee /tmp/out.log",
    "cp -r . /tmp/audit-copy", "git clone -q . /tmp/audit-copy", "git worktree add /tmp/audit-wt HEAD",
    "cd /tmp/audit-copy && git stash && pytest -q", "cd /tmp/audit-copy && git checkout HEAD~1 -- src/pricing.py && pytest -q",
    "cd /tmp/audit-copy && echo x > probe.py && rm probe.py", "git -C /tmp/audit-copy reset --hard HEAD~1", "rm -rf /tmp/audit-copy",
    "mkdir -p /tmp/audit && cp src/pricing.py /tmp/audit/", "sed -i s/a/b/ /tmp/audit-copy/src/pricing.py",
    "python3 -c 'open(\"/tmp/audit/x.txt\",\"w\").write(\"x\")'", "cd /tmp/audit-copy && ruff format src/", "touch /tmp/marker",
    "python3 .claude/hooks/overseer_verdict.py show", "head -50 .claude/state/overseer/requests/x/turn.md",
    "TMP=$(mktemp -d) && echo $TMP", "test -f src/a.py && echo yes", "[ 3 -gt 2 ] && echo ok", "echo 'a -> b'",
]

print("inside the overseer agent a shell write outside a temporary directory is refused")
for cmd in WRITES:
    done = shell(cmd, INSIDE)
    check(f"refused: {cmd!r}", done.returncode == 2 and "the overseer agent is read-only" in done.stderr, f"exit {done.returncode}: {done.stderr[:200]}")

print("\nthe negative cases: the agent's reading, its checks and its work in a copy under /tmp pass")
for cmd in READS:
    done = shell(cmd, INSIDE)
    check(f"allowed: {cmd!r}", done.returncode == 0, f"exit {done.returncode}: {done.stderr[:200]}")

print("\nthe working directory of the shell is followed")
for cmd in ('D=$(mktemp -d) && cp -r . "$D" && cd "$D" && git stash && pytest -q', "COPY=`mktemp -d` ; cp -r . ${COPY}/ ; rm -rf $COPY",
            "OUT=$(mktemp) && pytest -q > $OUT 2>&1; tail -5 $OUT", 'T="$(mktemp -d -t audit.XXXXXX)" && git clone -q . "$T/copy"'):
    check(f"a name assigned from mktemp is a temporary place: {cmd!r}", shell(cmd, INSIDE).returncode == 0, shell(cmd, INSIDE).stderr[:200])
for cmd in ("D=$(mktemp -d -p .) && cp -r src $D", "D=$(mktemp -d --tmpdir=$HOME) && cp -r . $D", 'D=$(pwd) && echo x > "$D/a.py"', 'cp -r . "$D"', "D=$(mktemp -d) && echo x > $DIR/a.py"):
    check(f"negative — a name whose place the text does not show is not one: {cmd!r}", shell(cmd, INSIDE).returncode == 2)
check("already in a copy under /tmp: a relative write there passes", shell("echo x > probe.py && git stash", INSIDE, cwd="/tmp/audit-copy").returncode == 0)
check("... and a path that climbs back into the project does not", shell(f"echo x > {P}/a.py", INSIDE, cwd="/tmp/audit-copy").returncode == 2)
check("TMPDIR names another temporary directory", shell("echo x > /scratch/t/a.txt", INSIDE, TMPDIR="/scratch/t").returncode == 0
      and shell("echo x > /scratch/other/a.txt", INSIDE, TMPDIR="/scratch/t").returncode == 2)

print("\na builder is judged as before: no agent_type, or another agent's")
for who, label in (({}, "the builder"), ({"agent_type": "simplifier"}, "another agent"), ({"agent_type": "overseer-like"}, "a name that only starts alike")):
    for cmd in ("echo x > src/pricing.py", "sed -i s/a/b/ src/pricing.py", "git stash", "git checkout -- src/pricing.py", "rm -rf build", "ruff format src/", "git add -A"):
        done = shell(cmd, who)
        check(f"{label}: {cmd!r} is not refused", done.returncode == 0, done.stderr[:200])
check("what is refused to everyone is refused to the agent too", shell(SECRET, INSIDE).returncode == 2 and shell(SECRET, {}).returncode == 2)

print("\nwithout python3 the agent's shell commands are refused, a builder's are not")
shims = Path(tempfile.mkdtemp(prefix="no-python-"))
for tool in ("bash", "jq", "git", "grep", "tr", "sed", "cat", "dirname", "tail"):
    found = shutil.which(tool)
    if found:
        (shims / tool).symlink_to(found)
done = shell("pytest -q", INSIDE, PATH=str(shims))
check("the agent: refused, and it says why", done.returncode == 2 and "no python3" in done.stderr, done.stderr[:300])
check("the builder: an ordinary command passes", shell("pytest -q", {}, PATH=str(shims)).returncode == 0)
shutil.rmtree(shims, ignore_errors=True)

print("\nan editing tool inside the agent is refused, whatever the path")
for tool, tool_input in (("Edit", {"file_path": f"{P}/src/pricing.py"}), ("Write", {"file_path": f"{P}/tests/test_new.py"}), ("MultiEdit", {"file_path": "README.md"}),
                         ("Write", {"file_path": "/tmp/audit-copy/a.py"}), ("NotebookEdit", {"notebook_path": f"{P}/analysis.ipynb"}), ("Edit", {})):
    check(f"{tool} {tool_input or '(no path in the call)'}: denied as read-only", edit_denied(tool, tool_input, INSIDE))
for who, label in (({}, "the builder"), ({"agent_type": "slice-builder"}, "another agent")):
    check(f"negative — {label}'s Edit of a source file is not denied", not edit_denied("Edit", {"file_path": f"{P}/src/pricing.py"}, who))
done = subprocess.run(["bash", str(HOOKS / "protect-paths.sh")], input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": f"{P}/.claude/settings.json"}}),
                      capture_output=True, text=True, env=hook_env(P), check=False)
check("negative — the builder's edit of a protected path is still denied, by its pattern", '"deny"' in done.stdout and "protected pattern" in done.stdout)

print("\nthe guard of overseer_verdict.py: the duplicate is gone, the Agent tool is still refused")


def guard(envelope: dict[str, object]) -> str:
    return subprocess.run([sys.executable, str(HOOKS / "overseer_verdict.py"), "guard"], input=json.dumps(envelope), capture_output=True, text=True,
                          env=hook_env(P), cwd=P, check=False).stdout


check("an Edit inside the agent is no longer the guard's to answer", guard(INSIDE | {"tool_name": "Edit", "tool_input": {"file_path": "src/pricing.py"}}) == "")
said = guard(INSIDE | {"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "prompt": "fix it"}})
check("inside the agent the Agent tool is refused", '"deny"' in said and "read-only" in said, said)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
