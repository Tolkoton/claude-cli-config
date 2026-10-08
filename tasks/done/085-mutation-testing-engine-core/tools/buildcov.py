import json
from pathlib import Path
B = Path("/tmp/mut085"); out = {}
for d in sorted((B / "cov").iterdir()):
    if d.is_dir():
        for f in d.iterdir():
            out.setdefault(f.name, {})[d.name + ".py"] = sorted({int(x) for x in f.read_text().split()})
(B / "coverage.json").write_text(json.dumps(out))
suites = json.loads((B / "suites.json").read_text())
for name, m in out.items():
    allc = set().union(*m.values())
    print(name, "lines hit:", len(allc), "| suites:", ", ".join(f"{s[5:-3]}({len(v)},{suites[s]['cpu']:.0f}s)" for s, v in sorted(m.items(), key=lambda kv: suites[kv[0]]["cpu"])))
