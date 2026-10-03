#!/usr/bin/env python3
"""gate_allows.py — every gate exemption a slice's diff adds, laid in front of the overseer.

    python3 .claude/hooks/gate_allows.py            # the list as text; nothing when there is none
    python3 .claude/hooks/gate_allows.py --json     # {"base": ..., "allows": [...]}
    python3 .claude/hooks/gate_allows.py --base REF # diff against REF instead of the slice's base

WHY. The bypass guard of gate.py lets a suppression through when a `gate-allow: <reason>` stands
next to it, and all it can check of the reason is its shape (12 characters, two words). Whether
the reason is TRUE is a judgement, and until package costs nobody who judges ever saw it: an
agent passed the gate by typing any sentence. This script is the deterministic half of the fix —
it collects, it does not judge. `overseer_stop.py` puts its list into OVERSEER_REQUEST, and the
overseer skill tells an overseer asked by hand to run it; the overseer judges every reason.

WHAT COUNTS. Lines the diff ADDS (working tree + index + untracked files against the base):
  code      in a .py file, a COMMENT token carrying the marker — a string or a docstring that
            mentions it is not an exemption. `what` is the suppression it stands beside
            (type-ignore, noqa, skip, xfail), on its own line or the line below a comment line.
  config    an added line of pyproject.toml / ruff.toml / mypy.ini / .claude/project.env.
  contract  an added suppression (or a changed config file) that carries no marker of its own
            and passes the gate because a SEALED slice contract grants its kind: listed at the
            line that uses the grant, with the contract's reason. Also any marker line a
            contract gains in the diff.
A marker with no reason at all is listed too (`reason` empty); `reason_ok` says whether gate.py
would accept the reason's shape.

NEW MEANS NOT YET JUDGED. A checkpoint commit must not hide an exemption from the overseer, so
the base is not HEAD. In order: `--base REF`; the commit recorded at the last ACCEPTED
OVERSEER_PASS (overseer_stop.py calls `record_pass`, state in
.claude/state/overseer/gate-allows-judged.json); the `base_commit` the active slice contract
names; the merge-base with the main branch; HEAD. Exemptions that were in front of the overseer
at an accepted PASS are remembered by fingerprint (file, kind, reason) and not listed again;
`--all` lists them too. Exit 0 always — except 2 for a base that is not a commit.

Standard library only; imports gate.py so the two can never disagree about a diff or a reason.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import gate

# Looser than gate.ALLOW_RE on purpose: a marker with an empty reason must be SEEN here.
MARKER_RE = re.compile(r"gate-allow:[ \t]*(?P<reason>.*)", re.IGNORECASE)
CONTRACT_LINE_RE = re.compile(
    r"^\s*gate-allow:\s*(?P<what>[\w./-]+)\s+[—–-]+\s*(?P<reason>.*)$", re.IGNORECASE
)
BASE_COMMIT_RE = re.compile(r"^\s*base_commit:\s*`?([0-9a-fA-F]{7,40})`?\s*$", re.MULTILINE)
SLICES_PREFIX = ".engine/slices/"
UNATTACHED = "nothing beside it"
JUDGED_REL = Path(".claude/state/overseer/gate-allows-judged.json")
MAIN_BRANCHES = ("origin/main", "main", "origin/master", "master")
JUDGED_CAP = 5000
HEADER = (
    "GATE-ALLOW REVIEW — the slice's diff adds {n} gate exemption(s). The gate checked only the "
    "shape of each reason; whether it is true is yours to judge (overseer check #4: a silenced "
    "check is a masked gap). For EACH one, open the line. A reason is weak when it only says the "
    "check was in the way (\"to make mypy pass\", \"temporary\", \"for now\", \"legacy\"), restates "
    "what the suppression does, or names no cause that makes the check wrong at THIS line. A weak "
    "or missing reason is `OVERSEER_BLOCK: #4 masked gap — gate-allow at <file>:<line>: <what is "
    "missing>`; the ledger entry names every exemption you judged."
)


@dataclass
class Allow:
    file: str
    line: int
    source: str
    what: str
    reason: str
    reason_ok: bool

    @property
    def fingerprint(self) -> str:
        key = f"{self.file}\x1f{self.source}\x1f{self.what}\x1f{self.reason}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def clean(reason: str) -> str:
    return reason.strip().rstrip("`").strip()


def changed_since(root: Path, base: str) -> list[str]:
    names: set[str] = set()
    names.update(gate.lines_of(gate.git(root, "diff", "--name-only", "--diff-filter=ACMR", base)))
    names.update(gate.lines_of(gate.git(root, "diff", "--name-only", "--cached", "--diff-filter=ACMR", base)))
    names.update(gate.lines_of(gate.git(root, "ls-files", "--others", "--exclude-standard")))
    return sorted(n for n in names if (root / n).is_file())


def added_since(root: Path, rel: str, base: str) -> set[int] | None:
    """Line numbers the diff against `base` adds to `rel`; None = every line (no version at base)."""
    if gate.git(root, "cat-file", "-e", f"{base}:{rel}").returncode != 0:
        return None
    out = gate.git(root, "diff", base, "-U0", "--no-color", "--", rel)
    if out.returncode != 0:
        return None
    added: set[int] = set()
    for hunk in gate.HUNK_RE.finditer(out.stdout):
        start = int(hunk.group("start"))
        count = 1 if hunk.group("count") is None else int(hunk.group("count"))
        added.update(range(start, start + count))
    return added


def suppressions_by_line(text: str, comments: dict[int, str]) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    for line, comment in comments.items():
        for kind, pattern in gate.SUPPRESSIONS:
            if pattern.search(comment):
                found.setdefault(line, []).append(kind)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and gate.dotted(node) in gate.SKIP_NAMES:
            kind = gate.SKIP_NAMES[gate.dotted(node)]
            if kind not in found.setdefault(node.lineno, []):
                found[node.lineno].append(kind)
    return found


def from_python(rel: str, text: str, added: set[int] | None, grants: dict[str, tuple[str, str]]) -> list[Allow]:
    comments = gate.comment_map(text)
    if comments is None:
        return []
    source_lines = text.splitlines()
    beside = suppressions_by_line(text, comments)

    def comment_only(line: int) -> bool:
        return 1 <= line <= len(source_lines) and source_lines[line - 1].lstrip().startswith("#")

    allows: list[Allow] = []
    marked: set[int] = set()
    for line in sorted(comments):
        match = MARKER_RE.search(comments[line])
        if not match:
            continue
        target = line if beside.get(line) or not comment_only(line) else line + 1
        marked.add(target)
        if added is not None and line not in added:
            continue
        reason = clean(match["reason"])
        kinds = "+".join(beside.get(target, [])) or UNATTACHED
        allows.append(Allow(rel, line, "code", kinds, reason, gate.valid_reason(reason)))
    # A suppression with no marker of its own that the gate lets through on a contract's grant.
    for line in sorted(beside):
        if line in marked or (added is not None and line not in added):
            continue
        for kind in beside[line]:
            if kind in grants:
                name, reason = grants[kind]
                allows.append(Allow(rel, line, "contract", f"{kind} (granted by {name})", reason, True))
    return sorted(allows, key=lambda a: a.line)


def from_lines(rel: str, text: str, added: set[int] | None, source: str) -> list[Allow]:
    allows: list[Allow] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if added is not None and number not in added:
            continue
        match = MARKER_RE.search(line)
        if not match:
            continue
        what, reason = "config", clean(match["reason"])
        if source == "contract":
            granted = CONTRACT_LINE_RE.match(line)
            what = granted["what"].lower() if granted else "?"
            reason = clean(granted["reason"]) if granted else reason
        allows.append(Allow(rel, number, source, what, reason, gate.valid_reason(reason)))
    return allows


def is_commit(root: Path, ref: str) -> bool:
    return gate.git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}").returncode == 0


def read_judged(root: Path) -> tuple[str, set[str]]:
    """(commit of the last accepted PASS, fingerprints judged so far); ("", empty) when none."""
    try:
        data = json.loads((root / JUDGED_REL).read_text(encoding="utf-8"))
        return str(data.get("commit", "")), {str(x) for x in data.get("judged", [])}
    except (OSError, ValueError, AttributeError, TypeError):
        return "", set()


def default_base(root: Path) -> str:
    """Where "not yet judged" starts: the last accepted PASS, else the slice's base_commit, else
    the point this branch left the main one, else HEAD."""
    commit, _ = read_judged(root)
    if commit and is_commit(root, commit):
        return commit
    slug = gate.active_slice(root)
    if slug:
        try:
            text = (root / ".engine" / "slices" / f"{slug}.md").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        named = BASE_COMMIT_RE.search(text)
        if named and is_commit(root, named.group(1)):
            return named.group(1)
    for branch in MAIN_BRANCHES:
        if is_commit(root, branch):
            merge = gate.git(root, "merge-base", "HEAD", branch).stdout.strip()
            if merge:
                return merge
    return "HEAD"


def collect(root: Path, base: str | None = None, include_judged: bool = False) -> list[Allow]:
    """Every gate exemption the diff against the base adds and no accepted PASS has seen.
    Raises ValueError for a base that is no commit."""
    if not gate.has_head(root):
        return []
    ref = base or default_base(root)
    if not is_commit(root, ref):
        raise ValueError(f"base '{ref}' is not a commit in this repository")
    grants = gate.contract_grants(root)
    allows: list[Allow] = []
    for rel in changed_since(root, ref):
        is_contract = rel.startswith(SLICES_PREFIX) and rel.endswith(".md")
        if not (rel.endswith(".py") or gate.is_config_file(rel) or is_contract):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        added = added_since(root, rel, ref)
        if rel.endswith(".py"):
            allows.extend(from_python(rel, text, added, grants))
            continue
        found = from_lines(rel, text, added, "contract" if is_contract else "config")
        if not found and not is_contract:
            grant = grants.get(rel.lower()) or grants.get(Path(rel).name.lower())
            if grant:
                found = [Allow(rel, 1, "contract", f"config change (granted by {grant[0]})", grant[1], True)]
        allows.extend(found)
    if include_judged or base:
        return allows
    _, judged = read_judged(root)
    return [a for a in allows if a.fingerprint not in judged]


def record_pass(root: Path) -> None:
    """Called by overseer_stop.py when it ACCEPTS an OVERSEER_PASS: what the diff holds now has
    been in front of the overseer, and the next unit's diff starts at this commit."""
    commit, judged = read_judged(root)
    try:
        judged |= {a.fingerprint for a in collect(root, include_judged=True)}
    except ValueError:
        pass
    head = gate.git(root, "rev-parse", "-q", "--verify", "HEAD").stdout.strip()
    gate.write_json(root / JUDGED_REL, {"commit": head or commit, "judged": sorted(judged)[-JUDGED_CAP:],
                                        "updated_utc": gate.utc_now()})


def render(allows: list[Allow]) -> str:
    """The list as the overseer reads it; the empty string when there is nothing to judge."""
    if not allows:
        return ""
    lines = [HEADER.format(n=len(allows))]
    for number, allow in enumerate(allows, start=1):
        if not allow.reason:
            reason = "MISSING"
        elif allow.reason_ok:
            reason = f'"{allow.reason}"'
        else:
            reason = f'"{allow.reason}" (too short for the gate itself)'
        lines.append(f"  {number}. {allow.file}:{allow.line} [{allow.source}: {allow.what}] reason: {reason}")
    return "\n".join(lines)


def unit_files(root: Path) -> set[str]:
    """Files changed since the base — the range the next verdict speaks for."""
    if not gate.has_head(root):
        return set()
    base = default_base(root)
    return set(changed_since(root, base)) if is_commit(root, base) else set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--base", default=None, help="diff base (default: see NEW MEANS NOT YET JUDGED)")
    parser.add_argument("--all", action="store_true", help="also list exemptions an accepted PASS has already seen")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    root = gate.project_root()
    try:
        allows = collect(root, args.base, include_judged=args.all)
    except ValueError as exc:
        print(f"gate_allows: {exc}", file=sys.stderr)
        return 2
    if args.json:
        payload = {"base": args.base or default_base(root), "allows": [asdict(a) for a in allows]}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif allows:
        print(render(allows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
