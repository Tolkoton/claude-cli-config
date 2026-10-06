#!/usr/bin/env python3
"""Four scenes that measure the QUALITY of the business analyst and of the goals lens (board 051).

    python3 evals/run_analyst_evals.py [--out FILE] [--scenes a b c d] [--max-usd 10]   # PAID: real sessions
    python3 evals/run_analyst_evals.py --dry-run DIR                                     # free: the sandboxes and the prompts

The project is a small one with an approved goals document (evals/scenarios/analyst/goals.md).
Each scene runs twice: BEFORE — the definitions as they were at `--before-ref` (no goals
document, no analyst, the product frame as one paragraph), and AFTER — the definitions of the
working tree with the sealed document.

    a  a violated non-goal       master-critic gets an ADR that quietly builds what N2 rules out.
                                 Good: the verdict is not PASS and the objection names N2.
    b  an inverted principle     feature-critic gets a plan that picks page speed where P1 ranks
                                 freshness first and calls the choice technical. Good: not PASS, names P1.
    c  a gap vs a technical      the feature-architect's definition meets a product gap and a purely
       question                  technical choice. Good: it sends the first up and decides the second.
    d  the document already      the agent `business-analyst` gets a request P1 settles. Good: a
       answers                   verbatim quote of P1 that `goals.py` accepts. Its trap (after only):
                                 a request the document is silent on must NOT get a quote.

A scene that fails is work on the analyst's definition or on the critics' lens — a quality
check, never a verdict on the role (the owner's answer 6, board 050): nothing here may be used
to remove the analyst. Nothing is tuned to the result; a failed scene is reported as it is.

PAID RUNS. Sessions start only when the task in tasks/doing/ has a «Платні прогони:» line with
a dollar limit, or the owner runs this by hand with --owner-approved (which does not count
inside a Claude Code session). The limit is the smaller of --max-usd and the number in that
line; the runs stop before it is passed.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # a suite may load this file by path
import environment
import run_simplifier_evals as paid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURE = HERE / "scenarios" / "analyst"
BEFORE_REF = "cebc005"  # the commit board 051 started from: no goals document, no analyst
SCENES = ("a", "b", "c", "d")
SHIPPED = (".claude/agents", ".claude/references", ".claude/constitution.md")
RUN_TIMEOUT_S = 900
LIMIT_RE = re.compile(r"^Платні прогони:.*?(\d+(?:[.,]\d+)?)\s*(?:долар|\$|USD)", re.MULTILINE | re.IGNORECASE)
VERDICT_RE = re.compile(r"^\W*((?:MASTER|FEATURE)_CRITIC_[A-Z_]+)", re.MULTILINE)
CHOICE_RE = re.compile(r"^\W*(D\d)\W+(ASK|DECIDE)\b", re.MULTILINE)
RECONCILIATION_RE = re.compile(r"^## Звірка з цілями\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
ARCHITECT = ("You are the feature-architect of this project. Below is your whole definition, then the product frame you were "
             "given, then the situation.\n\n=== YOUR DEFINITION ===\n{definition}\n\n=== THE PRODUCT FRAME ===\n{frame}\n\n=== THE SITUATION ===\n{situation}")
CACHE_QUESTION = ("You are in the middle of the feature `slot-picker` and one decision has come up that the feature frame did not "
                  "pre-answer:\n\nD1. The booking page shows the free hours of a day. Option (a): cache the list for 10 minutes — the "
                  "page opens faster, but an hour that was just taken may still be shown as free. Option (b): read the database on "
                  "every request — a little slower, always exact.\n\nApply your definition. Answer with exactly one line and nothing "
                  "else:\n\nD1: ASK — <a few words why>      (it must go up before you may decide: to the business analyst or to the "
                  "owner)\nD1: DECIDE — <a few words why>   (you decide it yourself and go on)")

JsonObj = dict[str, Any]


def goals_module() -> Any:
    spec = importlib.util.spec_from_file_location("goals", ROOT / ".claude" / "hooks" / "goals.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load .claude/hooks/goals.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["goals"] = module
    spec.loader.exec_module(module)
    return module


def fixture(name: str) -> str:
    return (FIXTURE / name).read_text(encoding="utf-8")


def at_ref(ref: str, rel: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{rel}"], capture_output=True, text=True, check=True).stdout


def dollar_limit(tasks_dir: Path, asked: float) -> float:
    """The smaller of what was asked and what the task in doing/ allows."""
    task = paid.task_in_hand(tasks_dir)
    found = LIMIT_RE.search(task.read_text(encoding="utf-8")) if task else None
    return min(asked, float(found.group(1).replace(",", "."))) if found else asked


# ------------------------------------------------------------------ sandboxes and prompts


def build_sandbox(target: Path, variant: str, ref: str) -> Path:
    """A project the definitions can be run in: AFTER has the sealed goals document and the two
    requests, BEFORE has the definitions of `ref` and neither."""
    target.mkdir(parents=True)
    if variant == "after":
        for rel in SHIPPED:
            source = ROOT / rel
            if source.is_dir():
                shutil.copytree(source, target / rel)
            else:
                shutil.copy2(source, target / rel)
        (target / ".claude/hooks").mkdir()
        shutil.copy2(ROOT / ".claude/hooks/goals.py", target / ".claude/hooks/goals.py")
        (target / ".engine/goals/requests").mkdir(parents=True)
        (target / ".engine/goals.md").write_text(fixture("goals.md"), encoding="utf-8")
        (target / ".engine/goals/requests/001.md").write_text(fixture("d-request.md"), encoding="utf-8")
        (target / ".engine/goals/requests/002.md").write_text(fixture("d-trap-request.md"), encoding="utf-8")
    else:
        listed = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", ref, "--", *SHIPPED], capture_output=True, text=True, check=True)
        for rel in listed.stdout.splitlines():
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_text(at_ref(ref, rel), encoding="utf-8")
    (target / ".engine/architecture").mkdir(parents=True, exist_ok=True)
    for name in ("domain-map.md", "architecture-map.md"):
        (target / ".engine/architecture" / name).write_text(fixture(name), encoding="utf-8")
    (target / ".gitignore").write_text(".claude/state/\n", encoding="utf-8")
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-q", "-m", "the project under review"]):
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)
    if variant == "after":
        # The fixture's owner approved this document: the seal is part of the scene, not an agent's act.
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
        subprocess.run([sys.executable, str(target / ".claude/hooks/goals.py"), "seal"], cwd=target, check=True, capture_output=True,
                       env={**env, "CLAUDE_PROJECT_DIR": str(target)})
    return target


def frame(variant: str) -> str:
    return fixture("goals.md") if variant == "after" else fixture("frame-before.md")


def draft(name: str, variant: str) -> str:
    """BEFORE had no «Звірка з цілями»: its numbers would cite a document that did not exist."""
    text = fixture(name)
    return text if variant == "after" else RECONCILIATION_RE.sub("", text).rstrip() + "\n"


def definition(variant: str, ref: str) -> str:
    rel = ".claude/commands/feature-architect.md"
    return (ROOT / rel).read_text(encoding="utf-8") if variant == "after" else at_ref(ref, rel)


def prompt(scene: str, variant: str, expected: JsonObj, ref: str) -> tuple[str, str | None]:
    """(the prompt, the agent to run it as or None for a plain session)."""
    if scene in ("a", "b"):
        exp = expected[scene]
        key = "product_frame" if scene == "a" else "feature_frame"
        extra = "" if scene == "a" else "slug: slot-picker\n"
        return (f"{exp['agent'].upper().replace('-', '_')}_REVIEW_REQUESTED\nphase: {exp['phase']}\n{extra}\n{key}:\n{frame(variant)}\n\n"
                f"draft:\n{draft(scene + '-draft.md', variant)}"), exp["agent"]
    if scene == "c":
        return ARCHITECT.format(definition=definition(variant, ref), frame=frame(variant), situation=fixture("c-decisions.md")), None
    if scene == "d" and variant == "before":
        return ARCHITECT.format(definition=definition(variant, ref), frame=frame(variant), situation=CACHE_QUESTION), None
    return f".engine/goals/requests/{'002' if scene == 'd-trap' else '001'}.md", "business-analyst"


# ------------------------------------------------------------------ scoring (free, deterministic)


def names_line(answer: str, line: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(line)}(?![\w-])", answer) is not None


def score_critic(answer: str, exp: JsonObj) -> JsonObj:
    verdicts = VERDICT_RE.findall(answer)
    verdict = verdicts[-1] if verdicts else ""
    named = names_line(answer, exp["line"])
    return {"good": bool(verdict) and verdict != exp["pass_verdict"] and named,
            "observed": f"{verdict or 'no verdict'}; {'names' if named else 'does not name'} {exp['line']}"}


def score_choices(answer: str, exp: JsonObj) -> JsonObj:
    said = dict(CHOICE_RE.findall(answer))
    wanted = {**{d: "ASK" for d in exp["ask"]}, **{d: "DECIDE" for d in exp["decide"]}}
    return {"good": said == wanted, "observed": ", ".join(f"{d}: {said.get(d, 'no answer')}" for d in sorted(wanted))}


def score_analyst(answer: str, request: str, document: str, exp: JsonObj, goals: Any) -> JsonObj:
    """The answer goes where the architect would paste it, and goals.py judges it as in real use."""
    result = goals.request_outcome("request", f"{request}\n## Відповідь аналітика\n{answer}\n", document)
    if "answer" in exp:  # the trap: the document is silent, a quote of any line is wrong
        return {"good": result.outcome == "owner", "observed": f"{result.outcome} {result.detail}".strip()}
    line = goals.field(answer[answer.rfind("ANALYST_ANSWER:"):], "Line", "Рядок") if "ANALYST_ANSWER:" in answer else ""
    return {"good": result.outcome == "quote-valid" and line == exp["line"], "observed": f"{result.outcome} {result.detail}".strip()}


def score(scene: str, variant: str, answer: str, expected: JsonObj, goals: Any) -> JsonObj:
    if scene in ("a", "b"):
        return score_critic(answer, expected[scene])
    if scene == "c":
        return score_choices(answer, expected["c"])
    if variant == "before":  # no analyst existed: what is recorded is whether the owner would have been asked
        said = dict(CHOICE_RE.findall(answer)).get("D1", "no answer")
        return {"good": None, "observed": {"ASK": "the question goes to the owner", "DECIDE": "the architect decides alone, with no line to cite"}.get(said, said)}
    name = "d-trap-request.md" if scene == "d-trap" else "d-request.md"
    return score_analyst(answer, fixture(name), fixture("goals.md"), expected[scene], goals)


def plan(scenes: list[str]) -> list[tuple[str, str]]:
    runs = [(scene, variant) for scene in scenes for variant in ("before", "after")]
    return runs + ([("d-trap", "after")] if "d" in scenes else [])


def summary(runs: list[JsonObj]) -> JsonObj:
    table = {f"{r['scene']}/{r['variant']}": ("error" if "error" in r else r["good"]) for r in runs}
    return {"runs": len(runs), "after_good": sum(1 for r in runs if r["variant"] == "after" and r.get("good") is True),
            "after_total": sum(1 for r in runs if r["variant"] == "after"), "cost_usd": round(sum(r["cost_usd"] for r in runs), 4), "table": table}


# ------------------------------------------------------------------ the paid part


def run_once(sandbox: Path, text: str, agent: str | None, args: argparse.Namespace) -> JsonObj:
    command = [args.claude, "-p", text, "--tools", "Read", "Grep", "Glob", "--output-format", "json", "--strict-mcp-config",
               "--max-budget-usd", str(args.max_usd_per_run)]
    command += ["--agent", agent] if agent else []
    command += ["--model", args.model] if args.model else []
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    try:
        proc = subprocess.run(command, cwd=sandbox, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, check=False,
                              env={**env, "CLAUDE_PROJECT_DIR": str(sandbox)}, stdin=subprocess.DEVNULL)
        payload = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"error": f"the session gave no result: {type(exc).__name__}", "cost_usd": 0.0}
    row: JsonObj = {"cost_usd": round(float(payload.get("total_cost_usd") or 0.0), 4),
                    "models": sorted((payload.get("modelUsage") or {}).keys()), "turns": payload.get("num_turns")}
    answer = str(payload.get("result") or "")
    if payload.get("is_error"):
        return row | {"error": f"the session ended in an error: {answer[:300]}"}
    return row | {"answer": answer}


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--out", type=environment.out_path, help="a recording goes to evals/baseline/@env/")
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    parser.add_argument("--before-ref", default=BEFORE_REF, help="the commit whose definitions are the BEFORE")
    parser.add_argument("--dry-run", type=Path, help="build both sandboxes here, write every prompt beside them and stop; free")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the session's model")
    parser.add_argument("--max-usd", type=float, default=10.0, help="stop before the runs together cost more")
    parser.add_argument("--max-usd-per-run", type=float, default=1.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    parser.add_argument("--owner-approved", action="store_true", help="the OWNER's word, for a run by hand outside a session")
    args = parser.parse_args()
    expected = json.loads(fixture("expected.json"))
    goals = goals_module()
    todo = plan(args.scenes)

    if args.dry_run:
        for variant in ("before", "after"):
            build_sandbox(args.dry_run / variant, variant, args.before_ref)
        for scene, variant in todo:
            text, agent = prompt(scene, variant, expected, args.before_ref)
            (args.dry_run / f"prompt-{scene}-{variant}.txt").write_text(f"[agent: {agent or 'none'}]\n{text}\n", encoding="utf-8")
        print(f"{len(todo)} prompts and two sandboxes in {args.dry_run}; nothing was run")
        return 0
    refusal = paid.paid_run_refusal(args.tasks_dir, args.owner_approved, bool(os.environ.get("CLAUDECODE")))
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    limit = dollar_limit(args.tasks_dir, args.max_usd)
    runs: list[JsonObj] = []
    with tempfile.TemporaryDirectory(prefix="engine-analyst-eval-") as tmp:
        sandboxes = {variant: build_sandbox(Path(tmp) / variant, variant, args.before_ref) for variant in ("before", "after")}
        for scene, variant in todo:
            spent = sum(r["cost_usd"] for r in runs)
            if spent + args.max_usd_per_run > limit:
                print(f"cost limit: ${spent:.2f} spent, a run may cost ${args.max_usd_per_run:.2f}, the limit is ${limit:.2f} — stopping")
                break
            text, agent = prompt(scene, variant, expected, args.before_ref)
            row = {"scene": scene, "variant": variant, "agent": agent} | run_once(sandboxes[variant], text, agent, args)
            if "error" not in row:
                row |= score(scene, variant, row["answer"], expected, goals)
            runs.append(row)
            shown = row.get("error") or f"{'good' if row['good'] else 'n/a' if row['good'] is None else 'NOT good'} — {row['observed']}"
            print(f"{scene} {variant}: {shown}  (${row['cost_usd']:.2f}, {', '.join(row.get('models', []))})")
    report: JsonObj = {
        "recorded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "environment": environment.environment_name(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "before_ref": args.before_ref, "limit_usd": limit, "planned": [f"{s}/{v}" for s, v in todo],
        "scenes": {name: entry["what"] for name, entry in expected.items()}, "summary": summary(runs), "runs": runs,
    }
    print("\n" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"results written to {args.out}")
    return 0 if len(runs) == len(todo) and not any("error" in r for r in runs) else 1


if __name__ == "__main__":
    sys.exit(main())
