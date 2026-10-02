#!/usr/bin/env python3
"""`engine.py install --personal` merges the personal layer into a home settings file the
way docs/plan/package-3b.md asks: --dry-run writes nothing, a second run changes nothing,
keys the layer does not name are kept, a backup is written before the file changes, and a
layer that wires hooks is refused.

Every case runs against a SYNTHETIC engine repository (one commit, one tag) and a temporary
home directory, so nothing under the real ~/.claude is touched and every expectation is
exact. engine.py is copied into that engine, as test_engine_install.py does: it finds its
repository relative to itself. The last group checks this repository's own user/settings.json
holds exactly the personal keys the plan moves.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ENGINE_PY = ROOT / "engine.py"
PERSONAL_HERE = ROOT / "user/settings.json"

LAYER: dict[str, Any] = {
    "_comment": "a comment key is not a setting",
    "permissions": {
        "defaultMode": "acceptEdits",
        "additionalDirectories": ["~/.claude/", "/tmp/claude/"],
        "allow": ["WebFetch", "WebSearch"],
    },
    "env": {"ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5"},
}


class Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ok   {name}")
        else:
            self.failed += 1
            print(f"  FAIL {name}  {detail[:800]}")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def snapshot(home: Path) -> dict[str, bytes]:
    return {str(p.relative_to(home)): p.read_bytes() for p in sorted(home.rglob("*")) if p.is_file()}


def main() -> int:
    t = Checks()
    with tempfile.TemporaryDirectory(prefix="personal-layer-test-") as tmp:
        tmp_path = Path(tmp)
        eng = tmp_path / "engine"
        eng.mkdir()
        git(eng, "init", "-q", "-b", "main")
        (eng / "user").mkdir()
        (eng / "user/settings.json").write_text(json.dumps(LAYER, indent=2) + "\n", encoding="utf-8")
        (eng / ".claude").mkdir()
        (eng / ".claude/ownership.txt").write_text("user  user/**\nproject  **\n", encoding="utf-8")
        git(eng, "add", "-A")
        git(eng, "commit", "-q", "-m", "v1")
        git(eng, "tag", "v1.0.0")
        bad = dict(LAYER)
        bad["hooks"] = {"Stop": [{"hooks": [{"type": "command", "command": "echo twice"}]}]}
        (eng / "user/settings.json").write_text(json.dumps(bad) + "\n", encoding="utf-8")
        git(eng, "commit", "-qam", "a layer that wires hooks")
        git(eng, "tag", "v1.1.0-hooks")
        git(eng, "checkout", "-q", "v1.0.0", "--", "user/settings.json")
        git(eng, "commit", "-qam", "back to a clean layer")
        shutil.copy2(ENGINE_PY, eng / "engine.py")

        def engine(*args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
            env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
            env.update(env_extra or {})
            return subprocess.run(
                [sys.executable, str(eng / "engine.py"), *args], capture_output=True, text=True, env=env, check=False
            )

        # --- a home without a settings file ---------------------------------------------------
        home = tmp_path / "home-empty"
        home.mkdir()
        r = engine("install", "--personal", "--home", str(home), "--ref", "v1.0.0", "--dry-run")
        t.check("dry run: exit 0", r.returncode == 0, r.stdout + r.stderr)
        t.check("dry run: writes nothing, not even the file", snapshot(home) == {}, str(snapshot(home)))
        t.check("dry run: says what it would set", "set     permissions" in r.stdout and "dry run" in r.stdout, r.stdout)
        r = engine("install", "--personal", "--home", str(home), "--ref", "v1.0.0")
        t.check("fresh: exit 0", r.returncode == 0, r.stdout + r.stderr)
        written = json.loads((home / "settings.json").read_text(encoding="utf-8"))
        expected = {k: v for k, v in LAYER.items() if not k.startswith("_")}
        t.check("fresh: the file holds exactly the layer (comment keys dropped)", written == expected, json.dumps(written))
        t.check("fresh: no backup when there was no file", not list(home.glob("settings.json.engine-backup-*")))

        # --- a home with foreign keys, an overlapping list and a different scalar -------------
        home = tmp_path / "home-owned"
        home.mkdir()
        before = {
            "model": "some-model[1m]",
            "theme": "dark",
            "permissions": {"defaultMode": "default", "allow": ["WebSearch", "Bash(ls:*)"]},
            "env": {"FOO": "bar"},
        }
        (home / "settings.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
        r = engine("install", "--personal", "--home", str(home), "--ref", "v1.0.0")
        t.check("merge: exit 0", r.returncode == 0, r.stdout + r.stderr)
        after = json.loads((home / "settings.json").read_text(encoding="utf-8"))
        t.check("merge: foreign keys are kept", after["model"] == "some-model[1m]" and after["theme"] == "dark" and after["env"]["FOO"] == "bar")
        t.check("merge: a scalar the layer names is set (and reported with its old value)", after["permissions"]["defaultMode"] == "acceptEdits" and "(was \"default\")" in r.stdout, r.stdout)
        t.check(
            "merge: lists gain what they lack, keep their order, repeat nothing",
            after["permissions"]["allow"] == ["WebSearch", "Bash(ls:*)", "WebFetch"],
            str(after["permissions"]["allow"]),
        )
        t.check("merge: a list the file lacked is added whole", after["permissions"]["additionalDirectories"] == ["~/.claude/", "/tmp/claude/"])
        backups = list(home.glob("settings.json.engine-backup-*"))
        t.check("merge: one backup, holding the file as it was", len(backups) == 1 and json.loads(backups[0].read_text()) == before, str(backups))
        t.check("merge: the backup is named in the output", bool(backups) and backups[0].name in r.stdout, r.stdout)

        # --- idempotence --------------------------------------------------------------------
        files_before = snapshot(home)
        r = engine("install", "--personal", "--home", str(home), "--ref", "v1.0.0")
        t.check("second run: exit 0 and 0 changes", r.returncode == 0 and "0 change(s)" in r.stdout, r.stdout)
        t.check("second run: nothing written, no new backup", snapshot(home) == files_before)

        # --- refusals -----------------------------------------------------------------------
        files_before = snapshot(home)
        r = engine("install", "--personal", "--home", str(home), "--ref", "v1.1.0-hooks")
        t.check("refuse: a layer that wires hooks (exit 2, says why)", r.returncode == 2 and "must not" in r.stderr and "hooks" in r.stderr, r.stderr)
        t.check("refuse: and writes nothing", snapshot(home) == files_before)
        broken = tmp_path / "home-broken"
        broken.mkdir()
        (broken / "settings.json").write_text("{not json", encoding="utf-8")
        r = engine("install", "--personal", "--home", str(broken), "--ref", "v1.0.0")
        t.check("refuse: a home file that is not JSON (exit 2, left as it is)", r.returncode == 2 and (broken / "settings.json").read_text() == "{not json" and not list(broken.glob("*backup*")), r.stderr)
        clash = tmp_path / "home-clash"
        clash.mkdir()
        (clash / "settings.json").write_text(json.dumps({"permissions": "a string"}), encoding="utf-8")
        r = engine("install", "--personal", "--home", str(clash), "--ref", "v1.0.0")
        t.check("refuse: a shape conflict between the file and the layer", r.returncode == 2 and "resolve that by hand" in r.stderr, r.stderr)
        r = engine("install", str(tmp_path), "--personal", "--ref", "v1.0.0")
        t.check("refuse: a project AND --personal", r.returncode == 2 and "either" in r.stderr, r.stderr)
        r = engine("install", "--ref", "v1.0.0")
        t.check("refuse: neither a project nor --personal", r.returncode == 2, r.stderr)

        # --- the config directory comes from CLAUDE_CONFIG_DIR when --home is absent ---------
        cfg = tmp_path / "config-dir"
        r = engine("install", "--personal", "--ref", "v1.0.0", "--dry-run", env_extra={"CLAUDE_CONFIG_DIR": str(cfg)})
        t.check("CLAUDE_CONFIG_DIR names the home when --home is absent", r.returncode == 0 and str(cfg / "settings.json") in r.stdout, r.stdout)
        t.check("…and the dry run created nothing there", not cfg.exists())

    # --- this repository's own personal layer -------------------------------------------------
    own: dict[str, Any] = json.loads(PERSONAL_HERE.read_text(encoding="utf-8"))
    settings = {k: v for k, v in own.items() if not k.startswith("_")}
    t.check("user/settings.json: only permissions and env", set(settings) == {"permissions", "env"}, str(set(settings)))
    perm = settings["permissions"]
    t.check("user/settings.json: defaultMode acceptEdits", perm.get("defaultMode") == "acceptEdits")
    t.check("user/settings.json: home directories as additionalDirectories", bool(perm.get("additionalDirectories")) and all(d.startswith(("~/", "/tmp/")) for d in perm["additionalDirectories"]), str(perm.get("additionalDirectories")))
    t.check("user/settings.json: WebFetch and WebSearch, nothing else, in allow", sorted(perm.get("allow", [])) == ["WebFetch", "WebSearch"])
    t.check("user/settings.json: only model variables under env", all(k.endswith("_MODEL") for k in settings["env"]) and len(settings["env"]) == 4, str(settings["env"]))
    t.check("user/settings.json: wires no hooks", "hooks" not in own)

    print(f"\nPASS {t.passed}   FAIL {t.failed}")
    return 1 if t.failed else 0


if __name__ == "__main__":
    sys.exit(main())
