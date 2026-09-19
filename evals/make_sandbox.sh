#!/usr/bin/env bash
# Build a throwaway sandbox project: the reference project + the engine taken
# from ONE git ref, installed the way docs/TEMPLATE-SETUP.md installs it today.
#
#   evals/make_sandbox.sh <engine-ref> <target-dir> [--no-sync] [--audit-fixtures]
#
#   <engine-ref>       tag, branch or commit of THIS repository (e.g. v0.9.0)
#   <target-dir>       new directory OUTSIDE this repository (must not exist)
#   --no-sync          skip `uv sync` (no .venv; verify/format scenarios will not
#                      find ruff, mypy or pytest)
#   --audit-fixtures   also install the slice contract and PROGRESS.md the manual
#                      audit scenarios rely on (evals/scenarios/audit/fixtures/)
#
# WHY A SEPARATE REPOSITORY. A project nested inside the engine repository would
# see two .claude/ directories (its own and the engine's), and every result
# would depend on which one a tool picked. A fresh git repository outside the
# engine removes the question, and building it from a ref makes two engine
# versions comparable on identical ground.
#
# The sandbox is disposable. Never point <target-dir> at a real project.
set -euo pipefail

die() { printf 'make_sandbox: %s\n' "$*" >&2; exit 1; }

USAGE="usage: evals/make_sandbox.sh <engine-ref> <target-dir> [--no-sync] [--audit-fixtures]"
[ $# -ge 2 ] || die "$USAGE"
REF="$1"; TARGET="$2"; shift 2
SYNC=1; AUDIT=0
for flag in "$@"; do
  case "$flag" in
    --no-sync) SYNC=0 ;;
    --audit-fixtures) AUDIT=1 ;;
    *) die "unknown option '$flag' — $USAGE" ;;
  esac
done

command -v git >/dev/null 2>&1 || die "git is required"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REFPROJ="$REPO_ROOT/evals/reference-project"
[ -f "$REFPROJ/pyproject.toml" ] || die "reference project not found at $REFPROJ"

COMMIT="$(git -C "$REPO_ROOT" rev-parse --verify --quiet "${REF}^{commit}")" \
  || die "engine ref '$REF' does not exist in $REPO_ROOT"

[ -e "$TARGET" ] && die "$TARGET already exists — sandboxes are created fresh, never reused"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
case "$TARGET/" in
  "$REPO_ROOT"/*) rmdir "$TARGET"; die "target must be OUTSIDE the engine repository" ;;
esac

# 1. Reference project: tracked and untracked files, never ignored ones (.venv, caches).
( cd "$REFPROJ" && git ls-files -co --exclude-standard -z . ) \
  | ( cd "$REFPROJ" && tar --null -T - -cf - ) | tar -xf - -C "$TARGET"

# 2. Engine from the ref — TEMPLATE-SETUP step 1: .claude/ wholesale, plus the
#    CLAUDE.md and AGENTS.md starting points. Paths a ref does not have are skipped.
PATHS=()
for p in .claude CLAUDE.md AGENTS.md; do
  git -C "$REPO_ROOT" cat-file -e "$COMMIT:$p" 2>/dev/null && PATHS+=("$p")
done
[ ${#PATHS[@]} -gt 0 ] || die "ref '$REF' has no .claude/ to install"
git -C "$REPO_ROOT" archive "$COMMIT" "${PATHS[@]}" | tar -xf - -C "$TARGET"

# The engine's ignore rules travel with it (TEMPLATE-SETUP copies .gitignore too).
if git -C "$REPO_ROOT" cat-file -e "$COMMIT:.gitignore" 2>/dev/null; then
  { printf '\n# --- engine ignore rules (from %s) ---\n' "$REF"
    git -C "$REPO_ROOT" show "$COMMIT:.gitignore"; } >> "$TARGET/.gitignore"
fi

# TEMPLATE-SETUP cleanup: nothing compiled, nothing machine-local.
find "$TARGET/.claude" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -f "$TARGET/.claude/settings.local.json"

# Fixtures go in AFTER the engine so they win over any file the ref shipped at the same path.
if [ "$AUDIT" -eq 1 ]; then
  cp -R "$REPO_ROOT/evals/scenarios/audit/fixtures/." "$TARGET/"
fi

# 3. Record what the ref SHIPPED, then normalise the supervision state.
#    A ref may ship .claude/overseer/mode = "unattended"; scenarios need the
#    documented default (attended) and set anything else explicitly.
SHIPPED_MODE="absent"
MODE_FILE="$TARGET/.claude/overseer/mode"
if [ -f "$MODE_FILE" ]; then
  SHIPPED_MODE="$(tr -d '[:space:]' < "$MODE_FILE")"
  printf 'attended\n' > "$MODE_FILE"
fi
cat > "$TARGET/SANDBOX-INFO.json" <<JSON
{
  "engine_ref": "$REF",
  "engine_commit": "$COMMIT",
  "shipped_supervision_mode": "$SHIPPED_MODE",
  "installed_by": "evals/make_sandbox.sh (git archive, TEMPLATE-SETUP step 1)",
  "audit_fixtures": $([ "$AUDIT" -eq 1 ] && echo true || echo false),
  "created_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

# 4. A real repository: hooks read the branch, the diff and the index.
git -C "$TARGET" init -q -b main
git -C "$TARGET" add -A -f .claude/overseer/mode 2>/dev/null || true
git -C "$TARGET" add -A
git -C "$TARGET" -c user.name="engine-sandbox" -c user.email="sandbox@example.invalid" \
  commit -q -m "sandbox: reference project + engine $REF"

# 5. Toolchain for the verify/format scenarios.
if [ "$SYNC" -eq 1 ]; then
  command -v uv >/dev/null 2>&1 || die "uv not found — install it or pass --no-sync"
  ( cd "$TARGET" && uv sync -q ) || die "uv sync failed (network needed once; later runs use the uv cache)"
fi

printf 'sandbox ready: %s\n  engine: %s (%s)\n  shipped supervision mode: %s\n' \
  "$TARGET" "$REF" "${COMMIT:0:7}" "$SHIPPED_MODE"
printf 'next: python3 evals/run_hook_scenarios.py --sandbox %q --out results-%s.json\n' "$TARGET" "$REF"
