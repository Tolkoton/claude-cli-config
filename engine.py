#!/usr/bin/env python3
"""Install, update and inspect the engine in a project — from ONE git ref of this repository.

    engine.py install <project> [--ref REF] [--dry-run] [--reseed-pristine] [--take PATH] [--no-register]
    engine.py install --personal [--ref REF] [--dry-run] [--home DIR]
    engine.py update  <project> [--ref REF] [--dry-run] [--reseed-pristine] [--take PATH]
    engine.py update  --all     [--ref REF] [--dry-run] [--reseed-pristine]
    engine.py status  [<project>] [--ref REF]

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
from "edited here" (report it, keep it). A project copied by hand before this installer existed
has no lock; then each file is compared with every version the engine ever had at that path —
any match is an untouched engine file (replace it), no match is an edit (keep it).

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


class EngineError(Exception):
    """A condition the user has to fix. Printed without a traceback, exit status 2."""


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
    verb: str  # add, update, chmod, keep, remove, seed, reseed
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
            if seed_entry.blob in ids or not ids & history.get(target_path, set()):
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
                    if target_path.startswith(".claude/overseer/")
                    else "is an unedited copy of an older engine version"
                )
                plan.notes.append(f"{target_path} {what}; --reseed-pristine replaces it with the seed")
        elif not target.exists() and target_path not in seeded_before:
            plan.actions.append(
                Action("seed", target_path, f"from {seed_path}", blob=seed_entry.blob, mode=seed_entry.mode)
            )
            blobs_needed.add(seed_entry.blob)
            seeded.add(target_path)

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

    plan.contents = src.read(blobs_needed)
    return plan


def apply_plan(plan: Plan) -> None:
    for action in plan.actions:
        target = plan.project / action.path
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
