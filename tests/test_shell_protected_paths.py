#!/usr/bin/env python3
"""A protected path is refused to a shell command too, not only to Edit/Write (board 714).

protect-paths.sh stands before Edit|Write|MultiEdit; block-dangerous.sh, the hook before Bash,
did not know the protected paths at all: `printf x > .claude/constitution.md`,
`sed -i … .github/workflows/ci.yml` and `cat .env` reached the shell (bug record 002, section 4).
Held here, every case on the real block-dangerous.sh:

  WRITE-*   a command that writes to a protected path is refused (exit 2, the path named);
  SECRET-*  a command that names a secret path is refused, reading included;
  ALLOW-*   reading a guarded file, writing next to it and text that only looks like a secret
            (`jq .key`, `process.env`) stay allowed — a hook that refuses these is switched off
            by its owner within a day;
  LIST-*    the list of paths is one file, sourced by both hooks: a pattern added there is
            honoured by both, and without the file both refuse rather than allow;
  NOPY-*    with no python3 to tell a read from a write, naming a protected path is refused.

Written as a Python file, not shell: the hook scans the whole command text, so a shell line
carrying these literals is refused by the very hook under test.

Run:   python3 tests/test_shell_protected_paths.py
Exit:  0 = all green, 1 = at least one case failed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hook_env import hook_env, main_repo, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
LIST_FILE = "protected-path-list.sh"
SHIPPED = ("block-dangerous.sh", "protect-paths.sh", LIST_FILE, "shell_paths.py")

PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + detail[:300]}")


# The project the commands "run" in: a repository on `main` holding the files whose EXISTENCE
# decides a case (a certificate, a key, an env file with a name of its own).
PROJECT = Path(main_repo())
(PROJECT / "certs").mkdir()
(PROJECT / "certs" / "server.pem").write_text("pem", encoding="utf-8")
(PROJECT / "prod.env").write_text("K=V", encoding="utf-8")
(PROJECT / "sub").mkdir()
(PROJECT / "sub" / "api.key").write_text("k", encoding="utf-8")
HOME = Path(sandbox_dir("hook-home-"))
(HOME / ".ssh").mkdir()
(HOME / ".ssh" / "id_rsa").write_text("k", encoding="utf-8")


def run(cmd: str, hooks: Path = HOOKS, cwd: Path = PROJECT, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(hooks / "block-dangerous.sh")],
        input=json.dumps({"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": cmd}}),
        capture_output=True, text=True, check=False, env=hook_env(PROJECT, HOME=str(HOME), **env))


def run_all(cmds: list[str]) -> list[subprocess.CompletedProcess[str]]:
    """Every case is one run of the real hook; side by side, because there are about ninety."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(run, cmds))


def refused(name: str, cmd: str, names: str, r: subprocess.CompletedProcess[str]) -> None:
    check(f"{name}: {cmd[:70]!r}", r.returncode == 2 and names in r.stderr,
          f"exit {r.returncode}, stderr {r.stderr.strip()[:200]!r}")


def allowed(name: str, cmd: str, r: subprocess.CompletedProcess[str]) -> None:
    check(f"{name}: {cmd[:70]!r}", r.returncode == 0 and not r.stderr.strip(),
          f"exit {r.returncode}, stderr {r.stderr.strip()[:200]!r}")


print("WRITE-*  a shell write to a protected path is refused")
WRITES = [
    # the five commands of the bug record, then every form the task names
    ("redirect", "printf x > .claude/constitution.md", ".claude/constitution.md"),
    ("redirect", "echo {} > .claude/settings.json", ".claude/settings.json"),
    ("append", "echo x >> .claude/settings.local.json", ".claude/settings.local.json"),
    ("redirect, no space", "echo x >.claude/settings.json", ".claude/settings.json"),
    ("redirect, quoted absolute", 'echo x > "/repo/.claude/settings.json"', "/repo/.claude/settings.json"),
    ("redirect of stderr", "make 2> .claude/constitution.md", ".claude/constitution.md"),
    ("redirect after a separator", "ls && echo x > alembic.ini", "alembic.ini"),
    ("heredoc into a workflow", "cat > .github/workflows/ci.yml <<EOF\nname: x\nEOF", ".github/workflows/ci.yml"),
    ("tee", "echo x | tee .claude/constitution.md", ".claude/constitution.md"),
    ("tee -a", "echo x | tee -a /repo/.claude/settings.json", "/repo/.claude/settings.json"),
    ("tee behind a wrapper", "echo x | env A=1 tee .claude/settings.json", ".claude/settings.json"),
    ("sed -i", "sed -i s/a/b/ .github/workflows/ci.yml", ".github/workflows/ci.yml"),
    ("sed -i.bak -e", "sed -i.bak -e s/a/b/ .claude/settings.json", ".claude/settings.json"),
    ("sed -Ei", "sed -Ei 's/a|b/c/' .claude/settings.json", ".claude/settings.json"),
    ("perl -pi", "perl -pi -e s/a/b/ .claude/constitution.md", ".claude/constitution.md"),
    ("cp into it", "cp docs/tasks/settings.json .claude/settings.json", ".claude/settings.json"),
    ("cp behind timeout", "timeout 5 cp /tmp/x .claude/settings.json", ".claude/settings.json"),
    ("mv into it", "mv /tmp/x .claude/constitution.md", ".claude/constitution.md"),
    ("mv it away", "mv .claude/constitution.md /tmp/x", ".claude/constitution.md"),
    ("rm", "rm -f .claude/settings.json", ".claude/settings.json"),
    ("rm a migration", "rm db/migrations/0002_x.py", "db/migrations/0002_x.py"),
    ("git rm", "git rm .github/workflows/ci.yml", ".github/workflows/ci.yml"),
    ("truncate", "truncate -s 0 .claude/constitution.md", ".claude/constitution.md"),
    ("dd of=", "dd if=/tmp/x of=.claude/settings.json", ".claude/settings.json"),
    ("curl -o", "curl -o .github/workflows/ci.yml https://example.com/ci.yml", ".github/workflows/ci.yml"),
    ("python open w", "python3 -c 'open(\".claude/constitution.md\",\"w\").write(\"x\")'", ".claude/constitution.md"),
    ("python open mode=", "python3 -c \"open('.claude/settings.json', mode='a').write('x')\"", ".claude/settings.json"),
    ("python json.dump(open)", "python3 -c \"import json; json.dump({}, open('.claude/settings.json', 'w'))\"", ".claude/settings.json"),
    ("python write_text", "python3 -c \"from pathlib import Path; Path('.claude/settings.json').write_text('{}')\"", ".claude/settings.json"),
    ("python Path.open w", "python3 -c \"from pathlib import Path; Path('.claude/settings.json').open('w')\"", ".claude/settings.json"),
    ("python in a heredoc", "python3 - <<'PY'\nwith open(\n    \".claude/settings.json\",\n    \"a\") as f:\n    f.write('x')\nPY", ".claude/settings.json"),
    ("python shutil.copy", "python3 -c \"import shutil; shutil.copy('/tmp/x', '.claude/settings.json')\"", ".claude/settings.json"),
    ("python os.replace", "python3 -c \"import os; os.replace('/tmp/x', '.claude/constitution.md')\"", ".claude/constitution.md"),
    ("python subprocess rm", "python3 -c \"import subprocess; subprocess.run(['rm', '.claude/settings.json'])\"", ".claude/settings.json"),
    ("python open assigned, no spaces", "python3 -c \"f=open('.claude/settings.json','w'); f.write('x')\"", ".claude/settings.json"),
    ("python open assigned, in a heredoc", "python3 - <<'PY'\nfh=open(\".claude/constitution.md\", \"a\")\nfh.write('x')\nPY", ".claude/constitution.md"),
    ("relative .git, redirect", "echo x > .git/hooks/pre-commit", ".git/hooks/pre-commit"),
    ("relative .git, append", "printf x >> .git/config", ".git/config"),
    ("relative .git, rm", "rm .git/hooks/pre-commit", ".git/hooks/pre-commit"),
    ("relative .git, cp into it", "cp /tmp/h .git/hooks/pre-commit", ".git/hooks/pre-commit"),
    ("relative dotfile secret, written", "echo x > .npmrc", ".npmrc"),
    ("git checkout from another revision", "git checkout HEAD~3 -- .claude/settings.json", ".claude/settings.json"),
    ("git restore from another revision", "git restore --source=HEAD~3 .claude/settings.json", ".claude/settings.json"),
    ("shell inside quotes", "bash -c 'ls; rm .claude/settings.json'", ".claude/settings.json"),
    ("node writeFileSync", "node -e \"require('fs').writeFileSync('.claude/settings.json','{}')\"", ".claude/settings.json"),
    ("a new secret file", "echo k > certs/new.key", "certs/new.key"),
    ("a new env file", "echo K=1 > staging.env", "staging.env"),
]
for (name, cmd, path), res in zip(WRITES, run_all([c for _, c, _ in WRITES]), strict=True):
    refused(f"WRITE {name}", cmd, path, res)

print("SECRET-* a command that names a secret path is refused, reading included")
SECRETS = [
    ("cat", "cat .env", ".env"),
    ("grep", "grep KEY .env", ".env"),
    ("source", "source .env", ".env"),
    ("input redirect", "wc -l < .env", ".env"),
    ("a dotted variant", "head -3 .env.local", ".env.local"),
    ("nested", "cat app/.env", "app/.env"),
    ("copied out", "cp .env /tmp/x", ".env"),
    ("python read", "python3 -c \"print(open('.env').read())\"", ".env"),
    ("secrets dir", "cat app/secrets/token.txt", "app/secrets/token.txt"),
    ("ssh key under ~", "cat ~/.ssh/id_rsa", ".ssh/id_rsa"),
    ("aws credentials under $HOME", "cat $HOME/.aws/credentials", ".aws/credentials"),
    ("credentials.json", "cat config/credentials.json", "config/credentials.json"),
    ("relative dotfile secret, read", "cat .npmrc", ".npmrc"),
    ("relative .ssh", "cat .ssh/config", ".ssh/config"),
    ("relative .aws", "cat .aws/config", ".aws/config"),
    ("a certificate that exists", "cat certs/server.pem", "certs/server.pem"),
    ("an env file that exists", "cat prod.env", "prod.env"),
    ("a key that exists, by glob", "cat sub/*.key", "sub/*.key"),
]
for (name, cmd, path), res in zip(SECRETS, run_all([c for _, c, _ in SECRETS]), strict=True):
    refused(f"SECRET {name}", cmd, path, res)

print("ALLOW-*  reading a guarded file, writing beside it, and look-alikes stay allowed")
ALLOWS = [
    ("the task's negative case", "git diff -- .claude/settings.json"),
    ("the task's negative case", "grep -n hooks .claude/settings.json"),
    ("read the constitution", "cat .claude/constitution.md"),
    ("read with jq", "jq .permissions .claude/settings.json"),
    ("read a workflow", "sed -n 1,5p .github/workflows/ci.yml"),
    ("list migrations", "ls db/migrations/0001_init.py"),
    ("history of a workflow", "git log --oneline -- .github/workflows/ci.yml"),
    ("copy it OUT", "cp .claude/settings.json /tmp/settings-copy.json"),
    ("redirect goes elsewhere", "git diff -- .claude/settings.json > /tmp/d.txt"),
    ("stderr to /dev/null", "diff docs/tasks/settings.json .claude/settings.json 2>/dev/null"),
    ("fd duplication", "wc -l .claude/settings.json 2>&1 | tee /tmp/o.txt"),
    ("python reads it", "python3 -c \"import json; print(len(json.load(open('.claude/settings.json'))))\""),
    ("python reads it, writes elsewhere", "python3 -c \"import json; d = json.load(open('.claude/settings.json')); open('/tmp/x.json', 'w').write(json.dumps(d))\""),
    ("revert it from git", "git checkout -- .claude/settings.json"),
    ("revert it from git, HEAD named", "git checkout HEAD -- .claude/settings.json"),
    ("revert it from git, restore", "git restore .claude/settings.json"),
    ("read under .git", "cat .git/config"),
    ("a stale git lock removed", "rm -f .git/index.lock"),
    ("the allowlisted config, read", "cat .claude/project.env"),
    ("the allowlisted config, written", "echo X=1 >> .claude/project.env"),
    ("the allowlisted config, joined with /", "python3 -c \"from pathlib import Path; (Path('.') / '.claude' / 'project.env').write_text('X=1')\""),
    ("an edit scripted with str.replace", "python3 -c \"from pathlib import Path; p = Path('docs/x.md'); p.write_text(p.read_text().replace('see .claude/settings.json', 'see the settings'))\""),
    ("a placeholder in a message", "python3 .claude/unattended/board.py open-item --what 'a file under <root>/.claude/constitution.md is refused'"),
    ("jq filter, not a key file", "jq -r .key data.json"),
    ("code, not an env file", "grep -rn process.env src/"),
    ("code, not an env file", "grep -rn 'process.env.API_KEY' src/"),
    ("a certificate that is not there", "ls certs/missing.pem"),
    ("ordinary in-place edit", "sed -i s/a/b/ src/app.py"),
    ("ordinary redirect", "echo x > notes.txt"),
    ("ordinary rm", "rm -rf ./build"),
    ("the suites of these hooks", "python3 tests/test_guardrail_paths.py"),
]
for (name, cmd), res in zip(ALLOWS, run_all([c for _, c in ALLOWS]), strict=True):
    allowed(f"ALLOW {name}", cmd, res)

print("LIST-*   one list of paths for both hooks")


def copy_hooks() -> Path:
    d = Path(tempfile.mkdtemp(prefix="hooks-copy-", dir=sandbox_dir()))
    for f in SHIPPED:
        if (HOOKS / f).exists():
            shutil.copy(HOOKS / f, d / f)
    return d


def edit_refused(hooks: Path, path: str) -> tuple[bool, subprocess.CompletedProcess[str]]:
    r = subprocess.run(
        ["bash", str(hooks / "protect-paths.sh")],
        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": path}}),
        capture_output=True, text=True, check=False, env=hook_env(PROJECT))
    return ('"deny"' in r.stdout or r.returncode == 2), r


check("LIST the list file exists", (HOOKS / LIST_FILE).is_file())
for hook in ("block-dangerous.sh", "protect-paths.sh"):
    text = (HOOKS / hook).read_text(encoding="utf-8")
    check(f"LIST {hook} sources the list and keeps none of its own",
          LIST_FILE in text and "PROTECTED_PATTERNS=(" not in text)

for rel in (".git/config", ".npmrc", ".ssh/config"):
    check(f"LIST a path relative to the project root is refused to Edit as well: {rel}", edit_refused(HOOKS, rel)[0])

extra = copy_hooks()
if (extra / LIST_FILE).exists():
    with (extra / LIST_FILE).open("a", encoding="utf-8") as fh:
        fh.write("\nGUARDED_PATTERNS+=('(^|/)Jenkinsfile$')\nPROTECTED_PATTERNS+=('(^|/)Jenkinsfile$')\n")
r = run("echo x > Jenkinsfile")
check("LIST control: the shipped list does not know Jenkinsfile (shell)", r.returncode == 0, r.stderr)
check("LIST control: the shipped list does not know Jenkinsfile (edit)", not edit_refused(HOOKS, "Jenkinsfile")[0])
r = run("echo x > Jenkinsfile", hooks=extra)
check("LIST a pattern added to the list is refused to a shell write", r.returncode == 2 and "Jenkinsfile" in r.stderr,
      f"exit {r.returncode} {r.stderr[:200]!r}")
check("LIST the same pattern is refused to Edit", edit_refused(extra, "Jenkinsfile")[0])
r = run("cat Jenkinsfile", hooks=extra)
check("LIST a guarded (not secret) pattern is still readable", r.returncode == 0, r.stderr)

gone = copy_hooks()
(gone / LIST_FILE).unlink(missing_ok=True)
r = run("ls -la", hooks=gone)
check("LIST without the list block-dangerous.sh refuses, says why", r.returncode == 2 and LIST_FILE in r.stderr,
      f"exit {r.returncode} {r.stderr[:200]!r}")
denied, r = edit_refused(gone, "src/app.py")
check("LIST without the list protect-paths.sh refuses, says why", r.returncode == 2 and LIST_FILE in r.stderr,
      f"exit {r.returncode} {r.stderr[:200]!r}")

print("NOPY-*   no python3: naming a protected path is refused, ordinary commands are not")
shims = Path(tempfile.mkdtemp(prefix="nopy-", dir=sandbox_dir()))
for tool in ("bash", "cat", "echo", "grep", "sed", "tr", "git", "jq", "dirname", "printf"):
    src = shutil.which(tool)
    if src:
        os.symlink(src, shims / tool)
r = run("git diff -- .claude/settings.json", PATH=str(shims))
check("NOPY a protected path named, nothing to judge it with -> refused, says why",
      r.returncode == 2 and "python3" in r.stderr, f"exit {r.returncode} {r.stderr[:200]!r}")
r = run("printf x > .claude/constitution.md", PATH=str(shims))
check("NOPY the write itself is refused", r.returncode == 2, f"exit {r.returncode}")
r = run("ls -la src", PATH=str(shims))
check("NOPY an ordinary command is allowed", r.returncode == 0, f"exit {r.returncode} {r.stderr[:200]!r}")

print()
print(f"PASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
