import random, shutil, sqlite3
from pathlib import Path
S = Path("/tmp/mut085/sessions")
for n in ["gate", "overseer_verdict", "overseer_stop", "board", "engine", "lesson_queue"]:
    c = sqlite3.connect(S / f"{n}.sqlite"); ids = sorted(r[0] for r in c.execute("select job_id from work_items")); c.close()
    random.Random(85).shuffle(ids)
    for k in range(4):
        keep = set(ids[k::4]); db = S / f"{n}.{k+1}.sqlite"; shutil.copy(S / f"{n}.sqlite", db)
        c = sqlite3.connect(db)
        drop = [(j,) for j in ids if j not in keep]
        c.executemany("delete from mutation_specs where job_id=?", drop); c.executemany("delete from work_items where job_id=?", drop)
        c.commit(); c.execute("vacuum"); c.close()
        print(db.name, len(keep))
