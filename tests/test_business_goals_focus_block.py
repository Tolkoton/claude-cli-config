#!/usr/bin/env python3
"""Feature business-goals-focus as one block: the integration tests (board 201, slice tester, mode `block`).

Written from the feature artifact `.engine/architecture/feature/business-goals-focus.md` («Inter-slice
contracts», «Integration exit criterion», the acceptance criteria A1–A8) and the public interface of
`goals.py` (its usage lines), not from the bodies. Every expected value is written by hand from the
artifact and S1's sealed contract `.engine/slices/goals-mechanics.md`.

  link_*  the S1 → S2 connection: what S2's definitions tell the agents to write is what S1's script reads
          (the `## Ядро` section of the template, the `NOT_REQUIRED` form of the agent, the example matrix and
          element table of `/master-architect` through `goals.py trace`, the subcommands the texts name);
  A1–A8   one test per acceptance criterion, through the command line of `goals.py` on a temporary project.

A9 (the task's report) depends on a question to the artifact: tests/test_business_goals_focus_block_disputed.py.

Run:   python3 tests/test_business_goals_focus_block.py            # every case
       python3 tests/test_business_goals_focus_block.py <test>     # one case by its name
Exit:  0 = all green, 1 = at least one case failed, 2 = no case of that name.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

from hook_env import hook_env, sandbox_dir

ROOT = Path(__file__).resolve().parent.parent
GOALS = ROOT / ".claude/hooks/goals.py"
TEMPLATE = ROOT / "templates/project/.engine/goals.md"
MASTER_ARCHITECT = ROOT / ".claude/commands/master-architect.md"
ANALYST_AGENT = ROOT / ".claude/agents/business-analyst.md"
ANALYST_COMMAND = ROOT / ".claude/commands/business-analyst.md"
MASTER_CRITIC = ROOT / ".claude/agents/master-critic.md"
REFERENCE = ROOT / ".claude/references/business-analysis.md"
OWNER_GUIDE = ROOT / "docs/OWNER-GUIDE.md"
SEAL_REL = ".claude/state/goals/goals.sha256"
TRACE = ".engine/architecture/traceability.md"
DOMAIN = ".engine/architecture/domain-map.md"
COUNT = "elements outside «Пропозиції»: "

P1_LINE = "- P1. Свіжість даних понад швидкість відповіді. Приклад: залишок читаємо без кешу [не слова власника]."
P1_NEW = "- P1. Швидкість відповіді понад свіжість даних. Приклад: залишок показуємо з кешу на хвилину."

# A document as it was sealed before this feature: no «## Ядро».
DOC_OLD = f"""# Цілі проєкту бібліотека
Версія: 1

## Для кого і навіщо
Читач знаходить книжку сам.

## Цілі
- G1. Читач сам знаходить книжку за хвилину — видно з того, що бібліотекаря не питають [не слова власника].
- ~~G2. Бібліотекар бачить усі видачі на одному екрані.~~ (скасовано)
- G3. Книжку можна відкласти на день.

## Принципи (що понад що)
{P1_LINE}

## Не-цілі
- N1. Не робимо мобільного застосунку — бо читачі приходять з браузера.

## Жорсткі обмеження
- C1. Один сервер — джерело: бюджет.

## Готово, коли
- D1. Сто пошуків на день без помилки.

## Зміни
- v1 — перша версія.
"""
DOC_CORE = DOC_OLD.replace("## Цілі\n", "## Ядро\n- G1 — «щоб читач знаходив сам»\n\n## Цілі\n", 1)
MATRIX_HEAD = "# Матриця трасування\n\n| Рядок | Як читаю | Елементи дизайну | Статус |\n|---|---|---|---|\n"
ALL_STANDING = ("G1", "G3", "P1", "N1", "C1", "D1")

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900].replace('Error', 'Err.')}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project(doc: str | None, sealed: bool = False, files: dict[str, str] | None = None) -> Path:
    """A temporary project; `sealed` records the document's fingerprint as `goals.py seal` writes it."""
    root = Path(sandbox_dir("goals-focus-block-"))
    (root / ".engine/goals/requests").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if doc is not None:
        (root / ".engine/goals.md").write_text(doc, encoding="utf-8")
    if sealed:
        assert doc is not None
        (root / SEAL_REL).parent.mkdir(parents=True, exist_ok=True)
        (root / SEAL_REL).write_text(f"{sha(doc)}  .engine/goals.md\n", encoding="utf-8")
    for rel, text in (files or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def goals(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """`goals.py` as the owner's terminal or the board runner runs it: outside a Claude Code session."""
    env = hook_env(root)
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_UNATTENDED_SESSION", None)
    return subprocess.run([sys.executable, str(GOALS), *args], cwd=root, capture_output=True, text=True, env=env, check=False)


def out(proc: subprocess.CompletedProcess[str]) -> str:
    return f"rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"


def seal_value(root: Path) -> str:
    seal = root / SEAL_REL
    return seal.read_text(encoding="utf-8").split()[0] if seal.is_file() else ""


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def amended(text: str) -> str:
    """A lawful amendment of a version-1 text: P1 changed, the version raised, a line in «Зміни»."""
    return (text.replace("Версія: 1", "Версія: 2").replace(P1_LINE, P1_NEW)
            .replace("- v1 — перша версія.", "- v1 — перша версія.\n- v2 — P1 перевернуто."))


def matrix(*ids: str) -> str:
    return MATRIX_HEAD + "".join(f"| {i} | як читаю {i} | Пошук | прочитано |\n" for i in ids)


def domain(rows: list[tuple[str, str]], proposals: list[tuple[str, str]] | None = None) -> str:
    def table(items: list[tuple[str, str]]) -> str:
        return "| Елемент | Що робить | Джерело |\n|---|---|---|\n" + "".join(f"| {n} | опис | {s} |\n" for n, s in items)
    text = "# Карта домену\n\n## Звірка з цілями\n- служить: G1\n\n## Сутності\n" + table(rows)
    return text + ("\n## Пропозиції\n" + table(proposals) if proposals else "")


def fenced_after(text: str, marker: str) -> str:
    """The body of the first fenced block after the line `marker`."""
    at = text.index(marker)
    found = re.search(r"^```[^\n]*\n(.*?)^```", text[at:], re.DOTALL | re.MULTILINE)
    assert found, f"no fenced block after {marker}"
    return found.group(1)


def fenced_blocks(text: str) -> list[str]:
    return re.findall(r"^```[^\n]*\n(.*?)^```", text, re.DOTALL | re.MULTILINE)


def table_rows(block: str) -> list[list[str]]:
    """The data rows of a markdown table (after the header and the `|---|` rule), cells stripped."""
    lines = [ln for ln in block.splitlines() if ln.strip().startswith("|")]
    return [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines[2:]]


# ------------------------------------------------------------------ the S1 → S2 connection


def test_link_core_section_of_the_template() -> None:
    """The template's `## Ядро` (S2 tells the analyst to write it) is the section S1's seal reads."""
    template = read(TEMPLATE)
    check("the template has the heading line `## Ядро`", re.search(r"^## Ядро[ \t]*$", template, re.MULTILINE) is not None, template[:400])
    check("/business-analyst names the section `## Ядро`", "## Ядро" in read(ANALYST_COMMAND))

    def filled(text: str, core: bool) -> str:
        text = re.sub(r"<!-- (- [GPNCD]1\. [^\n]*?) -->", lambda m: re.sub(r"<[^<>]*>", "щось", m.group(1)), text)
        if core:
            text = re.sub(r"<!-- Номери цілей[^\n]*\n(- G1 — «)<[^<>]*>(») -->", r"\1щоб читач знаходив сам\2", text)
        return text

    doc = filled(template, core=True)
    check("filled: the core example line stands uncommented under «Ядро»", "\n- G1 — «щоб читач знаходив сам»" in doc, doc[:1500])
    root = project(doc)
    r = goals(root, "seal")
    check("a document written as the template shows, the core filled, is sealed (exit 0)", r.returncode == 0 and seal_value(root) == sha(doc), out(r))
    r = goals(root, "status")
    check("…and status has no «no core» line", r.returncode == 0 and "no core" not in r.stdout, out(r))
    bare = filled(template, core=False)
    root = project(bare)
    r = goals(root, "seal")
    check("negative — the same with the core left as the template's comment is refused (exit 3), no seal",
          r.returncode == 3 and "REFUSED:" in r.stderr and seal_value(root) == "", out(r))


def test_link_not_required_form_of_the_agent() -> None:
    """The `NOT_REQUIRED` form copied out of the agent's definition is what `goals.py requests` reads."""
    blocks = [b for b in fenced_blocks(read(ANALYST_AGENT)) if "ANALYST_ANSWER: NOT_REQUIRED" in b]
    check("the agent shows the NOT_REQUIRED form in a fenced block", len(blocks) >= 1, blocks)
    if not blocks:
        return
    form = blocks[0]
    answer = (form.replace("<рядки, на які спирався запит>", "G3, P1")
              .replace("<...>", "жоден рядок цього не вимагає").replace("<нічого не будувати — або одне речення>", "нічого не будувати"))
    request = ("# Запит 007\nFrom: master-architect\nReason: 2\nDoor: two-way\n\n## Рішення\nЧи потрібен кошик.\n\n"
               "## Відповідь business analyst-а\n" + answer)
    root = project(DOC_CORE, sealed=True, files={".engine/goals/requests/007.md": request})
    r = goals(root, "requests")
    line = next((ln for ln in r.stdout.splitlines() if "007.md" in ln), "")
    check("requests: the filled form is the outcome not-required with its Lines", r.returncode == 0 and "\tnot-required\tG3, P1" in line, out(r))
    r = goals(root, "quote", ".engine/goals/requests/007.md")
    check("quote: there is no quote to check (exit 3)",
          r.returncode == 3 and "REFUSED: the analyst answers NOT_REQUIRED: there is no quote to check" in r.stderr, out(r))


def test_link_examples_of_master_architect_through_trace() -> None:
    """The example matrix and element table `/master-architect` shows, run through S1's `goals.py trace`."""
    text = read(MASTER_ARCHITECT)
    matrix_block = fenced_after(text, "<!-- example: traceability -->")
    elements_block = fenced_after(text, "<!-- example: elements -->")
    numbers = [row[0] for row in table_rows(matrix_block)]
    elements = table_rows(elements_block)
    check("the matrix example's first column is «Рядок» and it has rows", matrix_block.lstrip().startswith("| Рядок") and bool(numbers), matrix_block)
    check("the element example's first column is «Елемент» and it has rows", elements_block.lstrip().startswith("| Елемент") and bool(elements), elements_block)
    sections = {"G": "Цілі", "P": "Принципи (що понад що)", "N": "Не-цілі", "C": "Жорсткі обмеження", "D": "Готово, коли", "Q": "Відкрите"}
    first_g = next((n for n in numbers if n.startswith("G")), "G1")
    doc = f"# Цілі проєкту приклад\nВерсія: 1\n\n## Ядро\n- {first_g} — «слова власника»\n"
    for kind, title in sections.items():
        doc += f"\n## {title}\n" + "".join(f"- {n}. рядок {n}.\n" for n in numbers if n[0] == kind)
    doc += "\n## Зміни\n- v1 — перша версія.\n"
    adrs = {path: "# ADR\n\n## Звірка з цілями\n- служить: G1\n" for path in re.findall(r"docs/adr/[^\s|)\]]+\.md", elements_block)}
    domain_map = "# Карта домену\n\n## Звірка з цілями\n- служить: " + first_g + "\n\n## Сутності\n" + elements_block
    root = project(doc, sealed=True, files={TRACE: "# Матриця\n\n" + matrix_block, DOMAIN: domain_map, **adrs})
    r = goals(root, "trace")
    check("the examples as they stand: exit 0, the count of their elements",
          r.returncode == 0 and r.stdout.strip() == f"{COUNT}{len(elements)}" and r.stderr == "", out(r))
    name = elements[0][0]
    broken = elements_block.replace(f"| {elements[0][-1]} |", "|  |", 1)
    (root / DOMAIN).write_text(domain_map.replace(elements_block, broken), encoding="utf-8")
    r = goals(root, "trace")
    check(f"one element's source removed: «{name}» refused by name (exit 3), the count still printed",
          r.returncode == 3 and f"{DOMAIN}: «{name}» has no source" in r.stderr and COUNT in r.stdout, out(r))
    (root / DOMAIN).write_text(domain_map + "\n## Пропозиції\n| Елемент | Що робить | Джерело |\n|---|---|---|\n| Рекомендації | радить книжки | — |\n",
                               encoding="utf-8")
    r = goals(root, "trace")
    check("an element without a source under «## Пропозиції» is neither refused nor counted",
          r.returncode == 0 and r.stdout.strip() == f"{COUNT}{len(elements)}", out(r))


def test_link_subcommands_the_definitions_name() -> None:
    """Every `goals.py <subcommand>` S2's texts tell an agent to run is one S1's script has; `trace` among them."""
    doc = GOALS.read_text(encoding="utf-8")
    usage = set(re.findall(r"python3 \.claude/hooks/goals\.py ([a-z][a-z-]*)", doc.split('"""', 2)[1]))
    check("goals.py's usage names trace", "trace" in usage, sorted(usage))
    texts = {p: read(p) for p in (MASTER_ARCHITECT, ANALYST_AGENT, ANALYST_COMMAND, MASTER_CRITIC, REFERENCE)}
    named = {(p.name, s) for p, t in texts.items() for s in re.findall(r"goals\.py ([a-z][a-z-]*)", t)}
    unknown = sorted(f"{f}: {s}" for f, s in named if s not in usage)
    check("no definition names a subcommand goals.py does not have", not unknown, unknown)
    check("/master-architect tells to run `python3 .claude/hooks/goals.py trace`", "python3 .claude/hooks/goals.py trace" in texts[MASTER_ARCHITECT])


# ------------------------------------------------------------------ the acceptance criteria


def test_A1_new_text_without_core_refused_old_document_stays() -> None:
    root = project(DOC_OLD)
    r = goals(root, "seal")
    check("seal: an unsealed text without a core is refused (exit 3), no seal", r.returncode == 3 and "REFUSED:" in r.stderr and seal_value(root) == "", out(r))
    r = goals(root, "first-seal", sha(DOC_OLD))
    check("first-seal: refused (exit 1), no seal", r.returncode == 1 and "first-seal:" in r.stderr and seal_value(root) == "", out(r))
    root = project(DOC_CORE)
    r = goals(root, "first-seal", sha(DOC_CORE))
    check("negative — first-seal of the same text with a core seals it", r.returncode == 0 and seal_value(root) == sha(DOC_CORE), out(r))

    root = project(DOC_OLD, sealed=True)
    r = goals(root, "check")
    check("a document sealed without a core stays in force (check exit 0)", r.returncode == 0, out(r))
    r = goals(root, "status")
    check("status: exit 0 and says it has no core, the next amendment must add it",
          r.returncode == 0 and "no core:" in r.stdout and "the next amendment must add it" in r.stdout, out(r))
    new = amended(DOC_OLD)
    (root / ".engine/goals/proposed.md").write_text(new, encoding="utf-8")
    r = goals(root, "proposal")
    check("proposal: an amendment without a core is refused (exit 3)", r.returncode == 3 and "REFUSED:" in r.stderr and "Ядро" in r.stderr, out(r))
    r = goals(root, "amend", sha(new))
    check("amend: refused (exit 1), the document unchanged", r.returncode == 1 and read(root / ".engine/goals.md") == DOC_OLD, out(r))
    with_core = new.replace("## Цілі\n", "## Ядро\n- G1 — «щоб читач знаходив сам»\n\n## Цілі\n", 1)
    (root / ".engine/goals/proposed.md").write_text(with_core, encoding="utf-8")
    r = goals(root, "proposal")
    check("negative — the same amendment with a core added is lawful (exit 0)", r.returncode == 0, out(r))


def test_A2_not_required_is_an_outcome_of_its_own() -> None:
    nr = ("# Запит 002\nFrom: feature-architect\nReason: 1\nDoor: two-way\n\n## Відповідь business analyst-а\n"
          "ANALYST_ANSWER: NOT_REQUIRED\nLines: G1\nЧому не вимагають: G1 говорить про пошук.\nНайменша форма: нічого не будувати\n")
    quote = ("# Запит 001\nFrom: feature-architect\nReason: 1\nDoor: two-way\n\n## Відповідь business analyst-а\n"
             "ANALYST_ANSWER: QUOTE\nLine: G3\nQuote: Книжку можна відкласти на день.\n")
    root = project(DOC_CORE, sealed=True, files={".engine/goals/requests/002.md": nr, ".engine/goals/requests/001.md": quote})
    r = goals(root, "requests")
    lines = {ln.split("\t")[0]: ln.split("\t") for ln in r.stdout.splitlines() if "\t" in ln}
    two = next((v for k, v in lines.items() if k.endswith("002.md")), [])
    one = next((v for k, v in lines.items() if k.endswith("001.md")), [])
    check("requests: the NOT_REQUIRED answer is shown as not-required with its Lines", r.returncode == 0 and "not-required" in two and two[-1] == "G1", out(r))
    check("negative — the quote answer is not shown as not-required", one != [] and "not-required" not in one, out(r))


def test_A3_quote_compared_with_the_mark_as_it_stands() -> None:
    line = "Читач сам знаходить книжку за хвилину — видно з того, що бібліотекаря не питають [не слова власника]."
    request = "# Запит 003\nFrom: feature-architect\nReason: 1\nDoor: two-way\n\n## Відповідь business analyst-а\nANALYST_ANSWER: QUOTE\nLine: G1\nQuote: {q}\n"
    root = project(DOC_CORE, sealed=True, files={".engine/goals/requests/003.md": request.format(q=line)})
    r = goals(root, "quote", ".engine/goals/requests/003.md")
    check("the quote with the mark, as the line stands, is accepted (exit 0)", r.returncode == 0, out(r))
    (root / ".engine/goals/requests/003.md").write_text(request.format(q=line.replace(" [не слова власника]", "")), encoding="utf-8")
    r = goals(root, "quote", ".engine/goals/requests/003.md")
    check("the same quote without the mark is refused (exit 3)", r.returncode == 3, out(r))


def test_A4_trace_refusals_and_the_count() -> None:
    rows = [("Пошук", "G1, P1"), ("Сервер", "C1"), ("Лічильник", "D1")]
    root = project(DOC_CORE, sealed=True, files={TRACE: matrix(*ALL_STANDING), DOMAIN: domain(rows, proposals=[("Кошик", "")])})
    r = goals(root, "trace")
    check("a full matrix and sourced elements pass: exit 0, three outside «Пропозиції»", r.returncode == 0 and r.stdout.strip() == f"{COUNT}3", out(r))

    (root / TRACE).write_text(matrix("G1", "P1", "N1", "C1", "D1"), encoding="utf-8")
    r = goals(root, "trace")
    check("a standing line without a row: G3 refused", r.returncode == 3 and f"REFUSED: {TRACE}: G3 has no row" in r.stderr, out(r))
    (root / TRACE).write_text(matrix(*ALL_STANDING, "G9"), encoding="utf-8")
    r = goals(root, "trace")
    check("a row naming a number that does not exist: G9 refused",
          r.returncode == 3 and f"{TRACE}: G9 is not a line of the goals document" in r.stderr, out(r))
    (root / TRACE).write_text(matrix(*ALL_STANDING, "G2"), encoding="utf-8")
    r = goals(root, "trace")
    check("a row naming a struck number: G2 refused", r.returncode == 3 and f"{TRACE}: G2 is struck out of the goals document" in r.stderr, out(r))

    (root / TRACE).write_text(matrix(*ALL_STANDING), encoding="utf-8")
    (root / DOMAIN).write_text(domain([*rows, ("Черга", "")]), encoding="utf-8")
    r = goals(root, "trace")
    check("an element outside «Пропозиції» with no source: «Черга» refused, the count printed (4)",
          r.returncode == 3 and f"{DOMAIN}: «Черга» has no source" in r.stderr and r.stdout.strip() == f"{COUNT}4", out(r))
    (root / DOMAIN).write_text(domain([*rows, ("Застосунок", "N1")]), encoding="utf-8")
    r = goals(root, "trace")
    check("an element whose only source is a non-goal: «Застосунок» refused",
          r.returncode == 3 and f"{DOMAIN}: «Застосунок»: its only source is the non-goal N1" in r.stderr and r.stdout.strip() == f"{COUNT}4", out(r))


def test_A5_amendment_lists_the_domain_map_and_the_matrix_for_review() -> None:
    dmap = "# Карта домену\n\n## Звірка з цілями\n- служить: G1\n- вибір розв'язав: P1\n\n## Сутності\n| Елемент | Що робить | Джерело |\n|---|---|---|\n| Пошук | шукає | G1 |\n"
    adr_other = "# ADR 1\n\n## Звірка з цілями\n- служить: G3\n"
    new = amended(DOC_CORE)
    root = project(DOC_CORE, sealed=True, files={DOMAIN: dmap, TRACE: matrix(*ALL_STANDING), "docs/adr/0001-shelf.md": adr_other,
                                                 ".engine/goals/proposed.md": new})
    r = goals(root, "amend", sha(new))
    review_path = root / ".engine/goals/to-review.md"
    review = read(review_path) if review_path.is_file() else ""
    check("amend applied (exit 0), the new document sealed", r.returncode == 0 and seal_value(root) == sha(new), out(r))
    check("to-review.md lists the domain map that cites the changed P1", DOMAIN in review, review)
    check("to-review.md lists the matrix whose row names P1", TRACE in review, review)
    check("negative — a decision that cites only an unchanged line is not listed", "0001-shelf.md" not in review, review)


def section(text: str, start: str) -> str:
    """From the first `start` to the next level-2 heading."""
    at = text.find(start)
    if at < 0:
        return ""
    end = re.search(r"^## ", text[at + len(start):], re.MULTILINE)
    return text[at: at + len(start) + end.start()] if end else text[at:]


def test_A6_the_definitions() -> None:
    arch = read(MASTER_ARCHITECT)
    check("/master-architect has no `round == 4`", "round == 4" not in arch)
    check("/master-architect has the stop «Читання цілей»", "«Читання цілей»" in arch)
    agent = read(ANALYST_AGENT)
    for mode in ("consult", "preseal", "guardian"):
        check(f"business-analyst has the mode `{mode}`", re.search(rf"^##+ .*`{mode}`", agent, re.MULTILINE) is not None)
    forms = "\n".join(fenced_blocks(agent))
    for start in ("ANALYST_ANSWER: NOT_REQUIRED", "Lines:", "Чому не вимагають:", "Найменша форма:",
                  "PRESEAL_FINDING:", "PRESEAL_CLEAN", "GUARDIAN_BLOCK:", "GUARDIAN_NOTE:", "GUARDIAN_PASS"):
        check(f"business-analyst's output forms, in a fenced block: a line starting `{start}`",
              re.search(rf"^{re.escape(start)}", forms, re.MULTILINE) is not None)
    for kind in ("contradiction", "unmarked", "risk-reason", "consequence", "late-choice", "lost-emphasis", "no-core"):
        check(f"preseal's kind `{kind}` is named", f"`{kind}`" in agent or kind in forms)
    critic = read(MASTER_CRITIC)
    at = critic.find("`goals-fit`")
    lens = critic[at:]
    nxt = re.search(r"^(?:- \*\*`|## )", lens[1:], re.MULTILINE)
    lens = lens[: nxt.start() + 1] if nxt else lens
    for name in ("покриття", "необхідність", "пропорційність захисних механізмів", "узгодженість доводів"):
        check(f"master-critic's lens goals-fit names the check «{name}»", at >= 0 and name in lens)


def test_A7_context_budget() -> None:
    r = subprocess.run([sys.executable, str(ROOT / "tests/test_context_budget.py")], cwd=ROOT, capture_output=True, text=True, check=False)
    check("the context budget (200 lines) is not exceeded: tests/test_context_budget.py exit 0", r.returncode == 0, r.stdout[-600:] + r.stderr[-300:])


def test_A8_documents() -> None:
    ref = read(REFERENCE)
    for word in ("Ядро", "[не слова власника]", "interview.md", "preseal", "NOT_REQUIRED", "guardian"):
        check(f"business-analysis.md names {word}", word in ref)
    guide = read(OWNER_GUIDE)
    for word in ("Читання цілей", "Ядро", "[не слова власника]"):
        check(f"OWNER-GUIDE names {word}", word in guide)
    template = read(TEMPLATE)
    check("the template has the core section", re.search(r"^## Ядро[ \t]*$", template, re.MULTILINE) is not None)
    check("the template explains the mark", "[не слова власника]" in template)
    check("the template has no «Затвердив власник»", "Затвердив власник" not in template)


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
