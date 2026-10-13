#!/usr/bin/env python3
"""The golden set answers the same wherever it is run: a hook never inherits WHERE the runner stands (board 780).

A cloud container has CLAUDE_CODE_REMOTE=true and the board's runner sets CLAUDE_UNATTENDED_SESSION=1.
`evals/run_hook_scenarios.py` hands neither on to a hook: a scenario that is about the place sets
the variable itself (as the cloud scenarios do). Found in board 097: in a cloud session
`bd-commit-local-with-cloud-switch-on` — a commit «locally» — was allowed, because
block-dangerous.sh saw the container's variable.

  1. a synthetic sandbox with one hook that refuses when it sees either variable, naming it: the
     runner started with both set — a scenario with no `env` passes; negative — a scenario that
     sets a variable itself still reaches the hook with it;
  2. the real golden set under CLAUDE_CODE_REMOTE=true: the local commit scenario is refused, and
     the cloud scenarios, which set the variable themselves, answer as before.

Run:   python3 tests/test_golden_place_env.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "evals/run_hook_scenarios.py"
PLACE = {"CLAUDE_CODE_REMOTE": "true", "CLAUDE_UNATTENDED_SESSION": "1"}
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[-600:]}")


work = Path(tempfile.mkdtemp(prefix="golden-place-env-"))


def run(*argv: object, **place: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in hook_env(work, ENGINE_HEALTH_DIR=str(work / "health")).items() if k not in PLACE} | place
    return subprocess.run([sys.executable, str(RUNNER), *map(str, argv)], capture_output=True, text=True, cwd=ROOT, env=env, check=False)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   capture_output=True, text=True, check=True)


def shown(r: subprocess.CompletedProcess[str]) -> str:
    return f"rc={r.returncode} {r.stdout[-400:]} {r.stderr[-200:]}"


print("a synthetic sandbox: the hook refuses when it sees where the runner stands")
SEES = ('for name in CLAUDE_CODE_REMOTE CLAUDE_UNATTENDED_SESSION; do\n'
        '  [ -n "${!name:-}" ] && { echo "sees $name=${!name}" >&2; exit 2; }\n'
        'done\nexit 0\n')
sandbox = work / "sandbox"
(sandbox / ".claude" / "hooks").mkdir(parents=True)
(sandbox / ".claude" / "hooks" / "h.sh").write_text(SEES, encoding="utf-8")
(sandbox / "SANDBOX-INFO.json").write_text("{}\n", encoding="utf-8")
git(sandbox, "init", "-q", "-b", "main")
git(sandbox, "add", "-A")
git(sandbox, "commit", "-q", "-m", "sandbox")


def synthetic(name: str, scenario: dict[str, Any], **place: str) -> subprocess.CompletedProcess[str]:
    folder = work / f"scenarios-{name}"
    folder.mkdir()
    (folder / "a.json").write_text(json.dumps({"hook": "h.sh", "scenarios": [{"id": name, "input": {}, **scenario}]}), encoding="utf-8")
    return run("--sandbox", sandbox, "--scenarios", folder, **place)


r = synthetic("cloud-runner", {"expect": "allow"}, CLAUDE_CODE_REMOTE="true")
check("the runner in a cloud session (CLAUDE_CODE_REMOTE=true): a scenario with no `env` reaches the hook without it (board 780)",
      r.returncode == 0 and "PASS 1/1" in r.stdout, shown(r))
r = synthetic("board-runner", {"expect": "allow"}, CLAUDE_UNATTENDED_SESSION="1")
check("the runner under the board's runner (CLAUDE_UNATTENDED_SESSION=1): the hook does not see that either",
      r.returncode == 0 and "PASS 1/1" in r.stdout, shown(r))
r = synthetic("both", {"expect": "allow"}, **PLACE)
check("both at once: neither reaches the hook", r.returncode == 0 and "PASS 1/1" in r.stdout, shown(r))
r = synthetic("own-cloud", {"expect": "block", "expect_detail_contains": "sees CLAUDE_CODE_REMOTE=true", "env": {"CLAUDE_CODE_REMOTE": "true"}})
check("negative: a scenario that sets CLAUDE_CODE_REMOTE itself reaches the hook with it", r.returncode == 0 and "PASS 1/1" in r.stdout, shown(r))
r = synthetic("own-unattended", {"expect": "block", "expect_detail_contains": "sees CLAUDE_UNATTENDED_SESSION=1", "env": {"CLAUDE_UNATTENDED_SESSION": "1"}},
              CLAUDE_CODE_REMOTE="true")
check("negative: ...and one that sets CLAUDE_UNATTENDED_SESSION itself, with it and without the runner's own CLAUDE_CODE_REMOTE",
      r.returncode == 0 and "PASS 1/1" in r.stdout, shown(r))
r = synthetic("the-hook-refuses", {"expect": "allow", "env": {"CLAUDE_CODE_REMOTE": "true"}})
check("negative: the synthetic hook does refuse what it sees — an `allow` expectation fails there",
      r.returncode == 1 and "FAIL the-hook-refuses" in r.stdout, shown(r))

print("the real golden set, the runner started with CLAUDE_CODE_REMOTE=true")
r = run("--engine-ref", "HEAD", "--only", "bd-commit-", CLAUDE_CODE_REMOTE="true")
lines = {line.split()[1]: line.split()[0] for line in r.stdout.splitlines() if line.split()[:1] in (["ok"], ["FAIL"])}
check("the local commit with the cloud switch on is refused, as on the owner's machine (board 780)",
      lines.get("bd-commit-local-with-cloud-switch-on") == "ok" and r.returncode == 0, shown(r))
cloud = [name for name in lines if name.startswith("bd-commit-cloud-")]
check("negative: the cloud commit scenarios set the variable themselves and answer as before",
      len(cloud) >= 3 and all(lines[name] == "ok" for name in cloud), shown(r))
check("a partial run leaves no health record", not (work / "health").exists() or not list((work / "health").iterdir()))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
