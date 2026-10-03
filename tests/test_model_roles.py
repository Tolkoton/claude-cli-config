#!/usr/bin/env python3
"""Models by role (package costs, item 3): critics on the cheaper model, judges on the strongest.

Facts about the field (code.claude.com/docs/en/sub-agents, checked 2026-10-03): a subagent's
`model` frontmatter takes an alias (`sonnet`, `opus`, `haiku`, `fable`), a full model id, or
`inherit`; it outranks the session's model and is outranked only by a per-invocation parameter.
A skill or a command with no `model` runs on the session's model.

  * the four critics the owner named carry `model: sonnet`, inside the frontmatter;
  * the overseer and the architects name NO model, so they stay on the session's — the strongest
    one the owner runs; a cheaper model written there would be a silent downgrade of the judge;
  * /feature-architect allows two critic rounds per plan and no third.

Run:   python3 tests/test_model_roles.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".claude"
CHEAPER = "sonnet"
CRITICS = ("critic-core", "feature-critic", "master-critic", "slice-planner-critic")
STRONGEST = (
    "skills/overseer/SKILL.md", "skills/slice-builder/SKILL.md", "commands/feature-architect.md",
    "commands/master-architect.md", "commands/plan-slice.md", "commands/mvp-architect.md",
)
ALLOWED = re.compile(r"^(sonnet|opus|haiku|fable|inherit|claude-[a-z0-9-]+)$")
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {str(detail)[:400]}")


def frontmatter(path: Path) -> dict[str, str]:
    """Top-level `key: value` pairs of the leading --- block (block scalars keep only the key)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return fields
        found = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if found:
            fields[found.group(1)] = found.group(2).strip()
    return {}  # no closing line: not a frontmatter block


print("critics: the cheaper model")
for name in CRITICS:
    fields = frontmatter(CLAUDE / "agents" / f"{name}.md")
    check(f"{name}: model is `{CHEAPER}`, in the frontmatter", fields.get("model") == CHEAPER, fields)
    check(f"{name}: still names itself and describes itself", fields.get("name") == name and "description" in fields, fields)
for path in sorted((CLAUDE / "agents").glob("*.md")):
    value = frontmatter(path).get("model")
    check(f"{path.name}: a model value the docs allow (or none)", value is None or bool(ALLOWED.match(value)), value)
check("mvp-critic was not in the owner's list and names no model", "model" not in frontmatter(CLAUDE / "agents" / "mvp-critic.md"))

print("overseer and architects: the session's model, never a cheaper one")
for rel in STRONGEST:
    fields = frontmatter(CLAUDE / rel)
    check(f"{rel}: has frontmatter and names no model", bool(fields) and "model" not in fields, fields)

print("/feature-architect: two critic rounds per plan")
text = (CLAUDE / "commands" / "feature-architect.md").read_text(encoding="utf-8")
check("the cap is stated", "at most two\ncritic rounds" in text or "at most two critic rounds" in text, "")
check("the loop runs rounds 1 and 2 only", "for round in (1, 2):" in text, "")
check("the old four-round circuit-breaker is gone", not re.search(r"round == 4|after 4\s+rounds|Round 4", text), "")
check("what survives round two is recorded and routed, not dropped",
      "Open items requiring human decision" in text and "two-way door" in text and "one-way door" in text, "")
check("the critic is sent the whole plan", 'phase: "plan"' in text and "`plan`" in (CLAUDE / "agents/feature-critic.md").read_text(encoding="utf-8"), "")

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
