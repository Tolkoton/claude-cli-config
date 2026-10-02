#!/usr/bin/env python3
"""An engine hook wired at two settings levels fires once per event — and the stand-down
that makes it so can never be mistaken for an allow.

Claude Code runs an IDENTICAL handler defined in two settings files once; two DIFFERENT
command strings for the same script (a home-level ~/.claude/hooks/x next to the project's
$CLAUDE_PROJECT_DIR/.claude/hooks/x) run twice. Every engine hook therefore stands down when
it is not the project's own copy and the project wires hooks/<its name>, printing
`STOOD_DOWN: ...` on stderr with exit 0. Pinned here, against a project that wires the
hooks exactly as docs/tasks/settings.json does:

- the HOME copy of every hook stands down there, with the marker, and writes nothing;
- the PROJECT copy of every hook still does its job in the very same environment
  (the critic's O5: a wrongly triggered stand-down would look like an allow, so every
  MUST_BLOCK / MUST_REFUSE case of test_deny_gaps.py and test_guardrail_paths.py is
  re-run through the project's copy here and must still block);
- a project that does NOT wire the hook leaves the home copy running (the global guard
  keeps working in a repository without the engine);
- ENGINE_HOOK_ALWAYS_RUN=1 makes the home copy run anyway (the override for measuring);
- the personal layer wires no hooks, so `install --personal` can never create the
  duplicate in the first place.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude/hooks"
PROPOSAL = ROOT / "docs/tasks/settings.json"
ALL_HOOKS = sorted(p.name for p in HOOKS.iterdir() if p.suffix in (".sh", ".py"))
MARKER = "STOOD_DOWN:"

# Re-used verbatim from test_deny_gaps.py (MUST_BLOCK) and test_guardrail_paths.py (MUST_REFUSE).
DENY_COMMANDS = [
    "cd /tmp && git commit -m x",
    "echo hi; git commit -m x",
    "git -C /some/repo commit -m x",
    "git --no-pager commit -m x",
    'rm -rf "$HOME"',
    "rm -rf ${HOME}",
    "\tsudo rm -f /etc/hosts",
    "true && sudo rm -f /etc/hosts",
    "git commit -m x",
    "rm -rf $HOME",
]
REFUSE_PATHS = [
    ".claude/constitution.md",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".env",
]
ENVELOPE = {
    "block-dangerous.sh": {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}},
    "protect-paths.sh": {"tool_name": "Edit", "tool_input": {"file_path": ".env"}},
    "format-on-edit.sh": {"tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}},
    "verify-on-stop.sh": {"stop_hook_active": False},
    "env-check.sh": {},
    "park-ask-gated.py": {"tool_name": "Bash", "tool_input": {"command": "git push"}},
    "auto-approve-web.py": {"hook_event_name": "PreToolUse", "tool_name": "WebFetch", "tool_input": {"url": "https://x.y"}},
    "overseer_stop.py": {"last_assistant_message": "hi"},
    "complexity_budget.py": {"stop_hook_active": False},
}
ARGS = {"complexity_budget.py": ["hook"]}


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
            print(f"  FAIL {name}  {detail[:600]}")


def run(hook_file: Path, envelope: object, project: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("ENGINE_HOOK_ALWAYS_RUN", "CLAUDE_UNATTENDED_SESSION")}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(extra_env or {})
    interpreter = [sys.executable] if hook_file.suffix == ".py" else ["bash"]
    return subprocess.run(
        [*interpreter, str(hook_file), *ARGS.get(hook_file.name, [])],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        env=env,
        cwd=project if project.is_dir() else None,
        check=False,
        timeout=120,
    )


def stood_down(r: subprocess.CompletedProcess[str]) -> bool:
    return r.returncode == 0 and MARKER in r.stderr and r.stdout.strip() == ""


def blocked_bash(r: subprocess.CompletedProcess[str]) -> bool:
    return r.returncode == 2


def refused_edit(r: subprocess.CompletedProcess[str]) -> bool:
    return '"permissionDecision"' in r.stdout and '"deny"' in r.stdout


def make_project(root: Path, wire_hooks: bool) -> Path:
    """A git repository on main with the engine hooks installed and (optionally) wired."""
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    shutil.copytree(HOOKS, root / ".claude/hooks")
    shutil.copy2(ROOT / ".claude/project.env", root / ".claude/project.env")
    settings = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    if not wire_hooks:
        settings.pop("hooks", None)
    (root / ".claude/settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    (root / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=root, check=True)
    return root


def main() -> int:
    t = Checks()
    with tempfile.TemporaryDirectory(prefix="hooks-fire-once-") as tmp:
        tmp_path = Path(tmp)
        home_hooks = tmp_path / "home" / ".claude" / "hooks"
        shutil.copytree(HOOKS, home_hooks)
        wired = make_project(tmp_path / "wired", wire_hooks=True)
        unwired = make_project(tmp_path / "unwired", wire_hooks=False)

        # --- the home copy stands down, with the marker, where the project wires the hook -------
        for name in ALL_HOOKS:
            r = run(home_hooks / name, ENVELOPE[name], wired)
            t.check(f"home copy stands down: {name}", stood_down(r), f"rc={r.returncode} out={r.stdout[:80]!r} err={r.stderr[:160]!r}")

        # --- the project's own copy still decides in the same environment ---------------------
        own = wired / ".claude/hooks"
        for cmd in DENY_COMMANDS:
            r = run(own / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": cmd}}, wired)
            t.check(f"project copy still blocks: {cmd!r}", blocked_bash(r) and MARKER not in r.stderr, r.stderr[:160])
        for path in REFUSE_PATHS:
            r = run(own / "protect-paths.sh", {"tool_name": "Edit", "tool_input": {"file_path": str(wired / path)}}, wired)
            t.check(f"project copy still refuses: {path}", refused_edit(r) and MARKER not in r.stderr, r.stdout[:160])
        r = run(own / "park-ask-gated.py", ENVELOPE["park-ask-gated.py"], wired)
        t.check("project copy of park-ask-gated.py runs (attended: no decision, no marker)", r.returncode == 0 and MARKER not in r.stderr, r.stderr[:160])
        r = subprocess.run([sys.executable, str(own / "overseer_stop.py"), "--dry-run"], input="{}", capture_output=True, text=True, check=False, cwd=wired, env={**os.environ, "CLAUDE_PROJECT_DIR": str(wired)})
        t.check("project copy of overseer_stop.py --dry-run still blocks", '"decision": "block"' in r.stdout, r.stdout[:160])

        # --- the home copy keeps guarding a project that does not wire the hook ------------------
        r = run(home_hooks / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, unwired)
        t.check("home copy still blocks where the project wires nothing", blocked_bash(r) and MARKER not in r.stderr, r.stderr[:160])
        r = run(home_hooks / "protect-paths.sh", {"tool_name": "Edit", "tool_input": {"file_path": str(unwired / ".env")}}, unwired)
        t.check("home copy still refuses where the project wires nothing", refused_edit(r) and MARKER not in r.stderr, r.stdout[:160])
        r = run(home_hooks / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, tmp_path / "nowhere")
        t.check("home copy runs when CLAUDE_PROJECT_DIR names no project", blocked_bash(r), r.stderr[:160])

        # --- the override, in the safe direction only ------------------------------------------
        r = run(home_hooks / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, wired, {"ENGINE_HOOK_ALWAYS_RUN": "1"})
        t.check("ENGINE_HOOK_ALWAYS_RUN=1: the home copy runs and blocks", blocked_bash(r) and MARKER not in r.stderr, r.stderr[:160])
        r = run(home_hooks / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, wired, {"ENGINE_HOOK_ALWAYS_RUN": "0"})
        t.check("ENGINE_HOOK_ALWAYS_RUN=0 is not an override (no way to force a stand-down)", stood_down(r), r.stderr[:160])

        # --- the marker is distinguishable from an allow -----------------------------------------
        r_allow = run(own / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": "git status"}}, wired)
        r_down = run(home_hooks / "block-dangerous.sh", {"tool_name": "Bash", "tool_input": {"command": "git status"}}, wired)
        t.check("an allow is exit 0 with EMPTY stderr; a stand-down is exit 0 with the marker", r_allow.returncode == 0 and r_allow.stderr == "" and stood_down(r_down))

    # --- the personal layer cannot create the duplicate -----------------------------------------
    personal = json.loads((ROOT / "user/settings.json").read_text(encoding="utf-8"))
    t.check("user/settings.json wires no hooks", "hooks" not in personal)
    t.check("every engine hook carries the stand-down", all("engine_stand_down" in (HOOKS / n).read_text(encoding="utf-8") for n in ALL_HOOKS), str(ALL_HOOKS))

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
