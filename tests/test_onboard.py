#!/usr/bin/env python3
"""/onboard — the first meeting with an existing project (board 073) — is built as approved.

WHY. The command is prose a model follows; nothing executes it. What can be checked for free is
its structure: the eight steps in the approved order, the things it must never do, the path
without the owner (steps 1–4, then stop), the profile template the maintenance commands will
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
WORDS = ("Survey", "commands", "rules", "fresh reader", "owner decides", "stays", "snapshot", "premises")
check("the steps are the approved ones, in the approved order",
      len(steps) == 8 and all(word.lower() in title.lower() for word, (_, title) in zip(WORDS, steps)), steps)
# board 092 — the full trial (board 057): 9 references of 327 did not hold and 7 rules were worded more
# strongly than their source; with the reader after the verdicts the owner would have said «yes» to them
place = {word: next((int(n) for n, title in steps if word in title.lower()), 0) for word in ("fresh reader", "owner decides")}
check("the fresh reader stands before the owner's verdicts (092)", 0 < place["fresh reader"] < place["owner decides"], place)
check("the description names the reader before the owner's verdict and the path without the owner as steps 1–4 (092)",
      0 < command.find("has a fresh reader") < command.find("takes the owner's verdict") and "without the owner it does steps 1–4" in command,
      command[:700])

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
# board 091 — the five places of the full trial (board 057) where step 2 left the agent guessing
check("step 2 (091): the key variables of the session's environment are listed by name before any script runs; a script that would spend one is not run or runs with it unset",
      "list the key variables set in the session's environment" in commands and "names only, never a value" in commands
      and "explicitly unset" in commands and "paid or external service" in commands and "for (k in ENVIRON) print k" in commands
      and "A listing that failed is not an empty list" in commands, commands[:300])
check("step 2 (091): an environment that may have drifted from the lock file — the runner runs without syncing and offline, and that guard is no variant",
      "drifted from the lock file" in commands and "--no-sync" in commands and "offline" in commands
      and "does not make the command a variant" in commands, commands[:300])
check("step 2 (091): a tool only in the virtual environment is «ran» through the runner, not «tool absent»",
      "only in the project's virtual environment" in commands and "«ran» through the runner, not «tool absent»" in commands, commands[:300])
check("step 2 (091): one check spelled differently in several documents is one row with every source",
      "one row with every source" in commands and "not a row per spelling" in commands)
check("step 2 (091): exit 0 with nothing checked is «ran, checked nothing» and stays out of project.env",
      "«ran, checked nothing»" in commands and "is not «ran»" in commands
      and "«ran, checked nothing» does not go into `project.env`" in commands, commands[:300])
check("step 2 (092): one part ran its checks and another none — the first line names the part, steps 6–7 do not wait",
      "one part ran its checks and another ran none" in commands and "names the part with no check that ran" in commands
      and "Steps 6–7 do not wait" in commands and "which part it does not measure" in commands, commands[-900:])
rules = flat(section(command, "3."))
check("step 3: three sources, each named", all(f"**{s}**" in rules for s in ("written", "seen in the code", "seen in the history")), rules[:300])
check("step 3: no source, no candidate; a guess is called a guess", "no source is not offered" in rules and "guess is called a guess" in rules)
check("step 3: a habit lists the files that do not keep it too, and what it is counted over", "the files that do not" in rules and "counted over" in rules)
check("step 3 (from the trial): one or more sources; a written rule the code breaks comes with its counter-evidence",
      "one or more of three" in rules and "counter-evidence" in rules)
# board 093 — the full trial (board 057): 23 candidates, and in these places the agent drew the line by its own judgement
check("step 3 (093): a comment or docstring in the code is «written», and the source column says so",
      "A comment or a docstring in the code is **written** too" in rules and "«written, in code»" in rules, rules[:700])
check("step 3 (093): a rule is what a change could break, however short its source; one sentence the code does not confirm is a guess",
      "however short its source" in rules and "one sentence that nothing in the code confirms is a guess" in rules
      and "one sentence of a document is not by itself a rule" not in rules, rules[-900:])
check("step 3 (093): a rule is worded no more strongly than its source — the strong words need a count or a quotation, one case gives a rule about that case",
      "worded no more strongly than its source" in rules and "«only», «always», «every», «never» need a count or a quotation that carries the word" in rules
      and "is worded about that case" in rules, rules[-900:])
check("step 3 (093): a habit most files keep may name only the files that do not, when one search command lists the rest — and the command is written down",
      "name only the files that do **not** keep it" in rules and "are the majority" in rules
      and "one search command lists them" in rules and "write that command" in rules, rules[:900])
older = flat(section(command, "If the project already has agent files"))
check("an older engine or existing agent files (from the trial): surveyed as documents, engine policy is no candidate, nothing replaced",
      "documents to survey" in older and "not a candidate rule of the project" in older and "is not replaced" in older, older[:300])
check("the engine's rules (093): the sign is what the rule is about — the project's code and data, or the way an agent works — not where it is written",
      "the project's code and data" in older and "the way an agent works" in older and "wherever it is written" in older
      and all(w in older for w in ("secrets", "one commit per task", "memory")), older[:900])
check("the engine's commands (093): the engine's own commands and the checks of its hooks are not found commands",
      "the checks of its hooks are not *found* commands" in older and "not run in step 2" in older
      and "never go into `project.env`" in older, older[-700:])
check("step 1 (093): hot places are counted among code files; lock files, logs, manifests and engine records are one line «not code»",
      "counted among the files of code only" in survey and "«not code»" in survey
      and all(w in survey for w in ("lock files", "logs", "manifests", "records of an engine")), survey[:1200])
check("step 1 (093): of an older engine's records the decisions and rules are read, the rest is listed in «Not read»",
      "An older engine's records are not read whole either" in survey and "decisions and rules" in survey
      and "ledgers" in survey and "listed in «Not read» with its size in lines" in survey, survey[-900:])
check("step 1 (from the trial): a hot file is read in full before a rule about it; a search count is marked",
      "read in full before any rule about it" in survey and "«counted, not read»" in survey)
reader = flat(section(command, "4."))
check("step 4: a fresh agent with only the profile checks every reference and edits nothing",
      "fresh context" in reader and "only the path of the profile" in reader and "edits nothing" in reader, reader[:300])
check("step 4 (092): the reader runs before the owner sees a candidate, and without the owner too — it needs no owner",
      "Before the owner sees a candidate" in reader and "in a session without the owner too" in reader
      and "the reader needs no owner" in reader, reader[:300])
check("step 4 (092): the reader's second job — is a rule worded more strongly than its source",
      "worded more strongly than" in reader and "«only», «always», «every»" in reader and "with no count" in reader
      and "speaks of one case" in reader, reader[:600])
check("step 4 (092): what does not hold is corrected before the owner; a rule stronger than its source is reworded; no source left, no candidate",
      "reword every rule that is stronger than its source" in reader and "is not offered: it moves to the guesses" in reader, reader[:900])
check("step 4 (092): after the verdicts the reader checks only what the owner's words changed",
      "only over what the owner's words changed" in reader and "is not checked twice" in reader
      and "does not stay confirmed" in reader, reader[-500:])
owner = flat(section(command, "5."))
check("step 5: yes / no / corrected text, and the do-not-touch zones into SIMPLIFIER_PROTECTED",
      all(w in owner for w in ("**yes**", "**no**", "corrected text", "do-not-touch zones", "SIMPLIFIER_PROTECTED")), owner[:300])
check("step 5 (092): a long sitting has an order — the contradicted first, then those proposed for AGENTS.md",
      "first the contradicted ones" in owner and "then the ones you would propose for `AGENTS.md`" in owner, owner[:600])
check("step 5 (092): candidates of one kind go under one «yes» only when the owner asks for it; each still gets its verdict",
      "under one «yes» only if the owner asks for it" in owner and "never offer it" in owner
      and "the verdict is written on each" in owner, owner[:800])
stays = flat(section(command, "6."))
check("step 6 (092): the do-not-touch zones come from the owner's step, which is now step 5", "`SIMPLIFIER_PROTECTED` from step 5" in stays, stays[:600])
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
# board 095 — the full trial (board 057): the snapshot measured with the commands of an older project.env, which
# differed from the ones step 2 had run (other directories for the type check, tests stopping at the first failure)
check("step 7 (095): first the owner agrees the project.env of step 6, then the snapshot — `record` measures with the file on disk",
      0 < snapshot.find("First the owner agrees the `project.env` of step 6") < snapshot.find("The owner takes it")
      and "measures with the commands of `.claude/project.env` as it is on disk" in snapshot
      and "not the ones step 2 ran" in snapshot and "the snapshot waits" in snapshot, snapshot[:700])
check("step 7 (095): the warning about tests that stop at the first failure is the script's, and is not passed over",
      "stops at the first failure" in snapshot and "`record` prints a warning" in snapshot, snapshot[:900])
check("step 7 (095): in a session the first `record` shows what the first snapshot would hold; nothing in the step calls that a loosening",
      "what the first snapshot would record" in snapshot and "loosen" not in snapshot, snapshot[-700:])
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
check("never (091): an account identifier is not copied from a command's output either",
      "nor from the output of a command" in never, never[:400])
# board 094 — the full trial (board 057): the installation moved 19 records, the project's scripts went on naming the
# old paths, two checks then passed having checked nothing, the formatter failed on three moved files — and /onboard
# wrote all of it down as the state of the project
MOVED_FROM = (".claude/overseer", ".claude/premises", ".claude/architecture", ".claude/artifacts", "PROGRESS.md")
check("step 1 (094): «what the installation changed» is the first item of the survey — git status before anything is written, the count beside the commit",
      section(command, "1.").find("- **What the installation changed**") == section(command, "1.").find("\n- **") + 1
      and "`git status --short`" in survey and "before anything is written" in survey
      and "«tree not clean: N changes from the installation»" in survey and "the owner's unfinished work" in survey, survey[:700])
check("step 1 (094): the project's files that still name an old path are listed with file:line by a written search, the exclusions too; nothing is fixed",
      "still name an old path, with `file:line`" in survey and "git grep -n" in survey and all(f"-e '{old}'" in survey for old in MOVED_FROM)
      and "excludes an old directory and not `.engine/`" in survey and "Nothing is fixed" in survey, survey[:1400])
check("an older engine (094): its records are looked for in both places, the new and every old one",
      "Look for the records in both places" in older and "`.engine/`" in older
      and all(f"`{old}{'' if old.endswith('.md') else '/'}`" in older for old in MOVED_FROM), older[:700])
check("the search of step 1 names every place engine.py moves a record from (094)",
      all(any(old == place or old.startswith(place + "/") for place in MOVED_FROM) for old, _new in engine.MIGRATIONS),
      engine.MIGRATIONS)
check("step 2 (094): a result the move caused is a consequence of the installation, only with evidence, never «it passed before», and stays out of project.env",
      "consequence of the installation, not as the state of the project" in commands and "«after the installation»" in commands
      and "every failing file is one the installation moved or added" in commands and "is the project's, in full" in commands
      and "do not write that it passed" in commands and "Such a row does not go into `project.env`" in commands
      and "would record this consequence as the project's «as it was»" in commands, commands[-1500:])
check("never (091): a check's cache the project itself ignores is not a change to the project",
      "cache" in never and "the project itself ignores" in never and "is not a change to the project" in never, never[:400])
check("the prohibitions stand before the first step", 0 < command.find("## What /onboard never does") < command.find("## 1."))
alone = flat(section(command, "Who is here"))
check("without the owner: steps 1–4 only, a draft, then stop with questions written into the profile",
      "steps 1–4 only" in alone and "draft" in alone and "stop with the questions" in alone and "«Open questions»" in alone, alone[:300])
check("without the owner (092): the fresh reader is not skipped, and the owner's steps are 5–8",
      "the fresh reader of step 4 needs no owner and is not skipped" in alone and "Steps 5–8 are for a session the owner sits in" in alone
      and "1–3" not in command, alone[:400])
check("without the owner (092): step 5 is a procedure, not a list — the draft's questions are named",
      "a procedure, not a list" in alone and all(w in alone for w in (
          "«document against code»", "effect is unclear", "do-not-touch zones", "was not read", "one common question")), alone[:900])
check("without the owner (092): the common question is one, not a question per candidate", "never a question per candidate" in alone, alone[:900])
check("without the owner (094): what the installation changed is one of the draft's questions",
      "one for what the installation changed" in alone and "before the snapshot" in alone, alone[600:1500])
check("without the owner and without the board (092): the questions stay in the profile; the starter gets the path and the number",
      "has no addressee" in alone and "stay in the profile" in alone and "the profile's path and the number of questions" in alone, alone[-600:])
opening = flat(command.split("## What /onboard never does")[0])
check("one language (092): the owner's — in the command and in the template; without the owner it is the language of what started the session",
      "in the owner's language" in opening and "the task or request that started the session" in opening
      and "write in the language of the project's own documents" not in opening
      and "in the owner's language" in flat(text(".claude/references/onboard-profile.md")), opening[-500:])
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
check("the status line (092): without the owner it is steps 1–4, the owner confirms in step 5, the reader's count has the reworded rules",
      'add: "steps 1–4 only"' in flat(profile) and "after step 5" in flat(profile) and "K rules reworded" in profile
      and "1–3" not in profile and "after step 4" not in flat(profile), profile[:900])
check("the status line (094): beside the commit — whether the tree was clean, and how many changes are the installation's",
      re.search(r"^Surveyed at commit: `<sha>` · Tree: <clean \| not clean: N changes from the installation, M others> · Fresh reader:", profile, re.MULTILINE) is not None,
      profile[700:1100])
check("the map (094): what the installation changed has its place — the moved records and the project's files that still name an old path",
      "What the installation changed" in section(profile, "1.") and "still names an old path, or excludes it from lint / format" in section(profile, "1.")
      and '"after the installation:"' in flat(section(profile, "2.")), section(profile, "1.")[:900])
check("the risk zones (092): a part whose checks did not run has its row", "No check ran" in profile)
check("the hot places (093): the table is of code files, and what changes often but is not code has its own line",
      "among the files of code" in flat(profile) and "Not code that changes often" in profile, profile[900:1500])
check("a rule's source (093): the template names «written, in code» for a comment or docstring", "written, in code" in flat(profile))
# board 095 — the full trial (board 057): what step 1 and step 2 collected and the template had no place for
MAP, COMMANDS = section(profile, "1."), section(profile, "2.")
check("the map (095): reverts and the places fixed again and again have their table, with the commits",
      "Reverts, and places fixed again and again" in MAP
      and "| Path | What happened (reverted / fixed N times) | Commits |" in MAP, MAP[-1500:])
check("the map (095): a claim with no reference has a named place — marked, a question for the owner, never the opening sentence",
      "The project in one sentence: <" in MAP and "Claims of the map with no reference" in MAP
      and "the opening sentence included" in flat(MAP) and "section 6" in flat(MAP), MAP[:900])
check("the template's opening (095): a claim with nothing to cite is not written as a fact, and the map says where it goes",
      "a claim with nothing to cite is not written as a fact" in flat(profile)
      and "a claim with nothing to cite is not written." not in flat(profile), profile[:700])
check("the commands (095): a row names the part of the project the command belongs to",
      "| Purpose | Part of the project | Command | Found in | Status (ran / not run / variant) | Exit, duration | What fails, or why not run |" in COMMANDS,
      COMMANDS[:900])
check("the commands (095): «Found in» of a variant is the found command it varies and what was changed",
      "\"Found in\" of a variant" in flat(COMMANDS) and "the `file:line` of the found command it varies" in flat(COMMANDS)
      and "what was changed" in flat(COMMANDS), COMMANDS[:900])
check("the commands (095): tests and scripts that need a secret or the network — the number and the paths, in two lines",
      "Tests and scripts that need a secret or the network" in COMMANDS
      and re.search(r"^- Need a secret or a credential: <number> — <paths>$", COMMANDS, re.MULTILINE) is not None
      and re.search(r"^- Need the network or a running service: <number> — <paths>$", COMMANDS, re.MULTILINE) is not None, COMMANDS[-700:])
check("the command fills the new places (095): step 1 names the reverts' table and the unreferenced claims, step 2 the part, the variant's source and the count",
      "«Reverts, and places fixed again and again»" in survey and "«Claims of the map with no reference»" in survey
      and "«Part of the project»" in commands and "«Found in» of a variant" in commands
      and "the number and the paths" in commands, (survey[-600:], commands[-600:]))
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
check("the seed (092): the fresh reader comes before the owner's answers, and checks the wording too",
      0 < seed.find("Свіжий читач") < seed.find("власник відповідає") and "формулювання" in seed, seed[:900])
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
check("TEMPLATE-SETUP (092): the fresh reader before the owner's verdicts, and without the owner too",
      0 < setup.find("has a fresh reader check") < setup.find("takes the owner's «yes»") and "the candidates and the fresh reader's check" in flat(setup))
check("TEMPLATE-SETUP says what the command never does", "fixes nothing, installs nothing" in setup)
check("the engine's AGENTS.md names the command and the profile", "`/onboard`" in text("AGENTS.md") and ".engine/onboard/profile.md" in text("AGENTS.md"))
check("nothing of the trial project is in the engine", not (ROOT / ".engine/onboard").exists())

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
