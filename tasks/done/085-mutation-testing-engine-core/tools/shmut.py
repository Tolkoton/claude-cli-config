"""shmut.py: a small sample of text mutants of board-runner.sh (universalmutator, universal rules) against tests/test_board_runner.py."""
import difflib, json, os, random, re, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
B = Path("/tmp/mut085"); W = B / "w1"; REL = ".claude/unattended/board-runner.sh"; N = int(sys.argv[1])
orig = (B / "um" / "board-runner.sh").read_text().splitlines()
pool = []
for f in sorted((B / "um" / "muts").iterdir()):
    new = f.read_text().splitlines()
    ops = [o for o in difflib.SequenceMatcher(None, orig, new, autojunk=False).get_opcodes() if o[0] != "equal"]
    tag, i1, i2, j1, j2 = ops[0]
    old_line = orig[i1] if i1 < len(orig) and tag != "insert" else ""
    new_line = new[j1] if j1 < len(new) and tag != "delete" else ""
    if (old_line.strip().startswith("#") or (tag == "insert" and not new_line.strip())) or not (old_line.strip() or new_line.strip()):
        continue
    if old_line.split("#")[0].strip() == new_line.split("#")[0].strip():
        continue  # the change is inside a trailing comment
    if subprocess.run(["bash", "-n", str(f)], capture_output=True).returncode != 0:
        continue
    pool.append((f, i1 + 1, old_line, new_line))
print("usable mutants:", len(pool), flush=True)
sample = random.Random(85).sample(pool, N)
env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k not in ("AI_AGENT", "BOARD_MAX_USD")}
G = ["git", "-c", "user.name=mut", "-c", "user.email=mut@example.invalid"]
for f, line, old_line, new_line in sample:
    shutil.copy(f, W / REL)
    subprocess.run(G + ["commit", "-qam", "mutant"], cwd=W, check=True)
    tmp = tempfile.mkdtemp(prefix="m85-", dir=str(B / "tmp")); t0 = time.time(); how = None
    p = subprocess.Popen([sys.executable, "-u", "tests/test_board_runner.py"], cwd=W, env=dict(env, TMPDIR=tmp), stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, errors="replace", start_new_session=True)
    def on_alarm(*_):
        raise TimeoutError
    signal.signal(signal.SIGALRM, on_alarm); signal.alarm(4500)
    try:
        for ln in p.stdout:
            if re.match(r"\s*FAIL\b", ln) and not re.match(r"\s*FAIL\s*[:=]?\s*0\b", ln):
                how = "fail-line: " + ln.strip()[:120]; break
        if how is None and p.wait() != 0:
            how = "rc"
    except TimeoutError:
        how = "timeout"
    finally:
        signal.alarm(0)
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait(); shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run(["git", "reset", "-q", "--hard", "HEAD~1"], cwd=W, check=True)
    rec = {"mutant": f.name, "line": line, "old": old_line.strip()[:160], "new": new_line.strip()[:160], "killed": bool(how), "how": how, "secs": round(time.time() - t0)}
    with open(B / "log" / "sh.jsonl", "a") as out:
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(rec, flush=True)
