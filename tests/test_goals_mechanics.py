#!/usr/bin/env python3
"""Level 0 and its use, as far as a script can check it (board 201, slice goals-mechanics): the contract tests.

Written from the sealed contract `.engine/slices/goals-mechanics.md` before the code existed, by the
slice tester. Every expected value here is written by hand from the contract.

  1. `core_error` alone, and the core required of every NEW text: `seal` (unsealed, and changed
     with `--owner-approved`), `first-seal` (through owner_action.py `seal-goals` too), `proposal`,
     `amend` (through owner_action.py `amend-goals` too); the core in a comment (Seam 1);
  2. `status`'s «no core» line, and a document sealed before the slice staying in force (Seam 2, I2);
  3. `NOT_REQUIRED`: `requests`, `quote`, the owner's review (Seam 6);
  4. the matrix and the maps: `is_decision`, `citations`, `check` and `unreconciled` on the matrix,
     the review list after an amendment (Seam 5), `trace_errors` and `goals.py trace` (Seams 3, 4,
     I3, I4);
  5. A3's quote pair, kept: a quote is verbatim with the mark `[не слова власника]`.

The test that depends on a question to the contract is in tests/test_goals_mechanics_disputed.py.

Run:   python3 tests/test_goals_mechanics.py            # every case
       python3 tests/test_goals_mechanics.py <test>     # one case by its name (test_I1_..., ...)
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from hook_env import hook_env, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
GOALS = ROOT / ".claude/hooks/goals.py"
OWNER_ACTION = ROOT / ".claude/unattended/owner_action.py"
TEMPLATE = ROOT / "templates/project/.engine/goals.md"
SEAL_REL = ".claude/state/goals/goals.sha256"
TRACE = ".engine/architecture/traceability.md"
DOMAIN = ".engine/architecture/domain-map.md"
ARCH = ".engine/architecture/architecture-map.md"
ADR = "docs/adr/0001-cache.md"

NO_SECTION = "no «## Ядро» section: the owner names the goals without which the product loses its sense"
NO_STANDING = "«Ядро» names no standing goal G"
NO_MATRIX = f"{TRACE}: no matrix (a table whose first column is «Рядок»)"
NO_SOURCE = " has no source (a G, P, C or D line, or an owner's decision in docs/adr/): remove it or move it to «## Пропозиції»"
NR_END = "документ цього не вимагає (NOT_REQUIRED) — не будується, вас не турбували"

P1_LINE = "- P1. Свіжість даних понад швидкість відповіді. Приклад: залишок читаємо без кешу [не слова власника]."
P1_NEW = "- P1. Швидкість відповіді понад свіжість даних. Приклад: залишок показуємо з кешу на хвилину.\n- P2. Простота понад гнучкість. Приклад: один спосіб оплати."
G1_TEXT = "Покупець оформлює замовлення сам — видно з того, що дзвінків до оператора немає [не слова власника]."

# A document as it is sealed today: no «## Ядро» section.
DOC_OLD = f"""# Цілі проєкту крамниця
Версія: 1

## Для кого і навіщо
Покупець замовляє сам, без дзвінка оператору.

## Цілі
- G1. {G1_TEXT}
- ~~G2. Оператор бачить усі замовлення на одному екрані.~~ (скасовано)
- G3. Склад бачить замовлення одразу.

## Принципи (що понад що)
{P1_LINE}

## Не-цілі
- N1. Не робимо мобільного застосунку — бо покупці приходять з пошуку.

## Жорсткі обмеження
- C1. Дані покупців лишаються в ЄС — джерело: закон.

## Готово, коли
- D1. Сто замовлень на день без оператора.

## Відкрите
- Q1. Чи потрібна доставка — до вирішення архітектори вважають: ні.

## Зміни
- v1 — перша версія.
"""
CORE_GOOD = "- G1 — «щоб покупець замовляв сам»"


def with_core(body: str, base: str = DOC_OLD, heading: str = "## Ядро") -> str:
    return base.replace("## Цілі\n", f"{heading}\n{body}\n\n## Цілі\n", 1)


def amended(text: str) -> str:
    """A lawful amendment of a version-1 text: P1 changed, P2 added, the version raised, a line in «Зміни»."""
    return (text.replace("Версія: 1", "Версія: 2").replace(P1_LINE, P1_NEW)
            .replace("- v1 — перша версія.", "- v1 — перша версія.\n- v2 — P1 перевернуто, додано P2."))


DOC_CORE = with_core(CORE_GOOD)
GOOD_ADR = "# ADR 1\n\n## Звірка з цілями\n- служить: G1\n- вибір розв'язав: P1\n- не-цілі й обмеження: N1 не зачеплено\n"
QUOTE_REQUEST = "# Запит 001\nFrom: feature-architect\nReason: 1\nDoor: two-way\n\n## Відповідь business analyst-а\nANALYST_ANSWER: QUOTE\nLine: {line}\nQuote: {quote}\n"
NR_REQUEST = ("# Запит 004\nFrom: feature-architect\nReason: 2\nDoor: two-way\n\n## Відповідь business analyst-а\n"
              "ANALYST_ANSWER: QUOTE\nLine: G1\nQuote: щось\nLines: G1\n\n## Друга відповідь\nANALYST_ANSWER: NOT_REQUIRED\nLines: G3, P1\n")

MATRIX_HEAD = "# Матриця трасування\n\n| Рядок | Як читаю | Елементи дизайну | Статус |\n|---|---|---|---|\n"
ALL_STANDING = ("G1", "G3", "P1", "N1", "C1", "D1", "Q1")
BASE_ROWS = (("Замовлення", "G1"), ("Склад", "P1"), ("Регіон", "C1"), ("Звіт", "D1"), ("Кеш", ADR))

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900].replace('Error', 'Err.')}")


_loaded: dict[str, ModuleType] = {}


def by_path(name: str, path: Path) -> ModuleType:
    """A module loaded from its file, registered under `name` (board_review's own `import goals` finds it)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def goals() -> ModuleType:
    if "goals" not in _loaded:
        _loaded["goals"] = by_path("goals", GOALS)
    return _loaded["goals"]


def board_review() -> ModuleType:
    if "board_review" not in _loaded:
        goals()
        for folder in (".claude/hooks", ".claude/unattended"):   # its own imports (board, goals), as the suites load it
            if str(ROOT / folder) not in sys.path:
                sys.path.insert(0, str(ROOT / folder))
        _loaded["board_review"] = by_path("board_review", ROOT / ".claude/unattended/board_review.py")
    return _loaded["board_review"]


def matrix(*ids: str, extra: str = "") -> str:
    return MATRIX_HEAD + "".join(f"| {i} | як читаю {i} | Замовлення | є |\n" for i in ids) + extra


def table(rows: tuple[tuple[str, str], ...] | list[tuple[str, str]], head: str = "| Елемент | Що це | Джерело |") -> str:
    return head + "\n|---|---|---|\n" + "".join(f"| {name} | опис | {source} |\n" for name, source in rows)


def domain(outside: tuple[tuple[str, str], ...] | list[tuple[str, str]] = BASE_ROWS, proposals: tuple[tuple[str, str], ...] | list[tuple[str, str]] = ()) -> str:
    text = "# Карта домену\n\n## Звірка з цілями\n- служить: G1\n\n## Сутності\n" + table(outside)
    if proposals:
        text += "\n## Пропозиції\n" + table(proposals)
    return text


def run(script: Path, root: Path, *args: str, session: bool = False) -> subprocess.CompletedProcess[str]:
    env = hook_env(root)
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_UNATTENDED_SESSION", None)
    if session:
        env["CLAUDECODE"] = "1"
    return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env, check=False)


def out(proc: subprocess.CompletedProcess[str]) -> str:
    return f"rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project(doc: str | None = DOC_CORE, sealed: bool = False, files: dict[str, str] | None = None) -> Path:
    """A temporary project; `sealed` records the document's fingerprint as `goals.py seal` writes it."""
    root = Path(sandbox_dir("goals-mechanics-"))
    (root / ".engine/goals/requests").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if doc is not None:
        (root / ".engine/goals.md").write_text(doc, encoding="utf-8")
    if sealed:
        assert doc is not None
        seal = root / SEAL_REL
        seal.parent.mkdir(parents=True, exist_ok=True)
        seal.write_text(f"{sha(doc)}  .engine/goals.md\n", encoding="utf-8")
    for rel, text in (files or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def seal_value(root: Path) -> str:
    seal = root / SEAL_REL
    return seal.read_text(encoding="utf-8").split()[0] if seal.is_file() else ""


def stderr_lines(proc: subprocess.CompletedProcess[str]) -> list[str]:
    return proc.stderr.splitlines()


# ------------------------------------------------------------------ 1. the core


def test_core_error_no_section() -> None:
    check("a text with no «## Ядро» heading: the no-section sentence", goals().core_error(DOC_OLD) == NO_SECTION, goals().core_error(DOC_OLD))


def test_core_error_heading_forms() -> None:
    for name, text in (("## Ядро", DOC_CORE), ("## Core", with_core(CORE_GOOD, heading="## Core")),
                       ("## Ядро with trailing spaces", with_core(CORE_GOOD, heading="## Ядро   "))):
        got = goals().core_error(text)
        check(f"{name} naming the standing G1: no error", got == "", got)


def test_core_error_cites_missing_g() -> None:
    got = goals().core_error(with_core("- G1 — «сам»\n- G9 — «ще»"))
    check("a cited G that is not a line: the G9 sentence (even beside a standing G1)",
          got == "«Ядро» cites G9, which is not a line of the goals document", got)


def test_core_error_cites_struck_g() -> None:
    got = goals().core_error(with_core("- G2 — «екран»"))
    check("a cited struck G: the G2 sentence", got == "«Ядро» cites G2, which is struck out", got)


def test_core_error_first_in_body_order() -> None:
    first_missing = goals().core_error(with_core("- G9 — «ще»\n- G2 — «екран»"))
    first_struck = goals().core_error(with_core("- G2 — «екран»\n- G9 — «ще»"))
    check("G9 before G2 in the body: the G9 sentence", first_missing == "«Ядро» cites G9, which is not a line of the goals document", first_missing)
    check("G2 before G9 in the body: the G2 sentence", first_struck == "«Ядро» cites G2, which is struck out", first_struck)


def test_core_error_no_standing_g() -> None:
    for name, body in (("only P1 and N1", "- P1 — «свіжість»\n- N1 — «без застосунку»"), ("an empty body", ""),
                       ("prose with no number", "ціль, без якої продукт втрачає сенс")):
        got = goals().core_error(with_core(body))
        check(f"{name}: the no-standing-G sentence", got == NO_STANDING, got)


def test_core_error_comment_removed() -> None:
    for name, body in (("a one-line comment", "<!-- - G1 — «сам» -->"),
                       ("a comment across lines", "<!-- Номери цілей:\n- G1 — «сам»\n- G3 — «склад» -->")):
        got = goals().core_error(with_core(body))
        check(f"G1 only inside {name}: not counted", got == NO_STANDING, got)
    got = goals().core_error(with_core("<!-- - G9 — «ще» -->\n- G3 — «склад»"))
    check("a G9 inside a comment is not read; the G3 outside it stands", got == "", got)


def test_core_error_id_rule() -> None:
    got = goals().core_error(with_core("- версіяG1 та G1-бета, G1x"))
    check("G1 as part of a longer word is not a goal number", got == NO_STANDING, got)


def test_core_error_body_ends_at_heading() -> None:
    text = with_core("ціль ще не названо")
    later = DOC_OLD.replace("## Цілі\n", "## Ядро\nще не названо\n### Деталі\n- G1 — «сам»\n\n## Цілі\n", 1)
    level5 = DOC_OLD.replace("## Цілі\n", "## Ядро\nще не названо\n##### Деталі\n- G1 — «сам»\n\n## Цілі\n", 1)
    got_text, got_later, got_level5 = (goals().core_error(t) for t in (text, later, level5))
    check("the G1 lines under «Цілі» are not the core's", got_text == NO_STANDING, got_text)
    check("the body ends at a `### ` heading", got_later == NO_STANDING, got_later)
    check("a `##### ` line is not a HEADING: the body runs on", got_level5 == "", got_level5)


def test_seal_unsealed_refuses_without_core() -> None:
    root = project(DOC_OLD)
    r = run(GOALS, root, "seal")
    check("seal of an unsealed text with no core: REFUSED, exit 3, no seal",
          r.returncode == 3 and f"REFUSED: {NO_SECTION}" in stderr_lines(r) and not (root / SEAL_REL).exists(), out(r))
    good = project(DOC_CORE)
    r = run(GOALS, good, "seal")
    check("…the same text with a core is sealed", r.returncode == 0 and seal_value(good) == sha(DOC_CORE), out(r))


def test_seal_changed_owner_approved_refuses_without_core() -> None:
    root = project(DOC_CORE, sealed=True)
    changed = DOC_OLD.replace("одразу", "за хвилину")
    (root / ".engine/goals.md").write_text(changed, encoding="utf-8")
    r = run(GOALS, root, "seal", "--owner-approved")
    check("--owner-approved on a changed text with no core: REFUSED, exit 3, the old seal stays",
          r.returncode == 3 and f"REFUSED: {NO_SECTION}" in stderr_lines(r) and seal_value(root) == sha(DOC_CORE), out(r))
    with_one = with_core(CORE_GOOD, base=changed)
    (root / ".engine/goals.md").write_text(with_one, encoding="utf-8")
    r = run(GOALS, root, "seal", "--owner-approved")
    check("…the changed text with a core is sealed", r.returncode == 0 and seal_value(root) == sha(with_one), out(r))


def test_seal_core_in_template_comment_refused() -> None:
    """Seam 1: the template filled with lines, the core only in its comment."""
    seed = TEMPLATE.read_text(encoding="utf-8")
    filled = (seed.replace("## Цілі\n", "## Цілі\n- G1. Покупець оформлює замовлення сам.\n", 1)
              .replace("## Принципи (що понад що)\n", "## Принципи (що понад що)\n- P1. Свіжість понад швидкість.\n", 1))
    root = project(filled)
    r = run(GOALS, root, "seal")
    check("the template with G1 and the core's example comment naming G1: REFUSED, no seal",
          r.returncode == 3 and f"REFUSED: {NO_STANDING}" in stderr_lines(r) and not (root / SEAL_REL).exists(), out(r))


def test_first_seal_refuses_without_core() -> None:
    root = project(DOC_OLD)
    r = run(OWNER_ACTION, root, "--root", str(root), "seal-goals", sha(DOC_OLD))
    check("seal-goals on the owner's «так» for a text with no core: exit 1, the sentence, no seal",
          r.returncode == 1 and NO_SECTION in r.stderr and not (root / SEAL_REL).exists(), out(r))
    r = run(GOALS, root, "first-seal", sha(DOC_OLD))
    check("goals.py first-seal: `first-seal: <sentence>`, exit 1, no seal",
          r.returncode == 1 and f"first-seal: {NO_SECTION}" in r.stderr and not (root / SEAL_REL).exists(), out(r))
    bare = "# Цілі\n\nХочемо, щоб було добре.\n"
    r = run(GOALS, project(bare), "first-seal", sha(bare))
    check("…the numbered-line check comes first", r.returncode == 1 and "no numbered line" in r.stderr and NO_SECTION not in r.stderr, out(r))
    old = project(DOC_OLD, sealed=True)
    r = run(GOALS, old, "first-seal", sha(DOC_OLD))
    check("…and a sealed document returns early, whatever its core", r.returncode == 0 and seal_value(old) == sha(DOC_OLD), out(r))
    good = project(DOC_CORE)
    r = run(GOALS, good, "first-seal", sha(DOC_CORE))
    check("…a text with a core is sealed", r.returncode == 0 and seal_value(good) == sha(DOC_CORE), out(r))


def test_proposal_refuses_without_core() -> None:
    root = project(DOC_OLD, sealed=True, files={".engine/goals/proposed.md": amended(DOC_OLD)})
    r = run(GOALS, root, "proposal")
    check("a lawful amendment with no core: proposal REFUSED, exit 3", r.returncode == 3 and f"REFUSED: {NO_SECTION}" in stderr_lines(r), out(r))
    (root / ".engine/goals/proposed.md").write_text(amended(DOC_CORE), encoding="utf-8")
    r = run(GOALS, root, "proposal")
    check("…with a core it is accepted (Seam 2)", r.returncode == 0, out(r))


def test_amend_refuses_without_core() -> None:
    proposal = amended(DOC_OLD)
    root = project(DOC_OLD, sealed=True, files={".engine/goals/proposed.md": proposal})
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha(proposal))
    check("amend-goals with a proposal that has no core: exit 1, nothing written",
          r.returncode == 1 and (root / ".engine/goals.md").read_text(encoding="utf-8") == DOC_OLD and seal_value(root) == sha(DOC_OLD), out(r))
    r = run(GOALS, root, "amend", sha(proposal))
    check("goals.py amend: `amend: …` naming the core, exit 1, nothing written",
          r.returncode == 1 and "amend: " in r.stderr and NO_SECTION in r.stderr
          and (root / ".engine/goals.md").read_text(encoding="utf-8") == DOC_OLD and (root / ".engine/goals/proposed.md").is_file(), out(r))
    good = amended(DOC_CORE)
    (root / ".engine/goals/proposed.md").write_text(good, encoding="utf-8")
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha(good))
    check("…with a core it is applied and sealed (Seam 2)",
          r.returncode == 0 and (root / ".engine/goals.md").read_text(encoding="utf-8") == good and seal_value(root) == sha(good), out(r))


def accepted(path: str, text: str) -> tuple[bool, str]:
    """Whether `text` (a version-1 document) is taken as new text by one of the five paths."""
    if path == "seal unsealed":
        root = project(text)
        r = run(GOALS, root, "seal")
        return r.returncode == 0 and seal_value(root) == sha(text), out(r)
    if path == "seal changed --owner-approved":
        root = project(DOC_CORE, sealed=True)
        changed = text.replace("одразу", "за хвилину")
        (root / ".engine/goals.md").write_text(changed, encoding="utf-8")
        r = run(GOALS, root, "seal", "--owner-approved")
        return r.returncode == 0 and seal_value(root) == sha(changed), out(r)
    if path == "first-seal":
        root = project(text)
        r = run(OWNER_ACTION, root, "--root", str(root), "seal-goals", sha(text))
        return r.returncode == 0 and seal_value(root) == sha(text), out(r)
    new = amended(text)
    root = project(DOC_OLD, sealed=True, files={".engine/goals/proposed.md": new})
    if path == "proposal":
        r = run(GOALS, root, "proposal")
        return r.returncode == 0, out(r)
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha(new))
    return r.returncode == 0 and (root / ".engine/goals.md").read_text(encoding="utf-8") == new, out(r)


def test_I1_no_new_text_without_a_core_naming_a_standing_g() -> None:
    refused = {
        "no «## Ядро» section": DOC_OLD,
        "the core only in a one-line comment": with_core("<!-- - G1 — «сам» -->"),
        "the core only in a comment across lines": with_core("<!--\n- G1 — «сам»\n-->"),
        "the core names only the struck G2": with_core("- G2 — «екран»"),
        "the core names only G9, not a line": with_core("- G9 — «ще»"),
        "the core names a standing G1 and the missing G9": with_core("- G1 — «сам»\n- G9 — «ще»"),
        "the core names P1 and N1, no G": with_core("- P1 — «свіжість»\n- N1 — «без застосунку»"),
        "an empty core": with_core(""),
    }
    lawful = {
        "the core names G1": DOC_CORE,
        "`## Core` names G3 and P1": with_core("- G3 — «склад» і P1", heading="## Core"),
        "a comment naming G9 and G3 outside it": with_core("<!-- - G9 -->\n- G3 — «склад»"),
    }
    for path in ("seal unsealed", "seal changed --owner-approved", "first-seal", "proposal", "amend"):
        for name, text in refused.items():
            ok, detail = accepted(path, text)
            check(f"{path}: refused — {name}", not ok, detail)
        for name, text in lawful.items():
            ok, detail = accepted(path, text)
            check(f"{path}: accepted after the refusals — {name}", ok, detail)


# ------------------------------------------------------------------ 2. status, and an old document in force


def test_status_no_core_line_sealed() -> None:
    root = project(DOC_OLD, sealed=True)
    r = run(GOALS, root, "status")
    want = f"no core: {NO_SECTION} — the next amendment must add it"
    lines = r.stdout.splitlines()
    check("a sealed document with no core: exit 0, today's line, then the «no core» line",
          r.returncode == 0 and len(lines) >= 2 and lines[-1] == want and "is the document the owner approved" in r.stdout, out(r))
    r = run(GOALS, project(DOC_CORE, sealed=True), "status")
    check("…a sealed document with a core has no such line", r.returncode == 0 and "no core" not in r.stdout + r.stderr, out(r))


def test_status_no_core_line_unsealed_and_changed() -> None:
    want = f"no core: {NO_SECTION} — it is not sealed without one"
    r = run(GOALS, project(DOC_OLD), "status")
    check("an unsealed document with no core: exit 4 as today, the «not sealed without one» line",
          r.returncode == 4 and want in r.stdout.splitlines(), out(r))
    root = project(DOC_CORE, sealed=True)
    (root / ".engine/goals.md").write_text(DOC_OLD, encoding="utf-8")
    r = run(GOALS, root, "status")
    check("a changed document with no core: exit 3 as today, the same line", r.returncode == 3 and want in r.stdout.splitlines(), out(r))
    struck = with_core("- G2 — «екран»")
    r = run(GOALS, project(struck), "status")
    check("…the sentence is core_error's: a struck G2", "no core: «Ядро» cites G2, which is struck out — it is not sealed without one" in r.stdout.splitlines(), out(r))
    r = run(GOALS, project(TEMPLATE.read_text(encoding="utf-8")), "status")
    check("…a document with no numbered line has no second line", "no core" not in r.stdout + r.stderr, out(r))
    r = run(GOALS, project(DOC_OLD + "- G1. Ще раз.\n"), "status")
    check("…nor one whose items cannot be read (a number twice)", "no core" not in r.stdout + r.stderr, out(r))


def outcomes(doc: str) -> dict[str, int]:
    """The exit code of every command that reads a sealed document."""
    root = project(doc, sealed=True, files={ADR: "# ADR 1\n\n## Звірка з цілями\n- служить: G1\n", "docs/adr/0002-bad.md": "# ADR 2\n\n## Звірка з цілями\n- служить: G9\n",
                                            ".engine/goals/requests/001.md": QUOTE_REQUEST.format(line="G1", quote=G1_TEXT)})
    return {
        "status": run(GOALS, root, "status").returncode,
        "check a cited decision": run(GOALS, root, "check", ADR).returncode,
        "check a decision citing G9": run(GOALS, root, "check", "docs/adr/0002-bad.md").returncode,
        "check with no file": run(GOALS, root, "check").returncode,
        "quote": run(GOALS, root, "quote", ".engine/goals/requests/001.md").returncode,
        "requests": run(GOALS, root, "requests").returncode,
        "unreconciled": run(GOALS, root, "unreconciled").returncode,
        "affected": run(GOALS, root, "affected", "G1").returncode,
        "seal": run(GOALS, root, "seal").returncode,
    }


MINIMAL = f"# Цілі\nВерсія: 1\n\n## Цілі\n- G1. {G1_TEXT}\n\n## Зміни\n- v1 — перша версія.\n"


def test_I2_old_sealed_document_keeps_state_and_exit_codes() -> None:
    hand = {"status": 0, "check a cited decision": 0, "check a decision citing G9": 3, "check with no file": 3, "quote": 0}
    for name, doc in (("no «Ядро» at all", DOC_OLD),
                      ("«Ядро» only as a level-3 heading", DOC_OLD.replace("## Цілі\n", "### Ядро\n- G1 — «сам»\n\n## Цілі\n", 1)),
                      ("one goal line and «Зміни», nothing else", MINIMAL)):
        old = outcomes(doc)
        cored = outcomes(with_core(CORE_GOOD, base=doc))
        check(f"{name}: the exit codes written by hand", all(old[k] == v for k, v in hand.items()), old)
        check(f"{name}: every command exits as for the same document with a core", old == cored, {"no core": old, "core": cored})


# ------------------------------------------------------------------ 3. NOT_REQUIRED


def test_requests_not_required() -> None:
    root = project(DOC_CORE, sealed=True, files={".engine/goals/requests/004.md": NR_REQUEST,
                                                 ".engine/goals/requests/005.md": NR_REQUEST.replace("Lines: G3, P1\n", ""),
                                                 ".engine/goals/requests/006.md": ("# Запит 006\nReason: 3\n\nANALYST_ANSWER: NOT_REQUIRED\nLines: G3\n\n"
                                                                                                f"ANALYST_ANSWER: QUOTE\nLine: G1\nQuote: {G1_TEXT}\n")})
    r = run(GOALS, root, "requests")
    rows = {line.split("\t")[0].rsplit("/", 1)[-1]: line.split("\t") for line in r.stdout.splitlines()}
    check("the last answer NOT_REQUIRED: `not-required`, and the `Lines:` after it (not the earlier answer's)",
          rows.get("004.md", [])[1:4] == ["reason 2", "not-required", "G3, P1"], out(r))
    check("…with no `Lines:` after it, an empty detail", rows.get("005.md", [])[2:3] == ["not-required"] and rows["005.md"][3:4] in ([], [""]), out(r))
    check("…an earlier NOT_REQUIRED followed by a QUOTE is the quote's", rows.get("006.md", [])[2:3] == ["quote-valid"], out(r))
    got = goals().request_outcome(".engine/goals/requests/004.md", NR_REQUEST, DOC_CORE)
    check("request_outcome: Request(path, reason, 'not-required', the lines)",
          (got.path, got.outcome, got.detail) == (".engine/goals/requests/004.md", "not-required", "G3, P1"), got)


def test_quote_refuses_not_required() -> None:
    root = project(DOC_CORE, sealed=True, files={".engine/goals/requests/004.md": NR_REQUEST})
    r = run(GOALS, root, "quote", ".engine/goals/requests/004.md")
    check("quote on a NOT_REQUIRED answer: REFUSED, exit 3, and nothing about the owner",
          r.returncode == 3 and "REFUSED: the analyst answers NOT_REQUIRED: there is no quote to check" in stderr_lines(r)
          and "goes to the owner" not in r.stderr and "it goes to the owner" not in r.stderr, out(r))


class Tree:
    """What board_review.Source gives the goals section: the files of one commit and their text."""

    def __init__(self, texts: dict[str, str]) -> None:
        self.texts, self.files = texts, frozenset(texts)

    def show(self, path: str) -> str:
        return self.texts.get(path, "")


def test_review_shows_not_required() -> None:
    """Seam 6."""
    shown = "\n".join(board_review().goals_section(Tree({".engine/goals.md": DOC_CORE, ".engine/goals/requests/004.md": NR_REQUEST})))
    check("the owner's review renders a NOT_REQUIRED request with its sentence",
          f"`004.md` (привід 2): {NR_END}" in shown, shown)


# ------------------------------------------------------------------ 4. the matrix and the maps


def test_is_decision_domain_map_and_matrix() -> None:
    check("domain-map.md is a decision", goals().is_decision(DOMAIN) is True)
    check("traceability.md is a decision", goals().is_decision(TRACE) is True)
    root = project(DOC_CORE, sealed=True, files={DOMAIN: "# Карта домену\n\nБез звірки.\n"})
    r = run(GOALS, root, "unreconciled")
    check("unreconciled lists a domain map with no «Звірка з цілями»", f"{DOMAIN}:" in r.stdout and "no «Звірка з цілями» section" in r.stdout, out(r))


def test_citations_of_the_matrix() -> None:
    text = ("# Матриця\n\n| Поле | Значення |\n|---|---|\n| G7 | інша таблиця |\n\n"
            "| Рядок | Як читаю | Елементи |\n|---|---|---|\n| P1 | x | y |\n| G1 | x | y |\n| P1 | x | y |\n| Разом | x | y |\n"
            "| g3 | x | y |\n| G3a | x | y |\n| G3, P1 | x | y |\n|  D1  | x | y |\n\nТекст G9 після таблиці.\n\n| Рядок | x |\n|---|---|\n| C1 | друга матриця |\n")
    got = goals().citations(TRACE, text)
    check("the first «Рядок» table: its rows' first cells, in order, no repeat; a cell that is not a number gives nothing",
          got == (True, ["P1", "G1", "D1"]), got)
    english = goals().citations(TRACE, "| Line | x |\n|---|---|\n| Q1 | y |\n")
    check("…`Line` as the first header cell", english == (True, ["Q1"]), english)
    empty = goals().citations(TRACE, MATRIX_HEAD)
    check("…a matrix with no row", empty == (False, []), empty)
    none = goals().citations(TRACE, "# Матриця\n\nG1 і P1, але без таблиці.\n")
    check("…no table at all", none == (False, []), none)


def test_citations_of_other_paths() -> None:
    for path in (ADR, DOMAIN, ".engine/architecture/feature/cart.md"):
        for text in (GOOD_ADR, "# ADR\n\nНема розділу. G1.\n", MATRIX_HEAD + "| G1 | x | y | z |\n"):
            got = goals().citations(path, text)
            check(f"{path}: cited(text)", got == goals().cited(text), (got, goals().cited(text)))


def test_check_reads_the_matrix_rows() -> None:
    root = project(DOC_CORE, sealed=True, files={TRACE: matrix("G1", "P1", "N1")})
    r = run(GOALS, root, "check", TRACE)
    check("check on the matrix: ok, and the ok line lists its rows", r.returncode == 0 and f"ok: {TRACE}" in r.stdout and "cites G1, P1, N1" in r.stdout, out(r))
    (root / TRACE).write_text(MATRIX_HEAD, encoding="utf-8")
    r = run(GOALS, root, "check", TRACE)
    check("…a matrix with no row: refused with «the matrix has no row»", r.returncode == 3 and "the matrix has no row" in r.stderr, out(r))
    (root / TRACE).write_text(matrix("G1", "G9"), encoding="utf-8")
    r = run(GOALS, root, "check", TRACE)
    check("…a row of a number the document lacks: refused", r.returncode == 3 and "G9 is not a line" in r.stderr, out(r))


def test_unreconciled_reads_the_matrix_rows() -> None:
    root = project(DOC_CORE, sealed=True, files={TRACE: matrix("G1", "G2")})
    r = run(GOALS, root, "unreconciled")
    check("unreconciled: the matrix with a struck G2 row is listed", f"{TRACE}:" in r.stdout and "G2 is struck out" in r.stdout, out(r))
    (root / TRACE).write_text(matrix(*ALL_STANDING), encoding="utf-8")
    r = run(GOALS, root, "unreconciled")
    check("…a matrix of standing rows (and no «Звірка з цілями») is not", TRACE not in r.stdout, out(r))


def review_after_amend(matrix_ids: tuple[str, ...]) -> tuple[subprocess.CompletedProcess[str], str]:
    new = amended(DOC_CORE)
    root = project(DOC_CORE, sealed=True, files={
        DOMAIN: "# Карта домену\n\n## Звірка з цілями\n- служить: G1\n- вибір розв'язав: P1\n",
        TRACE: matrix(*matrix_ids),
        ".engine/goals/proposed.md": new,
    })
    r = run(OWNER_ACTION, root, "--root", str(root), "amend-goals", sha(new))
    review = root / ".engine/goals/to-review.md"
    return r, review.read_text(encoding="utf-8") if review.is_file() else ""


def test_review_list_after_amend() -> None:
    """Seam 5."""
    r, review = review_after_amend(ALL_STANDING)
    check("amend changed P1: the domain map citing P1 is in to-review.md", r.returncode == 0 and f"P1 → {DOMAIN}" in review, out(r) + review)
    check("…and the matrix with a P1 row", f"P1 → {TRACE}" in review, review)
    r, review = review_after_amend(("G1", "G3", "N1", "C1", "D1", "Q1"))
    check("a matrix without a P1 row is not; the domain map still is", r.returncode == 0 and f"P1 → {DOMAIN}" in review and TRACE not in review, out(r) + review)


def trace(texts: dict[str, str], adrs: tuple[str, ...] = (ADR,), doc: str = DOC_CORE) -> tuple[list[str], int]:
    present = {rel for rel, text in texts.items() if text} | set(adrs)
    errors, count = goals().trace_errors(lambda p: texts.get(p, ""), goals().items(doc), lambda p: p in present)
    return list(errors), count


def test_trace_errors_pass() -> None:
    got = trace({TRACE: matrix(*ALL_STANDING), DOMAIN: domain()})
    check("every standing line has a row (the struck G2 none), every element a valid source; the absent architecture map is not checked",
          got == ([], 5), got)


def test_trace_errors_no_matrix() -> None:
    for name, text in (("absent", ""), ("with no table", "# Матриця\n\nG1 — Замовлення.\n"), ("with another table", "| Поле | x |\n|---|---|\n| G1 | y |\n")):
        errors, count = trace({TRACE: text, DOMAIN: domain()})
        check(f"the matrix {name}: the no-matrix sentence", NO_MATRIX in errors and count == 5, (errors, count))


def test_trace_errors_matrix_rows() -> None:
    errors, _ = trace({TRACE: matrix(*ALL_STANDING, extra="| Разом | x | y | z |\n"), DOMAIN: domain()})
    check("a row whose first cell is not a number", errors == [f"{TRACE}: a row names no line: «Разом»"], errors)
    errors, _ = trace({TRACE: matrix(*ALL_STANDING, "G1"), DOMAIN: domain()})
    check("a number with two rows", errors == [f"{TRACE}: G1 has two rows"], errors)
    errors, _ = trace({TRACE: matrix(*ALL_STANDING, "G9"), DOMAIN: domain()})
    check("a number the document lacks", errors == [f"{TRACE}: G9 is not a line of the goals document"], errors)


def test_trace_errors_struck_and_missing_lines() -> None:
    """Seam 4."""
    errors, _ = trace({TRACE: matrix("G1", "G2", "G3", "P1", "N1", "C1", "D1", "Q1"), DOMAIN: domain()})
    check("a struck G with a row is refused", errors == [f"{TRACE}: G2 is struck out of the goals document"], errors)
    errors, _ = trace({TRACE: matrix("G1", "G3", "N1", "C1", "D1"), DOMAIN: domain()})
    check("a standing P and a standing Q with no row are refused; the struck G2 without one is fine",
          sorted(errors) == sorted([f"{TRACE}: P1 has no row", f"{TRACE}: Q1 has no row"]), errors)


def test_trace_errors_map_tables() -> None:
    errors, _ = trace({TRACE: matrix(*ALL_STANDING), DOMAIN: "# Карта домену\n\n## Сутності\nЗамовлення — G1.\n"})
    check("a map with no element table", errors == [f"{DOMAIN}: no element table (a table whose first column is «Елемент»)"], errors)
    errors, _ = trace({TRACE: matrix(*ALL_STANDING), DOMAIN: domain(), ARCH: "# Карта\n\n" + table([("Сервіс", "G1")], head="| Елемент | Що це | Звідки |")})
    check("an element table with no «Джерело» column", errors == [f"{ARCH}: the element table has no «Джерело» column"], errors)


def test_trace_errors_element_sources() -> None:
    rows = (*BASE_ROWS, ("Звіти", "G9"), ("Екран", "G2"), ("Черга", "docs/adr/0009-none.md"), ("Доставка", "Q1"), ("Детектор", "N1"))
    errors, count = trace({TRACE: matrix(*ALL_STANDING), DOMAIN: domain(rows)})
    by_name = {name: [e for e in errors if f"«{name}»" in e] for name, _ in rows}
    check("an ID that is not a line: the matrix's sentence prefixed by the map and the element",
          any(e.startswith(f"{DOMAIN}: «Звіти»") and e.endswith("G9 is not a line of the goals document") for e in by_name["Звіти"]), errors)
    check("a struck ID: the same", any(e.startswith(f"{DOMAIN}: «Екран»") and e.endswith("G2 is struck out of the goals document") for e in by_name["Екран"]), errors)
    check("an ADR path that is not a file", f"{DOMAIN}: «Черга»: docs/adr/0009-none.md is not a file" in errors, errors)
    check("only a Q: no source", f"{DOMAIN}: «Доставка»{NO_SOURCE}" in errors, errors)
    check("only an N: the non-goal sentence",
          f"{DOMAIN}: «Детектор»: its only source is the non-goal N1 — a non-goal is a boundary, not a source: remove it or move it to «## Пропозиції»" in errors, errors)
    check("the rows with a valid source are not named", not any(by_name[name] for name, _ in BASE_ROWS), errors)
    check("every row outside «Пропозиції» is counted", count == 10, count)


def test_seam3_n_only_element_cli() -> None:
    """Seam 3, through `goals.py trace`."""
    for name, outside, proposals, rc, count in (
        ("outside «Пропозиції», only N1: refused naming N1", (*BASE_ROWS, ("Детектор", "N1")), (), 3, 6),
        ("the same row with N1, G3: fine", (*BASE_ROWS, ("Детектор", "N1, G3")), (), 0, 6),
        ("the same row under «## Пропозиції»: fine, not counted", BASE_ROWS, (("Детектор", "N1"),), 0, 5),
    ):
        root = project(DOC_CORE, sealed=True, files={TRACE: matrix(*ALL_STANDING), DOMAIN: domain(outside, proposals), ADR: GOOD_ADR})
        r = run(GOALS, root, "trace")
        named = any(line.startswith("REFUSED: ") and "«Детектор»" in line and "N1" in line for line in stderr_lines(r))
        check(f"{name} (exit {rc}, count {count})",
              r.returncode == rc and named == (rc == 3) and f"elements outside «Пропозиції»: {count}" in r.stdout.splitlines(), out(r))


def test_trace_cli_refusals() -> None:
    root = project(DOC_CORE, sealed=True, files={TRACE: matrix("G1", "G2", "G3", "N1", "C1", "D1", "Q1", extra="| Разом | x | y | z |\n"),
                                                 DOMAIN: "# Карта домену\n\nБез таблиці.\n", ADR: GOOD_ADR})
    r = run(GOALS, root, "trace")
    want = {f"REFUSED: {TRACE}: G2 is struck out of the goals document", f"REFUSED: {TRACE}: P1 has no row",
            f"REFUSED: {TRACE}: a row names no line: «Разом»", f"REFUSED: {DOMAIN}: no element table (a table whose first column is «Елемент»)"}
    check("trace: every error as `REFUSED: <sentence>` on stderr, exit 3, the count on stdout",
          r.returncode == 3 and want <= set(stderr_lines(r)) and "elements outside «Пропозиції»: 0" in r.stdout.splitlines(), out(r))


def test_trace_cli_pass() -> None:
    root = project(DOC_CORE, sealed=True, files={TRACE: matrix(*ALL_STANDING), DOMAIN: domain(), ADR: GOOD_ADR})
    r = run(GOALS, root, "trace")
    check("trace on a sound matrix and map: exit 0, the count, nothing refused",
          r.returncode == 0 and r.stdout.splitlines() == ["elements outside «Пропозиції»: 5"] and "REFUSED" not in r.stderr, out(r))


def test_trace_cli_needs_a_sealed_document() -> None:
    files = {TRACE: matrix(*ALL_STANDING), DOMAIN: domain(), ADR: GOOD_ADR}
    r = run(GOALS, project(DOC_CORE, files=files), "trace")
    check("unsealed: today's check behaviour, exit 4", r.returncode == 4 and "no approval is recorded" in r.stderr, out(r))
    root = project(DOC_CORE, sealed=True, files=files)
    (root / ".engine/goals.md").write_text(DOC_CORE.replace("одразу", "за хвилину"), encoding="utf-8")
    r = run(GOALS, root, "trace")
    check("changed: exit 3, CHANGED", r.returncode == 3 and "CHANGED" in r.stderr, out(r))
    r = run(GOALS, project(None, files=files), "trace")
    check("absent: exit 4", r.returncode == 4, out(r))


def test_I3_element_passes_only_with_a_valid_source_and_never_by_a_non_goal() -> None:
    outside = [("A_G1", "G1"), ("A_P", "P1"), ("A_C", "C1"), ("A_D", "D1"), ("A_ADR", f"див. {ADR}"), ("A_N", "N1"), ("A_Q", "Q1"),
               ("A_STRUCK", "G2"), ("A_MISSING", "G9"), ("A_ADRNO", "docs/adr/0009-none.md"), ("A_EMPTY", ""), ("A_NG", "N1, G3"), ("A_QP", "Q1 і P1"),
               ("A_NN", "N1 N1")]
    second = "\n## Процеси\nТекст між таблицями.\n\n" + table([("B_N", "N1"), ("B_G", "G3")]).replace("| опис |", f"| опис {ADR} G1 |")
    domain_text = domain(outside, [("C_N", "N1"), ("C_EMPTY", "")]).replace("\n## Пропозиції\n", second + "\n## Пропозиції\n")
    arch_text = ("# Architecture map\n\n## Components\n" + table([("D_N", "N1"), ("D_D", "D1")], head="| Element | Kind | Source |")
                 + "\n## Proposals\n" + table([("E_Q", "Q1")], head="| Element | Kind | Source |"))
    errors, count = trace({TRACE: matrix(*ALL_STANDING), DOMAIN: domain_text, ARCH: arch_text})
    refused = {"A_N", "A_Q", "A_STRUCK", "A_MISSING", "A_ADRNO", "A_EMPTY", "A_NN", "B_N", "D_N"}
    every = {name for name, _ in outside} | {"B_N", "B_G", "C_N", "C_EMPTY", "D_N", "D_D", "E_Q"}
    for name in sorted(every):
        named = [e for e in errors if f"«{name}»" in e]
        check(f"{name}: {'refused' if name in refused else 'not refused'}", bool(named) == (name in refused), named or errors)
    check("an N-only row is refused naming the non-goal, in both maps",
          all(any("its only source is the non-goal N1" in e for e in errors if f"«{n}»" in e) for n in ("A_N", "B_N", "D_N")), errors)
    check("the count: the rows outside «Пропозиції» of both maps (14 + 2 + 2)", count == 18, count)


def test_I4_trace_prints_the_count_whether_or_not_it_refuses() -> None:
    arch = "# Architecture map\n\n## Components\n" + table([("Service", "G1"), ("Worker", "N1")], head="| Element | Kind | Source |")
    for name, files, count in (
        ("a pass", {TRACE: matrix(*ALL_STANDING), DOMAIN: domain()}, 5),
        ("a refusal: Q1 has no row", {TRACE: matrix("G1", "G3", "P1", "N1", "C1", "D1"), DOMAIN: domain()}, 5),
        ("no matrix at all", {DOMAIN: domain()}, 5),
        ("no map at all", {TRACE: matrix(*ALL_STANDING)}, 0),
        ("nothing at all", {}, 0),
        ("only proposals in the domain map", {TRACE: matrix(*ALL_STANDING), DOMAIN: domain((), (("Детектор", "N1"),)).replace("## Сутності\n| Елемент | Що це | Джерело |\n|---|---|---|\n", "")}, 0),
        ("both maps, a refused row in the second", {TRACE: matrix(*ALL_STANDING), DOMAIN: domain(), ARCH: arch}, 7),
        ("a map with no element table", {TRACE: matrix(*ALL_STANDING), DOMAIN: "# Карта\n\nТекст.\n"}, 0),
    ):
        root = project(DOC_CORE, sealed=True, files={**files, ADR: GOOD_ADR})
        r = run(GOALS, root, "trace")
        check(f"{name}: exactly one count line, {count}",
              [line for line in r.stdout.splitlines() if line.startswith("elements outside")] == [f"elements outside «Пропозиції»: {count}"], out(r))


# ------------------------------------------------------------------ 5. A3, kept


def test_A3_quote_keeps_the_mark() -> None:
    root = project(DOC_CORE, sealed=True)
    request = root / ".engine/goals/requests/001.md"
    request.write_text(QUOTE_REQUEST.format(line="G1", quote=G1_TEXT), encoding="utf-8")
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("a verbatim quote with [не слова власника] stands", r.returncode == 0 and "the quote stands" in r.stdout, out(r))
    request.write_text(QUOTE_REQUEST.format(line="G1", quote=G1_TEXT.replace(" [не слова власника]", "")), encoding="utf-8")
    r = run(GOALS, root, "quote", ".engine/goals/requests/001.md")
    check("the same quote with the mark dropped is refused", r.returncode == 3 and "is not the text of G1" in r.stderr, out(r))


TESTS: dict[str, Callable[[], None]] = {name: fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)}


def main(argv: list[str], tests: dict[str, Callable[[], None]] | None = None) -> int:
    global FAIL
    cases = TESTS if tests is None else tests
    wanted = argv or list(cases)
    unknown = [name for name in wanted if name not in cases]
    if unknown:
        print(f"no case named {', '.join(unknown)}; the cases: {', '.join(cases)}")
        return 2
    for name in wanted:
        print(name)
        try:
            cases[name]()
        # gate-allow: the suite's own runner must count a case that raises as a failed case and still run the next one
        except Exception as error:  # noqa: BLE001
            FAIL += 1
            last = traceback.extract_tb(error.__traceback__)[-1]
            print(f"  FAIL {name} raised {type(error).__name__.replace('Error', 'Err.')}: {str(error)[:300]}   ({Path(last.filename).name}:{last.lineno})")
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
