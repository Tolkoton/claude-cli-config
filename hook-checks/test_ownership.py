#!/usr/bin/env python3
"""The ownership map (.claude/ownership.txt) tells the truth about this repository.

engine.py ships exactly the paths the map calls `engine` and never touches the rest, so a
wrong line in the map is a wrong install in every project. What is pinned here:

- the map parses, and every tracked file has an owner;
- no tracked file is machine state, and this repository ignores every machine pattern itself;
- every seed exists, is tracked, and never ships (seeds are copied once, not kept in sync);
- the clean seeds of the overseer's records hold no dated records of this repository;
- the engine's own records stay project files of this repository;
- the lock engine.py writes into projects never exists here.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("engine", ROOT / "engine.py")
assert spec and spec.loader
engine = importlib.util.module_from_spec(spec)
sys.modules["engine"] = engine  # dataclasses look their module up while the class is built
spec.loader.exec_module(engine)

PASS = FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def samples(pattern: str) -> list[str]:
    """Concrete paths a pattern covers: `**/` as no directory and as one, `*`/`?` as `x`."""
    shapes = {pattern.replace("**/", ""), pattern.replace("**/", "x/")}
    out = []
    for shape in shapes:
        shape = shape.replace("**", "x").replace("*", "x").replace("?", "x")
        out.append(shape + "x" if shape.endswith("/") else shape)
    return sorted(out)


rules = engine.parse_ownership((ROOT / ".claude" / "ownership.txt").read_text(encoding="utf-8"))
tracked = [p for p in git("ls-files", "-z").split("\0") if p]
owners = {p: engine.owner_of(rules, p) for p in tracked}

unowned = [p for p, o in owners.items() if o is None]
check("every tracked file has an owner", not unowned, ", ".join(unowned[:5]))

machine_tracked = [p for p, o in owners.items() if o == "machine"]
check("no tracked file is machine state", not machine_tracked, ", ".join(machine_tracked[:5]))

not_ignored = []
for rule in (r for r in rules if r.owner == "machine"):
    for sample in samples(rule.pattern):
        ignored = (
            subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", sample], check=False).returncode
            == 0
        )
        if not ignored:
            not_ignored.append(f"{rule.pattern} ({sample})")
check("this repository's .gitignore ignores every machine pattern", not not_ignored, "; ".join(not_ignored))

seeds = [(r.pattern, r.seed) for r in rules if r.seed]
missing = [s for _, s in seeds if s not in owners]
check("every seed is a tracked file", not missing, ", ".join(missing))
shipped_seeds = [s for _, s in seeds if owners.get(s) == "engine"]
check("no seed ships (seeds are copied once, never kept in sync)", not shipped_seeds, ", ".join(shipped_seeds))

dated = re.compile(r"^## 20\d\d-\d\d-\d\d", re.MULTILINE)
records = [".engine/overseer/" + n for n in ("ledger.md", "audit.md", "escalations.md", "parked.md", "MEMORY.md")]
seed_of = dict(seeds)
for path in records:
    seed = seed_of.get(path)
    check(f"{path} is a project file with a seed", engine.owner_of(rules, path) == "project" and bool(seed))
    if seed:
        text = (ROOT / seed).read_text(encoding="utf-8")
        check(f"  its seed {seed} holds no dated record", not dated.search(text))
        own = (ROOT / path).read_text(encoding="utf-8")
        check("  and is the head of this repository's own file", own.startswith(text.rstrip("\n")))

expected = {
    ".claude/hooks/block-dangerous.sh": "engine",
    ".claude/settings.json": "engine",
    ".claude/ownership.txt": "engine",
    ".claude/unattended/unattended-decisions.md": "engine",
    ".claude/templates/slice-contract.md": "engine",
    ".claude/settings.local.json": "machine",
    ".claude/state/overseer/mode": "machine",
    ".claude/hooks/__pycache__/overseer_stop.cpython-312.pyc": "machine",
    ".claude/worktrees/feature-a/src/app.py": "machine",
    ".claude/project.env": "project",
    ".engine/architecture/feature-dag.json": "project",
    ".engine/artifacts/spikes/x/notes.md": "project",
    ".engine/slices/checkout.md": "project",
    "CLAUDE.md": "project",
    "evals/make_sandbox.sh": "project",
    "engine.py": "project",
    "templates/project/.engine/overseer/ledger.md": "project",
    "user/skills/live-build/SKILL.md": "user",
    "user/settings.json": "user",
    "docs/tasks/settings.json": "project",
    "docs/tasks/effective-before-split.json": "project",
    "evals/settings_parity.py": "project",
    "evals/permission_rules.py": "project",
    "hook-checks/fixtures/home-settings.json": "project",
    "docs/engine-limits.md": "project",
    ".claude/unattended/env-probe.sh": "engine",
    ".claude/hooks/approve-project-data.py": "engine",
    ".claude/skills/claude-autonomy/assets/settings.user.json.template": "engine",
    "evals/probe_permission_hook.sh": "project",
    "hook-checks/test_engine_lint.py": "project",
    ".claude/unattended/commit_checkpoint.sh": "engine",
    "templates/project/.claude/project.env": "project",
}
for path, owner in expected.items():
    got = engine.owner_of(rules, path)
    check(f"{path} -> {owner}", got == owner, f"got {got}")

check("the project lock never exists in this repository", engine.LOCK not in owners)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
