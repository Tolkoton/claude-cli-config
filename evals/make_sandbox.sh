#!/usr/bin/env bash
# Build a throwaway sandbox project: the reference project + the engine taken
# from ONE git ref, installed the way a real project gets it (engine.py install).
#
#   evals/make_sandbox.sh <engine-ref> <target-dir> [--no-sync] [--audit-fixtures]
#
#   <engine-ref>       tag, branch or commit of THIS repository (e.g. v0.9.0)
#   <target-dir>       new directory OUTSIDE this repository (must not exist)
#   --no-sync          skip `uv sync` (no .venv; verify/format scenarios will not
#                      find ruff, mypy or pytest)
#   --audit-fixtures   also install the slice contract and .engine/PROGRESS.md the manual
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

# 2. Engine from the ref. A ref with .claude/ownership.txt is installed by engine.py, the one
#    path real projects take. An older ref predates engine.py and is installed the way its own
#    docs/TEMPLATE-SETUP.md said (.claude/ wholesale, CLAUDE.md, AGENTS.md, .gitignore appended),
#    so engine versions on both sides of the change stay comparable.
if git -C "$REPO_ROOT" cat-file -e "$COMMIT:.claude/ownership.txt" 2>/dev/null; then
  INSTALLED_BY="engine.py install --ref $COMMIT"
  python3 "$REPO_ROOT/engine.py" install "$TARGET" --ref "$COMMIT" --no-register >/dev/null \
    || die "engine.py install of '$REF' failed (see above)"
else
  INSTALLED_BY="git archive (TEMPLATE-SETUP step 1 of a ref that predates engine.py)"
  PATHS=()
  for p in .claude CLAUDE.md AGENTS.md; do
    git -C "$REPO_ROOT" cat-file -e "$COMMIT:$p" 2>/dev/null && PATHS+=("$p")
  done
  [ ${#PATHS[@]} -gt 0 ] || die "ref '$REF' has no .claude/ to install"
  git -C "$REPO_ROOT" archive "$COMMIT" "${PATHS[@]}" | tar -xf - -C "$TARGET"

  # The engine's ignore rules travel with it (that TEMPLATE-SETUP copied .gitignore too).
  if git -C "$REPO_ROOT" cat-file -e "$COMMIT:.gitignore" 2>/dev/null; then
    { printf '\n# --- engine ignore rules (from %s) ---\n' "$REF"
      git -C "$REPO_ROOT" show "$COMMIT:.gitignore"; } >> "$TARGET/.gitignore"
  fi

  # That TEMPLATE-SETUP's cleanup: nothing compiled, nothing machine-local.
  find "$TARGET/.claude" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  rm -f "$TARGET/.claude/settings.local.json"
fi

# Fixtures go in AFTER the engine so they win over any file the ref shipped at the same path.
# .engine/PROGRESS.md is stored as PROGRESS.fixture.md: the engine's own .gitignore ignores every
# .engine/PROGRESS.md, so under its real name the fixture would never reach a commit of this repo.
FIXTURE_FILES=()
if [ "$AUDIT" -eq 1 ]; then
  FIXTURES="$REPO_ROOT/evals/scenarios/audit/fixtures"
  [ -f "$FIXTURES/PROGRESS.fixture.md" ] || die "audit fixture missing: $FIXTURES/PROGRESS.fixture.md"
  cp -R "$FIXTURES/." "$TARGET/"
  mkdir -p "$TARGET/.engine"
  mv "$TARGET/PROGRESS.fixture.md" "$TARGET/.engine/PROGRESS.md"
  while IFS= read -r -d '' f; do
    rel="${f#"$FIXTURES"/}"
    [ "$rel" = "PROGRESS.fixture.md" ] && rel=".engine/PROGRESS.md"
    FIXTURE_FILES+=("$rel")
  done < <(find "$FIXTURES" -type f -print0)
fi

# 3. Record what the ref SHIPPED, then normalise the supervision state.
#    A ref may ship .claude/state/overseer/mode = "unattended"; scenarios need the
#    documented default (attended) and set anything else explicitly.
SHIPPED_MODE="absent"
MODE_FILE="$TARGET/.claude/state/overseer/mode"
if [ -f "$MODE_FILE" ]; then
  SHIPPED_MODE="$(tr -d '[:space:]' < "$MODE_FILE")"
  printf 'attended\n' > "$MODE_FILE"
fi
cat > "$TARGET/SANDBOX-INFO.json" <<JSON
{
  "engine_ref": "$REF",
  "engine_commit": "$COMMIT",
  "shipped_supervision_mode": "$SHIPPED_MODE",
  "installed_by": "evals/make_sandbox.sh: $INSTALLED_BY",
  "audit_fixtures": $([ "$AUDIT" -eq 1 ] && echo true || echo false),
  "created_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

# 4. A real repository: hooks read the branch, the diff and the index.
git -C "$TARGET" init -q -b main
git -C "$TARGET" add -A -f .claude/state/overseer/mode 2>/dev/null || true
git -C "$TARGET" add -A
# Fixtures are FORCE-added: an older ref's appended ignore rules ignore .engine/PROGRESS.md, and an
# untracked, ignored file is deleted by the runner's reset (`git clean -fdx`).
for rel in "${FIXTURE_FILES[@]:-}"; do
  [ -n "$rel" ] && git -C "$TARGET" add -f -- "$rel"
done
git -C "$TARGET" -c user.name="engine-sandbox" -c user.email="sandbox@example.invalid" \
  commit -q -m "sandbox: reference project + engine $REF"

# Every fixture must be tracked, or the first reset silently removes it.
for rel in "${FIXTURE_FILES[@]:-}"; do
  [ -z "$rel" ] || git -C "$TARGET" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 \
    || die "fixture '$rel' is not tracked in the sandbox — a reset would delete it"
done

# 5. Toolchain for the verify/format scenarios.
if [ "$SYNC" -eq 1 ]; then
  command -v uv >/dev/null 2>&1 || die "uv not found — install it or pass --no-sync"
  ( cd "$TARGET" && uv sync -q ) || die "uv sync failed (network needed once; later runs use the uv cache)"
fi

printf 'sandbox ready: %s\n  engine: %s (%s)\n  shipped supervision mode: %s\n' \
  "$TARGET" "$REF" "${COMMIT:0:7}" "$SHIPPED_MODE"
printf 'next: python3 evals/run_hook_scenarios.py --sandbox %q --out results-%s.json\n' "$TARGET" "$REF"
