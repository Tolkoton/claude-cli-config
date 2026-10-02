#!/usr/bin/env bash
# Does THIS Claude Code version let approve-project-data.py lift the permission prompt?
# Three REAL headless sessions in a throwaway project (never a real one), about $0.02 each
# on haiku. Run from the engine repository:
#
#   bash evals/probe_permission_hook.sh            # PROBE_MODEL=haiku by default
#
#   A  hook wired, write to project-owned data under .claude/  -> the file must exist
#   B  hook wired, write outside .claude/                      -> no file (prompt unanswerable headless)
#   C  hook NOT wired, the same write as A                     -> no file (the control)
#
# WHY --settings AND NOT THE PROJECT'S .claude/settings.json. A headless session in a
# workspace that has never been trusted interactively ignores that project's settings
# ("Ignoring N permissions.allow entries … this workspace has not been trusted"), hooks
# included — measured 2026-10-02 on 2.1.287. A throwaway directory is never trusted, so the
# wiring is handed to the CLI with --settings, which the trust rule does not gate. In a real
# project the owner has trusted, the same block in .claude/settings.json is what fires.
#
# WHY .claude/architecture/ AND NOT .claude/overseer/probe.md. The hook approves ONLY paths
# the ownership map calls `project`; under overseer/ that is the five named records and
# slice/, not an arbitrary file. architecture/ is a project subtree. The first run of this
# probe used overseer/probe.md and the hook correctly stayed silent — which is the test
# working, not failing.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/claude-perm-probe-XXXX")"
MODEL="${PROBE_MODEL:-haiku}"
command -v claude >/dev/null 2>&1 || { echo "claude is not on PATH"; exit 2; }
echo "work dir: $WORK  model: $MODEL  claude: $(claude --version 2>/dev/null | head -1)"

make_project() {  # $1 = dir
  mkdir -p "$1/.claude/hooks" "$1/.claude/architecture" "$1/src"
  cp "$REPO/.claude/hooks/approve-project-data.py" "$1/.claude/hooks/"
  cp "$REPO/.claude/ownership.txt" "$1/.claude/ownership.txt"
  printf '{ "permissions": { "defaultMode": "default" } }\n' > "$1/.claude/settings.json"
  cat > "$1/hook-settings.json" <<'JSON'
{ "hooks": { "PermissionRequest": [ { "matcher": "Edit|Write|MultiEdit",
  "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/approve-project-data.py\"", "timeout": 5 } ] } ] } }
JSON
  ( cd "$1" && git init -q && git add -A && git -c user.name=t -c user.email=t@t commit -qm init )
}

run_case() {  # $1 = label, $2 = dir, $3 = target (relative), $4 = expect (exists|absent), $5 = wire (yes|no)
  local prompt="Create the file $3 with exactly one line of text: probe. Use the Write tool, once. Do nothing else and do not explain."
  local extra=()
  [ "$5" = yes ] && extra=(--settings "$2/hook-settings.json")
  ( cd "$2" && claude -p "$prompt" --model "$MODEL" --output-format json --permission-mode default "${extra[@]}" \
      < /dev/null > "$2/session.json" 2> "$2/session.err" )
  local rc=$?
  local cost; cost=$(python3 -c "import json;d=json.load(open('$2/session.json'));print(d.get('total_cost_usd','?'))" 2>/dev/null || echo '?')
  local exists=absent; [ -f "$2/$3" ] && exists=exists
  local verdict=FAIL; [ "$exists" = "$4" ] && verdict=ok
  echo "  $verdict  $1: rc=$rc file=$exists (expected $4) cost=\$$cost"
  [ "$verdict" = ok ] || { python3 -c "import json;d=json.load(open('$2/session.json'));print('       result:', str(d.get('result',''))[:300])" 2>/dev/null; head -c 400 "$2/session.err"; echo; }
  [ "$verdict" = ok ]
}

fails=0
make_project "$WORK/A"; run_case "A hook wired, project data (.claude/architecture/probe.md)" "$WORK/A" ".claude/architecture/probe.md" exists yes || fails=$((fails+1))
make_project "$WORK/B"; run_case "B hook wired, outside .claude/ (src/probe.md)"              "$WORK/B" "src/probe.md"                   absent yes || fails=$((fails+1))
make_project "$WORK/C"; run_case "C no hook, project data"                                     "$WORK/C" ".claude/architecture/probe.md" absent no  || fails=$((fails+1))
echo "transcripts under $WORK (session.json / session.err per case)"
[ "$fails" -eq 0 ] && echo "PASS 3/3: the PermissionRequest hook lifts the prompt in this Claude Code version" || echo "FAIL ($fails)"
exit "$fails"
