#!/usr/bin/env python3
"""Board 083: what the task board's own history says about running tasks in parallel.

    python3 .engine/artifacts/083-parallel/measure.py [branch]

Reads git history and .claude/state/board/costs.json; writes nothing in this repository (the
replay runs in a scratch clone under the system temp directory, removed at the end). Free: no
model is called. Three measurements:

  (the unit is a STRETCH of work: from a `→ doing` commit to the next closing commit of that task)
  overlap   how many pairs of neighbouring tasks changed a common file
  replay    each task merged as if it had started 1, 2 or 3 tasks earlier (a real three-way
            merge): clean, conflict in append-only journals only, conflict in other files
  schedule  a scheduler with K agents over the same tasks, with their real durations and the
            files they really changed (an oracle footprint: the best case for the overlap rule)
"""
import collections
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

BRANCH = sys.argv[1] if len(sys.argv) > 1 else "unattended/work"
ROOT = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
# What only the runner's home checkout would write (design, section 4): never a conflict of a task branch.
BOARD_MOVE = re.compile(r"^tasks/((todo|doing|blocked|done)/|\.first$|ANOMALIES\.md$)")
# The append-only journals that travel with the branch and that merge=union (board 739) is meant to cure.
JOURNAL = re.compile(r"^(\.engine/lesson-queue\.md|\.engine/overseer/(ledger|escalations|parked)\.md)$")
NOT_WORK = re.compile(r"^(tasks/|\.engine/lesson-queue\.md|\.engine/overseer/|\.engine/PROGRESS\.md|\.engine/artifacts/|\.engine/rule-proposals\.md)")


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)


def ranges():
    """Every STRETCH of work: a `→ doing` commit and the NEXT `→ done|blocked` commit of the same
    task, in the order they closed. A task that was blocked and taken again gives several stretches
    (`053-name`, `053-name#2`), each with its own files and its own time."""
    start, end, order, minutes, open_at, seen = {}, {}, [], {}, {}, collections.Counter()
    for line in git("log", "--reverse", "--format=%H\t%ct\t%s", BRANCH).stdout.splitlines():
        sha, when, subject = line.split("\t", 2)
        move = re.match(r"board: (\S+) → (doing|done|blocked)", subject)
        if not move:
            continue
        task, column = move.groups()
        if column == "doing":
            open_at[task] = (sha, int(when))
        elif task in open_at:
            seen[task] += 1
            unit = task if seen[task] == 1 else f"{task}#{seen[task]}"
            start[unit], begun = open_at.pop(task)
            end[unit] = sha
            minutes[unit] = (int(when) - begun) / 60
            order.append(unit)
    return start, end, order, minutes


def pct(part, whole):
    return f"{part} ({part * 100 // max(whole, 1)}%)"


def overlap(order, files):
    print("\n== overlap: neighbouring tasks that changed a common file (journals and board moves left out)")
    for window in (2, 3, 4):
        pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:i + window]]
        common = sum(1 for a, b in pairs if files[a] & files[b])
        print(f"   within {window - 1} task(s) of each other: pairs {len(pairs)}, with a common file {pct(common, len(pairs))}")


def replay(start, end, order):
    print("\n== replay: task B merged as if it had started N tasks earlier")
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="board083-"))
    try:
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(scratch)], check=True)
        for back in (1, 2, 3):
            clean = journal_only = other = 0
            hot, journals = collections.Counter(), collections.Counter()
            total = 0
            for i in range(back, len(order)):
                a, b = order[i - back], order[i]
                if git("checkout", "-q", "-f", "--detach", start[a], cwd=scratch).returncode:
                    continue
                git("clean", "-qfd", cwd=scratch)
                merged = git("merge-recursive", start[b], "--", start[a], end[b], cwd=scratch)
                total += 1
                unmerged = [f for f in git("diff", "--name-only", "--diff-filter=U", cwd=scratch).stdout.split()
                            if not BOARD_MOVE.match(f)]
                journals.update(f for f in unmerged if JOURNAL.match(f))
                if merged.returncode not in (0, 1):
                    total -= 1  # the merge itself failed: not a result
                elif not unmerged:
                    clean += 1
                elif all(JOURNAL.match(f) for f in unmerged):
                    journal_only += 1
                else:
                    other += 1
                    hot.update(f for f in unmerged if not JOURNAL.match(f))
            print(f"   N={back}: tasks {total}, clean {pct(clean, total)}, journals only {pct(journal_only, total)}, "
                  f"other files {pct(other, total)}")
            print("        most often: " + ", ".join(f"{name} ×{n}" for name, n in hot.most_common(6)))
            print("        journals:   " + ", ".join(f"{name} ×{n}" for name, n in journals.most_common(4)))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def schedule(order, files, minutes):
    costs_file = ROOT / ".claude/state/board/costs.json"
    usd = 0.0
    if costs_file.is_file():
        usd = sum(r.get("cost_usd", 0) for r in json.loads(costs_file.read_text(encoding="utf-8"))["tasks"].values())
    tasks = []
    for unit in order:
        name, _, again = unit.partition("#")
        depends = set()
        for path in [ROOT / "tasks/done" / name / "task.md", ROOT / "tasks/blocked" / f"{name}.md"]:
            line = re.search(r"^Залежить від:(.*)$", path.read_text(encoding="utf-8"), re.M) if path.is_file() else None
            if line:
                depends = {n for n in re.findall(r"\d+", line.group(1))}
        if again:  # a later stretch of a task waits for the one before it
            depends.add(name if again == "2" else f"{name}#{int(again) - 1}")
        tasks.append({"number": unit, "short": name[:3], "minutes": minutes[unit], "files": files[unit], "depends": depends})
    total = sum(t["minutes"] for t in tasks)
    durations = sorted(t["minutes"] for t in tasks)
    print(f"\n== schedule: {len(tasks)} stretches of work, one at a time {total / 60:.1f} h, median {durations[len(durations) // 2]:.0f} min"
          + (f"; the board's costs.json: {usd:.2f} USD" if usd else ""))
    last = {}  # a dependency on a number is on the LAST stretch of that task
    for t in tasks:
        last[t["short"]] = t["number"]
    for t in tasks:
        t["depends"] = {last.get(n, n) for n in t["depends"]} - {t["number"]}
    known = {t["number"] for t in tasks}

    def run(agents, window, overlap_rule):
        waiting, working, now, finished = list(tasks), [], 0.0, set()
        while waiting or working:
            started = True
            while started and len(working) < agents:
                started = False
                for task in waiting[:window]:
                    if any(n in known and n not in finished for n in task["depends"]):
                        continue
                    if overlap_rule and any(task["files"] & other["files"] for _, other in working):
                        continue
                    working.append((now + task["minutes"], task))
                    waiting.remove(task)
                    started = True
                    break
            if not working:
                break
            working.sort(key=lambda pair: pair[0])
            now, task = working.pop(0)
            finished.add(task["number"])
        return now

    for agents in (2, 3, 4):
        for window, shown in ((5, "5"), (15, "15"), (10 ** 6, "all")):
            ruled, free = run(agents, window, True), run(agents, window, False)
            print(f"   {agents} agents, queue seen {shown:>3}: with the no-overlap rule ×{total / ruled:.2f}; "
                  f"ceiling with no rule and no conflict ×{total / free:.2f}")


def main():
    start, end, order, minutes = ranges()
    files = {t: {f for f in git("diff", "--name-only", start[t], end[t]).stdout.split() if not NOT_WORK.match(f)}
             for t in order}
    print(f"branch {BRANCH}: {len(order)} stretches of work (a `→ doing` commit and the next closing one) "
          f"of {len({u.partition('#')[0] for u in order})} tasks")
    sizes = sorted(len(files[t]) for t in order)
    print(f"files changed per stretch: median {sizes[len(sizes) // 2]}, largest {sizes[-1]}")
    overlap(order, files)
    replay(start, end, order)
    schedule(order, files, minutes)


if __name__ == "__main__":
    main()
