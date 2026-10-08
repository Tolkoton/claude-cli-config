"""Instrument the six targets in a clone, run every suite once, record lines hit and CPU cost."""
import json, os, resource, shutil, subprocess, sys, tempfile, time
from pathlib import Path
clone = Path(sys.argv[1]); cov = Path("/tmp/mut085/cov")
targets = [".claude/hooks/gate.py", ".claude/hooks/overseer_verdict.py", ".claude/hooks/overseer_stop.py",
           ".claude/unattended/board.py", "engine.py", ".claude/hooks/lesson_queue.py"]
FUT = "from __future__ import annotations"
for t in targets:
    p = clone / t; s = p.read_text()
    assert s.count("\n" + FUT + "\n") == 1, t
    p.write_text(s.replace("\n" + FUT + "\n", "\n" + FUT + "; exec(open('/tmp/mut085/tools/tracer.py').read())\n", 1))
G = ["git", "-c", "user.name=mut", "-c", "user.email=mut@example.invalid"]
subprocess.run(G + ["commit", "-qam", "instrumented"], cwd=clone, check=True)
env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k not in ("AI_AGENT", "BOARD_MAX_USD")}
out = {}
for suite in sorted((clone / "tests").glob("test_*.py")):
    (cov / "current").write_text(suite.stem)
    tmp = tempfile.mkdtemp(prefix="m85-", dir="/tmp/mut085")
    e = dict(env, TMPDIR=tmp)
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN); w0 = time.time()
    p = subprocess.run([sys.executable, str(suite)], cwd=clone, env=e, capture_output=True, text=True)
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)
    out[suite.name] = {"rc": p.returncode, "cpu": round(cpu, 1), "wall": round(time.time() - w0, 1), "tail": p.stdout.strip().splitlines()[-1:] }
    print(suite.name, out[suite.name], flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
(cov / "current").write_text("")
Path("/tmp/mut085/suites.json").write_text(json.dumps(out, indent=1))
subprocess.run(["git", "reset", "-q", "--hard", "HEAD~1"], cwd=clone, check=True)
