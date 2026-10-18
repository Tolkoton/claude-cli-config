#!/usr/bin/env python3
"""The agents told to do what the owner decided (board 201, slice goals-roles): the contract tests.

Written from the sealed contract `.engine/slices/goals-roles.md` before the definitions were
changed, by the slice tester. Every expected string here is copied by hand from the contract's
«Seam» and «Exit criterion»; nothing is computed by the code under test.

  1. `.claude/agents/business-analyst.md` — the three modes, the description, the output forms
     (NOT_REQUIRED, PRESEAL_*, GUARDIAN_*), the seven kinds, the tools kept; Seam 2;
  2. `.claude/commands/business-analyst.md` — the journal, the core question, the mark, `preseal`;
  3. `.claude/commands/master-architect.md` — `goals.py trace`, the guardian, «Записав так», the
     readings of a non-goal and a default, «Пропозиції», the amendment's section, convergence (Seam 4),
     `BOARD_MAX_USD`, the two examples run through `goals.py trace` (Seam 1);
  4. `.claude/agents/master-critic.md` — the four checks of `goals-fit`, their order (Seam 5),
     `WebFetch`, «Пропозиції»;
  5. `.claude/references/business-analysis.md`, `docs/OWNER-GUIDE.md`, `tests/fast-suites.txt`.

Tests that depend on a question to the contract are in tests/test_goals_roles_disputed.py.

Run:   python3 tests/test_goals_roles.py            # every case
       python3 tests/test_goals_roles.py <test>     # one case by its name
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
AGENT = ROOT / ".claude/agents/business-analyst.md"
COMMAND = ROOT / ".claude/commands/business-analyst.md"
ARCHITECT = ROOT / ".claude/commands/master-architect.md"
CRITIC = ROOT / ".claude/agents/master-critic.md"
REFERENCE = ROOT / ".claude/references/business-analysis.md"
GUIDE = ROOT / "docs/OWNER-GUIDE.md"
FAST = ROOT / "tests/fast-suites.txt"
SEAL_REL = ".claude/state/goals/goals.sha256"
TRACE = ".engine/architecture/traceability.md"
DOMAIN = ".engine/architecture/domain-map.md"

NR_FORM = ("ANALYST_ANSWER: NOT_REQUIRED",
           "Lines: <рядки, на які спирався запит>",
           "Чому не вимагають: <...>",
           "Найменша форма: <нічого не будувати — або одне речення>")
PRESEAL_LINE = "PRESEAL_FINDING: <вид> | <рядки> | <слова власника або пояснення> | <питання до власника>"
KINDS = ("contradiction", "unmarked", "risk-reason", "consequence", "late-choice", "lost-emphasis", "no-core")
MARK = "[не слова власника]"
ID_RE = re.compile(r"(?<![A-Za-z0-9])([GPNCDQ])(\d+)(?![A-Za-z0-9])")
ADR_RE = re.compile(r"docs/adr/[^\s|)\]]+\.md")
KIND_SECTION = {"G": "## Цілі", "P": "## Принципи (що понад що)", "N": "## Не-цілі",
                "C": "## Жорсткі обмеження", "D": "## Готово, коли", "Q": "## Відкрите"}

PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:900].replace('Error', 'Err.')}")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def flat(value: str) -> str:
    """Whitespace collapsed: a string the contract writes on one line may be wrapped in the file."""
    return " ".join(value.split())


def has(path: Path, needle: str) -> bool:
    return flat(needle) in flat(text(path))


def fences(value: str) -> list[list[str]]:
    """The lines of every fenced block (``` … ```), each stripped."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in value.splitlines():
        if line.strip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line.strip())
    return blocks


def fence_lines(path: Path) -> list[str]:
    return [line for block in fences(text(path)) for line in block]


def description(path: Path) -> str:
    """The front matter's `description:` value (a `|` block or one line)."""
    value = text(path)
    if not value.startswith("---"):
        return ""
    head = value.split("---", 2)[1]
    out: list[str] = []
    inside = False
    for line in head.splitlines():
        if line.startswith("description:"):
            inside = True
            out.append(line[len("description:"):])
            continue
        if inside and line[:1] not in (" ", "\t", ""):
            break
        if inside:
            out.append(line)
    return flat(" ".join(out))


def frontmatter_line(path: Path, key: str) -> str | None:
    value = text(path)
    if not value.startswith("---"):
        return None
    for line in value.split("---", 2)[1].splitlines():
        if line.startswith(f"{key}:"):
            return line[len(key) + 1:].strip()
    return None


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project(doc: str, files: dict[str, str]) -> Path:
    """A temporary project with `doc` sealed as `goals.py seal` records it."""
    root = Path(sandbox_dir("goals-roles-"))
    (root / ".engine/goals/requests").mkdir(parents=True)
    (root / "docs/adr").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".engine/goals.md").write_text(doc, encoding="utf-8")
    seal = root / SEAL_REL
    seal.parent.mkdir(parents=True, exist_ok=True)
    seal.write_text(f"{sha(doc)}  .engine/goals.md\n", encoding="utf-8")
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    return root


def run_goals(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = hook_env(root)
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_UNATTENDED_SESSION", None)
    return subprocess.run([sys.executable, str(GOALS), *args], cwd=root, capture_output=True, text=True, env=env, check=False)


def out(proc: subprocess.CompletedProcess[str]) -> str:
    return f"rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"


def goals_doc(ids: list[str]) -> str:
    """A goals document with one standing line per number, and a core naming the first G."""
    ordered = sorted(set(ids), key=lambda i: ("GPNCDQ".index(i[0]), int(i[1:])))
    if not any(i[0] == "G" for i in ordered):
        ordered = ["G1", *ordered]
    gs = [i for i in ordered if i[0] == "G"]
    body = ["# Цілі проєкту приклад", "Версія: 1", "", "## Для кого і навіщо", "Приклад для перевірки.", "",
            "## Ядро", f"- {gs[0]} — «головне»", ""]
    for kind, heading in KIND_SECTION.items():
        lines = [i for i in ordered if i[0] == kind]
        if lines:
            body += [heading, *(f"- {i}. Рядок {i} прикладу." for i in lines), ""]
    body += ["## Зміни", "- v1 — перша версія.", ""]
    return "\n".join(body)


# ------------------------------------------------------------------ 1. the agent business-analyst


def test_agent_three_modes_named_by_their_prompt_forms() -> None:
    for form in ("consult <request path>", "preseal <draft> <journal>", "guardian <goals> <journal> <matrix> <artifact>"):
        check(f"the agent names the mode `{form}`", has(AGENT, form), "absent from .claude/agents/business-analyst.md")


def test_agent_description_names_modes_and_starters() -> None:
    desc = description(AGENT)
    for word in ("consult", "preseal", "guardian", "/master-architect", "/feature-architect", "/business-analyst"):
        check(f"the description names `{word}`", word in desc, desc)
    check("no sentence of the description says the agent is started only by architects",
          "only by architects" not in desc.lower() and "only by /master-architect or /feature-architect" not in desc, desc)


def test_agent_not_required_form_verbatim() -> None:
    blocks = fences(text(AGENT))
    found = any(block[i:i + len(NR_FORM)] == list(NR_FORM) for block in blocks for i in range(len(block)))
    check("a fenced block carries the four lines of the NOT_REQUIRED form, in order", found, blocks)


def test_seam2_not_required_form_read_by_goals_requests() -> None:
    blocks = fences(text(AGENT))
    form = next((block for block in blocks if "ANALYST_ANSWER: NOT_REQUIRED" in block), None)
    check("the NOT_REQUIRED form is in a fenced block of the agent", form is not None, blocks)
    if form is None:
        return
    start = form.index("ANALYST_ANSWER: NOT_REQUIRED")
    filled: list[str] = []
    for line in form[start:]:
        if line.startswith("Lines:"):
            filled.append("Lines: G1")
        else:
            filled.append(re.sub(r"<[^>]*>", "заповнено", line))
    request = ("# Запит 001\nFrom: feature-architect\nReason: 2\nDoor: two-way\n\n## Відповідь business analyst-а\n"
               + "\n".join(filled) + "\n")
    doc = goals_doc(["G1"])
    root = project(doc, {".engine/goals/requests/001.md": request})
    r = run_goals(root, "requests")
    row = next((line.split("\t") for line in r.stdout.splitlines() if line.split("\t")[0].endswith("001.md")), [])
    check("the form copied out of the definition, filled, is `not-required` with its Lines in `goals.py requests`",
          r.returncode == 0 and row[2:4] == ["not-required", "G1"], out(r) + f" request={request!r}")


def test_agent_preseal_forms() -> None:
    lines = [flat(line) for line in fence_lines(AGENT)]
    check("a fenced block carries the PRESEAL_FINDING line", PRESEAL_LINE in lines, lines)
    check("a fenced block carries the one line PRESEAL_CLEAN", "PRESEAL_CLEAN" in lines, lines)


def test_agent_seven_preseal_kinds() -> None:
    body = text(AGENT)
    for kind in KINDS:
        check(f"the kind `{kind}` is named", f"`{kind}`" in body or re.search(rf"(?<![\w-]){re.escape(kind)}(?![\w-])", body) is not None,
              "absent from .claude/agents/business-analyst.md")


def test_agent_guardian_forms() -> None:
    lines = fence_lines(AGENT)
    check("a fenced block carries a `GUARDIAN_BLOCK:` line", any(line.startswith("GUARDIAN_BLOCK:") for line in lines), lines)
    check("a fenced block carries a `GUARDIAN_NOTE:` line", any(line.startswith("GUARDIAN_NOTE:") for line in lines), lines)
    check("a fenced block carries the line `GUARDIAN_PASS`", "GUARDIAN_PASS" in lines, lines)


def test_agent_tools_stay_read_grep_glob() -> None:
    check("the agent's tools stay `Read, Grep, Glob`", frontmatter_line(AGENT, "tools") == "Read, Grep, Glob",
          frontmatter_line(AGENT, "tools"))


# ------------------------------------------------------------------ 2. the command /business-analyst


def test_command_interview_journal() -> None:
    check("/business-analyst keeps the journal `.engine/goals/interview.md`", has(COMMAND, ".engine/goals/interview.md"),
          "absent from .claude/commands/business-analyst.md")


def test_command_core_question_into_core_section() -> None:
    check("/business-analyst asks «Якби працювала лише одна з цих цілей — яка?»",
          has(COMMAND, "Якби працювала лише одна з цих цілей — яка?"), "the question is absent")
    check("…and writes the answer into `## Ядро`", has(COMMAND, "## Ядро"), "`## Ядро` is absent")


def test_command_mark_not_owners_words() -> None:
    check(f"/business-analyst names the mark `{MARK}`", has(COMMAND, MARK), "absent")


def test_command_preseal_step() -> None:
    check("/business-analyst starts the agent in mode `preseal`", has(COMMAND, "preseal"), "absent")


# ------------------------------------------------------------------ 3. the command /master-architect


def test_architect_runs_goals_trace() -> None:
    check("/master-architect runs `goals.py trace`", has(ARCHITECT, "goals.py trace"), "absent")


def test_architect_calls_the_guardian() -> None:
    check("/master-architect calls the analyst in mode `guardian`", has(ARCHITECT, "guardian"), "absent")


def test_architect_records_zapysav_tak() -> None:
    check("/master-architect answers `«Записав так: …»` after the owner's answer", has(ARCHITECT, "«Записав так"), "absent")


def test_architect_non_goal_reads_nothing_built() -> None:
    check("a non-goal reads «нічого не будуємо»", has(ARCHITECT, "нічого не будуємо"), "absent")


def test_architect_default_line_reads_default_applies() -> None:
    check("an open line with a default reads «діє значення за замовчуванням»", has(ARCHITECT, "діє значення за замовчуванням"), "absent")


def test_architect_proposals_section() -> None:
    check("/master-architect names the section `## Пропозиції`", has(ARCHITECT, "## Пропозиції"), "absent")


def test_architect_amendment_what_else_changed() -> None:
    check("after an amendment, the section «Що ще змінилося в дизайні через цю правку»",
          has(ARCHITECT, "Що ще змінилося в дизайні через цю правку"), "absent")


def test_seam4_no_round_limit_but_a_condition() -> None:
    body = text(ARCHITECT)
    check("`round == 4` is gone from /master-architect", "round == 4" not in body, "still present")
    check("`oscillation` is there", "oscillation" in body, "absent")
    check("`divergence` is there", "divergence" in body, "absent")


def test_architect_board_max_usd_guards_the_loop() -> None:
    check("`BOARD_MAX_USD` guards an endless loop unattended", has(ARCHITECT, "BOARD_MAX_USD"), "absent")


def example_after(marker: str) -> str | None:
    """The body of the first fenced block after the line `marker` (blank lines between allowed)."""
    lines = text(ARCHITECT).splitlines()
    try:
        at = next(i for i, line in enumerate(lines) if line.strip() == marker)
    except StopIteration:
        return None
    i = at + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not lines[i].strip().startswith("```"):
        return None
    body: list[str] = []
    for line in lines[i + 1:]:
        if line.strip().startswith("```"):
            return "\n".join(body) + "\n"
        body.append(line)
    return None


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def element_rows(value: str) -> list[tuple[str, str, bool]]:
    """(element, source cell, under «Пропозиції») of every element-table row, read as the contract names them."""
    rows: list[tuple[str, str, bool]] = []
    section = ""
    lines = value.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip()
        if line.lstrip().startswith("|") and cells(line)[0] in ("Елемент", "Element"):
            head = cells(line)
            src = next((k for k, cell in enumerate(head) if cell in ("Джерело", "Source")), None)
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                row = cells(lines[j])
                if src is not None and src < len(row):
                    rows.append((row[0], row[src], section in ("Пропозиції", "Proposals")))
                j += 1
            i = j
            continue
        i += 1
    return rows


def without_source(value: str, element: str) -> str | None:
    """`value` with the source cell of the first row of `element` outside «Пропозиції» emptied."""
    lines = value.splitlines()
    section, src = "", None
    for k, line in enumerate(lines):
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.lstrip().startswith("|"):
            src = None
            continue
        row = cells(line)
        if row[0] in ("Елемент", "Element"):
            src = next((i for i, cell in enumerate(row) if cell in ("Джерело", "Source")), None)
        elif src is not None and row[0] == element and section not in ("Пропозиції", "Proposals") and src < len(row):
            row[src] = ""
            lines[k] = "| " + " | ".join(row) + " |"
            return "\n".join(lines) + "\n"
    return None


def matrix_ids(value: str) -> list[str]:
    ids: list[str] = []
    lines = value.splitlines()
    for k, line in enumerate(lines):
        if line.lstrip().startswith("|") and cells(line)[0] in ("Рядок", "Line"):
            for row in lines[k + 2:]:
                if not row.lstrip().startswith("|"):
                    break
                first = cells(row)[0]
                if re.fullmatch(r"[GPNCDQ]\d+", first):
                    ids.append(first)
            break
    return ids


def test_seam1_examples_run_through_goals_trace() -> None:
    matrix = example_after("<!-- example: traceability -->")
    elements = example_after("<!-- example: elements -->")
    check("a fenced matrix example follows `<!-- example: traceability -->`", matrix is not None, "no such block")
    check("a fenced element-table example follows `<!-- example: elements -->`", elements is not None, "no such block")
    if matrix is None or elements is None:
        return
    rows = element_rows(elements)
    outside = [row for row in rows if not row[2]]
    check("the element example has a row outside «Пропозиції»", bool(outside), rows)
    if not outside:
        return
    ids = matrix_ids(matrix) + [m.group(0) for _, source, _ in outside for m in ID_RE.finditer(source)]
    adrs = {path for _, source, _ in rows for path in ADR_RE.findall(source)}
    files = {TRACE: matrix, DOMAIN: elements, **{path: "# ADR\n\n## Звірка з цілями\n- служить: G1\n" for path in adrs}}
    doc = goals_doc(ids)
    r = run_goals(project(doc, files), "trace")
    check("the two examples as traceability.md and domain-map.md: `goals.py trace` exits 0 with the count line",
          r.returncode == 0 and any(re.fullmatch(r"elements outside «Пропозиції»: [1-9]\d*", line) for line in r.stdout.splitlines()),
          out(r) + f" doc={doc!r}")
    name = outside[0][0]
    broken = without_source(elements, name)
    check("the source of the first element can be removed from the example", broken is not None, name)
    if broken is None:
        return
    files[DOMAIN] = broken
    r = run_goals(project(doc, files), "trace")
    check(f"…and with that source removed, `trace` refuses naming «{name}»",
          r.returncode == 3 and any(line.startswith("REFUSED: ") and f"«{name}»" in line and "has no source" in line
                                    for line in r.stderr.splitlines()), out(r))


# ------------------------------------------------------------------ 4. the agent master-critic


def goals_fit_lens() -> str:
    """The `goals-fit` lens: from its bullet to the next lens bullet or heading, whitespace collapsed."""
    lines = text(CRITIC).splitlines()
    start = next((i for i, line in enumerate(lines) if "**`goals-fit`**" in line), None)
    if start is None:
        return ""
    body = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith(("- **`", "#")):
            break
        body.append(line)
    return flat(" ".join(body))


def test_critic_goals_fit_four_named_checks() -> None:
    lens = goals_fit_lens().casefold()
    for name in ("покриття", "необхідність", "пропорційність захисних механізмів", "узгодженість доводів"):
        check(f"the `goals-fit` lens names the check «{name}»", name in lens, lens[:400])


def test_seam5_critic_necessity_and_proportionality_before_inversion_and_premortem() -> None:
    lens = goals_fit_lens().casefold()
    sentences = re.split(r"(?<=[.!?])\s+", lens)
    need, prop = re.compile(r"необхідн\w*"), re.compile(r"пропорційн\w*\s+захисних\s+механізм\w*")
    ordered = False
    for sentence in sentences:
        a, b = need.search(sentence), prop.search(sentence)
        c, d = sentence.find("inversion"), sentence.find("premortem")
        if a and b and c >= 0 and d >= 0:
            ordered = ordered or max(a.start(), b.start()) < min(c, d)
    check("inside `goals-fit`, the sentence that orders them puts necessity and proportionality before inversion and premortem",
          ordered, sentences)


def test_critic_webfetch_for_technical_premises() -> None:
    check("master-critic checks technical premises against official documentation (`WebFetch`)", has(CRITIC, "WebFetch"), "absent")


def test_critic_element_without_source_to_proposals() -> None:
    check("master-critic's one fix for an element without a source names «Пропозиції»", has(CRITIC, "Пропозиції"), "absent")


# ------------------------------------------------------------------ 5. the reference, the guide, the fast set


def test_reference_names_the_six_things() -> None:
    for word in ("Ядро", MARK, "interview.md", "preseal", "NOT_REQUIRED", "guardian"):
        check(f"the method reference names `{word}`", has(REFERENCE, word), "absent from .claude/references/business-analysis.md")


def test_owner_guide_names_the_stop_the_core_and_the_mark() -> None:
    for word in ("Читання цілей", "Ядро", MARK):
        check(f"docs/OWNER-GUIDE.md names «{word}»", has(GUIDE, word), "absent")


def test_suite_in_the_fast_set() -> None:
    names = [line.strip() for line in text(FAST).splitlines() if line.strip() and not line.startswith("#")]
    check("tests/test_goals_roles.py exists", (ROOT / "tests/test_goals_roles.py").is_file(), "no such file")
    check("…and is a line of tests/fast-suites.txt", "test_goals_roles.py" in names, names[-5:])


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
