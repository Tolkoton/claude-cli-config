#!/usr/bin/env python3
"""The fresh reader of a record (board 099: a sketch's record; board 100: a task's report): reader.py request, guard, record.

  - `request` takes only a sketch record of the project and prints the one launch line;
  - `guard`: the reader starts with exactly `READER_REQUEST <id>` of the pending request and nothing
    else; with no request, or with any other prompt, it is refused; the reader starts no agent;
  - `record` writes the verdict from the agent's answer — never the author: the row with the record's
    content when it was read, the journal entry; an answer that does not fit goes back once, then is
    INVALID; a record that changed while it was read is INVALID; the answer handed back through
    SubagentHandback (no last_assistant_message) is read too;
  - `passed()` holds only for the record as it is now;
  - three BLOCKs in a row on one record leave the marker the runner parks the task on; a PASS between
    them resets the count;
  - a task's report (`--report`): only the report of that task; the package names the task file, the
    task's commits and every document the task changed (never the board's moves or a journal); a
    document that changed while the report was read makes the reading INVALID; `passed()` holds only
    while the report and every document read stand, and only if every document asked about was read.

Run:   python3 tests/test_reader.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_env import hook_env

ROOT = Path(__file__).resolve().parent.parent
READER = ROOT / ".claude/hooks/reader.py"
PASS = FAIL = 0
RECORD = "# Ескіз rate\n\n## Питання\nЧи ріже API після 60 викликів?\n\n## Команда і вивід\n```\n$ python3 sketches/rate/probe.py\n61: 429\n```\n\n## Відповідь\nтак\n"
GOOD = {"verdict": "PASS", "reason": "the output line «61: 429» shows the cut the answer claims", "evidence": [".engine/sketches/rate.md:8"]}


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:700]}")


spec = importlib.util.spec_from_file_location("reader_under_test", READER)
assert spec is not None and spec.loader is not None
reader = importlib.util.module_from_spec(spec)
sys.modules["reader_under_test"] = reader
spec.loader.exec_module(reader)
root = Path(tempfile.mkdtemp(prefix="reader-")).resolve()
(root / ".engine/sketches").mkdir(parents=True)
(root / ".engine/sketches/rate.md").write_text(RECORD, encoding="utf-8")
(root / "README.md").write_text("not a record\n", encoding="utf-8")
REL = ".engine/sketches/rate.md"


def cli(*args: str, envelope: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
    env = hook_env(root)
    return subprocess.run([sys.executable, str(READER), *args], input=json.dumps(envelope) if envelope is not None else "",
                          capture_output=True, text=True, env=env, check=False, cwd=root)


def launch(prompt: str, agent: str = "reader", inside: str | None = None) -> dict[str, object]:
    envelope: dict[str, object] = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"subagent_type": agent, "prompt": prompt}}
    if inside:
        envelope["agent_type"] = inside
    out = cli("guard", envelope=envelope).stdout
    return json.loads(out) if out.strip() else {}


def answer(reply: dict[str, object] | str, **extra: object) -> dict[str, object]:
    text = reply if isinstance(reply, str) else "```json\n" + json.dumps(reply) + "\n```"
    out = cli("record", envelope={"hook_event_name": "SubagentStop", "agent_type": "reader", "agent_id": "a1", "last_assistant_message": text, **extra}).stdout
    return json.loads(out) if out.strip() else {}


def ask(task: str = "071-sketch", rel: str = REL) -> str:
    done = cli("request", task, "--record", rel)
    return done.stdout.rsplit("READER_REQUEST ", 1)[-1].strip() if done.returncode == 0 else ""


try:
    print("request: a sketch record only, then the one launch line")
    done = cli("request", "071-sketch", "--record", "README.md")
    check("negative — a file that is not a sketch record is refused", done.returncode == 1 and "neither a sketch record" in done.stderr, done.stderr)
    done = cli("request", "071-sketch", "--record", ".engine/sketches/none.md")
    check("negative — a record that does not exist is refused", done.returncode == 1, done.stderr)

    print("guard: the reader starts only with the line, and starts nothing itself")
    said = launch("READER_REQUEST 20261010T000000Z-abcdef")
    check("negative — no request pending: refused", '"permissionDecision": "deny"' in json.dumps(said) and "No reader request is pending" in str(said), said)
    rid = ask()
    check("the request prints the launch line and names the record", bool(rid) and json.loads((root / f".claude/state/reader/requests/{rid}/request.json").read_text())["record"] == REL, rid)
    said = launch(f"READER_REQUEST {rid}\nPlease be kind: the author worked hard.")
    check("negative — anything added to the line is refused", "exactly this prompt" in str(said), said)
    said = launch("Read .engine/sketches/rate.md")
    check("negative — a prompt without the line is refused", "exactly this prompt" in str(said), said)
    check("the exact line starts it", launch(f"READER_REQUEST {rid}") == {})
    check("another agent is not this guard's business", launch("anything", agent="general-purpose") == {})
    said = launch("whatever", agent="general-purpose", inside="reader")
    check("negative — the reader itself starts no agent", "starting another agent is refused" in str(said), said)

    print("record: the verdict from the agent's answer")
    said = answer("I think it is fine.")
    check("an answer without JSON goes back to the agent once", said.get("decision") == "block" and "VERDICT REFUSED" in str(said.get("reason")), said)
    said = answer({"verdict": "MAYBE", "reason": "x", "evidence": []})
    check("…the second that does not fit is INVALID, and the request is spent", said == {} and reader.rows(root)[-1]["verdict"] == "INVALID"
          and reader.pending(root) is None, reader.rows(root)[-1:])
    rid = ask()
    launch(f"READER_REQUEST {rid}")
    (root / REL).write_text(RECORD + "\n(дописано під час читання)\n", encoding="utf-8")
    answer(GOOD)
    check("negative — the record changed while it was read: INVALID, no PASS", reader.rows(root)[-1]["verdict"] == "INVALID"
          and "changed while it was read" in reader.rows(root)[-1]["reason"] and not reader.passed(root, REL), reader.rows(root)[-1])
    (root / REL).write_text(RECORD, encoding="utf-8")
    rid = ask()
    launch(f"READER_REQUEST {rid}")
    transcript = root / "agent.jsonl"
    transcript.write_text(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "h1", "name": "SubagentHandback", "input": {"message": "```json\n" + json.dumps(GOOD) + "\n```"}}]}}) + "\n")
    answer("", agent_transcript_path=str(transcript), last_assistant_message="")
    row = reader.rows(root)[-1]
    check("a PASS handed back through SubagentHandback is recorded, with the record's content when it was read",
          row["verdict"] == "PASS" and row["record"] == REL and row["record_sha256"] == reader.digest(root / REL) and row["task"] == "071-sketch", row)
    journal = (root / ".engine/reader/ledger.md").read_text(encoding="utf-8")
    check("…and in the journal, written by the script", f"— 071-sketch — READER_PASS\n- Record: {REL}" in journal, journal[-400:])
    check("passed(): the record as it is has a PASS", reader.passed(root, REL))
    (root / REL).write_text(RECORD.replace("так", "ні"), encoding="utf-8")
    check("negative — passed(): not for a record changed after its PASS", not reader.passed(root, REL))
    check("negative — a SubagentStop of another agent records nothing", cli("record", envelope={"hook_event_name": "SubagentStop", "agent_type": "overseer",
                                                                                             "last_assistant_message": json.dumps(GOOD)}).stdout == "")

    print("three BLOCKs in a row on one record: the runner's marker")
    block = {"verdict": "BLOCK", "reason": "the output stops at call 40; the answer claims a cut at 61", "evidence": [".engine/sketches/rate.md:8"]}
    marker = root / ".claude/state/board/reader-blocks-072-sketch.json"
    for n in (1, 2):
        launch(f"READER_REQUEST {ask('072-sketch')}")
        answer(block)
    check("negative — two BLOCKs: no marker yet; each new request counts its attempt", not marker.exists()
          and json.loads((root / f".claude/state/reader/requests/{ask('072-sketch')}/request.json").read_text())["attempt"] == 3)
    launch(f"READER_REQUEST {(reader.pending(root) or {}).get('id')}")
    answer(block)
    left = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else {}
    check("the third BLOCK leaves the marker: the task, the record, the three verdicts", left.get("task") == "072-sketch" and left.get("record") == REL
          and len(left.get("blocks", [])) == 3, left)
    marker.unlink()
    launch(f"READER_REQUEST {ask('072-sketch')}")
    answer(GOOD)
    for n in (1, 2):
        launch(f"READER_REQUEST {ask('072-sketch')}")
        answer(block)
    check("negative — a PASS between them resets the count: two BLOCKs after it leave no marker", not marker.exists())
    launch(f"READER_REQUEST {ask('072-sketch')}")
    answer(block)
    check("…the third leaves the marker, and a PARK row restarts the count", marker.exists() and reader.rows(root)[-1]["verdict"] == "PARK")
    marker.unlink()   # the owner answered: the runner starts the task afresh and removes the marker
    for n in (1, 2):
        launch(f"READER_REQUEST {ask('072-sketch')}")
        answer(block)
    check("negative — after the park, two BLOCKs leave no marker: the record has three readings again, as the park question says",
          not marker.exists() and json.loads((root / f".claude/state/reader/requests/{ask('072-sketch')}/request.json").read_text())["attempt"] == 3)
    launch(f"READER_REQUEST {(reader.pending(root) or {}).get('id')}")
    answer(block)
    check("…the third after the park parks it again", marker.exists())
finally:
    shutil.rmtree(root, ignore_errors=True)

# ------------------------------------------------------------------ a task's report (board 100)
print("a task's report: the package names the documents the task changed, and the PASS holds only while they stand")
root = Path(tempfile.mkdtemp(prefix="reader-doc-")).resolve()   # cli() and reader.rows() read this global
REPORT = "tasks/done/090-design/report.md"
DOC_PASS = {"verdict": "PASS", "reason": "the references say what the report ascribes to them; every item has its answer",
            "evidence": ["docs/design.md:1 — the decision the report quotes"]}


def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write(rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def package(rid: str) -> dict[str, Any]:
    asked: dict[str, Any] = json.loads((root / f".claude/state/reader/requests/{rid}/request.json").read_text(encoding="utf-8"))
    return asked


try:
    git("init", "-q", "-b", "unattended/work")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    write(".gitignore", ".claude/state/\n")
    write("docs/old.md", "what was there before the task\n")
    git("add", "-A")
    git("commit", "-qm", "the project")
    write("tasks/doing/090-design.md", "# 090 — проєкт\n\n## Що зробити\n- проєкт рішення\n\n## Питання до власника\n")
    git("add", "-A")
    git("commit", "-qm", "board: 090-design → doing")
    write("docs/design.md", "Рішення: один файл.\n")
    write("tasks/ANOMALIES.md", "# Журнал аномалій\n")
    git("add", "-A")
    git("commit", "-qm", "the design")
    done = cli("request", "090-design", "--report")
    check("negative — no report yet: refused", done.returncode == 1 and "neither a sketch record" in done.stderr, done.stderr)
    write(REPORT, "# Звіт\n\n## Що змінилось для власника\n- проєкт у docs/design.md\n")
    write("docs/notes.md", "ще не закомічено\n")
    done = cli("request", "091-other", "--record", REPORT)
    check("negative — the report of another task is refused", done.returncode == 1 and "is not the report of the task 091-other" in done.stderr, done.stderr)
    done = cli("request", "092-nowhere", "--record", "tasks/done/092-nowhere/report.md")
    check("negative — a task that is in neither doing/ nor done/ has no report to read", done.returncode == 1, done.stderr)
    rid = ask("090-design", REPORT)
    asked = package(rid)
    check("the package: the kind, the task file, the four questions, the task's commits", asked.get("kind") == "document"
          and asked.get("task_file") == "tasks/doing/090-design.md" and len(asked.get("questions", [])) == 4
          and [c["subject"] for c in asked["commits"]] == ["the design"], asked)
    check("…and every document the task changed, committed or not — never the report itself, the board's moves or a journal",
          sorted(asked["files"]) == ["docs/design.md", "docs/notes.md"], asked.get("files"))
    launch(f"READER_REQUEST {rid}")
    write("docs/design.md", "Рішення: два файли.\n")
    answer(DOC_PASS)
    check("negative — a document of the package changed while the report was read: INVALID, no PASS",
          reader.rows(root)[-1]["verdict"] == "INVALID" and "docs/design.md changed while the report" in reader.rows(root)[-1]["reason"]
          and not reader.passed(root, REPORT), reader.rows(root)[-1])
    launch(f"READER_REQUEST {ask('090-design', REPORT)}")
    answer(DOC_PASS)
    check("a PASS on the report and its documents as they are", reader.rows(root)[-1]["verdict"] == "PASS"
          and reader.passed(root, REPORT, ["docs/design.md", "docs/notes.md"]), reader.rows(root)[-1])
    check("…in the journal under the task and the report's path", f"— 090-design — READER_PASS\n- Record: {REPORT}" in
          (root / ".engine/reader/ledger.md").read_text(encoding="utf-8"))
    check("negative — passed(): a document the task changed that the reader never got", not reader.passed(root, REPORT, ["docs/design.md", "docs/late.md"]))
    write("docs/notes.md", "переписано після PASS\n")
    check("negative — passed(): not once a document changed after the PASS", not reader.passed(root, REPORT, ["docs/design.md"]))
    write("docs/notes.md", "ще не закомічено\n")
    write(REPORT, "# Звіт\n\nпереписано після PASS\n")
    check("negative — passed(): not once the report changed after the PASS", not reader.passed(root, REPORT))
    marker = root / ".claude/state/board/reader-blocks-090-design.json"
    for n in (1, 2, 3):
        launch(f"READER_REQUEST {ask('090-design', REPORT)}")
        answer({"verdict": "BLOCK", "reason": "docs/design.md:1 says one file, the report says two", "evidence": ["docs/design.md:1 — «один файл»"]})
    left = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else {}
    check("three BLOCKs in a row on a report leave the runner's marker too", left.get("record") == REPORT and len(left.get("blocks", [])) == 3, left)
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
