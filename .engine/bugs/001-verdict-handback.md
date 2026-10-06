# Bug 001-verdict-handback

type: bugfix
status: fixed
<!-- status: recorded → reproduced → fixed; or parked (not reproduced in three attempts);
     or question for the owner (the expected behaviour is written nowhere); or became a slice.
     This file is the contract of the fix and its report at once: the overseer audits against it.
     Sections 1–4 are written before the fix exists. -->

## 1. Record
- Symptom: «наглядача для юніта 1 запущено тричі (запит 20261004T224257Z-02b9cc); у тексті він відповів PASS, PASS і BLOCK #4, але жоден вердикт не потрапив у .engine/overseer/ledger.md» (tasks/doing/705-open-item-076-1.md). The Stop hook then parked the unit: "got no valid verdict in 3 requests: the agent left no verdict". Seen again on 045 (request 20261005T224756Z-098e23, question 711) and in the sandbox of 044 (task 706).
- Expected: the JSON object the overseer agent answers with is checked by `overseer_verdict.py record` and written as an entry of `.engine/overseer/ledger.md` and a row of `.claude/state/overseer/verdicts.jsonl`.
- Where the expected is written: `.claude/hooks/overseer_verdict.py:28-35` ("RECORD. The agent answers with one JSON object. This script — never a model — checks it against the schema … and then writes the entry into .engine/overseer/ledger.md and a row into .claude/state/overseer/verdicts.jsonl"); `.claude/engine-rules.md`, Overseer protocol ("`overseer_verdict.py` writes the ledger from the agent's answer").
- Actual: `record` refuses a valid answer with "VERDICT REFUSED — the answer does not fit the schema: - the answer holds no JSON object". The agent has already handed its answer back and gets no further turn, so nothing is recorded; after three requests the unit is parked.
- Where it was seen: this server, Claude Code 2.1.289, board tasks 076 (2026-10-04) and 045 (2026-10-05), reported by the agent in tasks/ANOMALIES.md. All six overseer transcripts (`~/.claude/projects/-home-lao-engine/{0293a03d…,2f65e1ae…}/subagents/agent-*.jsonl`) end the same way: an assistant `tool_use` `SubagentHandback` whose `message` is the valid JSON verdict, its tool result "Report delivered to your caller.", then a `hook_blocking_error` attachment from `overseer_verdict.py record` with the text above.

## 2. Reproduction
Three attempts, each a different way. Reproduced — stop at that attempt. Not reproduced after
the third — the status becomes `parked`, nothing below is filled in and no code is changed.

### Attempt 1
- Command: in a fresh temporary git repository: `overseer_verdict.py request --turn-file turn.md`, then `guard` with the printed launch line, then
  `echo '{"hook_event_name":"SubagentStop","agent_type":"overseer","agent_id":"a8800a0f5cc9b90f4","agent_transcript_path":"<the transcript of the first overseer of 076>"}' | python3 .claude/hooks/overseer_verdict.py record; python3 .claude/hooks/overseer_verdict.py status`
  — the envelope has the keys Claude Code 2.1.289 really sends for an agent that used a tool (`tasks/done/044-simplifier-live-check/evidence/subagentstop-probe.json`: no `last_assistant_message`); the transcript is the real one, whose last assistant record is `SubagentHandback` with a PASS.
- Output:
  ```
  {"decision": "block", "reason": "VERDICT REFUSED — the answer does not fit the schema:\n- the answer holds no JSON object\nAnswer again with the ONE JSON object and nothing else (…)"}
  wired in settings: yes
  pending request:   20261006T020056Z-134ea5 (asked 1, launched 1)
  ```
  The same text as the `hook_blocking_error` in the live transcripts; no verdict row.
- Result: reproduced

### Attempt 2
Not needed: attempt 1 reproduced.

### Attempt 3
Not needed.

## 3. Failing test
- Test: `tests/test_overseer_fresh.py`, section «the answer handed back through SubagentHandback (board 705 / 706)» — the case "a verdict handed back by SubagentHandback is recorded" (and "the LAST handback is the answer"), at the level of the hook's command: `overseer_verdict.py record` fed the envelope Claude Code sends, with a transcript of the live shape. Three negative cases beside it pass on both sides: a handback without JSON is refused, no message and no transcript is refused, an envelope that carries the message is judged by the message.
- Command that runs it: `python3 tests/test_overseer_fresh.py`
- It fails with: `FAIL a verdict handed back by SubagentHandback is recorded (seen live: three valid answers, no verdict, the unit parked)   [VERDICT REFUSED — the answer does not fit the schema: - the answer holds no JSON object …` and `FAIL the LAST handback is the answer   [[]]` — the symptom of section 1; every other check of the suite is `ok`.
- Tests written first to pin the present behaviour around the code (only when no test could reach it): none — the suite already reaches `record`.

## 4. Cause
Written before the fix.
- Where it showed: `.claude/hooks/overseer_verdict.py:602` — `parse_reply(str(envelope.get("last_assistant_message") or ""))` gets an empty string and reports "the answer holds no JSON object"; `record` answers `decision: block` (line 607).
- Why it happened: `record` assumes the agent's reply always arrives in the envelope's `last_assistant_message` (premise П2 of board 015, probed on 2.1.288 with an agent that called no tool). An agent that called a tool before answering — the overseer always does — returns its reply through the tool call `SubagentHandback(message=…)`; its SubagentStop envelope then has no `last_assistant_message` at all, and the reply exists only in the file `agent_transcript_path` names (`tasks/done/044-simplifier-live-check/evidence/subagentstop-probe.json`; the six live transcripts of 076 and 045). The refusal cannot be answered either: after the handback the agent gets no further turn, so the "second answer is recorded INVALID" branch never runs, no row is written, and `overseer_stop.py:635` resets `schema_errors` at each re-ask — three asks, "the agent left no verdict", parked.
- Same places: `grep -rn last_assistant_message` over `*.py *.sh *.md *.json` and `grep -rn SubagentStop` over `.claude docs engine.py`, plus both settings files. One reader of a subagent's answer exists: `overseer_verdict.py:602` (one `SubagentStop` handler in `.claude/settings.json` and in `docs/tasks/settings.json`). `overseer_stop.py:662,706` read the MAIN session's Stop envelope, where the field is present (both live requests were made from it) — not the same cause. Critics, business-analyst and simplifier have no recording hook: their answers reach the caller as the Agent tool's result. Nothing else to fix; task 706 is this same bug.

## 5. Fix
- What changed: `.claude/hooks/overseer_verdict.py` — `record` takes the reply from the envelope's `last_assistant_message` and, when that is empty, from the `message` of the last `SubagentHandback` call in the file `agent_transcript_path` names (a private helper `_handed_back`, +20 lines). `tests/test_overseer_fresh.py` — the five cases of section 3.
- Checked against the live data: the reproduction of section 2, run again with the fix, reads the real answer of the first overseer of 076 (it is then refused only because the temporary repository lacks the files that answer cites: "evidence cites `tasks/doing/076-maintain-build.md:33`, and there is no such file").
- Budget: `complexity_budget.py check` → within budget: 0 new files, +20 lines, 0 new public symbols, 0 new abstractions, 0 new dependencies.
- Nothing else: no tidying on the way, no renaming, no new helper for later.

The budget below is the ready small budget of a bug fix. The 40 is a signal, not a ceiling —
going over any line calls the simplifier; when it does not find the excess justified, this
stops being a bug fix and becomes a slice through `/plan-slice`. The numbers are not edited.

## Complexity budget
base_commit: 5b4156d55cb2a4e1f4edfc7d88d4a3996b3f3541
max_new_files: 0
max_net_new_lines: 40
max_new_public_symbols: 0
max_new_abstractions: 0
max_new_dependencies: 0
justification: none

## 6. Proof
Continued under board task 706 (2026-10-06): task 705 was parked by the runner before the gate; its uncommitted work was restored from `wip/705-open-item-076-1/20261006T020844Z`, the docstring's task reference became «705 / 706», and the proof was run again on the restored tree — the same first line, `PROVED: tests/test_overseer_fresh.py fails on 5b4156d and passes on the working tree; the failure shows «FAIL a verdict handed back by SubagentHandback is recorded»`. The output below is the first run's.
The command and the whole output of `python3 .claude/hooks/bugfix.py prove …`, pasted. `REFUSED` is not a proof.

Command: `python3 .claude/hooks/bugfix.py prove --record .engine/bugs/001-verdict-handback.md --test tests/test_overseer_fresh.py --cmd "python3 tests/test_overseer_fresh.py" --expect "FAIL a verdict handed back by SubagentHandback is recorded"`

````
PROVED: tests/test_overseer_fresh.py fails on 5b4156d and passes on the working tree; the failure shows «FAIL a verdict handed back by SubagentHandback is recorded»
  command: python3 tests/test_overseer_fresh.py
  the fix: .claude/hooks/overseer_verdict.py, .engine/bugs/001-verdict-handback.md
  before the fix: exit 1
    |   ok   a session that only TYPES a request (seen live, a small model) is told the real steps, once
    |   ok   negative — a message that only mentions the word inside a sentence is left alone
    |   ok   an answer without a pending request records nothing
    |   ok   another agent's answer is not a verdict
    | 
    | == the answer handed back through SubagentHandback (board 705 / 706)
    |   FAIL a verdict handed back by SubagentHandback is recorded (seen live: three valid answers, no verdict, the unit parked)   [VERDICT REFUSED — the answer does not fit the schema:
    | - the answer holds no JSON object
    | Answer again with the ONE JSON object and nothing else (verdict, check, reason, evidence, category; devils_advocate, adr or escalation where they apply). A second answer that does not fit is recorded INVALID and ]
    |   FAIL the LAST handback is the answer   [[]]
    |   ok   negative — a handback that holds no JSON object is refused as before
    |   ok   negative — no message and no transcript: refused, nothing recorded
    |   ok   negative — where the envelope carries the message, the message is the answer and the transcript is not read
    | 
    | FAIL (2): a verdict handed back by SubagentHandback is recorded (seen live: three valid answers, no verdict, the unit parked); the LAST handback is the answer
  with the fix: exit 0
    |   ok   the verdict is in the ledger; the Stop hook adds nothing (the report is the human's)
    |   ok   negative — not wired: `request` refuses instead of leaving a request nobody records
    |   ok   a session that only TYPES a request (seen live, a small model) is told the real steps, once
    |   ok   negative — a message that only mentions the word inside a sentence is left alone
    |   ok   an answer without a pending request records nothing
    |   ok   another agent's answer is not a verdict
    | 
    | == the answer handed back through SubagentHandback (board 705 / 706)
    |   ok   a verdict handed back by SubagentHandback is recorded (seen live: three valid answers, no verdict, the unit parked)
    |   ok   the LAST handback is the answer
    |   ok   negative — a handback that holds no JSON object is refused as before
    |   ok   negative — no message and no transcript: refused, nothing recorded
    |   ok   negative — where the envelope carries the message, the message is the answer and the transcript is not read
    | 
    | PASS: the fresh-context overseer protocol holds, every protection with its negative case
````

## 7. Gate and overseer
- Gate: all 70 suites `tests/test_*.py` exit 0 (2026-10-06, each run as `python3 tests/test_….py` in two loops of 35: the one-command `bash tests/run_all.sh` was twice cut off with the session — `tests/test_board_runner.py` alone took 847 s here; so no machine record `tests-full.json` from this run).
- Overseer: PASS — request 20261006T024303Z-69c5aa, the entry of 2026-10-06T02:46:36Z in `.engine/overseer/ledger.md`. This is also the live check of the fix: that overseer called twelve tools and handed its answer back through `SubagentHandback`, and `record` wrote the verdict at the first request. It reproduced the proof and read all six live transcripts of 076 and 045 through `_handed_back` (PASS, PASS, BLOCK, PASS, PASS, BLOCK). Its devil's advocate, kept: the fixture's other tool call carries no `message` key, so a helper that ignored the tool name would pass the suite (the helper does check the name). Closed under board 705 (2026-10-06): the case «negative — another tool's `message` is not the answer: only SubagentHandback is read» puts a later `SendMessage` call carrying a BLOCK after the handback of a PASS; with the name check removed from `_handed_back` (a temporary copy) that case alone goes red.
- The regression test stays in the suite: `tests/test_overseer_fresh.py`, section «the answer handed back through SubagentHandback (board 705 / 706)» (run by `bash tests/run_all.sh`; not in the fast subset — board 018 keeps this 13-second suite out of it).

## 8. Lesson
Why was this not caught earlier — one of: a test was missing | the contract was wrong | a rule was missing | external.
- Answer: a test was missing — the SubagentStop envelope was probed (board 015, premise П2) only with an agent that called no tool, so the shape every real overseer produces (the reply handed back through `SubagentHandback`, no `last_assistant_message`) was never put before `record`.
- Queued: `#34d4ada7 added`
