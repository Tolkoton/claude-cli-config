#!/usr/bin/env bash
# PostToolUse hook for Edit|Write|MultiEdit.
# Auto-formats code files after an edit. Silent on success; never blocks.
#
# Configuration: .claude/project.env (sourced if present).
# Key variables: FORMAT_CMD (with {file} placeholder), CODE_EXTENSIONS.
# See docs/TEMPLATE-SETUP.md for all variables.
set -euo pipefail

INPUT=$(cat)

# Read one string field from the hook envelope: jq when present, python3 otherwise.
# Exit status 0 = read (the value may be empty, and input that is not JSON reads as empty —
# pinned by hook-checks ROBUST-*); 97 = no parser on this machine at all.
# WHY: the old idiom `jq ... 2>/dev/null || echo ""` turned "jq is not installed" into "the
# field is empty", and the hook then allowed everything. Measured with evals/: without jq
# every block of this hook became an allow. Here the
# consequence was milder — nothing got formatted — but just as silent.
read_field() {
  if command -v jq >/dev/null 2>&1; then
    local expr="" path
    for path in "$@"; do expr="${expr:+$expr // }.${path}"; done
    printf '%s' "$INPUT" | jq -r "(${expr}) // \"\"" 2>/dev/null || true
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read())
except ValueError:
    sys.exit(0)
for path in sys.argv[1:]:
    node = data
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, str) and node:
        sys.stdout.write(node)
        break
' "$@"
  else
    return 97
  fi
}

if ! FILE_PATH=$(read_field tool_input.file_path tool_input.path 2>/dev/null); then
  echo "⚠ format-on-edit: could not read the hook input (no jq and no python3) — nothing formatted." >&2
  exit 0
fi

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# Resolve project root: CLAUDE_PROJECT_DIR → git → CWD
# ---------------------------------------------------------------------------
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
fi
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT="$(pwd)"
fi
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Load project configuration
# ---------------------------------------------------------------------------
CODE_EXTENSIONS=""
FORMAT_CMD=""

ENV_FILE="${PROJECT_ROOT}/.claude/project.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1091
  source "$ENV_FILE"
else
  echo "⚠ format-on-edit: .claude/project.env not found at ${ENV_FILE}" >&2
  echo "  Using built-in formatter defaults (ruff/prettier). See docs/TEMPLATE-SETUP.md." >&2
fi

# ---------------------------------------------------------------------------
# Normalize CODE_EXTENSIONS: tolerate commas, extra whitespace, leading dots.
# ".ts,.tsx" / "ts tsx" / ".ts .tsx" must all normalize the same way.
# ---------------------------------------------------------------------------
CODE_EXTENSIONS_RAW="$CODE_EXTENSIONS"
if [ -n "$CODE_EXTENSIONS_RAW" ]; then
  NORMALIZED=""
  for tok in $(echo "$CODE_EXTENSIONS_RAW" | tr ',' ' '); do
    tok="${tok#.}"
    tok=$(echo "$tok" | tr '[:upper:]' '[:lower:]')
    [ -n "$tok" ] && NORMALIZED="$NORMALIZED $tok"
  done
  CODE_EXTENSIONS="${NORMALIZED# }"
  if [ -z "$CODE_EXTENSIONS" ]; then
    echo "⚠ format-on-edit: CODE_EXTENSIONS='$CODE_EXTENSIONS_RAW' did not parse into" >&2
    echo "  any usable extension. Use space- or comma-separated values, e.g. \"ts tsx\" or \"ts,tsx\"." >&2
    echo "  FORMAT_CMD will never match — falling back to built-in handlers only." >&2
  fi
fi

# ---------------------------------------------------------------------------
# Get the file extension (lowercase, no dot)
# ---------------------------------------------------------------------------
BASENAME=$(basename "$FILE_PATH")
EXT="${BASENAME##*.}"

# If filename has no extension, EXT equals BASENAME — treat as no extension.
# Compare BEFORE lowercasing: lowercasing first breaks this test for any
# extensionless name containing a capital ("Makefile" gave EXT="makefile" vs
# BASENAME="Makefile"), so the whole filename leaked through as an extension.
if [ "$EXT" = "$BASENAME" ]; then
  EXT=""
else
  EXT=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
fi

# ---------------------------------------------------------------------------
# Configured path: FORMAT_CMD applies to CODE_EXTENSIONS files
# ---------------------------------------------------------------------------
if [ -n "$FORMAT_CMD" ] && [ -n "$CODE_EXTENSIONS" ]; then
  # Check if this file's extension is in CODE_EXTENSIONS
  for configured_ext in $CODE_EXTENSIONS; do
    configured_ext=$(echo "$configured_ext" | tr '[:upper:]' '[:lower:]' | sed 's/^\.//')
    if [ "$EXT" = "$configured_ext" ]; then
      # Replace {file} placeholder with the actual path
      # printf %q, not a bare expansion: the result is eval'd, so a path
      # containing a space would otherwise split into two arguments and the
      # formatter would run on the wrong target.
      CMD="${FORMAT_CMD/\{file\}/$(printf '%q' "$FILE_PATH")}"
      # stdout, not just stderr: stdout is the hook protocol channel, and a
      # chatty formatter ("1 file reformatted") would leak into the session on
      # every single edit. This hook never reports, so neither stream has a
      # consumer.
      eval "$CMD" >/dev/null 2>&1 || true
      exit 0
    fi
  done
  # Extension didn't match — fall through to built-in handlers below.
fi

# ---------------------------------------------------------------------------
# Built-in handlers (always active, regardless of CODE_EXTENSIONS)
# ---------------------------------------------------------------------------
case "$FILE_PATH" in
  *.py)
    # --force-exclude: honour exclude rules even for a file passed explicitly. Without it
    # ruff formats whatever it is handed — including the engine's own files under .claude/
    # (excluded by .claude/ruff.toml) and anything the project itself excludes, such as
    # generated code.
    # If we reached here, FORMAT_CMD either wasn't set or didn't match this
    # extension — use Python built-in auto-detect regardless.
    if [ -f uv.lock ] && command -v uv >/dev/null 2>&1; then
      uv run ruff format --force-exclude "$FILE_PATH" >/dev/null 2>&1 || true
      uv run ruff check --force-exclude --fix --select I "$FILE_PATH" >/dev/null 2>&1 || true
    elif [ -f poetry.lock ] && command -v poetry >/dev/null 2>&1; then
      poetry run ruff format --force-exclude "$FILE_PATH" >/dev/null 2>&1 || true
      poetry run ruff check --force-exclude --fix --select I "$FILE_PATH" >/dev/null 2>&1 || true
    elif command -v ruff >/dev/null 2>&1; then
      ruff format --force-exclude "$FILE_PATH" >/dev/null 2>&1 || true
      ruff check --force-exclude --fix --select I "$FILE_PATH" >/dev/null 2>&1 || true
    elif command -v black >/dev/null 2>&1; then
      black --quiet "$FILE_PATH" >/dev/null 2>&1 || true
    fi
    ;;
  *.json)
    if command -v jq >/dev/null 2>&1; then
      tmp=$(mktemp)
      if jq . "$FILE_PATH" > "$tmp" 2>/dev/null; then
        mv "$tmp" "$FILE_PATH"
      else
        rm -f "$tmp"
      fi
    fi
    ;;
  *.md|*.yml|*.yaml|*.toml)
    if command -v prettier >/dev/null 2>&1; then
      prettier --write --log-level silent "$FILE_PATH" >/dev/null 2>&1 || true
    fi
    ;;
esac

exit 0
