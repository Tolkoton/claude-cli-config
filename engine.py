#!/usr/bin/env python3
"""Install, update and inspect the engine in a project — from ONE git ref of this repository.

    engine.py install <project> [--ref REF] [--dry-run] [--reseed-pristine] [--take PATH] [--no-register]
    engine.py install --personal [--ref REF] [--dry-run] [--home DIR]
    engine.py update  <project> [--ref REF] [--dry-run] [--reseed-pristine] [--take PATH]
    engine.py update  --all     [--ref REF] [--dry-run] [--reseed-pristine]
    engine.py status  [<project>] [--ref REF]
    engine.py release <version> --owner-approved [--baseline FILE] [--remote NAME] [--message TEXT]

REF defaults to the newest `v*` tag. Files are read from the ref with git, never from the
working tree, so an install can be repeated byte for byte. `.claude/ownership.txt` in that
ref says who owns every path:

  engine   copied into the project; later replaced only while the project has not changed it
  project  never overwritten; a `seed=` creates the file once when the project lacks it
  machine  never shipped; its patterns go into a marked block of the project's .gitignore
  user     the owner's own: personal skills and `user/settings.json`, the personal settings
           layer. `install --personal` merges that layer into the home settings file
           (`~/.claude/settings.json`, or `$CLAUDE_CONFIG_DIR/settings.json`, or --home):
           keys the layer names are set, lists gain the entries they lack, every key the
           file already has and the layer does not name is kept, a backup is written next
           to the file before it changes, and a second run changes nothing. A layer that
           wires hooks is refused: a hook wired at the user level AND in a project fires
           twice per event.

The project keeps `.claude/engine-lock.json`: the ref, the commit and the git blob id of every
engine file as installed. That is how an update tells "unchanged since install" (replace it)
from "edited here" (report it, keep it). One exception to "keep it": a kept `.claude/settings.json`
gains the overseer's two handlers when it lacks them (`wire` in the report names each one) — the
audit runs through them and through nothing else; a file that is not readable JSON is left alone
and the report carries the text to add. The settings proposal `docs/tasks/settings.json` is the
project's: created once as a copy of the project's own live settings, and kept identical to them
(`follow`) only while it was identical before the run — a proposal that differs is never touched.
A project copied by hand before this installer existed
has no lock; then each file is compared with every version the engine ever had at that path —
any match is an untouched engine file (replace it), no match is an edit (keep it).

A project's CLAUDE.md starts from the seed in templates/project/: a marked block
(`<!-- >>> engine: ... -->` ... `<!-- <<< engine -->`) holding the import of the engine's
standing rules, then the project's own text. engine.py rewrites what is between the markers
when the ref's seed block differs, and never a byte outside them. An older project whose
CLAUDE.md still holds the rules inline is reported: an unedited copy is replaced by the seed
with --reseed-pristine; an edited one is left alone and the report names the import line to
add and the line ranges that now duplicate .claude/engine-rules.md.

`release` is the owner's command and the only one that pushes (docs/release.md): on a clean work
tree with green suites and a golden set identical to its baseline it tags HEAD with the version
and moves `main` and `stable` onto it, fast-forward only. Without --owner-approved, or inside a
Claude Code session, it does nothing.

engine.py never commits and never touches a file it does not own: review with `git status`.
Exit status: 0 done, 1 done but some engine files were held back (see "keep"), 2 error.

Standard library only. Where the engine lives is known to this file alone: it finds its own
repository relative to itself, and the project from the command line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

OWNERSHIP = ".claude/ownership.txt"
LOCK = ".claude/engine-lock.json"
PERSONAL = "user/settings.json"
HOME_SETTINGS = "settings.json"
BACKUP_PREFIX = "settings.json.engine-backup-"
OWNERS = ("engine", "project", "machine", "user")
LOCK_SCHEMA = 1
BLOCK_BEGIN = "# >>> engine: machine state — written by engine.py from .claude/ownership.txt; edit it there"
BLOCK_END = "# <<< engine"
EXIT_OK, EXIT_ATTENTION, EXIT_ERROR = 0, 1, 2
FILE_MODES = ("100644", "100755")
WRITING_VERBS = ("add", "update", "seed", "reseed")
# The marked block in a project's CLAUDE.md (package 2b). Between the markers stands the
# engine's text — today one line, `@.claude/engine-rules.md`, the import of the standing rules.
# engine.py rewrites what is between the markers when the ref's seed block differs, and never
# a byte outside them: everything below the end marker is the project's own.
MD_BLOCK_BEGIN = "<!-- >>> engine:"
MD_BLOCK_END = "<!-- <<< engine -->"
RULES_IMPORT = "@.claude/engine-rules.md"
RULES_FILE = ".claude/engine-rules.md"
# A run of at least this many consecutive non-blank lines found verbatim in some version of the
# engine's own CLAUDE.md (or of the seed) is reported as duplicated engine text.
DUPLICATE_RUN_MIN = 3

# Where a project's own data used to live before package 3c, and where it lives now. `update`
# (and `install` on a copy without a lock) MOVES each old path that exists to its new place —
# file by file for a directory — when the ref's ownership map knows the new layout. A file
# present in BOTH places is left alone and reported: the engine does not merge a project's
# records. The old paths stay `project`-owned in the map so nothing else ever touches them.
MIGRATIONS: tuple[tuple[str, str], ...] = (
    (".claude/overseer/ledger.md", ".engine/overseer/ledger.md"),
    (".claude/overseer/audit.md", ".engine/overseer/audit.md"),
    (".claude/overseer/escalations.md", ".engine/overseer/escalations.md"),
    (".claude/overseer/parked.md", ".engine/overseer/parked.md"),
    (".claude/overseer/MEMORY.md", ".engine/overseer/MEMORY.md"),
    (".claude/overseer/slice/", ".engine/slices/"),
    (".claude/architecture/", ".engine/architecture/"),
    (".claude/premises/", ".engine/premises/"),
    (".claude/artifacts/", ".engine/artifacts/"),
    ("PROGRESS.md", ".engine/PROGRESS.md"),
)
# Machine state moved the same way (package 3c put it under .claude/state/). A pattern entry
# (`*` in the old path) moves every match into the new directory under its own name. State is
# NOT moved while the unattended supervisor appears to be running — see supervisor_live().
STATE_MIGRATIONS: tuple[tuple[str, str], ...] = (
    (".claude/overseer/mode", ".claude/state/overseer/mode"),
    (".claude/overseer/state", ".claude/state/overseer/state"),
    (".claude/overseer/.last_audit_sha", ".claude/state/overseer/.last_audit_sha"),
    (".claude/overseer/.last_continue_sha", ".claude/state/overseer/.last_continue_sha"),
    (".claude/overseer/.continue_count", ".claude/state/overseer/.continue_count"),
    (".claude/overseer/.budget-*.json", ".claude/state/overseer/"),
    (".claude/overseer/complexity-report.md", ".claude/state/overseer/complexity-report.md"),
    (".claude/unattended/state.json", ".claude/state/unattended/state.json"),
    (".claude/unattended/cost.json", ".claude/state/unattended/cost.json"),
    (".claude/unattended/heartbeat", ".claude/state/unattended/heartbeat"),
    (".claude/unattended/restarts.log", ".claude/state/unattended/restarts.log"),
    (".claude/unattended/sim-plan.txt", ".claude/state/unattended/sim-plan.txt"),
    (".claude/unattended/supervisor.lock", ".claude/state/unattended/supervisor.lock"),
    (".claude/unattended/logs/", ".claude/state/unattended/logs/"),
    (".claude/unattended/archive/", ".claude/state/unattended/archive/"),
)
# The harness's stall timeout (config.sh STALL_TIMEOUT_SEC default): a heartbeat younger than
# this means a session may be writing state right now.
STALL_TIMEOUT_S = 900
# A release (docs/release.md). The branches that follow every release, the two checks it runs in
# the repository being released, and where the golden set's baselines live.
RELEASE_BRANCHES = ("main", "stable")
RELEASE_VERSION = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
RELEASE_TESTS = ("bash", "tests/run_all.sh")
RELEASE_GOLDEN = "evals/run_hook_scenarios.py"
RELEASE_BASELINES = "evals/baseline/*/results-*.json"
RELEASE_ENVIRONMENT = "evals/environment.py"
# The overseer's handlers (board 033). Every audit is done by the agent `overseer` and recorded by
# this script, which works only through its handlers in the project's settings file; the Stop hook
# has no other way to audit. A project that edited its settings keeps its file, so the handlers it
# lacks are ADDED to it — the one thing engine.py writes into an engine file the project changed.
SETTINGS = ".claude/settings.json"
SETTINGS_LOCAL = ".claude/settings.local.json"
OVERSEER_SCRIPT = "overseer_verdict.py"
# The settings proposal (board 038). An agent may not edit the settings file; it proposes the whole
# file here and the owner's «так» has the board runner copy it over the live one. A project gets
# the proposal as a copy of ITS OWN live settings — nothing is proposed yet — and a proposal that
# is identical to the live file stays identical when an update changes that file.
PROPOSAL = "docs/tasks/settings.json"
SUPERVISOR_STOP_FIRST = "unattended supervisor appears live ({why}): stop it first; the state is not moved"


def legacy_path_of(path: str) -> str | None:
    """The pre-3c path a new-layout path was moved from, or None."""
    for old, new in MIGRATIONS + STATE_MIGRATIONS:
        if "*" in old:
            continue
        if new.endswith("/") and path.startswith(new):
            return old + path[len(new) :]
        if path == new:
            return old
    return None


def supervisor_live(project: Path) -> str | None:
    """Why the unattended supervisor seems to be running — a lock, or a fresh heartbeat — else None."""
    for lock in (project / ".claude/unattended/supervisor.lock", project / ".claude/state/unattended/supervisor.lock"):
        if lock.exists():
            return f"{lock.relative_to(project).as_posix()} exists"
    for beat in (project / ".claude/unattended/heartbeat", project / ".claude/state/unattended/heartbeat"):
        try:
            age = datetime.now(timezone.utc).timestamp() - beat.stat().st_mtime
        except OSError:
            continue
        if age < STALL_TIMEOUT_S:
            return f"{beat.relative_to(project).as_posix()} is {int(age)} s old"
    return None


def migration_pairs(project: Path, old: str, new: str) -> list[tuple[str, str]]:
    """(old path, new path) for everything an entry of a migration table covers right now."""
    source = project / old
    if "*" in old:
        parent = source.parent
        if not parent.is_dir():
            return []
        return [(old.rsplit("/", 1)[0] + "/" + p.name, new + p.name) for p in sorted(parent.glob(source.name)) if p.is_file() and not p.is_symlink()]
    if old.endswith("/"):
        if not source.is_dir() or source.is_symlink():
            return []
        files = sorted(p for p in source.rglob("*") if p.is_file() and not p.is_symlink())
        return [(old + p.relative_to(source).as_posix(), new + p.relative_to(source).as_posix()) for p in files]
    if not source.is_file() or source.is_symlink():
        return []
    return [(old, new)]


def plan_migration(project: Path, table: tuple[tuple[str, str], ...] = MIGRATIONS) -> tuple[list[Action], set[str]]:
    """Moves for every old path that exists; conflicts as `keep`. Returns (actions, new paths)."""
    actions: list[Action] = []
    targets: set[str] = set()
    for old, new in table:
        pairs = migration_pairs(project, old, new)
        if not pairs:
            continue
        for old_rel, new_rel in pairs:
            if (project / new_rel).exists():
                actions.append(Action("keep", old_rel, f"exists in both places ({new_rel} too); nothing touched — merge by hand"))
            else:
                actions.append(Action("move", old_rel, f"-> {new_rel}"))
                targets.add(new_rel)
    return actions, targets


def apply_migration(project: Path, actions: list[Action]) -> None:
    for action in actions:
        if action.verb != "move":
            continue
        new_rel = action.detail[len("-> ") :]
        target = project / new_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(project / action.path, target)


def prune_old_dirs(project: Path) -> None:
    """An old directory emptied by the moves (and by a retired engine file leaving it) goes
    too, deepest first; one with anything left in it stays."""
    roots = {project / old.rstrip("/") if old.endswith("/") else (project / old).parent for old, _new in MIGRATIONS + STATE_MIGRATIONS}
    for root in sorted(roots, key=lambda p: -len(p.parts)):
        if root == project or not root.is_dir() or root.is_symlink():
            continue
        for folder in sorted((d for d in root.rglob("*") if d.is_dir()), key=lambda p: -len(p.parts)):
            if not any(folder.iterdir()):
                folder.rmdir()
        if not any(root.iterdir()):
            root.rmdir()


class EngineError(Exception):
    """A condition the user has to fix. Printed without a traceback, exit status 2."""


# --- the marked block and the duplicate-text report (CLAUDE.md, AGENTS.md) ----------------


def marked_block(lines: list[str]) -> tuple[int, int] | None:
    """(begin, end) line indexes of the engine's marked block, or None when a marker is missing."""
    begin = next((i for i, line in enumerate(lines) if line.startswith(MD_BLOCK_BEGIN)), None)
    end = next((i for i, line in enumerate(lines) if line.strip() == MD_BLOCK_END), None)
    if begin is None or end is None or end <= begin:
        return None
    return begin, end


def with_block_from(project_text: str, seed_text: str) -> str | None:
    """The project's text with the engine's block replaced by the seed's; None when nothing
    changes or either side lacks a complete block."""
    own, seed = project_text.splitlines(), seed_text.splitlines()
    own_block, seed_block = marked_block(own), marked_block(seed)
    if own_block is None or seed_block is None:
        return None
    (ob, oe), (sb, se) = own_block, seed_block
    if own[ob : oe + 1] == seed[sb : se + 1]:
        return None
    merged = own[:ob] + seed[sb : se + 1] + own[oe + 1 :]
    return "\n".join(merged) + ("\n" if project_text.endswith("\n") else "")


def duplicated_runs(project_text: str, engine_texts: list[str]) -> list[tuple[int, int, str]]:
    """(first line, last line, label) of every run of >= DUPLICATE_RUN_MIN consecutive non-blank
    lines of the project's file that occur verbatim (trailing whitespace ignored) in some version
    of the engine's own file. Blank lines inside a run are neutral; an import line (`@path`) ends
    a run — it is the project's wiring, not the engine's text. Line numbers are 1-based."""
    known: set[str] = set()
    for text in engine_texts:
        known.update(line.rstrip() for line in text.splitlines() if line.strip() and not line.startswith("@"))

    def neutral(line: str) -> bool:
        return not line.strip() or re.fullmatch(r"\|[-:| ]+\|", line.strip()) is not None
    runs: list[tuple[int, int, str]] = []
    start: int | None = None
    last = 0
    count = 0
    lines = project_text.splitlines()

    def close() -> None:
        nonlocal start, count
        if start is not None and count >= DUPLICATE_RUN_MIN:
            label = next((line.strip() for line in lines[start - 1 : last] if line.startswith("#")), lines[start - 1].strip())
            runs.append((start, last, label[:60]))
        start, count = None, 0

    for number, line in enumerate(lines, 1):
        if neutral(line):
            continue
        if line.rstrip() in known:
            if start is None:
                start = number
            last = number
            count += 1
        else:
            close()
    close()
    return runs


def format_ranges(runs: list[tuple[int, int, str]]) -> str:
    return ", ".join(f"lines {a}\u2013{b} ({label})" for a, b, label in runs)


# --- ownership ---------------------------------------------------------------------------


def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Anchored glob: `*` inside one directory, `**` across directories, trailing `/` = subtree."""
    if pattern.startswith(("/", "!")) or "\\" in pattern:
        raise EngineError(f"pattern {pattern!r}: write it relative to the root, without '/', '!' or '\\'")
    subtree = pattern.endswith("/")
    body = pattern.rstrip("/")
    out: list[str] = []
    i = 0
    while i < len(body):
        if body.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif body.startswith("**", i):
            out.append(".*")
            i += 2
        elif body[i] == "*":
            out.append("[^/]*")
            i += 1
        elif body[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(body[i]))
            i += 1
    return re.compile(r"\A" + "".join(out) + (r"/.*" if subtree else "") + r"\Z")


@dataclass(frozen=True)
class Rule:
    owner: str
    pattern: str
    seed: str | None
    line: int
    regex: re.Pattern[str]


def parse_ownership(text: str) -> list[Rule]:
    rules: list[Rule] = []
    for number, raw in enumerate(text.splitlines(), 1):
        fields = raw.split("#", 1)[0].split()
        if not fields:
            continue
        where = f"{OWNERSHIP}:{number}"
        if len(fields) not in (2, 3):
            raise EngineError(f"{where}: expected '<owner> <pattern> [seed=<file>]'")
        owner, pattern = fields[0], fields[1]
        if owner not in OWNERS:
            raise EngineError(f"{where}: unknown owner {owner!r} (one of {', '.join(OWNERS)})")
        seed: str | None = None
        if len(fields) == 3:
            if not fields[2].startswith("seed=") or len(fields[2]) == len("seed="):
                raise EngineError(f"{where}: the third field must be seed=<file>")
            if owner != "project":
                raise EngineError(f"{where}: only project files have a seed")
            if any(c in pattern for c in "*?") or pattern.endswith("/"):
                raise EngineError(f"{where}: a seeded rule must name exactly one file")
            seed = fields[2][len("seed=") :]
        rules.append(Rule(owner, pattern, seed, number, compile_pattern(pattern)))
    if not rules:
        raise EngineError(f"{OWNERSHIP} has no rules")
    return rules


def owner_of(rules: list[Rule], path: str) -> str | None:
    """The owner from the FIRST matching rule; None when no rule matches (never shipped)."""
    for rule in rules:
        if rule.regex.match(path):
            return rule.owner
    return None


# --- git ----------------------------------------------------------------------------------


def git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    proc = subprocess.run(["git", "-C", str(repo), *args], input=stdin, capture_output=True, check=False)
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", "replace").strip()
        raise EngineError(f"git {' '.join(args[:3])} failed in {repo}: {message}")
    return proc.stdout


def is_git_work_tree(path: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


@dataclass(frozen=True)
class Entry:
    mode: str
    blob: str


class EngineSource:
    """This repository, read through git: trees, blobs and the full history of every path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.algorithm = git(root, "rev-parse", "--show-object-format").decode().strip() or "sha1"
        self._history: dict[str, set[str]] | None = None

    @classmethod
    def here(cls) -> EngineSource:
        top = git(Path(__file__).resolve().parent, "rev-parse", "--show-toplevel").decode().strip()
        return cls(Path(top))

    def resolve(self, ref: str) -> str:
        try:
            return git(self.root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").decode().strip()
        except EngineError:
            raise EngineError(f"{ref!r} is not a tag, branch or commit of {self.root}") from None

    def newest_tag(self) -> str | None:
        tags = git(self.root, "tag", "--list", "v*", "--sort=-v:refname").decode().split()
        return tags[0] if tags else None

    def is_ancestor(self, older: str, newer: str) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(self.root), "merge-base", "--is-ancestor", older, newer],
            capture_output=True,
            check=False,
        )
        return proc.returncode == 0

    def tree(self, commit: str) -> dict[str, Entry]:
        entries: dict[str, Entry] = {}
        for record in git(self.root, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
            if record:
                meta, path = record.split(b"\t", 1)
                mode, _kind, blob = meta.decode().split()
                entries[path.decode("utf-8")] = Entry(mode, blob)
        return entries

    def show(self, commit: str, path: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "blob", f"{commit}:{path}"],
            capture_output=True,
            check=False,
        )
        return proc.stdout if proc.returncode == 0 else None

    def read(self, blobs: set[str]) -> dict[str, bytes]:
        """Many blobs in one `git cat-file --batch` call."""
        ordered = sorted(blobs)
        if not ordered:
            return {}
        out = git(self.root, "cat-file", "--batch", stdin=("\n".join(ordered) + "\n").encode())
        contents: dict[str, bytes] = {}
        pos = 0
        for _ in ordered:
            newline = out.index(b"\n", pos)
            header = out[pos:newline].decode().split()
            if len(header) != 3 or header[1] != "blob":
                raise EngineError(f"unexpected object in the engine repository: {' '.join(header)}")
            start = newline + 1
            size = int(header[2])
            contents[header[0]] = out[start : start + size]
            pos = start + size + 1
        return contents

    def history(self) -> dict[str, set[str]]:
        """Every blob id each path ever had, on every ref of this repository."""
        if self._history is None:
            raw = git(self.root, "log", "--all", "-m", "--raw", "--no-abbrev", "--no-renames", "--format=", "-z")
            seen: dict[str, set[str]] = {}
            tokens = raw.split(b"\0")
            i = 0
            while i < len(tokens):
                token = tokens[i].lstrip(b"\n")
                if token.startswith(b":") and i + 1 < len(tokens):
                    fields = token[1:].decode().split()
                    path = tokens[i + 1].decode("utf-8")
                    for blob in fields[2:4]:
                        if blob.strip("0"):
                            seen.setdefault(path, set()).add(blob)
                    i += 2
                else:
                    i += 1
            self._history = seen
        return self._history

    def blob_id(self, data: bytes) -> str:
        digest = hashlib.new(self.algorithm)
        digest.update(b"blob %d\0" % len(data))
        digest.update(data)
        return digest.hexdigest()

    def file_ids(self, path: Path) -> set[str]:
        """The blob id of a project file — and of its LF form, so a CRLF checkout still matches."""
        data = path.read_bytes()
        ids = {self.blob_id(data)}
        if b"\r\n" in data:
            ids.add(self.blob_id(data.replace(b"\r\n", b"\n")))
        return ids


# --- the lock -----------------------------------------------------------------------------


@dataclass
class Lock:
    ref: str
    commit: str
    installed_utc: str
    files: dict[str, str]
    seeded: list[str]


def read_lock(project: Path) -> Lock | None:
    path = project / LOCK
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != LOCK_SCHEMA:
            raise EngineError(f"{path}: schema {data.get('schema')!r}, this engine.py reads {LOCK_SCHEMA}")
        files = {str(k): str(v) for k, v in dict(data["files"]).items()}
        seeded = [str(s) for s in list(data.get("seeded", []))]
        return Lock(str(data["ref"]), str(data["commit"]), str(data.get("installed_utc", "")), files, seeded)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise EngineError(
            f"{path} cannot be read ({exc}); restore it from git, or delete it to adopt the copy anew"
        ) from None


def render_lock(ref: str, commit: str, files: dict[str, str], seeded: list[str]) -> str:
    data = {
        "schema": LOCK_SCHEMA,
        "ref": ref,
        "commit": commit,
        "installed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": dict(sorted(files.items())),
        "seeded": sorted(seeded),
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# --- the .gitignore block -----------------------------------------------------------------


def gitignore_with_block(current: str | None, patterns: list[str]) -> str:
    block = [BLOCK_BEGIN, *patterns, BLOCK_END]
    lines = (current or "").splitlines()
    begin = next((i for i, line in enumerate(lines) if line.startswith("# >>> engine:")), None)
    end = next((i for i, line in enumerate(lines) if line == BLOCK_END), None)
    if begin is not None and end is not None and end > begin:
        lines[begin : end + 1] = block
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block)
    return "\n".join(lines) + "\n"


# --- the plan -----------------------------------------------------------------------------


@dataclass
class Action:
    verb: str  # add, update, chmod, keep, remove, seed, reseed, move, block, wire, follow
    path: str
    detail: str = ""
    blob: str = ""
    mode: str = ""


@dataclass
class Plan:
    project: Path
    ref: str
    commit: str
    lock: Lock | None
    actions: list[Action] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    unchanged: int = 0
    gitignore: str | None = None
    lock_text: str | None = None
    contents: dict[str, bytes] = field(default_factory=dict)

    @property
    def held_back(self) -> list[Action]:
        return [a for a in self.actions if a.verb == "keep"]


def check_project(src: EngineSource, project: Path) -> Path:
    if not project.is_dir():
        raise EngineError(f"{project} is not a directory")
    resolved = project.resolve()
    engine_root = src.root.resolve()
    if resolved == engine_root or engine_root in resolved.parents:
        raise EngineError(f"{resolved} is inside the engine repository; install into a project outside it")
    return resolved


def plan_sync(src: EngineSource, ref: str, project: Path, reseed_pristine: bool, take: set[str]) -> Plan:
    commit = src.resolve(ref)
    text = src.show(commit, OWNERSHIP)
    if text is None:
        raise EngineError(
            f"{ref} ({commit[:7]}) has no {OWNERSHIP}: it predates installation by engine.py. "
            "Pass --ref with a newer tag, branch or commit."
        )
    rules = parse_ownership(text.decode("utf-8"))
    tree = src.tree(commit)
    lock = read_lock(project)
    history = src.history()
    plan = Plan(project, ref, commit, lock)

    def owned(path: str) -> str | None:
        return owner_of(rules, path)

    # 0. The project's own data moves to where this ref keeps it — only when the ref's map knows
    #    the new layout, so a project updated to an OLDER engine is never half-migrated.
    migration_targets: set[str] = set()
    if any(r.pattern.startswith(".engine/") for r in rules):
        moves, migration_targets = plan_migration(project)
        plan.actions.extend(moves)
        # Machine state follows — unless a supervisor may be writing it this very moment.
        live = supervisor_live(project)
        state_moves, state_targets = plan_migration(project, STATE_MIGRATIONS)
        if live is None:
            plan.actions.extend(state_moves)
            migration_targets |= state_targets
        else:
            for action in state_moves:
                plan.actions.append(Action("keep", action.path, SUPERVISOR_STOP_FIRST.format(why=live)))

    shipped = {p: e for p, e in tree.items() if owned(p) == "engine" and p != LOCK}
    for path, entry in shipped.items():
        if entry.mode not in FILE_MODES:
            raise EngineError(f"{path} in {ref} has mode {entry.mode} (a symlink or submodule); only files ship")
    seeds = [(r.pattern, r.seed) for r in rules if r.seed is not None]
    for seed_target, seed in seeds:
        if seed not in tree:
            raise EngineError(f"seed {seed} (for {seed_target}) is missing from {ref}")
    base_files = dict(lock.files) if lock else {}
    retired = set(base_files) | {p for p in history if owned(p) == "engine" and p != LOCK}
    unknown_take = take - set(shipped) - retired
    if unknown_take:
        raise EngineError(f"--take names paths that are not engine files: {', '.join(sorted(unknown_take))}")

    new_files: dict[str, str] = {}
    blobs_needed: set[str] = set()

    # 1. Engine files of the ref.
    for path in sorted(shipped):
        entry = shipped[path]
        target = project / path
        base = base_files.get(path)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            plan.actions.append(Action("keep", path, "not a regular file in the project; left as it is"))
            continue
        if not target.exists():
            if base is not None and path not in take:
                plan.actions.append(Action("keep", path, "deleted in the project; the engine's copy is not restored"))
                new_files[path] = base
            else:
                plan.actions.append(Action("add", path, blob=entry.blob, mode=entry.mode))
                new_files[path] = entry.blob
                blobs_needed.add(entry.blob)
            continue
        ids = src.file_ids(target)
        if entry.blob in ids:
            new_files[path] = entry.blob
            if (entry.mode == "100755") != os.access(target, os.X_OK):
                plan.actions.append(Action("chmod", path, "executable bit as in the engine", mode=entry.mode))
            else:
                plan.unchanged += 1
            continue
        if path in take:
            reason = "taken over on request (--take)"
        elif base is not None and base in ids:
            reason = ""
        elif base is None and ids & history.get(path, set()):
            reason = "an older engine version, adopted"
        else:
            plan.actions.append(Action("keep", path, "edited in the project; the engine's version is not applied"))
            if base is not None:
                new_files[path] = base
            if path == SETTINGS:
                plan_wiring(src, plan, commit)
            continue
        plan.actions.append(Action("update", path, reason, blob=entry.blob, mode=entry.mode))
        new_files[path] = entry.blob
        blobs_needed.add(entry.blob)

    # 2. Engine files the engine no longer has: remove them where the project left them untouched.
    for path in sorted(retired - set(shipped)):
        target = project / path
        if not target.is_file() or target.is_symlink():
            continue
        known = set(history.get(path, set())) | ({base_files[path]} if path in base_files else set())
        if path in take or src.file_ids(target) & known:
            plan.actions.append(Action("remove", path, "retired by the engine"))
        else:
            plan.actions.append(Action("keep", path, "retired by the engine but edited in the project; left in place"))

    # 3. Project files that start from a seed — created once, never overwritten.
    seeded_before = set(lock.seeded) if lock else set()
    seeded = set(seeded_before)
    seeded_targets = {seed_target for seed_target, _ in seeds}
    for target_path, seed_path in seeds:
        target = project / target_path
        seed_entry = tree[seed_path]
        if target.is_file():
            ids = src.file_ids(target)
            # A record that MOVED here carries the history of its old path (package 3c), and a
            # file seeded from an older version of the seed is pristine too (package 2b).
            known_blobs = (
                history.get(target_path, set())
                | history.get(legacy_path_of(target_path) or "", set())
                | history.get(seed_path, set())
            )
            if seed_entry.blob in ids:
                continue
            if not ids & known_blobs:
                # Edited by the project: never touched outside the marked block. Report what the
                # project should do about engine text it still carries (package 2b, item 4).
                if target_path in ("CLAUDE.md", "AGENTS.md"):
                    plan_root_file(src, plan, history, target_path, seed_path, seed_entry, commit)
                continue
            if reseed_pristine:
                plan.actions.append(
                    Action(
                        "reseed",
                        target_path,
                        "an unedited copy of an older engine version; replaced by the seed",
                        blob=seed_entry.blob,
                        mode=seed_entry.mode,
                    )
                )
                blobs_needed.add(seed_entry.blob)
                seeded.add(target_path)
            else:
                what = (
                    "holds only the engine's own records from an old copy, nothing of this project"
                    if target_path.startswith(".engine/overseer/")
                    else "is an unedited copy of an older engine version"
                )
                plan.notes.append(f"{target_path} {what}; --reseed-pristine replaces it with the seed")
        elif target_path in migration_targets:
            continue  # the project's own record is about to arrive there; a seed would overwrite it
        elif not target.exists() and target_path not in seeded_before:
            plan.actions.append(
                Action("seed", target_path, f"from {seed_path}", blob=seed_entry.blob, mode=seed_entry.mode)
            )
            blobs_needed.add(seed_entry.blob)
            seeded.add(target_path)

    # 3b. The settings proposal follows the live settings file (when this ref's map knows it).
    if any(r.pattern == PROPOSAL and r.owner == "project" for r in rules):
        plan_proposal(src, plan, seeded_before, seeded)

    # 4. Reports only: the engine's own records left behind by an old copy, machine state in git.
    for path in sorted(history):
        if path in seeded_targets or owned(path) != "project" or not path.startswith(".claude/"):
            continue
        target = project / path
        if target.is_file() and not target.is_symlink() and src.file_ids(target) & history[path]:
            plan.notes.append(f"{path} is one of the engine's own records from an old copy; the project can delete it")
    if is_git_work_tree(project):
        tracked = git(project, "ls-files", "-z", "--", ".claude").split(b"\0")
        machine = sorted(p.decode("utf-8") for p in tracked if p and owned(p.decode("utf-8")) == "machine")
        if machine:
            plan.notes.append(
                f"{len(machine)} file(s) of machine state are tracked by git; untrack them with "
                f"`git rm -r --cached -- <path>`: {', '.join(machine)}"
            )

    # 5. The .gitignore block and the lock — rewritten only when they change.
    patterns = [r.pattern for r in rules if r.owner == "machine"]
    ignore_path = project / ".gitignore"
    current = ignore_path.read_text(encoding="utf-8") if ignore_path.is_file() else None
    wanted = gitignore_with_block(current, patterns)
    if wanted != current:
        plan.gitignore = wanted
    unchanged_lock = (
        lock is not None
        and lock.ref == ref
        and lock.commit == commit
        and lock.files == new_files
        and set(lock.seeded) == seeded
    )
    if not unchanged_lock or any(a.verb != "keep" for a in plan.actions):
        plan.lock_text = render_lock(ref, commit, new_files, sorted(seeded))
    if lock is not None and lock.commit != commit and src.is_ancestor(commit, lock.commit):
        plan.notes.append(f"this moves the project BACK from {lock.ref} ({lock.commit[:7]}) to an older engine")

    plan.contents = {**plan.contents, **src.read(blobs_needed)}  # keeps a rendered block (plan_root_file)
    return plan


def plan_root_file(src: EngineSource, plan: Plan, history: dict[str, set[str]], target_path: str,
                   seed_path: str, seed_entry: Entry, commit: str) -> None:
    """A project-edited CLAUDE.md or AGENTS.md: maintain the marked block, else report."""
    target = plan.project / target_path
    text = target.read_text(encoding="utf-8", errors="replace")
    seed_bytes = src.show(commit, seed_path) or b""
    seed_text = seed_bytes.decode("utf-8", "replace")
    lines = text.splitlines()
    has_begin = any(line.startswith(MD_BLOCK_BEGIN) for line in lines)
    has_end = any(line.strip() == MD_BLOCK_END for line in lines)
    if target_path == "CLAUDE.md" and (has_begin or has_end):
        if has_begin and has_end and marked_block(lines) is not None:
            merged = with_block_from(text, seed_text)
            if merged is not None:
                plan.actions.append(Action("block", target_path, "the engine's marked block updated to this ref's seed; text outside the markers untouched"))
                plan.contents["block:" + target_path] = merged.encode("utf-8")
            return
        plan.notes.append(
            f"{target_path}: the engine's block marker is incomplete "
            f"({'end' if has_begin else 'begin'} marker missing); left alone — restore "
            f"`{MD_BLOCK_END if has_begin else MD_BLOCK_BEGIN + ' ... -->'}` so engine.py can maintain the block"
        )
        return
    # An old copy, edited: which of its lines are the engine's text that now lives elsewhere?
    blobs = history.get(target_path, set()) | history.get(seed_path, set())
    engine_texts = [data.decode("utf-8", "replace") for data in src.read(blobs).values()]
    runs = duplicated_runs(text, engine_texts)
    if target_path == "CLAUDE.md":
        parts = []
        if RULES_IMPORT not in text:
            parts.append(f"add the line `{RULES_IMPORT}` inside a marked block (see {seed_path})")
        if runs:
            parts.append(f"delete {format_ranges(runs)} — they duplicate {RULES_FILE}")
        if parts:
            plan.notes.append(f"{target_path} is edited by the project and still carries the engine's old rules: " + "; ".join(parts))
    elif runs:
        plan.notes.append(
            f"{target_path} {format_ranges(runs)} are this repository's own text from an old seed; keep only what describes your project"
        )


def overseer_groups(settings: object) -> list[tuple[str, str, JsonObj]]:
    """(event, subcommand, hook group) for every handler in a settings object that runs the
    verdict script. The group holds that one handler only. Raises ValueError on a shape that is
    not Claude Code's (`hooks` an object of lists of groups)."""
    hooks = settings.get("hooks", {}) if isinstance(settings, dict) else None
    if not isinstance(hooks, dict):
        raise ValueError("`hooks` is not an object")
    found: list[tuple[str, str, JsonObj]] = []
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError(f"`hooks.{event}` is not a list")
        for group in groups:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list):
                raise ValueError(f"a group of `hooks.{event}` has no list of handlers")
            for handler in handlers:
                command = handler.get("command") if isinstance(handler, dict) else None
                if isinstance(command, str) and OVERSEER_SCRIPT in command:
                    subcommand = command.split(OVERSEER_SCRIPT, 1)[1].strip(" \"'")
                    found.append((str(event), subcommand, {**group, "hooks": [handler]}))
    return found


def plan_wiring(src: EngineSource, plan: Plan, commit: str) -> None:
    """The project keeps its own settings file: add the overseer's handlers it lacks, or — when the
    file cannot be read — report the exact text to add."""
    try:
        wanted = overseer_groups(json.loads(src.show(commit, SETTINGS) or b"{}"))
    except ValueError:
        return  # the ref's own settings are not ours to judge here
    if not wanted:
        return
    try:
        try:
            current = json.loads((plan.project / SETTINGS).read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"not valid JSON ({exc})") from None
        if not isinstance(current, dict):
            raise ValueError("it does not hold a JSON object")
        have = {(event, sub) for event, sub, _ in overseer_groups(current)}
    except (OSError, ValueError) as why:
        to_add: dict[str, list[JsonObj]] = {}
        for event, _, group in wanted:
            to_add.setdefault(event, []).append(group)
        plan.notes.append(
            f"{SETTINGS} is edited by the project and cannot be read ({why}), so the overseer's handlers were "
            "NOT added: until they are there no unit is audited. Fix the file and run the update again, or add "
            f"these groups under `hooks` by hand: {json.dumps(to_add, ensure_ascii=False)}"
        )
        return
    try:
        local = json.loads((plan.project / SETTINGS_LOCAL).read_text(encoding="utf-8"))
        have |= {(event, sub) for event, sub, _ in overseer_groups(local)}  # wired there too, it would fire twice
    except (OSError, ValueError):
        pass
    missing = [(event, group) for event, sub, group in wanted if (event, sub) not in have]
    if not missing:
        return
    hooks = current.setdefault("hooks", {})
    for event, group in missing:
        hooks.setdefault(event, []).append(group)
    added = "; ".join(f"{event} [{group.get('matcher', '')}] {group['hooks'][0]['command']}" for event, group in missing)
    plan.actions.append(Action("wire", SETTINGS, f"the overseer's handlers added to the project's own file: {added} — nothing else in it changed"))
    plan.contents["wire:" + SETTINGS] = (json.dumps(current, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def plan_proposal(src: EngineSource, plan: Plan, seeded_before: set[str], seeded: set[str]) -> None:
    """The settings proposal of a project. Missing: created once as a copy of the live settings
    file as this run leaves it, so nothing is proposed. Identical to the live file that this run
    changes: it follows. Different from it (something is proposed, or was proposed and never
    applied): never touched — a note says the live file moved under it."""
    live, target = plan.project / SETTINGS, plan.project / PROPOSAL
    before = live.read_bytes() if live.is_file() and not live.is_symlink() else None
    after = before
    for action in plan.actions:
        if action.path != SETTINGS:
            continue
        if action.verb == "wire":
            after = plan.contents["wire:" + SETTINGS]
        elif action.verb in ("add", "update"):
            after = src.read({action.blob})[action.blob]
    if after is None or target.is_symlink() or (target.exists() and not target.is_file()):
        return
    if not target.exists():
        if PROPOSAL in seeded_before:
            return  # created once; the project deleted it
        plan.contents["live:" + SETTINGS] = after
        plan.actions.append(Action("seed", PROPOSAL, f"a copy of the project's {SETTINGS}: nothing is proposed yet", blob="live:" + SETTINGS, mode="100644"))
        seeded.add(PROPOSAL)
        return
    if after == before:
        return
    if target.read_bytes() == before:
        plan.contents["follow:" + PROPOSAL] = after
        plan.actions.append(Action("follow", PROPOSAL, f"it was identical to {SETTINGS}, which this run changes; kept identical — nothing was proposed, nothing is"))
    else:
        plan.notes.append(
            f"{PROPOSAL} differs from {SETTINGS}, and this run changes {SETTINGS}: the proposal was written against the "
            "previous file and is left as it is. Bring the change into it before it is applied, or applying it undoes the update"
        )


def apply_plan(plan: Plan) -> None:
    apply_migration(plan.project, plan.actions)  # first: a seed or an add must never land on a moving file
    for action in plan.actions:
        target = plan.project / action.path
        if action.verb in ("block", "wire", "follow"):
            target.write_bytes(plan.contents[f"{action.verb}:{action.path}"])
            continue
        if action.verb in WRITING_VERBS:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                target.unlink()
            target.write_bytes(plan.contents[action.blob])
        if action.verb in (*WRITING_VERBS, "chmod"):
            current = target.stat().st_mode
            target.chmod(current | 0o111 if action.mode == "100755" else current & ~0o111)
        elif action.verb == "remove":
            target.unlink()
    if plan.gitignore is not None:
        (plan.project / ".gitignore").write_text(plan.gitignore, encoding="utf-8")
    if plan.lock_text is not None:
        lock_path = plan.project / LOCK
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(plan.lock_text, encoding="utf-8")
    if any(a.verb == "move" for a in plan.actions):
        prune_old_dirs(plan.project)


def print_plan(plan: Plan, dry_run: bool) -> None:
    for action in plan.actions:
        detail = f"  — {action.detail}" if action.detail else ""
        print(f"  {action.verb:<7} {action.path}{detail}")
    if plan.gitignore is not None:
        print("  ignore  .gitignore  — the machine-state block")
    if plan.lock_text is not None:
        print(f"  lock    {LOCK}")
    for note in plan.notes:
        print(f"  note    {note}")
    counts: dict[str, int] = {}
    for action in plan.actions:
        counts[action.verb] = counts.get(action.verb, 0) + 1
    parts = [f"{n} {verb}" for verb, n in sorted(counts.items())] + [f"{plan.unchanged} unchanged"]
    print(f"  total   {', '.join(parts)}{' — dry run, nothing written' if dry_run else ''}")
    if plan.held_back:
        print(
            "  Held back: the project changed these engine files. Review each one; "
            "`--take <path>` applies the engine's version."
        )


# --- the personal layer -------------------------------------------------------------------

JsonObj = dict[str, object]


@dataclass
class PersonalPlan:
    target: Path
    merged: JsonObj
    actions: list[Action] = field(default_factory=list)
    unchanged: int = 0

    @property
    def changes(self) -> bool:
        return bool(self.actions)


def config_home(explicit: str | None) -> Path:
    """--home, else Claude Code's own override CLAUDE_CONFIG_DIR, else ~/.claude."""
    if explicit:
        return Path(explicit).expanduser()
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude"


def read_json_object(path: Path, what: str) -> JsonObj:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EngineError(f"{what} {path} cannot be read: {exc}") from None
    except ValueError as exc:
        raise EngineError(
            f"{what} {path} is not valid JSON ({exc}); nothing was written. Fix the file by hand first."
        ) from None
    if not isinstance(data, dict):
        raise EngineError(f"{what} {path} must hold a JSON object, not {type(data).__name__}")
    return {str(k): v for k, v in data.items()}


def parse_personal(text: bytes, where: str) -> JsonObj:
    try:
        data = json.loads(text.decode("utf-8"))
    except ValueError as exc:
        raise EngineError(f"{where} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise EngineError(f"{where} must hold a JSON object")
    layer = {str(k): v for k, v in data.items() if not str(k).startswith("_")}
    if "hooks" in layer:
        raise EngineError(
            f"{where} wires hooks; the personal layer must not. A hook wired in the home settings AND "
            "in a project fires twice per event — hooks belong to the project's .claude/settings.json only."
        )
    return layer


def merge_into(current: JsonObj, layer: JsonObj, plan: PersonalPlan, prefix: str = "") -> JsonObj:
    """Set what the layer names, union lists, keep everything else. Records each change in the plan."""
    merged: JsonObj = dict(current)
    for key, wanted in layer.items():
        path = f"{prefix}{key}"
        if key not in merged:
            merged[key] = wanted
            plan.actions.append(Action("set", path, json.dumps(wanted, ensure_ascii=False)))
            continue
        have = merged[key]
        if isinstance(wanted, dict) and isinstance(have, dict):
            merged[key] = merge_into(
                {str(k): v for k, v in have.items()}, {str(k): v for k, v in wanted.items()}, plan, path + "."
            )
        elif isinstance(wanted, list) and isinstance(have, list):
            items = list(have)
            for item in wanted:
                if item in items:
                    plan.unchanged += 1
                else:
                    items.append(item)
                    plan.actions.append(Action("append", path, json.dumps(item, ensure_ascii=False)))
            merged[key] = items
        elif isinstance(wanted, (dict, list)) or isinstance(have, (dict, list)):
            # dict+dict and list+list were handled above; any other pairing is a shape conflict
            raise EngineError(
                f"{path}: the home settings hold a {type(have).__name__} and the personal layer a "
                f"{type(wanted).__name__}; resolve that by hand, nothing was written"
            )
        elif have == wanted:
            plan.unchanged += 1
        else:
            merged[key] = wanted
            plan.actions.append(
                Action(
                    "set",
                    path,
                    f"{json.dumps(wanted, ensure_ascii=False)}  (was {json.dumps(have, ensure_ascii=False)})",
                )
            )
    return merged


def plan_personal(src: EngineSource, ref: str, home: Path) -> PersonalPlan:
    commit = src.resolve(ref)
    text = src.show(commit, PERSONAL)
    if text is None:
        raise EngineError(f"{ref} ({commit[:7]}) has no {PERSONAL}; pass --ref with a newer tag, branch or commit")
    layer = parse_personal(text, f"{PERSONAL} in {ref}")
    target = home / HOME_SETTINGS
    current: JsonObj = read_json_object(target, "the home settings file") if target.exists() else {}
    if target.exists() and not target.is_file():
        raise EngineError(f"{target} is not a regular file")
    plan = PersonalPlan(target, {})
    plan.merged = merge_into(current, layer, plan)
    return plan


def apply_personal(plan: PersonalPlan) -> Path | None:
    """Write the merged file; return the backup path when one was made."""
    backup: Path | None = None
    if plan.target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = plan.target.with_name(BACKUP_PREFIX + stamp)
        n = 0
        while backup.exists():
            n += 1
            backup = plan.target.with_name(f"{BACKUP_PREFIX}{stamp}-{n}")
        backup.write_bytes(plan.target.read_bytes())
    plan.target.parent.mkdir(parents=True, exist_ok=True)
    plan.target.write_text(json.dumps(plan.merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return backup


def cmd_install_personal(src: EngineSource, args: argparse.Namespace) -> int:
    ref = default_ref(src, args.ref)
    home = config_home(args.home)
    plan = plan_personal(src, ref, home)
    print(f"engine install --personal: {ref} ({src.resolve(ref)[:7]}) -> {plan.target}")
    if not plan.target.exists():
        print("  (no settings file there yet: it will be created)")
    for action in plan.actions:
        print(f"  {action.verb:<7} {action.path}  {'+= ' if action.verb == 'append' else '= '}{action.detail}")
    suffix = " — dry run, nothing written" if args.dry_run else ""
    print(f"  total   {len(plan.actions)} change(s), {plan.unchanged} already as the layer says{suffix}")
    if args.dry_run or not plan.changes:
        return EXIT_OK
    backup = apply_personal(plan)
    if backup is not None:
        print(f"  backup  {backup}")
    print(f"  wrote   {plan.target}  (keys the layer does not name were kept as they were)")
    return EXIT_OK


# --- commands -----------------------------------------------------------------------------


def projects_file() -> Path:
    override = os.environ.get("ENGINE_PROJECTS_FILE")
    if override:
        return Path(override)
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config) / "claude-engine" / "projects.txt"


def registered_projects() -> list[Path]:
    path = projects_file()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Path(line.strip()) for line in lines if line.strip() and not line.lstrip().startswith("#")]


def register(project: Path) -> None:
    if project in registered_projects():
        return
    path = projects_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{project}\n")
    print(f"  listed  {project} in {path} (for `update --all`)")


def default_ref(src: EngineSource, ref: str | None) -> str:
    if ref:
        return ref
    tag = src.newest_tag()
    if tag is None:
        raise EngineError("this repository has no v* tag yet; pass --ref <tag, branch or commit>")
    return tag


def sync(src: EngineSource, args: argparse.Namespace, project: Path, command: str) -> int:
    project = check_project(src, project)
    ref = default_ref(src, args.ref)
    plan = plan_sync(src, ref, project, args.reseed_pristine, set(args.take or []))
    print(f"engine {command}: {ref} ({plan.commit[:7]}) -> {project}")
    if plan.lock is None:
        print("  (no engine-lock.json: a fresh install, or a copy made by hand that is adopted now)")
    if not is_git_work_tree(project):
        print("  note    not a git repository: the change cannot be reviewed as a diff")
    print_plan(plan, args.dry_run)
    if not args.dry_run:
        apply_plan(plan)
        if command == "install" and not args.no_register:
            register(project)
        print(f"  next    review with `git -C {project} status`, then commit — engine.py never commits")
    return EXIT_ATTENTION if plan.held_back else EXIT_OK


def cmd_install(src: EngineSource, args: argparse.Namespace) -> int:
    if args.personal == (args.project is not None):
        raise EngineError("give either a project directory or --personal")
    if args.personal:
        for flag, used in (("--reseed-pristine", args.reseed_pristine), ("--take", args.take), ("--no-register", args.no_register)):
            if used:
                raise EngineError(f"{flag} applies to a project install, not to --personal")
        return cmd_install_personal(src, args)
    if args.home:
        raise EngineError("--home applies to --personal only")
    return sync(src, args, Path(args.project), "install")


def cmd_update(src: EngineSource, args: argparse.Namespace) -> int:
    if args.all == (args.project is not None):
        raise EngineError("give either a project directory or --all")
    if args.project is not None:
        return sync(src, args, Path(args.project), "update")
    projects = registered_projects()
    if not projects:
        print(f"no projects listed in {projects_file()}; `engine.py install` lists each project it installs")
        return EXIT_OK
    worst = EXIT_OK
    summary: list[str] = []
    for project in projects:
        if not project.is_dir():
            summary.append(f"  gone    {project}")
            continue
        try:
            code = sync(src, args, project, "update")
        except EngineError as exc:
            print(f"engine update: {project}: {exc}", file=sys.stderr)
            code = EXIT_ERROR
        worst = max(worst, code)
        summary.append(f"  {('ok', 'held', 'error')[code]:<7} {project}")
        print()
    print("update --all:")
    print("\n".join(summary))
    return worst


def cmd_status(src: EngineSource, args: argparse.Namespace) -> int:
    project = check_project(src, Path(args.project or "."))
    lock = read_lock(project)
    if lock is None:
        print(f"{project}: no {LOCK} — not installed by engine.py (a copy made by hand, or no engine)")
    else:
        print(f"{project}: engine {lock.ref} ({lock.commit[:7]}), installed {lock.installed_utc}")
    ref = default_ref(src, args.ref)
    try:
        plan = plan_sync(src, ref, project, False, set())
    except EngineError as exc:
        print(f"  cannot compare with {ref}: {exc}")
        return EXIT_ERROR
    if not plan.actions and plan.gitignore is None and plan.lock_text is None:
        print(f"  up to date with {ref} ({plan.commit[:7]}); {plan.unchanged} engine files unchanged")
        for note in plan.notes:
            print(f"  note    {note}")
        return EXIT_OK
    print(f"  `engine.py update` to {ref} ({plan.commit[:7]}) would do:")
    print_plan(plan, dry_run=True)
    return EXIT_OK


# --- release ------------------------------------------------------------------------------


def version_key(version: str) -> tuple[int, ...] | None:
    match = RELEASE_VERSION.fullmatch(version)
    return tuple(int(part) for part in match.groups()) if match else None


def ref_commit(src: EngineSource, ref: str) -> str | None:
    """The commit a ref points at, or None when the ref does not exist."""
    try:
        return src.resolve(ref)
    except EngineError:
        return None


def require_clean(src: EngineSource, when: str) -> None:
    dirty = git(src.root, "status", "--porcelain").decode("utf-8", "replace").splitlines()
    if dirty:
        listed = "\n".join(f"    {line}" for line in dirty[:10])
        raise EngineError(f"the work tree is not clean {when} ({len(dirty)} path(s)); nothing was released\n{listed}")


def check_version(src: EngineSource, version: str, remote: str) -> None:
    """The version was never released, here or on the remote, and is newer than every released one."""
    on_remote = git(src.root, "ls-remote", "--tags", remote, f"refs/tags/{version}").strip()
    if on_remote or ref_commit(src, f"refs/tags/{version}"):
        where = f" on {remote}" if on_remote else ""
        raise EngineError(f"the tag {version} already exists{where}; a released version is never moved")
    released = [(k, tag) for tag in git(src.root, "tag", "--list", "v*").decode().split() if (k := version_key(tag))]
    if released and (version_key(version) or ()) <= max(released)[0]:
        raise EngineError(f"{version} is not newer than {max(released)[1]}, the newest released version")


def check_fast_forward(src: EngineSource, head: str, remote: str) -> None:
    """Every existing `main` and `stable`, here and on the remote, must already be behind HEAD."""
    for branch in RELEASE_BRANCHES:
        for ref, name in ((f"refs/remotes/{remote}/{branch}", f"{remote}/{branch}"), (f"refs/heads/{branch}", branch)):
            commit = ref_commit(src, ref)
            if commit is not None and not src.is_ancestor(commit, head):
                raise EngineError(
                    f"{name} ({commit[:7]}) is not an ancestor of HEAD ({head[:7]}): moving it would not be a "
                    "fast-forward. Bring its commits into the branch being released first; nothing was released"
                )


def release_environment(src: EngineSource) -> str | None:
    """The name of the folder this environment's baselines live in, as the evals name it."""
    script = src.root / RELEASE_ENVIRONMENT
    if not script.is_file():
        return None
    res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
    return res.stdout.strip() or None if res.returncode == 0 else None


def newest_baseline(src: EngineSource) -> str:
    """The golden-set results file committed last — of THIS environment when it has one. A
    baseline of another environment is the fallback, and the release says so."""
    added = git(src.root, "log", "--diff-filter=A", "--format=", "--name-only", "HEAD", "--", RELEASE_BASELINES).decode().split("\n")
    present = [path for path in added if path and (src.root / path).is_file()]
    here = release_environment(src)
    for path in present:
        if here and Path(path).parent.name == here:
            return path
    if present:
        if here:
            print(f"  note    no golden-set baseline was recorded on {here}; comparing with {present[0]} — a CROSS-ENVIRONMENT comparison")
        return present[0]
    raise EngineError(f"no golden-set baseline ({RELEASE_BASELINES}) in this repository; pass --baseline FILE")


def run_check(src: EngineSource, what: str, command: list[str], red: str) -> None:
    print(f"  check   {what}: {' '.join(command)}", flush=True)
    if subprocess.run(command, cwd=src.root, check=False).returncode != 0:
        raise EngineError(f"{red}; nothing was released")


def cmd_release(src: EngineSource, args: argparse.Namespace) -> int:
    if not args.owner_approved:
        raise EngineError("release does nothing without --owner-approved: a release is the owner's decision (docs/release.md)")
    if os.environ.get("CLAUDECODE"):
        raise EngineError(
            "--owner-approved was given, but inside a Claude Code session (CLAUDECODE is set) it does not count: "
            "it is the owner's flag, for the owner's own terminal"
        )
    version, remote = args.version, args.remote
    if version_key(version) is None:
        raise EngineError(f"{version!r} is not a version: write it as vMAJOR.MINOR.PATCH, for example v0.12.0")
    git(src.root, "fetch", "--quiet", remote)
    check_version(src, version, remote)
    require_clean(src, "before the checks")
    head = src.resolve("HEAD")
    check_fast_forward(src, head, remote)
    baseline = args.baseline or newest_baseline(src)
    if not (src.root / baseline).is_file():
        raise EngineError(f"the baseline {baseline} is not a file in {src.root}")
    print(f"engine release: {version} at {head[:7]} -> {', '.join(RELEASE_BRANCHES)} on {remote}")
    run_check(src, "the suites", list(RELEASE_TESTS), "the tests are red")
    run_check(
        src,
        "the golden set",
        [sys.executable, RELEASE_GOLDEN, "--engine-ref", "HEAD", "--compare", baseline],
        f"the golden set is not identical to {baseline}",
    )
    require_clean(src, "after the checks")
    if src.resolve("HEAD") != head:
        raise EngineError("HEAD moved while the checks ran; nothing was released")

    git(src.root, "tag", "-a", version, "-m", args.message or f"engine {version}", head)
    try:
        git(src.root, "push", "--atomic", remote, f"refs/tags/{version}", *(f"{head}:refs/heads/{b}" for b in RELEASE_BRANCHES))
    except EngineError as exc:
        git(src.root, "tag", "-d", version)
        raise EngineError(f"the push was refused, the local tag is removed again and nothing was released\n  {exc}") from None
    print(f"  pushed  {version}, {', '.join(RELEASE_BRANCHES)} -> {remote} (fast-forward)")
    current = subprocess.run(
        ["git", "-C", str(src.root), "symbolic-ref", "--short", "-q", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    for branch in RELEASE_BRANCHES:
        if branch == current:
            continue
        try:
            git(src.root, "branch", "-f", branch, head)
        except EngineError as exc:
            print(f"  note    the local branch {branch} was not moved (the remote one was): {exc}")
    print(f"released {version} ({head[:7]}): {', '.join(RELEASE_BRANCHES)} and the tag point at it, here and on {remote}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engine.py", description=(__doc__ or "").split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser, writes: bool) -> None:
        p.add_argument("--ref", help="tag, branch or commit of the engine (default: the newest v* tag)")
        if writes:
            p.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
            p.add_argument(
                "--reseed-pristine",
                action="store_true",
                help="replace project files that hold only the engine's own records with their clean seed",
            )
            p.add_argument(
                "--take",
                action="append",
                metavar="PATH",
                help="apply the engine's version of PATH although the project changed it (repeatable)",
            )

    install = sub.add_parser(
        "install",
        help="install the engine into a project (or adopt a copy made by hand), or the personal layer into the home settings",
    )
    install.add_argument("project", nargs="?")
    common(install, writes=True)
    install.add_argument("--no-register", action="store_true", help="do not list the project for `update --all`")
    install.add_argument(
        "--personal",
        action="store_true",
        help=f"merge {PERSONAL} of the ref into the home settings file instead of installing into a project",
    )
    install.add_argument(
        "--home",
        metavar="DIR",
        help="with --personal: the Claude Code config directory (default: $CLAUDE_CONFIG_DIR, else ~/.claude)",
    )
    install.set_defaults(handler=cmd_install)

    update = sub.add_parser("update", help="update one project, or every listed project with --all")
    update.add_argument("project", nargs="?")
    update.add_argument("--all", action="store_true", help=f"every project listed in {projects_file()}")
    common(update, writes=True)
    update.set_defaults(handler=cmd_update)

    status = sub.add_parser("status", help="what is installed, and what an update would change")
    status.add_argument("project", nargs="?")
    common(status, writes=False)
    status.set_defaults(handler=cmd_status)

    release = sub.add_parser(
        "release", help="the owner's: tag HEAD with a version and move main and stable onto it, fast-forward only, and push"
    )
    release.add_argument("version", help="the new version, vMAJOR.MINOR.PATCH")
    release.add_argument(
        "--owner-approved",
        action="store_true",
        help="the owner's approval; without it nothing happens, and inside a Claude Code session it does not count",
    )
    release.add_argument(
        "--baseline",
        metavar="FILE",
        help=f"the golden-set results to compare with (default: the {RELEASE_BASELINES} committed last, this environment's first)",
    )
    release.add_argument("--remote", default="origin", help="the remote to push to (default: origin)")
    release.add_argument("--message", metavar="TEXT", help="the tag's message (default: `engine <version>`)")
    release.set_defaults(handler=cmd_release)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        src = EngineSource.here()
        code: int = args.handler(src, args)
        return code
    except EngineError as exc:
        print(f"engine.py: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
