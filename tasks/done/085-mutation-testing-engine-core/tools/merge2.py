"""merge2.py: fold the second pass (log/phase2.w*.jsonl) into after/<name>.json."""
import glob, json
from lib import *
n = 0
for f in glob.glob(f"{B}/log/phase2.w*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        if r["killed"]:
            p = B / "after" / f"{r['name']}.json"
            d = json.loads(p.read_text()) if p.exists() else {}
            d[r["job"]] = {"row": r["row"], "op": "", "killed": True, "by": "tests/" + r["by"]}
            p.write_text(json.dumps(d, indent=1)); n += 1
print("merged", n)
