#!/usr/bin/env python3
"""env-probe.sh prints the facts the commit policy decides on, as key=value lines, and never
a secret.

- every line is `key=value`; the keys the report relies on are present;
- a cloud-shaped environment is recognised (session_kind=cloud) and the probe's own
  commit-policy verdict follows the switch;
- the VALUE of ANTHROPIC_API_KEY never appears in the output, while its NAME does;
- a user:token@ part in a remote URL is masked;
- exit 0 even outside a git repository.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_env import trace_env

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / ".claude/unattended/env-probe.sh"
SECRET = "sk-ant-THIS-VALUE-MUST-NEVER-BE-PRINTED-0123456789"
REQUIRED_KEYS = {
    "probe_version", "utc", "hostname", "os", "session_kind", "env.CLAUDE_CODE_REMOTE",
    "env.CLAUDE_CODE_REMOTE_SESSION_ID", "env.CLAUDE_PROJECT_DIR", "env_names_claude_anthropic",
    "env.ANTHROPIC_API_KEY", "git_toplevel", "settings_user", "settings_project", "settings_local",
    "hooks_dir", "mode_file", "cloud_commit_policy", "tool.git", "tool.jq", "tool.python3",
    "commit_policy_here",
}


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
            print(f"  FAIL {name}  {detail[:500]}")


def probe(project: Path, extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/"), "CLAUDE_PROJECT_DIR": str(project), **trace_env()}
    env.update(extra)
    return subprocess.run(["bash", str(PROBE)], capture_output=True, text=True, env=env, check=False, cwd=project if project.is_dir() else None)


def parse(out: str) -> dict[str, str]:
    pairs = [line.split("=", 1) for line in out.splitlines() if line]
    return {k: v for k, v in pairs if len([k, v]) == 2}


def main() -> int:
    t = Checks()
    with tempfile.TemporaryDirectory(prefix="env-probe-") as tmp:
        project = Path(tmp) / "proj"
        project.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
        subprocess.run(["git", "remote", "add", "origin", "https://user:ghp_SECRETTOKEN@github.com/o/r.git"], cwd=project, check=True)
        (project / ".claude/hooks").mkdir(parents=True)
        for hook_file in ("block-dangerous.sh", "protected-path-list.sh"):   # the hook refuses without its list
            (project / ".claude/hooks" / hook_file).write_bytes((ROOT / ".claude/hooks" / hook_file).read_bytes())
        (project / ".claude/project.env").write_text('CLOUD_COMMIT_POLICY="off"\n', encoding="utf-8")
        (project / "f").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i"], cwd=project, check=True)
        subprocess.run(["git", "switch", "-qc", "claude/session-9"], cwd=project, check=True)

        # --- local, attended ------------------------------------------------------------------
        r = probe(project, {"ANTHROPIC_API_KEY": SECRET})
        facts = parse(r.stdout)
        t.check("exit 0", r.returncode == 0, r.stderr)
        t.check("every line is key=value", all("=" in line for line in r.stdout.splitlines() if line))
        missing = REQUIRED_KEYS - set(facts)
        t.check("the keys the report relies on are present", not missing, str(sorted(missing)))
        t.check("attended-local is recognised", facts.get("session_kind") == "attended-local", facts.get("session_kind", ""))
        t.check("the secret's VALUE is nowhere in the output", SECRET not in r.stdout and "ghp_SECRETTOKEN" not in r.stdout, r.stdout[:300])
        t.check("the secret's NAME is reported as set", facts.get("env.ANTHROPIC_API_KEY") == "<set, value withheld>" and "ANTHROPIC_API_KEY" in facts.get("env_names_claude_anthropic", ""))
        t.check("the remote URL's credentials are masked", "***@github.com" in facts.get("git_remotes", ""), facts.get("git_remotes", ""))
        t.check("branch and checkout kind are reported", facts.get("git_branch") == "claude/session-9" and facts.get("git_checkout_kind") == "main-checkout")
        t.check("the switch is read", facts.get("cloud_commit_policy") == "off")
        t.check("local on a session branch: the policy refuses", facts.get("commit_policy_here", "").startswith("refuse"), facts.get("commit_policy_here", ""))

        # --- cloud-shaped -----------------------------------------------------------------------
        r = probe(project, {"CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_REMOTE_SESSION_ID": "sess-123"})
        facts = parse(r.stdout)
        t.check("cloud is recognised from CLAUDE_CODE_REMOTE=true", facts.get("session_kind") == "cloud")
        t.check("the session id is printed (not a secret)", facts.get("env.CLAUDE_CODE_REMOTE_SESSION_ID") == "sess-123")
        t.check("cloud with the switch off: the policy refuses", facts.get("commit_policy_here", "").startswith("refuse"))
        (project / ".claude/project.env").write_text('CLOUD_COMMIT_POLICY="session-branch"\n', encoding="utf-8")
        r = probe(project, {"CLAUDE_CODE_REMOTE": "true"})
        facts = parse(r.stdout)
        t.check("cloud with the switch on: the policy allows on the session branch", facts.get("commit_policy_here") == "allow", facts.get("commit_policy_here", ""))

        # --- not a git repository at all --------------------------------------------------------
        bare = Path(tmp) / "bare"
        bare.mkdir()
        r = probe(bare, {})
        t.check("outside git: still exit 0 and says so", r.returncode == 0 and "<not a git work tree>" in r.stdout, r.stdout[:200])

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
