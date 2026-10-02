#!/usr/bin/env python3
"""Hygiene of the text the model reads (package 2b, item 5).

Three kinds of stale text, each of which once sent an agent down a path that does not exist:

  1. Four slash commands that no command file defines (`/lesson`, `/wrap-up`, `/stuck`,
     `/memory-maintenance`) must not be mentioned anywhere the model reads — a session that
     is told to type them gets "unknown command". The check greps the whole tree, not a list.
  2. No paragraph may claim that the hooks need `jq` alone: they parse their input with jq
     OR python3 and refuse the call with neither, on every operating system.
  3. The record templates a project is seeded from must not carry this repository's own
     history — dates, node ids, references to records that only exist here.

Prose about the past is allowed only in the engine's own records (.engine/) and in the plans
(docs/plan/), which are history, not instructions.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHANTOM = ("/lesson", "/wrap-up", "/stuck", "/memory-maintenance")
# Where the model reads: everything under .claude/ (skills, commands, agents, references,
# hooks, harness), the two root files, the seeds, and the docs — except the plans and the
# engine's own records, which are history.
ROOTS = (".claude", "CLAUDE.md", "AGENTS.md", "templates", "docs", "evals/README.md", "install.sh", "engine.py")
SKIP = ("docs/plan/",)
SELF = Path(__file__).resolve()
PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + detail[:600]}")


def tracked_text_files() -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard", "--", *ROOTS],
                         capture_output=True, text=True, check=True).stdout
    files = []
    for rel in filter(None, out.split("\n")):
        if rel.startswith(SKIP) or (ROOT / rel).resolve() == SELF:
            continue
        path = ROOT / rel
        if path.is_file() and path.suffix in (".md", ".py", ".sh", ".txt", ".json", ".env", ""):
            files.append(path)
    return files


def main() -> int:
    files = tracked_text_files()
    check(f"scanned {len(files)} files the model reads", len(files) > 50)

    # 1. The four phantom commands.
    phantom_re = re.compile(r"(?<![\w/.-])(" + "|".join(re.escape(c) for c in PHANTOM) + r")(?![\w-])")
    hits = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if phantom_re.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:80]}")
    check("no mention of the four phantom memory commands", not hits, "; ".join(hits[:6]))
    check("the phantom pattern catches a slash command and ignores a path",
          bool(phantom_re.search("type /lesson now")) and bool(phantom_re.search('say "/wrap-up"'))
          and not phantom_re.search("docs/lesson.md") and not phantom_re.search("triggers/stuck-protocol.md"))

    # 2. jq alone is not the requirement.
    bad_jq = []
    for path in files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"silently\s+enforce nothing without it", text) or re.search(r"REQUIRED:\s*four hooks", text):
            bad_jq.append(str(path.relative_to(ROOT)))
    check("no paragraph says the hooks need jq alone (they fall back to python3)", not bad_jq, "; ".join(bad_jq))
    hooks_ref = ROOT / ".claude/references/hooks.md"
    text = hooks_ref.read_text(encoding="utf-8") if hooks_ref.is_file() else ""
    check("the hooks reference states the jq-or-python3 rule for any OS",
          "python3" in text and "refuse" in text and ("apt" in text or "any operating system" in text))
    # The rule as written in the hooks: both deny hooks really do fall back to python3.
    for hook in ("block-dangerous.sh", "protect-paths.sh"):
        src = (ROOT / ".claude/hooks" / hook).read_text(encoding="utf-8")
        check(f"{hook} parses with jq, falls back to python3, refuses with neither",
              "command -v jq" in src and "python3" in src and "Neither jq nor python3" in src)

    # 3. The seeds carry no history of this repository.
    seeds = sorted((ROOT / "templates/project").rglob("*.md"))
    history_re = re.compile(r"\b20\d\d-\d\d-\d\d\b|\bnode S\d\b|\bD-\d+\b|package 3[bc]|claude-cli-config")
    stained = []
    for seed in seeds:
        for n, line in enumerate(seed.read_text(encoding="utf-8").splitlines(), 1):
            if history_re.search(line):
                stained.append(f"{seed.relative_to(ROOT)}:{n}: {line.strip()[:80]}")
    check(f"the {len(seeds)} seeds carry no dates, node ids or references to this repository's records", not stained, "; ".join(stained[:6]))

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
