"""cosmic-ray test-command: pick the suites that execute the mutated statement, run them fail-fast.
Usage (cwd = clone): runtests.py <target relpath> ; exit 1 = killed, 0 = survived."""
import ast, difflib, json, os, re, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
BASE = Path("/tmp/mut085"); CAP = float(os.environ.get("MUT_CAP", "75"))
target = sys.argv[1]; name = Path(target).name; clone = Path.cwd()
PRIO = {"gate.py": ["gate", "verify_on_stop", "gate_allows", "delete_guard", "baseline"], "lesson_queue.py": ["lesson_queue"],
        "overseer_stop.py": ["overseer_fresh", "source_dirs", "overseer_phase", "contract_fingerprint", "gate_allows"],
        "overseer_verdict.py": ["overseer_fresh", "contract_fingerprint", "gate_allows", "overseer_readonly"],
        "board.py": ["board", "onboard", "board_review"],
        "engine.py": ["engine_install", "project_seeds", "ownership", "migration", "settings_wiring", "state_migration", "claude_md_update",
                      "personal_layer", "legacy_records_survive", "supervisor_retired", "settings_proposal_install", "release"]}
G = ["git", "-c", "user.name=mut", "-c", "user.email=mut@example.invalid"]


def stmt_range(tree, line):
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for d in node.decorator_list:
                if d.lineno <= line <= d.end_lineno:
                    return (d.lineno, d.end_lineno)
        if isinstance(node, ast.Try):
            for h in node.handlers:
                if h.lineno <= line < max(h.body[0].lineno, h.lineno + 1) and not (h.body[0].lineno == h.lineno):
                    return (node.lineno, h.body[0].lineno - 1)
        if not isinstance(node, ast.stmt) or not (node.lineno <= line <= node.end_lineno):
            continue
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.stmt):
            if line >= body[0].lineno and body[0].lineno > node.lineno:
                continue  # inside the body (or orelse/finally): an inner statement owns it
            rng = (node.lineno, max(node.lineno, body[0].lineno - 1))
            if line > rng[1]:
                continue
        else:
            rng = (node.lineno, node.end_lineno)
        if best is None or (rng[1] - rng[0]) <= (best[1] - best[0]):
            best = rng
    return best or (line, line)


def changed_line(old, new):
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag != "equal":
            return next((i + 1 for i in range(i1, i2) if old[i].strip()), i1 + 1)
    return None


def run_suite(suite, env, limit):
    tmp = tempfile.mkdtemp(prefix="m85-", dir=str(BASE / "tmp"))
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
        p.wait()
        shutil.rmtree(tmp, ignore_errors=True)
    return killed


def main():
    old = (BASE / "pristine" / name).read_text().splitlines()
    new = (clone / target).read_text().splitlines()
    line = changed_line(old, new)
    rec = {"line": line, "t": time.time()}
    if line is None:
        rec["result"] = "no-change"; verdict = 0
    else:
        lo, hi = stmt_range(ast.parse("\n".join(old)), line)
        suites = json.loads((BASE / "suites.json").read_text())
        cover = json.loads((BASE / "coverage.json").read_text())[name]
        cands = sorted((s for s, lines in cover.items() if suites[s]["rc"] == 0 and any(lo <= x <= hi for x in lines)),
                       key=lambda s: suites[s]["cpu"])
        prio = [f"test_{x}.py" for x in PRIO[name] if f"test_{x}.py" in cands]
        cheap = [s for s in cands if suites[s]["cpu"] <= 2.5]
        cands = cheap + [s for s in prio if s not in cheap] + [s for s in cands if s not in cheap and s not in prio]
        first = next((s for s in prio if s not in cheap), None)
        rec.update(range=[lo, hi], covering=cands)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k not in ("AI_AGENT", "BOARD_MAX_USD")}
        ran, verdict, spent = [], 0, 0.0
        if cands:
            if subprocess.run(["git", "log", "-1", "--format=%s"], cwd=clone, capture_output=True, text=True).stdout.strip() == "mutant":
                subprocess.run(["git", "reset", "-q", "--soft", "HEAD~1"], cwd=clone)
            subprocess.run(G + ["commit", "-qam", "mutant"], cwd=clone, check=True)
            try:
                for s in cands:
                    if ran and spent + suites[s]["cpu"] > CAP and s != first:
                        continue
                    ran.append(s); spent += suites[s]["cpu"]
                    how = run_suite(s, env, 10 * suites[s]["wall"] + 300)
                    if how:
                        rec.update(killer=s, how=how); verdict = 1; break
            finally:
                subprocess.run(["git", "reset", "-q", "--soft", "HEAD~1"], cwd=clone, check=True)
                subprocess.run(["git", "reset", "-q"], cwd=clone, check=True)
        rec.update(ran=ran, not_run=[s for s in cands if s not in ran],
                   result="killed" if verdict else ("survived" if cands else "uncovered"))
    rec["secs"] = round(time.time() - rec.pop("t"), 1)
    with open(BASE / "log" / (name + ".jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    sys.exit(verdict)


main()
