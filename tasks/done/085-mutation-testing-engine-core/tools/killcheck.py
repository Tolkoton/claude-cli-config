"""killcheck.py <name> [suite ...]: apply every surviving mutant of <name> in w3 and run the given suites
(default tests/test_core_units.py, copied from the real repository first). Prints who is still alive."""
import glob, json, os, shutil, sqlite3, subprocess, sys
from pathlib import Path
B = Path("/tmp/mut085"); W = B / os.environ.get("KC_W", "w3"); REAL = Path("/home/lao/engine")
name = sys.argv[1]; suites = sys.argv[2:] or ["tests/test_core_units.py"]
for s in suites:
    shutil.copy(REAL / s, W / s)
env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k not in ("AI_AGENT", "BOARD_MAX_USD")}
env["PYTHONDONTWRITEBYTECODE"] = "1"
store = B / "after" / f"{name}.json"
known = json.loads(store.read_text()) if store.exists() else {}
alive = []
ROWS = {int(x) for x in os.environ.get("KC_ROWS", "").split(",") if x}
for s in suites:
    if subprocess.run([sys.executable, s], cwd=W, env=env, capture_output=True).returncode != 0:
        sys.exit(f"{s} is red on the unmutated code")
for db in sorted(glob.glob(f"{B}/sessions/{name}.[1-4].sqlite")):
    snap = f"/tmp/mut085/tmp/snap-{os.getpid()}.sqlite"; shutil.copy(db, snap); c = sqlite3.connect(snap)
    for job, row, op, outcome, diff in c.execute("select m.job_id, m.start_pos_row, m.operator_name, r.test_outcome, r.diff from mutation_specs m join work_results r using(job_id)").fetchall():
        if "SURVIVED" not in str(outcome).upper() or known.get(job, {}).get("killed"):
            continue
        if ROWS and row not in ROWS:
            continue
        patch = diff.split("\n", 1)[1] + "\n"
        a = subprocess.run(["git", "apply", "-"], cwd=W, input=patch, text=True, capture_output=True)
        if a.returncode:
            print("cannot apply", job[:6], a.stderr[:200]); continue
        killer = None
        for s in suites:
            try:
                r = subprocess.run([sys.executable, s], cwd=W, env=env, capture_output=True, text=True, timeout=int(os.environ.get("KC_TIMEOUT", "90")))
                bad = r.returncode != 0
            except subprocess.TimeoutExpired:
                bad = True
            if bad:
                killer = s; break
        subprocess.run(["git", "apply", "-R", "-"], cwd=W, input=patch, text=True, check=True)
        known[job] = {"row": row, "op": op, "killed": bool(killer), "by": killer}
        if not killer:
            alive.append((row, op.split("/")[-1], job[:6]))
store.write_text(json.dumps(known, indent=1))
k = sum(1 for v in known.values() if v["killed"])
print(f"{name}: killed by new tests {k}, still alive {len(alive)}")
for a in sorted(alive):
    print("  alive", *a)
