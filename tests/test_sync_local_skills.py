"""Tests for scripts.sync_local_skills.

Covers:
- The drift detector (`--check` mode) returns failure when the
  manifest and `.claude/skills/` disagree.
- The L2 safety guard refuses to clobber non-symlink directories
  unless `--force` is set.
- The happy path: a fresh sync produces a symlink per declared skill,
  and a follow-up `--check` returns no drift.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.sync_local_skills import detect_drift, sync


def _write_manifest(tmp_path: Path, skill_refs):
    cp_dir = tmp_path / ".claude-plugin"
    cp_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cp_dir / "marketplace.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": "test-pack",
                "owner": {"name": "test-org"},
                "metadata": {"description": "x", "version": "0.0.1"},
                "plugins": [
                    {
                        "name": "plugin-a",
                        "description": "x",
                        "source": "./",
                        "strict": False,
                        "skills": list(skill_refs),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _make_skill(tmp_path: Path, rel: str) -> None:
    skill_dir = tmp_path / rel.lstrip("./")
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_dir.name}\ndescription: stub\n---\n",
        encoding="utf-8",
    )


class TestSyncHappyPath:
    def test_fresh_sync_creates_symlinks(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        assert sync(tmp_path, manifest) == 0
        link = tmp_path / ".claude" / "skills" / "mart-brd"
        assert link.is_symlink()
        assert (link / "SKILL.md").exists()

    def test_check_passes_after_sync(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        sync(tmp_path, manifest)
        drift, _ = detect_drift(tmp_path, manifest)
        assert drift == []


class TestCheckModeDetectsDrift:
    """M3: the drift detector must catch every realistic way the
    `.claude/skills/` mirror can fall out of sync with the manifest.
    """

    def test_missing_symlink_for_declared_skill(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        # No .claude/skills/ created — pure drift.
        drift, _ = detect_drift(tmp_path, manifest)
        assert drift
        assert any("mart-brd" in msg and "missing" in msg for msg in drift)

    def test_extra_symlink_not_in_manifest(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        _make_skill(tmp_path, "skills/lifecycle/orphan")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        os.symlink("../../skills/lifecycle/mart-brd", target_dir / "mart-brd")
        os.symlink("../../skills/lifecycle/orphan", target_dir / "orphan")
        drift, _ = detect_drift(tmp_path, manifest)
        assert any("orphan" in msg and "not in the manifest" in msg for msg in drift)

    def test_real_directory_is_drift(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills" / "mart-brd"
        target_dir.mkdir(parents=True)
        (target_dir / "SKILL.md").write_text(
            "---\nname: mart-brd\n---\n", encoding="utf-8"
        )
        drift, _ = detect_drift(tmp_path, manifest)
        assert any("real directory" in msg for msg in drift)

    def test_wrong_symlink_target_is_drift(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        _make_skill(tmp_path, "skills/lifecycle/other")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        os.symlink("../../skills/lifecycle/other", target_dir / "mart-brd")
        drift, _ = detect_drift(tmp_path, manifest)
        assert any("points at" in msg for msg in drift)


class TestForceGuard:
    """L2: sync must refuse to remove a real directory under
    `.claude/skills/<name>` unless --force is passed."""

    def test_real_directory_preserved_without_force(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target = tmp_path / ".claude" / "skills" / "mart-brd"
        target.mkdir(parents=True)
        marker = target / "user-authored.md"
        marker.write_text("do not lose me\n", encoding="utf-8")

        # Run sync without --force; user data must survive.
        sync(tmp_path, manifest, force=False)
        assert marker.exists(), "L2 regression: real directory was wiped without --force"

    def test_real_directory_overwritten_with_force(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target = tmp_path / ".claude" / "skills" / "mart-brd"
        target.mkdir(parents=True)
        marker = target / "user-authored.md"
        marker.write_text("ok to lose\n", encoding="utf-8")

        sync(tmp_path, manifest, force=True)
        # Now mart-brd should be a symlink, and the marker should be gone.
        link = tmp_path / ".claude" / "skills" / "mart-brd"
        assert link.is_symlink()
        assert not marker.exists()
