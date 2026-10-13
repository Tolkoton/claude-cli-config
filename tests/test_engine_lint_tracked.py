#!/usr/bin/env python3
"""The oldest supported Python compiles every Python file of the repository, not only the top-level ones (board 771).

Board 748's check printed «python3.11 compiles every Python file of the repository (140)» while 238 were tracked: it
globbed the engine's files under .claude/, engine.py, evals/*.py and tests/*.py, so a 3.12-only form in
evals/scenarios/tester-property/watch.py — which run_tester_evals.py appends into the scene modules — or in any other
file below the top level passed. This suite holds the set in place:

  - a throwaway git repository with this repository's Python (`git ls-files '*.py'` and .claude/ownership.txt), judged
    by its own tests/test_engine_lint.py;
  - `python<MIN_PYTHON>` there is a stand-in first on PATH: it records the arguments the lint hands it, then runs them
    under this interpreter with the grammar held at MIN_PYTHON (ast.parse's feature_version). So the scene is the same
    on a machine that has the oldest Python and on one that has not, and it refuses `type X = ...` and `def f[T]()`
    wherever they stand. (It does not refuse every newer form — not a quote reused inside an f-string: board 1725.)
  - as the code stands the lint is green there and the files it handed over are exactly the repository's: the tracked
    ones and the new ones git does not ignore; an ignored file that parses under no Python is left alone;
  - with a 3.12-only form in watch.py, in a scene module and in a new file not yet added, the lint is red and names
    all three; and where git cannot list the files it fails rather than judging none.

Run:   python3 tests/test_engine_lint_tracked.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import hook_env
from tool_pins import tool_versions

ROOT = Path(__file__).resolve().parent.parent
MIN_PYTHON: str = tool_versions.MIN_PYTHON
OLDEST = f"python{MIN_PYTHON}"
WATCH = "evals/scenarios/tester-property/watch.py"
SCENE_MODULE = "evals/scenarios/tester/scenes/order/right.py"
NEW_FILE = "tests/fixtures_new/helper.py"
IGNORED = "ignored/broken.py"
TYPE_STATEMENT = "\ntype Row = dict[str, int]\n"
TYPE_PARAMETERS = "\ndef first[T](items: list[T]) -> T:\n    return items[0]\n"
# The stand-in: what the lint handed over goes to `record`, then the same `-c <code> <files>` runs here with compile()
# reading the source as MIN_PYTHON's grammar would.
STAND_IN = """#!{python}
import ast, builtins, json, sys
json.dump(sys.argv[1:], open({record!r}, "w", encoding="utf-8"))
real = compile
def held(source, filename, mode, *rest, **more):
    if rest or more:   # ast.parse's own call
        return real(source, filename, mode, *rest, **more)
    return real(ast.parse(source, filename, feature_version={version}), filename, mode)
assert sys.argv[1] == "-c", sys.argv[1:2]
code = real(sys.argv[2], "<probe>", "exec")
builtins.compile = held
sys.argv = ["-c", *sys.argv[3:]]
exec(code)
"""
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:1500]}")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def copy_of_repository(target: Path) -> None:
    """Every tracked .py file of this repository and the ownership map, in a git repository of their own."""
    tracked = [f for f in git(ROOT, "ls-files", "-z", "--", "*.py").split("\0") if f and (ROOT / f).is_file()]
    for name in [*tracked, ".claude/ownership.txt"]:
        place = target / name
        place.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, place)
    (target / ".gitignore").write_text("ignored/\n__pycache__/\n.mypy_cache/\n.ruff_cache/\n", encoding="utf-8")
    git(target, "init", "-q")
    git(target, "add", "-A")


def lint(copy: Path, path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "tests/test_engine_lint.py"], cwd=copy, env=hook_env(str(copy), PATH=path),
                          capture_output=True, text=True, check=False)


def handed_over(record: Path) -> list[str]:
    """The files of the last call of the stand-in — what follows `-c <code>` — or nothing when it was not called."""
    if not record.is_file():
        return []
    files: list[str] = json.loads(record.read_text(encoding="utf-8"))[2:]
    record.unlink()
    return files


def compile_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if OLDEST in line and "compiles" in line]


def findings(out: str) -> str:
    """What the compile check reported: its line and the lines under it, one per file, up to the verdict."""
    start = out.find(f"FAIL {OLDEST} compiles")
    return "" if start < 0 else out[start:].split("\n\n")[0]


with tempfile.TemporaryDirectory() as tmp:
    copy, record, shims = Path(tmp) / "repo", Path(tmp) / "handed.json", Path(tmp) / "bin"
    copy_of_repository(copy)
    shims.mkdir()
    stand_in = shims / OLDEST
    stand_in.write_text(STAND_IN.format(python=sys.executable, record=str(record),
                                        version=tuple(int(n) for n in MIN_PYTHON.split("."))), encoding="utf-8")
    stand_in.chmod(0o755)
    path = str(shims) + os.pathsep + os.environ.get("PATH", "")
    (copy / IGNORED).parent.mkdir()
    (copy / IGNORED).write_text("def broken(:\n", encoding="utf-8")
    tracked = sorted(f for f in git(copy, "ls-files", "-z", "--", "*.py").split("\0") if f)

    print(f"— the repository as it stands, {OLDEST} a stand-in that records what it is handed")
    check("the scene has what the item names: watch.py, a scene module, files below the top level of evals/ and tests/",
          WATCH in tracked and SCENE_MODULE in tracked and len(tracked) > 200, f"{len(tracked)} tracked")
    r = lint(copy, path)
    files = handed_over(record)
    line = (compile_lines(r.stdout) or [""])[0]
    check("the lint is green there", r.returncode == 0 and "PASS: engine lint clean" in r.stdout, f"exit {r.returncode}\n{r.stdout}{r.stderr}")
    check(f"{OLDEST} was handed every tracked .py file of the repository, each once",
          sorted(files) == tracked, f"{len(files)} handed, {len(tracked)} tracked; left out: {sorted(set(tracked) - set(files))[:12]}")
    check("…watch.py and the scene module among them", WATCH in files and SCENE_MODULE in files)
    check("…and not the file git ignores, which parses under no Python", IGNORED not in files, files)
    check("the line of the check says how many files it compiled", line.lstrip().startswith("ok") and f"({len(tracked)})" in line, line)

    print("— a 3.12-only form below the top level, and in a new file not yet added")
    for name, form in ((WATCH, TYPE_STATEMENT), (SCENE_MODULE, TYPE_PARAMETERS)):
        with (copy / name).open("a", encoding="utf-8") as handle:
            handle.write(form)
    (copy / NEW_FILE).parent.mkdir()
    (copy / NEW_FILE).write_text(TYPE_STATEMENT, encoding="utf-8")
    newer = sys.version_info >= (3, 12)
    parses_here = True
    for name in (WATCH, SCENE_MODULE, NEW_FILE):
        try:
            compile((copy / name).read_text(encoding="utf-8"), name, "exec")
        except SyntaxError:
            parses_here = False
    check("the forms are the ones this scene is about: python3.12+ parses the three files, an older one does not", parses_here == newer,
          f"parse under {sys.version.split()[0]}: {parses_here}")
    r = lint(copy, path)
    files = handed_over(record)
    check("the lint exits non-zero", r.returncode != 0, f"exit {r.returncode}\n{r.stdout}{r.stderr}")
    check("…its verdict line is FAIL, not «PASS: engine lint clean»",
          "FAIL: engine lint has findings" in r.stdout and "PASS: engine lint clean" not in r.stdout, r.stdout[-600:])
    found = findings(r.stdout)
    check("…the compile check is the one that failed, and it names watch.py with the line", f"{WATCH}:" in found, found or r.stdout)
    check("…and the scene module", f"{SCENE_MODULE}:" in found, found or r.stdout)
    check("…and the new file git does not track yet", NEW_FILE in files and f"{NEW_FILE}:" in found, found or r.stdout)

    print("— git cannot list the files")
    shutil.rmtree(copy / ".git")
    # GIT_CEILING_DIRECTORIES: the scene must not find a repository above the temporary directory either.
    r = subprocess.run([sys.executable, "tests/test_engine_lint.py"], cwd=copy, capture_output=True, text=True, check=False,
                       env=hook_env(str(copy), PATH=path, GIT_CEILING_DIRECTORIES=tmp))
    files = handed_over(record)
    check("the lint fails rather than compiling nothing and passing", r.returncode != 0 and "PASS: engine lint clean" not in r.stdout,
          f"exit {r.returncode}\n{r.stdout[-600:]}{r.stderr}")
    check(f"…with a FAIL line of the {OLDEST} check, and no file handed over", bool([x for x in compile_lines(r.stdout) if "FAIL" in x]) and not files,
          f"{compile_lines(r.stdout)} {files[:5]}")

print(f"\n{'FAIL' if FAIL else 'PASS'}: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
