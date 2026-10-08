import re, sqlite3, subprocess, sys
from pathlib import Path
BASE = Path("/tmp/mut085")
T = {"gate": ".claude/hooks/gate.py", "overseer_verdict": ".claude/hooks/overseer_verdict.py", "overseer_stop": ".claude/hooks/overseer_stop.py",
     "board": ".claude/unattended/board.py", "engine": "engine.py", "lesson_queue": ".claude/hooks/lesson_queue.py"}
KEEP = re.compile(r"core/(AddNot|ExceptionReplacer|NumberReplacer|RemoveDecorator|ReplaceAndWithOr|ReplaceOrWithAnd|ReplaceBreakWithContinue|"
                  r"ReplaceContinueWithBreak|ReplaceFalseWithTrue|ReplaceTrueWithFalse|ZeroIterationForLoop|"
                  r"ReplaceBinaryOperator_(Add_Sub|Sub_Add|Mul_FloorDiv|Div_Mul|FloorDiv_Mul|Mod_Mul|Pow_Mul|BitOr_BitAnd|BitAnd_BitOr|BitXor_BitAnd|LShift_RShift|RShift_LShift)|"
                  r"ReplaceComparisonOperator_(Eq_NotEq|NotEq_Eq|Lt_LtE|Lt_GtE|Gt_GtE|Gt_LtE|LtE_Lt|LtE_Gt|GtE_Gt|GtE_Lt|Is_IsNot|IsNot_Is|In_NotIn|NotIn_In)|"
                  r"ReplaceUnaryOperator_(Delete_Not|Delete_USub|Delete_Invert))$")
for n, path in T.items():
    cfg = BASE / "sessions" / f"{n}.toml"; db = BASE / "sessions" / f"{n}.sqlite"
    cfg.write_text(f'[cosmic-ray]\nmodule-path = "{path}"\ntimeout = 100000.0\nexcluded-modules = []\n'
                   f'test-command = "python3 /tmp/mut085/tools/runtests.py {path}"\n[cosmic-ray.distributor]\nname = "local"\n')
    db.unlink(missing_ok=True)
    subprocess.run(["uvx", "cosmic-ray", "init", str(cfg), str(db)], check=True, capture_output=True)
    c = sqlite3.connect(db)
    rows = c.execute("select job_id, operator_name from mutation_specs").fetchall()
    drop = [j for j, o in rows if not KEEP.match(o)]
    c.executemany("delete from mutation_specs where job_id=?", [(j,) for j in drop])
    c.executemany("delete from work_items where job_id=?", [(j,) for j in drop])
    c.commit()
    print(n, len(rows), "->", len(rows) - len(drop), sorted({o for _, o in rows if not KEEP.match(o) and "Binary" not in o and "Comparison" not in o}))
