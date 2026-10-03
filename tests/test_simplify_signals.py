#!/usr/bin/env python3
"""simplify_signals.py: what each scope measures, what it must not report, the history, the gate.

Every case is a real temporary git repository. vulture and pylint run through `uvx`, as in the
project; one case hides them to show that a tool that cannot run is reported, not read as clean.

Run:   python3 tests/test_simplify_signals.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / ".claude" / "hooks" / "simplify_signals.py"
GATE = ROOT / ".claude" / "hooks" / "gate.py"
PASS = FAIL = 0


def branchy(name: str, branches: int) -> str:
    return f"def {name}(a: int) -> int:\n" + "".join(
        f"    if a == {i}:\n        return {i}\n" for i in range(branches)) + "    return 0\n"


BASE = {
    "src/demo/pricing.py": '"""Prices."""\n\n\ndef total(prices: list[int]) -> int:\n    return sum(prices)\n\n\n' + branchy("legacy", 11),
    "src/demo/use.py": "from demo.pricing import legacy, total\n\nprint(total([legacy(1)]))\n",
    "src/demo/old.py": "def forgotten() -> int:\n    return 1\n",
    "tests/test_pricing.py": "from demo.pricing import total\n\n\ndef test_total() -> None:\n    assert total([1]) == 1\n\n\ndef helper_nobody_calls() -> None:\n    pass\n",
    "pyproject.toml": '[project]\nname = "demo"\nversion = "0"\ndependencies = ["requests>=2"]\n',
    ".claude/project.env": 'SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\nLINT_CMD="true"\nCOMPLEXITY_GATE="warn"\n',
    ".gitignore": ".claude/state/\n",
}


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def write(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")


def new_repo(files: dict[str, str] = BASE) -> Path:
    repo = Path(tempfile.mkdtemp(prefix="signals-"))
    for rel, text in files.items():
        write(repo, rel, text)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return repo


def signals(repo: Path, *args: str, path: str | None = None) -> list[dict[str, Any]]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}
    if path is not None:
        env["PATH"] = path
    proc = subprocess.run([sys.executable, str(SIGNALS), *args, "--json"], cwd=repo, env=env,
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    found: list[dict[str, Any]] = json.loads(proc.stdout)
    return found


def kinds(found: list[dict[str, Any]]) -> list[str]:
    return sorted(s["kind"] for s in found)


print("STOP-*   only what the change adds or makes worse, in the changed files")
repo = new_repo()
check("a clean tree gives no signal", signals(repo, "--scope", "stop") == [])
write(repo, "src/demo/pricing.py", BASE["src/demo/pricing.py"] + "\n\n" + branchy("route", 12))
write(repo, "src/demo/use.py", BASE["src/demo/use.py"].replace("legacy, total", "legacy, route, total") + "print(route(1))\n")
found = signals(repo, "--scope", "stop")
hit = [s for s in found if s["kind"] == "complexity"]
check("a new function above the limit is a signal with its file and line",
      len(hit) == 1 and hit[0]["file"] == "src/demo/pricing.py" and hit[0]["line"] == 34 and "route: complexity 13" in hit[0]["message"], found)
check("the old function above the limit in the same file is not this change's signal", "legacy" not in json.dumps(found), found)
check("every signal has an id", all(s["id"].startswith("S-") and len(s["id"]) == 10 for s in found), found)
check("the signals are written to machine state",
      json.loads((repo / ".claude/state/simplifier/signals-stop.json").read_text())["signals"] == found)

repo = new_repo()
write(repo, "src/demo/pricing.py", BASE["src/demo/pricing.py"].removesuffix("    return 0\n") + "    if a == 99:\n        return 99\n    return 0\n")
found = signals(repo, "--scope", "stop")
check("an old function made worse is a signal, with the value at HEAD",
      kinds(found) == ["complexity"] and "legacy: complexity 13" in found[0]["message"] and "was 12 at HEAD" in found[0]["message"], found)

repo = new_repo()
write(repo, "pyproject.toml", BASE["pyproject.toml"].replace('"requests>=2"', '"requests>=2", "Left-Pad>=1"'))
found = signals(repo, "--scope", "stop")
check("a dependency the change adds is a signal, the old one is not",
      kinds(found) == ["new-dependency"] and "left-pad" in found[0]["message"], found)

repo = new_repo()
write(repo, "src/demo/pricing.py", BASE["src/demo/pricing.py"] + "\n\ndef nobody_calls_me() -> int:\n    return 1\n")
found = signals(repo, "--scope", "stop")
check("dead code in a changed module is a signal",
      kinds(found) == ["dead-code"] and "nobody_calls_me" in found[0]["message"] and found[0]["line"] == 34, found)
check("dead code in a module the turn did not touch is not reported at stop", "forgotten" not in json.dumps(found), found)
check("a function another file uses is not dead", "total" not in json.dumps(found) and "legacy" not in json.dumps(found), found)
write(repo, "tests/test_pricing.py", BASE["tests/test_pricing.py"] + "\n\n" + branchy("test_huge", 15))
check("a test file is never measured", "test_huge" not in json.dumps(signals(repo, "--scope", "stop")))
write(repo, "src/demo/test_inline.py", branchy("test_beside_the_code", 15))
check("...also when it lives beside the code", "test_beside_the_code" not in json.dumps(signals(repo, "--scope", "stop")))
write(repo, "src/demo/fixtures/sample.py", branchy("planted_on_purpose", 15))
write(repo, ".claude/project.env", BASE[".claude/project.env"] + 'SIMPLIFY_EXCLUDE="src/demo/fixtures"\n')
check("a path in SIMPLIFY_EXCLUDE is never measured", "planted_on_purpose" not in json.dumps(signals(repo, "--scope", "stop")))
write(repo, ".claude/project.env", BASE[".claude/project.env"])
check("...and is measured without the exclusion", "planted_on_purpose" in json.dumps(signals(repo, "--scope", "stop")))
write(repo, "scripts/tool.py", branchy("outside", 15))
check("a file outside SOURCE_DIRS is never measured", "outside" not in json.dumps(signals(repo, "--scope", "stop")))

print("FULL-*   the whole repository: dead code, unused dependencies, duplication, every function above the limit")
SHARED = "\n".join(f"    step_{i} = prices[{i}] * {i + 2} + len(prices)" for i in range(12)) + "\n"
repo = new_repo(BASE | {
    "src/demo/a.py": "def first(prices: list[int]) -> int:\n" + SHARED + "    return step_1\n",
    "src/demo/b.py": "import os\n\n\ndef second(prices: list[int]) -> int:\n" + SHARED + "    return step_2 + len(os.sep)\n",
})
found = signals(repo, "--scope", "full")
by_kind = {k: [s for s in found if s["kind"] == k] for k in kinds(found)}
check("dead code anywhere is reported", any("forgotten" in s["message"] for s in by_kind.get("dead-code", [])), found)
check("an unused runtime dependency is reported at its line in pyproject.toml",
      [(s["file"], s["line"]) for s in by_kind.get("unused-dependency", [])] == [("pyproject.toml", 4)]
      and "requests" in by_kind["unused-dependency"][0]["message"], found)
check("duplication names both places",
      len(by_kind.get("duplication", [])) == 1 and "src/demo/a.py:" in by_kind["duplication"][0]["message"]
      and "src/demo/b.py:" in by_kind["duplication"][0]["message"], found)
check("every function above the limit is reported, old ones included",
      any("legacy: complexity 12" in s["message"] for s in by_kind.get("complexity", [])), found)
check("the test file's unused helper is not reported", "helper_nobody_calls" not in json.dumps(found), found)
write(repo, "src/demo/use.py", BASE["src/demo/use.py"] + "import requests\n\nprint(requests)\n")
check("an imported dependency is not unused", "unused-dependency" not in kinds(signals(repo, "--scope", "full")))
found = signals(repo, "--scope", "full", "--paths", "src/demo/old.py")
check("--paths narrows what is measured", {s["file"] for s in found if s["kind"] == "dead-code"} == {"src/demo/old.py"}, found)

print("TREND-*  growth against the project's own history calls the simplifier")
repo = new_repo()
history = repo / ".claude/state/simplifier/metrics.jsonl"
for _ in range(3):
    found = signals(repo, "--scope", "full", "--record")
check("three recorded runs, three lines of history", len(history.read_text().splitlines()) == 3)
check("no growth, no trend signal", "trend" not in kinds(found), found)
check("a run without --record leaves the history alone",
      signals(repo, "--scope", "full") is not None and len(history.read_text().splitlines()) == 3)
for i in range(4):
    write(repo, f"src/demo/dead{i}.py", f"def orphan_{i}() -> int:\n    return {i}\n")
found = signals(repo, "--scope", "full", "--record")
trend = [s["message"] for s in found if s["kind"] == "trend"]
check("dead code going from 1 to 5 is a trend signal", any(m.startswith("dead-code grew from 1 ") and m.endswith("to 5") for m in trend), found)
check("a small absolute change is not (files 3 -> 7 is; lines under the floor are not)",
      not any(m.startswith("lines ") for m in trend), trend)
proc = subprocess.run([sys.executable, str(SIGNALS), "--scope", "full"], cwd=repo, capture_output=True, text=True,
                      env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}, check=False)
check("the plain output says the simplifier is called", "SIMPLIFIER CALL (sharp growth)" in proc.stdout, proc.stdout[-300:])

print("TOOLS-*  a tool that cannot run is reported, never read as clean")
shim = Path(tempfile.mkdtemp(prefix="signals-path-"))
for tool in ("git", "python3"):
    target = shutil.which(tool)
    assert target
    (shim / tool).symlink_to(target)
repo = new_repo()
found = signals(repo, "--scope", "full", path=str(shim))
check("without uvx, vulture and pylint: two `unavailable` signals and no dead-code claim",
      [s["tool"] for s in found if s["kind"] == "unavailable"] == ["vulture", "pylint"] and "dead-code" not in kinds(found), found)

print("GATE-*   gate.py shows the signals and never blocks on them")


def gate(repo: Path, layer: str) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run([sys.executable, str(GATE), "--layer", layer], cwd=repo, capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}, check=False)
    report: dict[str, Any] = json.loads((repo / ".claude/state/gate/last-report.json").read_text())
    return proc.returncode, report


repo = new_repo()
write(repo, "src/demo/pricing.py", BASE["src/demo/pricing.py"] + "\n\n" + branchy("route", 12))
code, report = gate(repo, "stop")
rules = {f["rule"]: f["severity"] for f in report["findings"]}
check("stop: the signal is a `warn` finding and the gate passes",
      code == 0 and rules.get("simplify/complexity") == "warn" and report["result"] == "pass", report)
check("stop: the step is timed", "simplify_signals" in report["timings_ms"]["steps"], report["timings_ms"])
code, report = gate(repo, "ci")
check("ci: the whole repository is measured (the old dead code shows) and the gate passes",
      code == 0 and any(f["rule"] == "simplify/dead-code" and f["file"] == "src/demo/old.py" for f in report["findings"]), report)
check("ci: the run is recorded in the history", len((repo / ".claude/state/simplifier/metrics.jsonl").read_text().splitlines()) == 1)
write(repo, ".claude/project.env", BASE[".claude/project.env"].replace('"warn"', '"off"') + "# gate-allow: the switch is not a gate key\n")
code, report = gate(repo, "stop")
check("COMPLEXITY_GATE off: no signal, no step — the gate is exactly what it was",
      code == 0 and not any(f["rule"].startswith("simplify/") for f in report["findings"])
      and "simplify_signals" not in report["timings_ms"]["steps"], report)

for leftover in Path(tempfile.gettempdir()).glob("signals-*"):
    shutil.rmtree(leftover, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
