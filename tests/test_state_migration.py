#!/usr/bin/env python3
"""engine.py moves a project's MACHINE STATE from the pre-3c paths to .claude/state/ — unless
the unattended supervisor appears to be running — and never retires or holds it back.

The owner's reproduction (docs/plan/package-3c-fix.md): install v0.10.1 into an empty repo,
write mode=unattended and .last_audit_sha, update to HEAD — the mode vanished as "retired by
the engine" and the digest was held back as "edited" with exit 1, forever.

Cases, each on a real git repository:
- the reproduction, verbatim;
- a v0.10.1 install and a hand copy of v0.8.0, each with live state at every old path
  (STATE_MIGRATIONS is the list — the test imports it, so the table and the test cannot
  disagree), including a .budget-x.json match, logs/ and archive/: after `update --ref HEAD`
  all state is at the new paths byte for byte, the plan says neither `remove` nor `keep` for a
  state path, exit 0, and a second update changes nothing;
- supervisor.lock at the old place, and separately a fresh heartbeat: state stays, every state
  path is reported as `keep … stop it first`, exit 1, while the project's data still moves.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"


def load_engine() -> Any:
    spec = importlib.util.spec_from_file_location("engine", ENGINE_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["engine"] = module
    spec.loader.exec_module(module)
    return module


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


def state_files(table: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """old relative path -> new relative path, for one concrete file per table entry."""
    out = {}
    for old, new in table:
        if "*" in old:
            name = old.rsplit("/", 1)[1].replace("*", "x")
            out[old.rsplit("/", 1)[0] + "/" + name] = new + name
        elif old.endswith("/"):
            out[old + "sub/entry.log"] = new + "sub/entry.log"
        else:
            out[old] = new
    return out


def write_state(project: Path, files: dict[str, str]) -> dict[str, bytes]:
    data = {}
    for old in files:
        p = project / old
        p.parent.mkdir(parents=True, exist_ok=True)
        content = ("unattended\n" if old.endswith("/mode") else f"state of this machine: {old}\n").encode()
        p.write_bytes(content)
        data[old] = content
    return data


def state_lines(plan: str, files: dict[str, str]) -> list[str]:
    return [line for line in plan.splitlines() if any(old in line or new in line for old, new in files.items())]


def install(tmp_path: Path, env: dict[str, str], name: str, ref: str | None) -> Path:
    p = tmp_path / name
    p.mkdir()
    git(p, "init", "-q", "-b", "main")
    if ref:
        r = engine(env, "install", str(p), "--ref", ref, "--no-register")
        assert r.returncode == 0, r.stdout + r.stderr
    else:  # a hand copy of v0.8.0 the old way
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", "v0.8.0", ".claude", "CLAUDE.md", "AGENTS.md"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-xf", "-", "-C", str(p)], input=archive, check=True)
    return p


def main() -> int:
    eng = load_engine()
    table: tuple[tuple[str, str], ...] = eng.STATE_MIGRATIONS
    files = state_files(table)
    t = Checks()
    head_map = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:.claude/ownership.txt"], capture_output=True, text=True, check=False).stdout
    if "machine  .claude/overseer/mode" not in head_map:
        print("  skip: HEAD does not carry the legacy machine rules yet (commit X2 first)")
        print("\nPASS 0   FAIL 0")
        return 0
    with tempfile.TemporaryDirectory(prefix="state-migration-") as tmp:
        tmp_path = Path(tmp)
        env = {**os.environ, "ENGINE_PROJECTS_FILE": str(tmp_path / "projects.txt")}

        print("the owner's reproduction:")
        p = install(tmp_path, env, "repro", "v0.10.1")
        (p / ".claude/overseer/mode").write_text("unattended\n", encoding="utf-8")
        (p / ".claude/overseer/.last_audit_sha").write_text("abc123\n", encoding="utf-8")
        git(p, "add", "-A"); git(p, "commit", "-qm", "v0.10.1 with state")
        r = engine(env, "update", str(p), "--ref", "HEAD")
        t.check("exit 0", r.returncode == 0, r.stdout + r.stderr)
        t.check("mode=unattended survives, at the new path", (p / ".claude/state/overseer/mode").read_text() == "unattended\n" and not (p / ".claude/overseer/mode").exists())
        t.check(".last_audit_sha moved, not held back", (p / ".claude/state/overseer/.last_audit_sha").read_text() == "abc123\n" and "keep    .claude/overseer/.last_audit_sha" not in r.stdout)
        t.check("no state path was retired", "remove  .claude/overseer/mode" not in r.stdout and "remove  .claude/overseer/.last_audit_sha" not in r.stdout, r.stdout)

        # Live state, no live supervisor: every path but the lock, and a heartbeat older than the
        # stall timeout (a running supervisor is its own case below).
        files = {old: new for old, new in files.items() if not old.endswith("supervisor.lock")}
        stale = time.time() - 2 * eng.STALL_TIMEOUT_S
        for label, ref in (("v0.10.1 install", "v0.10.1"), ("hand copy of v0.8.0", None)):
            print(f"{label} with live state at every old path:")
            p = install(tmp_path, env, label.replace(" ", "-").replace(".", "_"), ref)
            data = write_state(p, files)
            os.utime(p / ".claude/unattended/heartbeat", (stale, stale))
            (p / "PROGRESS.md").write_text("# progress\n", encoding="utf-8")
            git(p, "add", "-A"); git(p, "commit", "-qm", "with state")
            before = {old: (p / old).read_bytes() for old in files}
            r = engine(env, "update", str(p), "--ref", "HEAD", "--dry-run")
            t.check("dry run: writes nothing", {old: (p / old).read_bytes() for old in files} == before)
            t.check("dry run: every state path listed as a move", all(f"move    {old}  — -> {new}" in r.stdout for old, new in files.items()), "\n".join(state_lines(r.stdout, files)))
            r = engine(env, "update", str(p), "--ref", "HEAD")
            t.check("update: exit 0", r.returncode == 0, "\n".join(state_lines(r.stdout, files)) + r.stderr)
            t.check("every state file at its new path, byte for byte", all((p / new).is_file() and (p / new).read_bytes() == data[old] for old, new in files.items()), str([new for old, new in files.items() if not (p / new).is_file()]))
            t.check("nothing left at the old paths", not any((p / old).exists() for old in files), str([old for old in files if (p / old).exists()]))
            t.check("plan: no remove and no keep for any state path", not any(line.strip().startswith(("remove", "keep")) for line in state_lines(r.stdout, files)), "\n".join(state_lines(r.stdout, files)))
            t.check("the project's data moved too", (p / ".engine/PROGRESS.md").is_file() and (p / ".engine/overseer/ledger.md").is_file())
            t.check("old logs/ and archive/ directories are gone", not (p / ".claude/unattended/logs").exists() and not (p / ".claude/unattended/archive").exists())
            snapshot = {str(q.relative_to(p)): q.read_bytes() for q in p.rglob("*") if q.is_file() and ".git" not in q.parts}
            r = engine(env, "update", str(p), "--ref", "HEAD")
            t.check("second update: exit 0, nothing moved, nothing changed", r.returncode == 0 and "move    " not in r.stdout and {str(q.relative_to(p)): q.read_bytes() for q in p.rglob("*") if q.is_file() and ".git" not in q.parts} == snapshot, r.stdout)
            ignore = (p / ".gitignore").read_text(encoding="utf-8")
            t.check("the .gitignore block lists .claude/state/ AND the old state paths", ".claude/state/\n" in ignore and ".claude/overseer/mode\n" in ignore and ".claude/unattended/logs/\n" in ignore)

        print("a live supervisor (supervisor.lock at the old place):")
        p = install(tmp_path, env, "locked", "v0.10.1")
        data = write_state(p, state_files(table))  # the lock included
        git(p, "add", "-A"); git(p, "commit", "-qm", "with lock")
        r = engine(env, "update", str(p), "--ref", "HEAD")
        t.check("exit 1", r.returncode == 1, str(r.returncode))
        t.check("the report says to stop the supervisor first", "stop it first" in r.stdout and "supervisor.lock exists" in r.stdout, "\n".join(state_lines(r.stdout, files)))
        t.check("no state moved", all((p / old).read_bytes() == data[old] for old in files) and not (p / ".claude/state/overseer/mode").exists())
        t.check("the project's data still moved", (p / ".engine/overseer/ledger.md").is_file() and not (p / ".claude/overseer/ledger.md").exists())
        t.check("no state path was removed", not any(line.strip().startswith("remove") for line in state_lines(r.stdout, files)))

        print("a live supervisor (fresh heartbeat, no lock):")
        p = install(tmp_path, env, "beating", "v0.10.1")
        data = write_state(p, files)
        os.utime(p / ".claude/unattended/heartbeat", (time.time(), time.time()))
        git(p, "add", "-A"); git(p, "commit", "-qm", "beating")
        r = engine(env, "update", str(p), "--ref", "HEAD")
        t.check("fresh heartbeat: exit 1 and state stays", r.returncode == 1 and (p / ".claude/overseer/mode").exists() and "heartbeat is" in r.stdout, "\n".join(state_lines(r.stdout, files))[:400])
        old_age = time.time() - 2 * eng.STALL_TIMEOUT_S
        os.utime(p / ".claude/unattended/heartbeat", (old_age, old_age))
        r = engine(env, "update", str(p), "--ref", "HEAD")
        t.check("stale heartbeat: the state moves, exit 0", r.returncode == 0 and (p / ".claude/state/overseer/mode").exists(), r.stdout[:300] + r.stderr)

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
