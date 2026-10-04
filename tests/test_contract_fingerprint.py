#!/usr/bin/env python3
"""A slice contract is sealed when approved; the overseer refuses to audit a contract that
changed afterwards and escalates instead.

- `contract_fingerprint.py seal` writes .claude/state/contracts/<slug>.sha256 and refuses
  (exit 3) to overwrite an existing fingerprint; `check` says match (0) / changed (3) /
  none (4);
- overseer_stop.py, on a unit-completion claim with the structural evidence: sealed and
  unchanged → the audit request as before; sealed and CHANGED → no audit request, a block
  whose reason says the contract changed and asks for an escalation; no fingerprint (a
  contract approved before sealing existed) → the audit request as before.

Each case runs the real hook against a temporary project with .claude/project.env, an
.engine/PROGRESS.md marking the slice IN PROGRESS, the contract, and a transcript whose
current turn edits src/ and runs pytest.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEAL = ROOT / ".claude/hooks/contract_fingerprint.py"
HOOK = ROOT / ".claude/hooks/overseer_stop.py"
CONTRACT = "# Slice tax — planning artifact\n\n## Goal\nCompute tax.\n\n## Exit criterion\nAll three rates.\n"


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


def run(args: list[str], cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_UNATTENDED_SESSION"}
    env["CLAUDE_PROJECT_DIR"] = str(cwd)
    return subprocess.run([sys.executable, *args], cwd=cwd, input=stdin, capture_output=True, text=True, env=env, check=False)


def make_project(root: Path) -> Path:
    (root / ".claude").mkdir(parents=True)
    (root / ".claude/project.env").write_text('SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\n', encoding="utf-8")
    (root / ".engine/slices").mkdir(parents=True)
    (root / ".engine/overseer").mkdir(parents=True)
    (root / ".engine/slices/tax.md").write_text(CONTRACT, encoding="utf-8")
    (root / ".engine/PROGRESS.md").write_text("# PROGRESS\n\n## Slice tax — IN PROGRESS\nPlanning artifact: `.engine/slices/tax.md`.\n", encoding="utf-8")
    # The overseer's handlers: without them the Stop hook makes no request at all (board 033).
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude/settings.json").write_text('{"hooks": {"SubagentStop": [{"matcher": "overseer", "hooks": [{"type": "command", '
                                                '"command": "python3 .claude/hooks/overseer_verdict.py record"}]}]}}\n', encoding="utf-8")
    transcript = root / "transcript.jsonl"
    records = [
        {"type": "user", "message": {"content": "build the tax slice"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": str(root / "src/tax.py")}}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "uv run pytest -x -q"}}]}},
    ]
    transcript.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return root


def stop(root: Path) -> subprocess.CompletedProcess[str]:
    envelope = {"last_assistant_message": "done\n=== UNIT 1 COMPLETE ===\n", "transcript_path": str(root / "transcript.jsonl")}
    # a fresh digest guard per call: the hook refuses to fire twice on one message; and no request
    # left waiting by the call before, or the hook would ask for that one's verdict instead
    for name in (".last_audit_sha", "pending.json"):
        (root / ".claude/state/overseer" / name).unlink(missing_ok=True)
    return run([str(HOOK)], root, json.dumps(envelope))


def decision(r: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    text = r.stdout.strip()
    if not text:
        return "pass", ""
    payload = json.loads(text)
    return str(payload.get("decision", "pass")), str(payload.get("reason", ""))


def main() -> int:
    t = Checks()
    with tempfile.TemporaryDirectory(prefix="contract-fp-") as tmp:
        project = make_project(Path(tmp) / "proj")

        print("the fingerprint tool:")
        r = run([str(SEAL), "check", ".engine/slices/tax.md"], project)
        t.check("check before sealing: exit 4 (no fingerprint)", r.returncode == 4, r.stdout + r.stderr)
        r = run([str(SEAL), "seal", ".engine/slices/tax.md"], project)
        fp = project / ".claude/state/contracts/tax.sha256"
        t.check("seal: exit 0 and the fingerprint file exists under .claude/state/contracts/", r.returncode == 0 and fp.is_file(), r.stdout + r.stderr)
        t.check("seal: the file holds a sha256 and the contract path", len(fp.read_text().split()[0]) == 64 and ".engine/slices/tax.md" in fp.read_text())
        r = run([str(SEAL), "seal", ".engine/slices/tax.md"], project)
        t.check("seal again: REFUSED with exit 3, fingerprint unchanged", r.returncode == 3 and "REFUSED" in r.stderr)
        r = run([str(SEAL), "check", ".engine/slices/tax.md"], project)
        t.check("check: match, exit 0", r.returncode == 0 and "match" in r.stdout, r.stdout)
        r = run([str(SEAL), "seal", ".engine/slices/missing.md"], project)
        t.check("seal of a missing contract: exit 2", r.returncode == 2)

        print("the overseer with a sealed, unchanged contract:")
        d, reason = decision(stop(project))
        t.check("unit-completion claim → the audit request as before", d == "block" and "OVERSEER_REQUEST" in reason, reason[:200])

        print("the overseer with a contract changed after sealing:")
        (project / ".engine/slices/tax.md").write_text(CONTRACT.replace("All three rates.", "One rate is enough."), encoding="utf-8")
        r = run([str(SEAL), "check", ".engine/slices/tax.md"], project)
        t.check("check: CHANGED, exit 3", r.returncode == 3 and "CHANGED" in r.stderr, r.stderr)
        d, reason = decision(stop(project))
        t.check("no audit request", "OVERSEER_REQUEST" not in reason)
        t.check("the turn is blocked with the escalation instruction", d == "block" and "CONTRACT CHANGED AFTER APPROVAL" in reason and "OVERSEER_ESCALATE" in reason, reason[:300])
        t.check("the reason names the contract and the fingerprint", ".engine/slices/tax.md" in reason and ".claude/state/contracts/tax.sha256" in reason)
        d2, _ = decision(run([str(HOOK)], project, json.dumps({"last_assistant_message": "done\n=== UNIT 1 COMPLETE ===\n", "transcript_path": str(project / "transcript.jsonl")})))
        t.check("the same message does not fire twice (idempotency guard shared with the audit)", d2 != "block", d2)

        print("the overseer with no fingerprint at all:")
        fp.unlink()
        d, reason = decision(stop(project))
        t.check("a contract approved before sealing existed is audited as before", d == "block" and "OVERSEER_REQUEST" in reason, reason[:200])

        print("the overseer without the sentinel is untouched:")
        for name in (".last_audit_sha", "pending.json"):
            (project / ".claude/state/overseer" / name).unlink(missing_ok=True)
        r = run([str(HOOK)], project, json.dumps({"last_assistant_message": "ordinary turn", "transcript_path": str(project / "transcript.jsonl")}))
        t.check("no claim → no block", decision(r)[0] != "block", r.stdout)
        r = run([str(HOOK), "--dry-run"], project, "{}")
        t.check("--dry-run still blocks", '"decision": "block"' in r.stdout, r.stdout[:120])

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
