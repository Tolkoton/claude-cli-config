#!/usr/bin/env python3
"""second_opinion.py and the lowering it feeds in simplifier.py, against a fake Gemini.

No real request is made: SECOND_OPINION_API_BASE points the hook at a local server that records
what it was sent and answers what the case tells it to. Shown here: what is sent and what never
is, where the key travels and where it must not appear, every way an answer can be wrong, and the
table of lowerings — each row with the case that lowers and the case that does not.

Run:   python3 tests/test_second_opinion.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
simplifier: Any = importlib.import_module("simplifier")
second: Any = importlib.import_module("second_opinion")

PASS = FAIL = 0
KEY = "test-key-7f3a9c1e5b"
ENV_ON = ('SOURCE_DIRS="src"\nCODE_EXTENSIONS="py"\nSIMPLIFY_EXCLUDE="vendor"\nSECOND_OPINION="on"\nSECOND_OPINION_MODEL="m-test"\n'
          'SECOND_OPINION_PRICE_IN="2.00"\nSECOND_OPINION_PRICE_OUT="12.00"\nSECOND_OPINION_MAX_USD="2"\n')
FILES = {
    "src/demo/pricing.py": "def total(prices: list[int]) -> int:\n    return sum(prices)\n\n\ndef old_total() -> int:\n    return 0\n",
    "src/demo/cli.py": "import sys\n\nfrom demo.pricing import old_total, total\n\nprint(total([1]), old_total(), sys.argv)\n",
    "secrets/tool.py": "from demo.pricing import old_total  # SECRET-MARK\n",
    "vendor/gen.py": "from demo.pricing import old_total  # VENDOR-MARK\n",
    ".engine/simplifier/report.md": "old_total has no caller RECORD-MARK\n",
    ".claude/project.env": ENV_ON,
    ".gitignore": ".claude/state/\n",
}
GOOD: dict[str, Any] = {
    "target": "src/demo/pricing.py:5", "category": "dead_code", "claim": "old_total has no caller",
    "evidence": [{"source": "grep", "ref": "src/demo/pricing.py:5", "detail": "only the definition EVIDENCE-MARK"}],
    "protected": False, "chesterton_checked": True, "test_safety": "characterization_exists",
    "proposed_action": "auto_remove", "traceability": "none found TRACE-MARK", "reversal_risk": "low",
}


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n         {str(detail)[:900]}")


class Gemini(BaseHTTPRequestHandler):
    seen: ClassVar[list[dict[str, Any]]] = []
    reply: Any = None  # (status, body bytes, delay seconds)

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        Gemini.seen.append({"path": self.path, "key": self.headers.get("x-goog-api-key"), "body": body.decode()})
        status, payload, delay = Gemini.reply
        time.sleep(delay)
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        except OSError:
            pass  # the client gave up: the timeout case

    def log_message(self, *args: Any) -> None:
        pass


def answer(verdict: str, refs: list[str] | None = None, status: int = 200, delay: float = 0.0, text: str | None = None) -> None:
    obj = {"verdict": verdict, "reason": f"because {verdict}", "counter_evidence": [{"ref": r, "detail": "uses it"} for r in refs or []]}
    payload = {"candidates": [{"content": {"parts": [{"text": json.dumps(obj) if text is None else text}]}}],
               "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 300, "thoughtsTokenCount": 200}}
    Gemini.reply = (status, json.dumps(payload).encode(), delay)
    Gemini.seen.clear()


def new_repo(env: str = ENV_ON) -> Path:
    repo = Path(tempfile.mkdtemp(prefix="second-opinion-"))
    for rel, text in (FILES | {".claude/project.env": env}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return repo


def valid(repo: Path, *changes: dict[str, Any]) -> list[dict[str, Any]]:
    result = simplifier.validate(repo, [GOOD | change for change in changes] or [GOOD], set())
    assert not result["rejected"], result["rejected"]
    return list(result["findings"])


def log_rows(repo: Path) -> list[dict[str, Any]]:
    return list(simplifier.second_log(repo))


def one(repo: Path, **kwargs: Any) -> dict[str, Any]:
    opinion: dict[str, Any] = second.review(repo, valid(repo), pause=0, **kwargs)[0]["second_opinion"]
    return opinion


server = ThreadingHTTPServer(("127.0.0.1", 0), Gemini)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ["SECOND_OPINION_API_BASE"] = f"http://127.0.0.1:{server.server_port}/v1beta"
os.environ[second.KEY_VAR] = KEY
os.environ.pop("GEMINI_API_KEY", None)
repos: list[Path] = []

print("SEND-*    what goes to the other model, and what never does")
repo = new_repo()
repos.append(repo)
answer("agree")
reviewed = second.review(repo, valid(repo))
sent = Gemini.seen[0] if Gemini.seen else {"path": "", "key": "", "body": ""}
check("one request per finding, to the configured model", len(Gemini.seen) == 1 and sent["path"] == "/v1beta/models/m-test:generateContent", Gemini.seen)
check("the key travels in the header and not in the address", sent["key"] == KEY and KEY not in sent["path"] and KEY not in sent["body"], sent["path"])
check("the claim, the target's code and the line that uses the name are sent",
      all(part in sent["body"] for part in ("old_total has no caller", "def old_total() -> int:", "from demo.pricing import old_total, total")), sent["body"][:900])
check("the simplifier's evidence, action, risk, test safety and traceability are not sent",
      not any(part in sent["body"] for part in ("EVIDENCE-MARK", "auto_remove", "characterization_exists", "reversal_risk", "TRACE-MARK")), sent["body"])
check("a protected path, an excluded path and the simplifier's own records are not sent",
      not any(part in sent["body"] for part in ("SECRET-MARK", "VENDOR-MARK", "RECORD-MARK")), sent["body"])
config = json.loads(sent["body"] or "{}").get("generationConfig", {})
check("temperature 0 and an answer by schema", config.get("temperature") == 0 and config.get("responseMimeType") == "application/json"
      and config.get("responseSchema", {}).get("properties", {}).get("verdict", {}).get("enum") == ["agree", "disagree", "unsure"], config)
row = (log_rows(repo) or [{}])[0]
check("agree is attached to the finding with the model's name", reviewed[0]["second_opinion"]["verdict"] == "agree"
      and reviewed[0]["second_opinion"]["model"] == "m-test" and reviewed[0]["id"] == row.get("finding"), reviewed[0])
check("the record has tokens (thinking counted as output), the cost from the configured prices, and both hashes",
      (row.get("tokens_in"), row.get("tokens_out"), row.get("cost_usd")) == (1000, 500, 0.008)
      and len(row.get("request_sha256", "")) == 64 and len(row.get("response_sha256", "")) == 64, row)
answer("agree")
second.review(repo, valid(repo, {"target": "secrets/tool.py:1", "claim": "the import is unused"}))
check("a finding on a protected path gets no request", not Gemini.seen and log_rows(repo)[-1]["verdict"] == "no_opinion"
      and "protected" in log_rows(repo)[-1]["reason"], log_rows(repo)[-1])

print("CHECK-*   the answer is checked like the simplifier's own")
answer("disagree", ["src/demo/cli.py:3"])
opinion = one(repo)
check("a disagreement citing a line that was sent is verified", opinion["verdict"] == "disagree" and opinion["verified"] is True
      and opinion["counter_evidence"][0]["verified"] is True, opinion)
for ref in ("src/demo/cli.py:999", "src/demo/nothing.py:1", "secrets/tool.py:1", "somewhere in cli"):
    answer("disagree", [ref])
    opinion = one(repo)
    check(f"an invented reference ({ref}) stays on record, unverified", opinion["verdict"] == "disagree" and opinion["verified"] is False
          and opinion["counter_evidence"][0] == {"ref": ref, "detail": "uses it", "verified": False}, opinion)
answer("disagree", ["src/demo/cli.py:999", "src/demo/cli.py:5"])
check("one real line among invented ones is enough, and each is marked", [c["verified"] for c in one(repo)["counter_evidence"]] == [False, True])
answer("agree", ["src/demo/cli.py:3"])
check("agree is never 'verified': the flag belongs to a disagreement", one(repo)["verified"] is False)
for name, text in (("not JSON", "I think it is fine"), ("an unknown verdict", '{"verdict": "maybe", "reason": "x", "counter_evidence": []}'),
                   ("a list", "[]"), ("no reason", '{"verdict": "agree"}')):
    answer("agree", text=text)
    opinion = one(repo)
    check(f"an answer that is {name}: no_opinion", opinion["verdict"] == "no_opinion" and "schema" in opinion["reason"], opinion)
answer("unsure", text='```json\n{"verdict": "unsure", "reason": "too little", "counter_evidence": []}\n```')
check("one code fence around the JSON is forgiven", one(repo)["verdict"] == "unsure")

print("FAIL-*    nothing that goes wrong stops the pass")
answer("agree", delay=0.5)
started = time.monotonic()
opinion = one(repo, timeout=0.1)
check("a timeout: no_opinion after two more tries", opinion["verdict"] == "no_opinion" and "no answer" in opinion["reason"] and len(Gemini.seen) == 3,
      (opinion, len(Gemini.seen), time.monotonic() - started))
time.sleep(0.5)
answer("agree", status=503)
check("a server error is tried three times", one(repo)["verdict"] == "no_opinion" and len(Gemini.seen) == 3, len(Gemini.seen))
Gemini.reply = (400, f"API key not valid: {KEY}".encode(), 0.0)
Gemini.seen.clear()
opinion = one(repo)
check("a refused request is not repeated, and the key is cut out of the error text",
      opinion["verdict"] == "no_opinion" and len(Gemini.seen) == 1 and "[key]" in opinion["reason"] and KEY not in json.dumps(opinion), opinion)
os.environ.pop(second.KEY_VAR)
os.environ["GEMINI_API_KEY"] = KEY
answer("agree")
opinion = one(repo)
check("no key: no_opinion naming the variable, nothing sent — and the general GEMINI_API_KEY is not read",
      opinion["verdict"] == "no_opinion" and second.KEY_VAR in opinion["reason"] and not Gemini.seen, (opinion, Gemini.seen))
os.environ.pop("GEMINI_API_KEY")
os.environ[second.KEY_VAR] = KEY
for missing in ("SECOND_OPINION_PRICE_IN", "SECOND_OPINION_PRICE_OUT", "SECOND_OPINION_MODEL"):
    bare = new_repo("\n".join(line for line in ENV_ON.splitlines() if not line.startswith(missing + "=")) + "\n")
    repos.append(bare)
    answer("agree")
    opinion = one(bare)
    check(f"without {missing} nothing is asked", opinion["verdict"] == "no_opinion" and not Gemini.seen, (opinion, Gemini.seen))
capped = new_repo(ENV_ON.replace('MAX_USD="2"', 'MAX_USD="0.005"'))
repos.append(capped)
answer("agree")
both = second.review(capped, valid(capped, {}, {"claim": "old_total is dead"}))
check("the pass limit: the first finding is asked, the one after the limit is not",
      [f["second_opinion"]["verdict"] for f in both] == ["agree", "no_opinion"] and len(Gemini.seen) == 1 and "limit" in both[1]["second_opinion"]["reason"], both)
check("the key is in no line of the record (four characters of its hash are)",
      KEY not in (repo / simplifier.SECOND_LOG_REL).read_text() and all(len(r["key_sha256_tail"]) == 4 for r in log_rows(repo) if "key_sha256_tail" in r))

print("LOWER-*   the table: the second opinion only lowers")


def lowered(action: str, verdict: str | None, verified: bool = False, required: bool = True) -> tuple[str, int]:
    item = {**valid(repo)[0], "proposed_action": action, "validator": []}
    if verdict is not None:
        item["second_opinion"] = {"verdict": verdict, "reason": "r", "counter_evidence": [], "verified": verified}
    out = simplifier.second_lowered(item, required)
    return out["proposed_action"], len(out["validator"])


check("auto_remove + agree stays auto_remove", lowered("auto_remove", "agree") == ("auto_remove", 0))
for verdict in ("disagree", "unsure", "no_opinion"):
    check(f"auto_remove + {verdict} becomes confirm", lowered("auto_remove", verdict) == ("confirm", 1))
check("auto_remove with no opinion at all, while the switch is on, becomes confirm", lowered("auto_remove", None) == ("confirm", 1))
check("…and is untouched while the switch is off", lowered("auto_remove", None, required=False) == ("auto_remove", 0))
check("an opinion that came with the finding lowers even with the switch off", lowered("auto_remove", "unsure", required=False) == ("confirm", 1))
check("a verdict nobody knows counts as no opinion", lowered("auto_remove", "certainly") == ("confirm", 1))
check("confirm + agree stays confirm, no note", lowered("confirm", "agree") == ("confirm", 0))
check("confirm + a verified disagreement becomes flag_only", lowered("confirm", "disagree", True) == ("flag_only", 1))
check("confirm + an unverified disagreement stays confirm, with a note", lowered("confirm", "disagree", False) == ("confirm", 1))
check("confirm + unsure stays confirm, with a note", lowered("confirm", "unsure") == ("confirm", 1))
for verdict in ("agree", "disagree", "unsure", "no_opinion"):
    check(f"flag_only + {verdict} stays flag_only", lowered("flag_only", verdict, True)[0] == "flag_only")
check("nothing is ever raised: flag_only + agree, confirm + agree",
      lowered("flag_only", "agree")[0] == "flag_only" and lowered("confirm", "agree")[0] == "confirm")

print("ROUTE-*   through the command line, as the builder runs it")


def cli(script: str, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(HOOKS / script), *args], cwd=repo, capture_output=True, text=True, check=False,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)})


work = new_repo()
repos.append(work)
SECOND = {"target": "src/demo/pricing.py:1", "claim": "total could be inlined", "proposed_action": "confirm"}
(work / "answer.json").write_text(json.dumps([GOOD, GOOD | SECOND]), encoding="utf-8")
cli("simplifier.py", work, "validate", "answer.json", "--out", "valid.json")
answer("disagree", ["src/demo/cli.py:3"])
done = cli("second_opinion.py", work, "review", "valid.json", "--out", "reviewed.json")
check("review writes the findings with the opinions", done.returncode == 0 and "disagree 2" in done.stderr
      and all("second_opinion" in f for f in json.loads((work / "reviewed.json").read_text())["findings"]), done.stderr)
routed = cli("simplifier.py", work, "route", "reviewed.json", "--title", "t")
report = (work / simplifier.REPORT_REL).read_text() if (work / simplifier.REPORT_REL).is_file() else ""
check("route: the automatic removal became the owner's question, the confirm a flag",
      routed.returncode == 0 and "0 auto_remove" in routed.stdout and "### confirm (1)" in report and "### flag_only (1)" in report, routed.stdout + report)
check("the report shows the second opinion, its reason, the checked line and the lowering",
      all(part in report for part in ("second opinion (m-test): disagree — because disagree", "src/demo/cli.py:3 (checked)",
                                      "auto_remove -> confirm: the second model did not agree", "confirm -> flag_only: the models disagree")), report)
agreed = new_repo()
repos.append(agreed)
(agreed / "answer.json").write_text(json.dumps([GOOD, GOOD | SECOND]), encoding="utf-8")
cli("simplifier.py", agreed, "validate", "answer.json", "--out", "valid.json")
answer("agree")
cli("second_opinion.py", agreed, "review", "valid.json", "--out", "reviewed.json")
routed = cli("simplifier.py", agreed, "route", "reviewed.json", "--title", "t")
check("with agreement the automatic removal stays for the builder", "1 auto_remove" in routed.stdout, routed.stdout)
data = json.loads((agreed / "reviewed.json").read_text())
data["findings"][0]["claim"] = "old_total and total have no caller"
(agreed / "forged.json").write_text(json.dumps(data), encoding="utf-8")
routed = cli("simplifier.py", agreed, "route", "forged.json", "--title", "t")
check("an agreement does not follow a finding whose text was changed after the review", "0 auto_remove" in routed.stdout, routed.stdout)
routed = cli("simplifier.py", agreed, "route", "valid.json", "--title", "t")
check("while the switch is on, a file that skipped the review removes nothing automatically", "0 auto_remove" in routed.stdout, routed.stdout)
mixed = new_repo()
repos.append(mixed)
(mixed / "answer.json").write_text(json.dumps([GOOD | {"proposed_action": "confirm", "claim": "first in the file"},
                                               GOOD | {"proposed_action": "confirm", "claim": "second in the file"}]), encoding="utf-8")
cli("simplifier.py", mixed, "validate", "answer.json", "--out", "valid.json")
data = json.loads((mixed / "valid.json").read_text())
for item, verdict in zip(data["findings"], ("agree", "disagree"), strict=True):
    item["second_opinion"] = {"verdict": verdict, "reason": "r", "counter_evidence": [], "verified": False, "model": "m-test"}
(mixed / "reviewed.json").write_text(json.dumps(data), encoding="utf-8")
cli("simplifier.py", mixed, "route", "reviewed.json", "--title", "t")
report = (mixed / simplifier.REPORT_REL).read_text()
check("the findings the models disagree on stand first", 0 < report.find("second in the file") < report.find("first in the file"), report)

off = new_repo(ENV_ON.replace('SECOND_OPINION="on"', 'SECOND_OPINION="off"'))
repos.append(off)
(off / "answer.json").write_text(json.dumps([GOOD]), encoding="utf-8")
cli("simplifier.py", off, "validate", "answer.json", "--out", "valid.json")
answer("disagree")
done = cli("second_opinion.py", off, "review", "valid.json", "--out", "reviewed.json")
check("switched off: nothing is sent and the findings pass unchanged",
      done.returncode == 0 and not Gemini.seen and "is off" in done.stderr and (off / "reviewed.json").read_text() == (off / "valid.json").read_text(), done.stderr)
routed = cli("simplifier.py", off, "route", "reviewed.json", "--title", "t")
check("…and the automatic removal is as it was before the second opinion existed",
      "1 auto_remove" in routed.stdout and not (off / simplifier.SECOND_LOG_REL).exists(), routed.stdout)
(off / "raw.json").write_text(json.dumps([GOOD]), encoding="utf-8")
check("review refuses a file that did not go through the validator", cli("second_opinion.py", work, "review", str(off / "raw.json")).returncode == 2)
leaked = [str(p) for r in repos for p in r.rglob("*") if p.is_file() and ".git/" not in str(p) and KEY in p.read_text(errors="replace")]
check("after everything above the key is in no file of any repository", not leaked, leaked)

print("LIVE-*    the owner's decisions, the reversal split, the cost")
ident = json.loads((work / "reviewed.json").read_text())["findings"][0]["id"]
done = cli("simplifier.py", work, "decide", ident, "ні")
decisions = simplifier.second_log(work, simplifier.DECISIONS_REL)
check("decide records the owner's «ні» with the second model's verdict next to it",
      done.returncode == 0 and decisions == [decisions[0]] and (decisions[0]["decision"], decisions[0]["second_opinion"]) == ("no", "disagree"), done.stdout)
check("decide refuses anything but так or ні, and a thing that is no finding id",
      cli("simplifier.py", work, "decide", ident, "maybe").returncode == 1 and cli("simplifier.py", work, "decide", "pricing", "так").returncode == 1)
shown = cli("simplifier.py", work, "reversals").stdout
check("reversals shows how the second model compares with the owner", "disagreed with 1 of the 1 the owner refused and with 0 of the 0" in shown, shown)
check("with no decision on record the line is absent", "Owner's decisions" not in cli("simplifier.py", agreed, "reversals").stdout)
(agreed / "src/demo/pricing.py").write_text(FILES["src/demo/pricing.py"].split("\n\n\ndef old_total")[0] + "\n", encoding="utf-8")
agreed_id = json.loads((agreed / "reviewed.json").read_text())["findings"][0]["id"]
subprocess.run(["git", "-C", str(agreed), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m",
                f"simplify: old_total\n\nSimplifier-Finding: {agreed_id}", "src/demo/pricing.py"], check=True, capture_output=True)
rate = simplifier.reversals(agreed, 20)
check("a removal the second model agreed with is counted apart", rate["second_opinion_agreed"] == {"removals": 1, "returned": 0}
      and "of the 1 the second model agreed with, 0 came back" in simplifier.reversal_text(rate), rate)
check("…and one it never saw is not", simplifier.reversals(off, 20)["second_opinion_agreed"]["removals"] == 0)
text = cli("second_opinion.py", work, "cost").stdout
check("cost adds up what the record holds", "$0.02 for 2 finding(s) in all" in text and "disagree 2" in text, text)
check("cost on an empty record says so", "no second opinion" in cli("second_opinion.py", off, "cost").stdout)

print("SEED-*    other projects start with it switched off")
seed = (ROOT / "templates/project/.claude/project.env").read_text(encoding="utf-8")
check("the seed of a new project says SECOND_OPINION=\"off\" and warns that code is sent to Google",
      '\nSECOND_OPINION="off"\n' in seed and "GOOGLE" in seed and second.KEY_VAR in seed, "")
check("a project.env without the key at all is off", second.settings({})["on"] is False and second.settings({"SECOND_OPINION": "ON"})["on"] is True)
check("the hook names no other source of the key", "GEMINI_API_KEY\"" not in (HOOKS / "second_opinion.py").read_text() and second.KEY_VAR == "GEMINI_API_KEY_SIMPLIFIER")

server.shutdown()
for path in repos:
    shutil.rmtree(path, ignore_errors=True)
print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
