#!/usr/bin/env python3
"""/onboard — the first meeting with an existing project (board 073) — is built as approved.

WHY. The command is prose a model follows; nothing executes it. What can be checked for free is
its structure: the eight steps in the approved order, the things it must never do, the path
without the owner (steps 1–3, then stop), the profile template the maintenance commands will
read, and the board task that needs the owner present. A step or a prohibition lost in a later
edit of the command would otherwise be noticed only in somebody's real project.

The one behaviour that IS executable is checked by running it: the task made from the template
is never offered to, or started by, an agent working alone.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / ".claude/unattended/board.py"
PASS = FAIL = 0


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


board = load("board", BOARD)
engine = load("engine", ROOT / "engine.py")


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def text(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(doc: str, heading: str) -> str:
    """The body of the `## ` section whose heading starts with `heading`; '' when absent."""
    match = re.search(rf"^## {re.escape(heading)}.*?\n(.*?)(?=^## |\Z)", doc, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def flat(body: str) -> str:
    return " ".join(body.split())


# --- the command: eight steps, in order ---------------------------------------------------------
print("the command")
command = text(".claude/commands/onboard.md")
check("/onboard exists with a description", command.startswith("---\ndescription:"), command[:120])
steps = re.findall(r"^## (\d)\. (.+)$", command, re.MULTILINE)
check("eight numbered steps, 1 to 8", [n for n, _ in steps] == list("12345678"), steps)
WORDS = ("Survey", "commands", "rules", "owner decides", "fresh reader", "stays", "snapshot", "premises")
check("the steps are the approved ones, in the approved order",
      len(steps) == 8 and all(word.lower() in title.lower() for word, (_, title) in zip(WORDS, steps)), steps)

survey = flat(section(command, "1."))
check("step 1 is read-only and says what was not read", "read only" in steps[0][1] and "nothing else is written in this step" in survey
      and "Not read" in survey and "git log" in survey, survey[:300])
commands = flat(section(command, "2."))
check("step 2: a command that was not run does not go into project.env",
      "not run does not go into `project.env`" in commands and "exit code" in commands, commands[:300])
check("step 2: a failing command is recorded, not fixed", "Do not fix them" in commands)
check("step 2 (from the trial): the tool is probed first, a runner that would download is tool absent, each run has a time limit",
      "command -v" in commands and "running it would install" in commands and "time limit" in commands, commands[:300])
check("step 2 (from the trial): a variant never reaches project.env; no check ran at all is the first line and the first question",
      "recorded as a variant and does not go into `project.env`" in commands and "first line of the profile" in commands and "first question" in commands)
rules = flat(section(command, "3."))
check("step 3: three sources, each named", all(f"**{s}**" in rules for s in ("written", "seen in the code", "seen in the history")), rules[:300])
check("step 3: no source, no candidate; a guess is called a guess", "no source is not offered" in rules and "guess is called a guess" in rules)
check("step 3: a habit lists the files that do not keep it too, and what it is counted over", "the files that do not" in rules and "counted over" in rules)
check("step 3 (from the trial): one or more sources; a written rule the code breaks comes with its counter-evidence",
      "one or more of three" in rules and "counter-evidence" in rules)
older = flat(section(command, "If the project already has agent files"))
check("an older engine or existing agent files (from the trial): surveyed as documents, engine policy is no candidate, nothing replaced",
      "documents to survey" in older and "not a candidate rule of the project" in older and "is not replaced" in older, older[:300])
check("step 1 (from the trial): a hot file is read in full before a rule about it; a search count is marked",
      "read in full before any rule about it" in survey and "«counted, not read»" in survey)
owner = flat(section(command, "4."))
check("step 4: yes / no / corrected text, and the do-not-touch zones into SIMPLIFIER_PROTECTED",
      all(w in owner for w in ("**yes**", "**no**", "corrected text", "do-not-touch zones", "SIMPLIFIER_PROTECTED")), owner[:300])
reader = flat(section(command, "5."))
check("step 5: a fresh agent with only the profile checks every reference and edits nothing",
      "fresh context" in reader and "only the path of the profile" in reader and "edits nothing" in reader, reader[:300])
stays = flat(section(command, "6."))
check("step 6: the profile, AGENTS.md by the documentation skill, project.env",
      all(w in stays for w in (".engine/onboard/profile.md", "skill `documentation`", ".claude/project.env", "only those step 2 ran")), stays[:300])
check("step 6: every rule in the profile, only the indispensable in AGENTS.md",
      "**every** rule" in stays and "only the rules without which any conversation would go wrong" in stays)
check("step 6: no number of rules — the 200-line test and the simplifier hold the limit",
      "There is no number of rules" in stays and "200 lines" in stays and "simplifier" in stays
      and not re.search(r"(?i)\b(ten|10) rules\b|at most \d+ rules", command))
snapshot = flat(section(command, "7."))
check("step 7: the owner takes the snapshot in their own terminal; the agent only shows it",
      "baseline.py record" in snapshot and "own terminal" in snapshot and "refuses to write" in snapshot, snapshot[:300])
premises = flat(section(command, "8."))
check("step 8: what could not be checked goes into the premise log", ".engine/premises/premise-log.md" in premises and "unverified premise" in premises)

# --- the command: what it never does, and the path without the owner ------------------------------
print("the prohibitions and the path without the owner")
never = flat(section(command, "What /onboard never does"))
for label, needle in (("fixes nothing", "fixes nothing"), ("no decisions in hindsight", "no decisions in hindsight"),
                      ("no ADR", "No ADR"), ("installs nothing", "installs nothing"),
                      ("an absent tool is «not run», never repaired", "«not run», never repaired"),
                      ("reads no secrets", "reads no secrets"), ("never answers for the owner", "never answers for the owner")):
    check(f"never: {label}", needle in never, never[:200])
check("the prohibitions stand before the first step", 0 < command.find("## What /onboard never does") < command.find("## 1."))
alone = flat(section(command, "Who is here"))
check("without the owner: steps 1–3 only, a draft, then stop with questions written into the profile",
      "steps 1–3 only" in alone and "draft" in alone and "stop with the questions" in alone and "«Open questions»" in alone, alone[:300])
check("without the owner: project.env, AGENTS.md, the snapshot and the premise log are not touched",
      all(w in alone for w in ("Do not touch", "`.claude/project.env`", "`AGENTS.md`", "snapshot", "premise log")), alone[:400])
check("without the owner: both signs of an unattended session are named, and the owner is not acted out",
      "CLAUDE_UNATTENDED_SESSION=1" in alone and ".claude/state/overseer/mode" in alone and "do not act out the owner" in alone)
check("the command names only commands that exist", all((ROOT / rel).is_file() for rel in
      (".claude/hooks/baseline.py", ".claude/hooks/complexity_budget.py", ".claude/references/onboard-profile.md",
       ".claude/skills/documentation/SKILL.md")))

# --- the profile template -----------------------------------------------------------------------
print("the profile template")
profile = text(".claude/references/onboard-profile.md")
heads = re.findall(r"^## \d\. (.+)$", profile, re.MULTILINE)
check("six sections: map, commands, rules, risk zones, not read, open questions",
      heads == ["Map", "Commands", "Rules", "Risk zones", "Not read", "Open questions for the owner"], heads)
check("it starts as a draft the owner has not confirmed", "draft — not confirmed by the owner" in profile)
check("a command row carries its status and the evidence of the run", "Status (ran / not run / variant)" in profile and "Exit, duration" in profile)
check("a rule row carries source, evidence, counter-evidence, the owner's verdict and whether it goes into AGENTS.md",
      "| Source | Evidence | Counter-evidence | Owner's verdict | Goes into AGENTS.md |" in profile)
check("not read has two levels below «read in full»; the survey's do-not-touch candidates stand apart from the owner's words",
      "- Searched only:" in profile and "- Not opened:" in profile and "candidates the survey saw" in profile and "the owner's words" in profile)
check("the three sources and the four verdicts are spelled out",
      "written / seen in the code / seen in the history" in flat(profile) and "yes / no / the corrected text verbatim / waits for the owner" in flat(profile))
check("the risk zones: tested, untested, do not touch", all(w in profile for w in ("Tests exist", "No tests", "Do not touch")))
check("secrets are named by path only", "never opened, never quoted" in profile)
check("it ships with the engine and the profile itself is the project's",
      engine.owner_of(engine.parse_ownership(text(".claude/ownership.txt")), ".claude/references/onboard-profile.md") == "engine"
      and engine.owner_of(engine.parse_ownership(text(".claude/ownership.txt")), ".engine/onboard/profile.md") == "project")
context = text("CLAUDE.md") + text("templates/project/CLAUDE.md")
check("the profile is read on demand: no root file imports it", "@.engine/onboard" not in context and "@.claude/references/onboard" not in context)

# --- the board task that needs the owner present -------------------------------------------------
print("the task template with the owner present")
SEED = "templates/project/tasks/TEMPLATE-onboard.md"
seed = text(SEED)
parsed = board.parse(seed) if seed else None
check("the seed exists and parses as a task that needs the owner present, with no audit and no dependency",
      parsed is not None and parsed.attended and not parsed.audit and parsed.depends == (), parsed)
check("it has the owner's sections and names the command", all(h in seed for h in ("## Що зробити", "## Готово, коли", "## Питання до власника", "/onboard", "--attended")))
check("it repeats the prohibitions", all(w in seed for w in ("Нічого не виправляти", "не встановлювати", "заднім числом", "секрети не читати")))
ownership = engine.parse_ownership(text(".claude/ownership.txt"))
rule = next((r for r in ownership if r.pattern == "tasks/TEMPLATE-onboard.md"), None)
check("ownership seeds it into a project's tasks/, once", rule is not None and rule.owner == "project" and rule.seed == SEED, rule)

root = Path(tempfile.mkdtemp(prefix="onboard-board-"))
try:
    for name in board.COLUMNS:
        (root / "tasks" / name).mkdir(parents=True)
    (root / "tasks/todo/010-onboard.md").write_text(seed, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_UNATTENDED_SESSION"}

    def cli(*args: str, unattended: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(BOARD), "--root", str(root), *args], capture_output=True, text=True, check=False,
                              env={**env, "CLAUDE_UNATTENDED_SESSION": "1"} if unattended else env)

    r = cli("next")
    check("an agent alone is not offered the onboarding task", "010-onboard.md" not in r.stdout and r.returncode != 0, r.stdout + r.stderr)
    r = cli("start", "tasks/todo/010-onboard.md")
    check("…and may not start it", r.returncode != 0 and (root / "tasks/todo/010-onboard.md").is_file(), r.stdout + r.stderr)
    r = cli("start", "--attended", "tasks/todo/010-onboard.md", unattended=True)
    check("…not even with --attended in an unattended session", r.returncode != 0 and (root / "tasks/todo/010-onboard.md").is_file(), r.stdout + r.stderr)
    r = cli("next", "--attended")
    check("the owner's session is offered it", r.returncode == 0 and "010-onboard.md" in r.stdout, r.stdout + r.stderr)
finally:
    shutil.rmtree(root, ignore_errors=True)

# --- the documents ------------------------------------------------------------------------------
print("the documents")
setup = text("docs/TEMPLATE-SETUP.md")
check("TEMPLATE-SETUP has the onboarding step with the task template and the profile",
      "`/onboard`" in setup and "tasks/TEMPLATE-onboard.md" in setup and ".engine/onboard/profile.md" in setup and "--attended" in setup)
check("TEMPLATE-SETUP says what the command never does", "fixes nothing, installs nothing" in setup)
check("the engine's AGENTS.md names the command and the profile", "`/onboard`" in text("AGENTS.md") and ".engine/onboard/profile.md" in text("AGENTS.md"))
check("nothing of the trial project is in the engine", not (ROOT / ".engine/onboard").exists())

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
