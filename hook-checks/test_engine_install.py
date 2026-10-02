#!/usr/bin/env python3
"""engine.py: install, update, status and adoption do what the ownership map promises.

Most cases run against a small SYNTHETIC engine built here with three tagged versions, so each
expectation is exact and nothing depends on this repository's content. engine.py is copied
into that engine's work tree: it finds its repository relative to itself, which is the rule
under test as much as anything else. The last group adopts a real copy of v0.8.0 made the old
way (`git archive`, as docs/TEMPLATE-SETUP.md used to say) and updates it to this repository's
HEAD. Nothing outside temporary directories is touched; the project list goes to a temp file.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
PASS = FAIL = 0
LOCK = ".claude/engine-lock.json"


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail[:600]}")


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=True).stdout


def git(cwd: Path, *args: str) -> str:
    return sh(cwd, "git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args)


def write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)


def blob(text: str) -> str:
    data = text.encode()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree_digest(project: Path) -> dict[str, str]:
    """Content and mode of every file outside .git — to prove a dry run wrote nothing."""
    out = {}
    for path in sorted(project.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(project).parts:
            out[str(path.relative_to(project))] = f"{oct(path.stat().st_mode)}:{blob(path.read_text())}"
    return out


MAP = """\
machine  .claude/settings.local.json
machine  .claude/state/overseer/mode
machine  .claude/state/
project  .engine/overseer/ledger.md  seed=templates/project/.engine/overseer/ledger.md
project  .engine/architecture/
engine   .claude/**
project  CLAUDE.md  seed=CLAUDE.md
project  **
"""

with tempfile.TemporaryDirectory(prefix="engine-install-test-") as tmp:
    tmp_path = Path(tmp)
    eng = tmp_path / "engine"
    env = {**os.environ, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}

    # --- the synthetic engine: v1, v2, v3 ---------------------------------------------------
    eng.mkdir()
    git(eng, "init", "-q", "-b", "main")
    write(eng / ".claude/ownership.txt", MAP)
    write(eng / ".claude/hooks/a.sh", "echo a1\n", executable=True)
    write(eng / ".claude/hooks/b.sh", "echo b1\n", executable=True)
    write(eng / ".claude/settings.json", '{"v": 1}\n')
    write(eng / ".engine/overseer/ledger.md", "# Ledger\n\n## 2026-08-27 — the engine's own record\n")
    write(eng / ".claude/state/overseer/mode", "unattended\n")  # machine state committed by mistake
    write(eng / "templates/project/.engine/overseer/ledger.md", "# Ledger\n")
    write(eng / "CLAUDE.md", "# Rules v1\n")
    write(eng / "evals/run.py", "print('the engine repository's own tooling')\n")
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v1")
    git(eng, "tag", "v1.0.0")
    write(eng / ".claude/hooks/a.sh", "echo a2\n", executable=True)
    (eng / ".claude/hooks/b.sh").unlink()
    write(eng / ".claude/hooks/c.sh", "echo c2\n", executable=True)
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v2")
    git(eng, "tag", "v2.0.0")
    write(eng / ".claude/hooks/a.sh", "echo a3\n", executable=True)
    write(eng / ".claude/settings.json", '{"v": 3}\n')
    write(eng / "templates/project/.engine/overseer/ledger.md", "# Ledger, v3 seed\n")
    git(eng, "add", "-A")
    git(eng, "commit", "-q", "-m", "v3")
    git(eng, "tag", "v3.0.0")
    shutil.copy2(ENGINE_PY, eng / "engine.py")  # untracked: found through its own location

    def engine(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(eng / "engine.py"), *args], capture_output=True, text=True, env=env, check=False)

    def project(name: str) -> Path:
        p = tmp_path / name
        p.mkdir()
        git(p, "init", "-q", "-b", "main")
        write(p / ".gitignore", ".venv/\n")
        return p

    # --- install into an empty repository -----------------------------------------------------
    p = project("fresh")
    r = engine("install", str(p), "--ref", "v1.0.0")
    check("install: exit 0", r.returncode == 0, r.stdout + r.stderr)
    check("install: engine files arrive", (p / ".claude/hooks/a.sh").read_text() == "echo a1\n")
    check("install: the executable bit comes with them", os.access(p / ".claude/hooks/a.sh", os.X_OK))
    check("install: the ownership map ships", (p / ".claude/ownership.txt").read_text() == MAP)
    check(
        "install: the ledger is the clean seed, not the engine's records",
        (p / ".engine/overseer/ledger.md").read_text() == "# Ledger\n",
    )
    check("install: CLAUDE.md starts from its seed", (p / "CLAUDE.md").read_text() == "# Rules v1\n")
    check("install: machine state never ships", not (p / ".claude/state/overseer/mode").exists())
    check("install: the engine repository's own files never ship", not (p / "evals").exists())
    ignore = (p / ".gitignore").read_text()
    check("install: the project's own ignore lines stay", ignore.startswith(".venv/\n"))
    check(
        "install: machine patterns go into the marked block",
        "# >>> engine:" in ignore and ".claude/state/overseer/mode\n" in ignore and ignore.endswith("# <<< engine\n"),
    )
    lock = __import__("json").loads((p / LOCK).read_text())
    check(
        "install: the lock records ref, commit and blob ids",
        lock["ref"] == "v1.0.0"
        and lock["commit"] == git(eng, "rev-parse", "v1.0.0").strip()
        and lock["files"].get(".claude/hooks/a.sh") == blob("echo a1\n")
        and ".engine/overseer/ledger.md" in lock["seeded"],
        str(lock),
    )
    check(
        "install: the project is listed for update --all",
        (tmp_path / "projects.txt").read_text().strip() == str(p.resolve()),
    )
    r = engine("install", str(p), "--ref", "v1.0.0")
    check(
        "install twice: nothing to do, block not duplicated",
        r.returncode == 0
        and (p / ".gitignore").read_text().count("# >>> engine:") == 1
        and "0 unchanged" not in r.stdout
        and "lock" not in r.stdout.split("total")[0],
        r.stdout,
    )

    # --- dry run ------------------------------------------------------------------------------
    before = tree_digest(p)
    r = engine("update", str(p), "--ref", "v2.0.0", "--dry-run")
    check("dry run: writes nothing", tree_digest(p) == before)
    check(
        "dry run: shows the plan",
        "update  .claude/hooks/a.sh" in r.stdout
        and "remove  .claude/hooks/b.sh" in r.stdout
        and "add     .claude/hooks/c.sh" in r.stdout
        and "dry run" in r.stdout,
        r.stdout,
    )

    # --- update without edits -----------------------------------------------------------------
    r = engine("update", str(p), "--ref", "v2.0.0")
    check("update: exit 0", r.returncode == 0, r.stdout + r.stderr)
    check("update: changed file replaced", (p / ".claude/hooks/a.sh").read_text() == "echo a2\n")
    check("update: retired file removed", not (p / ".claude/hooks/b.sh").exists())
    check("update: new file added", (p / ".claude/hooks/c.sh").read_text() == "echo c2\n")
    check("update: lock moved to v2", __import__("json").loads((p / LOCK).read_text())["ref"] == "v2.0.0")

    # --- a local edit is kept, reported, and taken only on request ------------------------------
    write(p / ".claude/settings.json", '{"v": 1, "mine": true}\n')
    write(p / ".engine/overseer/ledger.md", "# Ledger\n\n## our first entry\n")
    write(p / ".engine/architecture/map.md", "our architecture\n")
    r = engine("update", str(p), "--ref", "v3.0.0")
    check("edit: exit 1 (something held back)", r.returncode == 1, r.stdout + r.stderr)
    check(
        "edit: the edited engine file is kept", (p / ".claude/settings.json").read_text() == '{"v": 1, "mine": true}\n'
    )
    check("edit: and reported", "keep    .claude/settings.json" in r.stdout, r.stdout)
    check("edit: the untouched engine file still updates", (p / ".claude/hooks/a.sh").read_text() == "echo a3\n")
    check(
        "project: the seeded ledger is never overwritten",
        (p / ".engine/overseer/ledger.md").read_text() == "# Ledger\n\n## our first entry\n",
    )
    check(
        "project: project paths are never touched",
        (p / ".engine/architecture/map.md").read_text() == "our architecture\n",
    )
    r = engine("update", str(p), "--ref", "v3.0.0")
    check("edit: stays held back on the next update", r.returncode == 1 and "keep    .claude/settings.json" in r.stdout)
    r = engine("update", str(p), "--ref", "v3.0.0", "--take", ".claude/settings.json")
    check(
        "take: applies the engine's version on request",
        r.returncode == 0 and (p / ".claude/settings.json").read_text() == '{"v": 3}\n',
        r.stdout + r.stderr,
    )
    r = engine("update", str(p), "--ref", "v3.0.0", "--take", "evals/run.py")
    check("take: refuses a path the engine does not own", r.returncode == 2 and "not engine files" in r.stderr)
    (p / ".engine/overseer/ledger.md").unlink()
    r = engine("update", str(p), "--ref", "v3.0.0")
    check(
        "seed: a seed is created once — a deleted project file is not recreated",
        not (p / ".engine/overseer/ledger.md").exists(),
        r.stdout,
    )

    # --- a CRLF checkout of an untouched file counts as untouched --------------------------------
    write(p / ".claude/hooks/c.sh", "echo c2\r\n", executable=True)
    r = engine("status", str(p), "--ref", "v3.0.0")
    check("crlf: not mistaken for an edit", "keep" not in r.stdout and "up to date" in r.stdout, r.stdout)

    # --- adoption of a copy made by hand (no lock), the old way ----------------------------------
    old = project("copied-by-hand")
    archive = subprocess.run(
        ["git", "-C", str(eng), "archive", "v1.0.0", ".claude", ".engine", "CLAUDE.md"], capture_output=True, check=True
    ).stdout
    subprocess.run(["tar", "-xf", "-", "-C", str(old)], input=archive, check=True)
    git(old, "add", "-A")
    git(old, "commit", "-q", "-m", "engine copied by hand")
    write(old / ".claude/settings.json", '{"v": 1, "tuned": true}\n')
    r = engine("status", str(old), "--ref", "v2.0.0")
    check(
        "adopt: status says the copy was not made by the installer", "not installed by engine.py" in r.stdout, r.stdout
    )
    r = engine("update", str(old), "--ref", "v2.0.0")
    out = r.stdout
    check(
        "adopt: an older engine file is recognised and replaced",
        "update  .claude/hooks/a.sh  — an older engine version, adopted" in out
        and (old / ".claude/hooks/a.sh").read_text() == "echo a2\n",
        out,
    )
    check("adopt: a file the engine retired is removed", not (old / ".claude/hooks/b.sh").exists())
    check("adopt: an edited engine file is kept", "keep    .claude/settings.json" in out and r.returncode == 1)
    check(
        "adopt: the engine's records in a project file are reported, not touched",
        "note    .engine/overseer/ledger.md holds only the engine's own records" in out
        and "the engine's own record" in (old / ".engine/overseer/ledger.md").read_text(),
        out,
    )
    check(
        "adopt: tracked machine state is reported",
        "machine state are tracked by git" in out and ".claude/state/overseer/mode" in out,
        out,
    )
    check("adopt: a lock now exists", (old / LOCK).is_file())
    r = engine("update", str(old), "--ref", "v2.0.0", "--reseed-pristine")
    check(
        "reseed: the copied ledger becomes the clean seed",
        (old / ".engine/overseer/ledger.md").read_text() == "# Ledger\n",
        r.stdout,
    )

    # --- refusals -------------------------------------------------------------------------------
    inside = eng / "nested-project"
    inside.mkdir()
    r = engine("install", str(inside), "--ref", "v1.0.0")
    check("refuse: a project inside the engine repository", r.returncode == 2 and "inside the engine" in r.stderr)
    git(eng, "tag", "v0.0.1", git(eng, "rev-list", "--max-parents=0", "HEAD").strip())
    no_map = project("no-map")
    git(eng, "checkout", "-q", "--orphan", "bare")
    git(eng, "rm", "-rq", "--cached", ".")
    write(eng / "only.txt", "no map here\n")
    git(eng, "add", "only.txt")
    git(eng, "commit", "-q", "-m", "a ref without a map")
    git(eng, "tag", "v0.0.0-nomap")
    git(eng, "checkout", "-q", "-f", "main")
    r = engine("install", str(no_map), "--ref", "v0.0.0-nomap")
    check("refuse: a ref that predates the map", r.returncode == 2 and "predates" in r.stderr, r.stderr)
    r = engine("install", str(tmp_path / "missing"), "--ref", "v1.0.0")
    check("refuse: a project directory that does not exist", r.returncode == 2)

    # --- update --all ---------------------------------------------------------------------------
    gone = project("gone")
    engine("install", str(gone), "--ref", "v1.0.0")
    shutil.rmtree(gone)
    r = engine("update", "--all", "--ref", "v3.0.0")
    check(
        "update --all: updates every listed project and reports the one that is gone",
        r.returncode == 0
        and "ok      " + str(p.resolve()) in r.stdout
        and "gone    " + str(gone.resolve()) in r.stdout,
        r.stdout + r.stderr,
    )

    # --- a real copy of v0.8.0, made the old way, adopted by this repository's HEAD --------------
    head_has_map = (
        subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", "HEAD:.claude/ownership.txt"], capture_output=True, check=False).returncode
        == 0
    )
    has_tag = (
        subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", "v0.8.0"], capture_output=True, check=False).returncode
        == 0
    )
    if not (head_has_map and has_tag):
        print("  skip real v0.8.0 adoption: HEAD has no ownership map yet, or v0.8.0 is not here")
    else:
        real = project("real-v0.8.0")
        archive = subprocess.run(
            ["git", "-C", str(ROOT), "archive", "v0.8.0", ".claude", "CLAUDE.md", "AGENTS.md"],
            capture_output=True,
            check=True,
        ).stdout
        subprocess.run(["tar", "-xf", "-", "-C", str(real)], input=archive, check=True)
        git(real, "add", "-A")
        git(real, "commit", "-q", "-m", "v0.8.0 copied by hand")
        cmd = [sys.executable, str(ENGINE_PY), "update", str(real), "--ref", "HEAD"]
        r = subprocess.run(cmd + ["--dry-run"], capture_output=True, text=True, env=env, check=False)
        lines = r.stdout.splitlines()
        check(
            "real v0.8.0: nothing held back in an untouched copy",
            r.returncode == 0 and not any(line.startswith("  keep") for line in lines),
            r.stdout + r.stderr,
        )
        check(
            "real v0.8.0: older engine files are recognised",
            any("an older engine version, adopted" in line for line in lines),
            r.stdout,
        )
        old_ledger = (real / ".claude/overseer/ledger.md").read_bytes()
        r = subprocess.run(cmd + ["--reseed-pristine"], capture_output=True, text=True, env=env, check=False)
        check("real v0.8.0: the update applies", r.returncode == 0, r.stdout + r.stderr)
        ledger_seed = (ROOT / "templates/project/.engine/overseer/ledger.md").read_text()
        # Package 3c: the copy's ledger is first MOVED to its new path intact (a seed never lands on
        # a moving file); only the next update sees it as an unedited old engine record and reseeds.
        check(
            "real v0.8.0: the engine's old ledger moved to .engine/ intact",
            (real / ".engine/overseer/ledger.md").read_bytes() == old_ledger and not (real / ".claude/overseer/ledger.md").exists(),
        )
        r = subprocess.run(cmd + ["--reseed-pristine"], capture_output=True, text=True, env=env, check=False)
        check(
            "real v0.8.0: the next --reseed-pristine replaces the moved old record by the clean seed",
            r.returncode == 0 and (real / ".engine/overseer/ledger.md").read_text() == ledger_seed,
            r.stdout + r.stderr,
        )
        # The sandbox was installed from HEAD, so its hooks are HEAD's; the working tree's hooks
        # equal them only while nothing under .claude/hooks is uncommitted. Comparing while a
        # hook is being edited made this red between the edit and its commit — a false
        # alarm that taught people to ignore the suite. Skip, and say why, until it is clean.
        dirty_hooks = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--", ".claude/hooks"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if dirty_hooks:
            print("  skip real v0.8.0: every hook matches HEAD — .claude/hooks has uncommitted changes:")
            for line in dirty_hooks.splitlines():
                print(f"       {line}")
            print("       (the sandbox holds HEAD's hooks; commit or stash the edits to compare)")
        else:
            hooks_same = all(
                (real / ".claude/hooks" / h.name).read_bytes() == h.read_bytes()
                for h in (ROOT / ".claude/hooks").iterdir()
                if h.is_file()
            )
            check("real v0.8.0: every hook now matches HEAD", hooks_same)
        r = subprocess.run(
            [sys.executable, str(ENGINE_PY), "status", str(real), "--ref", "HEAD"],
            capture_output=True,
            text=True,
            env=env, check=False)
        check("real v0.8.0: status afterwards says up to date", "up to date" in r.stdout, r.stdout + r.stderr)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
