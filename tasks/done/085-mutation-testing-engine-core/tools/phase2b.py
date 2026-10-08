"""phase2b.py <clone> <name...>: every survivor still classed N against the suites the cap left out
(test_board_runner excepted), cheapest first, fail-fast. Appends to log/phase2.<clone>.jsonl."""
import glob, json, os, re, shutil, signal, sqlite3, subprocess, sys, tempfile, time
from lib import *
clone = B / sys.argv[1]; names = sys.argv[2:]
suites = json.loads((B / "suites.json").read_text())
out = B / "log" / f"phase2.{sys.argv[1]}.jsonl"
done = {json.loads(l)["job"] for l in open(out)} if out.exists() else set()
env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k not in ("AI_AGENT", "BOARD_MAX_USD")}
env["PYTHONDONTWRITEBYTECODE"] = "1"


def run_suite(suite, limit):
    tmp = tempfile.mkdtemp(prefix="m85-", dir=str(B / "tmp"))
    p = subprocess.Popen([sys.executable, "-u", f"tests/{suite}"], cwd=clone, env=dict(env, TMPDIR=tmp), stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, errors="replace", start_new_session=True)
    killed = None
    def on_alarm(*_):
        raise TimeoutError
    signal.signal(signal.SIGALRM, on_alarm); signal.alarm(int(limit))
    try:
        for ln in p.stdout:
            if re.match(r"\s*FAIL\b", ln) and not re.match(r"\s*FAIL\s*[:=]?\s*0\b", ln):
                killed = "fail-line"; break
        if killed is None:
            killed = None if p.wait() == 0 else "rc"
    except TimeoutError:
        killed = "timeout"
    finally:
        signal.alarm(0)
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait(); shutil.rmtree(tmp, ignore_errors=True)
    return killed


work = []
for name in names:
    notrun = {}
    for l in open(B / "log" / f"{name}.py.jsonl"):
        r = json.loads(l)
        if r.get("result") == "survived":
            notrun[r["line"]] = [s for s in r["not_run"] if s != "test_board_runner.py"]
    spans, rs, after = annotation_spans(name), rules(name), load_after(name)
    full = {}
    for db in sorted(glob.glob(f"{B}/sessions/{name}.1.sqlite")):
        snap = f"{B}/tmp/snap-{os.getpid()}.sqlite"; shutil.copy(db, snap); c = sqlite3.connect(snap)
        full.update(dict(c.execute("select job_id, diff from work_results").fetchall())); c.close()
    for m in results(name):
        if m["survived"] and m["job"] not in done and classify(name, m, spans, rs, after)[0] == "N":
            todo = sorted(notrun.get(m["row"], []), key=lambda s: suites[s]["cpu"])
            work.append((sum(suites[s]["cpu"] for s in todo), name, m, todo, full[m["job"]].split("\n", 1)[1] + "\n"))
subprocess.run(["git", "checkout", "-q", "--", "."], cwd=clone, check=True)
for cost, name, m, todo, patch in sorted(work, key=lambda w: w[0]):
    killer = None; t0 = time.time()
    if todo:
        subprocess.run(["git", "apply", "-"], cwd=clone, input=patch, text=True, check=True)
        try:
            for s in todo:
                if run_suite(s, 10 * suites[s]["wall"] + 300):
                    killer = s; break
        finally:
            subprocess.run(["git", "apply", "-R", "-"], cwd=clone, input=patch, text=True, check=True)
    with open(out, "a") as f:
        f.write(json.dumps({"name": name, "job": m["job"], "row": m["row"], "killed": bool(killer), "by": killer, "ran": todo, "secs": round(time.time() - t0)}) + "\n")
print("done", flush=True)
