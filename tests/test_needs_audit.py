#!/usr/bin/env python3
"""evals/needs_audit.py: an audit is due only when text the model reads changed.

A throwaway git repository with the engine's layout; no model, no network.
Run:   python3 tests/test_needs_audit.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "evals" / "needs_audit.py"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:500]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str) -> str:
    sh(root, "git", "add", "-A")
    sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return sh(root, "git", "rev-parse", "HEAD").stdout.strip()


def ask(root: Path, ref: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return sh(root, sys.executable, str(SCRIPT), ref, "--root", str(root), *extra)


FILES = {
    ".claude/skills/overseer/SKILL.md": "skill\n", ".claude/agents/feature-critic.md": "agent\n",
    ".claude/commands/plan-slice.md": "command\n", ".claude/engine-rules.md": "rules\n",
    ".claude/constitution.md": "articles\n", ".claude/references/gate.md": "reference\n",
    ".claude/hooks/overseer_stop.py": "x = 1\n", ".claude/hooks/block-dangerous.sh": "true\n",
    ".claude/settings.json": "{}\n", "CLAUDE.md": "@AGENTS.md\n", "AGENTS.md": "guide\n",
    "templates/project/CLAUDE.md": "seed\n", "evals/run_audit_scenarios.py": "y = 1\n",
    "tests/test_x.py": "z = 1\n", "docs/plan/p.md": "plan\n", "README.md": "readme\n",
    "evals/scenarios/audit/01.md": "scene\n", "evals/scenarios/audit/expected.json": "{}\n",
    "evals/scenarios/audit/work/common/tests/test_pricing.py": "t = 1\n",
    "evals/scenarios/hooks/01.json": "{}\n",
}
root = Path(tempfile.mkdtemp(prefix="needs-audit-"))
sh(root, "git", "init", "-q", "-b", "main")
for rel, text in FILES.items():
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text)
base = commit(root, "base")

print("nothing the model reads")
r = ask(root, base)
check("an unchanged tree: no audit, exit 0", r.returncode == 0 and "NO AUDIT NEEDED" in r.stdout, r.stdout)
for rel in ("evals/run_audit_scenarios.py", "tests/test_x.py", "docs/plan/p.md", "README.md",
            ".claude/hooks/block-dangerous.sh", ".claude/settings.json", "evals/scenarios/hooks/01.json"):
    (root / rel).write_text("changed\n")
(root / "tests/test_new.py").write_text("new = 1\n")
r = ask(root, base)
check("tests, instruments, records, a deny hook, settings, a hook scenario: still no audit",
      r.returncode == 0 and "NO AUDIT NEEDED" in r.stdout and "8 file(s)" in r.stdout, r.stdout)

print("each class of text the model reads, one at a time")
for rel in (".claude/skills/overseer/SKILL.md", ".claude/agents/feature-critic.md", ".claude/commands/plan-slice.md",
            ".claude/engine-rules.md", ".claude/constitution.md", ".claude/references/gate.md", "CLAUDE.md",
            "AGENTS.md", "templates/project/CLAUDE.md",
            # the audit's own scenes: the overseer reads the recorded turn, the tree and the ledger they lay down
            "evals/scenarios/audit/01.md", "evals/scenarios/audit/expected.json",
            "evals/scenarios/audit/work/common/tests/test_pricing.py"):
    original = (root / rel).read_text()
    (root / rel).write_text(original + "one more line\n")
    r = ask(root, base)
    check(f"{rel}: audit needed, exit 1, the file is named",
          r.returncode == 1 and "AUDIT NEEDED (smoke tier)" in r.stdout and f"M {rel}" in r.stdout, r.stdout)
    (root / rel).write_text(original)

print("every way a file can change")
(root / ".claude/skills/new-skill").mkdir()
(root / ".claude/skills/new-skill/SKILL.md").write_text("new\n")
r = ask(root, base)
check("an untracked new skill counts", r.returncode == 1 and "A .claude/skills/new-skill/SKILL.md" in r.stdout, r.stdout)
(root / ".claude/commands/plan-slice.md").unlink()
r = ask(root, base)
check("a deleted command counts", r.returncode == 1 and "D .claude/commands/plan-slice.md" in r.stdout, r.stdout)
sh(root, "git", "mv", ".claude/agents/feature-critic.md", ".claude/agents/feature-judge.md")
r = ask(root, base)
check("a rename is a deletion and an addition", "D .claude/agents/feature-critic.md" in r.stdout
      and "A .claude/agents/feature-judge.md" in r.stdout, r.stdout)
later = commit(root, "committed")
r = ask(root, base)
check("committed since the ref: still counted", r.returncode == 1 and "feature-judge.md" in r.stdout, r.stdout)
check("...and not counted against the later ref", ask(root, later).returncode == 0, ask(root, later).stdout)

print("the MAYBE class, JSON, a bad ref")
(root / ".claude/hooks/overseer_stop.py").write_text("x = 2\n")
r = ask(root, later)
check("a hook that speaks to the model, alone: exit 1, named as MAYBE, not as text",
      r.returncode == 1 and "AUDIT MAYBE NEEDED" in r.stdout and "AUDIT NEEDED (smoke" not in r.stdout
      and "M .claude/hooks/overseer_stop.py" in r.stdout, r.stdout)
data = json.loads(ask(root, base, "--json").stdout)
check("--json carries both lists and the tier",
      data["audit_needed"] is True and data["tier"] == "smoke" and data["maybe"] == ["M .claude/hooks/overseer_stop.py"]
      and "A .claude/skills/new-skill/SKILL.md" in data["text"], data)
r = ask(root, "no-such-ref")
check("a ref that is no commit: exit 2, said on stderr", r.returncode == 2 and "no-such-ref" in r.stderr, r.stderr)
r = sh(ROOT, sys.executable, str(SCRIPT), "HEAD")
check("runs on this repository", r.returncode in (0, 1), r.stderr)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
