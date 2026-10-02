#!/usr/bin/env bash
# PreToolUse hook for Bash. Blocks destructive commands and git commit.
# Exit 2 = block + show reason to Claude via stderr.
# Exit 0 = allow.
set -euo pipefail

INPUT=$(cat)

# --- fire once per event -------------------------------------------------------------------
# The same hook wired at two settings levels under DIFFERENT command strings runs twice
# (an identical string already runs once — code.claude.com/docs/en/hooks, "Merging across
# settings levels"). The project's own copy, $CLAUDE_PROJECT_DIR/.claude/hooks/<name>, always
# runs; any other copy (a home-level ~/.claude/hooks/<name>, say) stands down when the project
# wires hooks/<name> in .claude/settings.json or settings.local.json — and says so on stderr,
# so a stand-down is never mistaken for an allow. Decided from files only, never from timing
# or order. ENGINE_HOOK_ALWAYS_RUN=1 skips this: the one override, in the safe direction.
engine_stand_down() {
  [ "${ENGINE_HOOK_ALWAYS_RUN:-}" = "1" ] && return 1
  [ -n "${CLAUDE_PROJECT_DIR:-}" ] || return 1
  local name mine self theirs
  name="$(basename "${BASH_SOURCE[0]}")"
  mine="$CLAUDE_PROJECT_DIR/.claude/hooks/$name"
  [ -f "$mine" ] || return 1
  self="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)/$name"
  theirs="$(cd "$(dirname "$mine")" 2>/dev/null && pwd -P)/$name"
  [ "$self" != "$theirs" ] || return 1
  grep -qsF "hooks/$name" "$CLAUDE_PROJECT_DIR/.claude/settings.json" \
    "$CLAUDE_PROJECT_DIR/.claude/settings.local.json" || return 1
  echo "STOOD_DOWN: $name defers to $mine (wired by the project; this copy is $self)" >&2
  return 0
}
if engine_stand_down; then exit 0; fi

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

if ! CMD=$(read_field tool_input.command 2>/dev/null); then
  echo "BLOCKED by claude-autonomy safety hook: the tool call could not be read." >&2
  echo "Neither jq nor python3 parsed the hook input, so this command cannot be checked." >&2
  echo "Install jq (or python3) and retry. Until then Bash calls are refused on purpose:" >&2
  echo "an unchecked command is a breach, a refused one is a nuisance." >&2
  exit 2
fi

if [ -z "$CMD" ]; then
  exit 0
fi

# NOTE on false positives — decided deliberately (S7).
# These patterns match anywhere in the command text, INCLUDING inside quoted
# string literals and heredoc bodies. So merely *describing* a dangerous command
# in documentation is blocked as if it were being run. This was hit twice for
# real while filing and fixing node S7.
# It is NOT fixed here, and that is a choice: telling a real command from a
# quoted mention needs shell parsing, and the obvious shortcut — strip heredoc
# bodies before matching — opens a genuine hole, because a heredoc fed to a
# shell executes its body. For a deny control a false positive is a nuisance
# and a false negative is a breach, so the bias stays where it is.
# Workaround when a write is blocked by its own documentation text: split the
# literal across a concatenation, or write the file with the Edit/Write tool
# instead of a shell heredoc.
#
# Command-position prefix used below is (^|[;&|(`])[[:space:]]* — start of the
# command OR just after a separator. A bare ^ let a compound command walk past
# the check, and a leading tab defeated both anchored forms.

# Truly destructive patterns. Order: most specific first.
DANGEROUS_PATTERNS=(
  'rm -rf /[^a-zA-Z0-9_.]'
  'rm -rf /$'
  'rm -rf ~'
  'rm[[:space:]]+-[a-z]*[rf][a-z]*[[:space:]]+["'"'"']?\$\{?HOME\}?'
  'rm -rf \*'
  'rm -rf \.\s*$'
  'rm -rf \./\*'
  'rm -rf \$\('
  'rm -fr \$\('
  'rm -r \$\('
# NOTE: the git-commit pattern is deliberately NOT in this unconditional list.
# It lives in the branch-aware commit policy near the end of the file, because
# after 2026-08-27 a commit is legal on an unattended/<date> branch and illegal
# everywhere else. Putting it here would block it on every branch, including the
# one where it is now the point.
  'git push --force'
  'git push -f '
  'git push --force-with-lease'
  'git reset --hard origin'
  'git reset --hard HEAD~'
  'git filter-branch'
  'git clean -fdx'
  'git clean -fX'
  'git update-ref -d'
  'chmod -R 777'
  'chmod 777 '
  ':\(\)\{ :\|:& \};:'
  'curl [^|]+\| (sh|bash|zsh|fish)'
  'wget [^|]+\| (sh|bash|zsh|fish)'
  '(^|[;&|(`])[[:space:]]*sudo[[:space:]]'
  'mkfs\.'
  'dd if=.*of=/dev/(sd|disk|nvme|hd)'
  '> /dev/(sda|sdb|disk|nvme|hd)'
  'shred '
  'wipefs '
  'twine upload'
  'uv publish'
  'poetry publish'
  'python -m twine upload'
  'npm publish'
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$CMD" | grep -qE "$pattern"; then
    echo "BLOCKED by claude-autonomy safety hook." >&2
    echo "Pattern matched: $pattern" >&2
    echo "Command: $CMD" >&2
    echo "" >&2
    echo "If this is genuinely needed, ask the user to run it manually outside Claude Code." >&2
    exit 2
  fi
done

# Block direct git commit/push on protected branches (defense-in-depth)
BRANCH=""
# Ask git, do not look for a .git DIRECTORY: in a `git worktree` checkout .git is a FILE.
# With the old `[ -d .../.git ]` the branch stayed unknown there and a push from a
# protected branch was allowed (evals: bd-push-on-protected-branch-in-worktree).
if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && git -C "$CLAUDE_PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH=$(git -C "$CLAUDE_PROJECT_DIR" branch --show-current 2>/dev/null || echo "")
fi

PROTECTED_BRANCHES=("main" "master" "production" "prod" "release")
for protected in "${PROTECTED_BRANCHES[@]}"; do
  if [ "$BRANCH" = "$protected" ]; then
    if echo "$CMD" | grep -qE '(^|[;&|(`])[[:space:]]*git[[:space:]]+(-[^[:space:]]+[[:space:]]+([^-][^[:space:]]*[[:space:]]+)?)*(commit|push)([[:space:]]|$)'; then
      echo "BLOCKED: direct git $(echo "$CMD" | awk '{print $2}') on protected branch '$BRANCH'." >&2
      echo "Create a feature branch first: git checkout -b feat/<slug>" >&2
      exit 2
    fi
  fi
done

# Commit policy — owner-ratified 2026-08-27.
#
# Commits are allowed on an `unattended/<date>` branch and NOWHERE else. The
# checkpoint is preserved in the only place it does work: nothing reaches `main`
# without a human reading the diff. What it buys is that each session in a long
# run builds on a committed, verified base instead of on top of an unreviewed
# index it inherited from the session before it -- where one bad change is
# silently inherited by everything after.
#
# The pattern is the command-position form from S7: a bare `^` let `cd x && git
# commit` walk straight past the old check, and `git -C dir commit` hid the
# subcommand behind a global option. Both are covered here.
if echo "$CMD" | grep -qE '(^|[;&|(`])[[:space:]]*git[[:space:]]+(-[^[:space:]]+[[:space:]]+([^-][^[:space:]]*[[:space:]]+)?)*commit([[:space:]]|$)'; then
  case "$BRANCH" in
    unattended/*)
      : # allowed — an unattended run's own branch
      ;;
    *)
      echo "BLOCKED: commits are allowed only on an 'unattended/<date>' branch." >&2
      echo "Current branch: '${BRANCH:-unknown}'." >&2
      echo "On any other branch a commit is a human review checkpoint: stage with 'git add <files>'," >&2
      echo "summarise the change, suggest a message, and let the user run the commit themselves." >&2
      echo "For an unattended run, switch first: git switch -c unattended/\$(date -u +%Y-%m-%d)" >&2
      exit 2
      ;;
  esac
fi

exit 0
