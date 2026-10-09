#!/usr/bin/env bash
# Board 739: what `merge=union` does to the engine's journals. Two branches each add one entry
# (in the real format of the journal); a third case removes a line next to the other side's
# append. Run: bash .engine/artifacts/739-union/probe.sh — needs only git.
set -u
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
scene() {  # name, base text, python edit for branch a, python edit for branch b
  local dir="$work/$1"
  git init -q -b main "$dir" && cd "$dir" || exit 1
  git config user.name t; git config user.email t@t
  echo 'journal.md merge=union' > .gitattributes
  printf '%b' "$2" > journal.md
  git add -A && git commit -qm base
  git switch -qc a && python3 -c "$3" && git commit -qam a
  git switch -q main && git switch -qc b && python3 -c "$4" && git commit -qam b
  git merge -q a -m merge >/dev/null 2>&1; echo "=== $1 (merge exit $?)"; cat journal.md; echo
}
ins_top='t=open("journal.md").read(); i=t.index("## 2026"); open("journal.md","w").write(t[:i]+E+t[i:])'
app='open("journal.md","a").write(E)'
scene ledger-newest-first '# Ledger\n\n---\n## 2026-10-01T00:00Z — old — PASS\n- Verdict: PASS\n' \
  "E='## 2026-10-02T01:00Z — slice-a — PASS\n- Verdict: PASS\n- Check: none\n- Auditor: overseer agent\n\n'; $ins_top" \
  "E='## 2026-10-02T02:00Z — slice-b — PASS\n- Verdict: PASS\n- Check: none\n- Auditor: overseer agent\n\n'; $ins_top"
scene anomalies-appended '# Anomalies\n\n## 2026-10-01T00:00Z — 001\n- Що сталося: a\n- Хто записав: runner\n' \
  "E='\n## 2026-10-02T01:00Z — 002\n- Що сталося: c\n- Хто записав: runner\n'; $app" \
  "E='\n## 2026-10-02T02:00Z — 003\n- Що сталося: e\n- Хто записав: runner\n'; $app"
scene lesson-queue-resolved-next-to-append '# Lesson queue\n\n- 2026-10-01 | agent | s1 | one #aaaa1111\n- 2026-10-02 | agent | s2 | two #bbbb2222\n' \
  't=open("journal.md").read().replace("- 2026-10-02 | agent | s2 | two #bbbb2222\n",""); open("journal.md","w").write(t)' \
  "E='- 2026-10-03 | agent | s3 | three #cccc3333\n'; $app"
