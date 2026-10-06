#!/usr/bin/env python3
"""Deleting the root, the home directory or $HOME is refused; deleting a temporary directory
by its absolute path is not — by the deny list and the hook TOGETHER.

The live deny list carries a root rule written as `rm -rf /` followed by `*`. Claude Code's
`*` matches any text (code.claude.com/docs/en/permissions), so that rule also refused a
delete under /tmp. The proposal (docs/tasks/settings.json) narrows it to the exact root and
leaves the catastrophic forms to block-dangerous.sh, whose patterns tell `/` from `/tmp/...`.
It also gives `-fr` the same shape as `-rf`: the old list refused `rm -fr <anything>` while
letting `rm -rf <dir>` through, and the hook knew `-rf` only. Writing this test showed the
`./` + `*` rule has the same defect — it refused `rm -rf ./build`, the most ordinary delete
there is — so it goes the same way: the hook refuses the literal `./*`, the list says nothing.

Two instruments: evals/permission_rules.py (the documented Bash-rule semantics, applied to
the proposal) and the hook itself. A command is REFUSED when either says so.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude/hooks/block-dangerous.sh"
PROPOSAL = ROOT / "docs/tasks/settings.json"
LIVE = ROOT / ".claude/settings.json"

MUST_REFUSE = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf $HOME",
    "rm -fr /",
    "rm -fr /*",
    "rm -fr ~",
    "rm -fr $HOME",
    'rm -rf "$HOME"',
    "rm -rf .",
    "rm -fr ./*",
    "rm -r /",
    "cd /tmp && rm -rf /",
]
MUST_ALLOW = [
    "rm -rf /tmp/claude/scratch",
    "rm -fr /tmp/claude/scratch",
    "rm -rf /private/tmp/sandbox-123",
    "rm -rf /var/folders/xy/T/engine-hooks-abc",
    "rm -rf ./build",
    "rm -fr ./build",
    "rm -rf build dist",
    "rm -rf .venv",
]
# The deny list alone, after the change: what it still refuses and what it hands to the hook.
LIST_REFUSES = ["rm -rf /", "rm -fr /", "rm -rf ~", "rm -fr ~", "rm -rf $HOME", "rm -fr $HOME", "rm -rf .", "rm -r /"]
LIST_HANDS_TO_HOOK = ["rm -rf /*", "rm -fr /*", "rm -rf ./*", "rm -fr ./*"]


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
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
            print(f"  FAIL {name}  {detail[:400]}")


def hook_blocks(cmd: str) -> bool:
    r = subprocess.run(
        ["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}), capture_output=True, text=True, check=False,
        env=hook_env(),
    )
    return r.returncode == 2


def main() -> int:
    rules = load("permission_rules", ROOT / "evals/permission_rules.py")
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    t = Checks()

    def denied_by(settings: dict[str, Any], cmd: str) -> bool:
        verdict: str = rules.decide(settings, cmd)[0]
        return verdict == "deny"

    print("refused by the proposal's deny list OR the hook:")
    for cmd in MUST_REFUSE:
        by_list, by_hook = denied_by(proposal, cmd), hook_blocks(cmd)
        t.check(f"{cmd!r:28} list={'deny' if by_list else '-':4} hook={'block' if by_hook else '-'}", by_list or by_hook)

    print("let through by BOTH:")
    for cmd in MUST_ALLOW:
        by_list, by_hook = denied_by(proposal, cmd), hook_blocks(cmd)
        t.check(f"{cmd!r:44} list={'deny' if by_list else '-':4} hook={'block' if by_hook else '-'}", not by_list and not by_hook)

    print("the division of labour:")
    for cmd in LIST_REFUSES:
        t.check(f"the list itself still refuses {cmd!r}", denied_by(proposal, cmd))
    for cmd in LIST_HANDS_TO_HOOK:
        t.check(f"the list no longer needs to refuse {cmd!r}; the hook does", not denied_by(proposal, cmd) and hook_blocks(cmd))
    t.check("-fr mirrors -rf in the proposal, rule for rule", sorted(
        r.replace("-fr", "-rf") for r in proposal["permissions"]["deny"] if r.startswith("Bash(rm -fr")
    ) == sorted(r for r in proposal["permissions"]["deny"] if r.startswith("Bash(rm -rf")))
    t.check("no rm rule in the proposal ends in a bare wildcard after a slash", not any(
        r.endswith(" /*)") for r in proposal["permissions"]["deny"]
    ), str([r for r in proposal["permissions"]["deny"] if r.endswith(" /*)")]))

    print("the defect this fixes, shown on the live file:")
    live_rm = [r for r in live["permissions"]["deny"] if r.startswith("Bash(rm")]
    if live_rm == [r for r in proposal["permissions"]["deny"] if r.startswith("Bash(rm")]:
        print("  info the live rm rules already equal the proposal's (S7 applied); the defect is history")
    else:
        t.check("live list refuses a delete under /tmp (the defect)", denied_by(live, "rm -rf /tmp/claude/scratch"))
        t.check("live list refuses every rm -fr, even ./build (the inconsistency)", denied_by(live, "rm -fr ./build"))

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
