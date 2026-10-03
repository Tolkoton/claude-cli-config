#!/usr/bin/env python3
"""The proposed shared settings (docs/tasks/settings.json) plus the personal layer
(user/settings.json) are, in effect, exactly today's settings.

The owner applies the proposal by hand (protect-paths.sh refuses .claude/settings.json to
an agent), so this is the test of that one file. It holds before and after the apply:

- the effective settings of {home fixture + personal layer, proposal} equal the frozen
  effective settings of {home fixture, the shared file as it was before the split}
  (docs/tasks/effective-before-split.json) — except for the differences this file lists
  on purpose, each with the reason;
- the proposal carries no personal key; against the live file its hooks block drops the retired
  approve-project-data handler and adds the two stuck-counter handlers (STUCK_HANDLERS) and the
  two handlers of the fresh-context overseer (OVERSEER_HANDLERS, board 018), and nothing else — docs/tasks/settings.json is the ONE place a settings change is proposed, and
  `cp` of it the one way to apply it;
- once the live .claude/settings.json equals the proposal, that is reported as applied.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROPOSAL = ROOT / "docs/tasks/settings.json"
LIVE = ROOT / ".claude/settings.json"
PERSONAL = ROOT / "user/settings.json"
FROZEN = ROOT / "docs/tasks/effective-before-split.json"
HOME_FIXTURE = ROOT / "tests/fixtures/home-settings.json"
PERSONAL_KEYS = ("defaultMode", "additionalDirectories")
PERSONAL_ALLOW = ("WebFetch", "WebSearch")
PERSONAL_ENV = (
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
)

APPROVE_HANDLER = 'PermissionRequest|Edit|Write|MultiEdit|command|python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/approve-project-data.py"'
STUCK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/lesson_queue.py" stuck'
# The stuck counter on Bash results (package memory): a failed Bash call arrives as
# PostToolUseFailure, a finished one as PostToolUse. The owner's decision of 2026-10-03.
STUCK_HANDLERS = {f"{event}|Bash|command|{STUCK_COMMAND}" for event in ("PostToolUse", "PostToolUseFailure")}
# The overseer as a separate agent (board 015 / 018, the owner's answers of 2026-10-03): the guard
# before the Agent tool and the edit tools, and the verdict writer on the agent's SubagentStop.
OVERSEER_SCRIPT = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/overseer_verdict.py"'
OVERSEER_GUARD_MATCHER = "Agent|Task|Edit|Write|MultiEdit|NotebookEdit"
OVERSEER_HANDLERS = {f"PreToolUse|{OVERSEER_GUARD_MATCHER}|command|{OVERSEER_SCRIPT} guard",
                     f"SubagentStop|overseer|command|{OVERSEER_SCRIPT} record"}

# Differences against the frozen "before" that are intended. Path -> why.
INTENDED: dict[str, str] = {
    "permissions.deny": (
        "S4: the root rule `rm -rf /` + `*` matched any text and refused a delete under /tmp; now the exact root, "
        "with -fr given the same shape as -rf (tests/test_root_delete_deny.py); X5: the twelve Write(<path>) rules "
        "are gone — Claude Code 2.1.287 does not apply Write rules with a path and warns about them at start-up; "
        "each had an Edit(<path>) twin, which covers every file-modifying tool, so nothing is unguarded"
    ),
    "permissions.defaultMode": (
        "F4 (owner): the personal layer says `auto`, not `acceptEdits`; `auto` is legal at the user level only, "
        "which is where the layer lives. Unattended sessions do not depend on it: session-claude.sh passes "
        "--permission-mode acceptEdits itself"
    ),
    "env.ANTHROPIC_DEFAULT_SONNET_MODEL": "F4 (owner): removed, not moved — pinning a model id freezes an old model",
    "env.ANTHROPIC_DEFAULT_OPUS_MODEL": "F4 (owner): removed, not moved — pinning a model id freezes an old model",
    "env.ANTHROPIC_DEFAULT_HAIKU_MODEL": "F4 (owner): removed, not moved — pinning a model id freezes an old model",
    "hooks": (
        "owner, 2026-10-03 (package memory, board 008): the stuck counter listens to Bash results — "
        "`lesson_queue.py stuck` on PostToolUse and PostToolUseFailure, matcher Bash; without them a "
        "command that fails three times in a row goes unnoticed. Board 018 (owner, 2026-10-03): the overseer is "
        "a separate agent — `overseer_verdict.py guard` before the Agent tool and the edit tools, "
        "`overseer_verdict.py record` on the SubagentStop of the agent `overseer`. Exactly these four handlers, "
        "nothing else"
    ),
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
    # Board 008 (owner, 2026-10-03): the proposal ADDS the two stuck-counter handlers; until it
    # is applied the live file lacks them. No other handler may differ, in either direction.
    extra = set(parity.hook_handlers(proposal["hooks"])) - set(parity.hook_handlers(live["hooks"]))
    gone = set(parity.hook_handlers(live["hooks"])) - set(parity.hook_handlers(proposal["hooks"]))
    t.check(
        "proposal: the only hooks added against the live file are the two stuck-counter handlers and the two "
        "overseer handlers, and the only removal is approve-project-data on PermissionRequest",
        extra <= STUCK_HANDLERS | OVERSEER_HANDLERS and gone <= {APPROVE_HANDLER},
        json.dumps({"extra": sorted(extra), "gone": sorted(gone)}),
    )
    t.check("proposal: the retired hook is not wired anywhere", "approve-project-data" not in json.dumps(proposal["hooks"]))
    stuck = [
        (event, group, handler)
        for event in ("PostToolUse", "PostToolUseFailure")
        for group in proposal["hooks"].get(event, [])
        for handler in group["hooks"]
        if handler.get("command") == STUCK_COMMAND
    ]
    t.check(
        "proposal: the stuck counter is wired once on PostToolUse and once on PostToolUseFailure, for Bash, with a timeout",
        [event for event, _, _ in stuck] == ["PostToolUse", "PostToolUseFailure"]
        and all(group.get("matcher") == "Bash" and handler.get("timeout") for _, group, handler in stuck),
        json.dumps(stuck, ensure_ascii=False),
    )
    script = ROOT / ".claude/hooks/lesson_queue.py"
    helped = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True, check=False)
    t.check("...and the command names a script that exists with the sub-command it has", script.is_file() and "stuck" in helped.stdout)
    wired = set(parity.hook_handlers(proposal["hooks"])) & OVERSEER_HANDLERS
    t.check("proposal: the overseer's guard and its verdict writer are both wired, each once",
            wired == OVERSEER_HANDLERS and json.dumps(proposal["hooks"]).count("overseer_verdict.py") == 2, str(sorted(wired)))
    verdict_script = ROOT / ".claude/hooks/overseer_verdict.py"
    verdict_help = subprocess.run([sys.executable, str(verdict_script), "--help"], capture_output=True, text=True, check=False)
    t.check("...and the command names a script that exists with both sub-commands",
            verdict_script.is_file() and "guard" in verdict_help.stdout and "record" in verdict_help.stdout)
    t.check(
        "the old second way to apply is gone: no merge script, no fragment",
        not (ROOT / "docs/tasks/apply-lesson-hooks.py").exists() and not (ROOT / "docs/tasks/lesson-hooks.json").exists(),
    )
    t.check("proposal: the engine's own env stays", proposal["env"].get("CLAUDE_CODE_STOP_HOOK_BLOCK_CAP") is not None)
    t.check("personal layer: wires no hooks", "hooks" not in personal_raw)

    # X5 (owner): no Write(<path>) deny rule remains — Claude Code does not match them — and every
    # rule the proposal dropped relative to the live file is such a rule with its Edit twin kept.
    write_rules = [r for r in perm["deny"] if r.startswith("Write(")]
    t.check("proposal: no Write(<path>) deny rule left", not write_rules, str(write_rules))
    dropped = [r for r in live["permissions"]["deny"] if r not in perm["deny"]]
    t.check(
        "proposal: every deny rule dropped against the live file is a Write(...) whose Edit(...) twin stays",
        all(r.startswith("Write(") and ("Edit(" + r[len("Write("):]) in perm["deny"] for r in dropped),
        str(dropped),
    )

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
    t.check(
        "effective hooks: the frozen handlers plus exactly the two stuck-counter and the two overseer handlers",
        set(after["hooks"]) - set(frozen["hooks"]) == STUCK_HANDLERS | OVERSEER_HANDLERS and not set(frozen["hooks"]) - set(after["hooks"]),
        json.dumps(sorted(set(after["hooks"]) ^ set(frozen["hooks"]))),
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
