#!/usr/bin/env python3
"""Every outside tool whose answer decides a check runs at a version written in one place (board 107).

On 2026-10-09 ruff 0.17.0 came out and `uvx ruff`, which took the latest release, turned the
engine's lint red on the server with no change to the code. .claude/hooks/tool_versions.py now
holds the versions; this suite shows that

  - each version is exact (no range, no «latest»);
  - no call in the engine's code runs one of those tools through uvx without its version, and the
    places that call them take the version from the module;
  - the lookup is what the module says: a tool on PATH of the pinned version, else
    `uvx <tool>@<version>`, else None with a reason that names both versions — never a silent
    run with another release; a project's own tool (its virtual environment) is its own choice;
  - a signal of the simplifier with only another version at hand is `unavailable`, with the reason.

Every PATH here is built from nothing: stand-ins that answer `--version` and record their argv.

Run:   python3 tests/test_tool_versions.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / ".claude/hooks/tool_versions.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:600]}")


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tv = load("tool_versions", MODULE)
TOOLS = sorted(tv.VERSIONS)

print("— the versions are exact, in one place")
check("every pinned version is a plain release number", all(re.fullmatch(r"\d+(\.\d+)+", v) for v in tv.VERSIONS.values()), tv.VERSIONS)
check("ruff is 0.17.0, the release the engine's code is clean with", tv.VERSIONS["ruff"] == "0.17.0")
check("the tools of the engine's checks are all there", {"ruff", "mypy", "vulture", "pylint", "pytest", "hypothesis", "coverage"} <= set(TOOLS), TOOLS)

# A call that names one of the tools through uvx with no version: `"uvx", "ruff"`, `uvx --quiet mypy `,
# `"--with", "pytest"`, `--from coverage`. The pattern is built, so that this file does not match itself.
names = "|".join(TOOLS)
SEP = r'(?:"\s*,\s*"|\'\s*,\s*\'|\s+)'
UNPINNED = re.compile(rf'(?:uvx{SEP}(?:--quiet{SEP})?|--with{SEP}|--from{SEP})["\']?({names})(?![\w@=.-])')
code = [p for pattern in (".claude/**/*.py", ".claude/**/*.sh", "evals/*.py", "tests/*.py", "engine.py")
        for p in ROOT.glob(pattern) if "__pycache__" not in p.parts and p.name != Path(__file__).name]
found = [f"{p.relative_to(ROOT)}:{n}: {line.strip()}" for p in code
         for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if UNPINNED.search(line)]
check(f"no call of a pinned tool through uvx without its version ({len(code)} files read)", not found, "\n".join(found))
check("…and the reader would see one: an unpinned call is caught",
      bool(UNPINNED.search('["uvx", ' + '"ruff", "check"]')) and bool(UNPINNED.search("exec uvx --quiet " + "ruff \"$@\""))
      and bool(UNPINNED.search('"--with", ' + '"pytest", "pytest"')) and not UNPINNED.search('["uvx", "ruff@0.17.0"]')
      and not UNPINNED.search('"--with", "pytest==9.1.1"'))
callers = [".claude/hooks/gate.py", ".claude/hooks/simplify_signals.py", "tests/test_engine_lint.py",
           "evals/run_tester_evals.py", "evals/hook_coverage.py", "tests/test_simplifier_evals.py", "tests/test_format_on_edit.py"]
takes = ("tool_versions", "tool_pins")       # the module itself, or the suites' loader of it
check("the places that run the tools take the versions from the module",
      all(any(word in (ROOT / c).read_text(encoding="utf-8") for word in takes) for c in callers),
      [c for c in callers if not any(word in (ROOT / c).read_text(encoding="utf-8") for word in takes)])


def stand_in(d: Path, name: str, version: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(f'#!/usr/bin/env bash\n[ "$1" = --version ] && {{ echo "{name} {version}"; exit 0; }}\n'
                 f'echo "{d.name}:{name} $*" >> "{d.parent}/calls.log"\nexit 0\n')
    p.chmod(0o755)
    return p


def lookup(path: str, tool: str = "ruff") -> tuple[int, str]:
    """The module's own command line, with PATH exactly `path` (bash and env from /usr/bin and /bin)."""
    r = subprocess.run([sys.executable, str(MODULE), tool], capture_output=True, text=True, check=False,
                       env=hook_env(work, PATH=f"{path}:/usr/bin:/bin"))
    return r.returncode, r.stdout.strip() + r.stderr.strip()


print("— how a tool is found")
system_has = [t for t in ("uvx", "ruff", "mypy") if any((Path(d) / t).exists() for d in ("/usr/bin", "/bin"))]
check("(the system directories hold no uvx, ruff or mypy of their own)", not system_has, system_has)
work = Path(tempfile.mkdtemp(prefix="tool-versions-"))
right, wrong, fetch, own = work / "right", work / "wrong", work / "fetch", work / "own"
stand_in(right, "ruff", tv.VERSIONS["ruff"])
stand_in(wrong, "ruff", "0.16.8")
stand_in(fetch, "uvx", "0.11.0")
pinned = f"uvx --quiet ruff@{tv.VERSIONS['ruff']}"
rc, out = lookup(str(right))
check("a ruff on PATH of the pinned version is used as it is (no fetch)", rc == 0 and out.endswith(f"{right}/ruff"), out)
rc, out = lookup(f"{wrong}:{fetch}")
check("another version on PATH and uvx at hand: uvx with the pinned release", rc == 0 and pinned in out, out)
rc, out = lookup(str(fetch))
check("no ruff, uvx at hand: the same", rc == 0 and pinned in out, out)
rc, out = lookup(str(wrong))
check("another version on PATH and no uvx: it cannot run, and the reason names both versions",
      rc == 1 and "cannot run" in out and "0.16.8" in out and tv.VERSIONS["ruff"] in out, out)
rc, out = lookup(str(work / "nothing"))
check("neither: it cannot run, and says so", rc == 1 and "neither uvx nor ruff" in out, out)
rc, out = lookup(str(work / "nothing"), "hypothesis")
check("a library is named with the spelling it is brought with", rc == 0 and f"--with hypothesis=={tv.VERSIONS['hypothesis']}" in out, out)

project = work / "project"
venv_ruff = stand_in(project / ".venv" / "bin", "ruff", "9.9.9")
check("a project's own ruff in .venv/ is found (its version is the project's choice)", tv.project_tool(project, "ruff") == str(venv_ruff))
check("…and none is found where the project has none", tv.project_tool(work / "right", "mypy") is None)
saved = os.environ.get("VIRTUAL_ENV")
os.environ["VIRTUAL_ENV"] = str(own)
own_mypy = stand_in(own / "bin", "mypy", "1.0.0")
try:
    check("the activated virtual environment is the project's too", tv.project_tool(work / "right", "mypy") == str(own_mypy))
finally:
    if saved is None:
        os.environ.pop("VIRTUAL_ENV", None)
    else:
        os.environ["VIRTUAL_ENV"] = saved

print("— the simplifier's signals with only another version at hand")
sys.path.insert(0, str(ROOT / ".claude/hooks"))
signals = load("simplify_signals", ROOT / ".claude/hooks/simplify_signals.py")
old_vulture = stand_in(work / "old", "vulture", "2.10")
saved_path = os.environ["PATH"]
os.environ["PATH"] = f"{old_vulture.parent}:/usr/bin:/bin"
try:
    out, why = signals.run_tool(work, "vulture", "x.py")
    dead = signals.dead_code_signals(work, ["x.py"], [], None)
finally:
    os.environ["PATH"] = saved_path
check("vulture 2.10 and no uvx: the tool does not run", out is None and "2.10" in why and tv.VERSIONS["vulture"] in why, why)
check("…and the signal is `unavailable` with that reason, never a clean result",
      [s["kind"] for s in dead] == ["unavailable"] and "2.10" in dead[0]["message"], json.dumps(dead))
check("…and the old vulture was never asked to judge", not (work / "calls.log").exists() or "old:vulture" not in (work / "calls.log").read_text())

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
