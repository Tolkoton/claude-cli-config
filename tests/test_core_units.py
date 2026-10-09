#!/usr/bin/env python3
"""Unit-level pins on the engine's critical code, found by mutation testing (board 085).

A mutation run (cosmic-ray through uvx, on a throwaway copy) changed one operator, constant or
condition at a time in gate.py, overseer_verdict.py, overseer_stop.py, board.py, engine.py and
lesson_queue.py and ran the suites that execute the changed line. Every case here is a mutant
that stayed green: the line was executed by a suite, and no check noticed it had changed. The
cases call the functions in-process — no model, no network, no hook started — so the whole
file takes about a second.

Run:   python3 tests/test_core_units.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Any

from hook_env import hook_env, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:600]}")


def load(rel: str) -> Any:
    """The module at `rel`, imported under a name of its own (its directory importable, as when run)."""
    path = ROOT / rel
    name = "core_units_" + path.stem
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def raises(kind: type[BaseException], call: Callable[[], object]) -> bool:
    """`call` raised `kind`. Anything else it raises is left to end the suite red."""
    try:
        call()
    except kind:
        return True
    return False


def run_main_argv(module: Any, argv: list[str]) -> int:
    """The module's main(argv), its output swallowed."""
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return int(module.main(argv))


def scratch() -> Path:
    """A fresh empty directory, removed when the suite exits."""
    return Path(sandbox_dir("core-units-"))


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, capture_output=True,
                          text=True, check=True, env=hook_env(repo)).stdout.strip()


def root_from(module: Any, where: Path) -> Path:
    """The module's project_root() as seen from `where`, with CLAUDE_PROJECT_DIR unset."""
    here, inherited = Path.cwd(), os.environ.pop("CLAUDE_PROJECT_DIR", None)
    os.chdir(where)
    try:
        return Path(module.project_root()).resolve()
    finally:
        os.chdir(here)
        if inherited is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = inherited


# --- engine.py ---------------------------------------------------------------------------


def engine_lock(engine: Any) -> None:
    text = engine.render_lock("v1 — «тег»", "c0ffee", {"b": "2", "a": "1"}, ["s"])
    data = json.loads(text)
    check("the lock is written with schema 1 — the number every lock on disk already carries", data["schema"] == 1, data)
    check("...indented by two spaces, non-ASCII as written", '\n  "schema": 1' in text and "«тег»" in text, text)
    project = scratch()
    (project / ".claude").mkdir()
    lock = project / engine.LOCK
    lock.write_text(text, encoding="utf-8")
    check("...and read back", engine.read_lock(project).files == {"a": "1", "b": "2"})
    lock.write_text(json.dumps({**data, "schema": 2}), encoding="utf-8")
    check("a lock of another schema is refused, not half-read", raises(engine.EngineError, lambda: engine.read_lock(project)))
    lock.write_text(json.dumps({"schema": 1, "files": {}}), encoding="utf-8")
    check("a lock with a key missing is an engine error with the way out, not a traceback",
          raises(engine.EngineError, lambda: engine.read_lock(project)))
    shutil.rmtree(project)


def engine_supervisor(engine: Any) -> None:
    project = scratch()
    beat = project / ".claude/state/unattended/heartbeat"
    beat.parent.mkdir(parents=True)
    beat.write_text("x")
    check("a fresh heartbeat in the state directory is seen when the old path has none",
          "heartbeat" in (engine.supervisor_live(project) or ""), engine.supervisor_live(project))
    old = time.time() - 900.5
    os.utime(beat, (old, old))
    check("a heartbeat 900 s old is no longer a live supervisor", engine.supervisor_live(project) is None, engine.supervisor_live(project))
    shutil.rmtree(project)


def engine_migration_pairs(engine: Any) -> None:
    project = scratch()
    old = project / "old"
    (old / "a-dir.md").mkdir(parents=True)
    (old / "a-file.md").write_text("x")
    (old / "a-link.md").symlink_to(old / "a-file.md")
    pairs = engine.migration_pairs(project, "old/*.md", "new/")
    check("a glob entry of the migration table moves regular files only — no directory, no symlink",
          pairs == [("old/a-file.md", "new/a-file.md")], pairs)
    shutil.rmtree(project)


def engine_duplicated_runs(engine: Any) -> None:
    runs = engine.duplicated_runs("# Mine\nA\nB\nC\n", ["A\nB\nC\n"])
    check("a duplicated run is labelled by its own first line, never by the project's line above it", runs == [(2, 4, "A")], runs)
    runs = engine.duplicated_runs("# Mine\nintro\n# Theirs\nB\nC\n", ["# Theirs\nB\nC\n"])
    check("...and by its own heading when it has one", runs == [(3, 5, "# Theirs")], runs)
    runs = engine.duplicated_runs("A\nB\nC\nmine\nA\nB\n", ["A\nB\nC\n"])
    check("a second run starts its count from nothing: two lines after a run of three are not a run", runs == [(1, 3, "A")], runs)
    runs = engine.duplicated_runs("A\nB\nmine\n", ["A\nB\nC\n"])
    check("...and neither are two lines at the top of the file", runs == [], runs)
    glob = engine.compile_pattern("docs/**.md")
    check("`**` in a pattern consumes exactly its two characters", bool(glob.match("docs/a/b.md")) and not glob.match("docs/xmd"))
    begin, end = engine.MD_BLOCK_BEGIN, engine.MD_BLOCK_END
    blocks = [engine.marked_block(lines) for lines in ([begin, "x", end], [begin, "x"], ["x", end], [end, begin])]
    check("the engine's block in a markdown file needs both markers, in order", blocks == [(0, 2), None, None, None], blocks)
    seed = f"{begin}\nnew\n{end}\n"
    check("...and a file without the block takes nothing from the seed",
          engine.with_block_from("mine\n", seed) is None and engine.with_block_from(f"mine\n{begin}\nold\n{end}\n", seed) == f"mine\n{seed}")
    check("engine.py without a command is a usage error", raises(SystemExit, lambda: run_main_argv(engine, [])))
    refused = [raises(engine.EngineError, partial(engine.compile_pattern, pattern)) for pattern in ("/abs", "!not", "a\\b")]
    check("an ownership pattern with a leading '/', a '!' or a backslash is refused, each on its own", refused == [True, True, True], refused)


def engine_source_read(engine: Any) -> None:
    repo = scratch()
    git(repo, "init", "-q")
    (repo / "f.txt").write_text("hello\n")
    git(repo, "add", "f.txt")
    git(repo, "commit", "-qm", "init")
    src = engine.EngineSource(repo)
    blob, tree = git(repo, "rev-parse", "HEAD:f.txt"), git(repo, "rev-parse", "HEAD^{tree}")
    check("a blob is read by its id", src.read({blob}) == {blob: b"hello\n"})
    check("an object that is not a blob is refused", raises(engine.EngineError, lambda: src.read({tree})))
    check("with no v* tag and no --ref there is nothing to install, and the error says so",
          raises(engine.EngineError, lambda: engine.default_ref(src, None)) and engine.default_ref(src, "main") == "main")
    git(repo, "tag", "v1.2.3")
    check("...and with a tag the newest one is the default", engine.default_ref(src, None) == "v1.2.3", engine.default_ref(src, None))
    shutil.rmtree(repo)


def engine_personal(engine: Any) -> None:
    home = scratch()
    target = home / "settings.json"
    plan = engine.PersonalPlan(target, {})
    check("a new plan of the personal layer has counted nothing as unchanged", plan.unchanged == 0)
    merged = engine.merge_into({"same": 1, "other": 2}, {"same": 1, "other": 3}, plan)
    check("a key that already has the layer's value is counted once and is no action",
          plan.unchanged == 1 and [a.path for a in plan.actions] == ["other"] and merged == {"same": 1, "other": 3}, (plan, merged))

    class Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Frozen:
            return cls(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)

    real = engine.datetime
    engine.datetime = Frozen
    try:
        plan = engine.PersonalPlan(target, {"мова": "українська", "n": {"k": 1}})
        check("the first write of the home settings makes no backup", engine.apply_personal(plan) is None)
        text = target.read_text(encoding="utf-8")
        check("...writes non-ASCII as it is, indented by two spaces", '"мова": "українська"' in text and '\n  "n": {\n    "k": 1' in text, text)
        first = engine.apply_personal(plan)
        second = engine.apply_personal(plan)
        third = engine.apply_personal(plan)
        names = [p.name for p in (first, second, third) if p is not None]
        stamp = engine.BACKUP_PREFIX + "20261007T120000Z"
        check("backups made within one second get -1, -2 after the stamp and overwrite nothing",
              names == [stamp, stamp + "-1", stamp + "-2"], names)
    finally:
        engine.datetime = real
    shutil.rmtree(home)


def engine_symlinks(engine: Any) -> None:
    project = scratch()
    git(project, "init", "-q")
    (project / "elsewhere.md").write_text("the project's own\n")
    for path in (".claude/engine-rules.md", engine.PROPOSAL):
        (project / path).parent.mkdir(parents=True, exist_ok=True)
        (project / path).symlink_to(project / "elsewhere.md")
    plan = engine.plan_sync(engine.EngineSource.here(), "HEAD", project, False, set())
    kept = [(a.verb, a.detail) for a in plan.actions if a.path == ".claude/engine-rules.md"]
    check("a symlink to a file where an engine file goes is kept as not a regular file, never read or written through",
          len(kept) == 1 and kept[0][0] == "keep" and "not a regular file" in kept[0][1], kept)
    touched = [a.verb for a in plan.actions if a.path == engine.PROPOSAL] + [n for n in plan.notes if engine.PROPOSAL in n]
    check("...and a settings proposal that is a symlink is neither followed nor commented on", touched == [], touched)
    shutil.rmtree(project)


def engine_cases() -> None:
    print("engine.py")
    engine = load("engine.py")
    engine_lock(engine)
    engine_supervisor(engine)
    engine_migration_pairs(engine)
    engine_duplicated_runs(engine)
    engine_source_read(engine)
    engine_personal(engine)
    engine_symlinks(engine)


# --- gate.py -----------------------------------------------------------------------------

TI = "# type" + ": ignore"   # built, never written whole: this file is itself clean under the guard


def gate_small(gate: Any) -> None:
    check("a gate-allow reason needs twelve characters and two words",
          gate.valid_reason("abcdefghij k") and not gate.valid_reason("abcdefghi k") and not gate.valid_reason("abcdefghijklmnop"))
    names = {rel: gate.is_test_file(rel) for rel in ("tests/test_x.py", "pkg/x_test.py", "pkg/x.py", "tests/test_x.txt")}
    check("a test file is test_*.py or *_test.py", list(names.values()) == [True, True, False, False], names)
    env = gate.parse_env_text('A=x # note\nB="q # kept"\nC=plain\nD="open\n')
    check("project.env: a comment after an unquoted value is dropped, inside quotes it is the value; a lone quote is no quoting",
          env == {"A": "x", "B": "q # kept", "C": "plain", "D": '"open'}, env)
    check("a config file that cannot be read justifies nothing", gate.config_justified(None, None) is False)
    report = gate.Report("stop", ROOT)
    check("the gate's report carries schema 1, the number its readers know", report.as_json("pass")["schema"] == 1)
    gate.guard_python("broken.py", f"x = = 1  {TI}\n", None, {}, report)
    found = [(f.rule, f.severity) for f in report.findings]
    check("a Python file that does not parse still has its suppression comments judged",
          len(found) == 1 and found[0][0].startswith("bypass/") and found[0][1] == "block", found)


def gate_root_and_order(gate: Any) -> None:
    repo = scratch().resolve()
    git(repo, "init", "-q")
    (repo / "sub").mkdir()
    (repo / "notes.txt").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    check("without CLAUDE_PROJECT_DIR the project is the top of the git work tree, not the directory one stands in",
          root_from(gate, repo / "sub") == repo, root_from(gate, repo / "sub"))
    (repo / "notes.txt").write_text("y\n")
    (repo / "z.py").write_text(f"x = 1  {TI}\n")
    git(repo, "add", "-A")
    report = gate.Report("stop", repo)
    gate.bypass_guard(repo, "stop", ["notes.txt", "z.py"], None, report)
    files = [f.file for f in report.findings if f.severity == "block"]
    check("a file the bypass guard does not read does not end the pass over the files after it", files == ["z.py"], report.findings)
    shutil.rmtree(repo)


def gate_crash(gate: Any) -> None:
    import contextlib
    import io

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    root = scratch()
    saved = gate.run_layer, gate.project_root, gate.read_envelope
    gate.run_layer, gate.project_root, gate.read_envelope = boom, lambda: root, dict
    try:
        with contextlib.redirect_stderr(io.StringIO()) as err:
            crashed = gate.main(["--layer", "pre_commit"])
            advisory = gate.main(["--layer", "post_write"])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            hooked = gate.main(["--layer", "stop", "--hook"])
    finally:
        gate.run_layer, gate.project_root, gate.read_envelope = saved
    said = json.loads(out.getvalue() or "{}")
    check("a Stop hook that crashes blocks the turn through the hook protocol: exit 0 with a block decision",
          hooked == 0 and said.get("decision") == "block" and "crashed" in said.get("reason", ""), (hooked, out.getvalue()))
    check("a gate that crashes at a blocking layer exits 2 and says so — a crash never reads as a pass",
          crashed == 2 and "gate.py crashed: RuntimeError: boom" in err.getvalue(), (crashed, err.getvalue()))
    check("...and at post_write, which only advises, exits 0", advisory == 0, advisory)
    shutil.rmtree(root)


def gate_counter(gate: Any) -> None:
    root = scratch()
    gate.write_count(root, "s", 2)
    result, _ = gate.finish_stop(gate.Report("stop", root), root, "s")
    check("a Stop gate that passes resets the session's count of blocks to zero, not to one",
          result == "pass" and gate.read_count(root, "s") == 0, (result, gate.read_count(root, "s")))
    shutil.rmtree(root)


def gate_cases() -> None:
    print("gate.py")
    gate = load(".claude/hooks/gate.py")
    gate_small(gate)
    gate_root_and_order(gate)
    gate_crash(gate)
    gate_counter(gate)


# --- board.py ----------------------------------------------------------------------------


def run_main(module: Any, *argv: str) -> int:
    """The module's main() with this argv, its output swallowed."""
    import contextlib
    import io

    saved = sys.argv
    sys.argv = [str(module.__file__), *argv]
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return int(module.main())
    except SystemExit as stop:
        return int(stop.code or 0)
    finally:
        sys.argv = saved


def board_cases() -> None:
    print("board.py")
    board = load(".claude/unattended/board.py")
    task = board.parse("# 010\n\nАудит потрібен: так\nПлатні прогони: так, до 0,5 долара\n")
    check("board 078: an old «Платні прогони:» line is ignored, the audit line read as ever", task.audit and not hasattr(task, "paid"), task)
    root = scratch()
    for folder in ("todo", "doing", "blocked", "done"):
        (root / "tasks" / folder).mkdir(parents=True)
    check("`gate-answers` on a board with nothing answered exits 0", run_main(board, "--root", str(root), "gate-answers") == 0)
    (root / "tasks" / "todo" / "010-x.md").write_text("# 010\n")
    check("`where` exits 0 for a task it found", run_main(board, "--root", str(root), "where", "010-x") == 0)
    check("`open-item` without --what is a usage error",
          run_main(board, "--root", str(root), "open-item", "--to", "todo", "--title", "t") == 2)
    check("...and without --title", run_main(board, "--root", str(root), "open-item", "--to", "todo", "--what", "w") == 2)
    quiet = {command: run_main(board, "--root", str(root), command) for command in ("gate-closed", "maintain-task", "cleanup-task")}
    check("`gate-closed`, `maintain-task` and `cleanup-task` with nothing to do exit 0 in a project without project.env",
          set(quiet.values()) == {0}, quiet)
    two = root / "tasks" / "blocked" / "020-two.md"
    two.write_text("# 020 — two\n\nЗалежить від: —\nАудит потрібен: ні\n\n## Питання до власника\n"
                   f"1. Перше?\n   Дія runner-а: apply-settings {'a' * 64}\n   Відповідь:\n"
                   f"2. Друге?\n   Дія runner-а: amend-goals {'b' * 64}\n   Відповідь:\n", encoding="utf-8")
    task = board.read(two)
    check("a task that offers two actions offers the last one", (task.action, task.action_arg) == ("amend-goals", "b" * 64), (task.action, task.action_arg))
    offered = root / board.ACTION_FILES["apply-settings"]
    check("`action-line` without the file it offers is refused",
          run_main(board, "--root", str(root), "action-line", "apply-settings") == board.EXIT_REFUSED)
    offered.parent.mkdir(parents=True)
    offered.write_text("{}\n")
    check("...and with it exits 0", run_main(board, "--root", str(root), "action-line", "apply-settings") == 0)
    shutil.rmtree(root)


# --- overseer_verdict.py -----------------------------------------------------------------


def verdict_transcript(verdict: Any) -> None:
    check("a transcript that cannot be read is a turn without tool calls", verdict.turn_events("/nonexistent/core-units.jsonl") == [])
    folder = scratch()
    calls = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tool, "name": tool, "input": {"command": "x"}}]}}
             for tool in ("first", "second")]
    transcript = folder / "t.jsonl"
    transcript.write_text("".join(json.dumps(r) + "\n" for r in calls), encoding="utf-8")
    tools = [e["tool"] for e in verdict.turn_events(str(transcript))]
    check("a transcript with no user message yet is one turn from its first record", tools == ["first", "second"], tools)
    shutil.rmtree(folder)


def verdict_ledger(verdict: Any) -> None:
    root = scratch()
    ledger = root / verdict.LEDGER_REL
    ledger.parent.mkdir(parents=True)
    rows = [("s", "PASS"), ("other", "BLOCK"), ("s", "PASS"), ("s", "BLOCK"), ("s", "PASS")]
    ledger.write_text("".join(f"## 2026-10-0{9 - i}T10:00:00Z — {name} — {what}\n\nbody\n\n" for i, (name, what) in enumerate(rows)), encoding="utf-8")
    check("PASS entries in a row stop at the slice's first other verdict; another slice's entries do not count",
          verdict.passes_in_a_row(root, "s") == 2, verdict.passes_in_a_row(root, "s"))
    git(root, "init", "-q")
    (root / "sub").mkdir()
    (root / "a").write_text("x\n")
    check("without CLAUDE_PROJECT_DIR the verdict script finds the top of the work tree too", root_from(verdict, root / "sub") == root.resolve())
    files = (verdict.tree_fingerprint(root) or {}).get("files", {})
    check("the tree's fingerprint lists a changed file whose name is one character", "a" in files, files)
    errors = verdict.schema_errors(root, {"verdict": "PASS", "reason": "fine", "evidence": []}, {})
    check("a verdict with an empty evidence list is refused", any("evidence" in e for e in errors), errors)
    shutil.rmtree(root)


def verdict_settle(verdict: Any) -> None:
    seen: list[str] = []
    allows: Any = ModuleType("gate_allows")
    lessons: Any = ModuleType("lesson_queue")
    allows.record_pass = lambda root: seen.append("record_pass")
    allows.drop_request = lambda root: seen.append("drop_request")
    lessons.add_from_verdict = lambda root, text: seen.append("lesson")
    saved = {name: sys.modules.get(name) for name in ("gate_allows", "lesson_queue")}
    sys.modules.update(gate_allows=allows, lesson_queue=lessons)
    try:
        told = {}
        for what, origin in (("PASS", "hook"), ("PASS", "manual"), ("BLOCK", "hook"), ("BLOCK", "manual")):
            seen.clear()
            verdict.settle(ROOT, {"verdict": what, "origin": origin, "reason": "r", "check": 1})
            told[f"{what}/{origin}"] = list(seen)
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    check("only the hook's own PASS confirms the gate-allow request; the hook's other verdict drops it; every BLOCK is a lesson",
          told == {"PASS/hook": ["record_pass"], "PASS/manual": [], "BLOCK/hook": ["drop_request", "lesson"], "BLOCK/manual": ["lesson"]}, told)


def verdict_schema(verdict: Any) -> None:
    def wrong(obj: dict[str, Any], request: dict[str, Any] | None = None) -> bool:
        return bool(verdict.schema_errors(ROOT, {"reason": "one line", "evidence": ["ran the suite: green"], **obj}, request or {}))

    blocks = {n: wrong({"verdict": "BLOCK", "check": n}) for n in (0, 1, 12, 13)}
    check("a BLOCK names a check from 1 to 12, both ends included", blocks == {0: True, 1: False, 12: False, 13: True}, blocks)
    tired = {"passes_in_a_row": verdict.PASSES_FOR_ADVOCATE}
    check("after three PASS verdicts in a row the devil's advocate paragraph is required: forty characters are enough, thirty-nine are not",
          not wrong({"verdict": "PASS", "devils_advocate": "x" * 40}, tired) and wrong({"verdict": "PASS", "devils_advocate": "x" * 39}, tired)
          and not wrong({"verdict": "PASS"}))
    check("an empty reason and a blank evidence line are refused",
          wrong({"verdict": "PASS", "reason": ""}) and wrong({"verdict": "PASS", "evidence": [" "]}) and not wrong({"verdict": "PASS"}))
    check("an answer whose braces hold no JSON is a problem to hand back, not a crash", verdict.parse_reply("{not json}")[0] is None)
    print_one = {"head": "a", "files": {"f": "M:1"}}
    check("a fingerprint that could not be taken on either side compares as nothing changed",
          verdict.fingerprint_diff(None, print_one) == [] and verdict.fingerprint_diff(print_one, None) == []
          and verdict.fingerprint_diff(print_one, {"head": "b", "files": {}}) == ["HEAD", "f"])
    shown = verdict.render_evidence([{"tool": "Edit", "input": {}, "result": None, "is_error": False}], True)
    check("the evidence numbers the turn's tool calls from 1 and shows `?` for an edit without a path", "\n1. Edit `?`" in shown, shown)
    launches = [verdict.launches_overseer({"tool": tool, "input": {"subagent_type": kind}})
                for tool, kind in (("Agent", "overseer"), ("Task", "overseer"), ("Agent", "Explore"), ("Bash", "overseer"))]
    check("only an Agent or Task call for the overseer counts as launching it", launches == [True, True, False, False], launches)
    check("an ESCALATE without its question is refused, with it accepted",
          wrong({"verdict": "ESCALATE"}) and wrong({"verdict": "ESCALATE", "escalation": {"category": "c"}})
          and not wrong({"verdict": "ESCALATE", "escalation": {"question": "which one?"}}))


def verdict_cases() -> None:
    print("overseer_verdict.py")
    verdict = load(".claude/hooks/overseer_verdict.py")
    verdict_transcript(verdict)
    verdict_ledger(verdict)
    verdict_settle(verdict)
    verdict_schema(verdict)


# --- overseer_stop.py --------------------------------------------------------------------


def stop_cases() -> None:
    import contextlib
    import io

    print("overseer_stop.py")
    stop = load(".claude/hooks/overseer_stop.py")
    with contextlib.redirect_stderr(io.StringIO()) as err:
        dirs = stop._build_source_dirs({"SOURCE_DIRS": "src, lib/"})
    check("SOURCE_DIRS that parse are taken without a warning", dirs == ["src/", "lib/"] and err.getvalue() == "", (dirs, err.getvalue()))
    with contextlib.redirect_stderr(io.StringIO()) as err:
        dirs = stop._build_source_dirs({"SOURCE_DIRS": "/"})
    check("SOURCE_DIRS that parse into nothing are treated as unset, and the warning says so", dirs == [] and "SOURCE_DIRS" in err.getvalue(), (dirs, err.getvalue()))
    with contextlib.redirect_stderr(io.StringIO()) as err:
        own = stop._build_check_cmd_re({"CHECK_CMDS": "vitest, nx"})
        broad = stop._build_check_cmd_re({})
    check("CHECK_CMDS replaces the built-in check commands, without a warning; unset, the built-in ones stand",
          bool(own.search("npx vitest run")) and not own.search("pytest -q") and bool(broad.search("pytest -q")) and err.getvalue() == "",
          (own.pattern, err.getvalue()))
    engine = stop._build_check_cmd_re(stop._load_project_env(ROOT))
    check("this repository's own runner counts as a verification run: `bash tests/run_all.sh` asks for the audit (board 723)",
          bool(engine.search("bash tests/run_all.sh --fast 2>&1 | tail -1")) and bool(engine.search("python3 -m pytest -q")), engine.pattern)
    check("NEGATIVE — a command that only names the tests is no verification run", not engine.search("git add tests/test_cleanup.py"), engine.pattern)
    code: object = None
    with contextlib.redirect_stdout(io.StringIO()) as out:
        try:
            stop._emit_halt("enough")
        except SystemExit as halt:
            code = halt.code
    check("a halt is `continue: false` with exit 0 — a non-zero exit would be read as a hook error, not a stop",
          code == 0 and json.loads(out.getvalue()) == {"continue": False, "stopReason": "enough"}, (code, out.getvalue()))
    repo = scratch().resolve()
    git(repo, "init", "-q")
    (repo / "sub").mkdir()
    here, inherited = Path.cwd(), os.environ.pop("CLAUDE_PROJECT_DIR", None)
    os.chdir(repo / "sub")
    try:
        found = stop._get_project_dir()
    finally:
        os.chdir(here)
        if inherited is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = inherited
    check("without CLAUDE_PROJECT_DIR the Stop hook finds the top of the work tree", found == repo, found)
    shutil.rmtree(repo)


# --- lesson_queue.py ---------------------------------------------------------------------


def lessons_cases() -> None:
    import re

    print("lesson_queue.py")
    lessons = load(".claude/hooks/lesson_queue.py")
    bodies = [body for _, body in lessons.blocks("## a\nA\n## b\nB\n## c\nC\n", re.compile(r"^## \w$", re.MULTILINE))]
    check("every block of a record file ends where the next heading begins, the one before the last too", bodies == ["\nA\n", "\nB\n", "\nC\n"], bodies)
    root = scratch()
    record = root / ".engine/overseer/escalations.md"
    record.parent.mkdir(parents=True)
    record.write_text("# Escalations\n\n## 2026-10-07T10:00:00Z — ESCALATE — Which store\n\n- Decision: the file one\n\n"
                      "## 2026-10-07T11:00:00Z — ESCALATE — Closed one\n\n- Status: CLOSED\n", encoding="utf-8")
    added = lessons.collect_escalations(root, "s")
    essences = [e["essence"] for e in lessons.entries(root)]
    digest = lessons.digest(root)
    check("a digest under the limit is shown whole, with no ellipsis", digest.startswith("## lessons") and not digest.endswith("…"), digest)
    check("an open escalation becomes one lesson candidate that carries its decision; a closed one becomes none",
          added == 1 and len(essences) == 1 and essences[0].endswith("Which store: the file one"), (added, essences))
    shutil.rmtree(root)
    root = scratch()
    chain = ["CLAUDE.md", "a.md", "b.md", "c.md", "d.md", "e.md", "f.md"]
    for name, following in zip(chain, [*chain[1:], ""]):
        (root / name).write_text(f"one line of {name}\n" + (f"@{following}\n" if following else ""), encoding="utf-8")
    check("the persistent context is CLAUDE.md and its imports four hops deep, no further", lessons.context_lines(root) == 10, lessons.context_lines(root))
    shutil.rmtree(root)
    root = scratch()
    (root / "CLAUDE.md").write_text("top\n@a.md\n", encoding="utf-8")
    (root / "a.md").write_text("a\n@CLAUDE.md\n@missing.md\n", encoding="utf-8")
    check("a file that imports its importer is counted once", lessons.context_lines(root) == 5, lessons.context_lines(root))
    (root / ".engine").mkdir()
    (root / ".engine/PROGRESS.md").write_text("- done: slice `old-one`\n- IN PROGRESS: slice `alpha-1`, behaviour 2\n", encoding="utf-8")
    check("the current slice is the name on the IN PROGRESS line, without the word before it", lessons.current_slice(root) == "alpha-1", lessons.current_slice(root))
    note = root / "notes.md"
    note.write_text("a", encoding="utf-8")
    lessons.append(note, "b\n")
    lessons.append(note, "c\n")
    check("appending to a record adds the missing final newline and no empty line", note.read_text(encoding="utf-8") == "a\nb\nc\n", note.read_text(encoding="utf-8"))
    check("rejecting a proposal that does not exist is a refusal, and so is asking the owner about it",
          lessons.reject(root, "999", "no")[0] is False and lessons.ask_owner(root, "999")[0] is False)
    said = [lessons.note_failure(root, "pytest: 1 failed"), lessons.note_failure(root, "pytest: 1 failed")]
    lessons.note_success(root)
    said.append(lessons.note_failure(root, "pytest: 1 failed"))
    check("a success between two failures starts the count of identical failures again", said == ["", "", ""], said)
    said = [lessons.note_failure(root, "pytest: 1 failed"), lessons.note_failure(root, "pytest: 1 failed")]
    check("...and the third identical failure in a row is answered with the stuck protocol", said[0] == "" and "pytest" in said[1], said)
    check("lesson_queue.py without a command is a usage error", raises(SystemExit, lambda: run_main_argv(lessons, [])))
    shutil.rmtree(root)
    failure = lessons.tool_failure_text({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "make"},
                                         "tool_response": {"stderr": "boom happened", "exit_code": 1}})
    check("a failed command with nothing but stderr is remembered by its stderr", "boom happened" in (failure or ""), failure)
    failure = lessons.tool_failure_text({"hook_event_name": "PostToolUseFailure", "tool_name": "Edit", "tool_input": {"file_path": "src/x.py"}, "error": "no match"})
    check("...and a failed edit by the file it was for", "src/x.py" in (failure or "") and "no match" in (failure or ""), failure)


def costs_cases() -> None:
    """board 106: what every UTC day cost, from the runner's own records (board_state.py)."""
    print("board_state.py: the days")
    state = load(".claude/unattended/board_state.py")
    from datetime import date

    tasks = {
        "010-a": {"cost_usd": 3.0, "attempts": [
            {"utc": "2026-10-08T23:50:00Z", "session_id": "s1", "reported_usd": 1.0},
            {"utc": "2026-10-09T00:10:00Z", "session_id": "s1", "reported_usd": 2.5},   # the same conversation, continued: 1.5 more
            {"utc": "2026-10-09T01:00:00Z", "session_id": "s2", "reported_usd": 0.5}]},
        "011-old": {"cost_usd": 2.0, "attempts": [{"session_id": "s9", "reported_usd": 2.0}]},   # a record older than the time field
        "012-long-ago": {"cost_usd": 4.0, "attempts": [{"utc": "2026-09-01T10:00:00Z", "session_id": "s3", "reported_usd": 4.0}]},
    }
    lines = state.daily(tasks, date(2026, 10, 9))
    check("the day in progress first, then the seven before it, each by its date", [line.split(" (")[0] for line in lines[:8]]
          == [f"доба 2026-10-{d:02d}" for d in range(9, 1, -1)] and lines[0].startswith("доба 2026-10-09 (UTC, триває)"), lines)
    check("a continued conversation costs what its total grew by, on the day it grew: 1.50 + 0.50 today, 1.00 yesterday",
          "доба 2026-10-09 (UTC, триває): 2.00 USD" in lines and "доба 2026-10-08 (UTC): 1.00 USD" in lines, lines)
    check("NEGATIVE — a day with nothing spent is shown as zero, not left out", "доба 2026-10-05 (UTC): 0.00 USD" in lines, lines)
    check("NEGATIVE — an attempt with no time is a line of its own, never put on a day", lines[-1] == "без часу запису (старий запис), не приписано жодній добі: 2.00 USD"
          and sum(float(line.split(": ")[1].split()[0]) for line in lines[:8]) == 3.0, lines)
    check("what was spent before the eight days is said, so the lines add up to the tasks' costs",
          "раніше за 2026-10-02: 4.00 USD" in lines and round(sum(float(line.rsplit(": ", 1)[1].split()[0]) for line in lines), 2)
          == sum(t["cost_usd"] for t in tasks.values()), lines)
    ahead = state.daily({"013-ahead": {"attempts": [{"utc": "2026-10-11T00:00:00Z", "session_id": "s4", "reported_usd": 0.25}]}}, date(2026, 10, 9))
    check("NEGATIVE — an attempt dated after today (a clock that was ahead) is said, not lost", ahead[-1] == "пізніше за 2026-10-09 (годинник ішов уперед?): 0.25 USD", ahead)
    edge = state.daily({"015-edge": {"attempts": [{"utc": "2026-10-02T23:59:59Z", "session_id": "s6", "reported_usd": 0.75}]}}, date(2026, 10, 9))
    check("NEGATIVE — the oldest of the eight days keeps what it cost: none of it is said again as «earlier»",
          edge[7] == "доба 2026-10-02 (UTC): 0.75 USD" and len(edge) == 8, edge)
    check("no spending at all: eight zero days and nothing else", state.daily({}, date(2026, 10, 9)) == [
          f"доба 2026-10-{d:02d} (UTC{', триває' if d == 9 else ''}): 0.00 USD" for d in range(9, 1, -1)])
    report = state.report({"tasks": tasks, "total_cost_usd": 9.0}, date(2026, 10, 9))
    day_line = "доба 2026-10-09 (UTC, триває): 2.00 USD"
    check("the runner's report carries the days after the total", "total: 9.00 USD" in report and day_line in report
          and report.index("total: 9.00 USD") < report.index(day_line), report)
    box = scratch()   # the runner writes its summary with `board_state.py <dir> report`
    (box / "costs.json").write_text(json.dumps({"tasks": tasks, "total_cost_usd": 9.0}), encoding="utf-8")
    said = subprocess.run([sys.executable, str(ROOT / ".claude/unattended/board_state.py"), str(box), "report"], capture_output=True,
                          text=True, check=False, env={**os.environ, "BOARD_TODAY": "2030-01-02"})   # far from any real today
    check("`board_state.py report` takes the day in progress from BOARD_TODAY, as the runner's other day-bound steps do",
          said.returncode == 0 and "доба 2030-01-02 (UTC, триває): 0.00 USD" in said.stdout.splitlines()
          and "раніше за 2029-12-26: 7.00 USD" in said.stdout.splitlines(), said.stdout + said.stderr)
    dipped = [{"utc": "2026-10-09T01:00:00Z", "session_id": "s5", "reported_usd": v} for v in (1.0, 2.5, 2.0, 3.0)]
    check("NEGATIVE — a conversation whose figure dipped and rose again: the day counts its highest figure once, as the task's cost does",
          state.daily({"014-dip": {"attempts": dipped}}, date(2026, 10, 9))[0] == "доба 2026-10-09 (UTC, триває): 3.00 USD" and state.cost_of(dipped) == 3.0,
          state.daily({"014-dip": {"attempts": dipped}}, date(2026, 10, 9))[0])


def extra_cases() -> None:
    """board 078: every extra session of Claude is booked to the task in hand and shown with it."""
    print("board_state.py: the extra sessions (board 078)")
    state = load(".claude/unattended/board_state.py")
    box = scratch()
    tasks_dir = box / "tasks"
    for column in ("todo", "doing", "blocked", "done"):
        (tasks_dir / column).mkdir(parents=True)
    (tasks_dir / "doing" / "078-a.md").write_text("# 078\n\nАудит потрібен: ні\n", encoding="utf-8")
    books = box / "books"
    saved = os.environ.get("BOARD_STATE_DIR")
    os.environ["BOARD_STATE_DIR"] = str(books)
    try:
        state.book_extra(tasks_dir, "run_simplifier_evals", 0.5)
        state.book_extra(tasks_dir, "run_tester_evals", 0.25)
        (tasks_dir / "doing" / "079-b.md").write_text("# 079\n", encoding="utf-8")
        state.book_extra(tasks_dir, "run_manager_evals", 1.0)   # two tasks of this side in doing/: nobody's
        state.book_extra(box / "no-such-board", "run_analyst_evals", 2.0)   # no board at all: by hand
    finally:
        if saved is None:
            os.environ.pop("BOARD_STATE_DIR", None)
        else:
            os.environ["BOARD_STATE_DIR"] = saved
    rows = [json.loads(line) for line in (books / state.EXTRA_FILE).read_text(encoding="utf-8").splitlines()]
    check("each session is one line: the time, the task in hand, the tool, what it cost",
          [(r["task"], r["tool"], r["cost_usd"]) for r in rows] == [("078-a", "run_simplifier_evals", 0.5), ("078-a", "run_tester_evals", 0.25),
                                                                   ("", "run_manager_evals", 1.0), ("", "run_analyst_evals", 2.0)]
          and all(r["utc"].endswith("Z") for r in rows), rows)
    extra = state.extra_sessions(books)
    check("they add up per task; sessions with no task in hand are kept apart", extra == {"078-a": (2, 0.75), "": (2, 3.0)}, extra)
    saved = os.environ.pop("BOARD_STATE_DIR", None)
    try:
        (tasks_dir / "doing" / "079-b.md").unlink()
        state.book_extra(tasks_dir, "run_audit_scenarios", 0.2)
        check("NEGATIVE — with no project's .claude/ beside the board (a fixture), nothing is booked and no .claude/ is made",
              not (box / ".claude").exists())
        (box / ".claude").mkdir()
        state.book_extra(tasks_dir, "run_audit_scenarios", 0.2)
        beside = box / ".claude" / "state" / "board" / state.EXTRA_FILE
        check("…with one, the session is booked in its .claude/state/board/",
              beside.is_file() and json.loads(beside.read_text(encoding="utf-8"))["task"] == "078-a", beside)
    finally:
        if saved is not None:
            os.environ["BOARD_STATE_DIR"] = saved
    (books / state.EXTRA_FILE).open("a", encoding="utf-8").write("not json\n")
    check("NEGATIVE — a broken line is stepped over, the sums stand", state.extra_sessions(books) == extra)
    report = state.report({"tasks": {"078-a": {"cost_usd": 4.0, "attempts": [{}], "outcome": "done"}}, "total_cost_usd": 4.0},
                          extra=extra | {"080-owner": (1, 0.1)})
    check("the runner's summary shows each task's extra sessions after its own cost",
          "078-a: 4.00 USD, 1 attempt(s), done, додаткових сесій Claude: 2 (0.75 USD)" in report, report)
    check("…a task the runner never ran (a session with the owner) and the sessions started by hand on lines of their own",
          "080-owner: додаткових сесій Claude: 1 (0.10 USD) (сесія з власником)" in report
          and "без задачі (запуск руками): додаткових сесій Claude: 2 (3.00 USD)" in report, report)
    check("NEGATIVE — a task with no extra session says nothing of them",
          not any("додаткових" in line for line in state.report({"tasks": {"001-x": {"cost_usd": 1.0}}, "total_cost_usd": 1.0})), "")
    (books / "costs.json").write_text(json.dumps({"tasks": {"078-a": {"cost_usd": 4.0, "attempts": []}}, "total_cost_usd": 4.0}), encoding="utf-8")
    said = subprocess.run([sys.executable, str(ROOT / ".claude/unattended/board_state.py"), str(books), "report"],
                          capture_output=True, text=True, check=False)
    check("`board_state.py <dir> report` reads the books beside costs.json", said.returncode == 0 and "додаткових сесій Claude: 2 (0.75 USD)" in said.stdout,
          said.stdout + said.stderr)
    sys.path.insert(0, str(ROOT / ".claude/unattended"))
    review = load(".claude/unattended/board_review.py")
    state_root = box / "state"
    (state_root / "board").mkdir(parents=True)
    (state_root / "board" / state.EXTRA_FILE).write_text((books / state.EXTRA_FILE).read_text(encoding="utf-8"), encoding="utf-8")
    costs = review.task_costs(state_root)
    check("the review takes the extra sessions into each task's costs", costs.get("078-a", {}).get("extra") == (2, 0.75), costs)
    check("…and says them in the owner's words", review.extra_line(costs["078-a"]) == " Додаткових сесій Claude (evals, виміри): 2, $0.75.", review.extra_line(costs["078-a"]))
    check("NEGATIVE — no extra session, no words", review.extra_line({"cost_usd": 1.0}) == "")


def main() -> int:
    costs_cases()
    extra_cases()
    engine_cases()
    gate_cases()
    board_cases()
    verdict_cases()
    stop_cases()
    lessons_cases()
    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
