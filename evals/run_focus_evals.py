#!/usr/bin/env python3
"""Fifteen scenes that measure the FOCUS ON THE BUSINESS GOALS — the changes of boards 201, 202, 203 and 204 (boards 501–503).

    python3 evals/run_focus_evals.py [--out FILE] [--scenes e f g …] [--before m n o] [--twice h i …] [--max-usd 20] [--resume FILE]
    python3 evals/run_focus_evals.py --dry-run DIR                                                    # free: the sandboxes and the prompts

The project is an invented one, «Бігова група» (evals/scenarios/focus/README.md): it carries the
traps the engine v0.13.0 fell into in its first real project. BEFORE is the definitions of
`--before-ref` (v0.13.0) — or of the scene's own `before.ref` (p, q: v0.14.1, before board 204) —, AFTER
those of the working tree; a scene with no counterpart in v0.13.0 (e, j, k, k-neg) runs AFTER only.

    e      business-analyst, preseal     goals-v1 + the interview: the six findings of expected.json, and no G1–P1 contradiction
    f      business-analyst, consult     a request built around the non-goal N3: NOT_REQUIRED naming N3
    f-trap business-analyst, consult     a request the document is silent on: OWNER_DECISION
    g      master-critic, domain         the part «Безпека» has no source (N3 is a boundary): not PASS, and the judge agrees
    h      master-critic, domain         the owner writes the conclusions: not PASS, names G3 or G6, and the judge agrees
    i      master-critic, domain         the clean map: the judge finds no objection removing «Перевірка знеособлення»
                                         and none building a «Пропозиції» idea
    j      /master-architect, «Читання цілей»   the judge applies the seven-point rubric
    k      business-analyst, guardian M1 the owner writes the conclusions: a GUARDIAN_BLOCK names G3, G7 is named
    k-neg  business-analyst, guardian M1 the clean map: no GUARDIAN_BLOCK
    l      master-critic, decision       the premise «one instance, so no concurrent writes»: REVISE or POC_REQUIRED, and
                                         the judge agrees the objection is about that premise
    m      master-critic, decision       an «owner's decision» with no words of the owner in the interview: not PASS, and the
                                         judge agrees it is called an agent decision guarded out of proportion
    n      master-critic, decision       two writers in one file by the draft's own choice: not PASS, and the judge agrees
                                         the fix is one writer per file, not conditional writes
    o      master-critic, decision       a proof-of-concept with thresholds no goals line names: the judge finds an
                                         objection or a note that it must measure and report, the owner judges
    p      business-analyst, preseal     the re-check (`--changed` of recheck.changed) of goals-v3 + interview-v3: the
           re-check                      D1–N4 contradiction and G3 unmarked found, no consequence or late choice
                                         about G3, N4, P4; the judge agrees nothing re-opens answers 14–17
    q      business-analyst, preseal     goals-v2 + the interview: the judge finds no question about how something
                                         will work, and D1 put to the owner

The master-critic gets the interview journal in every scene, as /master-architect passes it (board 202) — where the
variant's /master-architect passes one: v0.13.0 did not, so its BEFORE gets none.

Where the output is structured (ANALYST_ANSWER, PRESEAL_FINDING, GUARDIAN_*, the critic's verdict) the
script checks it. Where a scene's goodness is what the text says, a fresh JUDGE session gets the
written rubric and answers «так» or «ні» with a quote for each point; the judge runs only when the
script's part already holds (a scene the script fails is not good whatever the text says).

Every AFTER run that is not good runs once more (attempt 2), to tell noise from a real miss, and the
scenes of --twice run twice whatever the first said; the report keeps both. --before narrows the
BEFORE runs to the scenes named (default: every scene that has one). A scene that fails is work on a definition, never a verdict on the role (board
051); nothing is tuned to the result.

EXTRA SESSIONS (board 078, 110). Each session — the judge's too — is booked to the task in hand; the
weekly cap stops the run before a session. With --out the file is written after every session, and
--resume FILE continues it: what is recorded is not run again.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
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
import run_analyst_evals as analyst
import run_simplifier_evals as shared

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURE = HERE / "scenarios" / "focus"
BEFORE_REF = "v0.13.0"
SCENES = ("e", "f", "f-trap", "g", "h", "i", "j", "k", "k-neg", "l", "m", "n", "o", "p", "q")
SHIPPED = (".claude/agents", ".claude/references", ".claude/commands", ".claude/constitution.md")
PRESEAL_RE = re.compile(r"^\W*PRESEAL_FINDING:\s*(.+)$", re.MULTILINE)
GUARDIAN_RE = re.compile(r"^\W*GUARDIAN_(BLOCK|NOTE|PASS)\b:?\s*(.*)$", re.MULTILINE)
JUDGE_RE = re.compile(r"^\W*(\d+)\W+(так|ні)\b\W*(.*)$", re.MULTILINE | re.IGNORECASE)
# where each input of expected.json goes in the sandbox (the critics get theirs in the prompt, as in real use)
PLACES = {"goals": ".engine/goals.md", "interview": ".engine/goals/interview.md", "request": ".engine/goals/requests/003.md",
          "artifact": ".engine/architecture/domain-map.md", "research": "docs/research/research-note.md"}
GUARDIAN = "guardian .engine/goals.md .engine/goals/interview.md .engine/architecture/traceability.md .engine/architecture/domain-map.md"
READING = ("You are the master-architect of this project. Below is your whole definition. The owner has asked you to begin the "
           "project's architecture; the goals document is `.engine/goals.md`, the researcher's note is in `docs/research/`.\n\n"
           "Carry out M1, step 1 — the stop «Читання цілей» — and nothing after it. In this session you cannot start agents "
           "(skip step 2, the guardian) and nobody can answer you: as your whole answer, write the left part of the "
           "traceability matrix (step 1) and then your message to the owner (step 3), exactly as the owner would get it.\n\n"
           "=== YOUR DEFINITION ===\n{definition}")
JUDGE = ("You are a judge of one answer, in a fresh context. You decide nothing about the project: you only check the "
         "answer against the rubric below, point by point, by what the answer actually says.\n\n=== THE INPUTS THE AUTHOR HAD ===\n"
         "{inputs}\n\n=== THE ANSWER UNDER JUDGEMENT ({who}) ===\n{answer}\n\n=== THE RUBRIC ===\n{rubric}\n\n"
         "For each point answer with exactly one line, and nothing else in your reply:\n"
         "<number>: так — «<a short verbatim quote from the answer that shows it>»\n"
         "<number>: ні — «<a short verbatim quote, or «нічого» when the answer is silent>» <one sentence why>")

JsonObj = dict[str, Any]


def fixture(name: str) -> str:
    return (FIXTURE / name).read_text(encoding="utf-8")


def variants(scene: str, expected: JsonObj) -> tuple[str, ...]:
    return ("after",) if expected[scene].get("before") is None else ("before", "after")


def plan(scenes: list[str], expected: JsonObj, before: list[str] | None = None) -> list[tuple[str, str]]:
    return [(scene, variant) for scene in scenes for variant in variants(scene, expected)
            if variant == "after" or before is None or scene in before]


def ref_of(scene: str, expected: JsonObj, default: str) -> str:
    """The BEFORE definitions of this scene: its own `before.ref` (board 503), else the run's `--before-ref`."""
    return (expected[scene].get("before") or {}).get("ref", default)


def inputs_of(scene: str, expected: JsonObj) -> JsonObj:
    """The scene's inputs; the master-critic's always carry the interview journal (board 502)."""
    exp = expected[scene]
    return dict(exp["inputs"]) | ({"interview": "interview.md"} if exp["agent"] == "master-critic" else {})


def passes_journal(variant: str, ref: str) -> bool:
    """Whether this variant's /master-architect hands the critic the journal — read from the definition, not assumed."""
    rel = ".claude/commands/master-architect.md"
    definition = (ROOT / rel).read_text(encoding="utf-8") if variant == "after" else analyst.at_ref(ref, rel)
    return "journal = .engine/goals/interview.md" in definition


# ------------------------------------------------------------------ sandboxes and prompts


def build_sandbox(target: Path, scene: str, variant: str, ref: str, expected: JsonObj) -> Path:
    """The definitions (the working tree's or `ref`'s) and the scene's inputs, each where real use puts it.
    The file names of the fixture never reach the sandbox: «domain-map-clean» would tell the reader."""
    target.mkdir(parents=True)
    if variant == "after":
        for rel in SHIPPED:
            source = ROOT / rel
            if source.is_dir():
                shutil.copytree(source, target / rel)
            else:
                shutil.copy2(source, target / rel)
    else:
        listed = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", ref, "--", *SHIPPED], capture_output=True, text=True, check=True)
        for rel in listed.stdout.splitlines():
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_text(analyst.at_ref(ref, rel), encoding="utf-8")
    exp = expected[scene]
    inputs = inputs_of(scene, expected)
    if "draft" in inputs and exp.get("mode") == "preseal":
        inputs["goals"] = inputs.pop("draft")  # /business-analyst writes the draft where the document will stand
    if "product_frame" in inputs:
        inputs["goals"] = inputs.pop("product_frame")
    for key, name in inputs.items():
        if key in PLACES:
            (target / PLACES[key]).parent.mkdir(parents=True, exist_ok=True)
            (target / PLACES[key]).write_text(fixture(name), encoding="utf-8")
    (target / ".gitignore").write_text(".claude/state/\n", encoding="utf-8")
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-q", "-m", "the project under review"]):
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)
    return target


def prompt(scene: str, variant: str, expected: JsonObj, ref: str) -> tuple[str, str | None]:
    """(the prompt, the agent to run it as or None for a plain session)."""
    exp = expected[scene]
    if exp["agent"] == "master-critic":
        inputs = inputs_of(scene, expected)
        journal = f"journal:\n{fixture(inputs['interview'])}\n\n" if passes_journal(variant, ref) else ""
        return (f"MASTER_CRITIC_REVIEW_REQUESTED\nphase: {exp['phase']}\n\nproduct_frame:\n{fixture(inputs['product_frame'])}\n\n"
                f"{journal}draft:\n{fixture(inputs['draft'])}"), "master-critic"
    if exp["agent"] == "master-architect":
        rel = ".claude/commands/master-architect.md"
        definition = (ROOT / rel).read_text(encoding="utf-8") if variant == "after" else analyst.at_ref(ref, rel)
        return READING.format(definition=definition), None
    mode = exp["mode"]
    if mode == "preseal":   # the re-check is the form board 204 gave preseal; BEFORE gets the same words
        changed = exp.get("recheck", {}).get("changed")
        return "preseal .engine/goals.md .engine/goals/interview.md" + (f" --changed {' '.join(changed)}" if changed else ""), "business-analyst"
    if mode == "guardian":
        return GUARDIAN, "business-analyst"
    return PLACES["request"], "business-analyst"  # consult: the bare path, the architects' form in both versions


# ------------------------------------------------------------------ scoring (free, deterministic)


def names(text: str, line: str) -> bool:
    return analyst.names_line(text, line)


def preseal_findings(answer: str) -> list[JsonObj]:
    found = []
    for raw in PRESEAL_RE.findall(answer):
        parts = [p.strip() for p in raw.split("|")]
        found.append({"kind": parts[0].strip("`*").lower(), "lines": parts[1] if len(parts) > 1 else "", "text": raw})
    return found


def flat(text: str) -> str:
    return " ".join(text.replace("’", "'").replace("ʼ", "'").lower().split())


def preseal_hit(finding: JsonObj, want: JsonObj) -> bool:
    if finding["kind"] != want["kind"]:
        return False
    if "lines" in want and not all(names(finding["text"], line) for line in want["lines"]):
        return False
    return "quote_contains" not in want or flat(want["quote_contains"]) in flat(finding["text"])


def finding_label(want: JsonObj) -> str:
    return want["kind"] + ("" if "lines" not in want else " " + "–".join(want["lines"]))


def score_preseal(answer: str, exp: JsonObj) -> JsonObj:
    findings = preseal_findings(answer)
    missed = [w for w in exp["must_find"] if not any(preseal_hit(f, w) for f in findings)]
    wrong = [w for w in exp["must_not_find"] if any(preseal_hit(f, w) for f in findings)]
    observed = (f"{len(findings)} findings; found {len(exp['must_find']) - len(missed)} of {len(exp['must_find'])}"
                + (f"; missed: {', '.join(finding_label(w) for w in missed)}" if missed else "")
                + (f"; must not find, found: {', '.join(finding_label(w) for w in wrong)}" if wrong else ""))
    return {"script_good": not missed and not wrong, "observed": observed}


def score_consult(answer: str, request: str, want: JsonObj, goals: Any) -> JsonObj:
    """The answer goes where the architect would paste it, and goals.py reads it as in real use."""
    result = goals.request_outcome("request", f"{request}\n## Відповідь аналітика\n{answer}\n", "")
    outcome = {"not-required": "NOT_REQUIRED", "owner": "OWNER_DECISION"}.get(result.outcome, result.outcome)
    if outcome.startswith("quote"):
        outcome = "QUOTE"
    good = outcome == want["answer"] and all(names(result.detail, line) for line in want.get("lines_include", []))
    return {"script_good": good, "observed": f"{outcome}{' — Lines: ' + result.detail if result.detail else ''}"}


def critic_verdict(answer: str) -> str:
    verdicts = analyst.VERDICT_RE.findall(answer)
    return verdicts[-1] if verdicts else ""


def score_critic(answer: str, want: JsonObj) -> JsonObj:
    verdict = critic_verdict(answer)
    good = bool(verdict)
    if "verdict_not" in want:
        good = good and verdict != want["verdict_not"]
    if "verdict_in" in want:
        good = good and verdict in want["verdict_in"]
    named = [line for line in want.get("objection_names_any", []) if names(answer, line)]
    if want.get("objection_names_any"):
        good = good and bool(named)
    return {"script_good": good, "observed": f"{verdict or 'no verdict'}" + (f"; names {', '.join(named) or 'none of ' + '/'.join(want['objection_names_any'])}" if want.get("objection_names_any") else "")}


def score_guardian(answer: str, want: JsonObj) -> JsonObj:
    said = GUARDIAN_RE.findall(answer)
    blocks = [rest for kind, rest in said if kind == "BLOCK"]
    if want.get("no_block"):
        return {"script_good": bool(said) and not blocks,
                "observed": f"{len(blocks)} BLOCK, {sum(1 for k, _ in said if k == 'NOTE')} NOTE" + ("" if said else "; no GUARDIAN_ line at all")}
    blocked = [line for line in want["block_names_any"] if any(names(b, line) for b in blocks)]
    mentioned = [line for line in want["mentions"] if any(names(rest, line) for _, rest in said)]
    good = bool(blocked) and len(mentioned) == len(want["mentions"])
    return {"script_good": good, "observed": f"{len(blocks)} BLOCK naming {', '.join(blocked) or 'none of ' + '/'.join(want['block_names_any'])}; "
                                             f"mentions {', '.join(mentioned) or 'none of ' + '/'.join(want['mentions'])}"}


def rubric(scene: str, expected: JsonObj) -> list[str]:
    """The judge's points: the scene's own list, or the one sentence of content the script cannot read."""
    want = expected[scene].get("after", {})
    if "judge" in want:
        return list(want["judge"])
    if "objection_or_note_about" in want:
        return [f"The critique carries an objection or a note to this effect: {want['objection_or_note_about']}."]
    if "objection_about" in want and expected[scene]["agent"] == "master-critic":
        return [f"An objection (or the POC_REQUIRED request) is about this: {want['objection_about']}."]
    return []


def score(scene: str, variant: str, answer: str, expected: JsonObj, goals: Any) -> JsonObj:
    exp = expected[scene]
    before = exp.get("before") or {}
    want = exp.get("after", {}) if variant == "after" or before.get("same_check") else before
    if exp["agent"] == "business-analyst" and exp["mode"] == "preseal":
        return score_preseal(answer, exp)
    if exp["agent"] == "business-analyst" and exp["mode"] == "consult":
        if "answer" not in want:   # f before: v0.13.0 had no NOT_REQUIRED; the same check, and the note says what to expect
            want = exp["after"]
        return score_consult(answer, fixture(exp["inputs"]["request"]), want, goals)
    if exp["agent"] == "business-analyst":
        return score_guardian(answer, want)
    if exp["agent"] == "master-critic":
        return score_critic(answer, want)
    return {"script_good": True, "observed": "judged only"}


def parse_judge(answer: str, points: int) -> JsonObj:
    said = {int(n): (verdict.lower(), rest.strip()) for n, verdict, rest in JUDGE_RE.findall(answer)}
    marks = [said.get(n, ("no answer", "")) for n in range(1, points + 1)]
    return {"judge_good": all(v == "так" for v, _ in marks), "judge": [{"point": n, "verdict": v, "quote": q} for n, (v, q) in enumerate(marks, 1)]}


def judge_prompt(scene: str, answer: str, expected: JsonObj) -> str:
    exp = expected[scene]
    inputs = "\n\n".join(f"--- {key}: {name} ---\n{fixture(name)}" for key, name in inputs_of(scene, expected).items())
    points = "\n".join(f"{n}. {text}" for n, text in enumerate(rubric(scene, expected), 1))
    who = exp["agent"] + (f", mode {exp['mode']}" if "mode" in exp else "") + (f", phase {exp['phase']}" if "phase" in exp else "") + (f", the step «{exp['step']}»" if "step" in exp else "")
    return JUDGE.format(inputs=inputs, who=who, answer=answer, rubric=points)


def summary(runs: list[JsonObj]) -> JsonObj:
    table: dict[str, list[Any]] = {}
    for r in runs:
        table.setdefault(f"{r['scene']}/{r['variant']}", []).append("error" if "error" in r else r.get("good"))
    firsts = [r for r in runs if r["variant"] == "after" and r.get("attempt", 1) == 1 and "error" not in r]
    return {"runs": len(runs), "after_good_first": sum(1 for r in firsts if r.get("good")), "after_total": len(firsts),
            "errors": sum(1 for r in runs if "error" in r), "cost_usd": round(sum(r.get("cost_usd", 0.0) + r.get("judge_cost_usd", 0.0) for r in runs), 4),
            "table": table}


# ------------------------------------------------------------------ the sessions


def judge(answer: str, scene: str, expected: JsonObj, args: argparse.Namespace, tmp: Path) -> JsonObj:
    capped = shared.week_cap(args.tasks_dir)
    if capped:   # the judge is a session too: the scene's row becomes an error, and --resume runs it again
        print(capped)
        return {"judge_error": capped, "judge_cost_usd": 0.0}
    room = tmp / f"judge-{scene}-{len(list(tmp.glob('judge-*')))}"
    room.mkdir()
    result = analyst.run_once(room, judge_prompt(scene, answer, expected), None, args)
    shared.book_session(args.tasks_dir, "run_focus_evals", result.get("cost_usd", 0.0))
    if "error" in result:
        return {"judge_error": result["error"], "judge_cost_usd": result["cost_usd"]}
    return parse_judge(result["answer"], len(rubric(scene, expected))) | {"judge_cost_usd": result["cost_usd"], "judge_answer": result["answer"]}


def one_run(scene: str, variant: str, attempt: int, expected: JsonObj, goals: Any, args: argparse.Namespace, tmp: Path) -> JsonObj:
    ref = ref_of(scene, expected, args.before_ref)
    sandbox = build_sandbox(tmp / f"{scene}-{variant}-{attempt}", scene, variant, ref, expected)
    text, agent = prompt(scene, variant, expected, ref)
    row: JsonObj = {"scene": scene, "variant": variant, "attempt": attempt, "agent": agent} | analyst.run_once(sandbox, text, agent, args)
    shared.book_session(args.tasks_dir, "run_focus_evals", row.get("cost_usd", 0.0))
    if "error" in row:
        return row
    row |= score(scene, variant, row["answer"], expected, goals)
    if row["script_good"] and rubric(scene, expected):
        row |= judge(row["answer"], scene, expected, args, tmp)
        if "judge_error" in row:
            return row | {"error": f"the judge gave no result: {row['judge_error']}"}
    row["good"] = row["script_good"] and row.get("judge_good", True)
    return row


def write(report: JsonObj, path: Path | None) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--out", type=environment.out_path, help="a recording goes to evals/baseline/@env/; written after every session")
    parser.add_argument("--resume", type=Path, help="a results file of this runner: what it holds without an error is not run again")
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    parser.add_argument("--no-repeat", action="store_true", help="do not run a failed AFTER scene a second time")
    parser.add_argument("--twice", nargs="+", choices=SCENES, default=[], help="these scenes' AFTER runs twice whatever the first said")
    parser.add_argument("--before", nargs="+", choices=SCENES, default=None, help="run BEFORE only for these scenes (default: every one that has it)")
    parser.add_argument("--before-ref", default=BEFORE_REF, help="the ref whose definitions are the BEFORE of a scene without its own before.ref")
    parser.add_argument("--dry-run", type=Path, help="build every sandbox here, write every prompt beside them and stop; free")
    parser.add_argument("--claude", default="claude", help="the Claude Code executable")
    parser.add_argument("--model", default="", help="override the session's model")
    parser.add_argument("--max-usd", type=float, default=None, help="a ceiling: stop before the runs together cost more (default: none)")
    parser.add_argument("--max-usd-per-run", type=float, default=2.0)
    parser.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    args = parser.parse_args()
    expected = json.loads(fixture("expected.json"))
    goals = analyst.goals_module()
    todo = plan(args.scenes, expected, args.before)

    if args.dry_run:
        for scene, variant in todo:
            ref = ref_of(scene, expected, args.before_ref)
            build_sandbox(args.dry_run / f"{scene}-{variant}", scene, variant, ref, expected)
            text, agent = prompt(scene, variant, expected, ref)
            (args.dry_run / f"prompt-{scene}-{variant}.txt").write_text(f"[agent: {agent or 'none'}]\n{text}\n", encoding="utf-8")
        print(f"{len(todo)} prompts and sandboxes in {args.dry_run}; nothing was run")
        return 0
    runs: list[JsonObj] = []
    if args.resume:
        runs = [r for r in json.loads(args.resume.read_text(encoding="utf-8"))["runs"] if "error" not in r]
    report: JsonObj = {
        "recorded_utc": "", "environment": environment.environment_name(),
        "engine_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
        "before_ref": args.before_ref, "limit_usd": args.max_usd, "planned": [f"{s}/{v}" for s, v in todo],
        "scenes": {name: {k: v for k, v in entry.items() if k != "inputs"} for name, entry in expected.items()}, "runs": runs,
    }
    stopped = False

    def go(scene: str, variant: str, attempt: int, tmp: Path) -> None:
        nonlocal stopped
        if stopped or any(r["scene"] == scene and r["variant"] == variant and r.get("attempt", 1) == attempt for r in runs):
            return
        spent = sum(r.get("cost_usd", 0.0) + r.get("judge_cost_usd", 0.0) for r in runs)
        stop = shared.over_limit(spent, args.max_usd_per_run, args.max_usd) or shared.week_cap(args.tasks_dir)
        if stop:
            print(stop)
            stopped = True
            return
        row = one_run(scene, variant, attempt, expected, goals, args, tmp)
        runs.append(row)
        shown = row.get("error") or f"{'good' if row['good'] else 'NOT good'} — {row['observed']}" + (
            "" if "judge" not in row else " · judge: " + " ".join(f"{j['point']}:{j['verdict']}" for j in row["judge"]))
        print(f"{scene} {variant} #{attempt}: {shown}  (${row.get('cost_usd', 0.0) + row.get('judge_cost_usd', 0.0):.2f})", flush=True)
        report.update(recorded_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), status=shared.status(runs, len(todo)), summary=summary(runs))
        write(report, args.out)

    with tempfile.TemporaryDirectory(prefix="engine-focus-eval-") as tmp:
        for scene, variant in todo:
            go(scene, variant, 1, Path(tmp))
        for scene, variant in todo:
            first = next((r for r in runs if r["scene"] == scene and r["variant"] == variant and r.get("attempt", 1) == 1), None)
            if variant != "after" or first is None or "error" in first:
                continue
            if scene in args.twice or (not args.no_repeat and not first["good"]):
                go(scene, variant, 2, Path(tmp))
    firsts = [r for r in runs if r.get("attempt", 1) == 1]
    report.update(recorded_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), status=shared.status(firsts, len(todo)), summary=summary(runs))
    print("\n" + json.dumps(report["summary"], indent=2, ensure_ascii=False))
    write(report, args.out)
    if args.out:
        print(f"results written to {args.out}")
    return 0 if len(firsts) == len(todo) and not any("error" in r for r in runs) else 1


if __name__ == "__main__":
    sys.exit(main())
