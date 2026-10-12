#!/usr/bin/env python3
"""The guarded files after the fact (board 724): protected_guard.py, the Stop gate, the commit script.

Deterministic: every scene runs the real env-check.sh (the SessionStart hook), the real gate.py
(layer stop, the hook protocol) and the real commit_checkpoint.sh in a throwaway git repository
that has a constitution, a settings file, `.engine/rules.md`, a CI workflow, a migration and a
task board. The negative case comes first: the gate is shown to BLOCK and to PUT THE FILE BACK
before it is shown to pass.

SCENES
  the table of design 717, section 2 — one scene a row:
    - no guarded file changed — the turn passes, nothing is said;
    - the owner changed a file before the turn began and did not commit — passes, the edit stays;
    - the agent wrote through a variable — block, the file is as the snapshot has it (the owner's
      uncommitted edit included), the discarded change is a patch, the anomaly journal has an entry;
    - the agent changed the file and committed it in the same turn — block, put back, and told
      that HEAD still carries it;
    - the runner applied the settings between sessions — the next session passes;
  the gate's own duties: a deleted file comes back, a new one is removed, the ignored
  settings.local.json is seen; the check stands before "no code changed" and before
  `stop_hook_active`; a compaction takes no snapshot; no snapshot, or the gate run by hand —
  compared with HEAD, blocked, nothing put back;
  the owner's `accept`: refused inside a session; in the owner's terminal it puts a discarded
  change back and the next turn passes;
  commit_checkpoint.sh: a guarded file is left out of the commit and named; `--staged` refuses;
  the runner's commands `before`, `after`, `pending`: the snapshot is printed, content included, and
  handed back — never a file; snapshots forged in the state directory, a state directory that cannot
  be written, a file that cannot be put back (exit 4), content that does not have its hash (exit 4).

Run:   python3 tests/test_protected_guard.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env
from journals import journal_text

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
GATE = HOOKS / "gate.py"
GUARD = HOOKS / "protected_guard.py"
ENV_CHECK = HOOKS / "env-check.sh"
CHECKPOINT = ROOT / ".claude" / "unattended" / "commit_checkpoint.sh"
STATE = ".claude/state/gate/protected"
CONSTITUTION, SETTINGS, RULES = ".claude/constitution.md", ".claude/settings.json", ".engine/rules.md"
WORKFLOW, MIGRATION, LOCAL = ".github/workflows/ci.yml", "migrations/0001_init.py", ".claude/settings.local.json"
FILES = {
    CONSTITUTION: "# Constitution\n\nArticle 1.\n", SETTINGS: '{"hooks": {}}\n', RULES: "# Rules\n",
    WORKFLOW: "on: push\n", MIGRATION: "def upgrade():\n    pass\n", "app.py": "def run():\n    return 1\n",
    ".claude/project.env": 'CODE_EXTENSIONS="py"\nLINT_CMD="true"\nTYPECHECK_CMD="true"\nTEST_CMD="true"\n',
    ".gitignore": ".claude/state/\n.claude/settings.local.json\n",
}
CHANGED = '{"hooks": {}, "disableAllHooks": true}\n'
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def commit(root: Path, message: str) -> None:
    sh(root, "git", "add", "-A")
    done = sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    assert done.returncode == 0, done.stderr


def project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="protected-guard-"))
    sh(root, "git", "init", "-q", "-b", "unattended/t")
    for key, value in (("user.name", "t"), ("user.email", "t@t")):
        sh(root, "git", "config", key, value)
    for rel, text in FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    for column in ("todo", "doing", "blocked", "done"):
        (root / "tasks" / column).mkdir(parents=True)
        (root / "tasks" / column / ".gitkeep").touch()
    commit(root, "base")
    return root


def env_of(root: Path, owner: bool = False) -> dict[str, str]:
    """The hook's environment; `owner` = the owner's terminal, where CLAUDECODE is not set."""
    env = hook_env(str(root))
    if owner:
        env.pop("CLAUDECODE", None)
    else:
        env["CLAUDECODE"] = "1"
    return env


def start(root: Path, session: str, source: str = "startup") -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(ENV_CHECK)], cwd=root, capture_output=True, text=True, env=env_of(root), check=False,
                          input=json.dumps({"hook_event_name": "SessionStart", "session_id": session, "source": source}))


def stop(root: Path, session: str, active: bool = False) -> tuple[bool, str]:
    """One end of a turn through the real gate: (blocked, the reason the agent is shown)."""
    done = subprocess.run([sys.executable, str(GATE), "--layer", "stop", "--hook"], cwd=root, capture_output=True, text=True,
                          env=env_of(root), check=False, input=json.dumps({"session_id": session, "stop_hook_active": active}))
    try:
        said: dict[str, Any] = json.loads(done.stdout) if done.stdout.strip() else {}
    except ValueError:
        said = {"decision": "unreadable", "reason": done.stdout + done.stderr}
    return said.get("decision") == "block", str(said.get("reason", "")) + ("" if done.returncode == 0 else f" rc={done.returncode} {done.stderr}")


def guard(root: Path, *args: str, owner: bool = True, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(GUARD), *args], cwd=root, capture_output=True, text=True, env=env_of(root, owner), check=False,
                          input=stdin)


def read(root: Path, rel: str) -> str | None:
    return (root / rel).read_text() if (root / rel).is_file() else None


def snapshot(root: Path, session: str) -> set[str]:
    """The files a session's snapshot holds; empty when there is none."""
    path = root / STATE / f"{session}.json"
    return set(json.loads(path.read_text())["files"]) if path.is_file() else set()


def patches(root: Path) -> str:
    return "".join(path.read_text() for path in sorted((root / STATE / "discarded").glob("*.patch")))


def events(root: Path) -> list[str]:
    return sorted(path.stem for path in (root / STATE / "discarded").glob("*.json"))


print("row 1: no guarded file changed")
root = project()
started = start(root, "s1")
check("the SessionStart hook takes the snapshot and says nothing", started.returncode == 0 and started.stdout == ""
      and snapshot(root, "s1") == {CONSTITUTION, SETTINGS, RULES, WORKFLOW, MIGRATION},
      started.stdout + started.stderr)
(root / "app.py").write_text("def run():\n    return 2\n")
blocked, reason = stop(root, "s1")
check("a turn that changed only code passes", not blocked and reason == "", reason)

print("row 3: the agent wrote through a variable — the negative case")
done = sh(root, "bash", "-c", 'f=.claude/constitution.md; printf "Article 9: the agent decides.\\n" >> "$f"')
assert done.returncode == 0 and "Article 9" in str(read(root, CONSTITUTION))
blocked, reason = stop(root, "s1")
check("the gate blocks the turn and names the file and the patch", blocked and f"GUARDED FILE {CONSTITUTION}" in reason
      and "protected/reverted" in reason and f"{STATE}/discarded/" in reason, reason)
check("the gate put the file back itself", read(root, CONSTITUTION) == FILES[CONSTITUTION], read(root, CONSTITUTION))
check("the discarded change is kept as a patch", "+Article 9: the agent decides." in patches(root)
      and f"+++ b/{CONSTITUTION}" in patches(root), patches(root))
journal = journal_text(root, "anomalies")
check("the anomaly journal has the entry, written by the gates", f"`{CONSTITUTION}`" in journal and "gates (protected_guard.py)" in journal
      and "латкою" in journal, journal)
check("the agent is given nothing to run and told where a change is proposed", "nothing is left for you to run" in reason
      and "docs/tasks/settings.json" in reason, reason)
blocked, reason = stop(root, "s1", active=True)
check("the turn after it passes: nothing is left to find", not blocked and reason == "", reason)

print("the check stands before `stop_hook_active` and before \"no code changed\"")
(root / "app.py").write_text(FILES["app.py"])
(root / SETTINGS).write_text('{"hooks": {}, "permissions": {"allow": ["Bash(*)"]}}\n')
blocked, reason = stop(root, "s1", active=True)
check("a stop another hook forced, in a turn that changed no code, is still checked and blocked", blocked
      and f"GUARDED FILE {SETTINGS}" in reason and read(root, SETTINGS) == FILES[SETTINGS], reason)

print("row 2: the owner changed a file before the turn began and did not commit")
root = project()
OWNER = FILES[CONSTITUTION] + "Article 2, by the owner.\n"
(root / CONSTITUTION).write_text(OWNER)
start(root, "s2")
blocked, reason = stop(root, "s2")
check("the turn passes and the owner's edit is where it was", not blocked and reason == "" and read(root, CONSTITUTION) == OWNER, reason)
(root / CONSTITUTION).write_text(OWNER + "Article 9: the agent decides.\n")
blocked, reason = stop(root, "s2")
check("the agent's write on top of it is discarded — back to the owner's edit, not to HEAD", blocked
      and read(root, CONSTITUTION) == OWNER and "+Article 9" in patches(root) and "Article 2, by the owner" not in
      "".join(line for line in patches(root).splitlines() if line.startswith(("+", "-"))), str(read(root, CONSTITUTION)) + patches(root))

print("row 4: changed and committed in the same turn")
root = project()
start(root, "s4")
(root / SETTINGS).write_text('{"hooks": {}, "disableAllHooks": true}\n')
commit(root, "the agent's own commit")
check("a comparison with HEAD would see nothing", sh(root, "git", "status", "--porcelain").stdout == "")
blocked, reason = stop(root, "s4")
check("the gate blocks and puts the file back as the turn found it", blocked and read(root, SETTINGS) == FILES[SETTINGS]
      and "disableAllHooks" in patches(root), reason)
check("the agent is told HEAD still carries the change and who commits the difference", "differs from HEAD" in reason
      and "the board runner or the owner commits it" in reason, reason)

print("row 5: the runner applied the settings between sessions")
root = project()
start(root, "s5a")
stop(root, "s5a")
APPLIED = '{"hooks": {"Stop": []}}\n'
(root / SETTINGS).write_text(APPLIED)
(root / RULES).write_text(FILES[RULES] + "- a rule the owner approved\n")
commit(root, "settings: the proposal applied on the owner's answer")
start(root, "s5b")
blocked, reason = stop(root, "s5b")
check("the next session passes, and both files are as the runner left them", not blocked and reason == ""
      and read(root, SETTINGS) == APPLIED and "a rule the owner approved" in str(read(root, RULES)), reason)

print("deleted, created, ignored by git")
root = project()
start(root, "s6")
(root / MIGRATION).unlink()
(root / ".github/workflows/deploy.yml").write_text("on: push\njobs: {}\n")
(root / LOCAL).write_text('{"permissions": {"allow": ["Bash(*)"]}}\n')
blocked, reason = stop(root, "s6")
check("a deleted migration comes back", blocked and read(root, MIGRATION) == FILES[MIGRATION] and "deleted a guarded file" in reason, reason)
check("a new workflow is removed, and kept in the patch", not (root / ".github/workflows/deploy.yml").exists()
      and "created a guarded file" in reason and "+jobs: {}" in patches(root), reason + patches(root))
check("a new settings.local.json, which git ignores, is removed too", not (root / LOCAL).exists() and f"GUARDED FILE {LOCAL}" in reason, reason)

print("a compaction takes no snapshot; a resume does")
root = project()
start(root, "s7")
(root / RULES).write_text(FILES[RULES] + "- a rule the agent wrote\n")
start(root, "s7", "compact")
blocked, reason = stop(root, "s7")
check("what the agent did before a compaction is not accepted by it", blocked and read(root, RULES) == FILES[RULES], reason)
(root / RULES).write_text(FILES[RULES] + "- a rule promoted between two attempts\n")
start(root, "s7", "resume")
blocked, reason = stop(root, "s7")
check("a resumed session starts from the files as they are", not blocked and "promoted between" in str(read(root, RULES)), reason)

print("no snapshot of the session; the gate run by hand")
root = project()
(root / CONSTITUTION).write_text(FILES[CONSTITUTION] + "Article 9.\n")
blocked, reason = stop(root, "s8")
check("without a snapshot the comparison is with HEAD: blocked, said so, nothing put back", blocked and "protected/changed" in reason
      and "no snapshot of the guarded files" in reason and "Article 9" in str(read(root, CONSTITUTION)) and events(root) == [], reason)
check("…and no snapshot is taken from a turn that was blocked", not (root / STATE / "s8.json").exists())
start(root, "s8b")
(root / CONSTITUTION).write_text(FILES[CONSTITUTION] + "Article 10.\n")
by_hand = subprocess.run([sys.executable, str(GATE), "--layer", "stop"], cwd=root, capture_output=True, text=True, env=env_of(root), check=False)
check("by hand the gate blocks (exit 2) and never puts a file back", by_hand.returncode == 2 and "protected/changed" in by_hand.stderr
      and "Article 10" in str(read(root, CONSTITUTION)), by_hand.stderr)

print("the owner's own edit during a turn: discarded like any other, never lost, taken back with `accept`")
root = project()
start(root, "s9")
MINE = FILES[CONSTITUTION] + "Article 3, typed by the owner while the agent worked.\n"
(root / CONSTITUTION).write_text(MINE)
blocked, reason = stop(root, "s9")
ident = events(root)[0] if events(root) else ""
check("the gate cannot tell it from the agent's and names the owner's command", blocked and read(root, CONSTITUTION) == FILES[CONSTITUTION]
      and f"protected_guard.py accept {ident}" in reason, reason)
refused = guard(root, "accept", ident, owner=False)
check("`accept` inside a session is refused and changes nothing", refused.returncode == 2 and "refused inside a Claude Code session" in refused.stderr
      and read(root, CONSTITUTION) == FILES[CONSTITUTION], refused.stderr)
accepted = guard(root, "accept", ident)
check("in the owner's terminal it puts the edit back", accepted.returncode == 0 and read(root, CONSTITUTION) == MINE, accepted.stdout + accepted.stderr)
blocked, reason = stop(root, "s9")
check("…and the next turn passes with it", not blocked and reason == "" and read(root, CONSTITUTION) == MINE, reason)
check("an event that does not exist is an error", guard(root, "accept", "20000101T000000Z-1").returncode == 1)

print("commit_checkpoint.sh: a guarded file never goes into an agent's commit")
root = project()
(root / "app.py").write_text("def run():\n    return 3\n")
(root / CONSTITUTION).write_text(FILES[CONSTITUTION] + "Article 9.\n")
(root / SETTINGS).write_text('{"hooks": {}, "x": 1}\n')
done = subprocess.run(["bash", str(CHECKPOINT), "n1", "unit"], cwd=root, capture_output=True, text=True, env=env_of(root), check=False)
committed = sh(root, "git", "show", "--name-only", "--format=", "HEAD").stdout.split()
check("the work is committed, the guarded files are not", done.returncode == 0 and committed == ["app.py"], done.stdout + done.stderr + str(committed))
check("each one left out is named", f"guarded file left out of the commit (only the owner or the board runner commits it): {CONSTITUTION}" in done.stdout
      and f"commits it): {SETTINGS}" in done.stdout, done.stdout)
check("…and stays changed and unstaged in the working tree", sh(root, "git", "status", "--porcelain").stdout.split("\n")[:2]
      == [f" M {CONSTITUTION}", f" M {SETTINGS}"], sh(root, "git", "status", "--porcelain").stdout)
head = sh(root, "git", "rev-parse", "HEAD").stdout
(root / "app.py").write_text("def run():\n    return 4\n")
(root / ".github/workflows/deploy.yml").write_text("on: push\n")
sh(root, "git", "add", "app.py", ".github/workflows/deploy.yml")
done = subprocess.run(["bash", str(CHECKPOINT), "--staged", "n2", "unit"], cwd=root, capture_output=True, text=True, env=env_of(root), check=False)
check("--staged with a guarded file in the index refuses, names it and commits nothing", done.returncode == 1
      and ".github/workflows/deploy.yml" in done.stderr and "Nothing was committed" in done.stderr
      and sh(root, "git", "rev-parse", "HEAD").stdout == head, done.stdout + done.stderr)
sh(root, "git", "restore", "--staged", ".github/workflows/deploy.yml")
done = subprocess.run(["bash", str(CHECKPOINT), "--staged", "n2", "unit"], cwd=root, capture_output=True, text=True, env=env_of(root), check=False)
check("--staged without it commits as before", done.returncode == 0 and sh(root, "git", "show", "--name-only", "--format=", "HEAD").stdout.split() == ["app.py"],
      done.stdout + done.stderr)

print("the runner's commands: before, after, pending — the snapshot is held by the runner, not in a file")
root = project()
inside = guard(root, "before", owner=False)
check("`before` is a read: inside a session it prints the same and writes nothing (a runner started there still guards)", inside.returncode == 0
      and set(json.loads(inside.stdout)["files"]) == {CONSTITUTION, SETTINGS, RULES, WORKFLOW, MIGRATION} and not (root / STATE).exists(), inside.stderr)
check("`after` with no snapshot handed to it is an error, not a pass", guard(root, "after").returncode == 1
      and guard(root, "after", stdin="not a snapshot").returncode == 1 and guard(root, "after", stdin='{"files": {}}').returncode == 1)
before = guard(root, "before")
check("`before` prints the snapshot, content included, and writes nothing at all", before.returncode == 0
      and set(json.loads(before.stdout)["files"]) == {CONSTITUTION, SETTINGS, RULES, WORKFLOW, MIGRATION}
      and set(json.loads(before.stdout)["content"]) == set(json.loads(before.stdout)["files"]) and not (root / STATE).exists(), before.stdout + before.stderr)
quiet = guard(root, "after", stdin=before.stdout)
check("a session that changed nothing: exit 0, nothing printed", quiet.returncode == 0 and quiet.stdout == "", quiet.stdout + quiet.stderr)
(root / SETTINGS).write_text(CHANGED)
(root / "app.py").write_text("def run():\n    return 5\n")
after = guard(root, "after", stdin=before.stdout)
check("a session that changed the settings: exit 3, the file printed and put back, the code untouched", after.returncode == 3
      and after.stdout.split() == [SETTINGS] and read(root, SETTINGS) == FILES[SETTINGS] and "return 5" in str(read(root, "app.py")),
      after.stdout + after.stderr)
check("…with the patch and the journal entry, written by the runner", "disableAllHooks" in patches(root)
      and "runner (protected_guard.py)" in journal_text(root, "anomalies"), patches(root))
check("nothing is pending: no commit of the session touched a guarded file", guard(root, "pending", stdin=before.stdout).stdout == "")
before = guard(root, "before")
(root / SETTINGS).write_text(CHANGED)
commit(root, "the agent's own commit")
after = guard(root, "after", stdin=before.stdout)
pending = guard(root, "pending", stdin=before.stdout)
check("a change the session committed: put back, and named as the runner's to commit", after.returncode == 3
      and read(root, SETTINGS) == FILES[SETTINGS] and pending.returncode == 0 and pending.stdout.split() == [SETTINGS],
      after.stdout + pending.stdout + pending.stderr)

print("the runner's check does not rest on the state directory, and it fails closed (the two audits of board 724)")
root = project()
start(root, "s10")
before = guard(root, "before")
(root / SETTINGS).write_text(CHANGED)
for path in (root / STATE).glob("*.json"):   # the session rewrites every snapshot it can reach to agree with its change
    forged = json.loads(path.read_text())
    forged["files"][SETTINGS] = hashlib.sha256(CHANGED.encode()).hexdigest()
    forged["content"][SETTINGS] = base64.b64encode(CHANGED.encode()).decode()
    path.write_text(json.dumps(forged))
(root / STATE / "runner.json").write_text((root / STATE / "s10.json").read_text())
after = guard(root, "after", stdin=before.stdout)
check("forged snapshots in the state directory: the runner, which held its own, puts the file back", after.returncode == 3
      and read(root, SETTINGS) == FILES[SETTINGS], after.stdout + after.stderr)
(root / SETTINGS).write_text(CHANGED)
shutil.rmtree(root / STATE)
(root / STATE).write_text("jammed\n")   # a file where the state directory was: nothing can be written under it
after = guard(root, "after", stdin=before.stdout)
check("a state directory that cannot be written: the file is put back all the same, exit 3", after.returncode == 3
      and read(root, SETTINGS) == FILES[SETTINGS], after.stdout + after.stderr)
kept_at = after.stderr.split("the discarded change: ")[-1].split("\n")[0].strip()
check("…and the discarded change is kept in a temporary directory, named in the journal", Path(kept_at).is_file()
      and "disableAllHooks" in Path(kept_at).read_text() and kept_at in journal_text(root, "anomalies"), after.stderr)
(root / STATE).unlink()
(root / SETTINGS).unlink()
(root / SETTINGS).mkdir()
(root / SETTINGS / "x").write_text("a directory where the settings file was\n")
after = guard(root, "after", stdin=before.stdout)
check("a file that cannot be put back: exit 4, said so, never a pass", after.returncode == 4 and "NOT put back" in after.stderr
      and after.stdout.split() == [SETTINGS] and "НЕ вдалося повернути" in journal_text(root, "anomalies"), after.stdout + after.stderr)
shutil.rmtree(root / SETTINGS)
altered = json.loads(before.stdout)
altered["content"][SETTINGS] = base64.b64encode(CHANGED.encode()).decode()
(root / SETTINGS).write_text('{"third": true}\n')
after = guard(root, "after", stdin=json.dumps(altered))
check("content that does not have the hash the snapshot names is not written as if it were the old text", after.returncode == 4
      and read(root, SETTINGS) != CHANGED and "does not have the hash" in after.stderr, after.stdout + after.stderr + str(read(root, SETTINGS)))

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
