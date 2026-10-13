#!/usr/bin/env python3
"""env-check.sh: silent on a complete machine, specific on an incomplete one, never failing."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import trace_env

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "env-check.sh"
PASS = FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


def path_with(*tools: str) -> str:
    d = Path(tempfile.mkdtemp(prefix="envcheck-"))
    for tool in tools:
        src = shutil.which(tool)
        if src:
            os.symlink(src, d / tool)
    return str(d)


LINUX = "Linux version 6.8.0-1070-gcp (buildd@lcy02-amd64-051) (x86_64-linux-gnu-gcc-12) #76-Ubuntu SMP"
WSL2 = "Linux version 5.15.167.4-microsoft-standard-WSL2 (root@f9c826d3017f) (gcc (GCC) 11.2.0) #1 SMP"
WSL1 = "Linux version 4.4.0-19041-Microsoft (Microsoft@Microsoft.com) (gcc version 5.4.0 (GCC) ) #1237-Microsoft"


def kernel(line: str) -> str:
    """A stand-in for /proc/version: the hook reads the kernel line from the file ENGINE_PROC_VERSION names."""
    f = Path(tempfile.mkdtemp(prefix="envcheck-proc-")) / "version"
    f.write_text(line + "\n")
    return str(f)


def home(autocrlf: str = "") -> str:
    """A home directory whose git configuration is known: nothing, or core.autocrlf set."""
    d = Path(tempfile.mkdtemp(prefix="envcheck-home-"))
    if autocrlf:
        (d / ".gitconfig").write_text(f"[core]\n\tautocrlf = {autocrlf}\n")
    return str(d)


def run(project: Path, path: str, proc: str = LINUX, home_dir: str = "", **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOK)], capture_output=True, text=True,
        env={"PATH": path, "CLAUDE_PROJECT_DIR": str(project), "HOME": home_dir or home(),
             "GIT_CONFIG_NOSYSTEM": "1", "ENGINE_PROC_VERSION": kernel(proc), **trace_env(), **extra}, check=False)


bash = shutil.which("bash")
assert bash, "bash is required to run this test"

plain = Path(tempfile.mkdtemp(prefix="envcheck-plain-"))          # no pyproject.toml
uvproj = Path(tempfile.mkdtemp(prefix="envcheck-uv-"))
(uvproj / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
(uvproj / "uv.lock").write_text("")
bare = Path(tempfile.mkdtemp(prefix="envcheck-bare-"))            # configured, no lock file
(bare / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")

full = path_with("bash", "git", "grep", "python3", "jq", "uv")
res = run(plain, full)
check("complete machine, plain project: silent", res.returncode == 0 and res.stdout == "", res.stdout[:80])

res = run(uvproj, path_with("bash", "git", "grep", "python3", "jq"))
check("uv.lock but no uv: names uv", res.returncode == 0 and "- uv " in res.stdout, res.stdout[:80])

res = run(plain, path_with("bash", "git", "grep", "jq"))
check("no python3: names the three Python hooks", "overseer_stop.py" in res.stdout, res.stdout[:80])
check("no python3 but jq present: does NOT claim the deny hooks refuse", "REFUSE" not in res.stdout)

res = run(plain, path_with("bash", "git", "grep"))
check("neither jq nor python3: says the deny hooks will refuse", "REFUSE" in res.stdout, res.stdout[:80])

res = run(plain, path_with("bash", "git", "grep", "python3"))
check("python3 without jq: silent (the hooks fall back, nothing is lost that matters)",
      res.stdout == "", res.stdout[:80])

res = run(bare, path_with("bash", "git", "grep", "python3", "jq"))
check("ruff/mypy configured, no lock file, not on PATH: names both",
      "- ruff " in res.stdout and "- mypy " in res.stdout, res.stdout[:80])

res = run(plain, path_with("bash", "grep", "python3", "jq"))
check("no git: says so and still exits 0", res.returncode == 0 and "- git " in res.stdout, res.stdout[:80])

# Windows is supported through WSL2 only (docs/WINDOWS.md): inside it the machine is Linux, and the
# hook names the two traps that come from the Windows side. The signs are faked: the kernel line
# and the project's path. /mnt/c/... need not exist — the hook judges the path, not the disk.
windows_disk = Path("/mnt/c/work/shop")
res = run(plain, full, proc=WSL2)
check("WSL2, project in the Linux home, git leaves line endings alone: silent",
      res.returncode == 0 and res.stdout == "", res.stdout[:80])

res = run(windows_disk, full, proc=WSL2)
check("WSL2, project on a Windows disk: names the path, says slow and permissions, points to the Linux home",
      res.returncode == 0 and "/mnt/c/work/shop" in res.stdout and "slow" in res.stdout
      and "permission" in res.stdout and "~/" in res.stdout, res.stdout[:200])
check("...and says nothing about line endings when git does not change them", "autocrlf" not in res.stdout, res.stdout[:200])

res = run(plain, full, proc=WSL2, home_dir=home("true"))
check("WSL2, core.autocrlf=true: names the setting and advises input",
      res.returncode == 0 and "core.autocrlf" in res.stdout and "git config --global core.autocrlf input" in res.stdout, res.stdout[:200])
check("...and says nothing about the disk when the project is in the Linux home", "/mnt/" not in res.stdout, res.stdout[:200])

res = run(plain, full, proc=WSL2, home_dir=home("input"))
check("WSL2, core.autocrlf=input: silent", res.stdout == "", res.stdout[:80])

res = run(windows_disk, full, proc=WSL2, home_dir=home("true"))
check("WSL2, both traps: both are named", "/mnt/c/" in res.stdout and "core.autocrlf" in res.stdout, res.stdout[:200])

res = run(windows_disk, full, proc=WSL1)
check("the older kernel line (capital Microsoft) is recognised too", "/mnt/c/" in res.stdout, res.stdout[:80])

res = run(windows_disk, full, proc=LINUX, home_dir=home("true"))
check("negative — plain Linux with the same path and the same git setting: silent", res.stdout == "", res.stdout[:200])

res = run(Path("/mnt/data/shop"), full, proc=WSL2)
check("negative — WSL2, /mnt/data is not a Windows drive letter: silent", res.stdout == "", res.stdout[:80])

res = run(windows_disk, path_with("bash", "grep", "python3", "jq"), proc=WSL2, home_dir=home("true"))
check("WSL2 without git: the disk and the missing git are named, the git setting is not asked, exit 0",
      res.returncode == 0 and "- git " in res.stdout and "/mnt/c/" in res.stdout and "autocrlf" not in res.stdout, res.stdout[:200])

res = subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, check=False,
                     env={"PATH": full, "CLAUDE_PROJECT_DIR": str(plain), "HOME": home(), "ENGINE_PROC_VERSION": "/nonexistent/version", **trace_env()})
check("no kernel line to read (macOS has no /proc): silent, exit 0", res.returncode == 0 and res.stdout == "" , res.stdout[:80] + res.stderr[:80])

# Board 750 (owner): in every cloud session a shallow clone gets its whole history and its tags at the start — the
# engine and every installed project, no switch, nothing said when it works. A git shim records its argv and answers
# the two questions the hook asks; the last case does it for real on a shallow clone of a local repository.
FETCH = "fetch -q --unshallow --tags origin"


def git_shim(shallow: str, fetch_rc: int = 0, *tools: str) -> tuple[str, Path]:
    d = Path(tempfile.mkdtemp(prefix="envcheck-git-"))
    log = d / "git.log"
    log.write_text("")
    (d / "git").write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        f'case "$*" in *"rev-parse --is-shallow-repository"*) echo {shallow}; exit 0 ;; *" fetch "*) exit {fetch_rc} ;; esac\n'
        f'exec "{shutil.which("git")}" "$@"\n')
    (d / "git").chmod(0o755)
    for tool in ("bash", "grep", "python3", "jq", *tools):
        src = shutil.which(tool)
        if src:
            os.symlink(src, d / tool)
    return str(d), log


cloud_path, log = git_shim("true", 0, "timeout")
res = run(plain, cloud_path, CLAUDE_CODE_REMOTE="true")
check("cloud session, shallow clone: the whole history and the tags are fetched, and nothing is said",
      res.returncode == 0 and f"-C {plain} {FETCH}" in log.read_text() and res.stdout == "", log.read_text() + res.stdout[:200])

seeded = Path(tempfile.mkdtemp(prefix="envcheck-seed-"))
(seeded / ".claude").mkdir()
shutil.copy(ROOT / "templates/project/.claude/project.env", seeded / ".claude/project.env")
no_timeout, log = git_shim("true")
res = run(seeded, no_timeout, CLAUDE_CODE_REMOTE="true")
check("an installed project (the seed project.env, no key for it) on a machine without `timeout`: fetched too, silently",
      res.returncode == 0 and f"-C {seeded} {FETCH}" in log.read_text() and res.stdout == "", log.read_text() + res.stdout[:200])

failing, log = git_shim("true", 128)
res = run(plain, failing, CLAUDE_CODE_REMOTE="true")
check("the fetch fails: exit 0 and one line for the agent naming the command, not a question for the owner",
      res.returncode == 0 and "git fetch --unshallow --tags origin" in res.stdout and "shallow" in res.stdout
      and res.stdout.count("\n- ") == 1 and "Tell the user" not in res.stdout, res.stdout[:300])

# Board 761: the fetch runs under `timeout`, below the time Claude Code gives the hook itself (the `timeout` of the
# SessionStart entry in settings.json; 60 s when it names none) — a hung fetch must end before the whole hook is
# killed, or the failure line and the lesson digest after it are lost. A `timeout` shim records its argv.
settings = json.loads((ROOT / ".claude/settings.json").read_text())
HOOK_LIMIT = next(h.get("timeout", 60) for entry in settings["hooks"]["SessionStart"] for h in entry["hooks"]
                  if "env-check.sh" in h.get("command", ""))


def timeout_shim(path: str, body: str) -> Path:
    """Put a `timeout` on the shim PATH that records its argv, then does `body`."""
    shim = Path(path) / "timeout"
    shim.unlink(missing_ok=True)
    shim.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{Path(path) / "timeout.log"}"\n{body}\n')
    shim.chmod(0o755)
    return Path(path) / "timeout.log"


limited, log = git_shim("true")
tlog = timeout_shim(limited, 'shift; exec "$@"')
res = run(plain, limited, CLAUDE_CODE_REMOTE="true")
argv = tlog.read_text() if tlog.exists() else ""
under = re.fullmatch(rf"(\d+)s? git -C {re.escape(str(plain))} {FETCH}\n", argv)
check(f"cloud session, shallow clone, `timeout` on PATH: the fetch runs as `timeout <n> git -C <root> fetch …`, n under the hook's {HOOK_LIMIT} s",
      res.returncode == 0 and under is not None and 0 < int(under.group(1)) < HOOK_LIMIT and res.stdout == "",
      f"timeout argv: {argv!r}; {res.stdout[:200]}")

memory = Path(tempfile.mkdtemp(prefix="envcheck-memory-"))
(memory / ".claude").mkdir()
(memory / ".claude/hooks").symlink_to(ROOT / ".claude/hooks")
(memory / ".engine/overseer").mkdir(parents=True)
(memory / ".engine/overseer/MEMORY.md").write_text("## 2026-08-27 — A pattern\n")
cut, log = git_shim("true")
timeout_shim(cut, "exit 124")                                     # the limit reached: the fetch never came back
res = run(memory, cut, CLAUDE_CODE_REMOTE="true")
check("the fetch is cut off at the limit (`timeout` answers 124): exit 0, the one line, and the lesson digest still follows it",
      res.returncode == 0 and " fetch " not in log.read_text() and res.stdout.count("git fetch --unshallow --tags origin") == 1
      and 0 < res.stdout.find("shallow") < res.stdout.find("## lessons"), res.stdout[:400])

for name, env, answer in (("negative — not a cloud session (no CLAUDE_CODE_REMOTE), shallow clone", {}, "true"),
                          ("negative — CLAUDE_CODE_REMOTE=false, shallow clone", {"CLAUDE_CODE_REMOTE": "false"}, "true"),
                          ("negative — cloud session, the clone is not shallow", {"CLAUDE_CODE_REMOTE": "true"}, "false")):
    shim_path, log = git_shim(answer, 0, "timeout")
    res = run(plain, shim_path, **env)
    check(f"{name}: no fetch, silent", res.returncode == 0 and " fetch " not in log.read_text() and res.stdout == "",
          log.read_text() + res.stdout[:200])

origin = Path(tempfile.mkdtemp(prefix="envcheck-origin-"))
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(origin)]
subprocess.run(["git", "init", "-q", str(origin)], check=True)
for n in range(3):
    (origin / "f.txt").write_text(f"{n}\n")
    subprocess.run([*GIT, "add", "f.txt"], check=True)
    subprocess.run([*GIT, "commit", "-qm", f"c{n}"], check=True)
    if n == 0:
        subprocess.run([*GIT, "tag", "v0.1"], check=True)
clone = Path(tempfile.mkdtemp(prefix="envcheck-clone-")) / "repo"
subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(clone)], check=True)


def in_clone(*args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True, check=False).stdout.strip()


before = (in_clone("rev-parse", "--is-shallow-repository"), in_clone("rev-list", "--count", "HEAD"), in_clone("tag"))
res = run(clone, path_with("bash", "git", "grep", "python3", "jq", "timeout"), CLAUDE_CODE_REMOTE="true")
after = (in_clone("rev-parse", "--is-shallow-repository"), in_clone("rev-list", "--count", "HEAD"), in_clone("tag"))
check("for real: a shallow clone (1 commit, no tag) comes out whole (3 commits, the tag v0.1), silently",
      before == ("true", "1", "") and after == ("false", "3", "v0.1") and res.returncode == 0 and res.stdout == "",
      f"{before} -> {after}; {res.stdout[:200]}")

lost = Path(tempfile.mkdtemp(prefix="envcheck-lost-")) / "repo"
subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(lost)], check=True)
subprocess.run(["git", "-C", str(lost), "remote", "set-url", "origin", f"file://{origin}-gone"], check=True)
res = run(lost, path_with("bash", "git", "grep", "python3", "jq", "timeout"), CLAUDE_CODE_REMOTE="true")
check("for real, the origin unreachable: exit 0, the one line, and git's own error kept out of the session",
      res.returncode == 0 and "git fetch --unshallow --tags origin" in res.stdout and "fatal" not in res.stdout + res.stderr,
      res.stdout[:200] + res.stderr[:200])

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
