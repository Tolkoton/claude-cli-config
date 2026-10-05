#!/usr/bin/env python3
"""engine.py release: a version tag, and `main` and `stable` moved onto it — only by the owner.

Every case runs against a SYNTHETIC engine repository built here, with a bare repository
beside it as its remote. engine.py is copied into the synthetic work tree (it finds its
repository relative to itself). The two checks a release runs — the full suites and the golden
set — are stubs there: each appends one line to a log outside the repository and exits with
the code an environment variable names, so a case can make either one red and can prove that a
refused release ran neither. Nothing outside a temporary directory is touched, and nothing
here reaches a network: the only push goes to the bare repository on disk.

The audit check (board 047) is real there: evals/needs_audit.py and the board's journal writer are
copied in, and the synthetic repository records a complete full-tier audit of the commit it
releases, so a case changes a text the model reads — or the audit's record — to make it stale.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
COPIED = ("engine.py", "evals/needs_audit.py", ".claude/unattended/board.py")
SKILL = ".claude/skills/demo/SKILL.md"
JOURNAL = "tasks/ANOMALIES.md"
PASS = FAIL = 0
IDENT = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")

RUN_ALL_STUB = """\
#!/usr/bin/env bash
echo "tests $*" >> "$FAKE_LOG"
[ -n "${FAKE_TESTS_DIRTY:-}" ] && echo left-behind > left-behind.txt
exit "${FAKE_TESTS_RC:-0}"
"""
GOLDEN_STUB = """\
import os, sys
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write("golden " + " ".join(sys.argv[1:]) + "\\n")
sys.exit(int(os.environ.get("FAKE_GOLDEN_RC", "0")))
"""


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail[:900]}")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *IDENT, *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def ref(cwd: Path, name: str) -> str:
    """The commit a ref points at, or "" when the ref does not exist."""
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}"], cwd=cwd, capture_output=True, text=True, check=False
    )
    return proc.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(work: Path, message: str, path: str = "notes.txt") -> str:
    with (work / path).open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", message)
    return git(work, "rev-parse", "HEAD")


class Repo:
    """A synthetic engine: `work` on branch unattended/work, `remote` a bare repository with main at v0.1.0."""

    def __init__(self, base: Path) -> None:
        self.remote = base / "remote.git"
        self.work = base / "work"
        self.log = base / "checks.log"
        git(base, "init", "-q", "--bare", "-b", "main", str(self.remote))
        git(base, "init", "-q", "-b", "main", str(self.work))
        for path in COPIED:
            (self.work / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / path, self.work / path)
        write(self.work / SKILL, "the words a model reads\n")
        write(self.work / "tasks/README.md", "the board\n")
        write(self.work / "tests/run_all.sh", RUN_ALL_STUB)
        write(self.work / "evals/run_hook_scenarios.py", GOLDEN_STUB)
        write(self.work / "evals/baseline/box/results-old.json", "{}\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", "the engine")
        git(self.work, "tag", "-a", "v0.1.0", "-m", "v0.1.0")
        git(self.work, "remote", "add", "origin", str(self.remote))
        git(self.work, "push", "-q", "origin", "main", "v0.1.0")
        git(self.work, "switch", "-q", "-c", "unattended/work")
        write(self.work / "evals/baseline/box/results-new.json", "{}\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", "a newer baseline")
        self.audited = commit(self.work, "work to release")
        self.head = self.audit("audit-work.json", self.audited)

    def audit(self, name: str, engine_commit: str, **fields: str) -> str:
        """Commit the record of an audit of `engine_commit` (full and complete unless `fields` say otherwise)."""
        record = {"tier": "full", "status": "complete", "recorded_utc": "2026-01-01T00:00:00Z", "engine_commit": engine_commit} | fields
        write(self.work / "evals/baseline/box" / name, json.dumps(record) + "\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", f"the record {name}")
        return git(self.work, "rev-parse", "HEAD")

    def journal(self) -> str:
        path = self.work / JOURNAL
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def release(self, *args: str, session: bool = False, **env: str) -> subprocess.CompletedProcess[str]:
        environ = {k: v for k, v in os.environ.items() if k != "CLAUDECODE" and not k.startswith("FAKE_")}
        environ.update(env, FAKE_LOG=str(self.log), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        if session:
            environ["CLAUDECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(self.work / "engine.py"), "release", *args],
            cwd=self.work, env=environ, capture_output=True, text=True, check=False,
        )

    def ran(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def state(self) -> dict[str, str]:
        """Every ref of the work tree and of the remote: a refused release must leave this equal."""
        return {
            "work": git(self.work, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags"),
            "remote": git(self.remote, "for-each-ref", "--format=%(refname) %(objectname)"),
            "head": git(self.work, "rev-parse", "HEAD"),
        }


def refused(name: str, repo: Repo, proc: subprocess.CompletedProcess[str], before: dict[str, str], says: str, checks_ran: bool) -> None:
    out = proc.stdout + proc.stderr
    check(f"{name}: exit 2", proc.returncode == 2, f"rc={proc.returncode} {out}")
    check(f"{name}: says why ({says!r})", says in out, out)
    check(f"{name}: no ref moved, here or on the remote", repo.state() == before, f"{before}\n{repo.state()}")
    check(f"{name}: the checks {'ran' if checks_ran else 'did not run'}", bool(repo.ran()) == checks_ran, str(repo.ran()))


def fresh(base: Path, name: str) -> Repo:
    directory = base / name
    directory.mkdir()
    return Repo(directory)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        print("without the owner's flag nothing happens")
        repo = fresh(base, "noflag")
        before = repo.state()
        refused("no --owner-approved", repo, repo.release("v0.2.0"), before, "--owner-approved", checks_ran=False)
        refused("the flag inside an agent session", repo, repo.release("v0.2.0", "--owner-approved", session=True),
                before, "CLAUDECODE", checks_ran=False)

        print("the version")
        for version, says in (("0.2.0", "vMAJOR.MINOR.PATCH"), ("v0.2", "vMAJOR.MINOR.PATCH"), ("v0.1.0", "already exists"),
                              ("v0.0.9", "not newer than v0.1.0")):
            refused(f"version {version}", repo, repo.release(version, "--owner-approved"), before, says, checks_ran=False)

        print("the work tree must be clean")
        repo = fresh(base, "dirty")
        before = repo.state()
        write(repo.work / "stray.txt", "x\n")
        refused("an untracked file", repo, repo.release("v0.2.0", "--owner-approved"), before, "not clean", checks_ran=False)
        (repo.work / "stray.txt").unlink()
        write(repo.work / "notes.txt", "edited\n")
        refused("an edited file", repo, repo.release("v0.2.0", "--owner-approved"), before, "not clean", checks_ran=False)

        print("red checks stop the release")
        repo = fresh(base, "red")
        before = repo.state()
        refused("red suites", repo, repo.release("v0.2.0", "--owner-approved", FAKE_TESTS_RC="1"), before, "tests are red", checks_ran=True)
        check("red suites: the golden set was not started", repo.ran() == ["tests "], str(repo.ran()))
        repo.log.unlink(missing_ok=True)
        refused("golden set differs", repo, repo.release("v0.2.0", "--owner-approved", FAKE_GOLDEN_RC="1"), before,
                "golden set", checks_ran=True)
        check("golden set: compared with the baseline committed last",
              repo.ran()[-1] == "golden --engine-ref HEAD --compare evals/baseline/box/results-new.json", str(repo.ran()))
        repo.log.unlink(missing_ok=True)
        refused("--baseline names a missing file", repo, repo.release("v0.2.0", "--owner-approved", "--baseline", "nope.json"),
                before, "nope.json", checks_ran=False)
        refused("--baseline picks the file", repo,
                repo.release("v0.2.0", "--owner-approved", "--baseline", "evals/baseline/box/results-old.json", FAKE_GOLDEN_RC="1"),
                before, "golden set", checks_ran=True)
        check("--baseline: that file was compared", repo.ran()[-1].endswith("--compare evals/baseline/box/results-old.json"), str(repo.ran()))
        repo.log.unlink(missing_ok=True)
        proc = repo.release("v0.2.0", "--owner-approved", FAKE_TESTS_DIRTY="1")
        (repo.work / "left-behind.txt").unlink()
        refused("the checks left a file behind", repo, proc, before, "not clean", checks_ran=True)

        print("the baseline of this environment comes first")
        repo = fresh(base, "environment")
        write(repo.work / "evals/environment.py", 'print("home")\n')
        write(repo.work / "evals/baseline/home/results-mine.json", "{}\n")
        git(repo.work, "add", "-A")
        git(repo.work, "commit", "-q", "-m", "this environment's baseline")
        write(repo.work / "evals/baseline/other/results-newer.json", "{}\n")
        git(repo.work, "add", "-A")
        git(repo.work, "commit", "-q", "-m", "a newer baseline of another environment")
        proc = repo.release("v0.2.0", "--owner-approved", FAKE_GOLDEN_RC="1")
        check("own environment: its baseline is compared, not the newer one of another",
              repo.ran()[-1].endswith("--compare evals/baseline/home/results-mine.json") and "CROSS-ENVIRONMENT" not in proc.stdout,
              str(repo.ran()) + proc.stdout)
        repo.log.unlink(missing_ok=True)
        write(repo.work / "evals/environment.py", 'print("elsewhere")\n')
        git(repo.work, "add", "-A")
        git(repo.work, "commit", "-q", "-m", "an environment without a baseline")
        proc = repo.release("v0.2.0", "--owner-approved", FAKE_GOLDEN_RC="1")
        check("no baseline of this environment: the newest of any, and the release says it is cross-environment",
              repo.ran()[-1].endswith("--compare evals/baseline/other/results-newer.json")
              and "CROSS-ENVIRONMENT" in proc.stdout and "elsewhere" in proc.stdout, str(repo.ran()) + proc.stdout)

        print("fast-forward only")
        repo = fresh(base, "diverged")
        other = base / "diverged" / "other"
        git(base, "clone", "-q", str(repo.remote), str(other))
        commit(other, "someone else's work on main", "other.txt")
        git(other, "push", "-q", "origin", "main")
        before = repo.state()
        proc = repo.release("v0.2.0", "--owner-approved")
        out = proc.stdout + proc.stderr
        check("remote main moved elsewhere: exit 2", proc.returncode == 2, out)
        check("remote main moved elsewhere: says fast-forward", "fast-forward" in out and "origin/main" in out, out)
        after = repo.state()
        check("remote main moved elsewhere: no tag, no branch moved",
              (after["work"], after["remote"]) == (before["work"], before["remote"]), f"{before}\n{after}")
        check("remote main moved elsewhere: the checks did not run", repo.ran() == [], str(repo.ran()))

        repo = fresh(base, "stable-ahead")
        git(repo.work, "switch", "-q", "-c", "side", "main")
        side = commit(repo.work, "a commit only stable has", "side.txt")
        git(repo.work, "push", "-q", "origin", f"{side}:refs/heads/stable")
        git(repo.work, "switch", "-q", "unattended/work")
        git(repo.work, "branch", "-q", "-D", "side")
        before = repo.state()
        refused("remote stable is not behind HEAD", repo, repo.release("v0.2.0", "--owner-approved"), before, "origin/stable",
                checks_ran=False)

        repo = fresh(base, "local-main-ahead")
        git(repo.work, "switch", "-q", "main")
        commit(repo.work, "local main only", "local.txt")
        git(repo.work, "switch", "-q", "unattended/work")
        before = repo.state()
        refused("local main is not behind HEAD", repo, repo.release("v0.2.0", "--owner-approved"), before, "main", checks_ran=False)

        print("a rejected push leaves nothing behind")
        repo = fresh(base, "rejected")
        hook = repo.remote / "hooks" / "pre-receive"
        write(hook, "#!/bin/sh\necho 'the remote says no' >&2\nexit 1\n")
        hook.chmod(0o755)
        before = repo.state()
        refused("the remote rejects the push", repo, repo.release("v0.2.0", "--owner-approved"), before, "push", checks_ran=True)

        print("a release")
        repo = fresh(base, "good")
        proc = repo.release("v0.2.0", "--owner-approved")
        out = proc.stdout + proc.stderr
        check("release: exit 0", proc.returncode == 0, out)
        check("release: both checks ran, suites first", [line.split()[0] for line in repo.ran()] == ["tests", "golden"], str(repo.ran()))
        check("release: the tag is on HEAD", ref(repo.work, "refs/tags/v0.2.0") == repo.head)
        check("release: the tag is annotated", git(repo.work, "cat-file", "-t", "v0.2.0") == "tag")
        for where, cwd in (("remote", repo.remote), ("local", repo.work)):
            check(f"release: {where} tag on HEAD", ref(cwd, "refs/tags/v0.2.0") == repo.head)
            check(f"release: {where} main on HEAD", ref(cwd, "refs/heads/main") == repo.head)
            check(f"release: {where} stable created on HEAD", ref(cwd, "refs/heads/stable") == repo.head)
        check("release: still on the branch it started from", git(repo.work, "symbolic-ref", "--short", "HEAD") == "unattended/work")
        check("release: the work tree is still clean", git(repo.work, "status", "--porcelain") == "")
        check("release: says what it did", "released v0.2.0" in out and repo.head[:7] in out, out)

        check("release: says which audit covers it", "audit-work.json" in out and repo.audited[:7] in out, out)
        check("release: nothing written into the journal", repo.journal() == "")

        print("the next release moves stable forward; the same version twice is refused")
        before = repo.state()
        repo.log.unlink(missing_ok=True)
        refused("v0.2.0 again", repo, repo.release("v0.2.0", "--owner-approved"), before, "already exists", checks_ran=False)
        newer = commit(repo.work, "more work")
        proc = repo.release("v0.3.0", "--owner-approved", "--message", "engine v0.3.0: more work")
        check("second release: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("second release: remote stable moved forward", ref(repo.remote, "refs/heads/stable") == newer)
        check("second release: remote main moved forward", ref(repo.remote, "refs/heads/main") == newer)
        check("second release: v0.2.0 stays where it was", ref(repo.remote, "refs/tags/v0.2.0") == repo.head)
        check("second release: --message is the tag's subject",
              git(repo.work, "tag", "-l", "--format=%(subject)", "v0.3.0") == "engine v0.3.0: more work")

        print("a text the model reads changed after the last full audit")
        repo = fresh(base, "stale-audit")
        commit(repo.work, "a reworded skill", SKILL)
        before = repo.state()
        proc = repo.release("v0.2.0", "--owner-approved")
        out = proc.stdout + proc.stderr
        refused("text changed, no fresh audit", repo, proc, before, "full audit", checks_ran=False)
        check("stale audit: names the changed file and the audit it is measured from",
              f"M {SKILL}" in out and "audit-work.json" in out, out)
        check("stale audit: names the command to run",
              "evals/run_audit_scenarios.py --tier full" in out and "audit-v0.2.0.json" in out, out)
        check("stale audit: names the owner's flag", "--without-audit" in out, out)
        check("stale audit: nothing written into the journal", repo.journal() == "")
        refused("a smoke audit of the new text does not count", repo,
                (repo.audit("audit-smoke.json", before["head"], tier="smoke", recorded_utc="2026-02-01T00:00:00Z"),
                 repo.release("v0.2.0", "--owner-approved"))[1], repo.state(), "full audit", checks_ran=False)
        refused("a full audit that stopped half way does not count", repo,
                (repo.audit("audit-partial.json", before["head"], status="partial", recorded_utc="2026-02-02T00:00:00Z"),
                 repo.release("v0.2.0", "--owner-approved"))[1], repo.state(), "full audit", checks_ran=False)
        refused("the bypass flag inside an agent session", repo,
                repo.release("v0.2.0", "--owner-approved", "--without-audit", session=True), repo.state(), "CLAUDECODE", checks_ran=False)
        check("bypass in a session: nothing written into the journal", repo.journal() == "")
        repo.audit("audit-again.json", before["head"], recorded_utc="2026-02-03T00:00:00Z")
        proc = repo.release("v0.2.0", "--owner-approved")
        check("a full audit of the new text: released", proc.returncode == 0 and "audit-again.json" in proc.stdout, proc.stdout + proc.stderr)

        print("no full audit at all")
        repo = fresh(base, "no-audit")
        git(repo.work, "rm", "-q", "evals/baseline/box/audit-work.json")
        git(repo.work, "commit", "-q", "-m", "the audit's record is gone")
        before = repo.state()
        refused("no full audit recorded", repo, repo.release("v0.2.0", "--owner-approved"), before, "full audit", checks_ran=False)

        print("the owner's bypass: released, and written into the journal")
        repo = fresh(base, "bypass")
        skill = commit(repo.work, "a reworded skill", SKILL)
        proc = repo.release("v0.2.0", "--owner-approved", "--without-audit")
        out = proc.stdout + proc.stderr
        check("bypass: exit 0", proc.returncode == 0, out)
        check("bypass: the checks ran", [line.split()[0] for line in repo.ran()] == ["tests", "golden"], str(repo.ran()))
        check("bypass: the tag, main and stable are on HEAD, here and on the remote",
              {ref(cwd, r) for cwd in (repo.work, repo.remote) for r in ("refs/tags/v0.2.0", "refs/heads/main", "refs/heads/stable")} == {skill})
        entry = repo.journal()
        check("bypass: one journal entry", entry.count("\n## ") == 1, entry)
        check("bypass: the entry names the version, the flag, the changed file and the owner",
              all(part in entry for part in ("v0.2.0", "--without-audit", SKILL, "Хто записав: власник")), entry)
        check("bypass: the release says where it is recorded", JOURNAL in out, out)
        check("bypass: the journal is the only thing left in the work tree",
              git(repo.work, "status", "--porcelain").split() == ["??", JOURNAL], git(repo.work, "status", "--porcelain"))

        print("the bypass flag with a fresh audit bypasses nothing")
        repo = fresh(base, "bypass-unneeded")
        proc = repo.release("v0.2.0", "--owner-approved", "--without-audit")
        check("unneeded bypass: released", proc.returncode == 0, proc.stdout + proc.stderr)
        check("unneeded bypass: nothing written into the journal", repo.journal() == "")

        print("a bypass whose release fails leaves no journal entry")
        repo = fresh(base, "bypass-rejected")
        commit(repo.work, "a reworded skill", SKILL)
        write(repo.work / JOURNAL, "# the journal\n")
        git(repo.work, "add", "-A")
        git(repo.work, "commit", "-q", "-m", "a journal")
        hook = repo.remote / "hooks" / "pre-receive"
        write(hook, "#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        before = repo.state()
        refused("bypass, the remote rejects the push", repo, repo.release("v0.2.0", "--owner-approved", "--without-audit"),
                before, "push", checks_ran=True)
        check("bypass, rejected push: the journal is as it was", repo.journal() == "# the journal\n", repo.journal())
        repo.log.unlink(missing_ok=True)
        refused("bypass, red suites", repo, repo.release("v0.2.0", "--owner-approved", "--without-audit", FAKE_TESTS_RC="1"),
                before, "tests are red", checks_ran=True)
        check("bypass, red suites: the journal is as it was", repo.journal() == "# the journal\n", repo.journal())

        print("released from main itself")
        repo = fresh(base, "on-main")
        git(repo.work, "switch", "-q", "main")
        git(repo.work, "merge", "-q", "--ff-only", "unattended/work")
        proc = repo.release("v0.2.0", "--owner-approved")
        check("on main: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("on main: remote main, stable and the tag on HEAD",
              {ref(repo.remote, r) for r in ("refs/heads/main", "refs/heads/stable", "refs/tags/v0.2.0")} == {repo.head})

        print("a tag only the remote has")
        repo = fresh(base, "remote-tag")
        git(repo.work, "tag", "-a", "v0.2.0", "-m", "pushed from elsewhere", "main")
        git(repo.work, "push", "-q", "origin", "v0.2.0")
        git(repo.work, "tag", "-d", "v0.2.0")
        proc = repo.release("v0.2.0", "--owner-approved")
        check("remote-only tag: refused", proc.returncode == 2 and "already exists" in proc.stderr, proc.stdout + proc.stderr)
        check("remote-only tag: main not moved", ref(repo.remote, "refs/heads/main") != repo.head)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
