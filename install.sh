#!/usr/bin/env bash
# Deploy this repo's user-scoped content into ~/.claude/.
#
# WHY THIS EXISTS
# ---------------
# This repo holds two kinds of content with different scopes:
#
#   .claude/   PROJECT-scoped. Copied into a target project (docs/TEMPLATE-SETUP.md).
#              Loaded by Claude Code only when the cwd is that project.
#   user/      USER-scoped. Symlinked into ~/.claude/ by this script.
#              Loaded by Claude Code in EVERY directory, including repos that
#              know nothing about this one.
#
# The live-build skill must resolve in an unrelated repository, so it is
# user-scoped and lives under user/. Putting it in .claude/skills/ would scope
# it to this repo and it would not exist where it is needed.
#
# SYMLINK, NOT COPY — verified, not assumed. The Claude Code skill loader
# dereferences symlinks: a probe skill symlinked from ~/.claude/skills/ into
# this repo listed correctly from an unrelated cwd (2026-08-26). Symlinking
# keeps exactly one copy of every file, so an edit in the repo is live
# immediately and a stale deployed copy is impossible by construction.
#
# The alternative — copying — is what this repo already does by hand for hooks,
# and ~/.claude/hooks/verify-on-stop.sh has drifted 224 lines from
# .claude/hooks/verify-on-stop.sh, with two hooks missing from the home copy
# entirely. That is the failure this script exists to avoid.
#
# Idempotent: safe to re-run. Replaces its own symlinks, refuses to clobber
# anything it did not create.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"

link_one() {
    local source="$1" target="$2"

    if [ -L "$target" ]; then
        # Ours (or a previous run's). Repoint it.
        ln -sfn "$source" "$target"
        printf '  relinked  %s -> %s\n' "$target" "$source"
        return
    fi

    if [ -e "$target" ]; then
        # A real file or directory we did not create. Never destroy it.
        printf '  SKIPPED   %s already exists and is not a symlink.\n' "$target" >&2
        printf '            Move or delete it, then re-run. Nothing was changed.\n' >&2
        return 1
    fi

    mkdir -p "$(dirname "$target")"
    ln -s "$source" "$target"
    printf '  linked    %s -> %s\n' "$target" "$source"
}

main() {
    local failed=0

    printf 'Deploying user-scoped content from %s into %s\n\n' "$REPO_ROOT/user" "$CLAUDE_HOME"

    if [ ! -d "$REPO_ROOT/user" ]; then
        printf 'Nothing to deploy: %s does not exist.\n' "$REPO_ROOT/user" >&2
        exit 1
    fi

    # Link each leaf (each skill), not the skills/ directory itself, so
    # skills installed by other means are left alone.
    for skill in "$REPO_ROOT"/user/skills/*/; do
        [ -d "$skill" ] || continue
        link_one "${skill%/}" "$CLAUDE_HOME/skills/$(basename "$skill")" || failed=1
    done

    printf '\n'
    if [ "$failed" -ne 0 ]; then
        printf 'Finished with skips — see above. Re-run after resolving.\n' >&2
        exit 1
    fi
    printf 'Done. Verify with:  claude -p "List the exact names of every skill available to you."\n'
    printf 'Run that from a directory OUTSIDE this repo — user scope is the whole point.\n'
}

main "$@"
