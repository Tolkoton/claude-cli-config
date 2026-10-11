#!/usr/bin/env python3
"""The fresh reader of a sketch's record (board 099): reader.py request, guard, record.

  - `request` takes only a sketch record of the project and prints the one launch line;
  - `guard`: the reader starts with exactly `READER_REQUEST <id>` of the pending request and nothing
    else; with no request, or with any other prompt, it is refused; the reader starts no agent;
  - `record` writes the verdict from the agent's answer — never the author: the row with the record's
    content when it was read, the journal entry; an answer that does not fit goes back once, then is
    INVALID; a record that changed while it was read is INVALID; the answer handed back through
    SubagentHandback (no last_assistant_message) is read too;
  - `passed()` holds only for the record as it is now;
  - three BLOCKs in a row on one record leave the marker the runner parks the task on; a PASS between
    them resets the count.

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
    check("negative — a file that is not a sketch record is refused", done.returncode == 1 and "is not a sketch record" in done.stderr, done.stderr)
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

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
