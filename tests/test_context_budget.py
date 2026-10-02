#!/usr/bin/env python3
"""The persistent context — CLAUDE.md, AGENTS.md and everything they import — stays under
200 lines, for this repository AND for a project seeded from templates/project/.

WHY. Claude Code loads CLAUDE.md and every `@path` it imports at launch; an import does not
save context, it only moves text. Files over about 200 lines consume more context and are
followed less reliably (code.claude.com/docs/en/memory). Package 2b moved the engine's
standing rules into `.claude/engine-rules.md` and the rarely needed detail into
`.claude/references/` precisely to get under that line, and nothing but a count keeps it there.

WHAT IS CHECKED
  - imports are resolved the way Claude Code resolves them: an `@path` token at the start of
    a line or after whitespace, outside code spans and fenced code blocks, relative to the
    file that contains it, recursively (the loader stops at 4 hops; so does this test);
  - an import that does not resolve to a file FAILS — the loader would silently load nothing;
  - the closure's line count is at most 200 for each root set;
  - `.claude/CLAUDE.md` and `.claude/rules/` do not exist: Claude Code loads both on its own,
    and the owner wants exactly one path in — the import;
  - the engine's rules file imports nothing (references are read on demand, not at launch).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGET = 200
MAX_HOPS = 4
# `@path` at the start of a line or after whitespace; the path runs to the next whitespace.
# An e-mail address (`x@y.z`) has a word character before the `@` and is not an import.
IMPORT_RE = re.compile(r"(?:(?<=\s)|^)@([^\s`]+)", re.MULTILINE)
FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
SPAN_RE = re.compile(r"`[^`\n]*`")

PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + detail[:400]}")


def imports_of(path: Path) -> list[str]:
    text = SPAN_RE.sub("", FENCE_RE.sub("", path.read_text(encoding="utf-8")))
    return [m.group(1).rstrip(".,;:)") for m in IMPORT_RE.finditer(text)]


def resolve(path: Path, token: str) -> Path:
    target = Path(token).expanduser()
    return target if target.is_absolute() else (path.parent / target)


def closure(root: Path) -> tuple[list[Path], list[str]]:
    """Every file loaded at launch from `root`, in load order, and every unresolved import."""
    seen: list[Path] = []
    missing: list[str] = []

    def walk(path: Path, hops: int) -> None:
        if path in seen:
            return
        seen.append(path)
        if hops >= MAX_HOPS:
            return
        for token in imports_of(path):
            target = resolve(path, token).resolve()
            if target.is_file():
                walk(target, hops + 1)
            else:
                shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                missing.append(f"{shown} imports @{token} -> {target} (not a file)")

    walk(root.resolve(), 0)
    return seen, missing


def lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def report(label: str, root: Path) -> None:
    files, missing = closure(root)
    check(f"{label}: every import resolves", not missing, "; ".join(missing))
    total = sum(lines(f) for f in files)
    detail = ", ".join(f"{f.relative_to(ROOT) if f.is_relative_to(ROOT) else f}={lines(f)}" for f in files)
    check(f"{label}: {total} lines in {len(files)} files, budget {BUDGET}", total <= BUDGET, detail)
    print(f"       {detail}")


def main() -> int:
    report("this repository (CLAUDE.md)", ROOT / "CLAUDE.md")
    seed = ROOT / "templates" / "project" / "CLAUDE.md"
    if seed.is_file():
        # A seeded project's CLAUDE.md sits at ITS root; its imports resolve against this
        # repository's `.claude/` — the engine files a project receives — and against the
        # seed AGENTS.md beside it. Resolve from a stand-in root that has both.
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory(prefix="context-budget-") as tmp:
            stand_in = Path(tmp)
            shutil.copy2(seed, stand_in / "CLAUDE.md")
            if (seed.parent / "AGENTS.md").is_file():
                shutil.copy2(seed.parent / "AGENTS.md", stand_in / "AGENTS.md")
            (stand_in / ".claude").symlink_to(ROOT / ".claude")
            files, missing = closure(stand_in / "CLAUDE.md")
            check("a seeded project: every import resolves", not missing, "; ".join(missing))
            total = sum(lines(f) for f in files)
            detail = ", ".join(f"{f.name}={lines(f)}" for f in files)
            check(f"a seeded project: {total} lines in {len(files)} files, budget {BUDGET}", total <= BUDGET, detail)
            print(f"       {detail}")
    else:
        print("  skip a seeded project: templates/project/CLAUDE.md does not exist yet")

    rules = ROOT / ".claude" / "engine-rules.md"
    check("the engine rules file exists", rules.is_file())
    if rules.is_file():
        check("the engine rules file imports nothing (references are read on demand)", not imports_of(rules), str(imports_of(rules)))
        check(f"the engine rules file is under 100 lines ({lines(rules)})", lines(rules) <= 100)
    check("no .claude/CLAUDE.md (Claude Code would load it on its own, twice with the import)", not (ROOT / ".claude" / "CLAUDE.md").exists())
    check("no .claude/rules/ (same reason)", not (ROOT / ".claude" / "rules").exists())

    # The parser itself: the cases that would make the count lie.
    sample = ROOT / "tests" / "fixtures"
    probe = "See @README and @docs/x.md\n```\n@not/an/import\n```\nmail noreply@anthropic.com `@also/not`\n@~/home.md"
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".md", dir=str(sample) if sample.is_dir() else None, delete=False) as fh:
        fh.write(probe)
        tmp_path = Path(fh.name)
    try:
        found = imports_of(tmp_path)
    finally:
        tmp_path.unlink()
    check("the import parser: inline and own-line imports, not code blocks, spans or e-mail",
          found == ["README", "docs/x.md", "~/home.md"], str(found))

    # The Stop gate's fast subset (package 2b, item 8): `--fast` must run at least one suite,
    # every name in the list must exist, and TEST_CMD must name the subset.
    import subprocess

    listed = subprocess.run(["bash", str(ROOT / "tests/run_all.sh"), "--fast", "--list"], capture_output=True, text=True, check=False)
    suites = [s for s in listed.stdout.split("\n") if s]
    check(f"`run_all.sh --fast` resolves to {len(suites)} suites (not a silent zero)", listed.returncode == 0 and len(suites) >= 1, listed.stderr)
    check("every fast suite exists", all((ROOT / s).is_file() for s in suites), str(suites))
    env_text = (ROOT / ".claude/project.env").read_text(encoding="utf-8")
    check("TEST_CMD of this repository runs the fast subset", 'TEST_CMD="bash tests/run_all.sh --fast"' in env_text)

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
