#!/usr/bin/env python3
"""The testing manager and the slice tester (board 062): testing.py, and what overseer_stop.py does with it.

Every rule is shown refusing first, then letting the allowed thing through:
  * `validate` refuses a decision that contradicts each of O1–O8 (O8 both ways: the coarse
    check and COVERAGE_CMD) and allows the decision the case demands;
  * `record` refuses a hand-in whose contract test PASSES against the skeleton, an invented
    contract line, a disputed test mixed into a file with undisputed ones; a disputed file is
    not sealed before its question is answered; `keeps` must be green;
  * a changed sealed test file blocks (`check`, `gate`), an unchanged one passes;
  * `guard` refuses both agents with an arbitrary prompt and with no request pending;
  * the manager refused twice: the script writes the mandatory decision itself;
  * two rounds of dispute, the third parks the slice; the next slice does not start and a
    feature does not close without point (b); a due debt cannot be deferred again;
  * overseer_stop.py makes no audit request without the decision of point (a).

Run:   python3 tests/test_testing.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPT = HOOKS / "testing.py"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import testing  # noqa: E402  # gate-allow: the module lives beside the hooks, not on the path
from hook_env import hook_env  # noqa: E402

PASS = FAIL = 0
CONTRACT = """# Slice discount — planning artifact

## Goal
A discount on a price.

## Seam (contract)
- Signature: `apply_discount(price: int, percent: int) -> int` in `src/pricing.py`
- Returns: the price after the discount, in cents
- Errors: a discount over 50 percent is refused with ValueError
- Dependencies (injected): none

## Hardest seams (test-confidence points — distinct from the contract Seam above)
{seams}

## Exit criterion
{exit}

## Deferred to later slices
- none
"""
SEAM = "- **Seam 1: the boundary** — test approach: exactly 50 and 51, by hand"
FEATURE = """# Feature shop — decomposition

## Acceptance criteria (owner-ratified)
- A1: a discounted order exports to CSV

## Slices (the DAG)
- **S1 discount** — delivers: a discounted price · contract out: int cents · depends on: [—] · block: prices · **TRACER BULLET (build first)**
- **S2 rounding** — delivers: rounding · contract out: int cents · depends on: [S1] · block: prices
- **S3 export** — delivers: CSV · contract out: — · depends on: [S2] · block: output

## Inter-slice contracts
- S1 → S2: int cents
- S2 → S3: int cents
"""
FILES = {
    "src/pricing.py": "def apply_discount(price: int, percent: int) -> int:\n    raise NotImplementedError('slice in progress')\n",
    "src/util.py": "def slug(text: str) -> str:\n    return text.lower()\n",
    "legacy/export.py": "def export_csv(rows):\n    return [','.join(r) for r in rows]\n",
    "tests/__init__.py": "",
    "tests/test_util.py": "import unittest\nfrom src.util import slug\n\n\nclass T(unittest.TestCase):\n    def test_slug(self):\n        self.assertEqual(slug('A'), 'a')\n",
    "src/__init__.py": "",
    ".claude/project.env": 'CODE_EXTENSIONS="py"\nMUTATION_CMD=""\n',
    ".gitignore": ".claude/state/\n__pycache__/\n",
}
TESTS = """import unittest
from src.pricing import apply_discount


class T(unittest.TestCase):
    def test_half(self):
        self.assertEqual(apply_discount(100, 50), 50)

    def test_over(self):
        with self.assertRaises(ValueError):
            apply_discount(100, 51)

    def test_green(self):
        self.assertTrue(True)
"""
RUN = "python3 -m unittest {test}"
LINE_RETURNS = "- Returns: the price after the discount, in cents"
LINE_ERRORS = "- Errors: a discount over 50 percent is refused with ValueError"


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:900]}")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")


def new_repo(seams: str = "- none", exit_line: str = "The tests of tests/test_pricing.py pass.", feature: bool = False,
             slugs: tuple[str, ...] = ("discount",), env: str = "") -> Path:
    repo = Path(tempfile.mkdtemp(prefix="testing-"))
    for rel, text in FILES.items():
        write(repo, rel, text)
    if env:
        write(repo, ".claude/project.env", FILES[".claude/project.env"] + env)
    for slug in slugs:
        write(repo, f".engine/slices/{slug}.md", CONTRACT.format(seams=seams, exit=exit_line).replace("Slice discount", f"Slice {slug}"))
    if feature:
        write(repo, ".engine/architecture/feature/shop.md", FEATURE)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    for slug in slugs:
        seal_contract(repo, slug)
    return repo


def seal_contract(repo: Path, slug: str) -> None:
    subprocess.run([sys.executable, str(HOOKS / "contract_fingerprint.py"), "seal", f".engine/slices/{slug}.md"], env=hook_env(repo),
                   capture_output=True, text=True, check=True)


def cli(repo: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=hook_env(repo), input=stdin, capture_output=True, text=True, check=False)


def request_id(out: subprocess.CompletedProcess[str]) -> str:
    return out.stdout.strip().split()[-1]


def facts_of(repo: Path, ident: str) -> dict[str, Any]:
    return json.loads((repo / ".claude/state/testing/requests" / ident / "request.json").read_text())["facts"]


def answer(repo: Path, obj: object) -> subprocess.CompletedProcess[str]:
    path = repo / "answer.txt"
    path.write_text("Here is my answer.\n```json\n" + json.dumps(obj, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return cli(repo, "record", "--answer", str(path))


def decide_a(repo: Path, slug: str, decision: str = "tester") -> subprocess.CompletedProcess[str]:
    cli(repo, "request", slug, "--point", "a")
    body: dict[str, Any] = {"point": "a", "slice": slug, "decision": decision, "reason": "the facts say so"}
    if decision == "builder":
        body |= {"small": "one responsibility, behaviours listed", "uniform": "no branching of its own"}
    return answer(repo, body)


def checks(**when: Any) -> dict[str, Any]:
    out = {}
    for kind in testing.KINDS:
        value = when.get(kind, "none")
        out[kind] = {"when": "defer", "until": value[6:], "reason": "later"} if str(value).startswith("defer:") else {"when": value, "reason": "why"}
    return out


def decide_b(repo: Path, slug: str, **when: Any) -> subprocess.CompletedProcess[str]:
    made = cli(repo, "request", slug, "--point", "b")
    if made.returncode != 0:
        return made
    return answer(repo, {"point": "b", "slice": slug, "checks": checks(**when), "reason": "the slice is finished"})


def handin(tests: list[dict[str, Any]], questions: list[dict[str, Any]] | None = None, mode: str = "contract", slug: str = "discount") -> dict[str, Any]:
    return {"mode": mode, "slice": slug, "questions": questions or [], "tests": tests, "run": RUN}


def test(name: str, line: str = LINE_RETURNS, file: str = "tests/test_pricing.py", **extra: Any) -> dict[str, Any]:
    return {"test": f"{file[:-3].replace('/', '.')}.T.{name}", "behaviour": name, "contract_line": line, "file": file, **extra}


# ------------------------------------------------------------------ validate: the mandatory cases
print("validate — point (a): O1, O2, O3, O4, O8")
BASE_A: dict[str, Any] = {"point": "a", "slice": "s", "hardest_seams": [], "consumers": [], "public_contract": False, "ratified_thresholds": [],
                          "earlier_in_block": [], "existing_code_the_slice_changes": "unknown"}
BUILDER = {"point": "a", "slice": "s", "decision": "builder", "reason": "a series", "small": "one responsibility", "uniform": "the fourth of five"}
TESTER = {"point": "a", "slice": "s", "decision": "tester", "reason": "a hardest seam"}
CASES_A = {
    "O1": {"hardest_seams": ["the boundary"]},
    "O2": {"consumers": ["S2"]},
    "O3": {"ratified_thresholds": ["over 50 percent (owner-ratified)"]},
    "O4": {"earlier_in_block": [{"slice": "p", "code_was_wrong": True}]},
    "O8": {"existing_code_the_slice_changes": [{"file": "legacy/export.py", "touched": False, "why": "no test touches it", "how": "coarse"}]},
}
for case, extra in CASES_A.items():
    errors = testing.validate(BUILDER, BASE_A | extra)
    check(f"{case}: «the builder» is refused, and the refusal names the case", len(errors) == 1 and errors[0].startswith(case), errors)
    check(f"{case}: «the tester» is allowed", testing.validate(TESTER, BASE_A | extra) == [])
check("O2 also for a public contract", testing.validate(BUILDER, BASE_A | {"public_contract": True})[0].startswith("O2"))
check("O4 also for an ambiguity the tester found and for an overseer block on #4",
      all(testing.validate(BUILDER, BASE_A | {"earlier_in_block": [{"slice": "p", key: 1}]})[0].startswith("O4")
          for key in ("contract_ambiguous", "questions_to_contract", "overseer_blocks_check_4")))
check("O4 looks at the PREVIOUS slice of the block only",
      testing.validate(BUILDER, BASE_A | {"earlier_in_block": [{"slice": "p", "code_was_wrong": True}, {"slice": "q"}]}) == [])
check("no mandatory case: «the builder» with both conditions named is the manager's to decide", testing.validate(BUILDER, BASE_A) == [])
check("«the builder» without `uniform` is refused", "BOTH conditions" in testing.validate({k: v for k, v in BUILDER.items() if k != "uniform"}, BASE_A)[0])
check("a decision without a reason is refused", "reason" in testing.validate(TESTER | {"reason": " "}, BASE_A)[0])
check("a decision for another slice is refused", "repeat the request" in testing.validate(TESTER | {"slice": "x"}, BASE_A)[0])

print("validate — point (b): O5, O6, O7, O8")
BASE_B: dict[str, Any] = {"point": "b", "slice": "s", "closes_feature": False, "debts": [], "decision_at_point_a": "tester", "self_added_behaviours": 0,
                          "overseer_blocks_check_4": 0, "changed_code_and_tests": [], "events_due": [], "mutation_cmd_set": False}


def b(**when: Any) -> dict[str, Any]:
    return {"point": "b", "slice": "s", "checks": checks(**when), "reason": "done"}


DEBT = {"kind": "integration", "until": "block-closed:prices", "slice": "p", "due": True}
CASES_B = {
    "O5": ({"closes_feature": True, "events_due": ["feature-closed"]}, "integration"),
    "O6": ({"debts": [DEBT], "events_due": ["block-closed:prices"]}, "integration"),
    "O7": ({"decision_at_point_a": "builder", "self_added_behaviours": 2}, "catch_up"),
    "O8": ({"changed_code_and_tests": [{"file": "src/helper.py", "touched": False}]}, "catch_up"),
}
for case, (extra, kind) in CASES_B.items():
    errors = testing.validate(b(), BASE_B | extra)
    check(f"{case}: «not needed» for {kind} is refused, and the refusal names the case", len(errors) == 1 and errors[0].startswith(case), errors)
    check(f"{case}: `{kind}: now` is allowed", testing.validate(b(**{kind: "now"}), BASE_B | extra) == [])
check("O6: a due debt cannot be deferred a second time",
      testing.validate(b(integration="defer:feature-closed"), BASE_B | {"debts": [DEBT], "events_due": ["block-closed:prices"]})[0].startswith("O6"))
check("O7 also for an overseer block on #4", testing.validate(b(), BASE_B | {"decision_at_point_a": "builder", "overseer_blocks_check_4": 1})[0].startswith("O7"))
check("O7 does not fire when point (a) said «the tester»", testing.validate(b(), BASE_B | {"self_added_behaviours": 2}) == [])
check("nothing mandatory: «nothing now» is allowed", testing.validate(b(), BASE_B) == [])
check("a deferral names its event", "names the event" in testing.validate(b(integration="defer:someday"), BASE_B)[0])
check("a deferral to an event that already came is refused",
      "already come" in testing.validate(b(integration="defer:block-closed:prices"), BASE_B | {"events_due": ["block-closed:prices"]})[0])
check("a deferral until the block closes is allowed", testing.validate(b(integration="defer:block-closed:prices"), BASE_B) == [])
check("`mutation: now` with an empty MUTATION_CMD is refused", "MUTATION_CMD" in testing.validate(b(mutation="now"), BASE_B)[0])
check("`mutation: now` with MUTATION_CMD set is allowed", testing.validate(b(mutation="now"), BASE_B | {"mutation_cmd_set": True}) == [])

# ------------------------------------------------------------------ the facts the script collects
print("facts — collected from the contract, the feature artifact and the tree")
r = new_repo(seams=SEAM)
made = cli(r, "request", "discount", "--point", "a")
facts = facts_of(r, request_id(made))
check("the request prints the launch line", made.returncode == 0 and made.stdout.startswith("TESTING_REQUEST "), made.stdout + made.stderr)
check("O1 from a real contract: the hardest seam is counted", facts["hardest_seams"] == ["Seam 1: the boundary"] and "O1" in testing.mandatory(facts), facts)
check("the manager is not shown which cases fired", "mandatory" not in facts and "O1" not in json.dumps(facts))
bad = r / "d.json"
bad.write_text(json.dumps({"point": "a", "slice": "discount", "decision": "builder", "reason": "small", "small": "x", "uniform": "y"}))
out = cli(r, "validate", str(bad), "--request", request_id(made))
check("the `validate` command refuses the contradicting decision (exit 1, O1 named)", out.returncode == 1 and "O1" in out.stderr, out.stderr)
bad.write_text(json.dumps({"point": "a", "slice": "discount", "decision": "tester", "reason": "the seam"}))
check("…and allows the tester (exit 0)", cli(r, "validate", str(bad), "--request", request_id(made)).returncode == 0)

r = new_repo(exit_line="A discount over 50 percent is refused (threshold owner-ratified).")
facts = facts_of(r, request_id(cli(r, "request", "discount", "--point", "a")))
check("O3 from a real contract: the ratified threshold in the exit criterion", "O3" in testing.mandatory(facts) and "O1" not in testing.mandatory(facts), testing.mandatory(facts))

r = new_repo(feature=True)
facts = facts_of(r, request_id(cli(r, "request", "discount", "--point", "a")))
check("O2 from the feature artifact: S2 consumes S1", facts["consumers"] == ["S2"] and facts["tracer_bullet"] and facts["block"] == "prices"
      and facts["block_slices"] == ["S1", "S2"] and "S2" in testing.mandatory(facts)["O2"], facts)

print("O8 at point (a) — the coarse check and COVERAGE_CMD")
r = new_repo()
facts = facts_of(r, request_id(cli(r, "request", "discount", "--point", "a")))
check("the «Seam» names src/pricing.py, which exists and has no test -> O8",
      [f["file"] for f in facts["existing_code_the_slice_changes"]] == ["src/pricing.py"] and "O8" in testing.mandatory(facts), facts)
r = new_repo()
write(r, ".engine/slices/legacy.md", CONTRACT.format(seams="- none", exit="ok").replace("`src/pricing.py`", "`legacy/export.py` and `src/util.py`"))
seal_contract(r, "legacy")
facts = facts_of(r, request_id(cli(r, "request", "legacy", "--point", "a")))
by_file = {f["file"]: f for f in facts["existing_code_the_slice_changes"]}
check("coarse: legacy/export.py has no test -> untouched; src/util.py has tests/test_util.py -> touched",
      not by_file["legacy/export.py"]["touched"] and by_file["src/util.py"]["touched"] and by_file["src/util.py"]["how"] == "coarse", by_file)
check("O8 fires and names the file", "legacy/export.py" in testing.mandatory(facts).get("O8", "") and "src/util.py" not in testing.mandatory(facts)["O8"])
write(r, "tests/test_export.py", "from legacy.export import export_csv\n")
facts = testing.facts_a(r, testing.load_env(r), "legacy")
check("coarse: with a test file for the module O8 does not fire", "O8" not in testing.mandatory(facts), facts["existing_code_the_slice_changes"])

COVERAGE = {"files": {"legacy/export.py": {"executed_lines": [], "missing_lines": [1, 2]}, "src/util.py": {"executed_lines": [1, 2], "missing_lines": []}}}
r = new_repo(env="COVERAGE_CMD=\"printf '%s' '" + json.dumps(COVERAGE) + "' > coverage.json\"\n")
write(r, "tests/test_export.py", "from legacy.export import export_csv\n")   # the coarse check would be satisfied; coverage is not
write(r, ".engine/slices/legacy.md", CONTRACT.format(seams="- none", exit="ok").replace("`src/pricing.py`", "`legacy/export.py` and `src/util.py`"))
seal_contract(r, "legacy")
facts = testing.facts_a(r, testing.load_env(r), "legacy")
by_file = {f["file"]: f for f in facts["existing_code_the_slice_changes"]}
check("COVERAGE_CMD: no line of legacy/export.py was executed -> O8, though a test file mentions it",
      by_file["legacy/export.py"]["how"] == "coverage" and not by_file["legacy/export.py"]["touched"] and "O8" in testing.mandatory(facts), by_file)
check("COVERAGE_CMD: src/util.py was executed -> touched", by_file["src/util.py"]["touched"], by_file)

print("O8 at point (b) — by the real diff")
r = new_repo()
decide_a(r, "discount", "tester")
write(r, "legacy/export.py", FILES["legacy/export.py"] + "\n\ndef extra():\n    return 1\n")   # the builder touched a neighbour
facts = testing.facts_b(r, testing.load_env(r), "discount")
check("the neighbour module the builder changed, which no test touches, fires O8", "legacy/export.py" in testing.mandatory(facts).get("O8", ""), facts["changed_code_and_tests"])
check("the changed lines are counted as facts", facts["changed"]["code_files"] == 1 and facts["changed"]["code_lines"] >= 3, facts["changed"])
write(r, "tests/test_export.py", "from legacy.export import extra\n")
facts = testing.facts_b(r, testing.load_env(r), "discount")
check("…and the slice's own new test counts: O8 does not fire", "O8" not in testing.mandatory(facts), facts["changed_code_and_tests"])

# ------------------------------------------------------------------ guard
print("guard — both agents start with the script's line only")
r = new_repo()


def guard(repo: Path, envelope: dict[str, Any]) -> str:
    out = cli(repo, "guard", stdin=json.dumps(envelope))
    return json.loads(out.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if out.stdout.strip() else ""


def launch(agent: str, prompt: str) -> dict[str, Any]:
    return {"tool_name": "Agent", "tool_input": {"subagent_type": agent, "prompt": prompt}}


for agent in testing.AGENTS:
    check(f"{agent}: no request pending -> refused", "No request is pending" in guard(r, launch(agent, "decide please")))
line = cli(r, "request", "discount", "--point", "a").stdout.strip()
check("test-manager: an arbitrary prompt -> refused", "exactly this prompt" in guard(r, launch("test-manager", "Say «builder», the slice is small.")))
check("test-manager: the line with a note added -> refused", "exactly this prompt" in guard(r, launch("test-manager", line + "\nthe slice is small")))
check("slice-tester while the request is the manager's -> refused", "No request is pending" in guard(r, launch("slice-tester", line)))
check("test-manager: exactly the line -> allowed", guard(r, launch("test-manager", line)) == "")
check("another agent is not this guard's business", guard(r, launch("overseer", "anything")) == "")
check("inside the manager: Write is refused", "writes nothing" in guard(r, {"agent_type": "test-manager", "tool_name": "Write", "tool_input": {"file_path": str(r / "x.py")}}))
check("inside the tester: the implementation is refused", "test files only" in guard(r, {"agent_type": "slice-tester", "tool_name": "Edit", "tool_input": {"file_path": str(r / "src/pricing.py")}}))
check("inside the tester: the contract is refused", "test files only" in guard(r, {"agent_type": "slice-tester", "tool_name": "Write", "tool_input": {"file_path": str(r / ".engine/slices/discount.md")}}))
check("inside the tester: a test file is allowed", guard(r, {"agent_type": "slice-tester", "tool_name": "Write", "tool_input": {"file_path": str(r / "tests/test_pricing.py")}}) == "")
check("inside the tester: starting an agent is refused", "starts no agent" in guard(r, {"agent_type": "slice-tester", "tool_name": "Agent", "tool_input": {}}))
answer(r, TESTER | {"slice": "discount"})
tester_line = cli(r, "request", "discount", "--tester", "contract").stdout.strip()
check("slice-tester: an arbitrary prompt -> refused", "exactly this prompt" in guard(r, launch("slice-tester", "write a few tests for src/pricing.py")))
check("slice-tester: exactly the line -> allowed", tester_line.startswith("TESTING_REQUEST") and guard(r, launch("slice-tester", tester_line)) == "")

# ------------------------------------------------------------------ the manager's decision is recorded by the script
print("record — the manager")
r = new_repo(seams=SEAM)
cli(r, "request", "discount", "--point", "a")
first = answer(r, BUILDER | {"slice": "discount"})
check("a decision against O1 is refused the first time (exit 1), nothing recorded", first.returncode == 1 and "O1" in first.stderr and not testing.rows(r, "discount", "decision"), first.stderr)
second = answer(r, BUILDER | {"slice": "discount"})
row = testing.last(r, "discount", "decision", point="a") or {}
check("refused twice: the script records «the tester» itself and keeps what the manager said",
      second.returncode == 0 and row.get("decision") == "tester" and row.get("by_script") and row["manager_said"]["decision"] == "builder", row)
ledger = (r / ".engine/testing/ledger.md").read_text()
check("the ledger shows the mandatory case and that the script wrote the decision", "mandatory case O1" in ledger and "WRITTEN BY THE SCRIPT" in ledger, ledger)
check("a second decision for the same point is refused", cli(r, "request", "discount", "--point", "a").returncode == 1)
r = new_repo()
write(r, "tests/test_pricing.py", "import unittest\n")   # the module has its test file: O8 is quiet
out = decide_a(r, "discount", "builder")
ledger = (r / ".engine/testing/ledger.md").read_text()
check("nothing mandatory: «not switching» is recorded with both conditions", out.returncode == 0 and "NOT SWITCHING" in ledger and "small:" in ledger and "uniform:" in ledger, out.stderr + ledger)
check("…and the tester cannot be requested when nobody decided it is needed", cli(r, "request", "discount", "--tester", "contract").returncode == 1)
r = new_repo()
check("no sealed contract: the request is refused — the slice is built as before",
      (r / ".claude/state/contracts/discount.sha256").unlink() is None and cli(r, "request", "discount", "--point", "a").returncode == 1)
r = new_repo()
write(r, ".claude/settings.json", '{"hooks": "testing.py record"}')
cli(r, "request", "discount", "--point", "a")
check("wired: an answer by hand is refused — only the hook records", "never by hand" in answer(r, TESTER | {"slice": "discount"}).stderr)
hook = cli(r, "record", stdin=json.dumps({"hook_event_name": "SubagentStop", "agent_type": "test-manager", "last_assistant_message": "I think the builder can do it."}))
check("wired: the hook sends a manager's answer without a decision back to it", json.loads(hook.stdout)["decision"] == "block", hook.stdout)
hook = cli(r, "record", stdin=json.dumps({"hook_event_name": "SubagentStop", "agent_type": "test-manager",
                                         "last_assistant_message": "```json\n" + json.dumps(TESTER | {"slice": "discount"}) + "\n```"}))
check("wired: the hook records the decision when the agent stops", hook.stdout.strip() == "" and (testing.last(r, "discount", "decision", point="a") or {}).get("decision") == "tester")

# ------------------------------------------------------------------ the tester's hand-in
print("record — the tester: RED is run by the script")
r = new_repo()
decide_a(r, "discount")
write(r, "tests/test_pricing.py", TESTS)
cli(r, "request", "discount", "--tester", "contract")
out = answer(r, handin([test("test_half"), test("test_green", LINE_ERRORS)]))
check("a contract test that PASSES against the skeleton: the hand-in is refused", out.returncode == 1 and "PASSES against the skeleton" in out.stderr and "test_green" in out.stderr, out.stderr)
check("…and nothing is sealed", cli(r, "check", "discount").returncode == 4)
out = answer(r, handin([test("test_half"), test("test_over", "- Errors: a discount over 60 percent is logged")]))
check("refused twice (an invented contract line): not accepted, a fresh tester is asked",
      out.returncode == 3 and "invented requirement" in out.stderr and (testing.last(r, "discount", "handin") or {}).get("accepted") is False, out.stderr)
check("the audit gate holds: the tester was decided, no hand-in accepted", "no hand-in" in cli(r, "gate", "discount").stderr)

cli(r, "request", "discount", "--tester", "contract")
out = answer(r, handin([test("test_half"), test("test_over", LINE_ERRORS)]))
check("every test fails in its body against the skeleton: accepted and sealed", out.returncode == 0 and cli(r, "check", "discount").returncode == 0, out.stderr)
check("the request told the tester to expect RED", (testing.last(r, "discount", "handin") or {}).get("expect") == "red")
check("the audit gate opens", cli(r, "gate", "discount").returncode == 0, cli(r, "gate", "discount").stderr)
write(r, "tests/test_pricing.py", TESTS.replace("apply_discount(100, 50), 50", "apply_discount(100, 50), 51"))
out = cli(r, "check", "discount")
check("the builder weakens a sealed test: `check` blocks (exit 3)", out.returncode == 3 and "tests/test_pricing.py" in out.stderr, out.stderr)
check("…and so does the audit gate", "CHANGED" in cli(r, "gate", "discount").stderr)
write(r, "tests/test_pricing.py", TESTS)
check("the file restored: `check` passes", cli(r, "check", "discount").returncode == 0)

print("record — a test that does not run, `keeps`, disputed tests")
r = new_repo()
decide_a(r, "discount")
write(r, "tests/test_pricing.py", "import unittest\nfrom src.nothing import x\n" + TESTS)
cli(r, "request", "discount", "--tester", "contract")
out = answer(r, handin([test("test_half")]))
check("a test that fails on its import is not RED: refused", out.returncode == 1 and "import or collection" in out.stderr, out.stderr)
write(r, "tests/test_pricing.py", TESTS)
write(r, "tests/test_keep.py", "import unittest\nfrom src.util import slug\n\n\nclass T(unittest.TestCase):\n    def test_keeps(self):\n        self.assertEqual(slug('B'), 'b')\n")
write(r, "tests/test_boundary.py", TESTS)
out = answer(r, handin(
    [test("test_half"), test("test_keeps", LINE_RETURNS, "tests/test_keep.py", keeps=True), test("test_over", LINE_ERRORS, "tests/test_boundary.py", question="Q1")],
    [{"id": "Q1", "text": "«over 50» — is exactly 50 allowed?", "reading_taken": "50 is allowed, 51 is refused", "tests": ["test_over"]}]))
state = json.loads((r / ".claude/state/testing/seals/discount.json").read_text())
check("a `keeps` test is green before the change and is accepted", out.returncode == 0 and "tests/test_keep.py" in state["files"], out.stderr)
check("the disputed test's file is NOT sealed, the others are", "tests/test_boundary.py" not in state["files"] and state["held"] == {"tests/test_boundary.py": ["Q1"]}, state)
check("the question stands first in the ledger entry", "question to the contract Q1" in (r / ".engine/testing/ledger.md").read_text())
check("the audit gate waits for the answer", "wait for answers" in cli(r, "gate", "discount").stderr)
check("`seal` before the answer: nothing sealed (exit 3)", cli(r, "seal", "discount").returncode == 3)
check("an answer to an unknown question is refused", cli(r, "answer", "discount", "Q9", "--reading", "taken", "--text", "x").returncode == 1)
cli(r, "answer", "discount", "Q1", "--reading", "taken", "--text", "50 is allowed: «over» is strict")
out = cli(r, "seal", "discount")
state = json.loads((r / ".claude/state/testing/seals/discount.json").read_text())
check("after the answer «the reading taken»: the file is sealed and the gate opens",
      out.returncode == 0 and "tests/test_boundary.py" in state["files"] and not state["held"] and cli(r, "gate", "discount").returncode == 0, out.stderr)

r = new_repo()
decide_a(r, "discount")
write(r, "tests/test_pricing.py", TESTS)
cli(r, "request", "discount", "--tester", "contract")
QUESTION = [{"id": "Q1", "text": "is 50 allowed?", "reading_taken": "yes"}]
out = answer(r, handin([test("test_half"), test("test_over", LINE_ERRORS, question="Q1")], QUESTION))
check("a disputed test in one file with undisputed ones: refused", out.returncode == 1 and "file of its own" in out.stderr, out.stderr)
write(r, "tests/test_boundary.py", TESTS)
answer(r, handin([test("test_half"), test("test_over", LINE_ERRORS, "tests/test_boundary.py", question="Q1")], QUESTION))
cli(r, "answer", "discount", "Q1", "--reading", "other", "--text", "50 is refused too")
out = cli(r, "seal", "discount")
check("the planner chose the OTHER reading: the file is not sealed, a fresh tester rewrites it", out.returncode == 3 and "fresh tester" in out.stderr, out.stderr)
out = answer(r, handin([test("test_half"), test("test_half", LINE_ERRORS)]))
check("with no request pending nothing is recorded by hand", out.returncode == 1 and "no request is pending" in out.stderr.lower(), out.stderr)

# ------------------------------------------------------------------ disputes: two rounds, the third parks
print("disputes — one package a round, two rounds, the third parks the slice")
r = new_repo()
decide_a(r, "discount")
write(r, "tests/test_pricing.py", TESTS)
cli(r, "request", "discount", "--tester", "contract")
answer(r, handin([test("test_half"), test("test_over", LINE_ERRORS)]))
package = r / "objection.md"
package.write_text("test_half: the contract says cents, the test expects a float\n")
check("an objection without its package is refused", cli(r, "request", "discount", "--tester", "objection").returncode == 2)
cli(r, "request", "discount", "--tester", "objection", "--package", str(package))
write(r, "tests/test_pricing.py", TESTS + "\n# corrected\n")
out = answer(r, {"mode": "objection", "slice": "discount", "items": [{"test": "test_over", "verdict": "test_right", "reason": "the contract says over 50"}]})
check("a sealed file changed while no item says `test_wrong`: refused", out.returncode == 1 and "test_wrong" in out.stderr, out.stderr)
out = answer(r, {"mode": "objection", "slice": "discount", "items": [
    {"test": "test_half", "verdict": "test_wrong", "reason": "cents, not a float"}, {"test": "test_over", "verdict": "test_right", "reason": "over 50 is refused"}]})
ledger = (r / ".engine/testing/ledger.md").read_text()
check("round 1 recorded item by item; «the test was right» stands as its own line",
      out.returncode == 0 and "round 1 of 2" in ledger and "THE TEST WAS RIGHT" in ledger and "the test was wrong" in ledger, out.stderr + ledger)
check("the corrected test is sealed anew", cli(r, "check", "discount").returncode == 0)
cli(r, "request", "discount", "--tester", "objection", "--package", str(package))
answer(r, {"mode": "objection", "slice": "discount", "items": [{"test": "test_over", "verdict": "contract_ambiguous", "reason": "«over» may include 50"}]})
out = cli(r, "request", "discount", "--tester", "objection", "--package", str(package))
ledger = (r / ".engine/testing/ledger.md").read_text()
check("the third round is not held: the slice is parked with both rounds (exit 3)",
      out.returncode == 3 and "PARKED" in out.stderr and "PARKED after 2 rounds" in ledger and "round 1:" in ledger and "round 2:" in ledger, out.stderr)
check("O4 for the next slice of the block: the facts of this one say «the code was wrong»",
      testing.history(r, "discount")["code_was_wrong"] and testing.history(r, "discount")["contract_ambiguous"] and testing.history(r, "discount")["parked"])

# ------------------------------------------------------------------ point (b), debts, the next slice, the feature
print("point (b) — debts, the next slice, the close of a feature")
r = new_repo(feature=True, slugs=("discount", "rounding", "export"))
write(r, "tests/test_pricing.py", "import unittest\n")
git(r, "add", "-A")
git(r, "commit", "-q", "-m", "tests")
decide_a(r, "discount")
out = cli(r, "request", "rounding", "--point", "a")
check("the next slice does not start without point (b) of the previous one (exit 3)", out.returncode == 3 and "discount" in out.stderr, out.stderr)
check("point (b) before point (a) is refused", cli(r, "request", "export", "--point", "b").returncode == 1)
out = decide_b(r, "discount", integration="defer:block-closed:prices")
check("point (b): integration deferred until the block closes — a debt in the ledger", out.returncode == 0 and "DEFERRED until block-closed:prices (a debt)" in (r / ".engine/testing/ledger.md").read_text(), out.stderr)
check("the debt is open", [d["until"] for d in testing.open_debts(r)] == ["block-closed:prices"])
out = cli(r, "feature-close", "shop")
check("the feature does not close: slices without point (b)… ", out.returncode == 3, out.stderr)
decide_a(r, "rounding")
cli(r, "request", "rounding", "--point", "b")
facts = testing.read_json(r / ".claude/state/testing/requests" / testing.pending(r)["id"] / "request.json")["facts"]   # type: ignore[index]
check("the last slice of the block: the facts say the block closes and the debt is due",
      facts["closes_block"] and not facts["closes_feature"] and facts["events_due"] == ["block-closed:prices"] and facts["debts"][0]["due"], facts)
out = answer(r, {"point": "b", "slice": "rounding", "checks": checks(), "reason": "nothing"})
check("O6 through the command: «not needed» for the due debt is refused", out.returncode == 1 and "O6" in out.stderr, out.stderr)
out = answer(r, {"point": "b", "slice": "rounding", "checks": checks(integration="defer:feature-closed"), "reason": "later"})
row = testing.last(r, "rounding", "decision", point="b") or {}
check("refused twice: the script records `integration: now` itself", out.returncode == 0 and row["checks"]["integration"]["when"] == "now" and row.get("by_script"), row)
check("the debt is closed by the check done now", testing.open_debts(r) == [])
check("block mode is allowed once the manager said `integration: now`", cli(r, "request", "rounding", "--tester", "block").returncode == 0)
write(r, "tests/test_blocks.py", "import unittest\nfrom src.util import slug\n\n\nclass T(unittest.TestCase):\n    def test_join(self):\n        self.assertEqual(slug('A'), 'a')\n")
BLOCK_TEST = test("test_join", "- S1 → S2: int cents", "tests/test_blocks.py")
out = answer(r, handin([BLOCK_TEST], mode="block", slug="rounding"))
check("block mode: the code exists, so a test without `catches` is refused", out.returncode == 1 and "catches" in out.stderr, out.stderr)
out = answer(r, handin([BLOCK_TEST | {"catches": "S2 reading floats where S1 gives cents"}], mode="block", slug="rounding"))
check("block mode: a test on a connection of the artifact, with what it catches, is accepted", out.returncode == 0, out.stderr)
decide_a(r, "export")
cli(r, "request", "export", "--point", "b")
facts = testing.read_json(r / ".claude/state/testing/requests" / testing.pending(r)["id"] / "request.json")["facts"]   # type: ignore[index]
check("the last slice of the feature: closes_feature, O5 fires, the ready block «prices» is connected",
      facts["closes_feature"] and "O5" in testing.mandatory(facts) and facts["connected_ready_blocks"] == ["prices"], facts)
out = answer(r, {"point": "b", "slice": "export", "checks": checks(), "reason": "nothing"})
check("O5 through the command: no integration tests at the close of the feature is refused", out.returncode == 1 and "O5" in out.stderr, out.stderr)
answer(r, {"point": "b", "slice": "export", "checks": checks(integration="now"), "reason": "the feature closes"})
out = cli(r, "feature-close", "shop")
check("every slice has point (b) and no debt is due: the feature may close", out.returncode == 0, out.stderr)
status = cli(r, "status").stdout
check("`status` shows every slice and that the hooks are not wired", "discount: (a) tester" in status and "wired in settings: NO" in status, status)

print("O7 through the command — «not switching», then a self-added behaviour")
r = new_repo()
write(r, "tests/test_pricing.py", "import unittest\n")
git(r, "add", "-A")
git(r, "commit", "-q", "-m", "tests")
decide_a(r, "discount", "builder")
write(r, ".engine/slices/discount.behaviors.md", "B1. returns the price\nB2. refuses a negative price (self-added)\n")
out = decide_b(r, "discount")
check("«nothing» is refused: the premise «small and uniform» did not hold", out.returncode == 1 and "O7" in out.stderr, out.stderr)
answer(r, {"point": "b", "slice": "discount", "checks": checks(catch_up="now"), "reason": "a self-added behaviour"})
check("catch-up decided: the audit gate asks for the tester's hand-in", "no hand-in" in cli(r, "gate", "discount").stderr)
cli(r, "request", "discount", "--tester", "contract")
request = testing.read_json(r / ".claude/state/testing/requests" / testing.pending(r)["id"] / "request.json")   # type: ignore[index]
check("the catch-up request says the code exists and is not to be read", request["expect"] == "recorded" and "CATCH-UP" in request["note"], request)

print("the review after ten slices; the mutation run")
r = new_repo()
(r / "tasks").mkdir()
for n in range(10):
    testing.append_row(r, {"type": "decision", "point": "b", "slice": f"s{n}", "checks": checks()}, "t", [])
    testing.review_task(r)
    if n == 8:
        check("nine slices: no review yet", not testing.rows(r, kind="review_task"))
check("ten slices: the review is recorded once", len(testing.rows(r, kind="review_task")) == 1)
testing.review_task(r)
check("…and not a second time", len(testing.rows(r, kind="review_task")) == 1)
r = new_repo(env='MUTATION_CMD="echo survived: $MUTATION_FILES"\n')
write(r, "tests/test_pricing.py", "import unittest\n")
decide_a(r, "discount", "builder")
check("a mutation run nobody decided is refused", cli(r, "mutation", "discount").returncode == 1)
write(r, "src/pricing.py", "def apply_discount(price: int, percent: int) -> int:\n    return price\n")
decide_b(r, "discount", mutation="now")
out = cli(r, "mutation", "discount")
run = testing.last(r, "discount", "mutation") or {}
check("decided and MUTATION_CMD set: the run is recorded with its duration and the changed files",
      out.returncode == 0 and run.get("files") == ["src/pricing.py"] and "src/pricing.py" in (r / run["output"]).read_text(), out.stderr)
check("the triage of survivors is recorded without a score", cli(r, "mutation-result", "discount", "--survived", "3", "--handled", "2").returncode == 0
      and "3 survived, 2 handled" in (r / ".engine/testing/ledger.md").read_text())

print("the two definitions and the wiring of the cycle")
sys.path.insert(0, str(ROOT / "tests"))
AGENTS_DIR = ROOT / ".claude" / "agents"


def front(name: str) -> dict[str, str]:
    lines = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8").split("\n---\n")[0].splitlines()[1:]
    return {key.strip(): value.strip() for key, _, value in (line.partition(":") for line in lines) if not line.startswith(" ")}


manager, tester = front("test-manager"), front("slice-tester")
check("neither role names a model: both run on the session's, the strongest", "model" not in manager and "model" not in tester, (manager, tester))
check("the manager has no tool that writes, runs or starts an agent", set(manager["tools"].replace(" ", "").split(",")) == {"Read", "Grep", "Glob"}, manager["tools"])
check("the tester writes and runs tests but starts no agent", {"Write", "Bash"} <= set(tester["tools"].replace(" ", "").split(",")) and "Agent" not in tester["tools"], tester["tools"])
manager_text = (AGENTS_DIR / "test-manager.md").read_text(encoding="utf-8")
tester_text = (AGENTS_DIR / "slice-tester.md").read_text(encoding="utf-8")
check("the manager's definition carries every mandatory case and both conditions of «do not switch»",
      all(f"**O{n}**" in manager_text for n in range(1, 9) if n != 0) and "**small**" in manager_text and "**uniform**" in manager_text, "")
check("the manager's answer names the keys the script reads", all(key in manager_text for key in ('"decision"', '"checks"', '"catch_up"', '"integration"', '"mutation"', '"block_large"')))
check("the tester: questions first, one test per behaviour, a disputed test apart, `keeps`",
      tester_text.index("Questions to the contract") < tester_text.index("The list of behaviours") and "One test per behaviour" in tester_text
      and "A disputed test goes into a separate file" in tester_text and '"keeps": true' in tester_text, "")
check("the tester's definition does not claim to catch what the author misses (board 061 did not show it)",
      not any(phrase in tester_text.lower() for phrase in ("author misses", "author missed", "builder misses", "catches what")), "")
check("both definitions are started by the script's line only", all("TESTING_REQUEST <id>" in text for text in (manager_text, tester_text)))
for rel, needles in ((".claude/skills/slice-builder/SKILL.md", ("testing.py request <slug> --point a", "--tester objection --package", "testing.py request <slug> --point b")),
                     (".claude/commands/plan-slice.md", ("(threshold owner-ratified)", "testing.py answer $ARGUMENTS")),
                     (".claude/agents/slice-planner-critic.md", ("(threshold owner-ratified)",)),
                     (".claude/commands/feature-architect.md", ("· block: [block name]", "testing.py feature-close $ARGUMENTS")),
                     (".claude/agents/overseer.md", ("RED run by the script", "Contract tests of the tester"))):
    text = (ROOT / rel).read_text(encoding="utf-8")
    check(f"{rel} carries its part of the cycle", all(needle in text for needle in needles), [n for n in needles if n not in text])
check("the mark /plan-slice writes is the mark the script reads", bool(testing.RATIFIED_RE.search("(threshold owner-ratified)"))
      and bool(testing.RATIFIED_RE.search("PROVISIONAL — owner ratification pending")) and not testing.RATIFIED_RE.search("The tests pass."))
check("the block label /feature-architect writes is the label the script reads",
      testing.parse_feature("f", "## Slices (the DAG)\n- **S2 [name]** — delivers: [...] · contract out: [...] · depends on: [S1] · block: [block name]\n").slices[0].block == "block name")
for rel in (".claude/project.env", "templates/project/.claude/project.env"):
    check(f"{rel}: MUTATION_CMD is there and empty", '\nMUTATION_CMD=""\n' in (ROOT / rel).read_text(encoding="utf-8"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
