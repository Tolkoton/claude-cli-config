"""The Python half of evals/hook_coverage.py: copied as `sitecustomize.py` onto PYTHONPATH of a traced run.

Notes every jump from line to line inside the engine's Python files and, when the interpreter
ends, writes them down with the SHA-1 of each file (HOOKCOV_DIR/py/<pid>.<random>.json). The
convention is coverage.py's, whose analysis reads the result: entering a code object is a jump
from minus its first line, leaving it a jump to minus its first line.

Without HOOKCOV_DIR in the environment it does nothing. Standard library only, Python 3.12+.
"""

import atexit
import hashlib
import json
import opcode
import os
import sys
import threading

_DIR = os.environ.get("HOOKCOV_DIR")
_ARCS: dict = {}
_SCOPE: dict = {}
_YIELD = opcode.opmap.get("YIELD_VALUE", -1)
_RESUME = opcode.opmap.get("RESUME", -1)


def _hookcov_scope(name):
    known = _SCOPE.get(name)
    if known is None:
        known = _SCOPE[name] = name.endswith(".py") and (
            "/.claude/hooks/" in name or "/.claude/unattended/" in name or name.endswith("/engine.py") or name == "engine.py")
    return known


def _hookcov_trace(frame, event, arg):
    code = frame.f_code
    if not _hookcov_scope(code.co_filename):
        return None
    arcs = _ARCS.get(code.co_filename)
    if arcs is None:
        arcs = _ARCS[code.co_filename] = set()
    first = code.co_firstlineno
    raw = code.co_code
    # A frame starts at RESUME: argument 0 is a call, anything else a generator taken up again.
    lasti = frame.f_lasti
    last = [-first if lasti < 0 or raw[lasti + 1] == 0 else frame.f_lineno]

    def local(frame, event, arg):
        if event == "line":
            line = frame.f_lineno
            arcs.add((last[0], line))
            last[0] = line
        elif event == "return":
            at = frame.f_lasti
            if not (raw[at] == _YIELD or (at + 2 < len(raw) and raw[at + 2] == _RESUME)):  # a yield is not a way out
                arcs.add((last[0], -first))
        return local

    return local


def _hookcov_write():
    sys.settrace(None)
    files = {}
    for name, arcs in list(_ARCS.items()):
        try:
            with open(name, "rb") as handle:
                files[os.path.abspath(name)] = {"sha": hashlib.sha1(handle.read()).hexdigest(), "arcs": sorted(arcs)}
        except OSError:
            pass
    if files:
        try:
            with open(os.path.join(_DIR, "py", f"{os.getpid()}.{os.urandom(4).hex()}.json"), "w", encoding="utf-8") as handle:
                json.dump(files, handle)
        except OSError:
            pass


if _DIR:
    atexit.register(_hookcov_write)
    threading.settrace(_hookcov_trace)
    sys.settrace(_hookcov_trace)
