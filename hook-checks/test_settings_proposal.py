#!/usr/bin/env python3
"""The proposed shared settings (docs/tasks/settings.json) plus the personal layer
(user/settings.json) are, in effect, exactly today's settings.

The owner applies the proposal by hand (protect-paths.sh refuses .claude/settings.json to
an agent), so this is the test of that one file. It holds before and after the apply:

- the effective settings of {home fixture + personal layer, proposal} equal the frozen
  effective settings of {home fixture, the shared file as it was before the split}
  (docs/tasks/effective-before-split.json) — except for the differences this file lists
  on purpose, each with the reason;
- the proposal carries no personal key, and its hooks block is byte-for-byte the live one
  (applying it changes no hook wiring);
- once the live .claude/settings.json equals the proposal, that is reported as applied.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROPOSAL = ROOT / "docs/tasks/settings.json"
LIVE = ROOT / ".claude/settings.json"
PERSONAL = ROOT / "user/settings.json"
FROZEN = ROOT / "docs/tasks/effective-before-split.json"
HOME_FIXTURE = ROOT / "hook-checks/fixtures/home-settings.json"
PERSONAL_KEYS = ("defaultMode", "additionalDirectories")
PERSONAL_ALLOW = ("WebFetch", "WebSearch")
PERSONAL_ENV = (
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
)

APPROVE_HANDLER = 'PermissionRequest|Edit|Write|MultiEdit|command|python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/approve-project-data.py"'

# Differences against the frozen "before" that are intended. Path -> why.
INTENDED: dict[str, str] = {
    "permissions.deny": (
        "S4: the root rule `rm -rf /` + `*` matched any text and refused a delete under /tmp; now the exact root, "
        "with -fr given the same shape as -rf (hook-checks/test_root_delete_deny.py)"
    ),
    "permissions.defaultMode": (
        "F4 (owner): the personal layer says `auto`, not `acceptEdits`; `auto` is legal at the user level only, "
        "which is where the layer lives. Unattended sessions do not depend on it: session-claude.sh passes "
        "--permission-mode acceptEdits itself"
    ),
    "env.ANTHROPIC_DEFAULT_SONNET_MODEL": "F4 (owner): removed, not moved — pinning a model id freezes an old model",
    "env.ANTHROPIC_DEFAULT_OPUS_MODEL": "F4 (owner): removed, not moved — pinning a model id freezes an old model",
    "env.ANTHROPIC_DEFAULT_HAIKU_MODEL": "F4 (owner): removed, not moved — pinning a model id freezes an old model",
    "env.CLAUDE_CODE_SUBAGENT_MODEL": "F4 (owner): removed — the variable is not documented at code.claude.com/docs/en/env-vars",
}


def load_module(name: str, path: Path) -> Any:
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
            print(f"  FAIL {name}  {detail[:800]}")


def main() -> int:
    parity = load_module("settings_parity", ROOT / "evals/settings_parity.py")
    engine = load_module("engine", ROOT / "engine.py")
    t = Checks()

    proposal: dict[str, Any] = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    live: dict[str, Any] = json.loads(LIVE.read_text(encoding="utf-8"))
    personal_raw: dict[str, Any] = json.loads(PERSONAL.read_text(encoding="utf-8"))

    # --- the proposal holds nothing personal --------------------------------------------------
    perm = proposal["permissions"]
    t.check("proposal: no defaultMode / additionalDirectories", not any(k in perm for k in PERSONAL_KEYS))
    t.check("proposal: WebFetch/WebSearch are not blanket-allowed", not any(a in perm["allow"] for a in PERSONAL_ALLOW))
    t.check("proposal: no model variables under env", not any(k in proposal.get("env", {}) for k in PERSONAL_ENV))
    t.check("personal layer: no model variables either (removed, not moved)", "env" not in {k: v for k, v in personal_raw.items() if not k.startswith("_")})
    t.check("personal layer: defaultMode auto", personal_raw["permissions"].get("defaultMode") == "auto")
    # C5 (owner, package 3c): approve-project-data.py is retired — after the move nothing
    # project-owned is left under .claude/ for it to approve — so the proposal DROPS its
    # PermissionRequest handler and changes no other wiring. Until the owner applies it the
    # live file still carries exactly that handler; afterwards the two are equal.
    extra = set(parity.hook_handlers(proposal["hooks"])) - set(parity.hook_handlers(live["hooks"]))
    gone = set(parity.hook_handlers(live["hooks"])) - set(parity.hook_handlers(proposal["hooks"]))
    t.check(
        "proposal: no hook added, and the only removal is approve-project-data on PermissionRequest",
        not extra and (not gone or gone == {APPROVE_HANDLER}),
        json.dumps({"extra": sorted(extra), "gone": sorted(gone)}),
    )
    t.check("proposal: the retired hook is not wired anywhere", "approve-project-data" not in json.dumps(proposal["hooks"]))
    t.check("proposal: the engine's own env stays", proposal["env"].get("CLAUDE_CODE_STOP_HOOK_BLOCK_CAP") is not None)
    t.check("personal layer: wires no hooks", "hooks" not in personal_raw)

    # --- effective parity against the frozen "before" ---------------------------------------
    frozen: dict[str, Any] = json.loads(FROZEN.read_text(encoding="utf-8"))
    home = parity.read_settings(HOME_FIXTURE)
    layer = engine.parse_personal(PERSONAL.read_bytes(), str(PERSONAL))
    merged = parity.strip_comments(engine.merge_into(home, layer, engine.PersonalPlan(PERSONAL, {})))
    after = parity.effective({"user": merged, "project": parity.read_settings(PROPOSAL)})
    diffs = parity.differences(frozen, after)
    unexpected = [d for d in diffs if d["path"] not in INTENDED]
    missing = [p for p in INTENDED if p not in {d["path"] for d in diffs}]
    t.check(
        f"effective settings: {len(parity.flatten(frozen)) - len(diffs)} identical, "
        f"{len(diffs)} intended difference(s)",
        not unexpected and not missing,
        json.dumps({"unexpected": unexpected, "intended but absent": missing}, ensure_ascii=False),
    )
    for d in diffs:
        if d["path"] in INTENDED:
            print(f"       intended: {d['path']} — {INTENDED[d['path']]}")

    # --- a control: the frozen file really is the pre-split state, not the proposal --------
    before_without_personal = parity.effective({"user": home, "project": parity.read_settings(PROPOSAL)})
    t.check(
        "control: without the personal layer the proposal is NOT today's settings",
        bool(parity.differences(frozen, before_without_personal)),
    )

    # --- applied yet? -----------------------------------------------------------------------
    applied = parity.strip_comments(live) == parity.strip_comments(proposal)
    print(f"  info {'APPLIED: the live .claude/settings.json equals the proposal' if applied else 'not applied yet: the live .claude/settings.json still differs from the proposal'}")

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
