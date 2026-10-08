#!/usr/bin/env python3
"""Which lines and branches of the engine's hooks and scripts does no test and no scenario run?

    python3 evals/hook_coverage.py run --data DIR -- bash tests/run_all.sh
    python3 evals/hook_coverage.py run --data DIR2 -- python3 evals/run_hook_scenarios.py --engine-ref HEAD
    python3 evals/hook_coverage.py report DIR [DIR2 ...] [--json FILE] [--missing] [--only PATH] [--root DIR]

`run` executes the command with tracing switched on for every process it starts, however deep:

- Python — a line tracer of the engine's own (`hook_coverage_trace.py`, put on PYTHONPATH as
  `sitecustomize`), which notes the jumps from line to line inside the engine's files only.
  coverage.py's own start-up costs a third of a second in EVERY interpreter, and the suites
  start thousands; this one costs nothing a suite notices.
- Shell — bash's own xtrace, switched on through BASH_ENV for a script of the engine and
  written to a file of its own (BASH_XTRACEFD), so a hook's stderr stays what it was.

The suites and the golden set run COPIES of the hooks — a sandbox `engine.py install` built, a
synthetic repository, sometimes an older tag. A traced file therefore counts for a file of this
repository only when its content is the same (SHA-1, taken when the process ends): a line number
in an older or a doctored copy says nothing about the file here.

`report` adds the traces of one or more runs and prints, per file of the scope (SCOPE below),
lines and branches run / in all. --missing lists what was not run, grouped by function.
--root names another repository whose files are the ones measured (the suite uses it).

WHAT THE NUMBERS ARE NOT. Shell has no branch measure: a line counts, and which lines of a
script can run at all is this file's reading of it (`shell_lines`), not bash's. Python embedded
in a shell script (`python3 -c`, a heredoc) is not seen. A Python process that ends without
running its exit handlers (a signal, `os._exit`, `os.exec*`) leaves nothing.

Standard library only, Python 3.12+; `report` alone needs coverage.py — it reads a file's possible
branches — and fetches it with `uvx` into uv's cache. The engine installs nothing. Nothing here talks to a model.
"""

from __future__ import annotations

import argparse
import ast
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

JsonObj = dict[str, Any]

REPO = Path(__file__).resolve().parent.parent
# The engine's hooks and scripts: what a project runs after `engine.py install`.
SCOPE = (".claude/hooks/*.py", ".claude/hooks/*.sh", ".claude/unattended/*.py", ".claude/unattended/*.sh",
         "engine.py", "install.sh")
TRACER = Path(__file__).resolve().parent / "hook_coverage_trace.py"

BASH_ENV = r'''# Sourced by every non-interactive bash (BASH_ENV), before $0 names the script: the DEBUG
# trap fires once, at the script's first command, and traces a script of the engine, nothing else.
# (The trap removes itself in its own string: a function's change to it is undone on return.)
__hookcov_start() {
  local f sum _
  case "${0:-}" in
    */.claude/hooks/*.sh|*/.claude/unattended/*.sh|.claude/hooks/*.sh|.claude/unattended/*.sh|*/install.sh|install.sh)
      if [ -n "${HOOKCOV_DIR:-}" ] && [ -f "$0" ] && exec {__hookcov_fd}>>"$HOOKCOV_DIR/sh/$$.$RANDOM$RANDOM.trace"; then
        {
          printf '#CWD %s\n' "$PWD"
          for f in "$0" "${0%/*}"/*.sh; do
            [ -f "$f" ] && read -r sum _ < <(@SHA1SUM@ < "$f") && printf '#SHA %s %s\n' "$sum" "$f"
          done
        } >&"$__hookcov_fd"
        BASH_XTRACEFD=$__hookcov_fd
        PS4='+|${BASH_SOURCE}|${LINENO}| '
        set -x
      fi
      ;;
  esac
  unset -f __hookcov_start
} 2>/dev/null
trap 'trap - DEBUG; __hookcov_start' DEBUG
'''

TRACE_LINE = re.compile(r"^\++\|([^|\n]+)\|(\d+)\| ")


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def scope_files(only: str = "") -> list[str]:
    found: list[str] = []
    for pattern in SCOPE:
        found.extend(str(p.relative_to(REPO)) for p in sorted(REPO.glob(pattern)) if p.is_file())
    return [f for f in found if only in f]


@functools.cache
def coverage_site() -> str:
    """The directory holding a coverage.py built for THIS interpreter (fetched by uvx)."""
    if not shutil.which("uvx"):
        raise SystemExit("hook_coverage: uvx is not installed — coverage.py cannot be fetched, nothing measured.")
    out = subprocess.run(
        ["uvx", "--quiet", "--python", sys.executable, "--from", "coverage", "python", "-c",
         "import coverage, os; print(os.path.dirname(os.path.dirname(coverage.__file__)))"],
        capture_output=True, text=True, check=False, cwd="/")
    site = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if out.returncode != 0 or not Path(site, "coverage").is_dir():
        raise SystemExit(f"hook_coverage: uvx could not provide coverage.py: {out.stderr.strip()[:300]}")
    return site


def cmd_run(args: argparse.Namespace) -> int:
    if not args.command:
        raise SystemExit("hook_coverage run: give the command after `--`.")
    data = args.data.resolve()
    if data.exists() and any(data.iterdir()):
        raise SystemExit(f"hook_coverage run: {data} is not empty — a run gets a directory of its own.")
    for sub in ("boot", "py", "sh"):
        (data / sub).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TRACER, data / "boot" / "sitecustomize.py")
    # A hook may be run with a PATH that holds next to nothing: the one tool the trace needs is named in full.
    (data / "bashenv.sh").write_text(BASH_ENV.replace("@SHA1SUM@", shutil.which("sha1sum") or "sha1sum"), encoding="utf-8")
    (data / "run.json").write_text(json.dumps({"command": args.command}) + "\n", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(data / "boot"), env.get("PYTHONPATH", "")) if p)
    env["BASH_ENV"] = str(data / "bashenv.sh")
    env["HOOKCOV_DIR"] = str(data)
    return subprocess.run(args.command, env=env, check=False).returncode


# ---- reading the traces --------------------------------------------------------------------

def python_arcs(dirs: list[Path], by_sha: dict[str, str]) -> tuple[dict[str, set[tuple[int, int]]], int]:
    """Jumps per repository file, from every traced copy that is identical to it; and how many
    traced copies were not."""
    arcs: dict[str, set[tuple[int, int]]] = defaultdict(set)
    foreign = 0
    for folder in dirs:
        for note in sorted((folder / "py").glob("*.json")):
            try:
                files = json.loads(note.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:  # a file cut short by a kill
                print(f"hook_coverage: skipped {note.name}: {exc}", file=sys.stderr)
                continue
            for entry in files.values():
                rel = by_sha.get(entry.get("sha", ""))
                if rel is None:
                    foreign += 1
                    continue
                arcs[rel].update((a, b) for a, b in entry.get("arcs", []))
    return arcs, foreign


def shell_hits(dirs: list[Path], by_sha: dict[str, str]) -> dict[str, set[int]]:
    hits: dict[str, set[int]] = defaultdict(set)
    for folder in dirs:
        for trace in (folder / "sh").glob("*.trace"):
            cwd, known = "", {}
            with trace.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("#CWD "):
                        cwd = line[5:].rstrip("\n")
                    elif line.startswith("#SHA "):
                        _, digest, name = line.rstrip("\n").split(" ", 2)
                        known[os.path.normpath(os.path.join(cwd, name))] = by_sha.get(digest)
                    elif (m := TRACE_LINE.match(line)):
                        rel = known.get(os.path.normpath(os.path.join(cwd, m.group(1))))
                        if rel:
                            hits[rel].add(int(m.group(2)))
    return hits


# A line that closes a block, whatever it redirects (`done < <(...)`, `} > file`), and a `case` arm that does nothing (`x) ;;`).
STRUCTURAL = re.compile(r"^(?:(?:then|else|fi|do|done|esac|\{|\}|\(|\)|;;|;&|in)(?:\s*[;&|]*\s*(?:then|else|fi|do|done|esac|\{|\}|\)|;;))*\s*(?:(?:\d*(?:<<<|>>|<|>)|2>&1).*)?|[^()\s][^()]*\)\s*;;)\s*(?:#.*)?$")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
FUNC_HEAD = re.compile(r"^(?:function\s+)?([A-Za-z_][A-Za-z0-9_:-]*)\s*\(\)\s*\{?\s*(?:#.*)?$")
CASE_PATTERN_ONLY = re.compile(r"^[^()\s][^()]*\)\s*(?:#.*)?$")
ARRAY_OPEN = re.compile(r"^(?:local\s+|declare\s+(?:-\w+\s+)*)?[A-Za-z_][A-Za-z0-9_]*\+?=\(\s*(?:#.*)?$")


def shell_lines(text: str) -> tuple[set[int], dict[int, str], dict[int, int]]:
    """The lines of a shell script that xtrace can report, the function each line is in, and —
    for a command that spans several lines (an array literal, a quoted string, a continued
    command), which bash may report at its first or its last line — every line's first line.

    A reading, not a parse: blank lines, comments, bare keywords, a `case` pattern alone on its
    line, function headers and heredoc bodies are left out."""
    lines: set[int] = set()
    owner: dict[int, str] = {}
    first: dict[int, int] = {}
    heredoc = ""
    func = ""
    quote_open = ""
    in_array = False
    span = 0  # the first line of the command the current line continues, 0 = none
    for number, raw in enumerate(text.splitlines(), 1):
        owner[number] = func
        if heredoc:
            if raw.strip() == heredoc:
                heredoc = ""
            continue
        stripped = raw.strip()
        if in_array or quote_open:
            first[number] = span
            if in_array:
                in_array = not stripped.startswith(")")
            else:
                quote_open = _unbalanced(stripped, quote_open)
            if not in_array and not quote_open and not stripped.endswith(("\\", "|", "&&", "||")):
                span = 0
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if span:
            first[number] = span
        if (m := FUNC_HEAD.match(stripped)) and not span:
            func = m.group(1)
            owner[number] = func
            continue
        if raw.startswith("}"):
            func = ""
        if (m := HEREDOC.search(stripped)) and "<<<" not in stripped:
            heredoc = m.group(2)
        in_array = bool(ARRAY_OPEN.match(stripped))
        quote_open = _unbalanced(stripped, "")
        continues = in_array or bool(quote_open) or stripped.endswith(("\\", "|", "&&", "||"))
        if span:
            span = span if continues else 0
            continue
        if continues:
            span = number
        if STRUCTURAL.match(stripped) or CASE_PATTERN_ONLY.match(stripped):
            continue
        lines.add(number)
    return lines, owner, first


def _unbalanced(text: str, state: str) -> str:
    """The quote still open at the end of `text`, starting inside `state` ('' = none)."""
    i = 0
    while i < len(text):
        ch = text[i]
        if state == "'":
            if ch == "'":
                state = ""
        elif state == '"':
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = ""
        elif ch == "\\":
            i += 1
        elif ch == "#" and (i == 0 or text[i - 1].isspace()):
            break
        elif ch in "'\"":
            state = ch
        i += 1
    return state


def python_report(rel: str, arcs: set[tuple[int, int]]) -> JsonObj:
    """Lines and branches of one Python file: in all, run, and what was missed, by function."""
    if (site := coverage_site()) not in sys.path:
        sys.path.append(site)
    from coverage import Coverage, CoverageData  # type: ignore[import-not-found]

    path = REPO / rel
    scratch = Path(os.environ.get("TMPDIR", "/tmp")) / f"hookcov-{os.getpid()}"
    scratch.mkdir(exist_ok=True)
    data_file = scratch / "combined"
    for old in scratch.glob("combined*"):
        old.unlink()
    data = CoverageData(basename=str(data_file))
    data.add_arcs({str(path): arcs})
    data.write()
    cov = Coverage(data_file=str(data_file), branch=True, config_file=False, include=[str(path)])
    cov.load()
    analysis = cov._analyze(str(path))  # the public analysis2() has no branch detail
    shutil.rmtree(scratch, ignore_errors=True)
    owner = python_owners(path)
    missing_branches = sorted((src, dst) for src, dsts in analysis.missing_branch_arcs().items() for dst in dsts)
    return {
        "kind": "python",
        "lines": len(analysis.statements), "lines_run": len(analysis.statements) - len(analysis.missing),
        "branches": analysis.numbers.n_branches, "branches_run": analysis.numbers.n_branches - analysis.numbers.n_missing_branches,
        "missing_lines": sorted(analysis.missing),
        "missing_branches": [[s, d] for s, d in missing_branches],
        "owner": {str(n): owner.get(n, "") for n in set(analysis.missing) | {s for s, _ in missing_branches}},
    }


def python_owners(path: Path) -> dict[int, str]:
    owner: dict[int, str] = {}
    tree = ast.parse(path.read_text(encoding="utf-8"))

    def walk(node: ast.AST, name: str) -> None:
        for child in ast.iter_child_nodes(node):
            inner = name
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                inner = f"{name}.{child.name}" if name else child.name
                for n in range(child.lineno, (child.end_lineno or child.lineno) + 1):
                    owner[n] = inner
            walk(child, inner)

    walk(tree, "")
    return owner


def shell_report(rel: str, hits: set[int]) -> JsonObj:
    lines, owner, first = shell_lines((REPO / rel).read_text(encoding="utf-8"))
    hits = {first.get(n, n) for n in hits}
    lines |= hits  # xtrace is the authority on what can run
    missing = sorted(lines - hits)
    return {"kind": "shell", "lines": len(lines), "lines_run": len(lines & hits), "branches": 0, "branches_run": 0,
            "missing_lines": missing, "missing_branches": [], "owner": {str(n): owner.get(n, "") for n in missing}}


def measure(dirs: list[Path], only: str = "") -> JsonObj:
    files = scope_files(only)
    by_sha = {sha1(REPO / rel): rel for rel in scope_files()}  # every file of the scope: --only narrows the report, not what counts as a copy
    arcs, foreign = python_arcs(dirs, by_sha)
    hits = shell_hits(dirs, by_sha)
    report: JsonObj = {"runs": [str(d) for d in dirs], "foreign_copies": foreign, "files": {}}
    for rel in files:
        report["files"][rel] = python_report(rel, arcs.get(rel, set())) if rel.endswith(".py") else shell_report(rel, hits.get(rel, set()))
    totals = {key: sum(f[key] for f in report["files"].values()) for key in ("lines", "lines_run", "branches", "branches_run")}
    report["totals"] = totals
    return report


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:5.1f}%" if whole else "    — "


def ranges(numbers: list[int]) -> str:
    out: list[str] = []
    start = prev = None
    for n in numbers:
        if prev is not None and n == prev + 1:
            prev = n
            continue
        if start is not None:
            out.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    if start is not None:
        out.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(out)


def print_report(report: JsonObj, missing: bool) -> None:
    print(f"{'file':44} {'lines':>11} {'':>6} {'branches':>11} {'':>6}")
    for rel, f in report["files"].items():
        print(f"{rel:44} {f['lines_run']:>5}/{f['lines']:<5} {pct(f['lines_run'], f['lines'])} "
              f"{f['branches_run']:>5}/{f['branches']:<5} {pct(f['branches_run'], f['branches'])}")
    t = report["totals"]
    print(f"{'TOTAL':44} {t['lines_run']:>5}/{t['lines']:<5} {pct(t['lines_run'], t['lines'])} "
          f"{t['branches_run']:>5}/{t['branches']:<5} {pct(t['branches_run'], t['branches'])}")
    if report["foreign_copies"]:
        print(f"\n{report['foreign_copies']} measured file(s) were copies that differ from this repository's — not counted.")
    if not missing:
        return
    for rel, f in report["files"].items():
        groups: dict[str, list[int]] = defaultdict(list)
        for n in f["missing_lines"]:
            groups[f["owner"].get(str(n), "")].append(n)
        partial: dict[str, list[str]] = defaultdict(list)
        gone = set(f["missing_lines"])
        for src, dst in f["missing_branches"]:
            if src not in gone:  # a branch out of a line that ran: the other way was never taken
                partial[f["owner"].get(str(src), "")].append(f"{src}->{dst if dst > 0 else 'exit'}")
        if not groups and not partial:
            continue
        print(f"\n== {rel}")
        for name in sorted(set(groups) | set(partial), key=lambda k: (groups.get(k) or [10**9])[0]):
            line = f"  {name or '<module>'}:"
            if groups.get(name):
                line += f" lines {ranges(groups[name])}"
            if partial.get(name):
                line += f"  | never taken: {', '.join(partial[name])}"
            print(line)


def cmd_report(args: argparse.Namespace) -> int:
    global REPO
    if args.root:
        REPO = args.root.resolve()
    for folder in args.data:
        if not (folder / "py").is_dir():
            raise SystemExit(f"hook_coverage report: {folder} holds no run (no py/ directory).")
    report = measure([d.resolve() for d in args.data], args.only)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print_report(report, args.missing)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="run a command with tracing on")
    run.add_argument("--data", type=Path, required=True, help="an empty directory for this run's traces")
    run.add_argument("command", nargs=argparse.REMAINDER)
    rep = sub.add_parser("report", help="add up the traces of one or more runs")
    rep.add_argument("data", type=Path, nargs="+")
    rep.add_argument("--json", type=Path, help="write the full result here")
    rep.add_argument("--missing", action="store_true", help="list what was not run, by function")
    rep.add_argument("--only", default="", help="only files whose path contains this")
    rep.add_argument("--root", type=Path, help="the repository whose files are measured (default: this one)")
    args = parser.parse_args()
    if args.action == "run":
        if args.command[:1] == ["--"]:
            args.command = args.command[1:]
        return cmd_run(args)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
