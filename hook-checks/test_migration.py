#!/usr/bin/env python3
"""engine.py moves a project's own data from the pre-3c paths to .engine/ — by the explicit
table in engine.py, file by file, reporting a conflict and touching nothing there.

Cases, each against a real git repository:

- a project INSTALLED from v0.10.1 (the last pre-move engine) with records appended to,
  slices, architecture, premises, spikes and a PROGRESS.md: `update --ref HEAD --dry-run`
  lists every move and writes nothing; the real update moves each file byte for byte, leaves
  no old path behind, seeds nothing on top of a moved record, and a second update has
  nothing to move;
- a hand copy of v0.8.0 (git archive, no lock): adopted AND migrated in one update;
- a conflict (a record in both places): kept, reported, both files untouched;
- an update to an OLDER ref (v0.10.1) migrates nothing — the table applies only when the
  ref's map knows the new layout.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
OLD_NEW = {
    ".claude/overseer/ledger.md": ".engine/overseer/ledger.md",
    ".claude/overseer/audit.md": ".engine/overseer/audit.md",
    ".claude/overseer/escalations.md": ".engine/overseer/escalations.md",
    ".claude/overseer/parked.md": ".engine/overseer/parked.md",
    ".claude/overseer/MEMORY.md": ".engine/overseer/MEMORY.md",
    ".claude/overseer/slice/checkout.md": ".engine/slices/checkout.md",
    ".claude/architecture/feature-dag.json": ".engine/architecture/feature-dag.json",
    ".claude/architecture/feature/x.md": ".engine/architecture/feature/x.md",
    ".claude/premises/premise-log.md": ".engine/premises/premise-log.md",
    ".claude/artifacts/spikes/s1/notes.md": ".engine/artifacts/spikes/s1/notes.md",
    "PROGRESS.md": ".engine/PROGRESS.md",
}


class Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ok   {name}")
        else:
            self.failed += 1
            print(f"  FAIL {name}  {detail[:700]}")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def engine(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ENGINE_PY), *args], capture_output=True, text=True, env=env, check=False)


def tree(project: Path) -> dict[str, bytes]:
    return {p.relative_to(project).as_posix(): p.read_bytes() for p in sorted(project.rglob("*")) if p.is_file() and ".git" not in p.relative_to(project).parts}


def fill_project_data(project: Path) -> dict[str, bytes]:
    """Append to the seeded records and add the un-seeded kinds; return old-path -> bytes."""
    for rel in OLD_NEW:
        p = project / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_file():
            p.write_bytes(p.read_bytes() + f"\n## 2026-10-02 — an entry of THIS project in {rel}\n".encode())
        else:
            p.write_text(f"this project's own {rel}\n", encoding="utf-8")
    return {rel: (project / rel).read_bytes() for rel in OLD_NEW}


def main() -> int:
    t = Checks()
    head_map = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:.claude/ownership.txt"], capture_output=True, text=True, check=False).stdout
    if "project  .engine/**" not in head_map:
        print("  skip: HEAD does not carry the post-move ownership map yet")
        print("\nPASS 0   FAIL 0")
        return 0
    with tempfile.TemporaryDirectory(prefix="migration-") as tmp:
        tmp_path = Path(tmp)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}

        # --- a project installed from v0.10.1, with its own data at the old paths -------------
        p = tmp_path / "v0101"
        p.mkdir()
        git(p, "init", "-q", "-b", "main")
        r = engine(env, "install", str(p), "--ref", "v0.10.1", "--no-register")
        t.check("installed from v0.10.1", r.returncode == 0, r.stdout + r.stderr)
        data = fill_project_data(p)
        git(p, "add", "-A")
        git(p, "commit", "-qm", "a project with records")
        before = tree(p)
        r = engine(env, "update", str(p), "--ref", "HEAD", "--dry-run")
        t.check("dry run: exit 0 or 1", r.returncode in (0, 1), r.stdout + r.stderr)
        t.check("dry run: writes nothing", tree(p) == before)
        for old, new in OLD_NEW.items():
            t.check(f"dry run lists: move {old} -> {new}", f"move    {old}  — -> {new}" in r.stdout, r.stdout)
        t.check("dry run: no seed on top of a moving record", "seed    .engine/overseer/ledger.md" not in r.stdout and "seed    .engine/premises/premise-log.md" not in r.stdout, r.stdout)
        r = engine(env, "update", str(p), "--ref", "HEAD")
        t.check("update: runs", r.returncode in (0, 1), r.stdout + r.stderr)
        after = tree(p)
        for old, new in OLD_NEW.items():
            t.check(f"moved byte for byte: {new}", after.get(new) == data[old] and old not in after, f"{old} present={old in after}")
        t.check("old directories are gone", not any((p / d).exists() for d in (".claude/overseer", ".claude/architecture", ".claude/premises", ".claude/artifacts")), str([d for d in (".claude/overseer", ".claude/architecture", ".claude/premises", ".claude/artifacts") if (p / d).exists()]))
        t.check("the slice template arrived at its new engine path", (p / ".claude/templates/slice-contract.md").is_file())
        settled = tree(p)
        r = engine(env, "update", str(p), "--ref", "HEAD")
        t.check("second update: nothing to move, nothing changed", "move    " not in r.stdout and tree(p) == settled, r.stdout)

        # --- a hand copy of v0.8.0: adopted and migrated in one update ----------------------------
        has_tag = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", "v0.8.0"], capture_output=True, check=False).returncode == 0
        if has_tag:
            hand = tmp_path / "hand-v0.8.0"
            hand.mkdir()
            git(hand, "init", "-q", "-b", "main")
            archive = subprocess.run(["git", "-C", str(ROOT), "archive", "v0.8.0", ".claude", "CLAUDE.md", "AGENTS.md"], capture_output=True, check=True).stdout
            subprocess.run(["tar", "-xf", "-", "-C", str(hand)], input=archive, check=True)
            (hand / "PROGRESS.md").write_text("# PROGRESS of the copied project\n", encoding="utf-8")
            (hand / ".claude/overseer/ledger.md").write_bytes((hand / ".claude/overseer/ledger.md").read_bytes() + "\n## 2026-10-02 — our entry\n".encode())
            ledger_bytes = (hand / ".claude/overseer/ledger.md").read_bytes()
            git(hand, "add", "-A")
            git(hand, "commit", "-qm", "v0.8.0 copied by hand")
            r = engine(env, "update", str(hand), "--ref", "HEAD", "--reseed-pristine")
            t.check("hand copy: update runs", r.returncode in (0, 1), r.stdout + r.stderr)
            t.check("hand copy: the appended ledger moved intact", (hand / ".engine/overseer/ledger.md").read_bytes() == ledger_bytes and not (hand / ".claude/overseer/ledger.md").exists())
            t.check("hand copy: PROGRESS.md moved", (hand / ".engine/PROGRESS.md").read_text(encoding="utf-8").startswith("# PROGRESS of the copied") and not (hand / "PROGRESS.md").exists())
            t.check("hand copy: the old engine template was retired, the new one arrived", not (hand / ".claude/overseer/_template.md").exists() and (hand / ".claude/templates/slice-contract.md").is_file())
            t.check("hand copy: .claude/overseer/ is gone", not (hand / ".claude/overseer").exists())
        else:
            print("  skip hand copy of v0.8.0: tag not here")

        # --- a conflict: a record in both places --------------------------------------------------
        c = tmp_path / "conflict"
        c.mkdir()
        git(c, "init", "-q", "-b", "main")
        engine(env, "install", str(c), "--ref", "v0.10.1", "--no-register")
        (c / ".claude/overseer/ledger.md").write_text("OLD ledger\n", encoding="utf-8")
        (c / ".engine/overseer").mkdir(parents=True)
        (c / ".engine/overseer/ledger.md").write_text("NEW ledger\n", encoding="utf-8")
        git(c, "add", "-A")
        git(c, "commit", "-qm", "both")
        r = engine(env, "update", str(c), "--ref", "HEAD")
        t.check("conflict: reported as keep", "keep    .claude/overseer/ledger.md  — exists in both places" in r.stdout, r.stdout)
        t.check("conflict: exit 1 (something held back)", r.returncode == 1, str(r.returncode))
        t.check("conflict: both files untouched", (c / ".claude/overseer/ledger.md").read_text() == "OLD ledger\n" and (c / ".engine/overseer/ledger.md").read_text() == "NEW ledger\n")
        t.check("conflict: the other records still moved", (c / ".engine/overseer/parked.md").is_file() and not (c / ".claude/overseer/parked.md").exists())

        # --- an older ref migrates nothing --------------------------------------------------------
        o = tmp_path / "older"
        o.mkdir()
        git(o, "init", "-q", "-b", "main")
        engine(env, "install", str(o), "--ref", "v0.10.1", "--no-register")
        fill_project_data(o)
        git(o, "add", "-A")
        git(o, "commit", "-qm", "data")
        snap = tree(o)
        r = engine(env, "update", str(o), "--ref", "v0.10.1")
        t.check("update to the pre-move ref: no move, nothing changed", "move    " not in r.stdout and tree(o) == snap, r.stdout)

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
