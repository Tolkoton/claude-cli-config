#!/usr/bin/env python3
"""gate.py — the one gate script. Four layers, one report, one place for the settings.

    python3 .claude/hooks/gate.py --layer post_write --files src/a.py
    python3 .claude/hooks/gate.py --layer stop                       # the files this turn changed
    python3 .claude/hooks/gate.py --layer pre_commit                 # the whole project, staged diff
    python3 .claude/hooks/gate.py --layer ci [--diff origin/main]    # the whole project
    ... --hook      speak Claude Code's hook protocol (stdin envelope, JSON on stdout)

Layers
    post_write  format one file, then a quick lint of it. NEVER blocks; what changed is shown to
                the model as additionalContext, and only when there is something to show.
    stop        quick, incremental: lint and types on the files the turn changed, tests that map
                to them. Reads `stop_hook_active` first. Counts consecutive blocks; on the Nth it
                lets the turn end and parks the item for a human (GATE_MAX_BLOCKS, default 3).
                Also refuses to be passed by silencing: see "bypass guard".
    pre_commit  the full set on the staged change (what a git pre-commit hook runs).
    ci          the full set (what a pipeline runs). No workflow file ships; see
                .claude/references/gate.md.

Exit code: 0 = no `block` finding, 2 = at least one. With --hook a Stop block is instead the
JSON {"decision":"block","reason":...} on stdout with exit 0 (the protocol every baseline pins);
the report's `exit_code` is always the CLI value.

Report: .claude/state/gate/last-report.json — file, line, rule, severity (block|warn|log),
message, hint per finding, plus timings per step. post_write writes it only when it has
something to say, so a clean edit does not overwrite the verdict of the last real gate. A
concise list of the most important findings goes to stderr.

Settings stay in .claude/project.env: CODE_EXTENSIONS, PROJECT_MARKER, LINT_CMD, TYPECHECK_CMD,
TEST_CMD, FORMAT_CMD, and the two optional keys TEST_CMD_FULL (pre_commit / ci only) and
GATE_MAX_BLOCKS.

BYPASS GUARD (stop, pre_commit). A block when the turn's diff ADDS a `# type: ignore`, a `# noqa`,
a pytest skip / skipif / xfail, or CHANGES the linter's or the type checker's configuration
(the parsed [tool.ruff] / [tool.mypy] of pyproject.toml, ruff.toml, mypy.ini, and the gate's own
keys in project.env) — unless the justification stands next to it:
    # gate-allow: <reason>           same line, or the comment-only line directly above
(any added line of a config file) or the slice contract (.engine/slices/*.md) says
    gate-allow: <type-ignore|noqa|skip|xfail|config path> — <reason>
A reason is at least 12 characters and two words. Syntax only: comments come from the tokenizer,
marks from the AST, configuration from the parsed tables — a string that merely mentions them
is not a finding.

Standard library only; Python 3.11+. The linters are external commands.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import tokenize
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tomllib

LAYERS = ("post_write", "stop", "pre_commit", "ci")
SEVERITIES = ("block", "warn", "log")
SCHEMA = 1
DEFAULT_MAX_BLOCKS = 3
STEP_TIMEOUT_S = 900
REPORT_REL = Path(".claude/state/gate/last-report.json")
COUNT_REL = Path(".claude/state/gate/stop-count.json")
PARKED_REL = Path(".engine/overseer/parked.md")
TAIL_LINES = {"lint": 30, "typecheck": 30, "tests": 40}
HEADINGS = {"lint": "LINT FAILED", "typecheck": "TYPECHECK FAILED", "tests": "TESTS FAILED"}
GATE_KEYS = ("LINT_CMD", "TYPECHECK_CMD", "TEST_CMD", "TEST_CMD_FULL", "FORMAT_CMD", "GATE_MAX_BLOCKS")
CONFIG_BASENAMES = ("ruff.toml", ".ruff.toml", "mypy.ini", ".mypy.ini")
SKIP_NAMES = {
    "pytest.mark.skip": "skip",
    "pytest.mark.skipif": "skip",
    "pytest.skip": "skip",
    "mark.skip": "skip",
    "mark.skipif": "skip",
    "pytest.mark.xfail": "xfail",
    "pytest.xfail": "xfail",
    "mark.xfail": "xfail",
}
SUPPRESSIONS = (
    ("type-ignore", re.compile(r"#\s*type:\s*ignore", re.IGNORECASE)),
    ("noqa", re.compile(r"#\s*(?:\w+:\s*)?noqa", re.IGNORECASE)),
)
ALLOW_RE = re.compile(r"gate-allow:\s*(?P<reason>.*\S)", re.IGNORECASE)
CONTRACT_ALLOW_RE = re.compile(
    r"^\s*gate-allow:\s*(?P<what>[\w./-]+)\s+[—–-]+\s+(?P<reason>\S.*)$", re.IGNORECASE | re.MULTILINE
)
DIAGNOSTIC_RE = re.compile(
    r"^(?P<file>[^\s:][^:\n]*\.py):(?P<line>\d+)(?::\d+)?:?\s+(?P<msg>.+)$", re.MULTILINE
)
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@", re.MULTILINE)


@dataclass
class Finding:
    file: str | None
    line: int | None
    rule: str
    severity: str
    message: str
    hint: str = ""


@dataclass
class Report:
    layer: str
    root: Path
    source: str = "gate"
    findings: list[Finding] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    steps_ms: dict[str, int] = field(default_factory=dict)
    started: float = field(default_factory=time.perf_counter)
    started_utc: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def blocked(self) -> bool:
        return any(f.severity == "block" for f in self.findings)

    @property
    def exit_code(self) -> int:
        return 2 if self.blocked else 0

    def as_json(self, result: str) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "source": self.source,
            "layer": self.layer,
            "started_utc": self.started_utc,
            "finished_utc": utc_now(),
            "result": result,
            "exit_code": self.exit_code,
            "files": self.files,
            "findings": [asdict(f) for f in self.findings],
            "timings_ms": {
                "total": int((time.perf_counter() - self.started) * 1000),
                "steps": self.steps_ms,
            },
            **self.extra,
        }


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ project, settings, git


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else Path.cwd()


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if not match:
            continue
        value = match.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        values[match.group(1)] = value
    return values


def load_env(root: Path) -> dict[str, str]:
    try:
        return parse_env_text((root / ".claude" / "project.env").read_text(encoding="utf-8"))
    except OSError:
        return {}


def code_extensions(env: dict[str, str]) -> list[str]:
    tokens = env.get("CODE_EXTENSIONS", "").replace(",", " ").split()
    return [t.lstrip(".").lower() for t in tokens if t.lstrip(".")]


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )


def has_head(root: Path) -> bool:
    return git(root, "rev-parse", "--verify", "-q", "HEAD").returncode == 0


def lines_of(proc: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in proc.stdout.splitlines() if ln.strip()] if proc.returncode == 0 else []


def changed_files(root: Path, layer: str, diff_ref: str | None) -> list[str]:
    """Files the turn changed: index and working tree against HEAD, plus untracked files."""
    names: set[str] = set()
    if layer == "pre_commit":
        names.update(lines_of(git(root, "diff", "--name-only", "--cached", "--diff-filter=ACMR")))
    elif diff_ref:
        names.update(lines_of(git(root, "diff", "--name-only", "--diff-filter=ACMR", diff_ref)))
    else:
        names.update(lines_of(git(root, "diff", "--name-only", "HEAD")))
        names.update(lines_of(git(root, "diff", "--name-only", "--cached")))
        names.update(lines_of(git(root, "ls-files", "--others", "--exclude-standard")))
    return sorted(n for n in names if (root / n).is_file())


def added_lines(root: Path, layer: str, rel: str, diff_ref: str | None) -> set[int] | None:
    """Line numbers this diff adds to `rel`; None means "every line" (a file with no base)."""
    if layer == "pre_commit":
        base = ["diff", "--cached", "-U0", "--no-color"]
    elif diff_ref:
        base = ["diff", diff_ref, "-U0", "--no-color"]
    elif has_head(root):
        base = ["diff", "HEAD", "-U0", "--no-color"]
    else:
        return None
    if layer != "pre_commit" and git(root, "ls-files", "--error-unmatch", "--", rel).returncode != 0:
        return None
    out = git(root, *base, "--", rel)
    if out.returncode != 0:
        return None
    new_in_head = layer != "pre_commit" and not diff_ref and has_head(root)
    if new_in_head and git(root, "cat-file", "-e", f"HEAD:{rel}").returncode != 0:
        return None
    added: set[int] = set()
    for hunk in HUNK_RE.finditer(out.stdout):
        start = int(hunk.group("start"))
        count = 1 if hunk.group("count") is None else int(hunk.group("count"))
        added.update(range(start, start + count))
    return added


def old_text(root: Path, layer: str, rel: str, diff_ref: str | None) -> str | None:
    ref = diff_ref or "HEAD"
    if layer == "pre_commit":
        ref = "HEAD"
    out = git(root, "show", f"{ref}:{rel}")
    return out.stdout if out.returncode == 0 else None


def new_text(root: Path, layer: str, rel: str) -> str | None:
    if layer == "pre_commit":
        out = git(root, "show", f":{rel}")
        return out.stdout if out.returncode == 0 else None
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


# ------------------------------------------------------------------ running commands


def run_shell(root: Path, command: str) -> tuple[int, str, int]:
    """Run `command` through bash with stderr merged into stdout (one stream, nothing clobbered)."""
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=STEP_TIMEOUT_S,
            check=False,
        )
        rc, out = proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        rc, out = 124, f"timed out after {STEP_TIMEOUT_S} s"
    return rc, out, int((time.perf_counter() - started) * 1000)


def tool_prefix(root: Path) -> str:
    if (root / "uv.lock").is_file() and shutil.which("uv"):
        return "uv run "
    if (root / "poetry.lock").is_file() and shutil.which("poetry"):
        return "poetry run "
    return ""


def pyproject_has(root: Path, table: str) -> bool:
    try:
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return False
    return re.search(rf"^\s*\[{re.escape(table)}[.\]]", text, re.MULTILINE) is not None


def quoted(files: list[str]) -> str:
    return " ".join(shlex.quote(f) for f in files)


def record_step(report: Report, kind: str, command: str, rc: int, out: str, ms: int) -> None:
    report.steps_ms[kind] = report.steps_ms.get(kind, 0) + ms
    if rc == 0:
        return
    tail = "\n".join(out.strip().splitlines()[-TAIL_LINES[kind]:])
    report.reasons.append(f"{HEADINGS[kind]} ({command}):\n{tail}")
    seen = 0
    for match in DIAGNOSTIC_RE.finditer(out):
        if seen >= 20:
            break
        seen += 1
        report.add(Finding(match["file"], int(match["line"]), kind, "block", match["msg"].strip(),
                           f"re-run: {command}"))
    if not seen:
        last = (out.strip().splitlines() or [f"exit {rc}"])[-1]
        report.add(Finding(None, None, kind, "block", f"{HEADINGS[kind]}: {last}",
                           f"re-run: {command}"))


# ------------------------------------------------------------------ bypass guard


def comment_map(text: str) -> dict[int, str] | None:
    comments: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                comments[tok.start[0]] = tok.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    return comments


def dotted(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def valid_reason(reason: str) -> bool:
    return len(reason) >= 12 and len(reason.split()) >= 2


def justified(line: int, comments: dict[int, str], source_lines: list[str]) -> bool:
    candidates = [comments.get(line)]
    if line >= 2 and source_lines[line - 2].lstrip().startswith("#"):
        candidates.append(comments.get(line - 1))
    for comment in candidates:
        match = ALLOW_RE.search(comment or "")
        if match and valid_reason(match["reason"].strip()):
            return True
    return False


def contract_allowances(root: Path) -> dict[str, str]:
    allowed: dict[str, str] = {}
    for contract in sorted((root / ".engine" / "slices").glob("*.md")):
        # Only a SEALED contract speaks: the fingerprint written at approval must match, so the
        # party the guard judges cannot grant itself an exemption by editing a slice file.
        seal = root / ".claude" / "state" / "contracts" / f"{contract.stem}.sha256"
        try:
            text = contract.read_text(encoding="utf-8")
            recorded = seal.read_text(encoding="utf-8").split()[0]
        except (OSError, IndexError):
            continue
        if recorded != hashlib.sha256(text.encode("utf-8")).hexdigest():
            continue
        for match in CONTRACT_ALLOW_RE.finditer(text):
            if valid_reason(match["reason"].strip()):
                allowed[match["what"].lower()] = contract.name
    return allowed


def guard_python(
    rel: str, text: str, added: set[int] | None, allowed: dict[str, str], report: Report
) -> None:
    comments = comment_map(text)
    if comments is None:
        report.add(Finding(rel, None, "bypass/unparsed", "log",
                           "not tokenizable, bypass guard skipped for this file"))
        return
    source_lines = text.splitlines()
    hits: list[tuple[str, int]] = []
    for line, comment in comments.items():
        if added is not None and line not in added:
            continue
        for kind, pattern in SUPPRESSIONS:
            if pattern.search(comment):
                hits.append((kind, line))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and dotted(node) in SKIP_NAMES:
                line = node.lineno
                if added is None or line in added:
                    hits.append((SKIP_NAMES[dotted(node)], line))
    for kind, line in sorted(hits, key=lambda h: h[1]):
        if kind in allowed or justified(line, comments, source_lines):
            report.add(Finding(rel, line, f"bypass/{kind}", "log", f"new {kind}, justified"))
            continue
        report.add(Finding(
            rel, line, f"bypass/{kind}", "block",
            f"the diff adds a {kind} — the gate is passed by silencing it, not by fixing the code",
            "fix the cause; or put `# gate-allow: <why, two words at least>` on this line or the "
            "comment line above; or the slice contract may carry "
            f"`gate-allow: {kind} — <reason>`",
        ))


def toml_tools(text: str | None) -> dict[str, Any] | None:
    if text is None:
        return {}
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    tool = data.get("tool", {})
    return {k: tool[k] for k in ("ruff", "mypy") if k in tool}


def config_justified(text: str | None, added: set[int] | None) -> bool:
    if text is None:
        return False
    for number, line in enumerate(text.splitlines(), start=1):
        if added is not None and number not in added:
            continue
        match = ALLOW_RE.search(line)
        if match and valid_reason(match["reason"].strip()):
            return True
    return False


def guard_config(
    root: Path, layer: str, rel: str, diff_ref: str | None, allowed: dict[str, str],
    added: set[int] | None, report: Report,
) -> None:
    old, new = old_text(root, layer, rel, diff_ref), new_text(root, layer, rel)
    base = Path(rel).name
    changed: str | None = None
    if base == "pyproject.toml":
        before, after = toml_tools(old), toml_tools(new)
        if before is not None and after is not None and before != after:
            changed = "the [tool.ruff] / [tool.mypy] settings"
    elif base in CONFIG_BASENAMES:
        if old != new:
            changed = "the linter / type-checker configuration"
    elif rel == ".claude/project.env":
        before_env = parse_env_text(old or "")
        after_env = parse_env_text(new or "")
        keys = [k for k in GATE_KEYS if before_env.get(k) != after_env.get(k)]
        if keys:
            changed = f"the gate's own settings ({', '.join(keys)})"
    if changed is None:
        return
    if rel.lower() in allowed or base.lower() in allowed or config_justified(new, added):
        report.add(Finding(rel, None, "bypass/config", "log", f"{changed} changed, justified"))
        return
    report.add(Finding(
        rel, None, "bypass/config", "block",
        f"the diff changes {changed} — a gate that can be re-tuned by the work it judges proves nothing",
        "if the change is meant: add a line `gate-allow: <why, two words at least>` among the "
        f"added lines of {rel}, or put `gate-allow: {rel} — <reason>` in the slice contract",
    ))


def bypass_guard(root: Path, layer: str, files: list[str], diff_ref: str | None, report: Report) -> None:
    allowed = contract_allowances(root)
    for rel in files:
        if not (rel.endswith(".py") or is_config_file(rel)):
            continue
        added = added_lines(root, layer, rel, diff_ref)
        if rel.endswith(".py"):
            text = new_text(root, layer, rel)
            if text is not None:
                guard_python(rel, text, added, allowed, report)
        else:
            guard_config(root, layer, rel, diff_ref, allowed, added, report)
    blocks = [f for f in report.findings if f.rule.startswith("bypass/") and f.severity == "block"]
    for f in blocks:
        where = f"{f.file}:{f.line}" if f.line else str(f.file)
        report.reasons.append(f"BYPASS GUARD {where} [{f.rule}] {f.message}. {f.hint}")


# ------------------------------------------------------------------ checks


def is_test_file(rel: str) -> bool:
    name = Path(rel).name
    return rel.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def test_targets(root: Path, files: list[str]) -> list[str]:
    targets: list[str] = []
    for rel in files:
        if not rel.endswith(".py"):
            continue
        if is_test_file(rel):
            candidates = [rel]
        else:
            stem = Path(rel).stem
            candidates = [f"{d}/test_{stem}.py" for d in ("tests", "test")]
        targets.extend(c for c in candidates if (root / c).is_file() and c not in targets)
    return targets


def run_checks(root: Path, env: dict[str, str], files: list[str], full: bool, report: Report) -> None:
    """lint, then types, then tests only if those passed — as the Stop hook always did."""
    configured = {k: env.get(k, "") for k in ("LINT_CMD", "TYPECHECK_CMD", "TEST_CMD")}
    if full and env.get("TEST_CMD_FULL"):
        configured["TEST_CMD"] = env["TEST_CMD_FULL"]
    prefix = tool_prefix(root)
    py_files = [f for f in files if f.endswith(".py")]
    steps: list[tuple[str, str]] = []
    if any(configured.values()):
        steps = [(k, c) for k, c in (("lint", configured["LINT_CMD"]),
                                     ("typecheck", configured["TYPECHECK_CMD"]),
                                     ("tests", configured["TEST_CMD"])) if c]
    else:
        exts = code_extensions(env)
        if exts and "py" not in exts:
            report.add(Finding(None, None, "no-checks", "log",
                               f"CODE_EXTENSIONS='{' '.join(exts)}' but no check commands are set in "
                               ".claude/project.env (LINT_CMD / TYPECHECK_CMD / TEST_CMD)",
                               "set them to enable verification for this language"))
            return
        if not py_files and not full:
            return
        scope = "." if full else quoted(py_files)
        if pyproject_has(root, "tool.ruff"):
            steps.append(("lint", f"{prefix}ruff check --force-exclude {scope}"))
        if pyproject_has(root, "tool.mypy"):
            steps.append(("typecheck", f"{prefix}mypy {scope}"))
        if (root / "tests").is_dir() or (root / "test").is_dir():
            if full:
                steps.append(("tests", f"{prefix}pytest -x --no-header -q"))
            else:
                targets = test_targets(root, files)
                if targets:
                    steps.append(("tests", f"{prefix}pytest -x --no-header -q {quoted(targets)}"))
                else:
                    report.add(Finding(None, None, "tests/unmapped", "log",
                                       "no test file maps to the changed files; tests not run"))
    failed = False
    for kind, command in steps:
        if kind == "tests" and failed:
            break
        rc, out, ms = run_shell(root, command)
        record_step(report, kind, command, rc, out, ms)
        failed = failed or rc != 0


# ------------------------------------------------------------------ report, counter, escalation


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_report(report: Report, result: str, name: str | None = None) -> Path:
    path = report.root / (REPORT_REL if name is None else REPORT_REL.with_name(name))
    try:
        write_json(path, report.as_json(result))
    except OSError as exc:
        print(f"gate: cannot write {path}: {exc}", file=sys.stderr)
    return path


def record_findings(root: Path, source: str, layer: str, findings: list[Finding],
                    result: str | None = None) -> Path:
    """For a gate that stays a separate script (complexity_budget, contract_fingerprint): write its
    verdict in this schema to .claude/state/gate/<source>-report.json. Its own file, not
    last-report.json — two Stop hooks run side by side and must not race on one path."""
    report = Report(layer=layer, root=root, source=source, started_utc=utc_now(), findings=findings)
    return write_report(report, result or ("block" if report.blocked else "pass"), f"{source}-report.json")


def read_count(root: Path, session: str) -> int:
    """Consecutive blocks of THIS session; another session's count is not ours."""
    try:
        data = json.loads((root / COUNT_REL).read_text(encoding="utf-8"))
        return int(data.get("sessions", {}).get(session, 0))
    except (OSError, ValueError, AttributeError):
        return 0


def write_count(root: Path, session: str, count: int) -> None:
    try:
        data = json.loads((root / COUNT_REL).read_text(encoding="utf-8"))
        sessions = dict(data.get("sessions", {}))
    except (OSError, ValueError, AttributeError):
        sessions = {}
    if count:
        sessions[session] = count
    else:
        sessions.pop(session, None)
    try:
        write_json(root / COUNT_REL, {"sessions": sessions, "updated_utc": utc_now()})
    except OSError:
        pass


def park_escalation(root: Path, report: Report, report_path: Path, blocks: int) -> None:
    top = "\n".join(f"  - {r.splitlines()[0]}" for r in report.reasons[:5])
    entry = (
        f"\n## {utc_now()} — gate stop layer — PARKED\n"
        f"- Blocked on: the Stop gate blocked {blocks} turns in a row and was not satisfied\n"
        "- Class: human-input\n"
        "- Reversibility: nothing was decided; the work is on disk and uncommitted\n"
        f"- Evidence: {report_path.relative_to(root) if report_path.is_relative_to(root) else report_path}\n"
        f"{top}\n"
        "- Unblocks when: a human reads the report and fixes or accepts the finding\n"
        "- Continued with: the turn was allowed to end\n"
    )
    path = root / PARKED_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(entry)
    except OSError as exc:
        print(f"gate: cannot park the escalation in {path}: {exc}", file=sys.stderr)


def lessons(root: Path, action: str, text: str = "") -> str:
    """Feed the lesson queue and the stuck counter (lesson_queue.py). Best effort: a problem here
    never changes what the gate decides. Returns the stuck protocol text when one is due."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import lesson_queue

        if action == "collect":
            lesson_queue.collect(root)
        elif action == "failure":
            return lesson_queue.note_failure(root, text)
        elif action == "success":
            lesson_queue.note_success(root)
    except (ImportError, OSError, ValueError):
        pass
    return ""


def summarise(report: Report, limit: int = 8) -> str:
    order = {s: i for i, s in enumerate(SEVERITIES)}
    top = sorted(report.findings, key=lambda f: order[f.severity])[:limit]
    lines = [f"gate[{report.layer}] {len(report.findings)} finding(s), exit {report.exit_code}"]
    for f in top:
        where = f"{f.file}:{f.line}" if f.line else (f.file or "-")
        lines.append(f"  {f.severity:5} {where} [{f.rule}] {f.message.splitlines()[0]}")
    return "\n".join(lines)


# ------------------------------------------------------------------ layers


def layer_post_write(root: Path, env: dict[str, str], rel: str, report: Report) -> str | None:
    """Format one file, lint it quickly, never block. Returns the additionalContext text."""
    path = root / rel if not Path(rel).is_absolute() else Path(rel)
    if not path.is_file():
        return None
    shown_rel = os.path.relpath(path, root)
    report.files = [shown_rel]
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter()
    own_formatter = format_file(root, env, path)
    report.steps_ms["format"] = int((time.perf_counter() - started) * 1000)
    changed = hashlib.sha256(path.read_bytes()).hexdigest() != before
    notes: list[str] = []
    if changed:
        notes.append(f"{shown_rel} was rewritten by the formatter; re-read it before your next edit.")
        report.add(Finding(rel, None, "format", "log", "rewritten by the formatter"))
    # A project that names its own formatter owns its tooling: no ruff lint on top of it.
    if path.suffix == ".py" and not own_formatter:
        command = f"{tool_prefix(root)}ruff check --force-exclude --output-format concise {shlex.quote(str(path))}"
        if tool_prefix(root) or shutil.which("ruff"):
            rc, out, ms = run_shell(root, command)
            report.steps_ms["lint"] = ms
            if rc == 1:
                for match in DIAGNOSTIC_RE.finditer(out):
                    shown = os.path.relpath(match["file"], root) if os.path.isabs(match["file"]) else match["file"]
                    report.add(Finding(shown, int(match["line"]), "lint", "warn", match["msg"].strip(),
                                       "fix it in the next edit"))
                    notes.append(f"lint {shown}:{match['line']} {match['msg'].strip()}")
    warns = [f for f in report.findings if f.severity == "warn"]
    if warns:
        stuck = lessons(root, "failure", f"{warns[0].rule} {warns[0].file} {warns[0].message}")
        if stuck:
            notes.append(stuck)
    else:
        lessons(root, "success")
    if not notes:
        return None
    return "gate: " + "\n".join(notes[:10])


def format_file(root: Path, env: dict[str, str], path: Path) -> bool:
    """Format `path`; True when the project's own FORMAT_CMD handled it."""
    ext = path.suffix.lstrip(".").lower() if path.suffix else ""
    configured_exts = code_extensions(env)
    fmt = env.get("FORMAT_CMD", "")

    def quiet_run(cmd: list[str]) -> None:
        subprocess.run(cmd, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    if fmt and ext and ext in configured_exts:
        quiet_run(["bash", "-c", fmt.replace("{file}", shlex.quote(str(path)), 1)])
        return True
    target = str(path)
    if ext == "py":
        prefix = tool_prefix(root).split()
        if prefix:
            runner = prefix + ["ruff"]
        elif shutil.which("ruff"):
            runner = ["ruff"]
        elif shutil.which("black"):
            quiet_run(["black", "--quiet", target])
            return False
        else:
            return False
        quiet_run([*runner, "format", "--force-exclude", target])
        quiet_run([*runner, "check", "--force-exclude", "--fix", "--select", "I", target])
    elif ext == "json" and shutil.which("jq"):
        proc = subprocess.run(["jq", ".", target], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            path.write_text(proc.stdout, encoding="utf-8")
    elif ext in ("md", "yml", "yaml", "toml") and shutil.which("prettier"):
        quiet_run(["prettier", "--write", "--log-level", "silent", target])
    return False


def eligible(env: dict[str, str], files: list[str]) -> list[str]:
    exts = code_extensions(env)
    if not exts:
        return files
    return [f for f in files if Path(f).suffix.lstrip(".").lower() in exts]


def is_config_file(rel: str) -> bool:
    return Path(rel).name in ("pyproject.toml", *CONFIG_BASENAMES) or rel == ".claude/project.env"


def layer_checks(root: Path, env: dict[str, str], layer: str, files: list[str],
                 diff_ref: str | None, report: Report) -> None:
    full = layer in ("pre_commit", "ci")
    report.files = files
    code = eligible(env, files)
    if layer == "stop":
        # A configuration file is not code, but changing the gate's own settings is exactly what
        # the guard exists to see; so a config-only turn still reaches the guard.
        if not code and not any(is_config_file(f) for f in files):
            return
        marker = env.get("PROJECT_MARKER", "")
        if marker and not (root / marker).exists():
            report.add(Finding(None, None, "marker", "log",
                               f"{marker} not found — verification skipped",
                               "add tooling, or clear PROJECT_MARKER in .claude/project.env"))
            return
    started = time.perf_counter()
    if layer in ("stop", "pre_commit"):
        bypass_guard(root, layer, files, diff_ref, report)
        report.steps_ms["bypass_guard"] = int((time.perf_counter() - started) * 1000)
    if layer != "stop" or code:
        run_checks(root, env, files, full, report)


def run_layer(layer: str, root: Path, files: list[str] | None, diff_ref: str | None) -> tuple[Report, str | None]:
    env = load_env(root)
    report = Report(layer=layer, root=root, started_utc=utc_now())
    if layer == "post_write":
        context = None
        for rel in files or []:
            context = layer_post_write(root, env, rel, report) or context
        return report, context
    selected = files if files else changed_files(root, layer, diff_ref)
    layer_checks(root, env, layer, selected, diff_ref, report)
    return report, None


def finish_stop(report: Report, root: Path, session: str) -> tuple[str, dict[str, Any]]:
    """Apply the counter: a block counts, a pass resets, the Nth block escalates."""
    limit = DEFAULT_MAX_BLOCKS
    raw = load_env(root).get("GATE_MAX_BLOCKS", "")
    if raw.isdigit() and int(raw) > 0:
        limit = int(raw)
    if not report.blocked:
        write_count(root, session, 0)
        report.extra["stop"] = {"consecutive_blocks": 0, "max": limit, "escalated": False}
        return "pass", {}
    count = read_count(root, session) + 1
    escalated = count >= limit
    report.extra["stop"] = {"consecutive_blocks": count, "max": limit, "escalated": escalated}
    if not escalated:
        write_count(root, session, count)
        return "block", {}
    write_count(root, session, 0)
    path = write_report(report, "escalated")
    park_escalation(root, report, path, count)
    message = (f"GATE ESCALATION: the Stop gate blocked {count} turns in a row. The turn may end; the "
               f"item is parked in {PARKED_REL} for a human. Report: {REPORT_REL}")
    return "escalated", {"systemMessage": message}


def read_envelope() -> dict[str, Any]:
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def emit_stop(report: Report, root: Path, hook: bool, session: str) -> int:
    result, extra = finish_stop(report, root, session)
    if result != "escalated":
        write_report(report, result)
    if report.blocked:
        stuck = lessons(root, "failure", next((f"{f.rule} {f.file} {f.message}" for f in report.findings
                                              if f.severity == "block"), ""))
        if stuck:
            report.reasons.append(stuck)
            if "systemMessage" in extra:
                extra["systemMessage"] += "\n" + stuck
    else:
        lessons(root, "success")
    lessons(root, "collect")
    if report.findings and any(f.severity != "log" for f in report.findings):
        print(summarise(report), file=sys.stderr)
    if result == "escalated":
        if hook:
            print(json.dumps(extra, ensure_ascii=False))
        else:
            print(extra["systemMessage"], file=sys.stderr)
        return 0
    if result == "block":
        reason = "\n\n".join(report.reasons) or "the gate blocked this turn"
        if hook:
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
            return 0
        print(reason, file=sys.stderr)
    return report.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--layer", required=True, choices=LAYERS)
    parser.add_argument("--files", nargs="*", default=None, help="files to check (default: the diff)")
    parser.add_argument("--diff", dest="diff_ref", default=None, help="diff base (default: HEAD)")
    parser.add_argument("--hook", action="store_true", help="speak Claude Code's hook protocol")
    args = parser.parse_args(argv)
    root = project_root()
    files: list[str] | None = args.files
    session = "cli"
    try:
        if args.hook:
            envelope = read_envelope()
            session = str(envelope.get("session_id") or "cli")
            # Read first. Claude Code sets the flag on the stop that follows a block, so a gate
            # that always exits on it can never count to N. The flag therefore ends the gate's
            # work only when the gate has not itself blocked this session (counter 0): a stop
            # forced by someone else's hook is not verified again, a re-entry after OUR block is.
            if (args.layer == "stop" and envelope.get("stop_hook_active") is True
                    and read_count(root, session) == 0):
                return 0
            if args.layer == "post_write":
                tool_input = envelope.get("tool_input")
                tool_input = tool_input if isinstance(tool_input, dict) else {}
                target = tool_input.get("file_path") or tool_input.get("path")
                files = [target] if isinstance(target, str) and target else []
        if args.layer == "post_write":
            report, context = run_layer("post_write", root, files, args.diff_ref)
            if report.findings:
                write_report(report, "info")
            if context and args.hook:
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PostToolUse", "additionalContext": context}}, ensure_ascii=False))
            elif context:
                print(context)
            return 0
        report, _ = run_layer(args.layer, root, files, args.diff_ref)
        if args.layer == "stop":
            return emit_stop(report, root, args.hook, session)
        result = "block" if report.blocked else "pass"
        write_report(report, result)
        if any(f.severity != "log" for f in report.findings):
            print(summarise(report), file=sys.stderr)
        return report.exit_code
    except Exception as exc:  # noqa: BLE001  # gate-allow: a crashed gate must not read as a passed gate
        if args.layer == "post_write":
            print(f"gate: post_write failed, nothing reported: {exc}", file=sys.stderr)
            return 0
        reason = f"gate.py crashed: {type(exc).__name__}: {exc}"
        if args.hook and args.layer == "stop":
            print(json.dumps({"decision": "block", "reason": reason}))
            return 0
        print(reason, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
