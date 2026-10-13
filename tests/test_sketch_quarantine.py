#!/usr/bin/env python3
"""The sketch's quarantine in gate.py (board 099; the design is board 080, «Ескіз докладніше»).

Every case is a synthetic git project with the template's code paths and the real gate.py layer
`stop` on the files the turn changed:

  - a task in ескіз that changed a file outside sketches/, .engine/ and tasks/ — a file of SOURCE_DIRS
    or of docs/ — is a block; one that changed only those three closes clean, and the gates do not
    check its code under sketches/;
  - in any mode, working code that refers to a sketch is a block: a Python import of `sketches`, a
    string that is a path into a named sketch, such a path on an added line of a shell script;
  - not a block: a comment or a docstring that names the quarantine, a test holding a sketch path as
    data, a reference that was there before the turn; and outside ескіз the quarantine's first rule
    does not apply.

The third overseer's two findings (BLOCK 20261010T052400Z-486a30) have their own cases:

  - with CODE_EXTENSIONS empty («every changed file is code») the sketch's own record and the task file,
    which hold the sketch's command, are not working code that refers to a sketch — a file outside the
    records still is;
  - on the full layers (pre_commit, ci) the default ruff / mypy / pytest of a project with the tool
    tables go over `.`: each is told to leave `sketches/` at the project's root out — seen in the argv
    of PATH shims, in a project that has the directory and unchanged in one that has not.

  - the delete guard reads the diff, not the gate's file list: a sketch that throws away its own code
    is not judged by it either, and the same deletion in working code still is.

Run:   python3 tests/test_sketch_quarantine.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0
ENV = 'SOURCE_DIRS="src"\nCODE_EXTENSIONS="py sh js"\nPROJECT_MARKER=""\nLINT_CMD=""\nTYPECHECK_CMD=""\nTEST_CMD=""\n'
spec = importlib.util.spec_from_file_location("gate_under_test", ROOT / ".claude/hooks/gate.py")
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
sys.modules["gate_under_test"] = gate
spec.loader.exec_module(gate)
made: list[Path] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def project(mode_line: str = "", before: dict[str, str] | None = None) -> Path:
    root = Path(tempfile.mkdtemp(prefix="quarantine-")).resolve()
    made.append(root)
    for rel, text in {".claude/project.env": ENV, ".gitignore": ".claude/state/\n",
                      "tasks/doing/010-work.md": f"# 010\n\nЗалежить від: —\n{mode_line + chr(10) if mode_line else ''}Аудит потрібен: ні\n\n## Що зробити\n- щось\n",
                      **(before or {})}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    for args in (["init", "-q", "-b", "unattended/work"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    return root


def full_layer(layer: str, sketch: bool) -> str:
    """The argv of ruff, mypy and pytest (PATH shims of the engine's versions) on a full layer of a
    project that has the tool tables, with or without a sketch in it."""
    sys.path.insert(0, str(ROOT / ".claude/hooks"))
    import tool_versions

    root = project(before={"pyproject.toml": "[tool.ruff]\n[tool.mypy]\n", "src/app.py": "x = 1\n", "tests/test_app.py": "def test_a():\n    pass\n"})
    shim_dir = root.parent / f"{root.name}-shims"
    shim_dir.mkdir()
    made.append(shim_dir)
    for name in ("ruff", "mypy", "pytest"):
        shim = shim_dir / name
        shim.write_text(f'#!/usr/bin/env bash\n[ "$1" = --version ] && {{ echo "{name} {tool_versions.VERSIONS.get(name, "1.0")}"; exit 0; }}\n'
                        f'echo "{name} $*" >> "{shim_dir}/calls.log"\n', encoding="utf-8")
        shim.chmod(0o755)
    files = {"src/app.py": "x = 2\n"} | ({"sketches/rate/probe.py": "def broken(:\n"} if sketch else {})
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"} | {"CLAUDE_PROJECT_DIR": str(root), "PATH": f"{shim_dir}:{os.environ['PATH']}"}
    subprocess.run([sys.executable, str(ROOT / ".claude/hooks/gate.py"), "--layer", layer], cwd=root, env=env, capture_output=True, text=True, check=False)
    log = shim_dir / "calls.log"
    return (log.read_text(encoding="utf-8") if log.exists() else "").replace(shlex.quote(str(root / "sketches")), "<root>/sketches")


def turn(root: Path, files: dict[str, str]) -> list[tuple[str | None, int | None, str]]:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    report, _ = gate.run_layer("stop", root, None, None)
    return [(f.file, f.line, f.rule) for f in report.findings if f.rule.startswith("sketch/") and f.severity == "block"]


SKETCH = "Режим: ескіз"
try:
    print("a task in ескіз: nothing outside sketches/, .engine/ and tasks/")
    found = turn(project(SKETCH), {"src/app.py": "x = 1\n"})
    check("negative — a sketch changed a file of SOURCE_DIRS: a block, the file named", found == [("src/app.py", None, "sketch/outside")], found)
    found = turn(project(SKETCH), {"docs/how.md": "текст\n"})
    check("negative — a sketch changed docs/ (no code at all in the turn): a block all the same", found == [("docs/how.md", None, "sketch/outside")], found)
    found = turn(project(SKETCH), {"sketches/rate/probe.py": "def broken(:\n", ".engine/sketches/rate.md": "# запис\n",
                                   "tasks/doing/010-work.md": "# 010\n\nРежим: ескіз\n\n## Що зробити\n- спроба\n"})
    check("a sketch that changed only sketches/, .engine/ and tasks/: no block — and its code is not checked (a syntax error there is no finding)",
          found == [], found)
    found = turn(project(), {"src/app.py": "x = 1\n", "docs/how.md": "текст\n"})
    check("negative — outside ескіз (no mode line: соло) the quarantine's first rule does not apply", found == [], found)
    raised = project(SKETCH)
    task_file = raised / "tasks/doing/010-work.md"
    task_file.write_text(task_file.read_text(encoding="utf-8") + "\n## Режим піднято\n- 2026-10-10T04:00:00Z — ескіз → соло: потрібен робочий код\n",
                         encoding="utf-8")
    found = turn(raised, {"src/app.py": "x = 1\n"})
    check("a sketch raised to соло (mode.py raise, the way out the block names): the mode in force decides — no sketch/outside", found == [], found)

    print("working code that refers to a sketch: a block in any mode")
    found = turn(project(), {"src/b.py": "import os\nfrom sketches.rate import probe\n"})
    check("negative — a Python import from sketches: a block on its line", found == [("src/b.py", 2, "sketch/reference")], found)
    found = turn(project(), {"src/c.py": "import sketches.rate\n"})
    check("negative — `import sketches.rate`: a block", found == [("src/c.py", 1, "sketch/reference")], found)
    found = turn(project(), {"src/d.py": "DATA = open('sketches/rate/data.txt').read()\n"})
    check("negative — a string that is a path into a named sketch: a block", found == [("src/d.py", 1, "sketch/reference")], found)
    found = turn(project(), {"scripts/run.sh": "#!/bin/sh\n# the probe lives in sketches/rate\nbash sketches/rate/run.sh\n"})
    check("negative — a shell line that runs a sketch: a block on that line, not on the comment", found == [("scripts/run.sh", 3, "sketch/reference")], found)
    found = turn(project(), {"src/app/main.js": 'import { f } from "../../sketches/rate/f.js";\n'})
    check("negative — a JavaScript import two directories up into a sketch: a block", found == [("src/app/main.js", 1, "sketch/reference")], found)
    found = turn(project(), {"scripts/a/run.sh": "#!/bin/sh\nbash ../../sketches/rate/run.sh\n",
                             "scripts/b.sh": '#!/bin/sh\nbash "$ROOT/sketches/rate/run.sh"\n',
                             "scripts/c.sh": '#!/bin/sh\nbash "$(dirname "$0")/../sketches/rate/run.sh"\n',
                             "scripts/d.sh": '#!/bin/sh\nbash "${ROOT}/sketches/rate/run.sh"\n'})
    check("negative — shell paths into a sketch after ../../, $ROOT/, ${ROOT}/ and $(dirname \"$0\")/../: each a block",
          set(found) == {("scripts/a/run.sh", 2, "sketch/reference"), ("scripts/b.sh", 2, "sketch/reference"),
                         ("scripts/c.sh", 2, "sketch/reference"), ("scripts/d.sh", 2, "sketch/reference")}, found)
    found = turn(project(), {"scripts/e.sh": '#!/bin/sh\nbash "$ROOT"/sketches/rate/run.sh\n',
                             "scripts/f.sh": '#!/bin/sh\nbash "$(dirname "$0")"/../sketches/rate/run.sh\n',
                             "scripts/g.sh": "#!/bin/sh\nbash ${ROOT:-.}/sketches/rate/run.sh\n",
                             "scripts/h.sh": "#!/bin/sh\nbash `dirname $0`/../sketches/rate/run.sh\n"})
    check("negative — the variable quoted apart (\"$ROOT\"/, \"$(…)\"/), ${ROOT:-.}/ and a backtick command before the path: each a block",
          set(found) == {(f"scripts/{n}.sh", 2, "sketch/reference") for n in "efgh"}, found)
    found = turn(project(), {"src/fs.py": 'import subprocess\nROOT = "."\nsubprocess.run(f"{ROOT}/sketches/rate/run.sh")\n'})
    check("negative — a Python f-string with the path after a placeholder: a block", found == [("src/fs.py", 3, "sketch/reference")], found)
    found = turn(project(), {"src/abs.py": "LOGO = '/srv/app/static/sketches/logo.png'\nNAME = f'{ROOT}/static/sketches.png'\n"})
    check("an absolute path and an f-string that names no sketch directory: no block", found == [], found)
    found = turn(project(), {"src/p.py": 'import subprocess\nsubprocess.run("bash sketches/rate/run.sh", shell=True)\n'})
    check("negative — a Python string that runs a sketch, the path inside the string: a block", found == [("src/p.py", 2, "sketch/reference")], found)
    found = turn(project(SKETCH), {"src/e.py": "from sketches.x import y\n"})
    check("in ескіз both rules speak: outside the quarantine and a reference", set(found) == {("src/e.py", None, "sketch/outside"), ("src/e.py", 1, "sketch/reference")}, found)

    print("not a reference")
    found = turn(project(), {"src/f.py": '"""Code of a sketch lives in sketches/<name>/ and never here."""\n# see sketches/rate for the probe\nPREFIX = "sketches/"\n'})
    check("a docstring and a comment naming the quarantine, a bare prefix string: no block", found == [], found)
    found = turn(project(), {"src/n.py": "DRAWINGS = 'src/sketches/a.png'\nUP = 'x/../sketches/a'\n"})
    check("a directory that only shares the name deeper in the tree: no block", found == [], found)
    found = turn(project(), {"tests/test_g.py": "PROBE = 'sketches/rate/probe.py'\n"})
    check("a test holding a sketch path as data: no block (tests are not looked at)", found == [], found)
    spanning = project(before={"src/m.py": 'CMD = """\necho start\n"""\n'})
    found = turn(spanning, {"src/m.py": 'CMD = """\necho start\nbash sketches/rate/run.sh\n"""\n'})
    check("negative — a line added in the middle of a string spanning several lines: the string is judged, a block",
          found == [("src/m.py", 1, "sketch/reference")], found)
    old = project(before={"src/h.py": "from sketches.rate import probe\n"})
    found = turn(old, {"src/h.py": "from sketches.rate import probe\nX = 1\n"})
    check("a reference that was there before the turn: no block on the line the turn did not add", found == [], found)

    print("CODE_EXTENSIONS empty: every file is code — the records are still records")
    every = 'SOURCE_DIRS=""\nCODE_EXTENSIONS=""\nPROJECT_MARKER=""\nLINT_CMD=""\nTYPECHECK_CMD=""\nTEST_CMD=""\n'
    record = "# rate\n\n## Команда і вивід\n```\n$ bash sketches/rate/run.sh\n200 OK\n```\n\n## Відповідь\nтак\n"
    task = "# 010\n\nРежим: ескіз\n\n## Що зробити\n- запусти `bash sketches/rate/run.sh`\n"
    found = turn(project(SKETCH, before={".claude/project.env": every}),
                 {"sketches/rate/run.sh": "echo 200 OK\n", ".engine/sketches/rate.md": record, "tasks/doing/010-work.md": task})
    check("a sketch whose record and task file hold its command (`bash sketches/rate/run.sh`): no block — the record is not working code",
          found == [], found)
    found = turn(project(before={".claude/project.env": every}), {"scripts/run": "bash sketches/rate/run.sh\n", ".engine/notes.md": "bash sketches/rate/run.sh\n"})
    check("negative — there a file outside the records that runs a sketch is still a block (and the record beside it is not)",
          found == [("scripts/run", 1, "sketch/reference")], found)

    print("the guards leave a sketch's code alone")
    long_function = "def a():\n" + "".join(f"    x{i} = {i}\n" for i in range(30)) + "    return 1\n\n\ndef b():\n    return 2\n"
    for layer in ("stop", "pre_commit"):
        thrown = project(SKETCH, before={"sketches/rate/probe.py": long_function, "sketches/rate/old.py": long_function, "src/kept.py": long_function})
        (thrown / "sketches/rate/probe.py").write_text("def b():\n    return 2  # type: ignore\n", encoding="utf-8")
        (thrown / "sketches/rate/old.py").unlink()
        subprocess.run(["git", "add", "-A"], cwd=thrown, check=True, capture_output=True)
        report, _ = gate.run_layer(layer, thrown, None, None)
        blocks = [(f.file, f.rule) for f in report.findings if f.severity == "block"]
        check(f"{layer} — a sketch throws away a function and a file of its own and marks a line type-ignore: no guard speaks", blocks == [], blocks)
    working = project(before={"src/kept.py": long_function})
    (working / "src/kept.py").write_text("def b():\n    return 2\n", encoding="utf-8")
    report, _ = gate.run_layer("stop", working, None, None)
    blocks = [(f.file, f.rule) for f in report.findings if f.severity == "block"]
    check("negative — the same deletion in working code is still the delete guard's block", blocks == [("src/kept.py", "delete/untested")], blocks)
    deeper = project(before={"src/sketches/kept.py": long_function})
    (deeper / "src/sketches/kept.py").write_text("def b():\n    return 2\n", encoding="utf-8")
    report, _ = gate.run_layer("stop", deeper, None, None)
    blocks = [(f.file, f.rule) for f in report.findings if f.severity == "block"]
    check("negative — the same deletion in src/sketches/ (a directory that only shares the name, inside SOURCE_DIRS) is still the delete guard's block",
          blocks == [("src/sketches/kept.py", "delete/untested")], blocks)

    print("the full layers: the default ruff / mypy / pytest leave sketches/ out")
    for layer in ("pre_commit", "ci"):
        log = full_layer(layer, sketch=True)
        check(f"negative — {layer}, a project with the tool tables and a sketch: ruff, mypy and pytest are each told to skip the root's sketches/",
              "ruff check --force-exclude --extend-exclude <root>/sketches ." in log and "mypy --exclude ^sketches/ ." in log
              and "pytest -x --no-header -q --ignore=sketches" in log, log)
    log = full_layer("ci", sketch=False)
    check("a project with no sketches/ directory: the three commands are what they were",
          log.splitlines() == ["ruff check --force-exclude .", "mypy .", "pytest -x --no-header -q"], log)
finally:
    for path in made:
        shutil.rmtree(path, ignore_errors=True)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
