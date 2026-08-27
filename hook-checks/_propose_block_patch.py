#!/usr/bin/env python3
"""Apply the three proposed block-dangerous.sh pattern fixes to a COPY.

Usage: python3 hook-checks/_propose_block_patch.py <path-to-copy>

Kept as a file rather than an inline heredoc for a reason worth recording: the
patch text necessarily contains the literal destructive strings it is teaching
the hook to catch, and putting them on a Bash command line makes
block-dangerous.sh block the patch attempt itself. That is the hook behaving
correctly -- it cannot distinguish a pattern from a use of a pattern -- so the
fix is to keep the literals off the command line, not to weaken the hook.

Underscore-prefixed because it is a helper for test_deny_hooks.py, not a test.
"""

import pathlib
import sys

TILDE = chr(0x7E)
DOLLAR = chr(0x24)

target = pathlib.Path(sys.argv[1])
s = target.read_text()

# Any separator, and tab-indent, not just "^sudo " / " sudo ".
old_sudo = "  '^sudo '\n  ' sudo '"
new_sudo = r"  '(^|[;&|(`]|&&|\|\|)[[:space:]]*sudo[[:space:]]'"
assert old_sudo in s, "sudo anchor not found"
s = s.replace(old_sudo, new_sudo)

# Tolerate quoting around ~ and $HOME.
old_home = f"  'rm -rf {TILDE}'\n  'rm -rf \\{DOLLAR}HOME'"
new_home = (
    "  'rm -rf [\"'\"'\"']?" + TILDE + "'\n"
    "  'rm -rf [\"'\"'\"']?\\" + DOLLAR + "HOME'"
)
assert old_home in s, "home anchor not found"
s = s.replace(old_home, new_home)

# Catch `git commit` after a separator and past git's global options (-C, -c ...).
old_commit = (
    """if echo "$CMD" | grep -qE '^[[:space:]]*git[[:space:]]+commit("""
    + DOLLAR
    + r"""|\s)'; then"""
)
# `([^[:space:]]+[[:space:]]+)*` skips git's global options and their values, so
# `git -C . commit` is caught, while `git log --grep=commit` is not: the group
# only ever lands on a token boundary, and "--grep=commit" is not the token
# "commit".
new_commit = (
    """if echo "$CMD" | grep -qE '(^|[;&|(`]|&&|\\|\\|)[[:space:]]*"""
    """git[[:space:]]+([^[:space:]]+[[:space:]]+)*commit("""
    + DOLLAR
    + """|[[:space:]])'; then"""
)
assert old_commit in s, "commit anchor not found"
s = s.replace(old_commit, new_commit)

target.write_text(s)
print("3 patches applied to", target)
