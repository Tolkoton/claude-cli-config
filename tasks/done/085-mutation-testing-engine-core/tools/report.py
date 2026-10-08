"""report.py: the numbers and the survivor list (markdown on stdout; --list for survivors.md)."""
import ast, collections, json, sqlite3, sys
from lib import *
src = (B / "tools" / "runtests.py").read_text().split("def changed_line")[0].split("def stmt_range")[1]
ns = {"ast": ast}; exec("def stmt_range" + src, ns); stmt_range = ns["stmt_range"]
cover = json.loads((B / "coverage.json").read_text())
PATHS = {"gate": ".claude/hooks/gate.py", "overseer_verdict": ".claude/hooks/overseer_verdict.py", "overseer_stop": ".claude/hooks/overseer_stop.py",
         "board": ".claude/unattended/board.py", "engine": "engine.py", "lesson_queue": ".claude/hooks/lesson_queue.py"}
rows, listing, tot = [], [], collections.Counter()
for name in NAMES:
    full = sqlite3.connect(B / f"{name}.count.sqlite").execute("select count(*) from mutation_specs").fetchone()[0]
    reduced = sqlite3.connect(B / "sessions" / f"{name}.sqlite").execute("select count(*) from mutation_specs").fetchone()[0]
    tree = ast.parse((B / "pristine" / f"{name}.py").read_text()); hit = set().union(*cover[f"{name}.py"].values())
    spans, rs, after = annotation_spans(name), rules(name), load_after(name)
    res = results(name); c = collections.Counter()
    for m in res:
        if not m["survived"]:
            c["killed"] += 1; continue
        lo, hi = stmt_range(tree, m["row"])
        covered = any(lo <= x <= hi for x in hit) or "RemoveDecorator" in m["op"]
        cat, why = classify(name, m, spans, rs, after)
        if cat == "?" and not covered:
            cat, why = "U", "рядок не виконує жоден набір тестів"
        c["survived"] += 1; c["uncovered" if not covered else "covered"] += 1; c[cat] += 1
        listing.append((name, m["row"], m["col"], m["op"], cat, why, m["diff"]))
    c.update(full=full, reduced=reduced, run=len(res)); tot.update(c); rows.append((name, c))
rows.append(("разом", tot))
if "--list" in sys.argv:
    names = {"K1": "вбито новим тестом", "K2": "вбиває наявний набір тестів, який не запускався через межу часу", "E": "рівнозначний оригіналу",
             "C": "лише текст повідомлення, межа показу чи телеметрія", "N": "не вбито: тест не написано", "U": "не вбито: рядок не виконує жоден тест", "?": "не розібрано"}
    for cat in ("K1", "K2", "E", "C", "N", "U", "?"):
        items = [x for x in listing if x[4] == cat]
        if not items:
            continue
        print(f"\n## {names[cat]} — {len(items)}\n")
        for name, row, col, op, _, why, diff in sorted(items):
            print(f"- `{PATHS[name]}:{row}` {op} — {why if cat not in ('K1',) else 'tests/test_core_units.py'}")
            if cat != "K1":
                for l in diff:
                    print(f"  - `{l[:1]} {l[1:].strip()[:150]}`")
else:
    print("| Файл | Мутантів усього | Після відбору операторів | Запущено | Вбито до | Вижило до | з них рядок не виконує жоден тест | Вбито новими тестами | Вбивають наявні тести поза межею часу | Рівнозначні | Лише текст/телеметрія | Не вбито | Не розібрано |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, c in rows:
        print(f"| {PATHS.get(name, name)} | {c['full']} | {c['reduced']} | {c['run']} | {c['killed']} | {c['survived']} | {c['uncovered']} | {c['K1']} | {c['K2']} | {c['E']} | {c['C']} | {c['N'] + c['U']} | {c['?']} |")
    c = tot
    print(f"\nдо: {c['killed']}/{c['run']} = {100*c['killed']/max(1,c['run']):.1f}% ; після: {c['killed']+c['K1']+c['K2']}/{c['run']} = {100*(c['killed']+c['K1']+c['K2'])/max(1,c['run']):.1f}% ; без рівнозначних: {c['killed']+c['K1']+c['K2']}/{c['run']-c['E']} = {100*(c['killed']+c['K1']+c['K2'])/max(1,c['run']-c['E']):.1f}%")
