#!/usr/bin/env bash
# SessionStart hook: say what this machine LACKS for the engine to enforce anything.
#
# Silent when nothing is missing. SessionStart output is added to the context of every
# session, so a routine "all good" line would be paid for in every session forever; a
# missing tool, on the other hand, used to cost nothing up front and everything later —
# hooks that silently enforced nothing, or a lint gate that could only ever fail.
#
# Never blocks (a SessionStart hook cannot) and never fails: exit 0 always.

ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -n "$ROOT" ] || ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

have() { command -v "$1" >/dev/null 2>&1; }

MISSING=()

have git || MISSING+=("git — the hooks cannot read the branch or the diff: the commit policy falls back to blocking every commit, and verify-on-stop sees no changes and checks nothing.")

if ! have python3; then
  MISSING+=("python3 — overseer_stop.py, park-ask-gated.py and auto-approve-web.py cannot run: no audit is ever requested, and unattended runs hang on the first permission prompt.")
  have jq || MISSING+=("jq (and no python3 to fall back on) — block-dangerous.sh and protect-paths.sh will REFUSE every Bash and Edit call rather than let it through unchecked.")
fi

# Can the Stop gate run the tools the project itself configured? Mirrors the hook's own
# choice of runner: uv when uv.lock exists, poetry when poetry.lock exists, else bare tools.
if [ -f "$ROOT/pyproject.toml" ]; then
  RUNNER=""
  if [ -f "$ROOT/uv.lock" ]; then
    have uv && RUNNER="uv" || MISSING+=("uv — this project has uv.lock, so ruff, mypy and pytest are expected to come from \`uv run\`.")
  elif [ -f "$ROOT/poetry.lock" ]; then
    have poetry && RUNNER="poetry" || MISSING+=("poetry — this project has poetry.lock, so ruff, mypy and pytest are expected to come from \`poetry run\`.")
  fi
  if [ -z "$RUNNER" ] && [ ! -f "$ROOT/uv.lock" ] && [ ! -f "$ROOT/poetry.lock" ]; then
    for tool in ruff mypy; do
      if grep -q "\[tool\.${tool}" "$ROOT/pyproject.toml" 2>/dev/null && ! have "$tool"; then
        MISSING+=("${tool} — pyproject.toml configures it, there is no uv.lock or poetry.lock to run it through, and it is not on PATH: verify-on-stop will block every Python change with 'command not found'.")
      fi
    done
  fi
fi

[ "${#MISSING[@]}" -eq 0 ] && exit 0

echo "## engine environment check — missing on this machine"
for line in "${MISSING[@]}"; do
  echo "- $line"
done
echo "Tell the user about the items above before relying on hook enforcement in this session."
exit 0
