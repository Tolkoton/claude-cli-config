#!/usr/bin/env python3
"""block-dangerous.sh refuses the dangerous forms of a push itself (board 017).

The ask rule in settings.json still prompts for every push; the hook stops, whatever the answer
would be:
  - a forced push in any spelling: the flag anywhere before the separator, `git -C dir push`,
    `git -c k=v push`, several spaces or a tab, a short-flag cluster (-uf), --force-with-lease,
    --force-if-includes, a refspec with a plus, --mirror;
  - the deletion of a remote branch: --delete, -d, a refspec that starts with a colon;
  - a push into a protected branch (main and stable unless PUSH_PROTECTED_BRANCHES in
    .claude/project.env names others): any refspec whose destination it is, --all and
    --branches, and a push that names no branch while one of them is checked out.
The negative cases matter as much: an ordinary push of a working branch, tags, a branch whose
name only contains `main`, `git stash push`, other commands with -f or -d all pass.

The key is the gate's own (gate.py, SCOPE_KEYS): the work being judged may not change it.

Every case runs the real hook against a real throwaway repository on a real branch.

Run:   python3 tests/test_push_hardening.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from hook_env import hook_env, main_repo

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude/hooks/block-dangerous.sh"
GATE = ROOT / ".claude/hooks/gate.py"
PASS = FAIL = 0
F = "--for" + "ce"   # split, so that the hook under test does not refuse THIS file being handled by a shell command


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


def hook(cmd: str, where: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(HOOK)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": where}),
                          capture_output=True, text=True, env=hook_env(where), cwd=where, check=False)


def with_env(root: str, text: str) -> str:
    env_file = Path(root) / ".claude/project.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(text, encoding="utf-8")
    return root


FEAT, MAIN, STABLE, MASTER = main_repo("feat/x"), main_repo("main"), main_repo("stable"), main_repo("master")
OTHER_MAIN = main_repo("main")

REFUSED = [
    # (what it is, the repository the command runs in, the command, a word the reason must carry)
    ("the plain forced push", FEAT, f"git push {F} origin feat/x", "force"),
    ("-f as the last word of the command", FEAT, "git push -f", "force"),
    ("-f before the remote (the old literal pattern answers first)", FEAT, "git push -f origin feat/x", "git push -f"),
    ("the flag after the refspec", FEAT, f"git push origin feat/x {F}", "force"),
    ("git -C <dir> push", FEAT, f"git -C /tmp/x push {F}", "force"),
    ("git -c key=value push", FEAT, f"git -c http.sslVerify=false push origin feat/x {F}", "force"),
    ("several spaces between the words", FEAT, f"git   push    {F}", "force"),
    ("tabs between the words", FEAT, "git\tpush\t-f", "force"),
    ("a short-flag cluster: -uf", FEAT, "git push -uf origin feat/x", "force"),
    ("a short-flag cluster: -fu", FEAT, "git push -fu origin feat/x", "force"),
    ("--force-with-lease", FEAT, f"git push {F}-with-lease origin feat/x", "force"),
    ("--force-with-lease=<ref>", FEAT, f"git push {F}-with-lease=feat/x:abc origin feat/x", "force"),
    ("--force-if-includes", FEAT, f"git push {F}-if-includes origin feat/x", "force"),
    ("a refspec with a plus", FEAT, "git push origin +feat/x", "force"),
    ("a quoted refspec with a plus", FEAT, "git push origin '+feat/x:feat/x'", "force"),
    ("--mirror", FEAT, "git push --mirror origin", "force"),
    ("after a separator: cd && git push", FEAT, f"cd /tmp && git push {F}", "force"),
    ("in the middle of a pipeline", FEAT, f"ls; git push origin feat/x {F} 2>&1 | tail -3", "force"),
    ("git by its full path", FEAT, f"/usr/bin/git push {F}", "force"),
    ("behind env VAR=value", FEAT, "env GIT_SSH=x git push -f", "force"),
    ("inside $( )", FEAT, f"echo $(git push {F})", "force"),
    ("--delete", FEAT, "git push --delete origin feat/old", "deletion"),
    ("-d", FEAT, "git push -d origin feat/old", "deletion"),
    ("a refspec that starts with a colon", FEAT, "git push origin :feat/old", "deletion"),
    ("main as the refspec", FEAT, "git push origin main", "into main"),
    ("HEAD:main", FEAT, "git push origin HEAD:main", "into main"),
    ("<branch>:refs/heads/main", FEAT, "git push origin feat/x:refs/heads/main", "into main"),
    ("stable, with -u", FEAT, "git push -u origin stable", "into stable"),
    ("main as the second refspec", FEAT, "git push origin feat/x main", "into main"),
    ("a quoted HEAD:stable", FEAT, 'git push origin "HEAD:stable"', "into stable"),
    ("main behind git's own option", FEAT, "git --no-pager push origin main", "into main"),
    ("--all", FEAT, "git push --all origin", "every branch"),
    ("--branches", FEAT, "git push --branches origin", "every branch"),
    ("no refspec, main checked out", MAIN, "git push", "into main"),
    ("the remote alone, main checked out", MAIN, "git push origin", "into main"),
    ("HEAD, main checked out", MAIN, "git push origin HEAD", "into main"),
    ("-u origin HEAD, main checked out", MAIN, "git push -u origin HEAD", "into main"),
    ("no refspec, stable checked out", STABLE, "git push", "into stable"),
    ("git -C <a repository on main> push", FEAT, f"git -C {OTHER_MAIN} push", "into main"),
]
ALLOWED = [
    ("no refspec on a working branch", FEAT, "git push"),
    ("the working branch named", FEAT, "git push origin feat/x"),
    ("-u origin <branch>", FEAT, "git push -u origin feat/x"),
    ("HEAD on a working branch", FEAT, "git push origin HEAD"),
    ("--set-upstream, output piped", FEAT, "git push --set-upstream origin feat/x 2>&1 | tail -3"),
    ("the runner's branch", FEAT, "git push origin unattended/work"),
    ("a branch whose name ends in main", FEAT, "git push origin feat/main"),
    ("a destination that only starts with main", FEAT, "git push origin feat/x:feat/main-fix"),
    ("main as the SOURCE of the refspec", FEAT, "git push origin main:feat/copy-of-main"),
    ("a tag", FEAT, "git push origin v1.2.0"),
    ("--tags", FEAT, "git push --tags origin"),
    ("a branch not on the list: release", FEAT, "git push origin release"),
    ("master is not protected by default", FEAT, "git push origin master"),
    ("-o <option> is not a flag cluster", FEAT, "git push -o merge_request.draft origin feat/x"),
    ("-q, then another command", FEAT, "git push -q origin feat/x && echo done"),
    ("git stash push", FEAT, "git stash push -m wip"),
    ("git stash push -- <file>", FEAT, "git stash push -- file.py"),
    ("git log of origin/main", FEAT, "git log --oneline -5 origin/main"),
    ("git diff main", FEAT, "git diff main -- docs/"),
    ("-f of another subcommand", FEAT, "git checkout -f feat/x"),
    ("-d of another subcommand", FEAT, "git branch -d feat/old"),
    ("git fetch origin main", FEAT, "git fetch origin main"),
    ("git pull --rebase origin main", FEAT, "git pull --rebase origin main"),
    ("grep for the word", FEAT, "grep -rn push tests/"),
    ("the words in an echo, no git", FEAT, "echo pushing main"),
    ("docker push of a tag called main", FEAT, "docker push registry/image:main"),
    ("on main, a push of another branch", MAIN, "git push origin feat/x"),
    ("on main, git status", MAIN, "git status"),
    ("on main, git -C <a repository on a working branch> push", MAIN, f"git -C {FEAT} push"),
]

print("the dangerous forms are refused")
for name, where, cmd, word in REFUSED:
    done = hook(cmd, where)
    check(f"{name}: refused, and the reason says why", done.returncode == 2 and word in done.stderr and "block-dangerous.sh" in done.stderr,
          f"{cmd!r} -> exit {done.returncode}: {done.stderr[:200]}")

print("\nthe negative cases: an ordinary push and its neighbours pass")
for name, where, cmd in ALLOWED:
    done = hook(cmd, where)
    check(f"{name}: allowed", done.returncode == 0, f"{cmd!r} -> exit {done.returncode}: {done.stderr[:200]}")

print("\nPUSH_PROTECTED_BRANCHES in .claude/project.env names the branches")
own = with_env(main_repo("feat/x"), 'SOURCE_DIRS="src"\nPUSH_PROTECTED_BRANCHES="master production"\n')
check("a branch the project named: refused", hook("git push origin HEAD:production", own).returncode == 2)
check("... the other one too", hook("git push origin master", own).returncode == 2)
check("the list replaces the default: main is the project's to push", hook("git push origin main", own).returncode == 0)
check("a forced push is refused whatever the list says", hook("git push -f origin feat/x", own).returncode == 2)
commas = with_env(main_repo("feat/x"), "PUSH_PROTECTED_BRANCHES='main,master, production'\n")
check("commas and single quotes read the same", all(hook(f"git push origin {b}", commas).returncode == 2 for b in ("main", "master", "production")))
check("... and a branch outside the list passes", hook("git push origin stable", commas).returncode == 0)
on_master = with_env(MASTER, 'PUSH_PROTECTED_BRANCHES="master"\n')
check("no refspec while the project's protected branch is checked out: refused", hook("git push", on_master).returncode == 2)
for label, text in (("empty", 'PUSH_PROTECTED_BRANCHES=""\n'), ("absent", 'SOURCE_DIRS="src"\n'), ("only spaces", 'PUSH_PROTECTED_BRANCHES="  "\n')):
    quiet = with_env(main_repo("feat/x"), text)
    check(f"the key {label}: main and stable stay protected",
          hook("git push origin main", quiet).returncode == 2 and hook("git push origin HEAD:stable", quiet).returncode == 2
          and hook("git push origin master", quiet).returncode == 0)
tricky = with_env(main_repo("feat/x"), 'PUSH_PROTECTED_BRANCHES="$(touch pwned) main"\n')
done = hook("git push origin main", tricky)
check("the value is read, never executed", done.returncode == 2 and not (Path(tricky) / "pwned").exists(), done.stderr[:200])

print("\nthe key is the gate's own: the work being judged may not change it")
ENV = 'CODE_EXTENSIONS="py"\nTEST_CMD="true"\n'


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def project(env: str = ENV) -> Path:
    root = Path(main_repo("main"))
    with_env(str(root), env)
    (root / ".gitignore").write_text(".claude/state/\n", encoding="utf-8")
    sh(root, "git", "add", "-A")
    done = sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "project")
    assert done.returncode == 0, done.stderr
    return root


def gate(root: Path) -> subprocess.CompletedProcess[str]:
    (root / ".claude/state/gate/stop-count.json").unlink(missing_ok=True)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), CLAUDECODE="1")
    return subprocess.run([sys.executable, str(GATE), "--layer", "stop"], cwd=root, capture_output=True, text=True, env=env, input="", check=False)


def config_findings(root: Path) -> list[str]:
    report = json.loads((root / ".claude/state/gate/last-report.json").read_text(encoding="utf-8"))
    return [f["message"] for f in report["findings"] if f["rule"] == "bypass/config" and f["severity"] == "block"]


def seal(root: Path, text: str) -> None:
    (root / ".engine/slices").mkdir(parents=True, exist_ok=True)
    (root / ".engine/slices/ctr.md").write_text(text, encoding="utf-8")
    (root / ".claude/state/contracts").mkdir(parents=True, exist_ok=True)
    (root / ".claude/state/contracts/ctr.sha256").write_text(f"{hashlib.sha256(text.encode()).hexdigest()}  .engine/slices/ctr.md\n", encoding="utf-8")


r = project()
(r / ".claude/project.env").write_text(ENV + 'PUSH_PROTECTED_BRANCHES="nothing"\n# gate-allow: this project pushes to main itself\n', encoding="utf-8")
done = gate(r)
check("the list emptied of main, with a reason of its own beside it: block",
      done.returncode == 2 and any("PUSH_PROTECTED_BRANCHES" in m for m in config_findings(r)), done.stderr[:400])
seal(r, "# Slice\n\ngate-allow: .claude/project.env — the whole file is ours to tune\n")
check("a grant of the whole file is not enough: block", gate(r).returncode == 2 and bool(config_findings(r)))
seal(r, "# Slice\n\ngate-allow: PUSH_PROTECTED_BRANCHES — the owner moved the release branch\n")
check("the sealed contract names the key: passes", gate(r).returncode == 0 and not config_findings(r), config_findings(r))
r = project()
(r / ".claude/project.env").write_text(ENV + 'PUSH_PROTECTED_BRANCHES="stable, main"\n', encoding="utf-8")
check("writing the default down, in another order and with a comma, is not a change", gate(r).returncode == 0 and not config_findings(r), config_findings(r))
r = project(ENV + 'PUSH_PROTECTED_BRANCHES="main master"\n')
(r / ".claude/project.env").write_text(ENV, encoding="utf-8")
check("dropping the line (master no longer protected) is a change: block",
      gate(r).returncode == 2 and any("PUSH_PROTECTED_BRANCHES" in m for m in config_findings(r)))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
