#!/usr/bin/env python3
"""A difference smaller than the audit's own noise is «у межах шуму», not a finding (board 058).

Until the noise was measured, `compare_audits.py` without two `--noise` files took the bound for
0: one session of three answering differently read as "better" or WORSE, and every "one scene
better" between two audits was a guess. Two full audits of one commit were recorded
(audit-task-058-noise-1.json, -2.json) and the noise is kept as a record beside the baselines.

Cases, on small result files written here (no session, no cost):
  * --measure-noise: the spread of every scene, the threshold (the largest spread), the scenes
    whose verdict varies although the match rate does not; the record is written;
  * negative: files of two commits, models, settings layers or run counts, or a partial file,
    measure nothing (exit 2, no record); a scene one run has no valid session for has no noise;
  * one session of three is the same size whichever thirds it lies between: with the noise
    measured as 2/3 against 1/3, a step from 3/3 to 2/3 is «у межах шуму». In floats it was
    not (1 − 2/3 > 2/3 − 1/3), and the comparison printed diff −0.33, noise 0.33, WORSE — the
    overseer's first BLOCK on this unit; the rates are exact fractions since;
  * a record of another environment is said to be one; a file that is no record is refused;
  * a comparison reads the record beside its --before file: a difference inside the bound is
    «у межах шуму» and fails nothing; one outside it is still WORSE / better; no difference is
    "same"; a scene still in both noise runs is bound by the threshold, as is a scene the
    record does not have;
  * negative: with `--noise-record none` the same one-session drop is WORSE, and the header says
    the noise was not measured;
  * a --must-fix scene that moved inside the noise is NOT FIXED and says why;
  * two --noise files given by hand win over the record;
  * the record of this repository: recomputed from its two source files it is the same, and
    evals/README.md states its threshold.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "evals" / "compare_audits.py"
WITHIN = "у межах шуму"
PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:700]}")


def result_file(path: Path, scenes: dict[str, list[str]], commit: str = "a" * 40, status: str = "complete",
                **other: object) -> Path:
    """A result file as run_audit_scenarios.py writes it. Every scene expects BLOCK#4; a session
    is given by its verdict ("BLOCK#4", "PASS", "BLOCK#1") or is "ERROR", a session lost to the
    tooling. `other` replaces top-level fields (model, environment, ...)."""
    rows = []
    for sid, verdicts in scenes.items():
        runs: list[dict[str, Any]] = []
        for verdict in verdicts:
            if verdict == LOST:
                runs.append({"error": "timed out after 1200 s", "cost_usd": 0.0, "sandbox": "x"})
                continue
            marker, _, number = verdict.partition("#")
            runs.append({"marker": marker, "check": int(number) if number else None, "matched": verdict == "BLOCK#4",
                         "cost_usd": 0.0, "sandbox": "x"})
        rows.append({"id": sid, "expected": {"marker": "BLOCK", "check": 4}, "runs": runs})
    data: dict[str, Any] = {"environment": "linux-test-1", "engine_ref": "HEAD", "engine_commit": commit,
                            "claude_version": "shim", "model": "default", "setting_sources": "project,local",
                            "runs_per_scenario": 3, "status": status, "total_cost_usd": 0.0, "scenarios": rows}
    path.write_text(json.dumps(data | other), encoding="utf-8")
    return path


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=ROOT, capture_output=True, text=True, check=False)


def judgements(stdout: str) -> dict[str, str]:
    rows = [line.split("|") for line in stdout.splitlines() if line.startswith("| `")]
    return {row[1].strip().strip("`"): row[-2].strip() for row in rows}


HIT, MISS, OTHER, LOST = "BLOCK#4", "PASS", "BLOCK#1", "ERROR"


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="audit-noise-"))
    try:
        # steady: 3/3 twice. shaky: 3/3 and 2/3 (spread 0.33). wrong: 0/3 twice, by two different verdicts.
        n1 = result_file(work / "n1.json", {"steady": [HIT] * 3, "shaky": [HIT] * 3, "wrong": [MISS] * 3})
        n2 = result_file(work / "n2.json", {"steady": [HIT] * 3, "shaky": [HIT, HIT, MISS], "wrong": [OTHER] * 3})
        record_path = work / "audit-noise.json"

        print("--measure-noise on two runs of one commit:")
        r = run("--measure-noise", n1, n2, "--out-record", record_path, "--out", work / "noise.md")
        check("exit 0 and the record is written", r.returncode == 0 and record_path.is_file(), f"rc={r.returncode} {r.stderr[-300:]}")
        record: dict[str, Any] = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {"scenarios": {}}
        noise = {sid: scene.get("noise") for sid, scene in record["scenarios"].items()}
        check("the spread of every scene: steady 0, shaky one session of three, wrong 0",
              noise.get("steady") == 0 and abs((noise.get("shaky") or 0) - 1 / 3) < 1e-9 and noise.get("wrong") == 0, str(noise))
        check("the threshold is the largest spread", abs(float(record.get("threshold", -1)) - 1 / 3) < 1e-9, str(record.get("threshold")))
        check("18 sessions counted, both sources named",
              record.get("sessions") == 18 and record.get("sources") == ["n1.json", "n2.json"], f"{record.get('sessions')} {record.get('sources')}")
        check("the report names the scene whose match rate moved",
              "match rate moved between the runs: `shaky`." in r.stdout, r.stdout[-900:])
        check("and the scene whose verdict varies at a match rate of 0 twice",
              "not the same in every session: `shaky`, `wrong`." in r.stdout and "vary: BLOCK#1, PASS" in r.stdout, r.stdout[-900:])
        check("a scene that never moved reads 'always'", "| `steady` | BLOCK#4 | 3/3 | 3/3 | 0.00 | always BLOCK#4 |" in r.stdout, r.stdout[:900])
        check("the report is written to --out", (work / "noise.md").is_file() and "Noise threshold: **0.33**" in (work / "noise.md").read_text(encoding="utf-8"))

        print("negative — files that are not two runs of one engine:")
        other = result_file(work / "other.json", {"steady": [HIT] * 3}, commit="b" * 40)
        r = run("--measure-noise", n1, other, "--out-record", work / "bad.json")
        check("two commits: exit 2, no record, the reason names engine_commit",
              r.returncode == 2 and not (work / "bad.json").exists() and "engine_commit" in r.stderr, f"rc={r.returncode} {r.stderr[-300:]}")
        partial = result_file(work / "partial.json", {"steady": [HIT]}, status="partial")
        r = run("--measure-noise", n1, partial, "--out-record", work / "bad.json")
        check("a partial file: exit 2, no record", r.returncode == 2 and not (work / "bad.json").exists() and "partial.json" in r.stderr,
              f"rc={r.returncode} {r.stderr[-300:]}")
        for field, value in (("model", "another"), ("setting_sources", "user,project,local"), ("runs_per_scenario", 1)):
            odd = result_file(work / "odd.json", {"steady": [HIT] * 3}, **{field: value})
            r = run("--measure-noise", n1, odd, "--out-record", work / "bad.json")
            check(f"another {field}: exit 2, no record, the reason names it",
                  r.returncode == 2 and not (work / "bad.json").exists() and field in r.stderr, f"rc={r.returncode} {r.stderr[-300:]}")
        odd = result_file(work / "odd.json", {"steady": [HIT] * 3}, environment="macos-14")
        r = run("--measure-noise", n1, odd, "--out-record", work / "bad.json")
        check("another environment: exit 2, no record, both environments named",
              r.returncode == 2 and not (work / "bad.json").exists() and "linux-test-1, macos-14" in r.stderr, f"rc={r.returncode} {r.stderr[-300:]}")
        r = run("--measure-noise", n1)
        check("one file is not a measurement", r.returncode == 2 and "two or more" in r.stderr, f"rc={r.returncode} {r.stderr[-300:]}")
        r = run("--measure-noise", n1, n2, "--before", n1, "--after", n2)
        check("a measurement is not a comparison: --before/--after with it are refused",
              r.returncode == 2 and "no --before/--after" in r.stderr, f"rc={r.returncode} {r.stderr[-300:]}")

        print("a scene one run has no valid session for:")
        g1 = result_file(work / "g1.json", {"steady": [HIT] * 3, "lost": [HIT] * 3, "torn": [HIT, HIT, LOST]})
        g2 = result_file(work / "g2.json", {"steady": [HIT] * 3, "lost": [LOST] * 3, "torn": [HIT, LOST, LOST]})
        r = run("--measure-noise", g1, g2, "--out-record", work / "gap.json")
        gap: dict[str, Any] = json.loads((work / "gap.json").read_text(encoding="utf-8")) if (work / "gap.json").is_file() else {"scenarios": {}}
        check("its noise is not measured (n/a), never 0", gap["scenarios"].get("lost", {}).get("noise", 0) is None
              and "| `lost` | BLOCK#4 | 3/3 | 0/0 (of 3) | n/a |" in r.stdout, f"{gap['scenarios'].get('lost')} {r.stdout[:700]}")
        check("a lost session is not a verdict of the scene: it still reads 'always'",
              gap["scenarios"].get("torn", {}).get("distinct_verdicts") == [HIT]
              and "| `torn` | BLOCK#4 | 2/2 (of 3) | 1/1 (of 3) | 0.00 | always BLOCK#4 |" in r.stdout, f"{gap['scenarios'].get('torn')} {r.stdout[:900]}")

        print("one session of three is one session of three, whichever thirds it was measured between:")
        for name, low_1, low_2 in (("2/3 against 1/3", [HIT, HIT, MISS], [HIT, MISS, MISS]),
                                   ("1/3 against 0/3", [HIT, MISS, MISS], [MISS] * 3),
                                   ("3/3 against 2/3", [HIT] * 3, [HIT, HIT, MISS])):
            folder = work / name.replace("/", "of").replace(" ", "-")
            folder.mkdir()
            m1 = result_file(folder / "m1.json", {"steady": [HIT] * 3, "low": low_1})
            m2 = result_file(folder / "m2.json", {"steady": [HIT] * 3, "low": low_2})
            run("--measure-noise", m1, m2, "--out-record", folder / "audit-noise.json")
            for step, (first, second) in (("3/3 → 2/3", ([HIT] * 3, [HIT, HIT, MISS])), ("2/3 → 1/3", ([HIT, HIT, MISS], [HIT, MISS, MISS])),
                                          ("1/3 → 0/3", ([HIT, MISS, MISS], [MISS] * 3))):
                down = result_file(folder / "down.json", {"steady": first})
                up = result_file(folder / "up.json", {"steady": second}, commit="c" * 40)
                r, back = run("--before", down, "--after", up), run("--before", up, "--after", down)
                check(f"noise measured as {name}: {step} is within the noise, and so is the step back; nothing fails",
                      judgements(r.stdout).get("steady") == WITHIN and judgements(back.stdout).get("steady") == WITHIN
                      and r.returncode == 0 and back.returncode == 0,
                      f"rc={r.returncode}/{back.returncode} {judgements(r.stdout)} {judgements(back.stdout)}")
            far = result_file(folder / "far.json", {"steady": [HIT, MISS, MISS]}, commit="c" * 40)
            r = run("--before", result_file(folder / "top.json", {"steady": [HIT] * 3}), "--after", far)
            check(f"noise measured as {name}: two sessions of three are still WORSE",
                  judgements(r.stdout).get("steady") == "WORSE" and r.returncode == 1, f"rc={r.returncode} {judgements(r.stdout)}")
        e1 = result_file(work / "e1.json", {"steady": [HIT] * 3, "low": [HIT, HIT, MISS]})
        e2 = result_file(work / "e2.json", {"steady": [HIT] * 3, "low": [HIT, MISS, MISS]})
        r = run("--before", result_file(work / "top.json", {"fresh": [HIT] * 3, "low": [HIT] * 3}),
                "--after", result_file(work / "one-down.json", {"fresh": [HIT, HIT, MISS], "low": [HIT, HIT, MISS]}, commit="c" * 40),
                "--noise", e1, e2)
        got = judgements(r.stdout)
        check("the same with two --noise files given by hand: the scene they moved on, and a scene they do not have",
              got.get("low") == WITHIN and got.get("fresh") == WITHIN and r.returncode == 0, f"rc={r.returncode} {got}")

        print("a comparison with the record beside its --before file:")
        before = result_file(work / "before.json", {"steady": [HIT] * 3, "shaky": [HIT] * 3, "wrong": [HIT] * 3,
                                                    "new": [HIT] * 3, "flat": [HIT, HIT, MISS]})
        after = result_file(work / "after.json", {"steady": [HIT, HIT, MISS], "shaky": [HIT, MISS, MISS], "wrong": [HIT, HIT, MISS],
                                                  "new": [HIT, HIT, MISS], "flat": [HIT, MISS, HIT]}, commit="c" * 40)
        r = run("--before", before, "--after", after)
        got = judgements(r.stdout)
        check("one session of three on a scene that stood still in both noise runs: within the noise (the threshold binds)",
              got.get("steady") == WITHIN and got.get("wrong") == WITHIN, str(got))
        check("a scene the record does not have: bound by the threshold", got.get("new") == WITHIN, str(got))
        check("two sessions of three: WORSE", got.get("shaky") == "WORSE", str(got))
        check("no difference is 'same', not noise", got.get("flat") == "same", str(got))
        check("the WORSE scene fails the comparison", r.returncode == 1, f"rc={r.returncode}")
        check("the header names the record and its threshold",
              f"the record `{record_path}` — threshold 0.33" in r.stdout and "18 sessions" in r.stdout, r.stdout[:900])
        calm = result_file(work / "calm.json", {"steady": [HIT, HIT, MISS], "shaky": [HIT] * 3, "wrong": [HIT] * 3,
                                                "new": [HIT] * 3, "flat": [HIT, HIT, MISS]}, commit="c" * 40)
        r = run("--before", before, "--after", calm)
        check("differences all inside the noise fail nothing", r.returncode == 0 and judgements(r.stdout).get("steady") == WITHIN,
              f"rc={r.returncode} {judgements(r.stdout)}")
        r = run("--before", calm, "--after", before)
        check("the same step upward is not 'better' either", judgements(r.stdout).get("steady") == WITHIN, str(judgements(r.stdout)))

        print("negative — the same files with no record:")
        r = run("--before", before, "--after", calm, "--noise-record", "none")
        check("one session of three is WORSE, exit 1", judgements(r.stdout).get("steady") == "WORSE" and r.returncode == 1,
              f"rc={r.returncode} {judgements(r.stdout)}")
        check("the header says the noise was not measured", "noise: NOT MEASURED" in r.stdout, r.stdout[:900])
        r = run("--before", before, "--after", calm, "--noise-record", work / "absent.json")
        check("a record named and absent is refused", r.returncode == 2 and "no such file" in r.stderr, f"rc={r.returncode} {r.stderr[-200:]}")
        r = run("--before", before, "--after", calm, "--noise-record", n1)
        check("a file that is not a noise record is refused, not read as a noise of 0",
              r.returncode != 0 and "not a noise record" in r.stderr and "| `" not in r.stdout, f"rc={r.returncode} {r.stderr[-200:]} {r.stdout[:200]}")

        print("a record measured in another environment:")
        elsewhere = result_file(work / "elsewhere.json", {"steady": [HIT] * 3}, environment="macos-14")
        r = run("--before", elsewhere, "--after", elsewhere)
        check("the header says the record is another environment's", "the noise record is another environment's" in r.stdout, r.stdout[:900])
        r = run("--before", before, "--after", before)
        check("negative: the record's own environment is not marked", "another environment's" not in r.stdout, r.stdout[:900])

        print("--must-fix and --noise:")
        r = run("--before", calm, "--after", before, "--must-fix", "steady")
        check("a must-fix scene already at 2/3 is MET", judgements(r.stdout).get("steady", "").startswith("MET"), str(judgements(r.stdout)))
        low = result_file(work / "low.json", {"steady": [MISS] * 3}, commit="c" * 40)
        lift = result_file(work / "lift.json", {"steady": [HIT, MISS, MISS]}, commit="d" * 40)
        r = run("--before", low, "--after", lift, "--must-fix", "steady")
        check("a must-fix scene that moved inside the noise is NOT FIXED and says so",
              judgements(r.stdout).get("steady") == f"NOT FIXED ({WITHIN})" and r.returncode == 1, f"rc={r.returncode} {judgements(r.stdout)}")
        q1 = result_file(work / "q1.json", {"steady": [HIT] * 3})
        r = run("--before", before, "--after", calm, "--noise", q1, q1)
        check("two --noise files given by hand win over the record (their noise is 0: WORSE)",
              judgements(r.stdout).get("steady") == "WORSE" and "the record `" not in r.stdout, f"{judgements(r.stdout)} {r.stdout[:600]}")

        print("the record of this repository:")
        records = sorted((ROOT / "evals" / "baseline").glob("*/audit-noise.json"))
        check("there is one", len(records) >= 1, str(records))
        readme = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
        for path in records:
            kept = json.loads(path.read_text(encoding="utf-8"))
            sources = [path.parent / name for name in kept["sources"]]
            fresh = work / f"fresh-{path.parent.name}.json"
            r = run("--measure-noise", *sources, "--out-record", fresh)
            check(f"{path.parent.name}: recomputed from its source files it is the same record",
                  r.returncode == 0 and fresh.is_file() and json.loads(fresh.read_text(encoding="utf-8")) == kept, r.stderr[-300:])
            stated = re.search(rf"`baseline/{re.escape(path.parent.name)}/audit-noise\.json`[^\n]*?threshold \*\*([0-9.]+)\*\*", readme)
            check(f"{path.parent.name}: evals/README.md states its threshold",
                  bool(stated) and stated is not None and stated.group(1) == f"{float(kept['threshold']):.2f}",
                  stated.group(0) if stated else "no line names the record with its threshold")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
