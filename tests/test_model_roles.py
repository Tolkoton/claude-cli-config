#!/usr/bin/env python3
"""Models by role: critics, judges and architects all on the session's model — the strongest.

Facts about the field (code.claude.com/docs/en/sub-agents, checked 2026-10-03): a subagent's
`model` frontmatter takes an alias (`sonnet`, `opus`, `haiku`, `fable`), a full model id, or
`inherit`; it outranks the session's model and is outranked only by a per-invocation parameter.
A skill or a command with no `model` runs on the session's model.

  * no critic names a model weaker than the session's (owner, task 001: a cheaper model for
    critics is a dead end). The session's model is not known here, so the only values that
    cannot be weaker are no `model` at all and `inherit`; any alias or id fails;
  * the overseer and the architects name NO model, so they stay on the session's — the strongest
    one the owner runs; a cheaper model written there would be a silent downgrade of the judge;
  * no other definition the engine ships, and no settings layer, names a cheaper model;
  * /feature-architect allows two critic rounds per plan and no third.

Run:   python3 tests/test_model_roles.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".claude"
CHEAPER = re.compile(r"sonnet|haiku")
CRITICS = ("critic-core", "feature-critic", "master-critic", "slice-planner-critic", "mvp-critic")
DEFINITION_DIRS = (CLAUDE / "agents", CLAUDE / "skills", CLAUDE / "commands", ROOT / "templates", ROOT / "user")
SETTINGS = (CLAUDE / "settings.json", ROOT / "user" / "settings.json", ROOT / "templates" / "project" / ".claude" / "settings.json")
STRONGEST = (
    "agents/overseer.md", "skills/overseer/SKILL.md", "skills/slice-builder/SKILL.md", "commands/feature-architect.md",
    "commands/master-architect.md", "commands/plan-slice.md", "commands/mvp-architect.md",
    "agents/test-manager.md", "agents/slice-tester.md",
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


def is_critic(path: Path) -> bool:
    return "critic" in path.stem


def inherits_session_model(fields: dict[str, str]) -> bool:
    """True when the definition cannot run on anything but the session's model."""
    return fields.get("model", "inherit") == "inherit"


def names_cheaper_model(fields: dict[str, str]) -> bool:
    return bool(CHEAPER.search(fields.get("model", "")))


def cheaper_model_settings(path: Path) -> list[str]:
    """`model` and `env.*MODEL*` entries of a settings file that name a cheaper model."""
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = [("model", data.get("model", ""))]
    pairs += [(f"env.{key}", value) for key, value in data.get("env", {}).items() if "MODEL" in key]
    return [f"{key}={value}" for key, value in pairs if CHEAPER.search(str(value))]


print("critics: never weaker than the session's model")
agents = sorted((CLAUDE / "agents").glob("*.md"))
critics = [path for path in agents if is_critic(path)]
check("every known critic is found by name", {path.stem for path in critics} >= set(CRITICS), critics)
for path in critics:
    fields = frontmatter(path)
    check(f"{path.stem}: no model, or `inherit`", inherits_session_model(fields), fields.get("model"))
    check(f"{path.stem}: still names itself and describes itself", fields.get("name") == path.stem and "description" in fields, fields)
for path in agents:
    value = frontmatter(path).get("model")
    check(f"{path.name}: a model value the docs allow (or none)", value is None or bool(ALLOWED.match(value)), value)

print("no other definition and no settings layer names a cheaper model")
definitions = sorted(path for top in DEFINITION_DIRS if top.is_dir() for path in top.rglob("*.md"))
cheaper = [str(path.relative_to(ROOT)) for path in definitions if names_cheaper_model(frontmatter(path))]
check(f"{len(definitions)} definitions under agents, skills, commands, templates, user", len(definitions) > 10 and not cheaper, cheaper)
for path in SETTINGS:
    if path.is_file():
        found = cheaper_model_settings(path)
        check(f"{path.relative_to(ROOT)}: no cheaper model", not found, found)

print("the checks refuse a planted cheaper model")
with tempfile.TemporaryDirectory() as tmp:
    planted = Path(tmp) / "feature-critic.md"
    for value, weaker_possible in (("sonnet", True), ("haiku", True), ("opus", True), ("claude-sonnet-5-5", True), ("inherit", False)):
        planted.write_text(f"---\nname: feature-critic\nmodel: {value}\ndescription: x\n---\nbody\n", encoding="utf-8")
        check(f"critic with `model: {value}` is {'refused' if weaker_possible else 'accepted'}",
              is_critic(planted) and inherits_session_model(frontmatter(planted)) != weaker_possible)
    planted.write_text("---\nname: feature-critic\ndescription: x\n---\nmodel: sonnet in the body is prose\n", encoding="utf-8")
    check("critic with no model field is accepted", inherits_session_model(frontmatter(planted)))
    check("a non-critic on `haiku` is refused", names_cheaper_model({"model": "haiku"}) and not names_cheaper_model({"model": "opus"}))
    settings = Path(tmp) / "settings.json"
    settings.write_text(json.dumps({"env": {"CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5", "FOO": "sonnet"}}), encoding="utf-8")
    check("a settings layer pinning subagents to sonnet is refused", cheaper_model_settings(settings) == ["env.CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5"], cheaper_model_settings(settings))

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
