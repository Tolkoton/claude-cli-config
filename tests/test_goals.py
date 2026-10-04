#!/usr/bin/env python3
"""The goals document is sealed, cited by number, and changed only on the owner's word (board 051).

`goals.py` against a temporary project, the refusals first:

  - `check` refuses a decision with no «Звірка з цілями» section, one that cites a number the
    document does not have, one that cites a struck-out number, and everything once the document
    differs from its fingerprint; it passes a decision that cites standing lines;
  - `quote` refuses a quote that is not the text of the named line, and a quote of a struck line;
    it accepts the verbatim line;
  - `seal`: the first seal is refused in an unattended session; a changed document is re-sealed
    only with `--owner-approved` outside a Claude Code session;
  - an amendment may not drop a number, revive a struck one or keep the version; `amend` (the
    board runner's action, through owner_action.py) is refused inside a session and for another
    sha256; applied, it seals the new document and lists what cited a changed line for review;
  - the board offers `amend-goals` as an owner action with the sha256 of the proposal;
  - `unreconciled` and `requests` list what the owner's review shows;
  - the lesson queue takes the source `analyst`; the simplifier never removes from the goals
    document by itself.

Run:   python3 tests/test_goals.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOALS = ROOT / ".claude/hooks/goals.py"
OWNER_ACTION = ROOT / ".claude/unattended/owner_action.py"
BOARD = ROOT / ".claude/unattended/board.py"
LESSONS = ROOT / ".claude/hooks/lesson_queue.py"
PASS = FAIL = 0

DOCUMENT = """# Цілі проєкту крамниця
Версія: 1 · Затвердив власник: сьогодні

## Цілі
- G1. Покупець оформлює замовлення сам — видно з того, що дзвінків до оператора немає.
- ~~G2. Оператор бачить усі замовлення на одному екрані.~~ (скасовано)

## Принципи (що понад що)
- P1. Свіжість даних понад швидкість відповіді. Приклад: залишок на складі читаємо без кешу.

## Не-цілі
- N1. Не робимо мобільного застосунку — бо покупці приходять з пошуку.

## Зміни
- v1 — перша версія.
"""
AMENDED = DOCUMENT.replace("Версія: 1", "Версія: 2").replace(
    "- P1. Свіжість даних понад швидкість відповіді. Приклад: залишок на складі читаємо без кешу.",
    "- P1. Швидкість відповіді понад свіжість даних. Приклад: залишок на складі показуємо з кешу на хвилину.\n- P2. Простота понад гнучкість. Приклад: один спосіб оплати.",
).replace("- v1 — перша версія.", "- v1 — перша версія.\n- v2 — P1 перевернуто, додано P2 (запит 001).")
GOOD = "# ADR 1\n\n## Звірка з цілями\n- служить: G1\n- вибір розв'язав: P1\n- не-цілі й обмеження: N1 не зачеплено\n\n## Далі\nG9 тут не рахується.\n"
REQUEST = "# Запит 001\nFrom: feature-architect\nReason: 1\nDoor: two-way\n\n## Рішення\nКеш чи ні.\n\n## Відповідь аналітика\nANALYST_ANSWER: QUOTE\nLine: {line}\nQuote: {quote}\n"
P1_TEXT = "Свіжість даних понад швидкість відповіді. Приклад: залишок на складі читаємо без кешу."


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:500]}")


def run(script: Path, root: Path, *args: str, session: bool = False, unattended: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_UNATTENDED_SESSION")}
    env["CLAUDE_PROJECT_DIR"] = str(root)
    if session:
        env["CLAUDECODE"] = "1"
    if unattended:
        env["CLAUDE_UNATTENDED_SESSION"] = "1"
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env, check=False)


def project(tmp: str) -> Path:
    root = Path(tmp)
    (root / ".engine/goals/requests").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    (root / ".engine/goals.md").write_text(DOCUMENT, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def out(proc: subprocess.CompletedProcess[str]) -> str:
    return f"rc={proc.returncode} {proc.stdout} {proc.stderr}"


with tempfile.TemporaryDirectory() as tmp:
    root = project(tmp)
    adr = root / "docs/adr/0001-cache.md"

    print("before any approval")
    r = run(GOALS, root, "check")
    check("check: an unsealed document is not in force (exit 4)", r.returncode == 4 and "no approval is recorded" in r.stderr, out(r))
    r = run(GOALS, root, "seal", session=True, unattended=True)
    check("seal: the first approval is refused in an unattended session", r.returncode == 2 and not (root / ".claude/state/goals/goals.sha256").exists(), out(r))
    r = run(GOALS, root, "seal", session=True)
    check("seal: the first approval, attended, writes the fingerprint", r.returncode == 0 and (root / ".claude/state/goals/goals.sha256").is_file(), out(r))

    print("check: citations")
    adr.write_text("# ADR 1\n\nWe cache. It serves G1.\n", encoding="utf-8")
    r = run(GOALS, root, "check", "docs/adr/0001-cache.md")
    check("refused: no «Звірка з цілями» section", r.returncode == 3 and "no «Звірка з цілями» section" in r.stderr, out(r))
    adr.write_text("# ADR 1\n\n## Звірка з цілями\nвибір технічний\n", encoding="utf-8")
    r = run(GOALS, root, "check", "docs/adr/0001-cache.md")
    check("refused: a section that cites no line", r.returncode == 3 and "cites no line" in r.stderr, out(r))
    adr.write_text(GOOD.replace("G1", "G7"), encoding="utf-8")
    r = run(GOALS, root, "check", "docs/adr/0001-cache.md")
    check("refused: a number the document does not have", r.returncode == 3 and "G7 is not a line" in r.stderr, out(r))
    adr.write_text(GOOD.replace("G1", "G2"), encoding="utf-8")
    r = run(GOALS, root, "check", "docs/adr/0001-cache.md")
    check("refused: a struck-out number", r.returncode == 3 and "G2 is struck out" in r.stderr, out(r))
    adr.write_text(GOOD, encoding="utf-8")
    r = run(GOALS, root, "check", "docs/adr/0001-cache.md")
    check("passes: standing lines cited; numbers outside the section are not read", r.returncode == 0 and "cites G1, P1, N1" in r.stdout, out(r))
    (root / "docs/adr/0002-queue.md").write_text("# ADR 2\n\nNo section.\n", encoding="utf-8")
    (root / "docs/adr/README.md").write_text("# ADRs\n", encoding="utf-8")
    r = run(GOALS, root, "unreconciled")
    check("unreconciled lists the decision without a citation, not the cited one and not the README",
          r.returncode == 0 and r.stdout.count("\n") == 1 and r.stdout.startswith("docs/adr/0002-queue.md:"), out(r))
    r = run(GOALS, root, "check")
    check("check with no file judges every decision", r.returncode == 3 and "ok: docs/adr/0001-cache.md" in r.stdout and "0002-queue.md" in r.stderr, out(r))

    print("quote: «the document already answers» only with a line of the document")
    request = root / ".engine/goals/requests/001.md"
    request.write_text(REQUEST.format(line="P1", quote="Швидкість понад усе."), encoding="utf-8")
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("refused: a quote the document does not contain", r.returncode == 3 and "is not the text of P1" in r.stderr and "goes to the owner" in r.stderr, out(r))
    request.write_text(REQUEST.format(line="G2", quote="Оператор бачить усі замовлення на одному екрані."), encoding="utf-8")
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("refused: a quote of a struck-out line", r.returncode == 3 and "struck out" in r.stderr, out(r))
    request.write_text(REQUEST.format(line="P9", quote=P1_TEXT), encoding="utf-8")
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("refused: the right text under a number that does not exist", r.returncode == 3 and "P9 is not a line" in r.stderr, out(r))
    request.write_text(REQUEST.format(line="P1", quote=f"«{P1_TEXT}»"), encoding="utf-8")
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("accepted: the verbatim line", r.returncode == 0 and "the quote stands" in r.stdout, out(r))
    (root / ".engine/goals/requests/002.md").write_text("# Запит 002\nReason: 2\n\n## Відповідь аналітика\nANALYST_ANSWER: OWNER_DECISION\nПитання: що понад що?\n", encoding="utf-8")
    (root / ".engine/goals/requests/003.md").write_text("# Запит 003\nReason: 3\n", encoding="utf-8")
    r = run(GOALS, root, "requests")
    rows = [line.split("\t") for line in r.stdout.splitlines()]
    check("requests lists each with its reason and how it ended",
          [row[1:3] for row in rows] == [["reason 1", "quote-valid"], ["reason 2", "owner"], ["reason 3", "unanswered"]], out(r))

    print("a changed document is not in force")
    (root / ".engine/goals.md").write_text(DOCUMENT.replace("без кешу", "з кешем"), encoding="utf-8")
    r = run(GOALS, root, "check", "docs/adr/0001-cache.md")
    check("check refuses everything when the document left its fingerprint", r.returncode == 3 and "CHANGED" in r.stderr and "ok:" not in r.stdout, out(r))
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("quote refuses against a changed document", r.returncode == 3 and "CHANGED" in r.stderr, out(r))
    r = run(GOALS, root, "seal", "--owner-approved", session=True)
    check("re-seal: --owner-approved inside a session does not count", r.returncode == 2 and "refused inside a Claude Code session" in r.stderr, out(r))
    r = run(GOALS, root, "seal")
    check("re-seal: refused without the owner's flag", r.returncode == 3, out(r))
    check("…and the document is still not in force", run(GOALS, root, "status").returncode == 3)
    (root / ".engine/goals.md").write_text(DOCUMENT, encoding="utf-8")
    check("the approved text back: in force again", run(GOALS, root, "status").returncode == 0)

    print("amendment: only a lawful one, only on the owner's word")
    proposed = root / ".engine/goals/proposed.md"
    for name, text, expect in (
        ("a dropped number", AMENDED.replace("- N1. Не робимо мобільного застосунку — бо покупці приходять з пошуку.\n", ""), "N1 is gone"),
        ("a revived struck number", AMENDED.replace("- ~~G2. Оператор бачить усі замовлення на одному екрані.~~ (скасовано)", "- G2. Щось нове."), "never used again"),
        ("the same version", AMENDED.replace("Версія: 2", "Версія: 1"), "the version must grow"),
        ("no line in «Зміни»", AMENDED.replace("- v2 — P1 перевернуто, додано P2 (запит 001).", ""), "«Зміни» has no line"),
        ("a number used twice", AMENDED + "- P2. Ще раз.\n", "numbered twice"),
    ):
        proposed.write_text(text, encoding="utf-8")
        r = run(GOALS, root, "proposal")
        check(f"proposal refused: {name}", r.returncode == 3 and expect in r.stderr, out(r))
    proposed.write_text(AMENDED.replace("- N1.", "- X1."), encoding="utf-8")
    sha = hashlib.sha256(proposed.read_bytes()).hexdigest()
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha)
    check("amend refuses an unlawful amendment (exit 1) and leaves the document", r.returncode == 1 and (root / ".engine/goals.md").read_text(encoding="utf-8") == DOCUMENT, out(r))
    proposed.write_text(AMENDED, encoding="utf-8")
    sha = hashlib.sha256(proposed.read_bytes()).hexdigest()
    r = run(GOALS, root, "proposal")
    check("proposal accepted: P1 changed, the decision that cites it named", r.returncode == 0 and "changed or struck: P1" in r.stdout
          and "docs/adr/0001-cache.md (cites P1)" in r.stdout and sha in r.stdout, out(r))
    r = run(BOARD, root, "--root", str(root), "action-line", "amend-goals")
    check("the board offers the action with the proposal's sha256", r.stdout.strip() == f"Дія виконавця: amend-goals {sha}", out(r))
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha, session=True)
    check("amend is refused inside a session", r.returncode == 2 and (root / ".engine/goals.md").read_text(encoding="utf-8") == DOCUMENT, out(r))
    r = run(GOALS, root, "amend", sha, session=True)
    check("…and so is goals.py amend typed by an agent", r.returncode == 2 and proposed.is_file(), out(r))
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", "0" * 64)
    check("amend with another sha256 is stale (exit 3)", r.returncode == 3 and (root / ".engine/goals.md").read_text(encoding="utf-8") == DOCUMENT, out(r))
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha)
    review = (root / ".engine/goals/to-review.md").read_text(encoding="utf-8") if (root / ".engine/goals/to-review.md").is_file() else ""
    check("amend on the owner's word: the new document, sealed, the proposal gone",
          r.returncode == 0 and (root / ".engine/goals.md").read_text(encoding="utf-8") == AMENDED and not proposed.exists()
          and run(GOALS, root, "status").returncode == 0, out(r))
    check("the decision that cited the changed line is marked for review, once", review.count("- [ ] v2 P1 → docs/adr/0001-cache.md") == 1 and "0002" not in review, review)
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("yesterday's quote no longer stands against the amended line", r.returncode == 3, out(r))
    r = run(GOALS, root, "affected", "P1", "N1")
    check("affected names the decision by line", r.stdout.splitlines() == ["docs/adr/0001-cache.md: cites P1", "docs/adr/0001-cache.md: cites N1"], out(r))

    print("no document at all")
    (root / ".engine/goals.md").unlink()
    check("check says there is nothing to reconcile with (exit 4)", run(GOALS, root, "check").returncode == 4)
    r = run(GOALS, root, "unreconciled")
    check("unreconciled lists nothing without a document", r.returncode == 4 and not r.stdout, out(r))

    print("the lesson queue and the simplifier")
    r = run(LESSONS, root, "add", "--source", "analyst", "did not ask who pays for delivery")
    queue = (root / ".engine/lesson-queue.md").read_text(encoding="utf-8") if (root / ".engine/lesson-queue.md").is_file() else ""
    check("a lesson from the owner's correction of the analyst is queued with the source `analyst`", r.returncode == 0 and "| analyst |" in queue, out(r) + queue)
    r = run(LESSONS, root, "add", "--source", "nobody", "x")
    check("an unknown source is still refused", r.returncode != 0, out(r))

print("the owner's review")
sys.path.insert(0, str(ROOT / ".claude/unattended"))
sys.path.insert(0, str(ROOT / ".claude/hooks"))
import board_review  # noqa: E402
import simplifier  # noqa: E402


class Tree:
    """What board_review.Source gives the section: the files of one commit and their text."""

    def __init__(self, texts: dict[str, str]) -> None:
        self.texts, self.files = texts, frozenset(texts)

    def show(self, path: str) -> str:
        return self.texts.get(path, "")


seed = (ROOT / "templates/project/.engine/goals.md").read_text(encoding="utf-8")
empty = "\n".join(board_review.goals_section(Tree({"docs/adr/0001-cache.md": "# ADR\n"})))  # type: ignore[arg-type]
check("no goals document: one line, and no decision is called unreconciled", "ще немає" in empty and "0001" not in empty and "###" not in empty, empty)
seeded = "\n".join(board_review.goals_section(Tree({".engine/goals.md": seed, "docs/adr/0001-cache.md": "# ADR\n"})))  # type: ignore[arg-type]
check("the unfilled seed counts as no document", seeded == empty, seeded)
shown = "\n".join(board_review.goals_section(Tree({  # type: ignore[arg-type]
    ".engine/goals.md": AMENDED,
    "docs/adr/0001-cache.md": GOOD,
    "docs/adr/0002-queue.md": "# ADR 2\n",
    ".engine/architecture/feature/cart.md": "# Feature\n\n## Звірка з цілями\n- служить: G2\n",
    ".engine/goals/requests/001.md": REQUEST.format(line="N1", quote="Не робимо мобільного застосунку — бо покупці приходять з пошуку."),
    ".engine/goals/requests/002.md": REQUEST.format(line="P1", quote="Свіжість понад усе."),
    ".engine/goals/to-review.md": "# x\n\n- [ ] v2 P1 → docs/adr/0001-cache.md\n- [x] v2 P1 → docs/adr/0009-old.md\n",
    ".engine/goals/proposed.md": AMENDED,
    ".engine/lesson-queue.md": "# q\n- 2026-10-04 | analyst | - | did not ask who pays for delivery #0a1b2c3d\n- 2026-10-04 | agent | - | other #0a1b2c3e\n",
})))
check("the review: the document's version and lines", "версія 2, чинних рядків 4, закреслених 1" in shown, shown)
check("the review: a decision with no citation and one citing a struck line are unreconciled; the cited one is not",
      "`docs/adr/0002-queue.md` — no «Звірка з цілями» section" in shown and "`.engine/architecture/feature/cart.md` — G2 is struck out" in shown
      and "`docs/adr/0001-cache.md` —" not in shown, shown)
check("the review: a request closed by a quote shows the quoted line", "`001.md` (привід 1): закрито цитатою документа, вас не турбували — N1: Не робимо" in shown, shown)
check("the review: a false quote is shown as going to the owner", "`002.md` (привід 1): цитата НЕ збігається з документом" in shown, shown)
check("the review: the amendments, what waits for the architect's reread, the pending proposal",
      "v2 — P1 перевернуто" in shown and "Чекає перегляду архітектором після поправки: v2 P1 → docs/adr/0001-cache.md" in shown
      and "0009-old" not in shown and "чекає вашого «так»" in shown, shown)
check("the review: the analyst's lessons, and only the analyst's", "did not ask who pays" in shown and "other #" not in shown, shown)

print("definitions: who reads level 0 and who must not")
CLAUDE = ROOT / ".claude"
READS = ("commands/business-analyst.md", "agents/business-analyst.md", "commands/master-architect.md", "commands/feature-architect.md",
         "commands/mvp-architect.md", "agents/master-critic.md", "agents/feature-critic.md", "agents/mvp-critic.md")
BLIND = ("commands/plan-slice.md", "skills/slice-builder/SKILL.md", "agents/overseer.md", "agents/slice-planner-critic.md", "skills/overseer/SKILL.md")


def mentions_goals(text: str) -> bool:
    return bool(re.search(r"goals\.md|goals\.py|business-analy|Звірка з цілями", text))


for rel in READS:
    check(f"{rel} reads the goals document", ".engine/goals.md" in (CLAUDE / rel).read_text(encoding="utf-8"))
for rel in BLIND:
    check(f"{rel} neither reads the goals document nor calls the analyst", not mentions_goals((CLAUDE / rel).read_text(encoding="utf-8")))
slice_dirs = [p for p in (CLAUDE / "skills/slice-builder").rglob("*.md")]
check("nothing under the slice builder's skill does either", not [p.name for p in slice_dirs if mentions_goals(p.read_text(encoding="utf-8"))])
check("the blindness check catches a planted reference", mentions_goals("read `.engine/goals.md` first") and mentions_goals("start the agent business-analyst")
      and not mentions_goals("the slice's goal and its exit criterion"))
for rel in ("agents/master-critic.md", "agents/feature-critic.md", "agents/mvp-critic.md"):
    text = (CLAUDE / rel).read_text(encoding="utf-8")
    check(f"{rel}: the goals lens checks non-goals and inverted principles and names the line", "non-goal" in text and "inverted" in text and "number" in text)
analyst = (CLAUDE / "agents/business-analyst.md").read_text(encoding="utf-8")
check("the analyst agent has no editing tool and no model of its own", "\ntools: Read, Grep, Glob\n" in analyst and "\nmodel:" not in analyst.split("---")[1])
master = (CLAUDE / "commands/master-architect.md").read_text(encoding="utf-8")
check("/master-architect does not start a new project without the approved document", "goals.py status" in master and "do not start" in master)
feature = (CLAUDE / "commands/feature-architect.md").read_text(encoding="utf-8")
check("/feature-architect warns and works as before; its report says which goals the feature advances",
      "warn the owner" in feature and "work as before" in feature and "Які цілі вона просуває" in feature)
check("/mvp-architect does not require the document", "not required" in (CLAUDE / "commands/mvp-architect.md").read_text(encoding="utf-8"))
for rel in ("commands/master-architect.md", "commands/feature-architect.md"):
    text = (CLAUDE / rel).read_text(encoding="utf-8")
    check(f"{rel}: «Звірка з цілями», the four reasons, the quote check", "Звірка з цілями" in text and "four reasons" in text and "goals.py quote" in text)

print("the method reference carries nothing private")
PRIVATE = {
    "an e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "a link": re.compile(r"https?://|www\."),
    "a phone number": re.compile(r"\+?\d[\d\s()-]{8,}\d"),
    "a sum of money": re.compile(r"[$€£₴]\s?\d|\d[\d\s.,]*\s?(?:грн|USD|EUR|UAH|дол|євро|dollars?|euros?)\b", re.IGNORECASE),
}
method = (CLAUDE / "references/business-analysis.md").read_text(encoding="utf-8")
for what, pattern in PRIVATE.items():
    found = pattern.search(method)
    check(f"no sign of {what}", found is None, found.group(0) if found else "")
planted = {"an e-mail address": "write to ivan@client.example", "a link": "see https://client.example/crm", "a phone number": "call +380 44 123 45 67",
           "a sum of money": "the contract was 40 000 грн"}
for what, text in planted.items():
    check(f"the check catches {what}", PRIVATE[what].search(text) is not None)
check("the reference says where its lines come from", "lesson queue" in method and "does not rewrite its own method" in method)
seed_items = __import__("goals").items(seed)
check("the seed has every section and no line of its own", not seed_items and all(h in seed for h in ("## Цілі", "## Принципи", "## Не-цілі", "## Жорсткі обмеження", "## Готово, коли", "## Відкрите", "## Зміни")), seed_items)
ownership = (CLAUDE / "ownership.txt").read_text(encoding="utf-8")
check("the goals document is the project's, seeded once", re.search(r"^project\s+\.engine/goals\.md\s+seed=templates/project/\.engine/goals\.md$", ownership, re.MULTILINE) is not None)

finding = {"target": ".engine/goals.md:12", "claim": "N1 duplicates G1", "traceability": "none", "category": "duplication",
           "evidence": [{"source": "read", "ref": ".engine/goals.md:12", "detail": "x"}], "protected": False, "chesterton_checked": True,
           "test_safety": "none", "proposed_action": "auto_remove", "reversal_risk": "low"}
lowered = simplifier.lowered({}, finding)
check("a simplifier finding about the goals document is protected and never automatic", lowered["protected"] and lowered["proposed_action"] == "confirm", lowered)
check("…while the same finding about another record may be automatic", simplifier.lowered({}, {**finding, "target": ".engine/notes.md:12"})["proposed_action"] == "auto_remove")

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
