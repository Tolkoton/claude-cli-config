#!/usr/bin/env python3
"""What settings actually apply, from the files Claude Code reads — and whether two set-ups agree.

    python3 evals/settings_parity.py effective [--user F] [--project F] [--local F] [--personal F]
    python3 evals/settings_parity.py compare  --before-user F --before-project F [--before-local F]
                                              --after-user F  --after-project F  [--after-local F]
                                              [--after-personal F] [--json]

`effective` prints the settings that are in force after Claude Code has read the user file
(`~/.claude/settings.json`), the shared project file (`.claude/settings.json`) and the project
local file (`.claude/settings.local.json`), combined by the documented rules: a key set at a
higher level overrides the same key lower (local > project > user); list keys MERGE across
files instead of overriding; `fallbackModel` and `modelPicker` are taken whole from the highest
file that sets them. Hooks are reduced to the set of (event, matcher, type, command) handlers,
because an identical handler defined in two files runs once. Keys starting with `_` and
`$schema` are comments, not settings. Source: code.claude.com/docs/en/settings,
/docs/en/hooks ("Merging across settings levels"), read 2026-10-02.

`--personal F` merges the engine's personal layer into the user file IN MEMORY, with the same
code `engine.py install --personal` uses — so the effect of that install can be shown without
writing a byte under the home directory.

`compare` computes both sides and lists every path whose effective value differs. Exit 0 when
the two set-ups are the same, 1 when they differ, 2 on unusable input. This is the parity check
for splitting the shared settings into a shared and a personal layer: before = today's files,
after = the proposed shared file plus the personal layer merged into the home file.

Standard library only, Python 3.12+. Reads files; never writes one.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TAKEN_WHOLE = {"fallbackModel", "modelPicker"}
LEVELS = ("user", "project", "local")

JsonObj = dict[str, Any]


class ParityError(Exception):
    """Input that cannot be read; exit status 2."""


def load_engine() -> Any:
    spec = importlib.util.spec_from_file_location("engine", ROOT / "engine.py")
    if spec is None or spec.loader is None:
        raise ParityError(f"cannot load {ROOT / 'engine.py'}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["engine"] = module  # dataclasses look their module up while the class is built
    spec.loader.exec_module(module)
    return module


def read_settings(path: Path | None) -> JsonObj:
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ParityError(f"{path}: {exc}") from None
    if not isinstance(data, dict):
        raise ParityError(f"{path}: a settings file holds a JSON object")
    settings: JsonObj = strip_comments({str(k): v for k, v in data.items()})
    return settings


def strip_comments(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): strip_comments(v) for k, v in value.items() if not str(k).startswith("_") and k != "$schema"
        }
    if isinstance(value, list):
        return [strip_comments(v) for v in value]
    return value


def merge_levels(lower: JsonObj, higher: JsonObj) -> JsonObj:
    """The documented combination of two settings levels; `higher` wins where keys collide."""
    out: JsonObj = dict(lower)
    for key, value in higher.items():
        if key not in out or key in TAKEN_WHOLE:
            out[key] = value
        elif isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = merge_levels(out[key], value)
        elif isinstance(out[key], list) and isinstance(value, list):
            out[key] = list(out[key]) + [v for v in value if v not in out[key]]
        else:
            out[key] = value
    return out


def hook_handlers(hooks: Any) -> list[str]:
    """Flatten a `hooks` block to its handlers: `event|matcher|type|command` — one line per handler."""
    found: set[str] = set()
    if not isinstance(hooks, dict):
        return []
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            matcher = str(group.get("matcher", ""))
            for handler in group.get("hooks", []) or []:
                if isinstance(handler, dict):
                    kind = str(handler.get("type", ""))
                    command = str(handler.get("command") or handler.get("prompt") or "")
                    found.add(f"{event}|{matcher}|{kind}|{command}")
    return sorted(found)


def effective(files: dict[str, JsonObj]) -> JsonObj:
    combined: JsonObj = {}
    for level in LEVELS:
        combined = merge_levels(combined, files.get(level, {}))
    if "hooks" in combined:
        combined["hooks"] = hook_handlers(combined["hooks"])
    return combined


def duplicate_handlers(files: dict[str, JsonObj]) -> list[str]:
    """Handlers that two levels both wire with the SAME string (Claude Code runs them once) —
    reported so a home file that repeats a project's hook is visible."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for level in LEVELS:
        for handler in hook_handlers(files.get(level, {}).get("hooks")):
            if handler in seen:
                duplicates.append(f"{handler}  (in {seen[handler]} and {level})")
            else:
                seen[handler] = level
    return duplicates


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Leaf paths -> values. Lists are compared as whole values (their order is not a setting)."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, inner in value.items():
            out.update(flatten(inner, f"{prefix}{key}."))
        return out
    if isinstance(value, list):
        return {prefix.rstrip("."): sorted(json.dumps(v, sort_keys=True, ensure_ascii=False) for v in value)}
    return {prefix.rstrip("."): value}


def differences(before: JsonObj, after: JsonObj) -> list[dict[str, Any]]:
    left, right = flatten(before), flatten(after)
    out: list[dict[str, Any]] = []
    for path in sorted(set(left) | set(right)):
        if left.get(path, "<absent>") != right.get(path, "<absent>"):
            out.append({"path": path, "before": left.get(path, "<absent>"), "after": right.get(path, "<absent>")})
    return out


def gather(args: argparse.Namespace, side: str) -> dict[str, JsonObj]:
    files: dict[str, JsonObj] = {}
    for level in LEVELS:
        path = getattr(args, f"{side}{level}", None)
        files[level] = read_settings(Path(path)) if path else {}
    personal = getattr(args, f"{side}personal", None)
    if personal:
        engine = load_engine()
        layer = engine.parse_personal(Path(personal).read_bytes(), personal)
        plan = engine.PersonalPlan(Path(personal), {})
        files["user"] = strip_comments(engine.merge_into(files["user"], layer, plan))
    return files


def cmd_effective(args: argparse.Namespace) -> int:
    files = gather(args, "")
    print(json.dumps(effective(files), indent=2, ensure_ascii=False, sort_keys=True))
    for line in duplicate_handlers(files):
        print(f"duplicate handler: {line}", file=sys.stderr)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    before = effective(gather(args, "before_"))
    after = effective(gather(args, "after_"))
    diff = differences(before, after)
    if args.json:
        print(json.dumps({"differences": diff, "settings_compared": len(flatten(before))}, indent=2, ensure_ascii=False))
    else:
        for d in diff:
            print(f"  DIFF {d['path']}")
            print(f"         before: {json.dumps(d['before'], ensure_ascii=False)}")
            print(f"         after:  {json.dumps(d['after'], ensure_ascii=False)}")
        same = len(flatten(before)) - len(diff)
        if diff:
            print(f"\n{len(diff)} setting(s) differ, {same} identical")
        else:
            print(f"identical: all {same} effective settings are the same on both sides")
    return 1 if diff else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="settings_parity.py", description=(__doc__ or "").split("\n\n")[1])
    sub = parser.add_subparsers(dest="command", required=True)
    eff = sub.add_parser("effective", help="print the settings in force for one set of files")
    for level in LEVELS:
        eff.add_argument(f"--{level}", metavar="FILE")
    eff.add_argument("--personal", metavar="FILE", help="merge this personal layer into the user file in memory")
    eff.set_defaults(handler=cmd_effective)
    cmp = sub.add_parser("compare", help="list the effective settings that differ between two set-ups")
    for side in ("before", "after"):
        for level in LEVELS:
            cmp.add_argument(f"--{side}-{level}", metavar="FILE")
        cmp.add_argument(f"--{side}-personal", metavar="FILE")
    cmp.add_argument("--json", action="store_true")
    cmp.set_defaults(handler=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code: int = args.handler(args)
        return code
    except ParityError as exc:
        print(f"settings_parity.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
