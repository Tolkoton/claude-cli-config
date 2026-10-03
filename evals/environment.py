#!/usr/bin/env python3
"""The name of the environment a result file is recorded in: the operating system and its version.

    python3 evals/environment.py            # linux-ubuntu-22.04, macos-14, ...

Recorded results live in `evals/baseline/<environment>/`. The engine is a shared project for
many machines, so a folder is named after what can differ between two recordings — the
operating system — and never after the machine or its owner (board 030). Every script that
writes or reads a baseline takes the name from here:

- `@env` in a path stands for this environment: `--out evals/baseline/@env/results-x.json`;
- a script refuses to record into the folder of another environment (`out_path`);
- a recorded file carries the name (`environment.name`, or `environment` where the file has no
  such object), and a comparison of files from two environments says so (`cross_note`).

Linux: `linux-<ID>-<VERSION_ID>` from /etc/os-release (`linux-<ID>` for a rolling release,
`linux` without the file). macOS: `macos-<major version>`. Anything else: the system's name
and the major version of its release.

Standard library only, Python 3.12+.
"""

from __future__ import annotations

import argparse
import platform
import re
import sys
from pathlib import Path
from typing import Any

JsonObj = dict[str, Any]

PLACEHOLDER = "@env"
BASELINE_DIR = Path(__file__).resolve().parent / "baseline"
OS_RELEASE = Path("/etc/os-release")
# What a folder under evals/baseline/ may be called: tests/test_baseline_environments.py.
NAME_SHAPE = re.compile(r"^(?:linux(?:-[a-z0-9]+(?:-[0-9][0-9.]*)?)?|macos-[0-9]+|[a-z][a-z0-9]*-[0-9]+)$")
UNKNOWN = "unknown"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "", text.lower())


def os_release_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def environment_name(system: str | None = None, os_release: str | None = None, release: str | None = None) -> str:
    """This environment's name. The arguments stand in for the machine in the tests."""
    system = platform.system() if system is None else system
    if system == "Linux":
        if os_release is None:
            os_release = OS_RELEASE.read_text(encoding="utf-8") if OS_RELEASE.is_file() else ""
        fields = os_release_fields(os_release)
        parts = ["linux", slug(fields.get("ID", "")), slug(fields.get("VERSION_ID", ""))]
        return "-".join(p for p in parts[: 3 if parts[1] else 1] if p)
    if release is None:
        release = platform.mac_ver()[0] if system == "Darwin" else platform.release()
    major = slug(release).split(".")[0] or "0"
    return f"{'macos' if system == 'Darwin' else slug(system) or UNKNOWN}-{major}"


def baseline_path(text: str) -> Path:
    """An argparse type for a file that is READ: `@env` becomes this environment's name."""
    return Path(*(environment_name() if part == PLACEHOLDER else part for part in Path(text).parts))


def baseline_folder(path: Path) -> str | None:
    """The environment folder a path under evals/baseline/ lies in; None for any other path."""
    try:
        parts = path.resolve().relative_to(BASELINE_DIR).parts
    except ValueError:
        return None
    return parts[0] if len(parts) > 1 else None


def out_path(text: str) -> Path:
    """An argparse type for a file that is WRITTEN: as `baseline_path`, and a recording never
    goes into another environment's folder."""
    path = baseline_path(text)
    folder, here = baseline_folder(path), environment_name()
    if folder is not None and folder != here:
        raise argparse.ArgumentTypeError(
            f"{text}: this environment is {here}, and its results go to evals/baseline/{here}/ "
            f"(write evals/baseline/{PLACEHOLDER}/{path.name}), not to {folder}/"
        )
    return path


def recorded_in(report: JsonObj, path: Path | None = None) -> str:
    """The environment a result file was recorded in: what the file says, else the folder it lies in."""
    env = report.get("environment")
    name = env.get("name") if isinstance(env, dict) else env
    if isinstance(name, str) and name:
        return name
    return (baseline_folder(path) if path else None) or UNKNOWN


def cross_note(first: str, second: str, names: tuple[str, str] = ("base", "candidate")) -> str | None:
    """The line a comparison prints when its two sides were not recorded in one environment."""
    if first == second and first != UNKNOWN:
        return None
    if UNKNOWN in (first, second):
        return (f"ENVIRONMENT NOT RECORDED: {names[0]} — {first}, {names[1]} — {second}. "
                "If the two sides come from different environments, a difference may be the environment's, not the engine's.")
    return (f"CROSS-ENVIRONMENT COMPARISON: {names[0]} was recorded on {first}, {names[1]} on {second}. "
            "A difference may be the environment's, not the engine's.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", action="store_true", help="print this environment's baseline folder instead of its name")
    args = parser.parse_args()
    print(BASELINE_DIR / environment_name() if args.dir else environment_name())
    return 0


if __name__ == "__main__":
    sys.exit(main())
