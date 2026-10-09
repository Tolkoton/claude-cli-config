#!/usr/bin/env python3
"""docs/ARCHITECTURE.md stays true to the repository (board 089).

  - every path the document names in backticks exists (a placeholder — `<slug>`, `NNN`, `…` — is not
    a path); a file renamed or removed turns this red, so the map cannot quietly point at nothing;
  - the three diagrams are there, in Mermaid: one task's way, one slice's way, the hooks by event;
  - every hook script `.claude/settings.json` wires is named in the document, and every event it wires
    a hook to has its box on the hooks diagram: a hook added to the settings without a place on the map
    turns this red;
  - in its event's box, each wired script stands on a line that begins with its matcher, verbatim
    («Agent|Task →», not «Agent →»): a matcher widened or narrowed in the settings turns this red;
  - and the other way round: every script drawn in a box is wired on that event with that matcher, and
    every box is an event the settings wire — a hook taken out of the settings and left on the map, or
    drawn where nothing is wired, turns this red. A part in parentheses says what a script runs
    («(gate.py stop)») and is not drawn as wired.

Run:   python3 tests/test_architecture_doc.py       Exit: 0 all green, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "ARCHITECTURE.md"
PLACEHOLDER = re.compile(r"[<>…]|NNN|\dNN")
PASS = FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '   ' + str(detail)[:600]}")


def paths(text: str) -> list[str]:
    """The backticked words of `text` that name a path: one with a slash or a file extension, no
    space and no placeholder in it."""
    found = []
    for word in re.findall(r"`([^`\n]+)`", text):
        if any(c.isspace() for c in word) or PLACEHOLDER.search(word):
            continue
        if "/" in word or re.search(r"\.(md|py|sh|json|txt|toml)$", word):
            found.append(word.rstrip("/"))
    return found


def missing(text: str) -> list[str]:
    """The paths `text` names that the repository does not have."""
    return [p for p in paths(text) if not (ROOT / p).exists()]


def unmapped(settings: dict[str, object], text: str) -> list[str]:
    """The hook scripts the settings wire that `text` does not name."""
    return sorted(s for s in hook_scripts(settings) if s not in text)


def wiring(settings: dict[str, object]) -> list[tuple[str, str, str]]:
    """(event, matcher, script) for every hook script the settings wire; "" when a group has no matcher."""
    found = []
    for event, groups in dict(settings.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                for script in re.findall(r"\.claude/hooks/([\w.-]+\.(?:py|sh))", hook.get("command", "")):
                    found.append((event, str(group.get("matcher") or ""), script))
    return found


def box(diagram: str, event: str) -> list[str]:
    """The lines of the subgraph `event` of the hooks diagram; none when it has no such subgraph."""
    head = f"subgraph {event}\n"
    return diagram.split(head, 1)[1].split("\n    end", 1)[0].splitlines() if head in diagram else []


def misplaced(settings: dict[str, object], diagram: str) -> list[str]:
    """Each wired script with no line in its event's box that names it after its matcher, verbatim: the
    matcher must open the label (after `"` or a space), so «Agent|Task|Edit →» does not stand for «Edit»."""
    def placed(matcher: str, script: str, line: str) -> bool:
        return script in line and (not matcher or re.search(r'["\s]' + re.escape(matcher) + " →", line) is not None)
    return [f"{event}: {matcher or '-'} → {script}" for event, matcher, script in wiring(settings)
            if not any(placed(matcher, script, line) for line in box(diagram, event))]


def drawn(diagram: str) -> list[tuple[str, str, str]]:
    """(event, matcher, script) for every script the hooks diagram draws in an event box; "" when the
    line has no matcher; a part in parentheses is not drawn as wired."""
    found = []
    for event in re.findall(r"subgraph (\w+)\n", diagram):
        for line in box(diagram, event):
            label = re.sub(r"\([^)]*\)", "", line.split('["', 1)[-1])
            matcher, _, scripts = label.rpartition(" →")
            found += [(event, matcher.strip(), script) for script in re.findall(r"[\w.-]+\.(?:py|sh)\b", scripts)]
    return found


def stale(settings: dict[str, object], diagram: str) -> list[str]:
    """What the hooks diagram draws and the settings do not wire: a box for an event with no hook, a
    script on an event or after a matcher it is not wired with."""
    wired, events = set(wiring(settings)), set(dict(settings.get("hooks") or {}))
    return ([f"subgraph {event}: nothing is wired on it" for event in re.findall(r"subgraph (\w+)\n", diagram) if event not in events]
            + [f"{event}: {matcher or '-'} → {script}" for event, matcher, script in drawn(diagram) if (event, matcher, script) not in wired])


def hook_scripts(settings: dict[str, object]) -> set[str]:
    """The file name of every hook script the settings wire."""
    names = set()
    for groups in dict(settings.get("hooks") or {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                names.update(re.findall(r"\.claude/hooks/([\w.-]+\.(?:py|sh))", hook.get("command", "")))
    return names


text = DOC.read_text(encoding="utf-8")
named, gone = paths(text), missing(text)
check(f"{len(named)} paths named in docs/ARCHITECTURE.md, every one exists", len(named) > 40 and not gone, gone)
check("the three diagrams are Mermaid blocks", text.count("```mermaid") >= 3, text.count("```mermaid"))
for words in (("todo/", "doing/", "done/", "blocked/"), ("planner", "builder", "overseer", "BLOCK", "PASS"), ("PreToolUse", "Stop", "SubagentStop")):
    check(f"a diagram shows {', '.join(words)}", any(all(w in block for w in words) for block in text.split("```mermaid")[1:]))
settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
scripts, absent = hook_scripts(settings), unmapped(settings, text)
check(f"every hook script .claude/settings.json wires ({len(scripts)}) is on the map", len(scripts) > 8 and not absent, absent)
hooks_map = next((block for block in text.split("```mermaid")[1:] if "SubagentStop" in block), "").split("```")[0]
events = sorted(dict(settings.get("hooks") or {}))
check(f"every event the settings wire a hook to ({len(events)}) has its box on the hooks diagram",
      len(events) >= 6 and all(f"subgraph {event}\n" in hooks_map for event in events), [e for e in events if f"subgraph {e}\n" not in hooks_map])
wired, wrong = wiring(settings), misplaced(settings, hooks_map)
check(f"each of the {len(wired)} wired hooks stands in its event's box after its matcher, verbatim", len(wired) >= 14 and not wrong, wrong)
extra = stale(settings, hooks_map)
check(f"…and the other way round: each of the {len(drawn(hooks_map))} scripts drawn is wired on its event after its matcher, each box is a wired event",
      len(drawn(hooks_map)) == len(wired) and not extra, extra)

print("the checks refuse what they should")
check("NEGATIVE: a path that does not exist is caught", missing("see `docs/NO-SUCH-FILE.md`, `x/y` and `tasks/README.md`")
      == ["docs/NO-SUCH-FILE.md", "x/y"])
check("NEGATIVE: placeholders and commands are not paths", paths("`.engine/slices/<slug>.md` `tasks/blocked/9NN-gate-….md` `board.py review` `main`") == [])
check("NEGATIVE: a hook wired but not named is caught",
      unmapped({"hooks": {"Stop": [{"hooks": [{"command": 'python3 "$X/.claude/hooks/new_guard.py"'}]}]}}, text) == ["new_guard.py"])

one = {"hooks": {"PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"command": 'bash "$X/.claude/hooks/protect-paths.sh"'}]}]}}
check("NEGATIVE: a matcher shortened on the map is caught («Edit/Write» for «Edit|Write|MultiEdit|NotebookEdit»)",
      misplaced(one, 'subgraph PreToolUse\n        b2["Edit/Write → protect-paths.sh"]\n    end') == ["PreToolUse: Edit|Write|MultiEdit|NotebookEdit → protect-paths.sh"])
check("…and the same line with the matcher verbatim is not",
      misplaced(one, 'subgraph PreToolUse\n        b2["Edit|Write|MultiEdit|NotebookEdit →<br/>protect-paths.sh"]\n    end') == [])
two = {"hooks": {"PreToolUse": [{"matcher": "Task", "hooks": [{"command": 'python3 "$X/.claude/hooks/g.py"'}]}]}}
check("NEGATIVE: a matcher that is only the tail of the label's matcher is caught («Task» in «Agent|Task →»)",
      misplaced(two, 'subgraph PreToolUse\n        b["Agent|Task → g.py"]\n    end') == ["PreToolUse: Task → g.py"])
three = {"hooks": {"Stop": [{"hooks": [{"command": 'python3 "$X/.claude/hooks/s.py"'}]}]}}
check("NEGATIVE: a script drawn under another event is caught",
      misplaced(three, 'subgraph PreToolUse\n        b["s.py"]\n    end\n    subgraph Stop\n        c["other.py"]\n    end') == ["Stop: - → s.py"])
four = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": 'python3 "$X/.claude/hooks/p.py"'}]}]}}
check("NEGATIVE: …and drawn in the box that follows its own event's box",
      misplaced(four, 'subgraph PreToolUse\n        b["Bash → other.py"]\n    end\n    subgraph Stop\n        c["Bash → p.py"]\n    end') == ["PreToolUse: Bash → p.py"])
five = {"hooks": {"Stop": [{"hooks": [{"command": 'bash "$X/.claude/hooks/v.sh"'}]}]}}
check("NEGATIVE: a script drawn but not wired is caught (a hook taken out of the settings and left on the map)",
      stale(five, 'subgraph Stop\n        s1["v.sh"]\n        s2["gone.py"]\n    end') == ["Stop: - → gone.py"])
check("NEGATIVE: a box for an event nothing is wired on is caught", stale(five, 'subgraph Stop\n        s1["v.sh"]\n    end\n    subgraph PostToolUseFailure\n    end')
      == ["subgraph PostToolUseFailure: nothing is wired on it"])
check("NEGATIVE: a matcher drawn wider than the one wired is caught", stale(four, 'subgraph PreToolUse\n        b["Bash|Edit → p.py"]\n    end') == ["PreToolUse: Bash|Edit → p.py"])
check("…and what a script runs, said in parentheses, is not taken as drawn", stale(five, 'subgraph Stop\n        s1["v.sh<br/>(gate.py stop)"]\n    end') == [])

print(f"\nPASS {PASS}   FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
