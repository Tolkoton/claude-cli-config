#!/usr/bin/env bash
# PreToolUse hook for Edit|Write|MultiEdit.
# Defense-in-depth for paths that should never be written to from a Claude session.
# Emits JSON with permissionDecision: "deny" so Claude sees the reason.
set -euo pipefail

INPUT=$(cat)

# Read one string field from the hook envelope: jq when present, python3 otherwise.
# Exit status 0 = read (the value may be empty, and input that is not JSON reads as empty —
# pinned by hook-checks ROBUST-*); 97 = no parser on this machine at all.
# WHY: the old idiom `jq ... 2>/dev/null || echo ""` turned "jq is not installed" into "the
# field is empty", and the hook then allowed everything. Measured with evals/: without jq
# every block of this hook became an allow. A deny control that
# cannot read its input must refuse, not wave the call through.
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
  echo "BLOCKED by protect-paths.sh: the tool call could not be read." >&2
  echo "Neither jq nor python3 parsed the hook input, so the target path cannot be checked." >&2
  echo "Install jq (or python3) and retry." >&2
  exit 2
fi

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# Narrow allowlist, checked BEFORE the deny patterns.
#
# `\.env$` below is a secrets heuristic: it cannot tell a config file from a
# credentials file by name. That is the right default and it stays. But this
# template ships .claude/project.env as a COMMITTED, secret-free config file
# and docs/TEMPLATE-SETUP.md Step 2 instructs the operator to edit it — so the
# heuristic was blocking the setup path of the very template it protects.
#
# Scoped as tightly as possible: this exact filename, only directly inside a
# .claude/ directory. Any other *.env, including .claude/anything-else.env and
# project.env outside .claude/, is still denied.
#
# Rejected alternative: renaming to project.sh. It reads better, but every
# project already built from this template has a project.env that three hooks
# read by name, and a rename would silently stop those hooks configuring
# themselves. Silent breakage of downstream projects costs more than one
# audited exception here. If a secret is ever put in this file, that is a
# review failure, not a hook failure — the file is committed and visible.
# ---------------------------------------------------------------------------
ALLOWED_PATTERNS=(
  '(^|/)\.claude/project\.env$'
)

for allowed in "${ALLOWED_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -qE "$allowed"; then
    exit 0
  fi
done

# Patterns to deny absolutely. Match against the full path.
PROTECTED_PATTERNS=(
  # The guardrails themselves. Added 2026-08-27 alongside the owner-ratified
  # grant letting spawned sessions write under .claude/hooks, .claude/unattended
  # and .claude/architecture so an overnight run can repair the harness it runs
  # on. Widening what an agent may edit is exactly when the things that define
  # its limits need a second layer: the permission list is one mechanism, and a
  # settings.local.json edit could quietly re-widen it. These three stay out of
  # reach in both mechanisms. Propose changes in .claude/overseer/audit.md.
  '\.claude/constitution\.md$'
  '\.claude/settings\.json$'
  '\.claude/settings\.local\.json$'
  '\.env$'
  '\.env\.'
  '/secrets/'
  '^secrets/'
  '/\.git/'
  '/\.ssh/'
  '/\.aws/'
  '/\.gnupg/'
  '/\.npmrc$'
  '/\.pypirc$'
  'id_rsa$'
  'id_rsa\.pub$'
  'id_ed25519$'
  'id_ed25519\.pub$'
  '\.pem$'
  '\.key$'
  '\.p12$'
  '\.pfx$'
  'credentials\.json$'
  'service-account.*\.json$'
  'gcloud-key\.json$'
  '/migrations/.*\.py$'
  '^migrations/.*\.py$'
  '/alembic/versions/.*\.py$'
  '^alembic/versions/.*\.py$'
  'alembic\.ini$'
  '/\.github/workflows/'
  '^\.github/workflows/'
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -qE "$pattern"; then
    # Encode with jq, not a heredoc. 23 of the 27 patterns above contain a
    # backslash (\.env$, \.pem$, /\.ssh/, ...), and interpolating one raw into
    # a JSON string produces an invalid escape — the harness then cannot parse
    # the decision and the deny is silently lost. Verified 2026-08-27: a write
    # to .env emitted 406 bytes of malformed JSON and was NOT denied.
    if ! command -v jq >/dev/null 2>&1; then
      # No jq to encode the JSON decision. A PreToolUse hook may equally deny with exit
      # code 2 and the reason on stderr — no encoding, so nothing to get wrong.
      echo "Path $FILE_PATH matches protected pattern $pattern. This is enforced by .claude/hooks/protect-paths.sh as defense-in-depth. If you genuinely need to edit this file, ask the user to do it manually outside Claude Code, or rename/move the file if the protection is wrong for your project." >&2
      exit 2
    fi
    jq -n --arg path "$FILE_PATH" --arg pattern "$pattern" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Path \($path) matches protected pattern \($pattern). This is enforced by .claude/hooks/protect-paths.sh as defense-in-depth. If you genuinely need to edit this file, ask the user to do it manually outside Claude Code, or rename/move the file if the protection is wrong for your project."}}'
    exit 0
  fi
done

exit 0
