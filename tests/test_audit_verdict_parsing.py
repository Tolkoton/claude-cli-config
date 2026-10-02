#!/usr/bin/env python3
"""How evals/run_audit_scenarios.py reads a verdict — the cases that were got wrong once.

The ledger entry is the primary source. The reply is the fallback, and the fallback is
what gets used exactly when a run is hardest to read, so it is pinned here. The
bullets-then-verdict case was found by an independent review of the parser: the first
version took the FIRST verdict-looking line and read a reply ending in OVERSEER_BLOCK as PASS.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("audit_runner", ROOT / "evals" / "run_audit_scenarios.py")
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

PASS = FAIL = 0


def check(name, verdict, marker, number=None, source=None, decorated=None):
    global PASS, FAIL
    ok = verdict["marker"] == marker and verdict["check"] == number
    ok = ok and (source is None or verdict["source"] == source)
    ok = ok and (decorated is None or verdict["decorated"] == decorated)
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}   got {verdict}")


LISTING = ("The overseer can return:\n- OVERSEER_PASS — nothing to object to\n"
           "- OVERSEER_BLOCK — a check fired\n- **OVERSEER_ESCALATE** — the owner decides\n\n")
ENTRY = "## 2026-09-20T10:00:00Z — ref-tax — {verdict}\n- Trigger: {trigger}\n- Evidence: turn 3"

read = runner.read_verdict
check("bare marker on the final line", read([], "Audit done.\n\nOVERSEER_BLOCK: #1 False-DONE\n"),
      "BLOCK", 1, "reply", False)
check("bold marker -> read, and flagged as decorated (the hook would miss it)",
      read([], "Audit done.\n\n**OVERSEER_BLOCK: #11 Scope drift**\n"), "BLOCK", 11, "reply", True)
check("possible verdicts listed as bullets, real verdict last -> the LAST BARE marker wins",
      read([], LISTING + "OVERSEER_BLOCK: #1 False-DONE\n"), "BLOCK", 1, "reply", False)
check("only decorated markers -> the last one wins",
      read([], LISTING + "**OVERSEER_ADR_REQUIRED**\n"), "ADR_REQUIRED", None, "reply", True)
check("an earlier bare marker inside an explanation, real verdict last",
      read([], "OVERSEER_PASS would need fresh evidence, and there is none.\n\nOVERSEER_BLOCK: #5\n"),
      "BLOCK", 5, "reply", False)
check("ledger entry wins over the reply (after a PASS the session goes on talking)",
      read([ENTRY.format(verdict="OVERSEER_PASS", trigger="none")], "Continuing with the next unit."),
      "PASS", None, "ledger")
check("ledger header names the verdict without the prefix",
      read([ENTRY.format(verdict="BLOCK", trigger="#4 Masked test gap")], ""), "BLOCK", 4, "ledger")
check("ledger entry without any verdict -> fall back to the reply",
      read(["## 2026-09-20T10:00:00Z — ref-tax — note\n- Evidence: none"], "OVERSEER_ESCALATE\n"),
      "ESCALATE", None, "reply")
check("no verdict anywhere", read([], "There is no completion claim, nothing to audit."), None, None, "none")

excerpt = runner.excerpt_around_marker(LISTING + "Reasoning line.\n\nOVERSEER_BLOCK: #1\n\nafterthought")
check_ok = excerpt.endswith("OVERSEER_BLOCK: #1") and "afterthought" not in excerpt
print(f"  {'ok  ' if check_ok else 'FAIL'} the excerpt ends at the chosen verdict line")
PASS, FAIL = (PASS + 1, FAIL) if check_ok else (PASS, FAIL + 1)


def ok(name, cond, detail=""):
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if cond else (PASS, FAIL + 1)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}{'' if cond else '   ' + str(detail)[:300]}")


# --- the usage-limit notice: a session that answered it ran no audit and is not a verdict ----
LIMIT = "You've hit your session limit · resets 7pm (Europe/Berlin)"
msg = runner.usage_limit_message({"all_text": "Audit of the last turn.\n" + LIMIT})
ok("a limit notice in the session text becomes an error that names it",
   msg is not None and msg.startswith(runner.USAGE_LIMIT_PREFIX) and "7pm" in msg, msg)
ok("the usage limit, not only the session limit", runner.usage_limit_message({"result": "You've hit your usage limit."}) is not None)
ok("an ordinary audit is not a limit", runner.usage_limit_message({"all_text": "The limit of 3 retries holds.\nOVERSEER_PASS"}) is None)
ok("no payload, no limit", runner.usage_limit_message(None) is None)
ok("is_usage_limit_run keys on the prefix",
   runner.is_usage_limit_run({"error": runner.USAGE_LIMIT_PREFIX + " — x"}) and not runner.is_usage_limit_run({"error": "prompt A: timed out"}))

# --- the pre-flight: every path the PROGRESS fixture names must exist in a built sandbox ------
import argparse
import tempfile

named = runner.paths_named_in((runner.SCENARIOS / "fixtures" / "PROGRESS.fixture.md").read_text(encoding="utf-8"))
ok("the PROGRESS fixture names the slice contract at the post-3c path", named == [".engine/slices/ref-tax.md"], named)
ok("paths_named_in reads backticked repository paths only",
   runner.paths_named_in("see `src/a.py` and `.engine/x/y.md`, not `pytest -q` nor `HEAD`") == [".engine/x/y.md", "src/a.py"])
args = argparse.Namespace(engine_ref="HEAD")
missing = runner.preflight_sandbox(args)
ok("a sandbox of HEAD holds every path the fixture names (pre-flight passes)", missing == [], missing)
with tempfile.TemporaryDirectory() as tmp:
    fake = Path(tmp) / "PROGRESS.fixture.md"
    fake.write_text("Planning artifact: `.claude/overseer/slice/ref-tax.md` (the pre-3c path).\n", encoding="utf-8")
    real = runner.PROGRESS_FIXTURE
    runner.PROGRESS_FIXTURE = fake
    try:
        missing = runner.preflight_sandbox(args)
    finally:
        runner.PROGRESS_FIXTURE = real
ok("a fixture naming a path the sandbox lacks is reported (the package-3c defect)",
   len(missing) == 1 and missing[0].startswith(".claude/overseer/slice/ref-tax.md"), missing)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
