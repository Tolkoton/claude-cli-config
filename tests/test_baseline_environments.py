#!/usr/bin/env python3
"""Recorded results are kept by ENVIRONMENT — the operating system and its version — and no
personal machine name is in the repository (board 030).

- `evals/environment.py` names an environment from the system, never from the host;
- every folder under evals/baseline/ carries such a name, and a file that records its platform
  lies in a folder of that system;
- no recorded file names a host, and no tracked file carries a personal machine name;
- a script refuses to record into another environment's folder, and `@env` is this one's;
- a comparison of two environments says so, in compare.py and in compare_audits.py.

Deterministic and offline: no sandbox, no session.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
BASELINE = EVALS / "baseline"
PASS = FAIL = 0

spec = importlib.util.spec_from_file_location("environment", EVALS / "environment.py")
assert spec and spec.loader
environment: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


def check(name: str, cond: bool, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:600]}")


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(EVALS / script), *args], cwd=ROOT, capture_output=True, text=True, check=False)


print("the name comes from the system")
UBUNTU = 'PRETTY_NAME="Ubuntu 22.04.5 LTS"\nNAME="Ubuntu"\nVERSION_ID="22.04"\nID=ubuntu\nID_LIKE=debian\n'
name = environment.environment_name
check("Ubuntu 22.04", name("Linux", UBUNTU) == "linux-ubuntu-22.04", name("Linux", UBUNTU))
check("a quoted ID and a single-number version", name("Linux", 'ID="debian"\nVERSION_ID="12"\n') == "linux-debian-12")
check("a rolling release has no version", name("Linux", "ID=arch\n") == "linux-arch", name("Linux", "ID=arch\n"))
check("Linux without os-release", name("Linux", "") == "linux", name("Linux", ""))
check("macOS: the major version only", name("Darwin", release="14.8.9") == "macos-14", name("Darwin", release="14.8.9"))
check("another system: its name and major release", name("FreeBSD", release="14.1-RELEASE") == "freebsd-14", name("FreeBSD", release="14.1-RELEASE"))
here = name()
check("this environment's name has the folder shape", bool(environment.NAME_SHAPE.match(here)), here)
check("the name is not the host's", platform.node().lower() not in here.split("-") or not platform.node(), here)
cli = run("environment.py")
check("the script prints the name", cli.returncode == 0 and cli.stdout.strip() == here, cli.stdout + cli.stderr)

print("the folders")
folders = sorted(p for p in BASELINE.iterdir() if p.is_dir())
check("there are recorded results", len(folders) >= 2, folders)
for directory in folders:
    check(f"{directory.name}/ is named after an environment", bool(environment.NAME_SHAPE.match(directory.name)), directory.name)
for bad in ("Someones-MacBook-Pro", "box", "clean-ubuntu-24.04", "ubuntu-26.04", "MACOS-14", "linux-ubuntu-22.04-mine"):
    check(f"the shape refuses {bad}", not environment.NAME_SHAPE.match(bad))

HOST = platform.node().split(".")[0]
records = sorted(BASELINE.glob("*/*.json"))
misplaced, hosts, named = [], [], []
for path in records:
    data = json.loads(path.read_text(encoding="utf-8"))
    folder = path.parent.name
    env = data.get("environment")
    system = str(env.get("platform", "")) if isinstance(env, dict) else ""
    if system and system.split("-")[0].lower() != folder.split("-")[0]:
        misplaced.append(f"{path.relative_to(ROOT)}: {system}")
    recorded = environment.recorded_in(data, path)
    if recorded != folder:
        misplaced.append(f"{path.relative_to(ROOT)}: says {recorded}")
    if any(key in data for key in ("host", "hostname", "machine")):
        hosts.append(str(path.relative_to(ROOT)))
    # Top-level text only: the scenarios below it quote whatever a hook was fed.
    text = " ".join(str(v) for v in data.values() if isinstance(v, str))
    if len(HOST) > 3 and re.search(rf"(?<![A-Za-z0-9]){re.escape(HOST)}(?![A-Za-z0-9])", text):
        named.append(str(path.relative_to(ROOT)))
check("every record lies in the folder of the system it was recorded on", not misplaced, misplaced)
check("no record has a host field", not hosts, hosts)
check("no record's label names the machine the suite runs on", not named, named)

print("no personal machine name in the repository")
# The shape macOS gives a personal machine: <Owner>s-MacBook-Pro, <Owner>s-iMac, <Owner>s-Mac-mini.
PERSONAL = re.compile(r"[A-Za-z][A-Za-z0-9]*s-(?:MacBook|iMac|Mac)(?:-[A-Za-z0-9]+)*")
SELF = Path(__file__).resolve()
tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                         capture_output=True, text=True, check=True).stdout.split("\n")
personal = []
for rel in filter(None, tracked):
    path = ROOT / rel
    if PERSONAL.search(rel):
        personal.append(rel)
    if path.resolve() == SELF or not path.is_file():
        continue
    try:
        found = PERSONAL.search(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        continue
    if found:
        personal.append(f"{rel}: {found.group(0)}")
check("no tracked path or file carries a personal machine name", not personal, personal[:8])
check("no tracked path under evals/baseline/ is the folder of the machine the suite runs on",
      not (BASELINE / HOST).exists() or bool(environment.NAME_SHAPE.match(HOST)), HOST)

print("writing: this environment's folder only")
other = "macos-99" if here != "macos-99" else "macos-98"
check("@env is this environment", environment.baseline_path("evals/baseline/@env/x.json") == Path("evals/baseline") / here / "x.json")
check("a path without @env is left alone", environment.baseline_path("some/dir/x.json") == Path("some/dir/x.json"))
check("out: this environment's folder is accepted", environment.out_path(str(BASELINE / here / "x.json")) == BASELINE / here / "x.json")
check("out: a path outside evals/baseline/ is accepted", environment.out_path("/tmp/x.json") == Path("/tmp/x.json"))
try:
    environment.out_path(str(BASELINE / other / "x.json"))
    refused = ""
except argparse.ArgumentTypeError as exc:
    refused = str(exc)
check("out: another environment's folder is refused, and the right path is named", here in refused and "@env/x.json" in refused, refused)
for script, extra in (("run_hook_scenarios.py", ["--engine-ref", "HEAD"]), ("run_gate_evals.py", ["--engine-ref", "HEAD"]),
                      ("run_audit_scenarios.py", []), ("run_simplifier_evals.py", [])):
    proc = run(script, *extra, "--out", f"evals/baseline/{other}/refused.json")
    check(f"{script} refuses to record into {other}/ before doing anything",
          proc.returncode == 2 and f"this environment is {here}" in proc.stderr, f"rc={proc.returncode} {proc.stderr[-300:]}")
check("nothing was written there", not (BASELINE / other).exists())

print("reading: a comparison across environments says so")


def hook_results(env: object) -> str:
    report: dict[str, Any] = {"label": "", "sandbox": {}, "results": [{"id": "a", "outcomes": ["block"]}]}
    if env is not None:
        report["environment"] = env
    return json.dumps(report)


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    for file, env in (("mac.json", {"name": "macos-14"}), ("linux.json", {"name": "linux-ubuntu-22.04"}),
                      ("linux2.json", {"name": "linux-ubuntu-22.04"}), ("old.json", {"platform": "Linux-6.8"}), ("bare.json", None)):
        (base / file).write_text(hook_results(env), encoding="utf-8")
    cross = run("compare.py", str(base / "mac.json"), str(base / "linux.json"))
    check("compare.py: two environments are marked",
          cross.returncode == 0 and "CROSS-ENVIRONMENT COMPARISON: base was recorded on macos-14, candidate on linux-ubuntu-22.04" in cross.stdout
          and "across two environments" in cross.stdout, cross.stdout + cross.stderr)
    same = run("compare.py", str(base / "linux.json"), str(base / "linux2.json"))
    check("compare.py: one environment is not marked",
          same.returncode == 0 and "ENVIRONMENT" not in same.stdout and "environment linux-ubuntu-22.04" in same.stdout, same.stdout)
    unknown = run("compare.py", str(base / "old.json"), str(base / "linux.json"))
    check("compare.py: a file that names no environment is said to be unknown, not assumed the same",
          "ENVIRONMENT NOT RECORDED" in unknown.stdout and "CROSS-ENVIRONMENT" not in unknown.stdout, unknown.stdout)

mac = sorted((BASELINE / "macos-14").glob("results-*.json"))
linux = sorted((BASELINE / "linux-ubuntu-22.04").glob("results-*.json"))
if mac and linux:
    proc = run("compare.py", str(mac[-1]), str(linux[0]))
    check("compare.py: a record without the field is of the folder it lies in",
          "CROSS-ENVIRONMENT COMPARISON: base was recorded on macos-14, candidate on linux-ubuntu-22.04" in proc.stdout, proc.stdout[:400])
    proc = run("compare.py", str(linux[0]), str(linux[-1]))
    check("compare.py: two records of one folder are not marked", "ENVIRONMENT" not in proc.stdout, proc.stdout[:400])
before, after = BASELINE / "macos-14/audit-v0.11.0.json", BASELINE / "linux-ubuntu-22.04/audit-v0.12.0.json"
if before.is_file() and after.is_file():
    proc = run("compare_audits.py", "--before", str(before), "--after", str(after))
    check("compare_audits.py: two environments are marked in the report's header",
          "**CROSS-ENVIRONMENT COMPARISON: before was recorded on macos-14, after on linux-ubuntu-22.04" in proc.stdout
          and "environment macos-14" in proc.stdout, proc.stdout[:600] + proc.stderr[-300:])
    proc = run("compare_audits.py", "--before", str(after), "--after", str(after))
    check("compare_audits.py: one environment is not marked", "CROSS-ENVIRONMENT" not in proc.stdout, proc.stdout[:400])
if here == "linux-ubuntu-22.04" and linux:
    proc = run("compare.py", f"evals/baseline/@env/{linux[0].name}", str(linux[0]))
    check("compare.py reads @env as this environment's folder", proc.returncode == 0 and "identical behaviour" in proc.stdout, proc.stdout + proc.stderr)

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
