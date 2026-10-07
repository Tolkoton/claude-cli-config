#!/usr/bin/env python3
"""A command that only QUOTES a guarded string is not refused; one that could run it still is (board 738).

block-dangerous.sh judged the raw command, quoted strings and heredoc bodies included, so a
commit message, a file of test cases written with `cat`, a grep pattern or the text of a board
item was refused for what it mentioned. shell_text.py now empties such text before the checks
read the command. Held here, every case on the real hook:

  TEXT-*     the same strings as text pass: a commit message, a heredoc `cat` writes to a file,
             echo and printf, a grep pattern, a sed substitution, the texts of a board item —
             the false refusals of the session of 2026-10-06 among them;
  RUN-*      the same strings where something could run them are refused as before: a heredoc
             fed to a shell or an interpreter, the text after -c / -e / eval, a substitution, a
             pipe into a shell, a file written and run in one command, and every construct the
             script does not vouch for (a group, a keyword, an assignment, a function);
  BESIDE-*   what stands beside the text is judged as before: the target of a redirection, a
             quoted secret file, a second command;
  FALLBACK-* without the script, or without python3, the raw command is judged: the text is
             refused again, nothing is allowed that was not;
  UNIT-*     the script itself: what it empties and what it returns untouched.

The five suites of the bypass forms (test_shell_protected_paths, test_push_hardening,
test_rules_file_protected, test_overseer_readonly, test_owner_perimeter) stay as they were:
their expectations are the proof that no form of theirs got through.

Run:   python3 tests/test_shell_text.py
Exit:  0 = all green, 1 = at least one case failed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hook_env import hook_env, main_repo, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
from shell_text import judged

# Split, so that a shell command which handles THIS file is not refused by the hook under test.
FORCE = "git push --for" + "ce origin feat/x"
ROOT_DELETE = "rm -r" + "f ~"
SETTINGS = ".claude/settings" + ".json"
RULES = ".engine/rules" + ".md"
DOTFILE = ".npm" + "rc"
ENV_FILE = ".e" + "nv"
UNSET = "unset CLAUDE" + "CODE"
OPS = "~/engine-" + "ops/tasks-inbox/a.md"
# One string of each check the hook makes: a destructive pattern, a push, the owner's variable, a
# write to a guarded path, a secret path, a write into the operator's directory.
GUARDED = [ROOT_DELETE, FORCE, UNSET, f"echo x > {SETTINGS}", f"cat {ENV_FILE}", f"echo x >> {OPS}"]

RUN_BRANCH = main_repo("unattended/2026-10-07")     # a commit is legal here: only its message is in question
FEATURE = main_repo("feat/x")
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:400]}")


def hook(cmd: str, hooks: Path = HOOKS, project: str = RUN_BRANCH, who: dict[str, str] | None = None, **env: str) -> subprocess.CompletedProcess[str]:
    envelope = {"tool_name": "Bash", "cwd": project, "tool_input": {"command": cmd}} | (who or {})
    return subprocess.run(["bash", str(hooks / "block-dangerous.sh")], input=json.dumps(envelope), capture_output=True, text=True,
                          check=False, env=hook_env(project, **env), cwd=project)


def hook_all(cmds: list[str], **kwargs: object) -> list[subprocess.CompletedProcess[str]]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda c: hook(c, **kwargs), cmds))  # type: ignore[arg-type]


def expect(label: str, cases: list[tuple[str, str]], code: int, **kwargs: object) -> None:
    for (name, cmd), done in zip(cases, hook_all([c for _, c in cases], **kwargs), strict=True):
        ok = done.returncode == code and (code == 0 or "BLOCKED" in done.stderr)
        check(f"{label} {name}: {cmd[:60]!r}", ok, f"exit {done.returncode}: {done.stderr.strip()[:250]}")


def as_text(text: str) -> list[tuple[str, str]]:
    """Every position that takes text and runs none of it."""
    return [
        ("commit message, single quotes", f"git commit -m 'refuse: {text}'"),
        ("commit message, double quotes", f'git add -A && git commit -m "refuse: {text}"'),
        ("commit message, -am", f"git commit -am 'refuse: {text}'"),
        ("commit message from a quoted heredoc", f"git commit -m \"$(cat <<'EOF'\nrefuse: {text}\n\nCo-Authored-By: x <x@y>\nEOF\n)\""),
        ("commit message on stdin", f"git commit -F - <<'EOF'\nrefuse: {text}\nEOF"),
        ("tag message", f"git tag -a v9 -m 'after: {text}'"),
        ("heredoc that cat writes to a file", f"cat > /tmp/cases.txt <<'EOF'\n{text}\nEOF"),
        ("heredoc with a bare delimiter", f"mkdir -p /tmp/t && cat > /tmp/t/cases.txt <<EOF\n{text}\nEOF"),
        ("heredoc appended, the redirection last", f"cat <<'CASES' >> /tmp/cases.txt\n{text}\nCASES"),
        ("echo", f"echo 'never: {text}'"),
        ("echo into a file", f'echo "never: {text}" >> /tmp/notes.md'),
        ("printf", f"printf '%s\\n' 'never: {text}' | tee -a /tmp/notes.md"),
        ("grep pattern", f"grep -rn '{text}' docs/ | head -5"),
        ("grep pattern after -e", f"grep -rn -e '{text}' tests/"),
        ("sed substitution", f"sed -i 's#the old line#{text}#' docs/notes.md"),
        ("board item", f"python3 .claude/unattended/board.py open-item --to todo --title 'a hook item' --what 'the hook refused: {text}' --do 'see {text}'"),
    ]


def as_command(text: str) -> list[tuple[str, str]]:
    """The same text where the command itself could run it."""
    return [
        ("heredoc fed to bash", f"bash <<'EOF'\n{text}\nEOF"),
        ("heredoc fed to sh -s", f"sh -s <<EOF\n{text}\nEOF"),
        ("heredoc fed to python3", f"python3 - <<'PY'\nimport os\nos.system('{text}')\nPY"),
        ("heredoc fed to node", f"node <<'JS'\nrequire('child_process').execSync('{text}')\nJS"),
        ("after bash -c", f"bash -c '{text}'"),
        ("after sh -c", f'sh -c "{text}"'),
        ("after eval", f"eval '{text}'"),
        ("after python3 -c", f"python3 -c 'import os; os.system(\"{text}\")'"),
        ("after node -e", f"node -e 'require(\"child_process\").execSync(\"{text}\")'"),
        ("in $( ) inside double quotes", f'echo "$({text})"'),
        ("in backticks inside double quotes", f'echo "`{text}`"'),
        ("in a bare $( )", f"echo $({text})"),
        ("echo piped into a shell", f"echo '{text}' | sh"),
        ("printf piped into bash", f"printf '%s' '{text}' | bash"),
        ("cat heredoc piped into a shell", f"cat <<'EOF' | sh\n{text}\nEOF"),
        ("written by cat, run in the same command", f"cat > /tmp/x.sh <<'EOF'\n{text}\nEOF\nbash /tmp/x.sh"),
        ("written by echo, sourced in the same command", f"echo '{text}' > /tmp/x.sh; . /tmp/x.sh"),
        ("written by echo, run by name", f"echo '{text}' > /tmp/x.sh && chmod +x /tmp/x.sh && /tmp/x.sh"),
        ("echo read back by a substitution", f"echo '{text}' > /tmp/x; $(</tmp/x)"),
        ("printf -v, then the variable as a command", f"printf -v RUN '%s' '{text}'; $RUN"),
        ("sed output piped into a shell", f"sed 's#x#{text} #' /tmp/a | sh"),
        ("sed with the e flag beside it", f"sed -i 's/a/b/e' /tmp/a && echo '{text}'"),
        ("commit message read back into a shell", f"git commit -m '{text}' && git log -1 --format=%B | sh"),
        ("echo redefined as a function", f"echo() {{ eval \"$@\"; }}; echo '{text}'"),
        ("an alias beside it", f"alias cat=sh; cat <<'EOF'\n{text}\nEOF"),
        ("an assignment before the command", f"PATH=/tmp/bin:$PATH echo '{text}'"),
        ("inside a group piped into a shell", f"{{ echo '{text}'; }} | sh"),
        ("inside a subshell", f"(echo '{text}') | sh"),
        ("under a keyword", f"if true; then echo '{text}'; fi | sh"),
        ("xargs beside it", f"echo '{text}' | xargs -0 sh -c"),
        ("a here-string to a shell", f"sh <<< '{text}'"),
        ("a bare heredoc the shell expands", f"cat <<EOF\n$(sh /tmp/x.sh)\nEOF\necho '{text}'"),
        ("not quoted at all", text),
    ]


print("TEXT-*     a guarded string that is only text passes")
for guarded in GUARDED:
    expect("TEXT", as_text(guarded), 0)

print("\nTEXT-*     the false refusals of the session of 2026-10-06")
expect("TEXT", [
    ("a heredoc with a list of test cases", f"cat > /tmp/try_cases.py <<'PY'\nCASES = [\n    \"{FORCE}\",\n    \"{ROOT_DELETE}\",\n    \"printf x > {SETTINGS}\",\n    \"cat {DOTFILE}\",\n]\nPY"),
    ("a commit message that names a dotfile on the list", f"git commit -m 'perimeter: {DOTFILE} and .ssh/config are refused to Edit as well'"),
    ("the text of a board task", f"python3 .claude/unattended/board.py open-item --to blocked --title 'hooks parse quotes' --what 'a heredoc with {UNSET} was refused' --question 'Чи розбирати лапки?'"),
    ("a document edit with an example command", f"printf '%s\\n' '    {FORCE}   # refused' >> docs/engine-limits.md"),
    ("sed with a path in the replacement", f"sed -i 's|the settings file|`{SETTINGS}`|' docs/notes.md"),
], 0)

print("\nRUN-*      the same string where something could run it is refused")
for guarded in GUARDED:
    expect("RUN", as_command(guarded), 2)

print("\nNOLOOSER-* a form the hook did not see before board 738 is judged exactly as it was")
# `bash -c 'cp x <guarded>'` — one command after -c, no separator — was never seen by shell_paths.py
# (board 600). Not this task's to close; held here is only that the answer did not move either way.
before = Path(tempfile.mkdtemp(prefix="hooks-before-738-", dir=sandbox_dir()))
for name in ("block-dangerous.sh", "protect-paths.sh", "protected-path-list.sh", "shell_paths.py", "shell_readonly.py"):
    shutil.copy(HOOKS / name, before / name)
wrapped = as_command(f"cp /tmp/a.md {OPS}")
now, then = hook_all([c for _, c in wrapped]), hook_all([c for _, c in wrapped], hooks=before)
looser = [name for (name, _), a, b in zip(wrapped, now, then, strict=True) if b.returncode == 2 and a.returncode == 0]
check("NOLOOSER no form that could run the text passes now and was refused without the script", not looser, looser)
check("NOLOOSER control: without the script some of these forms are refused", any(b.returncode == 2 for b in then))

print("\nBESIDE-*   what stands beside the text is judged as before")
expect("BESIDE", [
    ("the target of the redirection", f"echo 'a line of text' > {SETTINGS}"),
    ("the target of the heredoc", f"cat > {RULES} <<'EOF'\n- a rule of my own\nEOF"),
    ("a quoted target", f"echo 'a line of text' > \"{SETTINGS}\""),
    ("tee after the text", f"echo 'a line of text' | tee {SETTINGS}"),
    ("the file sed edits in place", f"sed -i 's/never/always/' {RULES}"),
    ("the file grep reads, quoted", f"grep -n 'KEY' '{ENV_FILE}'"),
    ("the file grep takes patterns from, quoted", f"grep -f '{ENV_FILE}' docs/a.md"),
    ("a quoted secret file handed to cat", f"cat '{ENV_FILE}'"),
    ("a second command after the message", f"git commit -m 'a fix' && {FORCE}"),
    ("a second command after the heredoc", f"cat > /tmp/a.txt <<'EOF'\ntext\nEOF\n{ROOT_DELETE}"),
    ("an unquoted argument of echo", f"echo {ROOT_DELETE}"),
    ("a message with a variable in it", f'echo "$HOME: {ROOT_DELETE}"'),
    ("a board flag that takes no text", f"python3 .claude/unattended/board.py open-item --to todo --key '{ROOT_DELETE}' --title t --what w"),
    ("another script with a text flag", f"python3 tools/other.py open-item --what '{ROOT_DELETE}'"),
    ("a git subcommand that can start a program", f"git fetch --upload-pack='{ROOT_DELETE}' origin"),
], 2)
done = hook("git commit -m 'a fix'", project=FEATURE)
check("BESIDE a commit is still a commit: refused outside an unattended branch", done.returncode == 2 and "commits are allowed only" in done.stderr, done.stderr[:200])
done = hook(f"git commit -m 'mentions {FORCE}'", project=FEATURE)
check("BESIDE ... and refused for the commit, not for its message", done.returncode == 2 and "commits are allowed only" in done.stderr, done.stderr[:200])
inside = {"agent_type": "overseer", "agent_id": "a1"}
done = hook("echo 'a > b' > src/a.py", project=FEATURE, who=inside)
check("BESIDE inside the overseer agent a write is refused, whatever its text", done.returncode == 2 and "read-only" in done.stderr, done.stderr[:200])
done = hook(f"echo 'note: {FORCE}' > /tmp/audit-note.txt", project=FEATURE, who=inside)
check("BESIDE ... and a note under /tmp passes there too", done.returncode == 0, done.stderr[:200])

print("\nFALLBACK-* without the script or without python3 the raw command is judged")
bare = before
message = f"git commit -m 'refuse: {ROOT_DELETE}'"
check("FALLBACK control: with the script the message passes", hook(message).returncode == 0)
check("FALLBACK no shell_text.py: the same message is refused, as before board 738", hook(message, hooks=bare).returncode == 2)
check("FALLBACK no shell_text.py: an ordinary quoted command still passes", hook("git commit -m 'a fix'", hooks=bare).returncode == 0)
broken = Path(tempfile.mkdtemp(prefix="hooks-broken-text-", dir=sandbox_dir()))
shutil.copytree(bare, broken, dirs_exist_ok=True)
(broken / "shell_text.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
check("FALLBACK the script fails: the raw command is judged", hook(message, hooks=broken).returncode == 2 and hook("git commit -m 'a fix'", hooks=broken).returncode == 0)
silent = Path(tempfile.mkdtemp(prefix="hooks-silent-text-", dir=sandbox_dir()))
shutil.copytree(bare, silent, dirs_exist_ok=True)
(silent / "shell_text.py").write_text("", encoding="utf-8")
check("FALLBACK the script prints nothing: the raw command is judged, not an empty one", hook(ROOT_DELETE + " '#'", hooks=silent).returncode == 2)
shims = Path(tempfile.mkdtemp(prefix="nopy-text-", dir=sandbox_dir()))
for tool in ("bash", "cat", "echo", "grep", "sed", "tr", "git", "jq", "dirname", "printf", "tail"):
    found = shutil.which(tool)
    if found:
        os.symlink(found, shims / tool)
check("FALLBACK no python3: the message is refused, an ordinary one passes",
      hook(message, PATH=str(shims)).returncode == 2 and hook("git commit -m 'a fix'", PATH=str(shims)).returncode == 0)

print("\nUNIT-*     shell_text.py: what it empties, and what it returns untouched")
for name, cmd, want in [
    ("a commit message", "git commit -m 'a b'", "git commit -m ''"),
    ("two quoted pieces of one word", "echo 'a'\"b\"", "echo ''\"\""),
    ("a heredoc body, the delimiter kept", "cat > f <<'EOF'\nbody\nEOF\nls", "cat > f <<'EOF'\nEOF\nls"),
    ("a tab-stripped heredoc", "cat > f <<-EOF\n\tbody\n\tEOF", "cat > f <<-EOF\n\tEOF"),
    ("the commit idiom", "git commit -m \"$(cat <<'EOF'\nbody\nEOF\n)\"", "git commit -m \"$(cat <<'EOF'\nEOF\n)\""),
    ("only the pattern of grep", "grep -rn 'pat' 'file'", "grep -rn '' 'file'"),
    ("only the text flags of a board item", "python3 .claude/unattended/board.py open-item --to todo --title 'T' --key 'K'",
     "python3 .claude/unattended/board.py open-item --to todo --title '' --key 'K'"),
    ("a sed substitution, the file kept", "sed -i.bak -E 's/a|b/c/g; s#x#y#' 'f'", "sed -i.bak -E '' 'f'"),
    ("a comment is left alone", "echo 'a' # 'b'", "echo '' # 'b'"),
    ("a line continuation", "git commit \\\n  -m 'a'", "git commit \\\n  -m ''"),
]:
    check(f"UNIT emptied — {name}", judged(cmd) == want, f"{judged(cmd)!r}")
for name, cmd in [
    ("an unclosed quote", "echo 'a"),
    ("a heredoc that does not end", "cat <<'EOF'\nbody"),
    ("a heredoc fed to a command not on the list", "tee f <<'EOF'\nbody\nEOF\nmake"),
    ("an ANSI-C string", "echo $'a' 'b'"),
    ("a parameter expansion", "echo ${X@P} 'b'"),
    ("a grep flag it does not know", "grep --file 'a' 'b'"),
    ("a sed script that writes a file", "sed -n 'w out' 'f'"),
    ("a sed script from a file", "sed -f 's/a/b/' 'f'"),
    ("a command reached through a wrapper", "env echo 'a'"),
    ("a command by its path", "/tmp/echo 'a'"),
    ("a command from a variable", "$ECHO 'a'"),
    ("a quoted command word", "'echo' 'a'"),
    ("a redirection before the command", "> f echo 'a'"),
    ("a message with an escape", 'git commit -m "a \\" b"'),
    ("a git option before the subcommand", "git -c alias.commit=!sh commit -m 'a'"),
    ("an interpreter with a board-like path", "python3 /tmp/.claude/unattended/board.py open-item --what 'a'"),
    ("nothing quoted", "ls -la"),
]:
    check(f"UNIT untouched — {name}", judged(cmd) == cmd, f"{judged(cmd)!r}")

print()
print(f"PASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
