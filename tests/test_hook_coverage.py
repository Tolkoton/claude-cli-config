#!/usr/bin/env python3
"""evals/hook_coverage.py: which lines and branches of the hooks no test and no scenario runs (board 086).

Offline: the reading of a shell script (which lines can run), the ranges, the shell traces.
With `uvx` at hand (coverage.py is fetched by it): a synthetic project with one shell and one
Python hook is run one way only — the other way is reported as missed, and a doctored copy of
the same hook, run from another directory, counts for nothing.

Run:   python3 tests/test_hook_coverage.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "evals" / "hook_coverage.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:700]}")


spec = importlib.util.spec_from_file_location("hook_coverage", SCRIPT)
assert spec and spec.loader
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)

print("the reading of a shell script")
SHELL = """#!/usr/bin/env bash
# a comment
set -u

say() {
  echo "$1"
}
PATTERNS=(
  'one'
  'two'
)
if [ "${1:-}" = "loud" ]; then
  say LOUD
else
  say quiet \\
    --and-more
fi
case "${2:-}" in
  a)
    say a ;;
  b|c) say bc ;;
esac
python3 - <<'PY'
print("not shell")
PY
TEXT="first
second line of a string"
exit 0
"""
lines, owner, first = hc.shell_lines(SHELL)
check("commands count; comments, keywords, a function header and a bare case pattern do not",
      {3, 6, 8, 12, 13, 15, 18, 20, 21, 23, 26, 28} == lines, sorted(lines))
check("a command of several lines is one line, its first: an array, a continued command, a quoted string",
      first == {9: 8, 10: 8, 11: 8, 16: 15, 27: 26}, first)
check("a heredoc body is not shell", not {24, 25} & lines, sorted(lines))
check("a line knows its function", owner[6] == "say" and owner[13] == "", owner)
check("ranges", hc.ranges([1, 2, 3, 7, 9, 10]) == "1-3, 7, 9-10" and hc.ranges([]) == "", hc.ranges([1, 2, 3, 7, 9, 10]))

print("a shell trace counts only for an identical file")
work = Path(tempfile.mkdtemp(prefix="hook-coverage-"))
data = work / "data"
(data / "sh").mkdir(parents=True)
(data / "sh" / "1.trace").write_text(
    "#CWD /somewhere\n#SHA aaa /copy/.claude/hooks/demo.sh\n#SHA bbb other/.claude/hooks/demo.sh\n"
    "+|/copy/.claude/hooks/demo.sh|3| set -u\n++|/copy/.claude/hooks/demo.sh|6| echo 'a\nline that is no trace|9| x'\n"
    "+|other/.claude/hooks/demo.sh|12| '[' x = y ']'\n", encoding="utf-8")
hits = hc.shell_hits([data], {"aaa": ".claude/hooks/demo.sh"})
check("the identical copy's lines are counted, the other copy's are not", dict(hits) == {".claude/hooks/demo.sh": {3, 6}}, dict(hits))

print("a run, end to end")
if not shutil.which("uvx"):
    print("  skip (uvx is not installed: coverage.py cannot be fetched)")
else:
    proj = work / "proj"
    hooks = proj / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "demo.sh").write_text(SHELL, encoding="utf-8")
    (hooks / "demo.py").write_text(
        "import sys\n\n\ndef kind(word):\n    if word == 'loud':\n        return 'LOUD'\n    return 'quiet'\n\n\n"
        "def unused():\n    return 1\n\n\nprint(kind(sys.argv[1]))\n", encoding="utf-8")
    doctored = work / "old" / ".claude" / "hooks"
    doctored.mkdir(parents=True)
    (doctored / "demo.py").write_text("import sys\n\n\n\n\n\n\n\n\n\n\n" + (hooks / "demo.py").read_text(encoding="utf-8"), encoding="utf-8")
    driver = work / "driver.sh"
    driver.write_text(f"bash {hooks}/demo.sh loud a\npython3 {hooks}/demo.py loud\npython3 {doctored}/demo.py quiet\n", encoding="utf-8")
    run = subprocess.run([sys.executable, str(SCRIPT), "run", "--data", str(work / "run1"), "--", "bash", str(driver)],
                         capture_output=True, text=True, check=False, env=hook_env(proj))
    check("the command runs as without tracing: same output, nothing on stderr",
          run.returncode == 0 and run.stdout.split() == ["LOUD", "a", "not", "shell", "LOUD", "quiet"] and run.stderr == "", run.stdout + run.stderr)
    out = work / "report.json"
    rep = subprocess.run([sys.executable, str(SCRIPT), "report", str(work / "run1"), "--root", str(proj), "--json", str(out), "--missing"],
                         capture_output=True, text=True, check=False)
    files = json.loads(out.read_text(encoding="utf-8"))["files"] if out.is_file() else {}
    sh_file, py_file = files.get(".claude/hooks/demo.sh", {}), files.get(".claude/hooks/demo.py", {})
    check("shell: the branch not taken is missed, the one taken is not",
          rep.returncode == 0 and sh_file.get("missing_lines") == [15, 21], (sh_file, rep.stderr))
    check("python: the line not run and the function never called are missed",
          py_file.get("missing_lines") == [7, 11] and py_file.get("owner", {}).get("11") == "unused", py_file)
    check("python: the branch never taken is named", [5, 7] in py_file.get("missing_branches", []) and py_file.get("branches_run") == 1, py_file)
    check("the doctored copy ran `quiet` (line 7 of the real file) and counts for nothing",
          7 in py_file.get("missing_lines", []) and "copies that differ" in rep.stdout, rep.stdout)
    check("the listing names the function", "unused: lines 11" in rep.stdout and "kind: lines 7" in rep.stdout, rep.stdout)
    again = subprocess.run([sys.executable, str(SCRIPT), "run", "--data", str(work / "run1"), "--", "true"], capture_output=True, text=True, check=False)
    check("a run refuses a directory that already holds one", again.returncode != 0 and "not empty" in again.stderr, again.stderr)
    subprocess.run([sys.executable, str(SCRIPT), "run", "--data", str(work / "run2"), "--", "bash", "-c",
                    f"bash {hooks}/demo.sh quiet b; python3 {hooks}/demo.py quiet"], capture_output=True, text=True, check=False, env=hook_env(proj))
    both = subprocess.run([sys.executable, str(SCRIPT), "report", str(work / "run1"), str(work / "run2"), "--root", str(proj), "--json", str(out)],
                          capture_output=True, text=True, check=False)
    files = json.loads(out.read_text(encoding="utf-8"))["files"]
    check("two runs add up: only the function never called is left",
          files[".claude/hooks/demo.py"]["missing_lines"] == [11] and files[".claude/hooks/demo.sh"]["missing_lines"] == [], (files, both.stderr))
r = subprocess.run([sys.executable, str(SCRIPT), "report", str(work)], capture_output=True, text=True, check=False)
check("a directory that holds no run is refused", r.returncode != 0 and "holds no run" in r.stderr, r.stderr)
check("the measured files of this repository are found", ".claude/hooks/gate.py" in hc.scope_files() and "engine.py" in hc.scope_files(), hc.scope_files())
shutil.rmtree(work, ignore_errors=True)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
