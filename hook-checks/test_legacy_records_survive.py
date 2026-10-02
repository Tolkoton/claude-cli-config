#!/usr/bin/env python3
"""A project's un-migrated records are never swept up by the engine's retirement step.

Package 3c moves the records out of .claude/ into .engine/. engine.py removes an engine
file the engine no longer ships when the project's copy matches ANY blob the path ever had
in the engine's history. The engine repository's own .claude/overseer/ledger.md used to be
tracked at that path, so a project's PRISTINE ledger (installed from a seed, never appended
to) matches a historical blob exactly — the one input where blob-match retirement fires if
the old record paths are not kept `project` in the ownership map. decana cannot exercise
this: its records diverged from the seeds long ago. (The feature-critic's premise probe for
package 3c.)

The fixture: a project installed from v0.10.1 (the last pre-move engine), every seeded
record left byte-identical to its seed, then `engine.py update --ref HEAD --dry-run`. Every
legacy path must still be there, unchanged, and the plan must never say `remove` for one.
Meaningful only once HEAD carries the post-move map; until then it says so and passes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
LEGACY = [
    ".claude/overseer/ledger.md", ".claude/overseer/audit.md", ".claude/overseer/escalations.md",
    ".claude/overseer/parked.md", ".claude/overseer/MEMORY.md", ".claude/premises/premise-log.md",
]


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
            print(f"  FAIL {name}  {detail[:600]}")


def main() -> int:
    t = Checks()
    head_map = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:.claude/ownership.txt"], capture_output=True, text=True, check=False).stdout
    if "project  .claude/overseer/ledger.md\n" not in head_map or "seed=templates/project/.engine/" not in head_map:
        print("  skip: HEAD does not carry the post-move ownership map yet (commit the move, then this test bites)")
        print("\nPASS 0   FAIL 0")
        return 0
    has_tag = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", "v0.10.1"], capture_output=True, check=False).returncode == 0
    t.check("v0.10.1 is available as the pre-move engine", has_tag)
    if not has_tag:
        print(f"\nPASS {t.passed}   FAIL {t.failed}")
        return 1

    with tempfile.TemporaryDirectory(prefix="legacy-records-") as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "pristine"
        project.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}
        r = subprocess.run([sys.executable, str(ENGINE_PY), "install", str(project), "--ref", "v0.10.1", "--no-register"], capture_output=True, text=True, env=env, check=False)
        t.check("installed from v0.10.1", r.returncode == 0, r.stdout + r.stderr)
        before = {rel: (project / rel).read_bytes() for rel in LEGACY if (project / rel).is_file()}
        t.check("the pre-move install seeded the records at their OLD paths", set(before) == set(LEGACY), str(sorted(before)))
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pristine v0.10.1"], cwd=project, check=True)

        r = subprocess.run([sys.executable, str(ENGINE_PY), "update", str(project), "--ref", "HEAD", "--dry-run"], capture_output=True, text=True, env=env, check=False)
        plan = r.stdout
        t.check("update --dry-run to HEAD runs", r.returncode in (0, 1), r.stdout + r.stderr)
        removes = [line for line in plan.splitlines() if line.strip().startswith("remove") and any(p in line for p in LEGACY)]
        t.check("the plan never says `remove` for a pristine legacy record", not removes, "\n".join(removes))
        after = {rel: (project / rel).read_bytes() for rel in LEGACY if (project / rel).is_file()}
        t.check("dry run: every legacy record still there, byte for byte", after == before)
        r = subprocess.run([sys.executable, str(ENGINE_PY), "update", str(project), "--ref", "HEAD"], capture_output=True, text=True, env=env, check=False)
        t.check("the real update runs", r.returncode in (0, 1), r.stdout + r.stderr)
        after = {rel: (project / rel).read_bytes() for rel in LEGACY if (project / rel).is_file()}
        migrated = {rel: (project / rel.replace(".claude/overseer/", ".engine/overseer/").replace(".claude/premises/", ".engine/premises/")).is_file() for rel in LEGACY}
        if all(migrated.values()):
            # a later slice taught engine.py to MOVE them — the content must have travelled intact
            moved = {rel: (project / rel.replace(".claude/overseer/", ".engine/overseer/").replace(".claude/premises/", ".engine/premises/")).read_bytes() for rel in LEGACY}
            t.check("migrated: every record arrived at its new path with the same bytes", moved == before)
            t.check("migrated: nothing was left behind at the old paths", not after, str(sorted(after)))
        else:
            t.check("not migrated (yet): every legacy record still there, byte for byte", after == before, str(sorted(after)))
        t.check("no stray `.engine` seed with the OLD record's name was removed either", "remove  .claude/overseer" not in plan)

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
