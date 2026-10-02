#!/usr/bin/env python3
"""SOURCE_DIRS matches the paths Claude Code actually sends.

overseer_stop.py counts an Edit/Write as the "code edit" half of its trigger when the
file lies under one of SOURCE_DIRS. Claude Code hands the hook ABSOLUTE paths. Until the
package 3c fix round a multi-segment entry — `backend/src`, the very example project.env
gives for a monorepo, or `.claude/hooks` for this repository — matched a relative path and
nothing else: the dir-segment check split the path on "/" and looked for the whole entry as
one segment. The setting was inert in every real session and nothing noticed, because the
single-segment `src` of every sandbox took a different branch.

Cases: relative and absolute, single- and multi-segment, the look-alike prefixes that must
NOT match (src2/, srcfoo/, tests_old/), a dir deep in the path, the extension fallback, and
this repository's own project.env parsed by the hook's own reader.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def load_hook() -> Any:
    spec = importlib.util.spec_from_file_location("overseer_stop", ROOT / ".claude/hooks/overseer_stop.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["overseer_stop"] = module
    spec.loader.exec_module(module)
    return module


PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


def main() -> int:
    hook = load_hook()
    py = frozenset({"py", "sh"})

    def dirs(raw: str) -> list[str]:
        result: list[str] = hook._build_source_dirs({"SOURCE_DIRS": raw})
        return result

    def is_code(path: str, raw: str, exts: frozenset[str] = py) -> bool:
        result: bool = hook._is_code_path(path, dirs(raw), exts)
        return result

    print("single-segment dir, as every sandbox has it:")
    check("relative src/app.py", is_code("src/app.py", "src"))
    check("absolute /work/proj/src/app.py", is_code("/work/proj/src/app.py", "src"))
    check("nested src/pkg/mod.py", is_code("/work/proj/src/pkg/mod.py", "src"))
    check("src2/app.py does NOT match src", not is_code("/work/proj/src2/app.py", "src"))
    check("srcfoo/app.py does NOT match src", not is_code("srcfoo/app.py", "src"))
    check("docs/readme.md does NOT match src", not is_code("/work/proj/docs/readme.md", "src"))
    check("a file named src is not under src/", not is_code("/work/proj/src", "src"))
    check("other-src/app.py does NOT match src (suffix look-alike)", not is_code("/work/proj/other-src/app.py", "src"))
    check("src as the final segment of a directory path does not match", not is_code("/work/proj/lib/src", "src"))

    print("multi-segment dir — the documented monorepo example and this repository:")
    check("relative backend/src/app.py", is_code("backend/src/app.py", "backend/src frontend/src"))
    check("ABSOLUTE backend/src/app.py (was False before the fix)",
          is_code("/work/proj/backend/src/app.py", "backend/src frontend/src"))
    check("absolute frontend/src/x.ts (second entry)", is_code("/work/proj/frontend/src/x.ts", "backend/src frontend/src"))
    check("absolute .claude/hooks/block-dangerous.sh", is_code("/work/engine/.claude/hooks/block-dangerous.sh", ".claude/hooks tests"))
    check("absolute tests/test_x.py with a multi-segment list", is_code("/work/engine/tests/test_x.py", ".claude/hooks tests"))
    check("tests_old/t.py does NOT match tests", not is_code("/work/engine/tests_old/t.py", ".claude/hooks tests"))
    check("backend/app.py does NOT match backend/src", not is_code("/work/proj/backend/app.py", "backend/src"))
    check("x.claude/hooks/a.sh does NOT match .claude/hooks (suffix look-alike)", not is_code("/work/x.claude/hooks/a.sh", ".claude/hooks"))
    check(".claude/hooks as the final segment does not match", not is_code("/work/engine/.claude/hooks", ".claude/hooks"))
    check("comma-separated list parses the same", is_code("/work/proj/backend/src/app.py", "backend/src,frontend/src"))
    check("trailing slash in the setting is harmless", is_code("/work/proj/backend/src/app.py", "backend/src/"))
    check("backslashes are normalised", is_code("C:\\proj\\backend\\src\\app.py", "backend/src"))

    print("fallbacks:")
    check("empty SOURCE_DIRS: extension decides (py)", is_code("/work/proj/anything/x.py", ""))
    check("empty SOURCE_DIRS: extension decides (md is not code)", not is_code("/work/proj/anything/x.md", ""))
    check("both empty: any edit counts", is_code("/work/proj/anything/x.md", "", frozenset()))
    check("SOURCE_DIRS set: a .md under it counts (dirs win over extensions)",
          is_code("/work/proj/src/notes.md", "src"))

    print(f"\nPASS {PASS}   FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
