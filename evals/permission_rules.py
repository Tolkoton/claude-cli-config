#!/usr/bin/env python3
"""A reference matcher for Claude Code's Bash permission rules, as the documentation states them.

    python3 evals/permission_rules.py SETTINGS.json "<command>" [...]

Prints, for each command, the rule that decides it (deny, ask, allow) or `-` when no rule
matches, so a deny list can be reasoned about before it is applied. Nothing here is loaded
by Claude Code; it exists so a test can say "this list refuses X and lets Y through" from
the documented semantics rather than from a guess.

The semantics implemented (code.claude.com/docs/en/permissions, "Bash" and "Wildcard
patterns", read 2026-10-02):

- `Bash` with no parentheses matches every command.
- A `*` matches any text, including spaces; a rule with no `*` matches one exact command.
  Everything before the first `*` is matched as written.
- The `:*` suffix is the same as a trailing ` *` (`Bash(ls:*)` == `Bash(ls *)`).
- Claude Code splits a command on `&&`, `||`, `;`, `|`, `|&`, `&` and newlines, and a rule
  must match each subcommand independently; deny and ask rules apply when ANY subcommand
  matches. (Quoted text is not split here; neither is a subshell body — the docs say deny
  and ask also apply inside subshells and control-flow bodies, which this matcher
  approximates by also testing the whole command.)
- Precedence between the lists is not spelled out in one sentence; deny is checked first,
  then ask, then allow, which is the order that can never turn a deny into an allow. A
  different order would change only what this prints for a command that two lists match.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEPARATORS = re.compile(r"\|\||&&|\|&|;|\||&|\n")


def rule_regex(spec: str) -> re.Pattern[str]:
    """`Bash(<spec>)` -> an anchored regex for one subcommand."""
    if spec.endswith(":*"):
        spec = spec[:-2] + " *"
    parts = [re.escape(part) for part in spec.split("*")]
    body = ".*".join(parts)
    if spec.endswith(" *"):
        # `ls *` is documented as the family of ls commands; a bare `ls` belongs to it too.
        body = re.escape(spec[:-2]) + r"(?: .*)?"
    return re.compile(r"\A" + body + r"\Z", re.DOTALL)


def bash_rules(entries: list[str]) -> list[tuple[str, re.Pattern[str] | None]]:
    """(rule text, regex) for the Bash rules; regex None means `Bash` alone (everything)."""
    out: list[tuple[str, re.Pattern[str] | None]] = []
    for entry in entries:
        if entry == "Bash":
            out.append((entry, None))
        elif entry.startswith("Bash(") and entry.endswith(")"):
            out.append((entry, rule_regex(entry[len("Bash(") : -1])))
    return out


def subcommands(command: str) -> list[str]:
    """The command split on the documented separators, outside quotes, plus the whole command."""
    pieces: list[str] = []
    buf: list[str] = []
    quote = ""
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        m = SEPARATORS.match(command, i)
        if m:
            pieces.append("".join(buf))
            buf = []
            i = m.end()
            continue
        buf.append(ch)
        i += 1
    pieces.append("".join(buf))
    cleaned = [p.strip() for p in pieces if p.strip()]
    whole = command.strip()
    return cleaned + ([whole] if whole not in cleaned else [])


def matching_rule(entries: list[str], command: str) -> str | None:
    for text, regex in bash_rules(entries):
        if regex is None:
            return text
        if any(regex.match(sub) for sub in subcommands(command)):
            return text
    return None


def decide(settings: dict[str, object], command: str) -> tuple[str, str | None]:
    """('deny'|'ask'|'allow'|'-', the rule) for a command under a settings file's permissions."""
    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        return "-", None
    for verdict in ("deny", "ask", "allow"):
        entries = permissions.get(verdict)
        if isinstance(entries, list):
            rule = matching_rule([str(e) for e in entries], command)
            if rule is not None:
                return verdict, rule
    return "-", None


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print((__doc__ or "").split("\n\n")[0], file=sys.stderr)
        return 2
    settings = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    for command in argv[1:]:
        verdict, rule = decide(settings, command)
        print(f"{verdict:<6} {command!r}" + (f"  <- {rule}" if rule else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
