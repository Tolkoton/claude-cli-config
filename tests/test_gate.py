#!/usr/bin/env python3
"""gate.py: the layers, the report, the Stop counter, and the bypass guard.

Deterministic: every case runs gate.py in a throwaway git repository. The tools it would call
(ruff, mypy, pytest) are PATH shims that record their argv, so a case proves WHICH command the
gate issues and on WHICH files; real-tool behaviour is the evals' job (evals/run_gate_evals.py).
Nothing here talks to a model or the network.

Run:   python3 tests/test_gate.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tool_pins import tool_versions as VERSIONS

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           check=True).stdout.strip())
GATE = ROOT / ".claude" / "hooks" / "gate.py"
PASS = 0
FAIL = 0

# The strings the guard looks for are built here, never written as one literal in this file, so
# that this file is itself clean under the guard it tests (and a test below pins that).
TI = "# type" + ": ignore"
NQ = "# no" + "qa"
SKIP = "pytest.mark" + ".skip"


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:600]}")


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def new_repo(env_lines: str = 'CODE_EXTENSIONS="py"\n', commit: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="gate-"))
    sh(root, "git", "init", "-q", "-b", "main")
    (root / ".claude").mkdir()
    (root / ".claude" / "project.env").write_text(env_lines)
    (root / "mod.py").write_text("x = 1\n")
    sh(root, "git", "add", "-A")
    if commit:
        sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return root


def set_env(root: Path, text: str) -> None:
    """Change project.env and commit it, so the guard sees no change of the gate's settings."""
    (root / ".claude/project.env").write_text(text)
    sh(root, "git", "add", "-A")
    sh(root, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "env", "--allow-empty")


def shims(root: Path, version: str | None = None, names: tuple[str, ...] = ("ruff", "mypy", "pytest"),
          where: str = "_shims", **exit_codes: int) -> Path:
    """ruff / mypy / pytest / uv stand-ins: log argv to <root>/calls.log, exit as told. `--version`
    names the version tool_versions.py pins (board 107) unless `version` says another."""
    d = root / where
    d.mkdir(parents=True, exist_ok=True)
    for name in names:
        rc = exit_codes.get(name, 0)
        out = {"ruff": "mod.py:1:1: F401 unused import", "mypy": "mod.py:1: error: bad type",
               "pytest": "FAILED tests/test_mod.py::t", "uvx": "", "black": ""}[name]
        shown = version or VERSIONS.VERSIONS.get(name, "1.0")
        p = d / name
        p.write_text(f'#!/usr/bin/env bash\n[ "$1" = --version ] && {{ echo "{name} {shown}"; exit 0; }}\n'
                     f'echo "{where.strip("_")}:{name} $*" >> "{root}/calls.log"\n'
                     f'[ {rc} -ne 0 ] && echo "{out}"\nexit {rc}\n')
        p.chmod(0o755)
    return d


def without_uvx() -> str:
    """PATH with no directory that holds uvx (nor what sits beside it, mypy among them)."""
    return os.pathsep.join(d for d in os.environ["PATH"].split(os.pathsep) if d and not (Path(d) / "uvx").exists())


def gate(root: Path, *args: str, stdin: Any = None, path: Path | None = None, rest: str | None = None
         ) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"} | {"CLAUDE_PROJECT_DIR": str(root)}
    if rest is not None:
        env["PATH"] = rest
    if path:
        env["PATH"] = f"{path}:{env['PATH']}"
    return subprocess.run([sys.executable, str(GATE), *args], cwd=root, capture_output=True, text=True,
                          env=env, input=json.dumps(stdin) if stdin is not None else "", check=False)


def hook_stop(root: Path, session: str = "s1", active: bool = False, path: Path | None = None,
              rest: str | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    proc = gate(root, "--layer", "stop", "--hook", stdin={"stop_hook_active": active, "session_id": session},
                path=path, rest=rest)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        payload = {"_malformed": proc.stdout}
    return proc, payload


def report(root: Path) -> Any:
    return json.loads((root / ".claude/state/gate/last-report.json").read_text())


def calls(root: Path) -> str:
    p = root / "calls.log"
    return p.read_text() if p.exists() else ""


def write_check(root: Path, name: str, rc: int, text: str = "boom") -> str:
    p = root / name
    p.write_text(f'#!/usr/bin/env bash\necho "{name}" >> "{root}/ran.log"\necho "{text}"\nexit {rc}\n')
    p.chmod(0o755)
    return f"bash {p}"


def rules(root: Path) -> list[str]:
    return [f["rule"] for f in report(root)["findings"]]


def severities(root: Path, rule: str) -> list[str]:
    return [f["severity"] for f in report(root)["findings"] if f["rule"] == rule]


# ---------------------------------------------------------------- report + CLI contract
print("report and exit codes")
r = new_repo()
(r / "mod.py").write_text("x = 2\n")
cmd = write_check(r, "lint.sh", 1, "mod.py:1:1: E999 broken")
(r / ".claude/project.env").write_text(f'CODE_EXTENSIONS="py"\nLINT_CMD="{cmd}"\n')
p = gate(r, "--layer", "ci")
check("ci: a failing LINT_CMD exits 2", p.returncode == 2, (p.returncode, p.stderr))
rep = report(r)
check("report names layer, result, exit_code", (rep["layer"], rep["result"], rep["exit_code"]) == ("ci", "block", 2), rep)
f0 = rep["findings"][0]
check("finding carries file, line, rule, severity, message, hint",
      all(k in f0 for k in ("file", "line", "rule", "severity", "message", "hint")) and f0["file"] == "mod.py"
      and f0["line"] == 1 and f0["severity"] == "block", f0)
check("timings are recorded per step and in total", "total" in rep["timings_ms"] and "lint" in rep["timings_ms"]["steps"], rep["timings_ms"])
check("stderr carries a concise list", "gate[ci]" in p.stderr and "mod.py:1" in p.stderr, p.stderr)
(r / ".claude/project.env").write_text('CODE_EXTENSIONS="py"\nLINT_CMD="true"\n')
p = gate(r, "--layer", "ci")
check("ci: all green exits 0 and reports pass", p.returncode == 0 and report(r)["result"] == "pass", p.stderr)
check("an unknown layer is refused", gate(r, "--layer", "nope").returncode == 2)

# ---------------------------------------------------------------- stop: preserved behaviour
print("stop: what verify-on-stop always did")
r = new_repo()
proc, payload = hook_stop(r)
check("nothing changed -> silent allow", proc.returncode == 0 and not proc.stdout.strip(), proc.stdout)
(r / "notes.md").write_text("docs\n")
proc, payload = hook_stop(r)
check("a docs-only change does not run the gates", proc.returncode == 0 and not proc.stdout.strip() and not (r / "ran.log").exists())
lint, types, tests = (write_check(r, n, rc) for n, rc in (("lint.sh", 0), ("types.sh", 1), ("tests.sh", 0)))
(r / ".claude/project.env").write_text(f'CODE_EXTENSIONS=".PY, ts"\nLINT_CMD="{lint}"\nTYPECHECK_CMD="{types}"\nTEST_CMD="{tests}"\n')
(r / "mod.py").write_text("x = 2\n")
proc, payload = hook_stop(r)
reason = str(payload.get("reason", ""))
check("a failing type check blocks with its own heading", payload.get("decision") == "block" and "TYPECHECK FAILED" in reason, proc.stdout)
check("tests do not run after a failed check", "tests.sh" not in (r / "ran.log").read_text())
check("the block reason carries the check's output intact", "boom" in reason, reason)
set_env(r, f'CODE_EXTENSIONS="py"\nPROJECT_MARKER="absent.toml"\nLINT_CMD="{write_check(r, "l2.sh", 1)}"\n')
(r / "mod.py").write_text("x = 3\n")
proc, payload = hook_stop(r, session="m")
check("PROJECT_MARKER absent -> verification skipped", not proc.stdout.strip() and proc.returncode == 0, proc.stdout)
check("PROJECT_MARKER absent -> the lint command did not run", "l2.sh" not in (r / "ran.log").read_text())
set_env(r, 'CODE_EXTENSIONS="ts"\n')
(r / "app.ts").write_text("export {}\n")
proc, payload = hook_stop(r, session="e")
check("non-Python extensions and no commands: no block, a log finding", not proc.stdout.strip() and "no-checks" in rules(r), rules(r))
(r / ".claude/project.env").write_text(f'CODE_EXTENSIONS="py"\nLINT_CMD="{write_check(r, "l3.sh", 1)}"\n')
proc, payload = hook_stop(r, session="a", active=True)
check("stop_hook_active with a fresh counter: not verified again", not proc.stdout.strip() and proc.returncode == 0, proc.stdout)

# ---------------------------------------------------------------- stop: the counter
print("stop: counter, re-entry, escalation")
r = new_repo()
set_env(r, f'CODE_EXTENSIONS="py"\nLINT_CMD="{write_check(r, "lint.sh", 1)}"\n')
(r / "mod.py").write_text("x = 2\n")
_, p1 = hook_stop(r, "A")
check("block 1", p1.get("decision") == "block")
_, p2 = hook_stop(r, "A", active=True)
check("re-entry after OUR block is verified again (flag set, counter 1) and blocks", p2.get("decision") == "block", p2)
_, other = hook_stop(r, "B")
check("another session has its own count", other.get("decision") == "block" and report(r)["stop"]["consecutive_blocks"] == 1, report(r))
proc, p3 = hook_stop(r, "A", active=True)
check("the 3rd block escalates: the turn may end", p3.get("decision") is None and "GATE ESCALATION" in str(p3.get("systemMessage")), proc.stdout)
parked = (r / ".engine/overseer/parked.md").read_text()
check("the escalation is parked for a human", "PARKED" in parked and "Class: human-input" in parked and "last-report.json" in parked, parked)
check("escalation is recorded in the report and the counter resets",
      report(r)["result"] == "escalated" and report(r)["stop"]["escalated"] is True, report(r))
_, p4 = hook_stop(r, "A")
check("after the escalation counting starts over", p4.get("decision") == "block" and report(r)["stop"]["consecutive_blocks"] == 1, report(r))
set_env(r, f'CODE_EXTENSIONS="py"\nLINT_CMD="{write_check(r, "ok.sh", 0)}"\n')
hook_stop(r, "A")
check("a pass resets the counter", report(r)["stop"]["consecutive_blocks"] == 0, report(r))
set_env(r, f'CODE_EXTENSIONS="py"\nGATE_MAX_BLOCKS="2"\nLINT_CMD="{write_check(r, "lint.sh", 1)}"\n')
(r / "mod.py").write_text("x = 77\n")
hook_stop(r, "C")
_, e2 = hook_stop(r, "C")
check("GATE_MAX_BLOCKS is honoured", "GATE ESCALATION" in str(e2.get("systemMessage")), e2)

# ---------------------------------------------------------------- stop: incremental auto-detect
print("stop: incremental checks on the changed files")
r = new_repo()
(r / "pyproject.toml").write_text('[tool.ruff]\nline-length = 100\n[tool.mypy]\nstrict = true\n')
(r / "tests").mkdir()
(r / "tests/test_mod.py").write_text("def test_a() -> None:\n    pass\n")
(r / "other.py").write_text("y = 1\n")
sh(r, "git", "add", "-A")
sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "more")
sd = shims(r)
(r / "mod.py").write_text("x = 3\n")
proc, payload = hook_stop(r, path=sd)
log = calls(r)
check("ruff and mypy get ONLY the changed file", "ruff check --force-exclude mod.py" in log and "mypy mod.py" in log and "other.py" not in log, log)
check("pytest gets the sibling test of the changed module", "pytest -x --no-header -q tests/test_mod.py" in log, log)
check("a green change allows silently", not proc.stdout.strip(), proc.stdout)
(r / "calls.log").unlink()
(r / "other.py").write_text("y = 2\n")
sh(r, "git", "checkout", "mod.py")
proc, payload = hook_stop(r, path=sd)
check("a module with no sibling test: tests not run, said in the report", "pytest" not in calls(r) and "tests/unmapped" in rules(r), calls(r))
(r / "calls.log").unlink()
sd = shims(r, mypy=1)
proc, payload = hook_stop(r, session="t", path=sd)
check("a type error blocks with TYPECHECK FAILED and the diagnostic as a finding",
      "TYPECHECK FAILED" in str(payload.get("reason")) and any(f["rule"] == "typecheck" and f["line"] == 1 for f in report(r)["findings"]), payload)
check("tests do not run after a failed type check", "pytest" not in calls(r), calls(r))
sd = shims(r, ruff=1)
(r / "calls.log").unlink(missing_ok=True)
proc, payload = hook_stop(r, session="l", path=sd)
check("a lint error blocks with LINT FAILED", "LINT FAILED" in str(payload.get("reason")), payload)
(r / "pyproject.toml").write_text("[project]\nname = 'x'\n")
(r / "calls.log").unlink(missing_ok=True)
hook_stop(r, session="n", path=shims(r))
check("without [tool.ruff] / [tool.mypy] the tools are not run", "ruff" not in calls(r) and "mypy" not in calls(r), calls(r))

print("stop: the check tools at the engine's pinned versions (board 107)")
r = new_repo()
(r / "pyproject.toml").write_text('[tool.ruff]\nline-length = 100\n[tool.mypy]\nstrict = true\n')
sh(r, "git", "add", "-A")
sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "tools")
(r / "mod.py").write_text("x = 4\n")
old = shims(r, version="0.0.1")
proc, payload = hook_stop(r, session="v1", path=old, rest=without_uvx())
reason = str(payload.get("reason"))
check("another version on PATH and no uvx: the stop is blocked, and the reason names both versions",
      proc.returncode == 0 and payload.get("decision") == "block" and "ruff did not run" in reason
      and "0.0.1" in reason and VERSIONS.VERSIONS["ruff"] in reason and "mypy did not run" in reason, payload)
check("...and neither tool judged the change with the other version", "ruff check" not in calls(r) and "mypy mod.py" not in calls(r), calls(r))
(r / "calls.log").unlink(missing_ok=True)
fetch = shims(r, version="0.0.1", names=("ruff", "mypy", "pytest", "uvx"), where="_fetch")
proc, payload = hook_stop(r, session="v2", path=fetch, rest=without_uvx())
log = calls(r)
check("another version on PATH and uvx at hand: uvx runs exactly the pinned release",
      f"fetch:uvx --quiet ruff@{VERSIONS.VERSIONS['ruff']} check --force-exclude mod.py" in log
      and f"fetch:uvx --quiet mypy@{VERSIONS.VERSIONS['mypy']} mod.py" in log and "fetch:ruff check" not in log, log)
(r / "calls.log").unlink(missing_ok=True)
own = shims(r, version="9.9.9", names=("ruff", "mypy"), where=".venv/bin")
proc, payload = hook_stop(r, session="v3", path=old, rest=without_uvx())
log = calls(r)
check("a project that installed the tools in its own virtual environment keeps its own versions",
      "venv/bin:ruff check --force-exclude mod.py" in log and "venv/bin:mypy mod.py" in log and "shims:ruff" not in log, log)

# ---------------------------------------------------------------- pre_commit and ci: the full set
print("pre_commit / ci: the full set")
r = new_repo()
(r / "pyproject.toml").write_text('[tool.ruff]\nline-length = 100\n[tool.mypy]\nstrict = true\n')
(r / "tests").mkdir()
(r / "tests/test_mod.py").write_text("def test_a() -> None:\n    pass\n")
sh(r, "git", "add", "-A")
sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "t")
sd = shims(r)
p = gate(r, "--layer", "ci", path=sd)
log = calls(r)
check("ci: ruff and mypy run over the project, pytest over everything",
      "ruff check --force-exclude ." in log and "mypy ." in log and "pytest -x --no-header -q\n" in log and p.returncode == 0, log)
set_env(r, f'CODE_EXTENSIONS="py"\nTEST_CMD="{write_check(r, "fast.sh", 0)}"\nTEST_CMD_FULL="{write_check(r, "full.sh", 0)}"\nLINT_CMD="true"\n')
gate(r, "--layer", "ci")
gate(r, "--layer", "pre_commit")
ran = (r / "ran.log").read_text()
check("TEST_CMD_FULL is what pre_commit and ci run", ran.count("full.sh") == 2 and "fast.sh" not in ran, ran)
hook_stop(r, "z")
check("...and stop keeps to TEST_CMD (nothing changed here, so no run at all)", "fast.sh" not in (r / "ran.log").read_text())
(r / "mod.py").write_text("x = 9\n")
hook_stop(r, "z2")
check("stop with a change runs the fast TEST_CMD", "fast.sh" in (r / "ran.log").read_text() and (r / "ran.log").read_text().count("full.sh") == 2)

# ---------------------------------------------------------------- post_write
print("post_write: format, quick lint, never blocks")
r = new_repo()
sd = shims(r, ruff=1)
(r / "uv.lock").touch()
payload_in = {"tool_input": {"file_path": str(r / "mod.py")}}
p = gate(r, "--layer", "post_write", "--hook", stdin=payload_in, path=sd)
out = json.loads(p.stdout) if p.stdout.strip() else {}
ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
check("a lint finding comes back as additionalContext and the exit is 0", p.returncode == 0 and "F401" in ctx and out["hookSpecificOutput"]["hookEventName"] == "PostToolUse", p.stdout)
check("the finding is a warn, not a block", severities(r, "lint") == ["warn"], rules(r))
r2 = new_repo()
p = gate(r2, "--layer", "post_write", "--hook", stdin={"tool_input": {"file_path": str(r2 / "mod.py")}}, path=shims(r2))
check("a clean edit prints nothing and writes no report", p.returncode == 0 and not p.stdout.strip() and not (r2 / ".claude/state/gate/last-report.json").exists(), p.stdout)
p = gate(r2, "--layer", "post_write", "--hook", stdin={"tool_input": {"file_path": str(r2 / "gone.py")}})
check("a vanished path is a no-op", p.returncode == 0 and not p.stdout.strip())
r3 = new_repo()
(r3 / "mod.py").write_text("import os\nx=1\n")
p = gate(r3, "--layer", "post_write", "--hook", stdin={"tool_input": {"file_path": str(r3 / "mod.py")}},
         path=shims(r3, version="0.0.1", names=("ruff", "black")), rest=without_uvx())
check("board 107: a ruff of another version on PATH neither formats nor lints, nor hands the file to black — "
      "the report says why, the edit is never blocked",
      p.returncode == 0 and not calls(r3) and (r3 / "mod.py").read_text() == "import os\nx=1\n"
      and "tools/version" in rules(r3), calls(r3) + p.stdout)
p = gate(r2, "--layer", "post_write", "--hook", stdin=None)
check("an empty envelope never blocks", p.returncode == 0)

# ---------------------------------------------------------------- bypass guard
print("bypass guard: stop and pre_commit")


def guarded(files: dict[str, str], env: str = 'CODE_EXTENSIONS="py"\n', layer: str = "stop", stage: bool = False,
            base_files: dict[str, str] | None = None) -> tuple[Path, dict[str, object]]:
    r = new_repo(env_lines=env)
    for name, body in (base_files or {}).items():
        (r / name).parent.mkdir(parents=True, exist_ok=True)
        (r / name).write_text(body)
    sh(r, "git", "add", "-A")
    sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base", "--allow-empty")
    for name, body in files.items():
        (r / name).parent.mkdir(parents=True, exist_ok=True)
        (r / name).write_text(body)
    if stage:
        sh(r, "git", "add", "-A")
    if layer == "stop":
        _, payload = hook_stop(r)
        return r, payload
    p = gate(r, "--layer", layer)
    return r, {"rc": p.returncode, "stderr": p.stderr}


def blocked(r: Path, rule: str) -> bool:
    return "block" in severities(r, rule)


r, pl = guarded({"mod.py": f"x = 1  {TI}[assignment]\n"})
check("a new type-ignore blocks the Stop gate", pl.get("decision") == "block" and blocked(r, "bypass/type-ignore"), pl)
check("...naming file and line", "mod.py:1" in str(pl.get("reason")), pl)
r, pl = guarded({"mod.py": f"import os  {NQ}: F401\nx = 1\n"})
check("a new noqa blocks", blocked(r, "bypass/noqa"), rules(r))
for label, line in (("skip", f"@{SKIP}\ndef test_a() -> None:\n    pass\n"),
                    ("skipif", "@pytest.mark" + ".skipif(True, reason='r')\ndef test_a() -> None:\n    pass\n"),
                    ("xfail", "@pytest.mark" + ".xfail\ndef test_a() -> None:\n    pass\n"),
                    ("skip", "def test_a() -> None:\n    pytest" + ".skip('later')\n")):
    r, pl = guarded({"tests/test_x.py": "import pytest\n\n" + line})
    check(f"a new {label} blocks ({line.splitlines()[0][:28]!r})", blocked(r, "bypass/skip" if label == "skipif" else f"bypass/{label}"), rules(r))
r, pl = guarded({"mod.py": f"x = 1  {TI}  # gate-allow: stub has no types upstream\n"})
check("same-line gate-allow with a real reason passes", pl.get("decision") is None and severities(r, "bypass/type-ignore") == ["log"], pl)
r, pl = guarded({"mod.py": f"# gate-allow: vendored stub has no types\nx = 1  {TI}\n"})
check("a gate-allow on the comment line above passes", pl.get("decision") is None, pl)
r, pl = guarded({"mod.py": f"x = 1  {TI}  # gate-allow: ok\n"})
check("a reason that is too short does not pass", blocked(r, "bypass/type-ignore"), rules(r))
r, pl = guarded({"mod.py": f"y = 0\nx = 1  {TI}\n# gate-allow: stray reason far away\nz = 2\n"})
check("a gate-allow that is not adjacent does not pass", blocked(r, "bypass/type-ignore"), rules(r))
r, pl = guarded({"mod.py": f'"""Docs: never write {TI} or {NQ} or {SKIP}."""\nx = "{TI}"\n'})
check("TRAP: a string or docstring that merely mentions them is not a finding", pl.get("decision") is None and not any(x.startswith("bypass/") and x != "bypass/unparsed" for x in rules(r)), rules(r))
r, pl = guarded({"mod.py": f"x = 1  {TI}\ny = 2\n"}, base_files={"mod.py": f"x = 1  {TI}\n"})
check("a suppression that was already there is not new", pl.get("decision") is None, pl)
r, pl = guarded({"mod.py": f"x = 1  {TI}\ny = 2  {TI}\n"}, base_files={"mod.py": f"x = 1  {TI}\n"})
check("...but a second one added next to it is", blocked(r, "bypass/type-ignore") and report(r)["findings"][0]["line"] == 2, report(r))
r, pl = guarded({"brand_new.py": f"x = 1  {TI}\n"})
check("a brand-new untracked file: every line counts as added", blocked(r, "bypass/type-ignore"), rules(r))
r, pl = guarded({"mod.py": f"x = 1  {TI}\n"}, layer="pre_commit", stage=True)
check("pre_commit: a staged type-ignore blocks (exit 2)", pl["rc"] == 2 and blocked(r, "bypass/type-ignore"), pl)
r, pl = guarded({"mod.py": f"x = 1  {TI}\n"}, layer="pre_commit", stage=False)
check("pre_commit judges the INDEX: an unstaged ignore is not in this commit", pl["rc"] == 0, pl)
r, pl = guarded({"mod.py": f"x = 1  {TI}\n"}, layer="ci")
check("ci does not run the guard (the owner's spec: stop and pre_commit)", pl["rc"] == 0 and not any(x.startswith("bypass/") for x in rules(r)), rules(r))

print("bypass guard: runs without the project marker")
NO_MARKER = 'CODE_EXTENSIONS="py"\nPROJECT_MARKER="absent.toml"\n'
r, pl = guarded({"mod.py": f"import os  {NQ}\n"}, env=NO_MARKER)
check("no marker: an added noqa still blocks", pl.get("decision") == "block" and blocked(r, "bypass/noqa"), pl)
check("no marker: the skipped verification is still logged", severities(r, "marker") == ["log"], rules(r))
r, pl = guarded({"mod.py": f"x: int = 'a'  {TI}\n"}, env=NO_MARKER)
check("no marker: an added type-ignore still blocks", blocked(r, "bypass/type-ignore"), pl)
r, pl = guarded({"tests/test_mod.py": f"import pytest\n\n\n@{SKIP}\ndef test_a() -> None:\n    assert False\n"}, env=NO_MARKER)
check("no marker: a skipped test still blocks", blocked(r, "bypass/skip"), pl)
r, pl = guarded({"ruff.toml": "line-length = 120\n"}, env=NO_MARKER, base_files={"ruff.toml": "line-length = 100\n"})
check("no marker: a changed linter configuration still blocks", blocked(r, "bypass/config"), pl)
r, pl = guarded({"mod.py": f"import os  {NQ}  # gate-allow: os is re-exported for the plugins\n"}, env=NO_MARKER)
check("no marker: a justified suppression passes", pl.get("decision") is None and severities(r, "bypass/noqa") == ["log"], pl)
r, pl = guarded({"mod.py": "x = 2\n"}, env=NO_MARKER)
check("no marker: a clean change passes", pl.get("decision") is None and rules(r) == ["marker"], (pl, rules(r)))

print("bypass guard: configuration")
PY = '[tool.ruff]\nline-length = 100\n[tool.ruff.lint]\nselect = ["E", "F"]\n[tool.mypy]\nstrict = true\n'
r, pl = guarded({"pyproject.toml": PY.replace('"E", "F"', '"E"')}, base_files={"pyproject.toml": PY})
check("narrowing the ruff rule set blocks", pl.get("decision") == "block" and blocked(r, "bypass/config"), pl)
r, pl = guarded({"pyproject.toml": PY.replace("strict = true", "strict = false")}, base_files={"pyproject.toml": PY})
check("loosening mypy blocks", blocked(r, "bypass/config"), rules(r))
r, pl = guarded({"pyproject.toml": "# a comment\n" + PY.replace("\n", "\n\n", 1)}, base_files={"pyproject.toml": PY})
check("a reformat or a comment in pyproject.toml is not a change of the settings", pl.get("decision") is None, pl)
r, pl = guarded({"pyproject.toml": PY + '[project]\nname = "x"\n'}, base_files={"pyproject.toml": PY})
check("unrelated tables are free", pl.get("decision") is None, pl)
r, pl = guarded({"pyproject.toml": PY.replace('"E", "F"', '"E"') + "# gate-allow: F rules are enforced by the CI job instead\n"}, base_files={"pyproject.toml": PY})
check("a gate-allow among the added lines of the config passes", pl.get("decision") is None and severities(r, "bypass/config") == ["log"], pl)
r, pl = guarded({"ruff.toml": "line-length = 120\n"}, base_files={"ruff.toml": "line-length = 100\n"})
check("ruff.toml: any change blocks", blocked(r, "bypass/config"), rules(r))
r, pl = guarded({".claude/project.env": 'CODE_EXTENSIONS="py"\nTEST_CMD="true"\n'}, env='CODE_EXTENSIONS="py"\nTEST_CMD="pytest"\n')
check("project.env: a changed TEST_CMD blocks", blocked(r, "bypass/config") and "TEST_CMD" in str(pl.get("reason")), pl)
r, pl = guarded({".claude/project.env": '# moved\nCODE_EXTENSIONS="py"   \nTEST_CMD=\'pytest\'\n'}, env='CODE_EXTENSIONS="py"\nTEST_CMD="pytest"\n')
check("project.env: compared by parsed value — a reformat does not fire", pl.get("decision") is None, pl)
r, pl = guarded({".claude/project.env": 'CODE_EXTENSIONS="py"\nTEST_CMD="pytest"\nGATE_MAX_BLOCKS="5"  # gate-allow: owner raised the retry limit\n'}, env='CODE_EXTENSIONS="py"\nTEST_CMD="pytest"\n')
check("project.env: a justified change passes", pl.get("decision") is None, pl)

print("bypass guard: the slice contract")
CONTRACT = "# Slice ctr\n\ngate-allow: type-ignore — the vendored stub has no types\n"


def with_contract(seal: str) -> tuple[Path, dict[str, object]]:
    r = new_repo()
    (r / ".engine/slices").mkdir(parents=True)
    c = r / ".engine/slices/ctr.md"
    c.write_text(CONTRACT)
    if seal != "none":
        (r / ".claude/state/contracts").mkdir(parents=True)
        digest = hashlib.sha256(CONTRACT.encode()).hexdigest()
        (r / ".claude/state/contracts/ctr.sha256").write_text(f"{digest}  .engine/slices/ctr.md\n")
        if seal == "stale":
            c.write_text(CONTRACT + "gate-allow: noqa — added after approval, grants itself\n")
    sh(r, "git", "add", "-A")
    sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c")
    (r / "mod.py").write_text(f"x = 1  {TI}\nimport os  {NQ}\n")
    _, pl = hook_stop(r)
    return r, pl


r, pl = with_contract("sealed")
check("a SEALED contract's gate-allow permits that kind", severities(r, "bypass/type-ignore") == ["log"], rules(r))
check("...and only that kind", blocked(r, "bypass/noqa") and pl.get("decision") == "block", rules(r))
r, pl = with_contract("none")
check("an UNSEALED contract grants nothing", blocked(r, "bypass/type-ignore"), rules(r))
r, pl = with_contract("stale")
check("a contract edited after its seal grants nothing, not even for its old lines", blocked(r, "bypass/type-ignore") and blocked(r, "bypass/noqa"), rules(r))

print("bypass guard: PROJECT_MARKER and CODE_EXTENSIONS pass on the sealed contract only (board 025)")
ENV_BASE = 'CODE_EXTENSIONS="py"\nPROJECT_MARKER=""\nLINT_CMD="false"\n'
SCOPE_CHANGES = {"PROJECT_MARKER": ENV_BASE.replace('PROJECT_MARKER=""', 'PROJECT_MARKER="absent.toml"'),
                 "CODE_EXTENSIONS": ENV_BASE.replace('CODE_EXTENSIONS="py"', 'CODE_EXTENSIONS="ts"')}


def scope_change(env_after: str, contract: str | None = None, seal: bool = True, layer: str = "stop") -> tuple[Path, dict[str, object]]:
    """A turn that edits mod.py and rewrites project.env; `contract` is committed before the turn."""
    r = new_repo(env_lines=ENV_BASE)
    if contract is not None:
        (r / ".engine/slices").mkdir(parents=True)
        (r / ".engine/slices/scope.md").write_text(contract)
        if seal:
            (r / ".claude/state/contracts").mkdir(parents=True)
            digest = hashlib.sha256(contract.encode()).hexdigest()
            (r / ".claude/state/contracts/scope.sha256").write_text(f"{digest}  .engine/slices/scope.md\n")
        sh(r, "git", "add", "-A")
        sh(r, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "contract")
    (r / "mod.py").write_text("x = 2\n")
    (r / ".claude/project.env").write_text(env_after)
    if layer == "stop":
        _, payload = hook_stop(r)
        return r, payload
    sh(r, "git", "add", "-A")
    p = gate(r, "--layer", layer)
    return r, {"rc": p.returncode, "stderr": p.stderr}


for key, after in SCOPE_CHANGES.items():
    r, pl = scope_change(after)
    check(f"a changed {key} blocks the Stop gate", pl.get("decision") == "block" and blocked(r, "bypass/config"), pl)
    check(f"...the reason names {key} and the contract line that would allow it",
          f"gate-allow: {key} —" in str(pl.get("reason")), pl)
    r, pl = scope_change(after, layer="pre_commit")
    check(f"pre_commit: a staged change of {key} blocks (exit 2)", pl["rc"] == 2 and blocked(r, "bypass/config"), pl)
    r, pl = scope_change(after + "# gate-allow: the project moved to another language\n")
    check(f"{key}: a gate-allow line in project.env itself does NOT pass", blocked(r, "bypass/config"), pl)
    r, pl = scope_change(after, contract="# Slice\n\ngate-allow: .claude/project.env — the settings are re-tuned here\n")
    check(f"{key}: a contract grant of the whole file does NOT pass — the key must be named", blocked(r, "bypass/config"), pl)
    granted = f"# Slice\n\ngate-allow: {key} — the project moves to another layout\n"
    r, pl = scope_change(after, contract=granted)
    check(f"{key}: the sealed contract naming the key lets the guard pass", severities(r, "bypass/config") == ["log"], rules(r))
    r, pl = scope_change(after, contract=granted, seal=False)
    check(f"{key}: an unsealed contract grants nothing", blocked(r, "bypass/config"), pl)
    other = next(k for k in SCOPE_CHANGES if k != key)
    r, pl = scope_change(after, contract=f"# Slice\n\ngate-allow: {other} — the project moves to another layout\n")
    check(f"{key}: a grant of {other} does not cover it", blocked(r, "bypass/config"), pl)
r, pl = scope_change(SCOPE_CHANGES["CODE_EXTENSIONS"], contract="# Slice\n\ngate-allow: CODE_EXTENSIONS — the project moves to TypeScript\n")
check("CODE_EXTENSIONS allowed by the contract: the turn ends (mod.py is no longer code)", pl.get("decision") is None, pl)
r, pl = scope_change(SCOPE_CHANGES["PROJECT_MARKER"], contract="# Slice\n\ngate-allow: PROJECT_MARKER — tooling arrives in the next slice\n")
check("PROJECT_MARKER allowed by the contract: the turn ends (checks wait for the marker)", pl.get("decision") is None and "marker" in rules(r), pl)
both = ENV_BASE.replace('PROJECT_MARKER=""', 'PROJECT_MARKER="absent.toml"').replace('LINT_CMD="false"', 'LINT_CMD="true"')
r, pl = scope_change(both, contract="# Slice\n\ngate-allow: PROJECT_MARKER — tooling arrives in the next slice\n")
check("a granted key does not carry an ungranted change of another gate key with it",
      blocked(r, "bypass/config") and "LINT_CMD" in str(pl.get("reason")) and "PROJECT_MARKER" not in str(pl.get("reason")).split("BYPASS GUARD", 1)[1].split(" — ", 1)[0], pl)
r, pl = scope_change(both + "# gate-allow: the lint command moved to the CI job\n", contract="# Slice\n\ngate-allow: PROJECT_MARKER — tooling arrives in the next slice\n")
check("...the other key still passes its own way (a reason among the added lines)", pl.get("decision") is None and severities(r, "bypass/config") == ["log", "log"], pl)
r, pl = scope_change('# moved\nPROJECT_MARKER=\'\'\nCODE_EXTENSIONS="py"  \nLINT_CMD="false"\n')
check("compared by parsed value: reordering and requoting the two keys is not a change", not any(x == "bypass/config" for x in rules(r)), rules(r))
r, pl = scope_change('CODE_EXTENSIONS="py"\nLINT_CMD="false"\n')
check("an empty key dropped from the file is not a change (unset and empty read the same)", not any(x == "bypass/config" for x in rules(r)), rules(r))

# ---------------------------------------------------------------- the separate gates share the format
print("contract_fingerprint and complexity_budget report in the same schema")
FP = ROOT / ".claude/hooks/contract_fingerprint.py"
r = new_repo()
(r / ".engine/slices").mkdir(parents=True)
(r / ".engine/slices/c1.md").write_text("# c\n")
fenv = dict(os.environ, CLAUDE_PROJECT_DIR=str(r))
subprocess.run([sys.executable, str(FP), "seal", str(r / ".engine/slices/c1.md")], env=fenv, capture_output=True, check=False)
subprocess.run([sys.executable, str(FP), "check", str(r / ".engine/slices/c1.md")], env=fenv, capture_output=True, check=False)
fp_ok = json.loads((r / ".claude/state/gate/contract_fingerprint-report.json").read_text())
check("a matching fingerprint is reported as a pass", fp_ok["result"] == "pass" and fp_ok["findings"][0]["severity"] == "log", fp_ok)
(r / ".engine/slices/c1.md").write_text("# c edited\n")
cp = subprocess.run([sys.executable, str(FP), "check", str(r / ".engine/slices/c1.md")], env=fenv, capture_output=True, text=True, check=False)
fp_bad = json.loads((r / ".claude/state/gate/contract_fingerprint-report.json").read_text())
check("a changed contract is a block finding with the shared fields and the unchanged exit status 3",
      cp.returncode == 3 and fp_bad["result"] == "block" and fp_bad["exit_code"] == 2
      and all(k in fp_bad["findings"][0] for k in ("file", "line", "rule", "severity", "message", "hint")), fp_bad)
check("last-report.json is gate.py's alone (no race between two Stop hooks)", not (r / ".claude/state/gate/last-report.json").exists())

# ---------------------------------------------------------------- robustness
print("robustness")
r = new_repo(commit=False)
(r / "mod.py").write_text(f"x = 1  {TI}\n")
sh(r, "git", "add", "-A")
_, pl = hook_stop(r)
check("a repository with no commit yet: the staged file is guarded, nothing crashes", blocked(r, "bypass/type-ignore"), pl)
r = new_repo()
(r / "mod.py").write_text("def (:\n")
_, pl = hook_stop(r)
check("a file that does not parse is skipped by the guard, not a crash", pl.get("decision") is None and "bypass/unparsed" in rules(r), pl)
r = new_repo()
(r / ".claude/project.env").unlink()
(r / "mod.py").write_text("x = 5\n")
_, pl = hook_stop(r)
check("no project.env at all: no crash, nothing to run", pl.get("decision") is None)
own = Path(__file__).read_text()
check("this file passes its own guard: the strings are never written whole", TI not in own and NQ not in own and SKIP not in own)

print()
print(f"PASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
