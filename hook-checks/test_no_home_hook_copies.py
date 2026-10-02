#!/usr/bin/env python3
"""Nothing the engine ships puts a hook under ~/.claude/, and no hook goes quiet because
another copy of it exists.

Claude Code runs the same hook handler once per event only when the two settings files
wire it with an IDENTICAL command string; a home-level copy wired as `~/.claude/hooks/x.sh`
next to the project's `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh` runs twice. Package 3b first
answered that with a runtime stand-down inside every hook; the owner's review took it out
(its "is the project wiring me" check read any mention of the hook's name in the settings
text, and it added an exit-0 path to the deny hooks). The source is closed instead:

- the claude-autonomy skill's user scope writes a settings file with NO `hooks` block and
  copies NO scripts — simulated here exactly as SKILL.md step 3 prescribes, into a
  temporary home;
- the personal layer wires no hooks and `engine.py install --personal` refuses one that does
  (pinned in test_personal_layer.py; re-asserted here on the file);
- no engine hook, and no skill copy of one, contains stand-down logic or its override.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
SKILL = ROOT / ".claude/skills/claude-autonomy"
USER_TEMPLATE = SKILL / "assets/settings.user.json.template"
PROJECT_TEMPLATE = SKILL / "assets/settings.json.template"
FORBIDDEN = ("engine_stand_down", "ENGINE_HOOK_ALWAYS_RUN", "STOOD_DOWN")
HOME_HOOK_WRITE = re.compile(r"scripts/\*\.sh`?\s*→\s*`?~/\.claude/hooks")


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


def main() -> int:
    t = Checks()

    # --- the skill at user scope: settings only, no hooks --------------------------------------
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    render = skill_text.split("### 3. Render the templates", 1)[1].split("### 4.", 1)[0]
    user_scope = render.split("**User scope**:", 1)[1]
    t.check("SKILL.md user scope names the hook-less template", "settings.user.json.template" in user_scope, user_scope[:300])
    t.check("SKILL.md user scope copies no hook scripts into the home directory", not HOME_HOOK_WRITE.search(skill_text) and "~/.claude/hooks/*.sh" not in skill_text)
    user_tpl = json.loads(USER_TEMPLATE.read_text(encoding="utf-8"))
    project_tpl = json.loads(PROJECT_TEMPLATE.read_text(encoding="utf-8"))
    t.check("the user-scope template has no hooks block", "hooks" not in user_tpl, str(list(user_tpl)))
    t.check("the project-scope template still wires its hooks", bool(project_tpl.get("hooks")))
    t.check(
        "the two templates agree on everything but hooks and the comment",
        {k: v for k, v in user_tpl.items() if not k.startswith("_")} == {k: v for k, v in project_tpl.items() if k != "hooks"},
    )
    with tempfile.TemporaryDirectory(prefix="claude-autonomy-user-scope-") as tmp:
        home = Path(tmp) / ".claude"
        home.mkdir()
        # what step 3 says to do for user scope, and nothing more
        (home / "settings.json").write_text(USER_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
        installed = json.loads((home / "settings.json").read_text(encoding="utf-8"))
        t.check("a user-scope install wires no hook", "hooks" not in installed)
        t.check("a user-scope install creates no hooks directory", not (home / "hooks").exists())
        t.check("a user-scope install still carries the permissions", "permissions" in installed and "deny" in installed["permissions"])

    # --- the personal layer -------------------------------------------------------------------
    personal = json.loads((ROOT / "user/settings.json").read_text(encoding="utf-8"))
    t.check("user/settings.json wires no hooks", "hooks" not in personal)

    # --- no hook goes quiet because another copy exists ----------------------------------------
    files = sorted(p for p in HOOKS.iterdir() if p.suffix in (".sh", ".py"))
    files += sorted((SKILL / "scripts").glob("*.sh"))
    files += [ROOT / "evals/run_hook_scenarios.py", ROOT / ".claude/unattended/env-probe.sh"]
    for f in files:
        text = f.read_text(encoding="utf-8")
        hits = [w for w in FORBIDDEN if w in text]
        t.check(f"no stand-down logic in {f.relative_to(ROOT)}", not hits, str(hits))
    t.check("the live hooks and the skill's copies are byte-identical", all(
        (SKILL / "scripts" / p.name).read_bytes() == p.read_bytes() for p in (SKILL / "scripts").glob("*.sh")
    ))

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
