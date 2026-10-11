#!/usr/bin/env bash
# Spike for feature task-numbers-by-class (premise PR-numbers-02): after the runner's
# `pull --rebase` and after a true merge, can git alone tell (1) which of two same-numbered
# task files appeared in history first, and (2) which side a `Залежить від:` line came from?
# Two clones of one synthetic repository; clone b pulls from clone a (no remote is written to).
set -e
W=$(mktemp -d); cd "$W"
git init -q a; cd a; git config user.email a@a; git config user.name a
mkdir -p tasks/todo; echo base > tasks/todo/100-base.md; git add -A; git commit -qm base; git branch -M work; cd ..
git clone -q -b work a b; cd b; git config user.email b@b; git config user.name b; cd ..
cd a; echo x > tasks/todo/301-a.md; printf 'Залежить від: 301\n' > tasks/todo/302-depa.md; git add -A; git commit -qm "a: 301-a"; cd ..
cd b; echo y > tasks/todo/301-b.md; git add -A; git commit -qm "b: 301-b"; printf 'Залежить від: 301\n' > tasks/todo/105-depb.md; git add -A; git commit -qm "b: dep"
git pull -q --rebase origin work
add(){ git log --diff-filter=A --format=%H --reverse -- "$1" | head -1; }
anc(){ git merge-base --is-ancestor "$1" "$2" && echo yes || echo no; }
K=$(add tasks/todo/301-a.md); L=$(add tasks/todo/301-b.md); DA=$(add tasks/todo/302-depa.md); DB=$(add tasks/todo/105-depb.md)
echo "REBASE: keeper(a) ancestor of loser(b): $(anc "$K" "$L"); loser ancestor of keeper: $(anc "$L" "$K")"
echo "  loser ancestor of b's dependent: $(anc "$L" "$DB"); loser ancestor of a's dependent: $(anc "$L" "$DA")"
cd ../a
git checkout -q -b side HEAD~1; echo z > tasks/todo/401-m1.md; git add -A; GIT_COMMITTER_DATE="2026-01-01T00:00:00Z" git commit -qm "side: 401-m1"; printf 'Залежить від: 401\n' > tasks/todo/106-dep1.md; git add -A; git commit -qm dep1
git checkout -q work; echo w > tasks/todo/401-m2.md; git add -A; GIT_COMMITTER_DATE="2026-02-01T00:00:00Z" git commit -qm "work: 401-m2"; printf 'Залежить від: 401\n' > tasks/todo/107-dep2.md; git add -A; git commit -qm dep2
git merge -q --no-edit side
addt(){ git log --diff-filter=A --format='%H %ct' --reverse -- "$1" | head -1; }
set -- $(addt tasks/todo/401-m1.md); K=$1; KT=$2; set -- $(addt tasks/todo/401-m2.md); L=$1; LT=$2
D1=$(add tasks/todo/106-dep1.md); D2=$(add tasks/todo/107-dep2.md)
echo "MERGE: m1 ancestor of m2: $(anc "$K" "$L"); m2 ancestor of m1: $(anc "$L" "$K"); m1 committed earlier: $([ "$KT" -lt "$LT" ] && echo yes || echo no)"
echo "  loser(m2) ancestor of its own side's dependent: $(anc "$L" "$D2"); of the other side's dependent: $(anc "$L" "$D1")"
mkdir -p tasks/doing; git mv tasks/todo/401-m1.md tasks/doing/401-m1.md; git commit -qm move
echo "MOVED: first add of the name in any column: $(git log --diff-filter=A --format=%s --reverse -- 'tasks/*/401-m1.md' | head -1)"
git --version
