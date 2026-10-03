#!/usr/bin/env python3
"""engine.py release: a version tag, and `main` and `stable` moved onto it — only by the owner.

Every case runs against a SYNTHETIC engine repository built here, with a bare repository
beside it as its remote. engine.py is copied into the synthetic work tree (it finds its
repository relative to itself). The two checks a release runs — the full suites and the golden
set — are stubs there: each appends one line to a log outside the repository and exits with
the code an environment variable names, so a case can make either one red and can prove that a
refused release ran neither. Nothing outside a temporary directory is touched, and nothing
here reaches a network: the only push goes to the bare repository on disk.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
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
        shutil.copy(ENGINE_PY, self.work / "engine.py")
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
        self.head = commit(self.work, "work to release")

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
