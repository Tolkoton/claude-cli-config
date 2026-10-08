import ast, glob, json, os, shutil, sqlite3
from pathlib import Path
B = Path("/tmp/mut085")
NAMES = ["gate", "overseer_verdict", "overseer_stop", "board", "engine", "lesson_queue"]


def results(name):
    """Every finished mutant of a target: dicts with job, op, row, col, outcome, diff lines."""
    out = []
    for db in sorted(glob.glob(f"{B}/sessions/{name}.[1-4].sqlite")):
        snap = f"{B}/tmp/snap-{os.getpid()}.sqlite"; shutil.copy(db, snap); c = sqlite3.connect(snap)
        for job, op, row, col, outcome, diff in c.execute(
                "select m.job_id, m.operator_name, m.start_pos_row, m.start_pos_col, r.test_outcome, r.diff from mutation_specs m join work_results r using(job_id)").fetchall():
            d = [l for l in (diff or "").splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            out.append({"job": job, "op": op.split("/")[-1].replace("Replace", ""), "row": row, "col": col,
                        "survived": "SURVIVED" in str(outcome).upper(), "diff": d, "chunk": Path(db).name})
        c.close()
    return out


def annotation_spans(name):
    tree = ast.parse((B / "pristine" / f"{name}.py").read_text()); spans = []
    for n in ast.walk(tree):
        anns = []
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            anns += [x.annotation for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None and x.annotation] + ([n.returns] if n.returns else [])
        if isinstance(n, ast.AnnAssign):
            anns.append(n.annotation)
        spans += [((x.lineno, x.col_offset), (x.end_lineno, x.end_col_offset)) for x in anns]
    return spans


def rules(name):
    out = []
    f = B / "classify.tsv"
    for line in f.read_text().splitlines() if f.exists() else []:
        t, row, op, cat, why = line.split("\t")
        if t == name:
            out.append((row, op, cat, why))
    return out


def classify(name, m, spans, rs, after):
    """(category, reason): K1 new test, K2 capped-out suite, E equivalent, C cosmetic, N not killed, ? untriaged."""
    a = after.get(m["job"], {})
    if a.get("killed"):
        return ("K1" if "core_units" in a["by"] else "K2", a["by"])
    if "BitOr" in m["op"] and any(s <= (m["row"], m["col"]) < e for s, e in spans):
        return ("E", "анотація типу: під `from __future__ import annotations` не обчислюється")
    for row, op, cat, why in rs:
        if row in ("*", str(m["row"])) and (op == "*" or op.split("@")[0].replace("Replace", "") in m["op"]) and "@annotation" not in op and cat != "K2":
            return (cat, why)
    return ("?", "")


def load_after(name):
    f = B / "after" / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else {}
