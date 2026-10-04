#!/usr/bin/env python3
"""Run the deterministic hook scenarios against a sandbox and record the outcomes.

    python3 evals/run_hook_scenarios.py --engine-ref REF [--compare FILE] [options]
    python3 evals/run_hook_scenarios.py --sandbox DIR [--out FILE] [options]

With --engine-ref the script builds its own sandbox in a temporary directory and removes
it when done: one command, nothing left behind. --sandbox keeps working for a sandbox you
built yourself and want to look into afterwards.

A scenario feeds one hook the JSON envelope Claude Code would send it, inside a
sandbox built by `evals/make_sandbox.sh`, and records what the hook DECIDED:

    block           exit code 2, or {"decision":"block"}, or permissionDecision "deny"
    ask             permissionDecision "ask"
    allow-explicit  permissionDecision "allow" / PermissionRequest behavior "allow"
    allow           exit code 0 and no decision (the call goes ahead)
    malformed-json  stdout looks like JSON but does not parse — the harness cannot
                    read the decision, so a deny written this way is silently LOST
    absent          this engine version does not ship the hook
    error:<n>       any other exit code (Claude Code treats it as non-blocking)
    timeout         the hook did not finish in time

`expect` values in the scenario files describe the CURRENT engine. Run an older
ref with --record-only and diff the two result files with `evals/compare.py`:
the differences are exactly what changed between the versions.

THE MACHINE RECORD (board 035). A run of the whole shipped set against the sandbox's own hooks
— no --only, no --record-only, no --scenarios or --hooks-dir of your own — leaves
.claude/state/health/golden.json in this repository: the time (UTC), the commit, the ref the
sandbox was built from, how many scenarios ran and how many met their expectation, the baseline
compared against and how many differences. The owner's review reads its «Здоров'я» from there.
ENGINE_HEALTH_DIR names another directory.

Standard library only, Python 3.12+. Nothing here talks to a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # a suite may load this file by path
import environment

# Why 240 s: the slowest scenarios run ruff + mypy + pytest through `uv run` on a
# cold cache; that is ~20 s here and gets a 10x margin for slow disks and CI.
DEFAULT_TIMEOUT_S = 240
# Caches survive the per-scenario reset so mypy and ruff stay warm; they hold no
# project state a hook could read a decision from.
KEEP_ON_CLEAN = (".venv", ".mypy_cache", ".ruff_cache", ".pytest_cache")
DETAIL_CHARS = 200

JsonObj = dict[str, Any]


class SandboxError(Exception):
    """The sandbox is unusable; no scenario outcome would mean anything."""


def git(sandbox: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(sandbox), *args], capture_output=True, text=True, check=check
    )


def reset_sandbox(sandbox: Path) -> None:
    """Return the sandbox to its initial commit on `main`, keeping only caches."""
    try:
        git(sandbox, "switch", "-q", "-f", "main")
        git(sandbox, "reset", "-q", "--hard")
        # -ff: a scenario may have created a `git worktree` inside the sandbox; a single -f
        # refuses to delete a directory that contains its own .git.
        clean = ["clean", "-q", "-ffdx"]
        for keep in KEEP_ON_CLEAN:
            clean += ["-e", keep]
        git(sandbox, *clean)
        git(sandbox, "worktree", "prune")
        heads = git(sandbox, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout
        for branch in heads.split():
            if branch != "main":
                git(sandbox, "branch", "-q", "-D", branch)
    except subprocess.CalledProcessError as exc:
        raise SandboxError(f"cannot reset sandbox: {exc.stderr.strip() or exc}") from exc


def substitute(value: Any, mapping: dict[str, str]) -> Any:
    """Replace {{PLACEHOLDER}} tokens in every string of a JSON-like value."""
    if isinstance(value, str):
        for token, replacement in mapping.items():
            value = value.replace("{{" + token + "}}", replacement)
        return value
    if isinstance(value, list):
        return [substitute(v, mapping) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, mapping) for k, v in value.items()}
    return value


def apply_setup(sandbox: Path, steps: list[JsonObj]) -> None:
    """Declarative setup only — no arbitrary shell, so a scenario file cannot do
    anything outside the sandbox."""
    for step in steps:
        if "write" in step:
            target = (sandbox / step["write"]["path"]).resolve()
            if sandbox.resolve() not in target.parents:
                raise SandboxError(f"setup writes outside the sandbox: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(step["write"]["content"], encoding="utf-8")
        elif "remove" in step:
            (sandbox / step["remove"]).unlink(missing_ok=True)
        elif "git" in step:
            result = git(sandbox, *step["git"], check=False)
            if result.returncode != 0:
                raise SandboxError(f"setup git {step['git']} failed: {result.stderr.strip()}")
        else:
            raise SandboxError(f"unknown setup step: {step}")


def file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def classify(returncode: int, stdout: str) -> tuple[str, str]:
    """Map a hook's exit code and stdout to (outcome, reason-text)."""
    if returncode == 2:
        return "block", ""
    if returncode != 0:
        return f"error:{returncode}", ""
    text = stdout.strip()
    if not text.startswith("{"):
        return "allow", ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "malformed-json", text
    if not isinstance(payload, dict):
        return "allow", ""
    if payload.get("decision") == "block":
        return "block", str(payload.get("reason", ""))
    specific = payload.get("hookSpecificOutput")
    if isinstance(specific, dict):
        reason = str(specific.get("permissionDecisionReason", ""))
        decision = specific.get("permissionDecision")
        if decision is None and isinstance(specific.get("decision"), dict):
            decision = specific["decision"].get("behavior")
        if decision == "deny":
            return "block", reason
        if decision == "ask":
            return "ask", reason
        if decision == "allow":
            return "allow-explicit", reason
    return "allow", ""


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def run_scenario(
    sandbox: Path,
    hooks_dir: Path,
    hook: str,
    scenario: JsonObj,
    timeout_s: int,
    foreign_hooks: bool = False,
) -> JsonObj:
    result: JsonObj = {"id": scenario["id"], "hook": hook, "expect": scenario.get("expect")}
    if "expect_detail_contains" in scenario:
        result["expect_detail_contains"] = scenario["expect_detail_contains"]
    hook_path = hooks_dir / hook
    if not hook_path.is_file():
        result.update(outcomes=["absent"], detail="hook not shipped by this engine version")
        return result

    reset_sandbox(sandbox)
    workdir = Path(tempfile.mkdtemp(prefix="hook-scenario-"))
    try:
        transcript = workdir / "transcript.jsonl"
        head = git(sandbox, "rev-parse", "HEAD").stdout.strip()
        mapping = {"SANDBOX": str(sandbox), "TRANSCRIPT": str(transcript), "HEAD": head}
        if "transcript" in scenario:
            records = substitute(scenario["transcript"], mapping)
            transcript.write_text(
                "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
            )
        apply_setup(sandbox, substitute(scenario.get("setup", []), mapping))

        watched = sandbox / scenario["check_file"] if "check_file" in scenario else None
        before = file_digest(watched) if watched else None

        # `project_dir`: run the hook as if Claude Code had been started in a subdirectory
        # of the sandbox — used for `git worktree` checkouts, where .git is a file.
        project_dir = (sandbox / scenario.get("project_dir", ".")).resolve()
        if project_dir != sandbox.resolve() and sandbox.resolve() not in project_dir.parents:
            raise SandboxError(f"project_dir escapes the sandbox: {project_dir}")
        # A session started in a subdirectory runs THAT checkout's copy of the hook, as Claude
        # Code would (`$CLAUDE_PROJECT_DIR/.claude/hooks/<hook>`) — unless --hooks-dir names the
        # directory to measure explicitly.
        if not foreign_hooks and project_dir != sandbox.resolve():
            own = project_dir / ".claude" / "hooks" / hook
            if own.is_file():
                hook_path = own
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        env.pop("CLAUDE_UNATTENDED_SESSION", None)
        env.update(substitute(scenario.get("env", {}), mapping))
        interpreter = [sys.executable] if hook.endswith(".py") else ["bash"]
        envelope = json.dumps(substitute(scenario.get("input", {}), mapping))

        outcomes: list[str] = []
        detail = ""
        for _ in range(int(scenario.get("runs", 1))):
            try:
                proc = subprocess.run(
                    [*interpreter, str(hook_path), *scenario.get("_hook_args", [])],
                    input=envelope, capture_output=True, text=True,
                    cwd=project_dir, env=env, timeout=timeout_s, check=False,
                )
            except subprocess.TimeoutExpired:
                outcomes.append("timeout")
                continue
            outcome, reason = classify(proc.returncode, proc.stdout)
            outcomes.append(outcome)
            detail = first_line(reason) or first_line(proc.stderr) or first_line(proc.stdout)
            # A reason of several paragraphs (the audit request plus what a hook appends to it):
            # `detail_line` names the line the scenario is about, by a phrase it contains.
            anchor = scenario.get("detail_line")
            if anchor:
                detail = next((ln.strip() for ln in reason.splitlines() if anchor in ln), detail)

        for real, shown in ((str(sandbox), "<SANDBOX>"), (str(workdir), "<TMP>")):
            detail = detail.replace(real, shown)
        result.update(outcomes=outcomes, detail=detail[:DETAIL_CHARS])
        if watched:
            result["file_changed"] = file_digest(watched) != before
            result["expect_file_changed"] = scenario.get("expect_file_changed")
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def meets_expectation(result: JsonObj) -> bool | None:
    """True/False against the scenario's expectation; None when it states none."""
    checks: list[bool] = []
    expect = result.get("expect")
    if isinstance(expect, str):
        checks.append(result["outcomes"][-1] == expect)
    elif isinstance(expect, list):
        checks.append(result["outcomes"] == expect)
    if result.get("expect_file_changed") is not None:
        checks.append(result.get("file_changed") == result["expect_file_changed"])
    if result.get("expect_detail_contains"):
        # A block for the WRONG reason is not a pass: the gate has to object to the
        # defect the scenario planted, not to something unrelated that came first.
        checks.append(result["expect_detail_contains"] in result.get("detail", ""))
    return all(checks) if checks else None


def tool_version(*cmd: str) -> str:
    if shutil.which(cmd[0]) is None:
        return "not found"
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "error"
    return first_line(out.stdout or out.stderr)


def record_health(repo: Path, engine_ref: str, results: list[JsonObj], compare: Path | None, differences: int | None) -> None:
    """The machine record of a whole run of the golden set (see the head of this file)."""
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False).stdout.strip()

    record = {"what": "evals/run_hook_scenarios.py", "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")), "engine_ref": engine_ref,
              "scenarios": len(results), "green": sum(1 for r in results if r.get("pass")),
              "red": [str(r.get("id")) for r in results if r.get("pass") is False],
              "compare": compare.name if compare else "", "differences": differences}
    folder = Path(os.environ.get("ENGINE_HEALTH_DIR") or repo / ".claude/state/health")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        scratch = folder / "golden.json.tmp"
        scratch.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        scratch.replace(folder / "golden.json")
    except OSError as exc:
        print(f"the machine record was not written: {exc}", file=sys.stderr)


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sandbox", type=Path, help="an existing sandbox (kept afterwards)")
    parser.add_argument("--engine-ref", help="build a temporary sandbox from this tag, branch "
                                             "or commit, and delete it afterwards")
    parser.add_argument("--compare", type=environment.baseline_path,
                        help="diff the outcome against this results file (evals/compare.py); "
                             "@env in the path is this environment's folder")
    parser.add_argument("--hooks-dir", type=Path, help="default: <sandbox>/.claude/hooks")
    parser.add_argument("--scenarios", type=Path, default=here / "scenarios" / "hooks")
    parser.add_argument("--out", type=environment.out_path,
                        help="write machine-readable results here; a baseline goes to "
                             "evals/baseline/@env/ (@env = this environment, evals/environment.py)")
    parser.add_argument("--label", default="", help="free text stored with the results")
    parser.add_argument("--only", default="", help="run scenarios whose id contains this")
    parser.add_argument("--record-only", action="store_true",
                        help="record outcomes, do not fail on expectation mismatches")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args()
    if bool(args.sandbox) == bool(args.engine_ref):
        parser.error("give exactly one of --sandbox and --engine-ref")

    temp_root: Path | None = None
    if args.engine_ref:
        temp_root = Path(tempfile.mkdtemp(prefix="engine-hooks-"))
        args.sandbox = temp_root / "sandbox"
        build = subprocess.run(["bash", str(here / "make_sandbox.sh"), args.engine_ref,
                                str(args.sandbox)], capture_output=True, text=True, check=False)
        if build.returncode != 0:
            shutil.rmtree(temp_root, ignore_errors=True)
            print(build.stderr.strip() or "make_sandbox.sh failed", file=sys.stderr)
            return 2
    try:
        return run_all(args, here)
    finally:
        if temp_root:
            shutil.rmtree(temp_root, ignore_errors=True)


def run_all(args: argparse.Namespace, here: Path) -> int:
    # Only a run of the whole shipped set against the sandbox's own hooks is a fact about the engine.
    whole_set = not (args.only or args.record_only or args.hooks_dir) and args.scenarios == here / "scenarios" / "hooks"
    sandbox = args.sandbox.resolve()
    info_file = sandbox / "SANDBOX-INFO.json"
    if not info_file.is_file():
        print(f"{sandbox} is not a sandbox (no SANDBOX-INFO.json). "
              "Build one with evals/make_sandbox.sh — never point this at a real project.",
              file=sys.stderr)
        return 2
    hooks_dir = (args.hooks_dir or sandbox / ".claude" / "hooks").expanduser().resolve()
    scenario_files = sorted(args.scenarios.glob("*.json"))
    if not scenario_files:
        print(f"no scenario files in {args.scenarios}", file=sys.stderr)
        return 2

    results: list[JsonObj] = []
    failed = 0
    try:
        for file in scenario_files:
            group = json.loads(file.read_text(encoding="utf-8"))
            for scenario in group["scenarios"]:
                if args.only and args.only not in scenario["id"]:
                    continue
                scenario["_hook_args"] = group.get("args", [])
                result = run_scenario(
                    sandbox, hooks_dir, group["hook"], scenario, args.timeout, foreign_hooks=bool(args.hooks_dir)
                )
                verdict = meets_expectation(result)
                result["pass"] = verdict
                results.append(result)
                shown = " -> ".join(result["outcomes"])
                if "file_changed" in result:
                    shown += f" (file changed: {str(result['file_changed']).lower()})"
                if verdict is False and not args.record_only:
                    failed += 1
                    want = result["expect"]
                    if result.get("expect_detail_contains"):
                        want = f"{want} because '{result['expect_detail_contains']}'"
                        shown += f" [{result.get('detail', '')[:60]}]"
                    if result.get("expect_file_changed") is not None:
                        want = f"{want}, file changed: {str(result['expect_file_changed']).lower()}"
                    print(f"  FAIL {result['id']:42} {shown}   (expected {want})")
                else:
                    print(f"  ok   {result['id']:42} {shown}")
        reset_sandbox(sandbox)
    except SandboxError as exc:
        print(f"sandbox error: {exc}", file=sys.stderr)
        return 2

    out_file = args.out
    if args.compare and not out_file:
        out_file = Path(tempfile.mkdtemp(prefix="engine-hooks-out-")) / "results.json"
    if out_file:
        report = {
            "label": args.label,
            "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sandbox": json.loads(info_file.read_text(encoding="utf-8")),
            "hooks_dir": str(hooks_dir).replace(str(sandbox), "<SANDBOX>"),
            "environment": {
                "name": environment.environment_name(),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "bash": tool_version("bash", "--version"),
                "jq": tool_version("jq", "--version"),
                "uv": tool_version("uv", "--version"),
                "git": tool_version("git", "--version"),
            },
            "results": results,
        }
        out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        if args.out:
            print(f"\nresults written to {args.out}")

    total = len(results)
    differences: int | None = None
    if args.compare and out_file:
        print()
        diff = subprocess.run([sys.executable, str(here / "compare.py"), str(args.compare),
                               str(out_file)], capture_output=True, text=True, check=False)
        print(diff.stdout.rstrip())
        if not args.out:
            shutil.rmtree(out_file.parent, ignore_errors=True)
        if diff.returncode == 2:
            return 2
        failed += diff.returncode            # differences count as a failed check
        differences = diff.returncode
    if whole_set:
        record_health(here.parent, args.engine_ref or "", results, args.compare, differences)
    if args.record_only:
        print(f"\nRECORDED {total} scenarios (expectations not enforced)")
        return 0
    if failed:
        print(f"\nFAIL ({failed}) of {total}")
        return 1
    print(f"\nPASS {total}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
