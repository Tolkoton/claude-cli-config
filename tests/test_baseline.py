#!/usr/bin/env python3
"""The snapshot "as it was" and the rule "no worse than it was" (board 071): baseline.py and
what gate.py does with `.engine/baseline.json`.

Deterministic: every scene runs the real gate.py and baseline.py in a throwaway git repository.
The project's test command and linter are small scripts that print what the files `failing.txt`
and `lint.txt` say, so a scene decides what fails by writing one line. The negative case comes
first in every scene: a check is shown to BLOCK before it is shown to pass.

SCENES
  - a project with three old failures: the agent adds a fourth — block; adds none — the turn ends;
  - the agent writes a line into the snapshot (by hand, by `record` in its session, by creating
    the first snapshot) — block; the owner's `record` in their own terminal — passes;
  - an old test is fixed — `tighten` shrinks the snapshot, and the test is guarded from then on;
  - lint and type counts per (file, rule): above the snapshot — block; at or below — pass;
  - a failure that names nothing readable blocks with or without a snapshot;
  - a project without a snapshot behaves as before this task, to the very commands issued.

Run:   python3 tests/test_baseline.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tool_pins import tool_versions as TOOL_VERSIONS

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
GATE = HOOKS / "gate.py"
BASELINE = HOOKS / "baseline.py"
SNAPSHOT = ".engine/baseline.json"
PASS = FAIL = 0

spec = importlib.util.spec_from_file_location("baseline", BASELINE)
assert spec is not None and spec.loader is not None
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str) -> None:
    sh(root, "git", "add", "-A")
    done = sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    assert done.returncode == 0, done.stderr


# The project's checks: every line of failing.txt is a failing test, every line of lint.txt /
# types.txt a finding; the command fails when its file has a line. `broken` fails and names nothing.
CHECK = '#!/usr/bin/env bash\nf="$(dirname "$0")/{file}"\n[ -s "$f" ] || exit 0\n{print}\nexit 1\n'
OLD = ["tests/test_pay.py::test_refund", "tests/test_pay.py::test_rounding", "tests/test_user.py::test_rename"]
FOURTH = "tests/test_user.py::test_delete"


def project(tests: list[str] | None = None, lint: list[str] | None = None, types: list[str] | None = None) -> Path:
    """A legacy project: code, three checks that read their findings from files, one commit."""
    root = Path(tempfile.mkdtemp(prefix="baseline-"))
    sh(root, "git", "init", "-q", "-b", "main")
    (root / ".claude").mkdir()
    (root / "checks").mkdir()
    (root / "checks/tests.sh").write_text(CHECK.format(file="failing.txt", print='sed "s/^/FAILED /; s/$/ - AssertionError/" "$f"; echo "3 failed, 9 passed"'))
    (root / "checks/lint.sh").write_text(CHECK.format(file="lint.txt", print='cat "$f"'))
    (root / "checks/types.sh").write_text(CHECK.format(file="types.txt", print='cat "$f"'))
    (root / ".claude/project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="bash checks/lint.sh"\n'
                                              'TYPECHECK_CMD="bash checks/types.sh"\nTEST_CMD="bash checks/tests.sh"\n')
    (root / ".gitignore").write_text(".claude/state/\n")
    (root / "pay.py").write_text("x = 1\n")
    findings(root, tests, lint, types)
    commit(root, "legacy")
    return root


def findings(root: Path, tests: list[str] | None = None, lint: list[str] | None = None, types: list[str] | None = None) -> None:
    for name, lines in (("failing.txt", tests), ("lint.txt", lint), ("types.txt", types)):
        if lines is not None:
            (root / "checks" / name).write_text("".join(f"{line}\n" for line in lines))


def run(script: Path, root: Path, *args: str, session: bool, stdin: Any = None) -> subprocess.CompletedProcess[str]:
    """`session=True`: as the agent's tools run it (CLAUDECODE set); False: the owner's terminal."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(root)}
    if session:
        env["CLAUDECODE"] = "1"
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env,
                          input=json.dumps(stdin) if stdin is not None else "", check=False)


def gate(root: Path, layer: str = "stop") -> subprocess.CompletedProcess[str]:
    # The Stop counter is not what these scenes are about: the third block in a row would let the
    # turn end with an escalation (tests/test_gate.py), so every run starts from zero.
    (root / ".claude/state/gate/stop-count.json").unlink(missing_ok=True)
    return run(GATE, root, "--layer", layer, session=True)


def record(root: Path, session: bool = False) -> subprocess.CompletedProcess[str]:
    return run(BASELINE, root, "record", session=session)


def report(root: Path) -> Any:
    return json.loads((root / ".claude/state/gate/last-report.json").read_text())


def found(root: Path, rule: str, severity: str = "block") -> list[dict[str, Any]]:
    return [f for f in report(root)["findings"] if f["rule"] == rule and f["severity"] == severity]


def snapshot(root: Path) -> Any:
    return json.loads((root / SNAPSHOT).read_text())


def onboarded(tests: list[str] | None = None, lint: list[str] | None = None, types: list[str] | None = None) -> Path:
    """A legacy project whose owner took the snapshot and committed it."""
    root = project(tests, lint, types)
    done = record(root)
    assert done.returncode == 0, done.stderr
    commit(root, "snapshot")
    return root


def touch(root: Path) -> None:
    """The turn changes a code file, so the Stop layer has something to verify."""
    (root / "pay.py").write_text((root / "pay.py").read_text() + "y = 2\n")


# ---------------------------------------------------------------- without a snapshot: as before
print("a project without a snapshot behaves as before")
r = project(tests=OLD)
touch(r)
p = gate(r)
check("three failing tests and no snapshot: the Stop gate blocks — «must be clean»", p.returncode == 2 and "TESTS FAILED" in p.stderr, (p.returncode, p.stderr))
check("…and the report says nothing about a snapshot", not any(f["rule"].startswith("baseline/") for f in report(r)["findings"]), report(r)["findings"])
findings(r, tests=[])
check("…clean: the turn ends", gate(r).returncode == 0)
r = project()
(r / ".claude/project.env").write_text('CODE_EXTENSIONS="py"\n')
(r / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
(r / "tests").mkdir()
(r / "tests/test_pay.py").write_text("def test_a():\n    assert True\n")
shims = r / "_shims"
shims.mkdir()
for tool in ("ruff", "mypy", "pytest"):
    # `--version` names the pinned release (tool_versions.py, board 107): the gate runs a tool on PATH only at it.
    pinned = TOOL_VERSIONS.VERSIONS[tool]
    (shims / tool).write_text(f'#!/usr/bin/env bash\n[ "$1" = --version ] && {{ echo "{tool} {pinned}"; exit 0; }}\n'
                              f'echo "{tool} $*" >> "{r}/calls.log"\nexit 0\n')
    (shims / tool).chmod(0o755)
(r / ".gitignore").write_text(".claude/state/\n_shims/\ncalls.log\n")
commit(r, "python defaults")
touch(r)
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(r), "PATH": f"{shims}:{os.environ['PATH']}"}
subprocess.run([sys.executable, str(GATE), "--layer", "stop"], cwd=r, env=env, capture_output=True, check=False)
calls = (r / "calls.log").read_text()
check("no snapshot: the default commands are the ones issued before this task",
      "ruff check --force-exclude pay.py\n" in calls and "pytest -x --no-header -q tests/test_pay.py\n" in calls, calls)
(r / "calls.log").unlink()
(r / ".engine").mkdir()
(r / SNAPSHOT).write_text(baseline.render(baseline.empty()))
commit(r, "an empty snapshot")
touch(r)
subprocess.run([sys.executable, str(GATE), "--layer", "stop"], cwd=r, env=env, capture_output=True, check=False)
calls = (r / "calls.log").read_text()
check("with a snapshot: ruff prints one line per finding and pytest runs to the end, not to the first failure",
      "ruff check --force-exclude --output-format concise pay.py\n" in calls and "pytest --no-header -q tests/test_pay.py\n" in calls, calls)

# ---------------------------------------------------------------- three old failures, a fourth
print("three old failures: a fourth blocks, none passes")
r = onboarded(tests=OLD)
check("the owner's record lists the three failing tests by name", snapshot(r)["tests"] == sorted(OLD), snapshot(r))
check("…with how long the full run took, and no coverage figure", "duration_s" in snapshot(r)["measured"]["tests"] and "coverage" not in json.dumps(snapshot(r)))
touch(r)
findings(r, tests=[*OLD, FOURTH])
p = gate(r)
check("the agent adds a fourth failure: the Stop gate blocks", p.returncode == 2, (p.returncode, p.stderr))
blocks = found(r, "tests")
check("…on the new test only, by name", len(blocks) == 1 and FOURTH in blocks[0]["message"] and not any(o in blocks[0]["message"] for o in OLD), blocks)
check("…and the reason says it is worse than the snapshot", "worse than the snapshot" in p.stderr and FOURTH in p.stderr, p.stderr)
hooked = run(GATE, r, "--layer", "stop", "--hook", session=True, stdin={"session_id": "s", "stop_hook_active": False})
payload = json.loads(hooked.stdout or "{}")
check("…the same through the hook protocol: decision block, the new test in the reason",
      payload.get("decision") == "block" and FOURTH in payload.get("reason", ""), hooked.stdout)
findings(r, tests=OLD)
p = gate(r)
check("the agent adds none: the turn ends, though the test command still fails", p.returncode == 0 and report(r)["result"] == "pass", (p.returncode, p.stderr))
check("…and the report says only old failures were seen", len(found(r, "baseline/tests", "log")) == 1, report(r)["findings"])
findings(r, tests=OLD[:2])
check("one of the three is fixed and nothing is new: the turn ends", gate(r).returncode == 0)
commit(r, "work")
check("pre_commit and ci judge against the snapshot too", (gate(r, "pre_commit").returncode, gate(r, "ci").returncode) == (0, 0))
check("…and say that a fixed entry is still listed", "tighten" in found(r, "baseline/stale", "warn")[0]["hint"], report(r)["findings"])
findings(r, tests=[*OLD, FOURTH])
check("…a fourth failure blocks there as well", (gate(r, "pre_commit").returncode, gate(r, "ci").returncode) == (2, 2))

# ---------------------------------------------------------------- the snapshot cannot be loosened
print("the agent cannot loosen the snapshot")
r = onboarded(tests=OLD)
touch(r)
findings(r, tests=[*OLD, FOURTH])
data = snapshot(r)
data["tests"].append(FOURTH)
(r / SNAPSHOT).write_text(baseline.render(data))
p = gate(r)
blocks = found(r, "bypass/baseline")
check("the agent writes the fourth test into the snapshot: block by the bypass guard", p.returncode == 2 and len(blocks) == 1 and FOURTH in blocks[0]["message"], (p.stderr, report(r)["findings"]))
check("…the hint names the owner's command", "baseline.py record" in blocks[0]["hint"] and "own terminal" in blocks[0]["hint"], blocks)
sh(r, "git", "add", "-A")
check("…staged, the pre_commit layer blocks it as well", gate(r, "pre_commit").returncode == 2 and found(r, "bypass/baseline"), report(r)["findings"])
sh(r, "git", "checkout", "-q", "HEAD", "--", SNAPSHOT)
before = (r / SNAPSHOT).read_text()
p = record(r, session=True)
check("`record` inside the agent's session refuses to loosen: exit 2, the file untouched",
      p.returncode == 2 and (r / SNAPSHOT).read_text() == before and FOURTH in p.stderr and "own terminal" in p.stderr, (p.returncode, p.stderr))
(r / SNAPSHOT).write_text(before.replace('"tests": [', '"tests": [\n    "tests/test_x.py::test_only_listed",'))
check("a line for a test that does not even fail is still a loosening: block", gate(r).returncode == 2 and found(r, "bypass/baseline"), report(r)["findings"])
(r / SNAPSHOT).write_text("{ not json")
p = gate(r)
check("a snapshot that cannot be read excuses nothing: the old failures block again",
      p.returncode == 2 and found(r, "baseline/unreadable", "warn") and found(r, "tests"), report(r)["findings"])
sh(r, "git", "checkout", "-q", "HEAD", "--", SNAPSHOT)
p = record(r, session=False)
check("the owner's `record` in their own terminal takes the fourth in", p.returncode == 0 and FOURTH in snapshot(r)["tests"], (p.returncode, p.stderr))
p = gate(r)
check("…and the gate lets exactly that text through, saying who approved it", p.returncode == 0 and found(r, "bypass/baseline", "log"), (p.stderr, report(r)["findings"]))
data = snapshot(r)
data["tests"].append("tests/test_x.py::test_after_the_approval")
(r / SNAPSHOT).write_text(baseline.render(data))
check("…a line added after the approval is not covered by it: block", gate(r).returncode == 2 and found(r, "bypass/baseline"), report(r)["findings"])

r = project(tests=OLD)
touch(r)
p = record(r, session=True)
check("no snapshot yet: the agent's `record` refuses the first one", p.returncode == 2 and not (r / SNAPSHOT).exists() and "Nothing was written" in p.stderr, p.stderr)
clean = project()
p = record(clean, session=True)
check("…even an empty one: whether a project has a snapshot is the owner's decision", p.returncode == 2 and not (clean / SNAPSHOT).exists() and "no snapshot yet" in p.stderr, p.stderr)
(r / ".engine").mkdir()
(r / SNAPSHOT).write_text(baseline.render(baseline.empty() | {"tests": OLD}))
check("…and a first snapshot written by hand is a loosening: block", gate(r).returncode == 2 and found(r, "bypass/baseline"), report(r)["findings"])

# ---------------------------------------------------------------- tighten
print("an old test is fixed: the snapshot shrinks")
r = onboarded(tests=OLD, lint=["pay.py:1:1: F401 unused", "pay.py:2:1: F401 unused", "pay.py:3:1: E501 long"])
touch(r)
findings(r, tests=OLD[1:], lint=["pay.py:1:1: F401 unused"])
p = run(BASELINE, r, "tighten", session=True)
check("`tighten` (the agent may run it) drops the fixed test and names it", p.returncode == 0 and snapshot(r)["tests"] == sorted(OLD[1:]) and OLD[0] in p.stdout, (p.stdout, p.stderr))
check("…lowers a count that went down and drops a rule that is gone", snapshot(r)["lint"] == {"pay.py": {"F401": 1}}, snapshot(r)["lint"])
check("the shrunk snapshot passes the gate: a tightening is not a bypass", gate(r).returncode == 0 and not found(r, "bypass/baseline"), report(r)["findings"])
commit(r, "fixed one")
touch(r)
findings(r, tests=OLD)
p = gate(r)
check("the fixed test breaks again: now it blocks", p.returncode == 2 and OLD[0] in found(r, "tests")[0]["message"], report(r)["findings"])
findings(r, tests=[*OLD[1:], FOURTH])
before = (r / SNAPSHOT).read_text()
p = run(BASELINE, r, "tighten", session=True)
check("`tighten` never adds: a new failure leaves the snapshot as it was", p.returncode == 0 and (r / SNAPSHOT).read_text() == before and "nothing was fixed" in p.stdout, p.stdout)
findings(r, tests=OLD[1:])
(r / "checks/tests.sh").write_text("#!/usr/bin/env bash\necho 'Segmentation fault'\nexit 139\n")
before = (r / SNAPSHOT).read_text()
p = run(BASELINE, r, "tighten", session=True)
check("a test run that crashed without naming a test proves nothing fixed: the list stays", (r / SNAPSHOT).read_text() == before, (p.stdout, p.stderr))
plain = project()
p = run(BASELINE, plain, "tighten", session=True)
check("no snapshot: `tighten` has nothing to do and creates none", p.returncode == 0 and not (plain / SNAPSHOT).exists(), p.stderr)
p = run(BASELINE, r, "show", session=True)
check("`show` lists what is left", p.returncode == 0 and OLD[1] in p.stdout and "[F401] 1" in p.stdout, p.stdout)

# ---------------------------------------------------------------- lint and types per (file, rule)
print("lint and types: the count per (file, rule)")
LINT = ["pay.py:1:1: F401 [*] `os` imported but unused", "pay.py:2:1: F401 [*] `re` imported but unused", "user.py:9:1: E501 line too long"]
TYPES = ["pay.py:4: error: Incompatible types in assignment  [assignment]", "pay.py:4: note: see the docs"]
r = onboarded(lint=LINT, types=TYPES)
check("the record counts findings per file and rule; a note is not a finding",
      snapshot(r)["lint"] == {"pay.py": {"F401": 2}, "user.py": {"E501": 1}} and snapshot(r)["types"] == {"pay.py": {"assignment": 1}}, snapshot(r))
touch(r)
findings(r, lint=[*LINT, "pay.py:7:1: F401 [*] `sys` imported but unused"])
p = gate(r)
blocks = found(r, "lint")
check("a third F401 in a file that had two: block, naming the file, the rule and both numbers",
      p.returncode == 2 and len(blocks) == 1 and blocks[0]["file"] == "pay.py" and "F401: 3 now, 2 in the snapshot" in blocks[0]["message"], (p.stderr, blocks))
findings(r, lint=[LINT[0], LINT[2], "pay.py:7:1: E711 comparison to None"])
p = gate(r)
check("fewer of the old rule but a rule the file never had: block on the new rule", p.returncode == 2 and "E711: 1 now, 0" in found(r, "lint")[0]["message"], report(r)["findings"])
findings(r, lint=["pay.py:30:1: F401 [*] `os` imported but unused", "pay.py:41:1: F401 [*] `re` imported but unused", LINT[2]])
check("the same findings on other lines (the code moved): the turn ends", gate(r).returncode == 0, report(r)["findings"])
findings(r, lint=LINT, types=[*TYPES, "pay.py:8: error: Missing return statement  [return]"])
p = gate(r)
check("a new type error: block", p.returncode == 2 and "return: 1 now, 0" in found(r, "typecheck")[0]["message"], report(r)["findings"])
findings(r, types=TYPES)
(r / "checks/lint.sh").write_text("#!/usr/bin/env bash\necho 'ruff: command not found'\nexit 127\n")
(r / ".gitignore").write_text(".claude/state/\nchecks/\n")
p = gate(r)
check("a linter that fails and names no file and line blocks, snapshot or not", p.returncode == 2 and found(r, "lint") and "LINT FAILED" in p.stderr, (p.stderr, report(r)["findings"]))

r = project(tests=OLD)
(r / ".claude/project.env").write_text((r / ".claude/project.env").read_text().replace("tests.sh", "tests.sh -x"))
commit(r, "a test command that stops at the first failure")
p = record(r)
check("`record` warns that a test command stopping at the first failure hides the rest", p.returncode == 0 and "first failure" in p.stderr, p.stderr)
commit(r, "snapshot")
touch(r)
check("…and so does the gate, as a warning", gate(r).returncode == 0 and found(r, "baseline/exitfirst", "warn"), report(r)["findings"])

# ---------------------------------------------------------------- the readers
print("what is read from a command's output")
names = baseline.failed_tests("FAILED tests/a.py::test_x[1 2] - assert 1 == 2\nERROR tests/b.py - ImportError\n"
                              "FAIL: test_y (tests.c.T.test_y)\nfailed to connect\n  FAILED indented\n")
check("pytest's and unittest's failure lines, and nothing else", names == {"tests/a.py::test_x[1 2]", "tests/b.py", "test_y (tests.c.T.test_y)"}, names)
counts = baseline.diagnostic_counts(f"{ROOT}/a.py:1:2: F401 x\n./a.py:5: F401 y\nsrc/b.ts:3:1: unexpected any [no-explicit-any]\nc.sh:2:1: something odd\n"
                                    "a.py:9: note: more\nnot a finding\n", ROOT)
check("findings per file and rule: absolute and ./ paths are one file; a trailing [code]; `other` when there is none",
      counts == {"a.py": {"F401": 2}, "src/b.ts": {"no-explicit-any": 1}, "c.sh": {"other": 1}}, counts)
check("loosened: a missing or broken new file permits nothing", baseline.loosened('{"tests": ["a"]}', None) == [] and baseline.loosened('{"tests": ["a"]}', "{") == [])
check("loosened: a removed test and a lowered count are not", baseline.loosened('{"tests": ["a", "b"], "lint": {"f": {"R": 2}}}', '{"tests": ["a"], "lint": {"f": {"R": 1}}}') == [])
check("loosened: a raised count, a new rule and a new file each are",
      len(baseline.loosened('{"lint": {"f": {"R": 1}}}', '{"lint": {"f": {"R": 2, "S": 1}, "g": {"R": 1}}}')) == 3)
check("the snapshot is the project's, the script the engine's, the approval machine state",
      SNAPSHOT.startswith(".engine/") and str(baseline.SEAL_REL).startswith(".claude/state/"))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
