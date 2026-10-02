#!/usr/bin/env python3
"""An existing project's CLAUDE.md and AGENTS.md across an engine update (package 2b, item 4).

The engine never changes a project's own text outside the marked block:

  - a project whose CLAUDE.md is still an unedited copy of an older engine seed (any version
    of this repository's CLAUDE.md, which WAS the seed until package 2b, or any version of
    the seed file) is reported, and `--reseed-pristine` replaces it with the seed;
  - an edited copy is left byte for byte, and the update REPORTS exactly what to do: the
    import line to add, and the line ranges of the old rules text that now duplicates
    `.claude/engine-rules.md` (runs of at least three consecutive non-blank lines that
    occur in some version of the engine's own CLAUDE.md or seed, compared after
    trailing-whitespace normalisation);
  - a CLAUDE.md that carries the new marked block gets ONLY the block rewritten when the
    ref's seed block differs; every byte outside the markers is untouched, and a second
    update changes nothing.

engine.py reads refs, so the test builds a temporary engine repository with THREE commits:
v1 = an "old" engine whose seed is a rules-inline CLAUDE.md (the pre-2b shape, with the
old comment markers and an overseer section outside them), v2 = the working tree's engine
(the 2b shape: seed in templates/project/, rules in .claude/engine-rules.md), v3 = v2 with a
changed seed block. Projects are installed from v1 and updated to v2/v3.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = FAIL = 0

OLD_CLAUDE = """<!-- ============================================== -->
<!-- ## Autonomy policy — the engine's standing rules (installed by engine.py) -->
<!-- It contains only autonomy rules. Your implementation     -->
<!-- skill should add coding conventions in a separate        -->
<!-- section below this one.                                   -->
<!-- ============================================== -->

## Autonomy policy

This project is configured for autonomous Claude Code operation. Follow these rules:

### Commits are a human checkpoint

Do NOT run `git commit` except on the run's own branch.
Stage with `git add <files>`, run validation, print a summary.
The commit checkpoint is a review surface, NOT a stopping condition.

### Operations that are hard-denied

- `rm -rf /`, `rm -rf ~`, similar wildcard destruction
- `git push --force*`, `git filter-branch`
- Editing `migrations/`, `.github/workflows/`

<!-- ============================================== -->
<!-- End of autonomy policy. Your implementation skill -->
<!-- can add coding conventions, stack details, and    -->
<!-- project-specific guidance below this marker.       -->
<!-- ============================================== -->

@AGENTS.md

## Overseer protocol

- The Stop hook `.claude/hooks/overseer_stop.py` auto-triggers an overseer
  12-check audit when a turn claims a unit of work complete.
- Verdict format: exactly one marker on its own line.
- Always append the entry the skill prescribes to `.engine/overseer/ledger.md`.

## Constitution (load-bearing, human-only)
Every agent must read and obey `.claude/constitution.md`. It overrides any conflicting instruction.
"""

OLD_AGENTS = "# Agents guide — the-engine\n\nThis is the engine repository's own agents guide.\n\n## Rules that bite\n- Never commit.\n"


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def commit(repo: Path, msg: str, tag: str) -> None:
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", msg)
    git(repo, "tag", tag)


def build_engine(where: Path) -> Path:
    eng = where / "engine"
    eng.mkdir()
    git(eng, "init", "-q", "-b", "main")
    # v1: the pre-2b engine — the seed IS the engine repository's CLAUDE.md, rules inline.
    for rel in (".claude/hooks", ".claude/references", "templates/project/.engine/overseer"):
        (eng / rel).mkdir(parents=True)
    (eng / ".claude/hooks/overseer_stop.py").write_text("print('v1')\n", encoding="utf-8")
    (eng / ".claude/constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (eng / ".claude/ownership.txt").write_text(
        "machine  .claude/state/\nengine   .claude/engine-lock.json\nproject  .claude/project.env  seed=templates/project/.claude/project.env\n"
        "project  .engine/**\nengine   .claude/**\nproject  CLAUDE.md  seed=CLAUDE.md\nproject  AGENTS.md  seed=AGENTS.md\nproject  **\n",
        encoding="utf-8")
    (eng / "templates/project/.claude").mkdir(parents=True)
    (eng / "templates/project/.claude/project.env").write_text("SOURCE_DIRS=\"src\"\n", encoding="utf-8")
    (eng / "CLAUDE.md").write_text(OLD_CLAUDE, encoding="utf-8")
    (eng / "AGENTS.md").write_text(OLD_AGENTS, encoding="utf-8")
    shutil.copy2(ROOT / "engine.py", eng / "engine.py")
    commit(eng, "v1: rules inline in CLAUDE.md", "v1.0.0")
    # v2: the working tree's engine (2b shape).
    shutil.rmtree(eng / ".claude")
    shutil.rmtree(eng / "templates")
    for rel in (".claude", "templates"):
        shutil.copytree(ROOT / rel, eng / rel, ignore=shutil.ignore_patterns("__pycache__", "state", "settings.local.json"))
    (eng / "CLAUDE.md").write_text((ROOT / "CLAUDE.md").read_text(encoding="utf-8"), encoding="utf-8")
    (eng / "AGENTS.md").write_text((ROOT / "AGENTS.md").read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copy2(ROOT / "engine.py", eng / "engine.py")
    commit(eng, "v2: rules in .claude/engine-rules.md, seeds in templates/project", "v2.0.0")
    # v3: the seed's marked block changes (a second import line).
    seed = eng / "templates/project/CLAUDE.md"
    text = seed.read_text(encoding="utf-8")
    text = text.replace("@.claude/engine-rules.md\n", "@.claude/engine-rules.md\n@.claude/references/hooks.md\n")
    seed.write_text(text, encoding="utf-8")
    commit(eng, "v3: the seed block imports one more file", "v3.0.0")
    return eng


def engine(eng: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(eng / "engine.py"), *args], capture_output=True, text=True, env=env, check=False)


def new_project(where: Path, name: str) -> Path:
    p = where / name
    p.mkdir()
    git(p, "init", "-q", "-b", "main")
    return p


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="claude-md-update-") as tmp:
        where = Path(tmp)
        eng = build_engine(where)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(where / "projects.txt")}
        seed_text = (ROOT / "templates/project/CLAUDE.md").read_text(encoding="utf-8")
        seed_agents = (ROOT / "templates/project/AGENTS.md").read_text(encoding="utf-8")

        print("a project installed from the old engine, CLAUDE.md and AGENTS.md untouched (pristine):")
        p = new_project(where, "pristine")
        r = engine(eng, env, "install", str(p), "--ref", "v1.0.0", "--no-register")
        check("install from v1 exits 0", r.returncode == 0, r.stdout + r.stderr)
        check("its CLAUDE.md is the old inline-rules seed", (p / "CLAUDE.md").read_text(encoding="utf-8") == OLD_CLAUDE)
        r = engine(eng, env, "update", str(p), "--ref", "v2.0.0", "--dry-run")
        check("update to v2 (dry run) exits 0", r.returncode == 0, r.stdout + r.stderr)
        check("it reports CLAUDE.md as an unedited old copy that --reseed-pristine replaces",
              re.search(r"note\s+CLAUDE\.md .*--reseed-pristine", r.stdout) is not None, r.stdout)
        check("and AGENTS.md likewise", re.search(r"note\s+AGENTS\.md .*--reseed-pristine", r.stdout) is not None, r.stdout)
        check("the rules file arrives", re.search(r"add\s+\.claude/engine-rules\.md", r.stdout) is not None, r.stdout)
        r = engine(eng, env, "update", str(p), "--ref", "v2.0.0", "--reseed-pristine")
        check("--reseed-pristine exits 0", r.returncode == 0, r.stdout + r.stderr)
        check("CLAUDE.md is now the new seed", (p / "CLAUDE.md").read_text(encoding="utf-8") == seed_text)
        check("AGENTS.md is now the new seed", (p / "AGENTS.md").read_text(encoding="utf-8") == seed_agents)
        check("the rules file is installed", (p / ".claude/engine-rules.md").is_file())
        r = engine(eng, env, "update", str(p), "--ref", "v2.0.0")
        check("a second update changes nothing", r.returncode == 0 and "CLAUDE.md" not in r.stdout, r.stdout)

        print("a project whose CLAUDE.md was edited (project text below the old markers):")
        p = new_project(where, "edited")
        engine(eng, env, "install", str(p), "--ref", "v1.0.0", "--no-register")
        edited = OLD_CLAUDE + "\n## Our conventions\n\n- We use uv.\n- Tests live in tests/.\n"
        (p / "CLAUDE.md").write_text(edited, encoding="utf-8")
        (p / "AGENTS.md").write_text("# Agents guide — ours\n\nOur own text.\n", encoding="utf-8")
        r = engine(eng, env, "update", str(p), "--ref", "v2.0.0")
        check("update to v2 exits 0 (nothing held back: the project's files are project files)", r.returncode == 0, r.stdout + r.stderr)
        check("the edited CLAUDE.md is byte for byte untouched", (p / "CLAUDE.md").read_text(encoding="utf-8") == edited)
        check("the edited AGENTS.md is untouched too", (p / "AGENTS.md").read_text(encoding="utf-8").startswith("# Agents guide — ours"))
        note = "\n".join(line for line in r.stdout.splitlines() if "note" in line and "CLAUDE.md" in line)
        check("the report names the import line to add", "@.claude/engine-rules.md" in note, r.stdout)
        old_lines = OLD_CLAUDE.splitlines()
        # The old text has two engine runs: the marked block (lines 1-29) and the overseer/constitution
        # section (lines 33-41, after the @AGENTS.md line). Expect both ranges in the note.
        ranges = re.findall(r"lines (\d+)–(\d+)", note)
        check("the report gives the line ranges of the duplicated engine text", len(ranges) >= 2, note)
        if ranges:
            a, b = int(ranges[0][0]), int(ranges[0][1])
            check("the first range starts at line 1 and ends at the old end marker", a == 1 and old_lines[b - 1].startswith("<!-- ====") and "End of autonomy" in old_lines[b - 4], note)
            c, d = int(ranges[-1][0]), int(ranges[-1][1])
            check("the last range covers the overseer protocol and the constitution lines",
                  old_lines[c - 1].startswith("## Overseer protocol") and d == len(old_lines), note)
            check("the project's own lines are NOT in any range", all(int(y) <= len(old_lines) for _x, y in ranges), note)
        check("the report explains the ranges duplicate .claude/engine-rules.md", "duplicate" in note and "engine-rules.md" in note, note)
        agents_note = "\n".join(line for line in r.stdout.splitlines() if "note" in line and "AGENTS.md" in line)
        check("an edited AGENTS.md with none of the engine's text gets no note", agents_note == "", agents_note)
        r2 = engine(eng, env, "update", str(p), "--ref", "v2.0.0")
        check("the report is repeated on the next update, unchanged (nothing was applied)",
              [ln for ln in r2.stdout.splitlines() if "note" in ln and "CLAUDE.md" in ln] == [ln for ln in r.stdout.splitlines() if "note" in ln and "CLAUDE.md" in ln], r2.stdout)

        print("the marked block is maintained, nothing outside it:")
        p = new_project(where, "blocked")
        r = engine(eng, env, "install", str(p), "--ref", "v2.0.0", "--no-register")
        check("install from v2 seeds the new CLAUDE.md", (p / "CLAUDE.md").read_text(encoding="utf-8") == seed_text)
        own = seed_text + "\n## Ours\n\n- a convention\n"
        (p / "CLAUDE.md").write_text(own, encoding="utf-8")
        r = engine(eng, env, "update", str(p), "--ref", "v3.0.0", "--dry-run")
        check("v3 changed the seed block: the dry run announces a block update", re.search(r"block\s+CLAUDE\.md", r.stdout) is not None, r.stdout)
        r = engine(eng, env, "update", str(p), "--ref", "v3.0.0")
        after = (p / "CLAUDE.md").read_text(encoding="utf-8")
        check("update exits 0", r.returncode == 0, r.stdout + r.stderr)
        check("the block now holds v3's import lines", "@.claude/references/hooks.md" in after.split("<!-- <<< engine -->")[0])
        check("every byte outside the markers is the project's, unchanged",
              after.split("<!-- <<< engine -->", 1)[1] == own.split("<!-- <<< engine -->", 1)[1])
        r = engine(eng, env, "update", str(p), "--ref", "v3.0.0")
        actions = [ln for ln in r.stdout.splitlines() if ln.startswith("  block") or ln.startswith("  note")]
        check("a second update changes nothing", not actions and r.returncode == 0, r.stdout)
        (p / "CLAUDE.md").write_text(after.replace("<!-- <<< engine -->", ""), encoding="utf-8")
        r = engine(eng, env, "update", str(p), "--ref", "v3.0.0")
        check("a CLAUDE.md whose end marker was removed is left alone and reported", r.returncode == 0 and "marker" in r.stdout, r.stdout)

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
