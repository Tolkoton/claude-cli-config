#!/usr/bin/env python3
"""The journals every session adds to in a file of its own (board 739): journal.py and its writers.

The owner's answer: each session writes its entries of the overseer's ledger, the anomaly journal, the
parked log and the lesson queue into its own file, so merging branches never conflicts; the entries are
put together by time without loss, and two sessions that triaged one candidate differently are settled
by an agent, not by the script. Pinned against real throwaway repositories:

- two branches, two sessions, every journal written through its real writer: `git merge` and `git rebase`
  pass without a conflict, every entry of both is there whole — the lines entries share included, which
  `merge=union` loses — and the readers see what a single folded file gives them;
- negative: the same two branches writing the shared file the old way conflict, and so does a file
  outside the four (MEMORY.md);
- the lesson queue: a triaged candidate stays triaged through merge and fold; two different triages are a
  contradiction put on the board once, and `settle` closes it; two equal triages are none;
- `fold`: lossless, idempotent, removes only session files older than KEEP_DAYS;
- without a session file a reader gets the shared file byte for byte (nothing changes for a project
  that never wrote one);
- the session's name, `journal.py add/show/contradictions`, and board_review reading through git.

Run:   python3 tests/test_journal.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from hook_env import hook_env

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/unattended"))
import board
import board_review
import journal
import lesson_queue
import overseer_verdict

ROOT = Path(__file__).resolve().parent.parent

JOURNAL = ROOT / ".claude/hooks/journal.py"
PASS = FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:700]}")


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, capture_output=True, text=True, check=False)


@contextlib.contextmanager
def session(name: str | None) -> Iterator[None]:
    """Run the writers as one Claude Code session (CLAUDE_CODE_SESSION_ID), or as none."""
    saved = {k: os.environ.pop(k) for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID") if k in os.environ}
    if name is not None:
        os.environ["CLAUDE_CODE_SESSION_ID"] = name
    try:
        yield
    finally:
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        os.environ.update(saved)


LEDGER_HEAD = (ROOT / "templates/project/.engine/overseer/ledger.md").read_text(encoding="utf-8")
OLD_ENTRY = "## 2026-10-01T10:00:00Z — slice-s — BLOCK\n- Verdict: BLOCK\n- Auditor: overseer agent\n"   # a BLOCK: the shared file alone counts no PASS


def base() -> Path:
    """A project as it stands before the two sessions: the four shared files committed."""
    root = Path(tempfile.mkdtemp(prefix="journal-"))
    git(root, "init", "-q", "-b", "main")
    (root / ".gitignore").write_text(".claude/state/\n")
    for column in ("todo", "doing", "blocked", "done"):
        (root / "tasks" / column).mkdir(parents=True)
        (root / "tasks" / column / ".gitkeep").write_text("")
    (root / ".engine/overseer").mkdir(parents=True)
    (root / ".engine/overseer/ledger.md").write_text(LEDGER_HEAD.rstrip("\n") + "\n\n" + OLD_ENTRY)
    (root / ".engine/overseer/parked.md").write_text("# Parked items\n")
    (root / ".engine/overseer/MEMORY.md").write_text("# Memory\n")
    (root / "tasks/ANOMALIES.md").write_text(board.ANOMALIES_HEAD + "\n## 2026-10-01T09:00:00Z — task board\n- Що сталося: old\n- Що зроблено: nothing\n- Хто записав: runner\n")
    (root / ".engine/lesson-queue.md").write_text(lesson_queue.QUEUE_HEADER + "- 2026-10-01 | agent | s | the first old lesson #aaaa1111\n"
                                                  "- 2026-10-01 | agent | s | the second old lesson #bbbb2222\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    return root


def ledger_entry(stamp: str, slice_name: str, verdict: str) -> str:
    return f"## {stamp} — {slice_name} — {verdict}\n- Verdict: {verdict}\n- Request: {stamp}-r (attempt 1, hook)\n- Auditor: overseer agent\n"


def parked_entry(stamp: str, item: str) -> str:
    return f"## {stamp} — {item} — PARKED\n- Blocked on: the owner\n- Class: human-input\n- Unblocks when: the owner answers\n"


def write_session(root: Path, name: str, minute: int, resolve: tuple[str, str] | None) -> dict[str, list[str]]:
    """One session's work, through the real writers. What it wrote, per journal."""
    def stamp(second: int) -> str:
        return f"2026-10-10T07:{minute:02d}:{second:02d}Z"

    written: dict[str, list[str]] = {"ledger": [], "anomalies": [], "parked": [], "lessons": []}
    with session(name):
        for second, verdict in ((1, "BLOCK"), (2, "PASS")):
            entry = ledger_entry(stamp(second), "slice-s", verdict)
            overseer_verdict.write_ledger(root, entry)
            written["ledger"].append(entry.strip())
        path = board.anomaly(board.Board(root / "tasks"), f"0{minute}-task", f"odd thing of {name}", "worked past it")
        written["anomalies"].append(journal.split(path.read_text(encoding="utf-8"), journal.JOURNALS["anomalies"])[1][-1])
        entry = parked_entry(stamp(3), f"unit-{name}")
        journal.add(root, "parked", entry)
        written["parked"].append(entry.strip())
        ident = lesson_queue.add(root, "agent", "s", f"a lesson session {name} learned")
        written["lessons"].append(str(ident))
        if resolve:
            ok, message = lesson_queue.resolve(root, resolve[0], resolve[1], f"{name} decided {resolve[1]}", ["c1", "c2"], "")
            assert ok, message
    return written


def commit_all(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)


def two_branches() -> tuple[Path, dict[str, list[str]], dict[str, list[str]]]:
    root = base()
    git(root, "switch", "-qc", "a")
    a = write_session(root, "session-A", 1, ("aaaa1111", "discard"))
    commit_all(root, "a")
    git(root, "switch", "-q", "main")
    shutil.rmtree(root / ".claude/state", ignore_errors=True)   # another machine: its own seen ids
    git(root, "switch", "-qc", "b")
    b = write_session(root, "session-B", 2, ("bbbb2222", "discard"))
    commit_all(root, "b")
    return root, a, b


def main() -> int:
    print("without a session file: the shared file byte for byte")
    root = base()
    for name in journal.JOURNALS:
        check(f"{name}: text() is the shared file exactly", journal.text(root, name) == (root / journal.JOURNALS[name].shared).read_text())
    check("an empty project: every journal reads as empty", all(journal.text(Path(tempfile.mkdtemp()), n) == "" for n in journal.JOURNALS))

    print("the session's name")
    with session("session_01HPq/x y"):
        check("CLAUDE_CODE_SESSION_ID, made safe for a file name", journal.session_id(root) == "session_01HPq-x-y", journal.session_id(root))
    with session(None):
        first, second = journal.session_id(root), journal.session_id(root)
        today = f"{datetime.now(UTC):%Y-%m-%d}-"
        check("no session id: the date and one id per working tree, kept in machine state",
              first == second and first.startswith(today) and len(first) == len(today) + 12
              and (root / journal.SESSION_REL).read_text().strip() == first[len(today):], first)

    print("two branches, two sessions, every journal")
    root, a, b = two_branches()
    a_head = git(root, "rev-parse", "a").stdout.strip()
    git(root, "switch", "-q", "a")
    merged = git(root, "merge", "--no-edit", "b")
    check("git merge of the two branches: no conflict", merged.returncode == 0 and "CONFLICT" not in merged.stdout, merged.stdout + merged.stderr)
    for name in ("ledger", "anomalies", "parked"):
        whole = journal.text(root, name)
        check(f"{name}: every entry of both sessions is there whole, the lines they share included",
              all(entry in whole for entry in a[name] + b[name]), whole[-1500:])
    whole = journal.text(root, "ledger")
    stamps = [m.group(1) for m in journal.ENTRY_RE.finditer(whole)]
    check("ledger: newest first across the sessions' files and the shared file", stamps == sorted(stamps, reverse=True) and len(stamps) == 5, stamps)
    check("…and the old entry of the shared file is still there", OLD_ENTRY.strip() in whole)
    check("the overseer's PASS count reads the sessions' files (newest is session-B's PASS above its BLOCK; the shared file alone holds none)",
          overseer_verdict.passes_in_a_row(root, "slice-s") == 1, overseer_verdict.passes_in_a_row(root, "slice-s"))
    pending = {e["id"] for e in lesson_queue.entries(root)}
    check("lessons: both sessions' candidates wait, both triaged old ones are gone", pending == set(a["lessons"] + b["lessons"]), pending)
    rebased = Path(tempfile.mkdtemp(prefix="journal-rebase-"))
    shutil.rmtree(rebased)
    shutil.copytree(root, rebased)
    git(rebased, "switch", "-q", "b")
    replay = git(rebased, "rebase", a_head)
    check("git rebase of one branch onto the other: no conflict", replay.returncode == 0, replay.stdout + replay.stderr)
    check("…and the rebased branch reads the same journals as the merge", all(journal.text(rebased, n) == journal.text(root, n) for n in journal.JOURNALS))

    print("negative — the old way and a file outside the four still conflict")
    old = base()
    git(old, "switch", "-qc", "a")
    with (old / "tasks/ANOMALIES.md").open("a") as fh:
        fh.write("\n## 2026-10-10T07:01:00Z — 01-task\n- Що сталося: a\n- Хто записав: runner\n")
    with (old / ".engine/overseer/MEMORY.md").open("a") as fh:
        fh.write("\n## 2026-10-10 — a learned\n")
    commit_all(old, "a")
    git(old, "switch", "-qc", "b", "main")
    with (old / "tasks/ANOMALIES.md").open("a") as fh:
        fh.write("\n## 2026-10-10T07:02:00Z — 02-task\n- Що сталося: b\n- Хто записав: runner\n")
    with (old / ".engine/overseer/MEMORY.md").open("a") as fh:
        fh.write("\n## 2026-10-10 — b learned\n")
    commit_all(old, "b")
    git(old, "switch", "-q", "a")
    clash = git(old, "merge", "--no-edit", "b")
    check("both branches appending to tasks/ANOMALIES.md itself: a conflict (what board 739 removes)",
          clash.returncode != 0 and "tasks/ANOMALIES.md" in clash.stdout, clash.stdout)
    check("…and MEMORY.md, a file outside the four journals, conflicts as before", ".engine/overseer/MEMORY.md" in clash.stdout, clash.stdout)
    git(old, "merge", "--abort")

    print("fold: one file, lossless, idempotent")
    before = {n: journal.text(root, n) for n in journal.JOURNALS}
    queue_before = lesson_queue.entries(root)
    done = journal.fold(root, now=datetime.now(UTC) + timedelta(days=30))
    check("fold names what it gathered", len(done) == 4 and all("folded" in line for line in done), done)
    check("old session files are removed", not any(journal.pieces(root, n) for n in journal.JOURNALS), list((root / ".engine/journal").rglob("*.md")))
    for name in ("ledger", "anomalies", "parked"):
        check(f"{name}: the shared file now holds what the reader saw before, byte for byte",
              (root / journal.JOURNALS[name].shared).read_text() == before[name], (root / journal.JOURNALS[name].shared).read_text()[-600:])
    shared_queue = (root / ".engine/lesson-queue.md").read_text()
    check("lessons: the same queue after the fold", lesson_queue.entries(root) == queue_before)
    check("…the triaged candidates' lines are gone, their resolution lines stay",
          "#aaaa1111" in shared_queue and "the first old lesson" not in shared_queue and "resolved:discard" in shared_queue, shared_queue)
    again = {n: (root / journal.JOURNALS[n].shared).read_text() for n in journal.JOURNALS}
    journal.fold(root, now=datetime.now(UTC) + timedelta(days=30))
    check("a second fold changes nothing", all((root / journal.JOURNALS[n].shared).read_text() == again[n] for n in journal.JOURNALS))
    commit_all(root, "folded")

    recent = base()
    with session("session-R"):
        overseer_verdict.write_ledger(recent, ledger_entry(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "slice-r", "PASS"))
        lesson_queue.resolve(recent, "aaaa1111", "discard", "r decided", [], "")
    journal.fold(recent)
    check("fold keeps a session file younger than KEEP_DAYS (its session may still add to it)…",
          len(journal.pieces(recent, "ledger")) == 1 and len(journal.pieces(recent, "lessons")) == 1)
    check("…and the reader counts its entry once, though it now stands in both files",
          journal.text(recent, "ledger").count("— slice-r — PASS") == 1 and journal.text(recent, "lessons").count("resolved:discard") == 1)
    (recent / ".engine/lesson-queue.md").write_text(lesson_queue.QUEUE_HEADER + "- 2026-10-01 | agent | s | the first old lesson #aaaa1111\n")
    check("a triaged candidate whose line comes back (an older branch's copy) stays triaged: the resolution line stays",
          "aaaa1111" not in {e["id"] for e in lesson_queue.entries(recent)})
    shutil.rmtree(recent / ".claude/state", ignore_errors=True)   # a fresh clone: no seen ids on this machine
    with session("session-S"):
        again = lesson_queue.add(recent, "agent", "s", "a lesson session session-A learned")
        known = lesson_queue.item_id("agent", "a lesson session session-A learned")
        lesson_queue.close(recent, known, "discard", "triaged on another machine")
        shutil.rmtree(recent / ".claude/state", ignore_errors=True)   # …and its seen ids gone again: only the journal knows
        back = lesson_queue.add(recent, "agent", "s", "a lesson session session-A learned")
    check("a fresh clone does not queue again a candidate the journal holds as triaged (no seen ids needed)",
          again == known and back is None and known not in {e["id"] for e in lesson_queue.entries(recent)}, (again, back))

    print("the lesson queue: contradictions go to an agent")
    root = base()
    git(root, "switch", "-qc", "c")
    with session("session-C"):
        lesson_queue.resolve(root, "aaaa1111", "discard", "C saw nothing in it", [], "")
    commit_all(root, "c")
    git(root, "switch", "-qc", "d", "main")
    with session("session-D"):
        lesson_queue.resolve(root, "aaaa1111", "engine", "D sent it to the engine", [], "")
        lesson_queue.resolve(root, "bbbb2222", "discard", "D discarded it", [], "")
    commit_all(root, "d")
    git(root, "switch", "-q", "c")
    merged = git(root, "merge", "--no-edit", "d")
    found = journal.contradictions(journal.lesson_lines(root))
    check("git merge: no conflict, though both sessions triaged #aaaa1111", merged.returncode == 0, merged.stdout)
    check("the script names the contradiction and does not choose", list(found) == ["aaaa1111"] and {r["to"] for r in found["aaaa1111"]} == {"discard", "engine"}, found)
    check("…the candidate is out of the queue either way (both sessions triaged it)", "aaaa1111" not in {e["id"] for e in lesson_queue.entries(root)})
    raised = lesson_queue.raise_contradictions(root)
    task = (root / raised[0]).read_text() if raised else ""
    check("collect puts it on the board for an agent: one task in todo/ with both triages and the settle command",
          len(raised) == 1 and raised[0].startswith("tasks/todo/") and "discard" in task and "engine" in task and "settle aaaa1111" in task, raised)
    check("…once: a second collect finds the open task", lesson_queue.raise_contradictions(root) == raised)
    lesson_queue.collect(root)
    check("…and collect() itself raises nothing new", len(list((root / "tasks/todo").glob("*-open-item-*.md"))) == 1)
    cli = subprocess.run([sys.executable, str(JOURNAL), "--root", str(root), "contradictions"], capture_output=True, text=True, env=hook_env(root), check=False)
    check("journal.py contradictions: exit 1 and the candidate named", cli.returncode == 1 and "#aaaa1111" in cli.stdout, cli.stdout + cli.stderr)
    check("negative — settle without a reason is refused", lesson_queue.settle(root, "aaaa1111", "discard", " ")[0] is False)
    check("negative — settle of a candidate nobody triaged is refused", lesson_queue.settle(root, "cccc3333", "discard", "why")[0] is False)
    with session("session-E"):
        ok, message = lesson_queue.settle(root, "aaaa1111", "engine", "the engine is where it belongs")
    check("settle records the agent's decision and closes the contradiction", ok and journal.contradictions(journal.lesson_lines(root)) == {}, message)
    same = base()
    with session("session-F"):
        lesson_queue.resolve(same, "aaaa1111", "discard", "F", [], "")
    with session("session-G"):
        lesson_queue.resolve(same, "aaaa1111", "discard", "G, in other words", [], "")
    check("negative — two equal triages of one candidate are no contradiction", journal.contradictions(journal.lesson_lines(same)) == {})

    print("the lesson queue: one candidate two branches queued on different days")
    root, real_today = base(), lesson_queue.today
    ids = []
    for branch, name, day in (("h", "session-H", "2026-10-08"), ("i", "session-I", "2026-10-09")):
        git(root, "switch", "-qc", branch, "main")
        shutil.rmtree(root / ".claude/state/lessons", ignore_errors=True)   # another machine: nothing seen yet
        lesson_queue.today = lambda day=day: day
        try:
            with session(name):
                ids.append(lesson_queue.add(root, "agent", "-", "the same lesson, met on two branches"))
        finally:
            lesson_queue.today = real_today
        commit_all(root, branch)
    merged = git(root, "merge", "--no-edit", "h")
    twice = [line for line in journal.lesson_lines(root) if line.endswith(f"#{ids[0]}")]
    listed = [e["id"] for e in lesson_queue.entries(root)]
    check("both sessions queued it under one id, a day apart, and git merge meets no conflict",
          merged.returncode == 0 and ids[0] is not None and ids[0] == ids[1] and len(twice) == 2, (ids, twice, merged.stdout))
    check("the queue lists that candidate once (board 765)", listed.count(ids[0]) == 1, listed)
    check("…with the day it was first met", [e["date"] for e in lesson_queue.entries(root) if e["id"] == ids[0]] == ["2026-10-08"])
    check("…and the review request counts it once", f"{len(listed)} candidate(s)" in lesson_queue.review_request(root), lesson_queue.review_request(root)[:80])
    journal.fold(root, now=datetime.now(UTC) + timedelta(days=30))
    check("fold writes it into the shared file once", journal.read(root / ".engine/lesson-queue.md").count(f"#{ids[0]}") == 1)
    with session("session-J"):
        lesson_queue.resolve(root, ids[0], "discard", "J discarded it", [], "")
    check("one triage closes it", ids[0] not in {e["id"] for e in lesson_queue.entries(root)})

    print("the golden set watches the files the hooks write")
    shared = {j.shared for j in journal.JOURNALS.values()}
    stale = [f"{path.name}: {s['id']}" for path in sorted((ROOT / "evals/scenarios/hooks").glob("*.json"))
             for s in json.loads(path.read_text(encoding="utf-8"))["scenarios"] if s.get("check_file") in shared]
    check("no hook scenario watches a journal's shared file — no hook writes it, so `file changed: false` could never fail", stale == [], stale)

    print("the command line and board_review")
    root = base()
    env = hook_env(root, CLAUDE_CODE_SESSION_ID="session-cli")
    good = subprocess.run([sys.executable, str(JOURNAL), "--root", str(root), "add", "ledger"], input=ledger_entry("2026-10-10T08:00:00Z", "slice-c", "PASS"),
                          capture_output=True, text=True, env=env, check=False)
    check("journal.py add ledger: the entry goes into the session's own file", good.returncode == 0 and good.stdout.strip() == ".engine/journal/ledger/session-cli.md"
          and "— slice-c — PASS" in journal.text(root, "ledger"), good.stdout + good.stderr)
    bad = subprocess.run([sys.executable, str(JOURNAL), "--root", str(root), "add", "ledger"], input="- Verdict: PASS\n", capture_output=True, text=True, env=env, check=False)
    check("negative — an entry without its `## <UTC time> — ` heading is refused (exit 2), nothing written",
          bad.returncode == 2 and journal.text(root, "ledger").count("## 2026-10-10T") == 1, bad.stderr)
    try:
        journal.add(root, "ledger", "- Verdict: PASS\n")
        refused = False
    except ValueError:
        refused = True
    check("negative — journal.add refuses an entry without its heading rather than write what no reader would find", refused)
    stray_file = root / journal.PIECES_REL / "ledger" / "hand-written.md"
    now_entry = ledger_entry(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "slice-n", "PASS")
    stray_file.write_text("a note written past the format\n\n" + now_entry)   # a young file: one entry of today
    check("text a hand put in a session file past the entry format is still read, never dropped",
          "a note written past the format" in journal.text(root, "ledger"))
    journal.fold(root)   # the session file is young: it stays, and its text is now in the shared file too
    check("…after a fold that keeps its young file, that text is read exactly once",
          stray_file.is_file() and journal.text(root, "ledger").count("a note written past the format") == 1, journal.text(root, "ledger")[-400:])
    stray_file.unlink()
    fresh = base()
    (fresh / ".engine/overseer/ledger.md").write_text(LEDGER_HEAD)   # the template: no entry yet
    young = fresh / journal.PIECES_REL / "ledger" / "by-hand.md"
    young.parent.mkdir(parents=True)
    young.write_text("a note written past the format\n\n" + ledger_entry(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "slice-z", "PASS"))
    before_fold = journal.text(fresh, "ledger")
    journal.fold(fresh)
    after_fold = journal.text(fresh, "ledger")
    check("a shared ledger with no entry yet and a young session file with a note and one entry: before and after a fold, "
          "the entry and the note each once, and the PASS counted once",
          young.is_file() and [t.count("— slice-z — PASS") for t in (before_fold, after_fold)] == [1, 1]
          and [t.count("a note written past the format") for t in (before_fold, after_fold)] == [1, 1]
          and overseer_verdict.passes_in_a_row(fresh, "slice-z") == 1, after_fold[-500:])
    shown = subprocess.run([sys.executable, str(JOURNAL), "--root", str(root), "show", "ledger"], capture_output=True, text=True, env=hook_env(root), check=False)
    check("journal.py show ledger prints the journal whole", shown.stdout == journal.text(root, "ledger"))
    with session("session-review"):
        board.anomaly(board.Board(root / "tasks"), "01-x", "a fresh oddity", "noted")
    commit_all(root, "pieces")
    src = board_review.Source(root, git(root, "rev-parse", "HEAD").stdout.strip(), "main", "")
    check("board_review reads a journal whole through git (the session's file at that commit)",
          "a fresh oddity" in src.whole("anomalies") and src.whole("anomalies") == journal.text(root, "anomalies"))
    old_commit = git(root, "rev-parse", "HEAD~1").stdout.strip()
    check("…and at an older commit, without the file added since", "a fresh oddity" not in board_review.journal_at_commit(root, old_commit, "anomalies"))

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
