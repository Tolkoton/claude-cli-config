#!/usr/bin/env python3
"""Every push is decided by environment in park-ask-gated.py (board 603, owner decision).

`git push` left the ask list of the settings file: a rule there prompted in every environment,
and no hook can lift an ask rule, so a cloud session stopped on every push of its own branch.
The rule is the hook's now:

  - a cloud session (CLAUDE_CODE_REMOTE=true) whose project.env says
    CLOUD_COMMIT_POLICY="session-branch": the push of its own checked-out claude/ branch to
    origin goes without a question; any other push — another branch or remote, unattended/*,
    main, stable, --all, tags, a bare push — is refused with the reason;
  - a local session with the owner (and a cloud session with the switch off): "ask";
  - the runner, a session nobody watches (the mode file, or CLAUDE_UNATTENDED_SESSION=1): refused;
  - a push inside `bash -c`, `sh -c` or `eval` is judged as if it were typed; a forced push and
    the deletion of a remote branch are refused everywhere — by block-dangerous.sh, as before.

Each case runs BOTH real Bash hooks, against a real throwaway repository on a real branch, and
checks what park-ask-gated.py says and what the two together decide (a refusal of either wins
over a question). Then the mirror: the ask list of the settings proposal and the hook's
ASK_GATED name the same commands, and neither names a push.

Run:   python3 tests/test_push_by_environment.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from hook_env import hook_env, main_repo, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
PARK = ROOT / ".claude/hooks/park-ask-gated.py"
BLOCK = ROOT / ".claude/hooks/block-dangerous.sh"
PROPOSAL = ROOT / "docs/tasks/settings.json"
PUSH = "git " + "push"            # split, so that a shell handling THIS file does not judge its cases
F = "--for" + "ce"
B = "claude/s-1"
PLACE = ("CLAUDE_CODE_REMOTE", "CLAUDE_UNATTENDED_SESSION")   # what says where a session runs
PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail[:600]}")


def repo(branch: str, policy: str | None = None, mode: str | None = None) -> str:
    """A throwaway repository on `branch`, with CLOUD_COMMIT_POLICY and the mode file as given."""
    root = main_repo(branch)
    if policy is not None:
        env_file = Path(root, ".claude/project.env")
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(f'SOURCE_DIRS="src"\nCLOUD_COMMIT_POLICY="{policy}"\n', encoding="utf-8")
    if mode is not None:
        mode_file = Path(root, ".claude/state/overseer/mode")
        mode_file.parent.mkdir(parents=True, exist_ok=True)
        mode_file.write_text(mode + "\n", encoding="utf-8")
    return root


def environment(root: str, place: dict[str, str]) -> dict[str, str]:
    """The hook's environment: the project pinned, and only the place variables the case names."""
    env = hook_env(root, **place)
    for name in PLACE:
        if name not in place:
            env.pop(name, None)
    return env


def park(cmd: str, root: str, place: dict[str, str]) -> tuple[str, str]:
    envelope = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                           "tool_input": {"command": cmd}, "cwd": root})
    r = subprocess.run([sys.executable, str(PARK)], input=envelope, capture_output=True, text=True,
                       env=environment(root, place), cwd=root, check=False)
    if r.returncode != 0:
        return f"error:{r.returncode}", r.stderr
    if not r.stdout.strip():
        return "none", ""
    out = json.loads(r.stdout)["hookSpecificOutput"]
    said = "allow-explicit" if out["permissionDecision"] == "allow" else out["permissionDecision"]
    return said, out["permissionDecisionReason"]


def block(cmd: str, root: str, place: dict[str, str]) -> str:
    envelope = json.dumps({"tool_input": {"command": cmd}, "cwd": root})
    r = subprocess.run(["bash", str(BLOCK)], input=envelope, capture_output=True, text=True,
                       env=environment(root, place), cwd=root, check=False)
    return "deny" if r.returncode == 2 else "allow"


def together(parked: str, blocked: str) -> str:
    """What Claude Code does with both answers: a refusal wins, then a question; "allow" is either
    hook's approval or no objection, after which the settings decide."""
    if "deny" in (parked, blocked):
        return "deny"
    return "ask" if parked == "ask" else "allow"


CLOUD = {"CLAUDE_CODE_REMOTE": "true"}
LOCAL: dict[str, str] = {}
RUNNER = {"CLAUDE_UNATTENDED_SESSION": "1"}

ON = repo(B, "session-branch")                       # the cloud session's own branch, switch on
FEAT = repo("feat/x", "session-branch")
UNATT_BRANCH = repo("unattended/2026-10-09", "session-branch")
MAIN = repo("main", "session-branch")
OFF = repo(B, "off")
NO_ENV = repo(B)
LOCAL_FEAT = repo("feat/x")
UNATT = repo("unattended/2026-10-09", mode="unattended")
ON_UNATT = repo(B, "session-branch", mode="unattended")
OTHER = repo("feat/y")                               # another repository, another branch
EMPTY = sandbox_dir("push-env-empty-")               # no repository at all

CASES: list[tuple[str, dict[str, str], str, str, str, str]] = [
    # (name, place, repo, command, park-ask-gated says, the two together)
    # --- cloud, switch on: the session's own branch to origin goes ------------------------------
    ("cloud: own branch with -u", CLOUD, ON, f"{PUSH} -u origin {B}", "allow-explicit", "allow"),
    ("cloud: own branch", CLOUD, ON, f"{PUSH} origin {B}", "allow-explicit", "allow"),
    ("cloud: HEAD", CLOUD, ON, f"{PUSH} -u origin HEAD", "allow-explicit", "allow"),
    ("cloud: HEAD:<own branch>", CLOUD, ON, f"{PUSH} origin HEAD:{B}", "allow-explicit", "allow"),
    ("cloud: own:refs/heads/own", CLOUD, ON, f"{PUSH} origin {B}:refs/heads/{B}", "allow-explicit", "allow"),
    ("cloud: --set-upstream and --quiet", CLOUD, ON, f"{PUSH} --set-upstream --quiet origin {B}", "allow-explicit", "allow"),
    ("cloud: after a cd into the repository", CLOUD, ON, f"cd {ON} && {PUSH} -u origin {B}", "allow-explicit", "allow"),
    ("cloud: git -C <repository>", CLOUD, ON, f"git -C {ON} push -u origin {B}", "allow-explicit", "allow"),
    ("cloud: with 2>&1", CLOUD, ON, f"{PUSH} -u origin {B} 2>&1", "allow-explicit", "allow"),
    ("cloud: output dropped", CLOUD, ON, f"{PUSH} -u origin {B} >/dev/null 2>&1", "allow-explicit", "allow"),
    ("cloud: output written to a file, the settings decide", CLOUD, ON, f"{PUSH} -u origin {B} > /tmp/push.log 2>&1", "none", "allow"),
    ("cloud: git -C an absolute path after a variable cd", CLOUD, ON, f"cd $HOME && git -C {ON} push -u origin {B}", "allow-explicit", "allow"),
    ("cloud: inside a longer command the settings decide", CLOUD, ON, f"{PUSH} -u origin {B} && ls", "none", "allow"),
    ("cloud: piped, the settings decide", CLOUD, ON, f"{PUSH} -u origin {B} | tail -3", "none", "allow"),
    ("cloud: inside bash -c", CLOUD, ON, f'bash -c "{PUSH} -u origin {B}"', "none", "allow"),
    ("cloud: inside sh -c", CLOUD, ON, f"sh -c '{PUSH} -u origin {B}'", "none", "allow"),
    ("cloud: inside eval", CLOUD, ON, f'eval "{PUSH} -u origin {B}"', "none", "allow"),
    ("cloud: a push only quoted in a commit message is no push", CLOUD, ON,
     f'git commit -m "refuse {PUSH} origin main"', "none", "allow"),
    ("cloud: git stash push is no push", CLOUD, ON, "git stash push -m wip", "none", "allow"),
    # --- cloud, switch on: every other push is refused ------------------------------------------
    ("cloud: another branch", CLOUD, ON, f"{PUSH} origin claude/other", "deny", "deny"),
    ("cloud: another remote", CLOUD, ON, f"{PUSH} upstream {B}", "deny", "deny"),
    ("cloud: a URL instead of origin", CLOUD, ON, f"{PUSH} https://example.com/r.git {B}", "deny", "deny"),
    ("cloud: an unattended/* branch named", CLOUD, ON, f"{PUSH} origin unattended/2026-10-09", "deny", "deny"),
    ("cloud: into main", CLOUD, ON, f"{PUSH} origin main", "deny", "deny"),
    ("cloud: into stable", CLOUD, ON, f"{PUSH} origin stable", "deny", "deny"),
    ("cloud: own branch into main", CLOUD, ON, f"{PUSH} origin {B}:main", "deny", "deny"),
    ("cloud: own branch into another branch", CLOUD, ON, f"{PUSH} origin {B}:claude/other", "deny", "deny"),
    ("cloud: --all", CLOUD, ON, f"{PUSH} --all origin", "deny", "deny"),
    ("cloud: --tags", CLOUD, ON, f"{PUSH} origin --tags", "deny", "deny"),
    ("cloud: --follow-tags with the own branch", CLOUD, ON, f"{PUSH} --follow-tags origin {B}", "deny", "deny"),
    ("cloud: a tag by its ref", CLOUD, ON, f"{PUSH} origin refs/tags/v1.0", "deny", "deny"),
    ("cloud: a tag by the tag keyword", CLOUD, ON, f"{PUSH} origin tag v1.0", "deny", "deny"),
    ("cloud: a bare push", CLOUD, ON, PUSH, "deny", "deny"),
    ("cloud: the remote without a branch", CLOUD, ON, f"{PUSH} origin", "deny", "deny"),
    ("cloud: two branches at once", CLOUD, ON, f"{PUSH} origin {B} claude/other", "deny", "deny"),
    ("cloud: a forced push of the own branch", CLOUD, ON, f"{PUSH} {F} origin {B}", "deny", "deny"),
    ("cloud: -f", CLOUD, ON, f"{PUSH} -f origin {B}", "deny", "deny"),
    ("cloud: a +refspec", CLOUD, ON, f"{PUSH} origin +{B}", "deny", "deny"),
    ("cloud: force-with-lease", CLOUD, ON, f"{PUSH} {F}-with-lease origin {B}", "deny", "deny"),
    ("cloud: the deletion of the own branch (--delete)", CLOUD, ON, f"{PUSH} origin --delete {B}", "deny", "deny"),
    ("cloud: the deletion by :branch", CLOUD, ON, f"{PUSH} origin :{B}", "deny", "deny"),
    ("cloud: the deletion by -d", CLOUD, ON, f"{PUSH} -d origin {B}", "deny", "deny"),
    ("cloud: an option it does not know (-o)", CLOUD, ON, f"{PUSH} -o ci.skip origin {B}", "deny", "deny"),
    ("cloud: inside bash -c, into main", CLOUD, ON, f'bash -c "{PUSH} origin main"', "deny", "deny"),
    ("cloud: inside sh -c, another branch", CLOUD, ON, f"sh -c '{PUSH} origin claude/other'", "deny", "deny"),
    ("cloud: inside eval, another remote", CLOUD, ON, f'eval "{PUSH} upstream {B}"', "deny", "deny"),
    ("cloud: inside bash -c after a separator", CLOUD, ON, f"bash -c 'true; {PUSH} origin claude/other'", "deny", "deny"),
    ("cloud: after a separator, another branch", CLOUD, ON, f"cd . && {PUSH} origin claude/other", "deny", "deny"),
    ("cloud: the own push and then another", CLOUD, ON, f"{PUSH} -u origin {B} && {PUSH} origin claude/other", "deny", "deny"),
    ("cloud: an assignment before git", CLOUD, ON, f"HOME=/tmp/x {PUSH} -u origin {B}", "deny", "deny"),
    ("cloud: a GIT_* variable before git", CLOUD, ON, f"GIT_DIR=/tmp/x/.git {PUSH} -u origin {B}", "deny", "deny"),
    ("cloud: a GIT_* variable exported first", CLOUD, ON, f"export GIT_DIR=/tmp/x/.git; {PUSH} -u origin {B}", "deny", "deny"),
    ("cloud: git -c can redirect origin", CLOUD, ON, f"git -c remote.origin.url=/tmp/x push -u origin {B}", "deny", "deny"),
    ("cloud: from another repository after a cd", CLOUD, ON, f"cd {OTHER} && {PUSH} -u origin {B}", "deny", "deny"),
    ("cloud: from a directory that is no repository", CLOUD, ON, f"cd {EMPTY} && {PUSH} -u origin {B}", "deny", "deny"),
    ("cloud: from a directory named by a variable", CLOUD, ON, f"cd $HOME/x && {PUSH} -u origin {B}", "deny", "deny"),
    ("cloud: a feature branch checked out", CLOUD, FEAT, f"{PUSH} -u origin feat/x", "deny", "deny"),
    ("cloud: an unattended/* branch checked out", CLOUD, UNATT_BRANCH, f"{PUSH} -u origin unattended/2026-10-09", "deny", "deny"),
    ("cloud: main checked out", CLOUD, MAIN, f"{PUSH} -u origin main", "deny", "deny"),
    ("cloud: HEAD with main checked out", CLOUD, MAIN, f"{PUSH} origin HEAD", "deny", "deny"),
    # --- cloud, switch off: the owner confirms, as before ---------------------------------------
    ("cloud, switch off: asks", CLOUD, OFF, f"{PUSH} -u origin {B}", "ask", "ask"),
    ("cloud, no project.env: asks", CLOUD, NO_ENV, f"{PUSH} -u origin {B}", "ask", "ask"),
    ("cloud, switch off: a forced push is still refused", CLOUD, OFF, f"{PUSH} {F} origin {B}", "ask", "deny"),
    # --- local, with the owner: ask --------------------------------------------------------------
    ("local: a feature branch asks", LOCAL, LOCAL_FEAT, f"{PUSH} origin feat/x", "ask", "ask"),
    ("local: the switch on does not matter outside the cloud", LOCAL, ON, f"{PUSH} -u origin {B}", "ask", "ask"),
    ("local: after a separator asks", LOCAL, LOCAL_FEAT, f"cd . && {PUSH} origin feat/x", "ask", "ask"),
    ("local: inside bash -c asks", LOCAL, LOCAL_FEAT, f'bash -c "{PUSH} origin feat/x"', "ask", "ask"),
    ("local: inside sh -c asks", LOCAL, LOCAL_FEAT, f"sh -c '{PUSH} origin feat/x'", "ask", "ask"),
    ("local: inside eval asks", LOCAL, LOCAL_FEAT, f'eval "{PUSH} origin feat/x"', "ask", "ask"),
    ("local: git status is no push", LOCAL, LOCAL_FEAT, "git status", "none", "allow"),
    ("local: a push only quoted in a message is no push", LOCAL, LOCAL_FEAT, f"echo '{PUSH} origin feat/x'", "none", "allow"),
    ("local: a forced push is refused whatever the answer", LOCAL, LOCAL_FEAT, f"{PUSH} {F} origin feat/x", "ask", "deny"),
    ("local: the deletion of a branch is refused", LOCAL, LOCAL_FEAT, f"{PUSH} origin --delete feat/x", "ask", "deny"),
    ("local: into main is refused", LOCAL, LOCAL_FEAT, f"{PUSH} origin main", "ask", "deny"),
    ("local: a forced push inside bash -c is refused", LOCAL, LOCAL_FEAT, f'bash -c "{PUSH} -f origin feat/x"', "ask", "deny"),
    # --- the runner, nobody watching: refused -----------------------------------------------------
    ("runner (mode file): refused", LOCAL, UNATT, f"{PUSH} origin unattended/2026-10-09", "deny", "deny"),
    ("runner (CLAUDE_UNATTENDED_SESSION=1): refused", RUNNER, LOCAL_FEAT, f"{PUSH} origin feat/x", "deny", "deny"),
    ("runner: after a separator, refused", LOCAL, UNATT, f"cd . && {PUSH} origin unattended/2026-10-09", "deny", "deny"),
    ("runner: inside bash -c, refused", LOCAL, UNATT, f'bash -c "{PUSH} origin unattended/2026-10-09"', "deny", "deny"),
    ("runner: inside eval, refused", LOCAL, UNATT, f'eval "{PUSH}"', "deny", "deny"),
    ("runner in a cloud session: refused, the cloud rule does not apply", CLOUD, ON_UNATT, f"{PUSH} -u origin {B}", "deny", "deny"),
    ("runner: another ask-gated command is still parked", LOCAL, UNATT, "uv add requests", "deny", "deny"),
    ("runner: an ordinary command goes", LOCAL, UNATT, "uv run pytest -q", "none", "allow"),
]

print("— decisions by environment (park-ask-gated.py and block-dangerous.sh together)")
REASONS: dict[str, str] = {}
for name, place, root, cmd, want_park, want_both in CASES:
    said, reason = park(cmd, root, place)
    both = together(said, block(cmd, root, place))
    REASONS[name] = reason
    check(f"{name}: {said} / {both}", said == want_park and both == want_both,
          f"expected {want_park} / {want_both}; reason: {reason}")

print("— the reasons say why")
for name, phrase in [
    ("cloud: another branch", "does not send the checked-out branch claude/s-1"),
    ("cloud: another remote", "the remote upstream is not origin"),
    ("cloud: a bare push", "exactly one branch are not named"),
    ("cloud: --tags", "the option --tags"),
    ("cloud: own branch into main", "into another branch (main)"),
    ("cloud: a feature branch checked out", "feat/x is not the session's own claude/ branch"),
    ("cloud: from another repository after a cd", "feat/y is not the session's own claude/ branch"),
    ("cloud: an assignment before git", "an assignment before git"),
    ("runner (mode file): refused", "the board runner sends the branch itself"),
    ("local: a feature branch asks", "needs the owner's confirmation"),
]:
    check(f"{name} — «{phrase}»", phrase in REASONS.get(name, ""), REASONS.get(name, ""))
check("a cloud refusal names the one allowed form", f"{PUSH} -u origin <that branch>" in REASONS["cloud: into main"])
check("the explicit allow names the owner's decision", "board 603" in REASONS["cloud: own branch with -u"])


# --- a push the hook fails to read is never let through unasked ---------------------------------
def load_park():
    spec = importlib.util.spec_from_file_location("park_ask_gated", PARK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["park_ask_gated"] = module      # a dataclass looks its module up by name
    spec.loader.exec_module(module)
    return module


def broken_run(root: str, place: dict[str, str]) -> str:
    """main() with push_decision raising: what the fallback decides."""
    module = load_park()

    def boom(*_args: object) -> None:
        raise RuntimeError("unreadable")

    module.push_decision = boom
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(environment(root, place))
    out = io.StringIO()
    sys.stdin = io.StringIO(json.dumps({"tool_input": {"command": f"{PUSH} -u origin {B}"}, "cwd": root}))
    try:
        with contextlib.redirect_stdout(out), contextlib.suppress(SystemExit):
            module.main()
    finally:
        sys.stdin = sys.__stdin__
        os.environ.clear()
        os.environ.update(saved)
    text = out.getvalue().strip()
    return json.loads(text)["hookSpecificOutput"]["permissionDecision"] if text else "none"


print("— a push the hook cannot read")
check("local: it asks", broken_run(LOCAL_FEAT, LOCAL) == "ask")
check("cloud, switch on: it is refused", broken_run(ON, CLOUD) == "deny")
check("runner: it is refused", broken_run(UNATT, LOCAL) == "deny")

# --- the mirror: the proposal's ask list and ASK_GATED name the same commands -------------------
print("— the mirror of the ask list")
hook = load_park()
ask = json.loads(PROPOSAL.read_text(encoding="utf-8"))["permissions"]["ask"]
commands = [m.group(1) for rule in ask if (m := re.fullmatch(r"Bash\((.+?)(?::\*)?\)", rule))]
check("every ask rule of the proposal is a Bash rule", len(commands) == len(ask), str(ask))
check("the proposal's ask list holds no push", not any(c.startswith(PUSH) for c in commands), str(commands))
unmirrored = [c for c in commands if not any(rx.search(f"{c} x") for rx in hook.ASK_GATED_RE)]
check("every ask rule has its pattern in ASK_GATED", not unmirrored, str(unmirrored))
orphans = [rx.pattern for rx in hook.ASK_GATED_RE if not any(rx.search(f"{c} x") for c in commands)]
check("every ASK_GATED pattern stands for an ask rule", not orphans, str(orphans))
check("no ASK_GATED pattern is a push (the push is the hook's own rule)",
      not any(rx.search(f"{PUSH} origin x") for rx in hook.ASK_GATED_RE))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
