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
#
# NAMES. A personal skill is invoked as /<name>, in the same namespace as the engine's
# skills (.claude/skills/) and commands (.claude/commands/). A personal skill that shares
# a name with one of them would shadow it in every project the engine is installed in,
# or be shadowed by it — which one wins is not something to find out in a live session.
# So this script REFUSES to deploy when any user/skills/<name> equals an engine skill or
# command name, before it links anything. Convention for NEW personal skills: prefix the
# directory with `my-` (user/skills/my-<name>), which no engine skill will ever carry.
# Existing personal skills keep their names; the check is what protects them.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
PERSONAL_PREFIX="my-"

engine_names() {
    # Every name the engine already answers to: skills by directory, commands by file stem.
    local d f
    for d in "$REPO_ROOT"/.claude/skills/*/; do [ -d "$d" ] && basename "${d%/}"; done
    for f in "$REPO_ROOT"/.claude/commands/*.md; do [ -f "$f" ] && basename "${f%.md}"; done
}

is_engine_name() {
    # A loop, not `engine_names | grep -q`: under `set -o pipefail` grep's early exit on a
    # match sends SIGPIPE to the producer and the pipeline reports FAILURE for a hit on any
    # name but the last — the check passed a colliding `overseer` and caught `plan-slice`.
    local n
    while IFS= read -r n; do
        [ "$n" = "$1" ] && return 0
    done <<<"$ENGINE_NAMES"
    return 1
}

check_collisions() {
    local collisions=0 skill name
    ENGINE_NAMES="$(engine_names)"
    for skill in "$REPO_ROOT"/user/skills/*/; do
        [ -d "$skill" ] || continue
        name="$(basename "${skill%/}")"
        if is_engine_name "$name"; then
            printf '  COLLISION %s: user/skills/%s has the same name as an engine skill or command.\n' "$name" "$name" >&2
            printf '            Deployed, it would shadow the engine'"'"'s %s (or be shadowed by it) in every\n' "$name" >&2
            printf '            project the engine is installed in. Rename the personal skill — new ones\n' >&2
            printf '            take the prefix %s (user/skills/%s%s) — and re-run. Nothing was linked.\n' "$PERSONAL_PREFIX" "$PERSONAL_PREFIX" "$name" >&2
            collisions=1
        fi
    done
    return $collisions
}

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

    # Refuse BEFORE linking anything: a half-deployed set is worse than none.
    if ! check_collisions; then
        printf '\nRefused: a personal skill collides with an engine name (see above).\n' >&2
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
