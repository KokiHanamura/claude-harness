import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import harness  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "REGISTRY", tmp_path / "registry.json")
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    return r


def lock(r):
    return json.loads((r / harness.LOCK_REL).read_text())


def test_merge_unions_lists_and_normalizes_legacy_wildcards():
    base = {"permissions": {"allow": ["Bash(git status *)"]}, "a": 1}
    over = {"permissions": {"allow": ["Bash(git status:*)", "Bash(make *)"]}, "a": 2}
    assert harness.merge(base, over) == {"permissions": {"allow": ["Bash(git status *)", "Bash(make *)"]}, "a": 2}


def test_subtract_returns_only_repo_specific_parts():
    base = {"permissions": {"allow": ["x"], "deny": ["y"]}}
    cur = {"permissions": {"allow": ["x", "z"], "deny": ["y"]}, "env": {"A": "1"}}
    assert harness.subtract(cur, base) == {"permissions": {"allow": ["z"]}, "env": {"A": "1"}}
    assert harness.subtract(base, base) is None


def test_init_installs_everything_and_writes_lock(repo):
    harness.main(["init", str(repo)])
    assert (repo / ".claude/agents/codebase-researcher.md").exists()
    assert (repo / ".claude/skills/feature/SKILL.md").exists()
    assert (repo / ".claude/harness.config.json").exists()
    assert (repo / "CLAUDE.md").exists()
    settings = json.loads((repo / ".claude/settings.json").read_text())
    assert "SessionStart" in settings["hooks"]
    lk = lock(repo)
    assert lk["version"] == harness.version()
    assert ".claude/hooks/guard_bash.py" in lk["files"]
    assert ".claude/settings.local.json" in (repo / ".gitignore").read_text()
    assert json.loads(harness.REGISTRY.read_text())["repos"]


def test_existing_settings_are_captured_into_overlay_without_legacy_hooks(repo):
    (repo / ".claude").mkdir()
    (repo / ".claude/settings.json").write_text(json.dumps({
        "permissions": {"allow": ["Bash(git status:*)", "Bash(.venv/bin/python -m pytest:*)"]},
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "afplay /System/Library/Sounds/Hero.aiff"}]}]},
    }))
    harness.main(["init", str(repo)])
    overlay = json.loads((repo / harness.OVERLAY_REL).read_text())
    assert overlay == {"permissions": {"allow": ["Bash(.venv/bin/python -m pytest:*)"]}}
    settings = json.loads((repo / ".claude/settings.json").read_text())
    assert "Bash(.venv/bin/python -m pytest:*)" in settings["permissions"]["allow"]


def test_resync_is_idempotent(repo, capsys):
    harness.main(["init", str(repo)])
    capsys.readouterr()
    assert harness.main(["sync", str(repo)]) == 0
    assert "up to date" in capsys.readouterr().out


def test_local_modification_is_reported_as_conflict_and_kept(repo):
    harness.main(["init", str(repo)])
    f = repo / ".claude/agents/code-reviewer.md"
    f.write_text("local edit")
    old_hash = lock(repo)["files"][".claude/agents/code-reviewer.md"]
    # ベース側も変わったことにする
    harness_base = harness.BASE_DIR / ".claude/agents/code-reviewer.md"
    original = harness_base.read_text()
    try:
        harness_base.write_text(original + "\n<!-- upstream change -->\n")
        assert harness.main(["sync", str(repo)]) == 1
        assert f.read_text() == "local edit"
        assert lock(repo)["files"][".claude/agents/code-reviewer.md"] == old_hash
        assert harness.main(["sync", str(repo), "--force"]) == 0
        assert "upstream change" in f.read_text()
    finally:
        harness_base.write_text(original)


def test_seed_files_are_never_overwritten(repo):
    harness.main(["init", str(repo)])
    (repo / "CLAUDE.md").write_text("mine")
    harness.main(["sync", str(repo)])
    assert (repo / "CLAUDE.md").read_text() == "mine"


def test_direct_settings_edit_is_moved_to_overlay_on_next_sync(repo):
    harness.main(["init", str(repo)])
    s = json.loads((repo / ".claude/settings.json").read_text())
    s["env"] = {"FOO": "1"}
    (repo / ".claude/settings.json").write_text(json.dumps(s))
    harness.main(["sync", str(repo)])
    assert json.loads((repo / harness.OVERLAY_REL).read_text()) == {"env": {"FOO": "1"}}
    assert json.loads((repo / ".claude/settings.json").read_text())["env"] == {"FOO": "1"}


def test_manifest_removed_files_are_deleted(repo):
    legacy = repo / ".claude/skills/daily-setup.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("old")
    harness.main(["init", str(repo)])
    assert not legacy.exists()


def test_noop_sync_does_not_touch_lock_and_dry_run_is_quiet(repo, capsys):
    harness.main(["init", str(repo)])
    before = (repo / harness.LOCK_REL).read_text()
    capsys.readouterr()
    harness.main(["sync", str(repo), "--dry-run"])
    assert "up to date" in capsys.readouterr().out
    harness.main(["sync", str(repo)])
    assert (repo / harness.LOCK_REL).read_text() == before
