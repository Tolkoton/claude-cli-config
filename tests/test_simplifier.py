#!/usr/bin/env python3
"""simplifier.py: the validator, the routing of findings, the reversal rate, the agent's definition.

The validator is what stands between the agent's judgement and the repository: every rule is
shown passing a legal finding and lowering or rejecting an illegal one.

Run:   python3 tests/test_simplifier.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPT = HOOKS / "simplifier.py"
sys.path.insert(0, str(HOOKS))
simplifier = importlib.import_module("simplifier")

PASS = FAIL = 0
FILES = {
    "src/demo/pricing.py": "def total(prices: list[int]) -> int:\n    return sum(prices)\n\n\ndef old_total() -> int:\n    return 0\n",
    "docs/goals.md": "# Goals\n\n- G1: sum prices\n",
    ".claude/constitution.md": "rules\n",
    "db/migrations/0001_init.py": "x = 1\n",
    "vendor/keep.py": "x = 1\n",
    ".claude/project.env": 'SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\nSIMPLIFIER_PROTECTED="vendor/**"\n',
    ".claude/state/simplifier/signals-full.json": json.dumps({"signals": [{"id": "S-11111111"}]}),
    ".gitignore": ".claude/state/\n",
}
GOOD: dict[str, Any] = {
    "target": "src/demo/pricing.py:5", "category": "dead_code", "claim": "old_total has no caller",
    "evidence": [{"source": "signal", "ref": "S-11111111", "detail": "vulture: unused function"},
                 {"source": "grep", "ref": "src/demo/pricing.py:5", "detail": "only the definition"}],
    "protected": False, "chesterton_checked": True, "test_safety": "characterization_exists",
    "proposed_action": "auto_remove", "traceability": "none found", "reversal_risk": "low",
}


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def new_repo() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="simplifier-"))
    for rel, text in FILES.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}, check=False)


def one(repo: Path, **changes: Any) -> dict[str, Any]:
    """Validate GOOD with `changes`; the finding, or {'errors': [...]} when it was rejected."""
    result = simplifier.validate(repo, [GOOD | changes], {"S-11111111"})
    if result["rejected"]:
        return {"errors": result["rejected"][0]["errors"]}
    found: dict[str, Any] = result["findings"][0]
    return found


repo = new_repo()
print("VALID-*   a legal finding passes untouched")
found = one(repo)
check("auto_remove with tool evidence, a checked fence and a test stays auto_remove",
      found.get("proposed_action") == "auto_remove" and found.get("validator") == [], found)
check("the finding gets a stable id", re.fullmatch(r"F-[0-9a-f]{8}", found.get("id", "")) is not None and one(repo)["id"] == found["id"], found)
for target in ("src/demo/pricing.py", "src/demo/pricing.py:5-6", "src/demo/pricing.py::old_total"):
    check(f"target form {target} is accepted", "errors" not in one(repo, target=target), one(repo, target=target))

print("REJECT-*  a finding that breaks the schema is rejected, with the reason")
without = {k: v for k, v in GOOD.items() if k != "traceability"}
rejected = simplifier.validate(repo, [without, GOOD | {"extra": 1}, "text"], set())["rejected"]
check("a missing field, an unknown field, a non-object", [r["errors"][0] for r in rejected]
      == ["missing field traceability", "unknown field extra", "not an object"], rejected)
for field, value in (("category", "ugly_code"), ("test_safety", "probably"), ("proposed_action", "delete_now"),
                     ("reversal_risk", "tiny"), ("protected", "no"), ("claim", " "), ("evidence", [])):
    check(f"{field}={value!r} is rejected", "errors" in one(repo, **{field: value}), one(repo, **{field: value}))
check("a target that is not a file of the repository is rejected", "errors" in one(repo, target="src/demo/gone.py:3"))
check("a target line past the end of the file is rejected", "errors" in one(repo, target="src/demo/pricing.py:400"))
check("evidence citing a signal that was not in the input is rejected",
      "S-99999999" in str(one(repo, evidence=[{"source": "signal", "ref": "S-99999999", "detail": "x"}]).get("errors")))
check("evidence citing a line that does not exist is rejected",
      "errors" in one(repo, evidence=[{"source": "read", "ref": "src/demo/pricing.py:999", "detail": "x"}]))
check("evidence with no source is rejected", "errors" in one(repo, evidence=[{"detail": "trust me"}]))

print("LOWER-*   a finding that claims more than it may is lowered, never raised")
found = one(repo, target=".claude/constitution.md")
check("a protected path: `protected` is set here and auto_remove becomes confirm",
      found.get("protected") is True and found.get("proposed_action") == "confirm" and len(found["validator"]) == 2, found)
check("a migration is protected", one(repo, target="db/migrations/0001_init.py").get("protected") is True)
check("SIMPLIFIER_PROTECTED adds the project's own zones", one(repo, target="vendor/keep.py").get("protected") is True)
check("the agent's own `protected: true` is honoured on any path", one(repo, protected=True).get("proposed_action") == "confirm")
for action in ("auto_remove", "confirm"):
    found = one(repo, test_safety="none", proposed_action=action)
    check(f"code with no test: {action} becomes flag_only", found.get("proposed_action") == "flag_only" and found["validator"], found)
found = one(repo, target="docs/goals.md:3", category="invented_requirement", test_safety="none", proposed_action="confirm")
check("a document with no test keeps confirm (the rule is about logic)", found.get("proposed_action") == "confirm", found)
check("an unchecked fence: auto_remove becomes confirm", one(repo, chesterton_checked=False).get("proposed_action") == "confirm")
check("a high reversal risk: auto_remove becomes confirm", one(repo, reversal_risk="high").get("proposed_action") == "confirm")
check("judgement alone: auto_remove becomes confirm",
      one(repo, evidence=[{"source": "judgement", "ref": "", "detail": "looks unused"}]).get("proposed_action") == "confirm")
check("nothing is ever raised: a protected flag_only stays flag_only",
      one(repo, proposed_action="flag_only", protected=True).get("proposed_action") == "flag_only")

print("CLI-*     the answer must be a JSON list, nothing else")
(repo / "answer.json").write_text(json.dumps([GOOD, GOOD | {"category": "ugly_code"}]))
done = cli(repo, "validate", "answer.json", "--out", "validated.json")
validated = json.loads((repo / "validated.json").read_text())
check("validate: exit 1 when something was rejected; both lists are written",
      done.returncode == 1 and len(validated["findings"]) == 1 and len(validated["rejected"]) == 1, done.stderr)
(repo / "fenced.txt").write_text("```json\n" + json.dumps([GOOD]) + "\n```\n")
check("one code fence around the list is forgiven", cli(repo, "validate", "fenced.txt").returncode == 0)
(repo / "prose.txt").write_text("Here are my findings:\n" + json.dumps([GOOD]))
done = cli(repo, "validate", "prose.txt")
check("prose around the list is INVALID", done.returncode == 2 and "INVALID" in done.stderr, done.stderr)
(repo / "object.json").write_text(json.dumps({"finding": GOOD}))
check("an object instead of a list is INVALID", cli(repo, "validate", "object.json").returncode == 2)
validated["findings"][0]["proposed_action"] = "auto_remove"
validated["findings"][0]["target"] = ".claude/constitution.md"
(repo / "validated.json").write_text(json.dumps(validated))
done = cli(repo, "route", "validated.json", "--title", "tampered")
check("a validated file edited by hand is validated again, not trusted", "0 auto_remove" in done.stdout, done.stdout + done.stderr)

print("ROUTE-*   confirm and flag_only go to the owner and the lesson queue; nothing is removed")
repo = new_repo()
(repo / "answer.json").write_text(json.dumps([
    GOOD, GOOD | {"claim": "worth a look", "proposed_action": "flag_only"},
    GOOD | {"target": "docs/goals.md:3", "category": "invented_requirement", "claim": "nobody asked", "proposed_action": "confirm"}]))
before = (repo / "src/demo/pricing.py").read_text()
done = cli(repo, "route", "answer.json", "--title", "first pass")
report = (repo / ".engine/simplifier/report.md").read_text()
check("the report lists the confirm and the flag_only finding with their evidence",
      "### confirm (1)" in report and "### flag_only (1)" in report and "docs/goals.md:3" in report and "vulture: unused function" in report, report)
check("the auto_remove finding is handed to the builder, not written for the owner",
      "1 auto_remove: F-" in done.stdout and "src/demo/pricing.py:5" in done.stdout and "old_total has no caller" not in report, done.stdout)
queue = (repo / ".engine/lesson-queue.md").read_text()
check("both owner findings are in the lesson queue, source simplifier",
      queue.count("| simplifier |") == 2 and "nobody asked" in queue, queue)
check("nothing was removed", (repo / "src/demo/pricing.py").read_text() == before)

print("RATE-*    the reversal rate: reverted, or the removed lines are back")


def removal(repo: Path, index: int) -> str:
    path = repo / "src" / "demo" / f"extra{index}.py"
    path.write_text(f"def extra_function_{index}() -> int:\n    return {index} * 1000\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"add {index}")
    path.unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"simplify: drop extra{index}\n\nSimplifier-Finding: F-{index:08d}")
    return git(repo, "rev-parse", "HEAD")


def rate(repo: Path, *args: str) -> str:
    return cli(repo, "reversals", *args).stdout


repo = new_repo()
shas = [removal(repo, i) for i in range(9)]
check("nine removals: too few to judge", "0 of the last 9" in rate(repo) and "too few removals" in rate(repo), rate(repo))
shas.append(removal(repo, 9))
check("ten removals, none back: 0 % — be bolder", "0 of the last 10" in rate(repo) and "be bolder" in rate(repo), rate(repo))
git(repo, "revert", "--no-edit", shas[2])
out = rate(repo)
check("one reverted with git revert: 10 % — inside the corridor",
      "1 of the last 10" in out and "inside the corridor" in out and "F-00000002" in out and "reverted" in out, out)
(repo / "src/demo/again.py").write_text("x = 1\n")
(repo / "src/demo/extra5.py").write_text("def extra_function_5() -> int:\n    return 5 * 1000\n")
git(repo, "add", "-A")
git(repo, "commit", "-q", "-m", "the function was needed after all")
out = rate(repo)
check("the same code written again counts as returned: 20 % — still inside",
      "2 of the last 10" in out and "inside the corridor" in out and "the removed lines are in the file again" in out, out)
(repo / "src/demo/extra7.py").write_text("y = 2\n")
git(repo, "add", "-A")
git(repo, "commit", "-q", "-m", "an unrelated file at the old path")
check("a different file at the old path does not count", "2 of the last 10" in rate(repo), rate(repo))
(repo / "note.txt").write_text("n\n")
git(repo, "add", "-A")
git(repo, "commit", "-q", "-m", "undo\n\nSimplifier-Reverts: F-00000008")
out = rate(repo, "--record")
check("a third one undone by trailer: 30 % — be more careful", "3 of the last 10" in out and "more careful" in out, out)
check("outside the corridor, --record leaves a note for the owner",
      "outside the corridor" in (repo / ".engine/simplifier/report.md").read_text())
check("--last narrows the window", "of the last 4 removals" in rate(repo, "--last", "4"), rate(repo, "--last", "4"))

print("AGENT-*   the definition matches what the validator enforces")
text = (ROOT / ".claude/agents/simplifier.md").read_text(encoding="utf-8")
front = text.split("---")[1]
check("model fable, tools Read, Grep and Glob only",
      re.search(r"^model: fable$", front, re.MULTILINE) is not None
      and re.search(r"^tools: Read, Grep, Glob$", front, re.MULTILINE) is not None, front)
for group in (simplifier.CATEGORIES, simplifier.TEST_SAFETY, simplifier.ACTIONS, simplifier.RISKS, simplifier.FIELDS,
              simplifier.EVIDENCE_SOURCES):
    missing = [word for word in group if f"`{word}`" not in text and f'"{word}"' not in text]
    check(f"the definition names every one of: {', '.join(group[:3])}…", not missing, missing)
example = json.loads(text.split("```json\n")[1].split("```")[0])
ROOT_TMP = new_repo()
example[0]["target"] = "src/demo/pricing.py:5"
example[0]["evidence"] = [e | ({"ref": "S-11111111"} if e["source"] == "signal" else {"ref": "src/demo/pricing.py:5"} if e["source"] == "grep" else {}) for e in example[0]["evidence"]]
check("the example in the definition is itself a valid answer",
      simplifier.validate(ROOT_TMP, example, {"S-11111111"})["rejected"] == [], simplifier.validate(ROOT_TMP, example, {"S-11111111"}))
check("the request for the agent carries the lens and the signals",
      "LENS: code" in cli(ROOT_TMP, "request", "--lens", "code").stdout and "DETERMINISTIC SIGNALS" in cli(ROOT_TMP, "request", "--lens", "code").stdout)

for leftover in Path(tempfile.gettempdir()).glob("simplifier-*"):
    shutil.rmtree(leftover, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
