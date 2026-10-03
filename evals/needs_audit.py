#!/usr/bin/env python3
"""Has any text the model reads changed since a ref? If not, no audit is due.

    python3 evals/needs_audit.py <ref> [--json]

WHY. The audit (run_audit_scenarios.py) measures a model's judgement, in paid sessions. That
judgement can only move when the words the model is given move. A change to a test, an
instrument, the installer or a record cannot change a verdict, and auditing after it buys
nothing. The rule (evals/README.md): an audit only when this script says so, at the `smoke`
tier; the `full` tier only before a version tag.

WHAT COUNTS as text the model reads — the owner's list (package costs, item 2):
    skills      .claude/skills/
    agents      .claude/agents/
    commands    .claude/commands/
    rules       .claude/engine-rules.md, .claude/constitution.md, .claude/references/,
                .engine/rules.md
    CLAUDE.md, AGENTS.md  (and the seeds a project receives: templates/project/...)
A second class is reported apart, as MAYBE: hook files that put strings of their own in front of
the model (the audit request, the continue text, the gate's block reason). Most edits there
change logic, not words — look at the diff and decide.

Changed means: differs between <ref> and the working tree — committed since, staged, unstaged,
untracked, deleted. A rename is a deletion plus an addition.

Exit: 0 nothing the model reads changed; 1 something did (TEXT or MAYBE), listed; 2 the ref is
not a commit. It never starts an audit. Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIRS = (".claude/skills/", ".claude/agents/", ".claude/commands/", ".claude/references/")
TEXT_FILES = frozenset({
    ".claude/engine-rules.md", ".claude/constitution.md", ".engine/rules.md", "CLAUDE.md", "AGENTS.md",
    "templates/project/CLAUDE.md", "templates/project/AGENTS.md", "templates/project/.engine/rules.md",
})
MAYBE_FILES = frozenset({
    ".claude/hooks/overseer_stop.py", ".claude/hooks/gate_allows.py", ".claude/hooks/lesson_queue.py",
    ".claude/hooks/gate.py", ".claude/hooks/env-check.sh",
})


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def classify(path: str) -> str | None:
    """"text", "maybe" or None for a repository-relative path."""
    if path in TEXT_FILES or path.startswith(TEXT_DIRS):
        return "text"
    if path in MAYBE_FILES:
        return "maybe"
    return None


def changed_since(root: Path, ref: str) -> list[tuple[str, str]]:
    """(status letter, path) for everything that differs between `ref` and the working tree."""
    changed: dict[str, str] = {}
    diff = git(root, "diff", "--name-status", "--no-renames", ref)
    for line in diff.stdout.splitlines():
        status, _, path = line.partition("\t")
        if path:
            changed[path] = status[:1]
    for path in git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines():
        if path:
            changed.setdefault(path, "A")
    return sorted((status, path) for path, status in changed.items())


class Assessment(TypedDict):
    ref: str
    audit_needed: bool
    tier: str | None
    text: list[str]
    maybe: list[str]
    changed_files: int


def assess(root: Path, ref: str) -> Assessment:
    changed = changed_since(root, ref)
    text = [f"{s} {p}" for s, p in changed if classify(p) == "text"]
    maybe = [f"{s} {p}" for s, p in changed if classify(p) == "maybe"]
    return {"ref": ref, "audit_needed": bool(text or maybe), "tier": "smoke" if text or maybe else None,
            "text": text, "maybe": maybe, "changed_files": len(changed)}


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("ref", help="tag, branch or commit to compare the working tree with")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=None, help="another checkout (default: this repository)")
    args = parser.parse_args(argv)
    root = args.root or root or ROOT
    if git(root, "rev-parse", "--verify", "--quiet", f"{args.ref}^{{commit}}").returncode != 0:
        print(f"needs_audit: '{args.ref}' is not a commit of {root}", file=sys.stderr)
        return 2
    result = assess(root, args.ref)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if result["audit_needed"] else 0
    text, maybe = result["text"], result["maybe"]
    if not text and not maybe:
        print(f"NO AUDIT NEEDED — nothing the model reads changed since {args.ref} "
              f"({result['changed_files']} file(s) changed in all).")
        return 0
    if text:
        print(f"AUDIT NEEDED (smoke tier) — {len(text)} file(s) the model reads changed since {args.ref}:")
        for line in text:
            print(f"  {line}")
    if maybe:
        head = "MAYBE" if text else f"AUDIT MAYBE NEEDED since {args.ref}"
        print(f"{head} — hook files whose own strings reach the model (read the diff: words or only logic?):")
        for line in maybe:
            print(f"  {line}")
    print("next: python3 evals/run_audit_scenarios.py --tier smoke --out evals/baseline/@env/audit-<ref>.json"
          "   (the full tier only before a version tag)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
