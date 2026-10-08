#!/usr/bin/env python3
"""The delete guard (board 072): delete_guard.py and what gate.py does with it.

Deterministic: every scene runs the real gate.py in a throwaway git repository. The project has a
module with its test file (pay.py), a module no test touches (legacy.py) and a module whose
function a test only mentions (util.py). The negative case comes first in every scene: the guard
is shown to BLOCK before it is shown to pass.

SCENES
  - a function, a class, a file of untested code deleted — block (turn end, hook protocol, pre-commit);
  - the same with a test — passes; moved within the change — passes;
  - more than DELETE_GUARD_LINES lines removed inside one function — block; at the threshold — passes;
  - a simplifier finding the owner confirmed — passes; confirmed inside the session, or with no
    tool evidence — refused, still a block;
  - the owner's grant in a sealed contract — passes; in an unsealed one — block;
  - DELETE_GUARD_LINES changed without the sealed contract naming it — block;
  - with COVERAGE_CMD the answer is the coverage of the code BEFORE the change, with the tests of
    the change laid over it; without a readable report the coarser check is used, with a warning.

Run:   python3 tests/test_delete_guard.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
GATE = HOOKS / "gate.py"
GUARD = HOOKS / "delete_guard.py"
PASS = FAIL = 0

sys.path.insert(0, str(HOOKS))
import delete_guard  # noqa: E402  # gate-allow: the module lives beside the hooks, not on the path


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str) -> None:
    sh(root, "git", "add", "-A")
    done = sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    assert done.returncode == 0, done.stderr


BIG = "def big(n):\n    total = 0\n" + "".join(f"    total += n * {i}\n" for i in range(30)) + "    return total\n"
LEGACY = ('"""Code nobody wrote a test for."""\n\n\n'
          "def export_csv(rows):\n    out = []\n    for row in rows:\n        out.append(','.join(row))\n    return out\n\n\n"
          "class Report:\n    def render(self):\n        return 'report'\n\n    def title(self):\n        return 'title'\n\n\n"
          + BIG)
PAY = "def refund(amount):\n    return -amount\n\n\ndef charge(amount):\n    return amount\n"
UTIL = "def slugify(text):\n    return text.lower()\n\n\ndef unused(text):\n    return text\n"
ENV = 'CODE_EXTENSIONS="py sh"\nTEST_CMD="true"\n'


def project(env: str = ENV) -> Path:
    root = Path(tempfile.mkdtemp(prefix="delete-guard-"))
    sh(root, "git", "init", "-q", "-b", "main")
    for rel, text in ((".claude/project.env", env), (".gitignore", ".claude/state/\n"), ("legacy.py", LEGACY),
                      ("pay.py", PAY), ("util.py", UTIL), ("deploy.sh", "".join(f"echo step {i}\n" for i in range(30))),
                      ("tests/test_pay.py", "from pay import refund\nfrom util import slugify\n\n\ndef test_refund():\n    assert refund(1) == -1\n")):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    commit(root, "legacy")
    return root


def run(script: Path, root: Path, *args: str, session: bool, stdin: Any = None) -> subprocess.CompletedProcess[str]:
    """`session=True`: as the agent's tools run it (CLAUDECODE set); False: the owner's terminal."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"} | {"CLAUDE_PROJECT_DIR": str(root)}
    if session:
        env["CLAUDECODE"] = "1"
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env,
                          input=json.dumps(stdin) if stdin is not None else "", check=False)


def gate(root: Path, layer: str = "stop", *args: str, stdin: Any = None) -> subprocess.CompletedProcess[str]:
    # The Stop counter is not what these scenes are about (tests/test_gate.py): every run starts from zero.
    (root / ".claude/state/gate/stop-count.json").unlink(missing_ok=True)
    return run(GATE, root, "--layer", layer, *args, session=True, stdin=stdin)


def found(root: Path, rule: str, severity: str = "block") -> list[dict[str, Any]]:
    report = json.loads((root / ".claude/state/gate/last-report.json").read_text())
    return [f for f in report["findings"] if f["rule"] == rule and f["severity"] == severity]


def blocked(root: Path, layer: str = "stop") -> bool:
    return gate(root, layer).returncode == 2 and bool(found(root, "delete/untested"))


def passed(root: Path, layer: str = "stop") -> bool:
    done = gate(root, layer)
    return done.returncode == 0 and not found(root, "delete/untested")


def cut(root: Path, rel: str, start: str, end: str | None = None) -> None:
    """Remove from the line that starts with `start` up to (not including) the one that starts with `end`."""
    lines = (root / rel).read_text().splitlines(keepends=True)
    first = next(i for i, line in enumerate(lines) if line.startswith(start))
    last = next((i for i, line in enumerate(lines) if i > first and end and line.startswith(end)), len(lines))
    (root / rel).write_text("".join(lines[:first] + lines[last:]))


def seal(root: Path, text: str, honest: bool = True) -> None:
    (root / ".engine/slices").mkdir(parents=True, exist_ok=True)
    (root / ".engine/slices/ctr.md").write_text(text)
    (root / ".claude/state/contracts").mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((text if honest else text + "x").encode()).hexdigest()
    (root / ".claude/state/contracts/ctr.sha256").write_text(f"{digest}  .engine/slices/ctr.md\n")


# ---------------------------------------------------------------- a function no test touched
print("a function no test touched is deleted")
r = project()
cut(r, "legacy.py", "def export_csv", "class Report")
done = gate(r)
hit = found(r, "delete/untested")
check("turn end: block, and the finding names the function and its file", done.returncode == 2 and len(hit) == 1
      and hit[0]["file"] == "legacy.py" and "function export_csv" in hit[0]["message"], (done.stderr, hit))
check("the reason shows the three ways through", all(w in done.stderr for w in ("DELETE GUARD", "a test that pins", "simplifier finding", "gate-allow: delete")), done.stderr)
done = gate(r, "stop", "--hook", stdin={"session_id": "s1"})
answer = json.loads(done.stdout or "{}")
check("hook protocol: decision block, the reason names the guard", answer.get("decision") == "block" and "DELETE GUARD legacy.py" in answer.get("reason", ""), done.stdout)
sh(r, "git", "add", "-A")
check("before a commit: the staged deletion blocks too", blocked(r, "pre_commit"))
sh(r, "git", "checkout", "-q", "HEAD", "--", "legacy.py")
sh(r, "git", "reset", "-q")
check("the deletion taken back: the turn ends", passed(r))

print("the same with a test")
r = project()
cut(r, "pay.py", "def charge")
check("the module has its test file (tests/test_pay.py): passes", passed(r), found(r, "delete/untested"))
check("... and the report says why", any("tests/test_pay.py" in f["message"] for f in found(r, "delete/passed", "log")))
r = project()
cut(r, "util.py", "def unused")
check("no test file for the module, no test mentions the name: block", blocked(r))
r = project()
cut(r, "util.py", "def slugify", "def unused")
check("no test file for the module, a test mentions the name: passes", passed(r), found(r, "delete/untested"))
r = project()
(r / "tests/test_export.py").write_text("from legacy import export_csv\n\n\ndef test_export():\n    assert export_csv([['a', 'b']]) == ['a,b']\n")
cut(r, "legacy.py", "def export_csv", "class Report")
check("a test written in the same change, not committed yet, counts", passed(r), found(r, "delete/untested"))
r = project()
(r / "tests/test_pay.py").unlink()
cut(r, "pay.py", "def charge")
check("the test file deleted together with the code: there WAS a test, passes", passed(r), found(r, "delete/untested"))

print("moved within the same change is not a deletion")
r = project()
cut(r, "legacy.py", "def export_csv", "class Report")
check("(block first: the function is just gone)", blocked(r))
(r / "exports.py").write_text("def export_csv(rows):\n    out = []\n    for row in rows:\n        out.append(','.join(row))\n    return out\n")
check("the function appears in a new file of the same change: passes", passed(r), found(r, "delete/untested"))
sh(r, "git", "add", "-A")
check("... and before a commit", passed(r, "pre_commit"), found(r, "delete/untested"))
r = project()
sh(r, "git", "mv", "legacy.py", "old_code.py")
check("the file renamed: passes", passed(r) and passed(r, "pre_commit"), found(r, "delete/untested"))
r = project()
text = (r / "legacy.py").read_text().replace("class Report:\n    def render(self):\n        return 'report'\n\n", "class Report:\n")
(r / "legacy.py").write_text(text + "\n\ndef render(report):\n    return 'report'\n")
check("a method turned into a function of the same name: passes", passed(r), found(r, "delete/untested"))

print("a class, a file")
r = project()
cut(r, "legacy.py", "class Report", "def big")
hit = found(r, "delete/untested") if gate(r).returncode == 2 else []
check("a class deleted: block, reported once (not once per method)", len(hit) == 1 and "class Report" in hit[0]["message"]
      and "render" not in hit[0]["message"], hit)
r = project()
(r / "legacy.py").unlink()
done = gate(r)
hit = found(r, "delete/untested")
check("a file deleted, and nothing else changed in the turn: block", done.returncode == 2 and len(hit) == 1
      and all(w in hit[0]["message"] for w in ("export_csv", "class Report", "function big")), (done.stderr, hit))
sh(r, "git", "add", "-A")
check("... and before a commit", blocked(r, "pre_commit"))
r = project()
(r / "pay.py").unlink()
check("a file with its test file deleted: passes", passed(r), found(r, "delete/untested"))
r = project()
(r / "tests/test_pay.py").unlink()
(r / "tests/helpers.py").write_text("def helper():\n    return 1\n")
commit(r, "helper")
(r / "tests/helpers.py").unlink()
check("test code is not working code: deleting a test helper is not this guard's business", gate(r).returncode == 0 and not found(r, "delete/untested"))

print("lines inside one function, against DELETE_GUARD_LINES")
r = project()
lines = (r / "legacy.py").read_text().splitlines(keepends=True)
start = next(i for i, line in enumerate(lines) if line.startswith("def big")) + 2
(r / "legacy.py").write_text("".join(lines[:start] + lines[start + 21:]))
done = gate(r)
hit = found(r, "delete/untested")
check("21 lines removed inside big(), threshold 20: block", done.returncode == 2 and len(hit) == 1 and "21 lines inside big()" in hit[0]["message"], hit)
(r / "legacy.py").write_text("".join(lines[:start] + lines[start + 20:]))
check("20 lines removed: passes", passed(r), found(r, "delete/untested"))
(r / "legacy.py").write_text("".join(lines[:start] + lines[start + 25:]))
check("(25 lines removed: block)", blocked(r))
(r / "parts.py").write_text("def part(n):\n    total = 0\n" + "".join(lines[start:start + 25]) + "    return total\n")
check("the 25 lines moved out into a function of another file: passes", passed(r), found(r, "delete/untested"))
r = project()
(r / "deploy.sh").write_text("".join(f"echo step {i}\n" for i in range(5)))
hit = found(r, "delete/untested") if gate(r).returncode == 2 else []
check("not Python: 25 lines removed from a script with no test — block by the count of lines", len(hit) == 1 and "25 lines" in hit[0]["message"], hit)
# Board 086: the whole-file path for code with no names to go by was run by no suite.
r = project()
(r / "deploy.sh").unlink()
done = gate(r)
hit = found(r, "delete/untested")
check("not Python: the whole script deleted — block, named as the file", done.returncode == 2 and len(hit) == 1 and hit[0]["file"] == "deploy.sh"
      and "the file" in hit[0]["message"], (done.stderr, hit))
r = project()
(r / "hook.sh").write_text("echo one\necho two\n")
(r / "limits.py").write_text("MAX_RETRIES = 3\nTIMEOUT_S = 30\n")
commit(r, "two small files")
(r / "hook.sh").unlink()
hit = found(r, "delete/untested") if gate(r).returncode == 2 else []
check("a script of two lines deleted whole: block — the threshold counts lines inside a file, not a file", len(hit) == 1 and hit[0]["file"] == "hook.sh", hit)
sh(r, "git", "checkout", "-q", "--", "hook.sh")
(r / "limits.py").unlink()
hit = found(r, "delete/untested") if gate(r).returncode == 2 else []
check("a Python file with no function or class (constants) deleted: block, as the file", len(hit) == 1 and hit[0]["file"] == "limits.py"
      and "the file" in hit[0]["message"], hit)
sh(r, "git", "checkout", "-q", "--", "limits.py")
check("(both restored: passes)", passed(r), found(r, "delete/untested"))
check("threshold(): unset, empty and garbage are the default; a number is itself",
      [delete_guard.threshold(e) for e in ({}, {"DELETE_GUARD_LINES": ""}, {"DELETE_GUARD_LINES": "many"}, {"DELETE_GUARD_LINES": "5"})] == [20, 20, 20, 5])

print("DELETE_GUARD_LINES is the gate's own key")
r = project()
(r / ".claude/project.env").write_text(ENV + 'DELETE_GUARD_LINES="500"\n# gate-allow: the functions here are long anyway\n')
done = gate(r)
check("raised by the work being judged, with a reason of its own beside it: block", done.returncode == 2
      and any("DELETE_GUARD_LINES" in f["message"] for f in found(r, "bypass/config")), done.stderr)
sh(r, "git", "add", "-A")
check("... and before a commit", gate(r, "pre_commit").returncode == 2 and bool(found(r, "bypass/config")))
seal(r, "# Slice\n\ngate-allow: .claude/project.env — the whole file is ours to tune\n")
check("a grant of the whole file is not enough: block", gate(r).returncode == 2 and bool(found(r, "bypass/config")))
seal(r, "# Slice\n\ngate-allow: DELETE_GUARD_LINES — the owner calibrated it on history\n", honest=False)
check("the key named in a contract edited after its seal: block", gate(r).returncode == 2 and bool(found(r, "bypass/config")))
seal(r, "# Slice\n\ngate-allow: DELETE_GUARD_LINES — the owner calibrated it on history\n")
check("the sealed contract names the key: passes", gate(r).returncode == 0 and not found(r, "bypass/config"), found(r, "bypass/config"))
r = project()
(r / ".claude/project.env").write_text(ENV + 'DELETE_GUARD_LINES="20"\n')
check("writing the default down is not a change", gate(r).returncode == 0 and not found(r, "bypass/config"), found(r, "bypass/config"))
r = project(ENV + 'DELETE_GUARD_LINES="30"\n')
start = next(i for i, line in enumerate(lines) if line.startswith("def big")) + 2
(r / "legacy.py").write_text("".join(lines[:start] + lines[start + 25:]))
check("the project's own threshold is the one used: 25 lines under 30 pass", passed(r), found(r, "delete/untested"))
r = project()
(r / ".claude/project.env").write_text(ENV + 'COVERAGE_CMD="true"\n')
check("COVERAGE_CMD changed with no reason beside it: block", gate(r).returncode == 2 and any("COVERAGE_CMD" in f["message"] for f in found(r, "bypass/config")))

print("the owner's grant in the sealed contract")
r = project()
cut(r, "legacy.py", "def export_csv", "class Report")
seal(r, "# Slice\n\ngate-allow: delete — the export moved to the reporting service\n", honest=False)
check("a contract that is not sealed grants nothing: block", blocked(r))
seal(r, "# Slice\n\ngate-allow: delete — the export moved to the reporting service\n")
check("sealed `gate-allow: delete — <reason>`: passes", passed(r), found(r, "delete/untested"))
seal(r, "# Slice\n\ngate-allow: pay.py — another file altogether, not this one\n")
check("a grant of another file: block", blocked(r))
seal(r, "# Slice\n\ngate-allow: legacy.py — the export moved to the reporting service\n")
check("a grant of this file: passes", passed(r), found(r, "delete/untested"))

print("a simplifier finding the owner confirmed")
r = project()
FINDING = {"target": "legacy.py::export_csv", "category": "dead_code", "claim": "export_csv is called from nowhere",
           "evidence": [{"source": "signal", "ref": "S-0a1b2c3d", "detail": "vulture: unused function"}],
           "protected": False, "chesterton_checked": True, "test_safety": "none", "proposed_action": "confirm",
           "traceability": "nothing asks for a CSV export", "reversal_risk": "low"}
OPINION = FINDING | {"claim": "export_csv looks unused", "evidence": [{"source": "judgement", "detail": "looks unused"}]}
(r / "request.txt").write_text("signals: S-0a1b2c3d vulture unused function legacy.py:4\n")
(r / "answer.json").write_text(json.dumps([FINDING, OPINION]))
valid = json.loads(run(HOOKS / "simplifier.py", r, "validate", "answer.json", "--request", "request.txt", session=True).stdout)
ident, opinion = (f["id"] for f in valid["findings"])
commit(r, "the simplifier's answer")
cut(r, "legacy.py", "def export_csv", "class Report")
check("(block first: the finding exists, nobody confirmed it)", blocked(r))
done = run(GUARD, r, "confirm", "answer.json", ident, "--request", "request.txt", session=True)
check("the agent confirms in its own session: refused, nothing written, still a block", done.returncode == 2
      and "refused" in done.stderr and not (r / ".claude/state/delete-guard/confirmed.json").exists() and blocked(r), done.stderr)
done = run(GUARD, r, "confirm", "answer.json", opinion, "--request", "request.txt", session=False)
check("the owner confirms a finding with a judgement and no tool evidence: refused, still a block", done.returncode == 1
      and "no evidence from a tool" in done.stderr and blocked(r), done.stderr)
(r / ".engine/simplifier").mkdir(parents=True, exist_ok=True)
(r / ".engine/simplifier/decisions.jsonl").write_text(json.dumps({"finding": ident, "decision": "yes"}) + "\n")
check("a «так» the agent wrote into the simplifier's decisions is not the owner's: block", blocked(r))
done = run(GUARD, r, "confirm", "answer.json", ident, "--request", "request.txt", session=False)
check("the owner confirms it in their own terminal", done.returncode == 0 and "export_csv" in done.stdout, done.stderr)
check("... and the deletion passes", passed(r), found(r, "delete/untested"))
check("... with the finding named in the report", any(ident in f["message"] for f in found(r, "delete/passed", "log")))
cut(r, "legacy.py", "class Report", "def big")
hit = found(r, "delete/untested") if gate(r).returncode == 2 else []
check("the confirmation covers what the finding named and nothing else: the class next to it blocks",
      len(hit) == 1 and "class Report" in hit[0]["message"] and "export_csv" not in hit[0]["message"], hit)
(r / "answer.json").write_text(json.dumps([FINDING | {"target": "legacy.py", "claim": "nothing imports the module"}]))
whole = json.loads(run(HOOKS / "simplifier.py", r, "validate", "answer.json", "--request", "request.txt", session=True).stdout)["findings"][0]["id"]
done = run(GUARD, r, "confirm", "answer.json", whole, "--request", "request.txt", session=False)
check("a confirmed finding about the whole file covers the class too", done.returncode == 0 and "the whole file" in done.stdout and passed(r), done.stderr)
cut(r, "util.py", "def unused")
hit = found(r, "delete/untested") if gate(r).returncode == 2 else []
check("... and no other file: a function deleted elsewhere blocks", len(hit) == 1 and hit[0]["file"] == "util.py", hit)
shown = run(GUARD, r, "show", session=True)
check("show: the threshold, the mode, the confirmed finding", shown.returncode == 0 and "20 line" in shown.stdout
      and "coarse" in shown.stdout and ident in shown.stdout, shown.stdout + shown.stderr)

print("with COVERAGE_CMD the answer is exact")
# The project's coverage command: refuses to run on code where export_csv is already gone, says
# that export_csv's lines ran when a test names it, and that Report's lines never ran.
COVERAGE = ('#!/usr/bin/env bash\ngrep -q "def export_csv" legacy.py || exit 3\n'
            'ran=""\ngrep -rqs "export_csv" tests/ && ran="5, 6, 7, 8"\n'
            'printf \'{"files": {"legacy.py": {"executed_lines": [1, 4, 11, 12, 15, %s], "missing_lines": [13, 16]}}}\' "${ran:-1}" > coverage.json\n')
COVERED_ENV = ENV + 'COVERAGE_CMD="bash checks/coverage.sh"\n'


def covered_project() -> Path:
    root = project(COVERED_ENV)
    (root / "checks").mkdir()
    (root / "checks/coverage.sh").write_text(COVERAGE)
    (root / "tests/test_legacy.py").write_text("import legacy\n\n\ndef test_import():\n    assert legacy\n")
    commit(root, "coverage")
    return root


r = covered_project()
cut(r, "legacy.py", "def export_csv", "class Report")
done = gate(r)
hit = found(r, "delete/untested")
check("the module has a test file, but no test executed the function: block (the coarse check would pass it)",
      done.returncode == 2 and len(hit) == 1 and "no test executed it" in hit[0]["message"], (done.stderr, hit))
check("the command ran on the code BEFORE the change (it refuses the code after it)", not found(r, "delete/coverage-unavailable", "warn"))
(r / "tests/test_export.py").write_text("from legacy import export_csv\n\n\ndef test_export():\n    assert export_csv([['a']]) == ['a']\n")
check("a test of the change, laid over the old code, executes the function: passes", passed(r), found(r, "delete/untested"))
r = covered_project()
(r / "tests/test_export.py").write_text("from legacy import export_csv\n\n\ndef test_export():\n    assert export_csv([['a']]) == ['a']\n")
commit(r, "the test of export_csv")
cut(r, "legacy.py", "def export_csv", "class Report")
(r / "tests/test_export.py").write_text("def test_nothing():\n    assert True\n")
check("the function and, in the same change, its test edited away: there WAS a test, passes", passed(r), found(r, "delete/untested"))
r = covered_project()
cut(r, "legacy.py", "class Report", "def big")
check("a class whose def lines ran at import and whose methods never ran: block", blocked(r))
r = covered_project()
(r / "checks/coverage.sh").write_text("#!/usr/bin/env bash\nexit 1\n")
commit(r, "a coverage command that leaves no report")
cut(r, "legacy.py", "def export_csv", "class Report")
done = gate(r)
check("no readable coverage.json: a warning, and the coarser check decides (here: the module has a test file)",
      done.returncode == 0 and bool(found(r, "delete/coverage-unavailable", "warn")), done.stderr)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
