"""Tests for scripts.sync_local_skills — main() CLI and sync() edge cases.

Extends test_sync_local_skills.py with coverage for the CLI entry-point,
--check with drift, --force flag, manifest collision, missing source
directories, and the FileExistsError defensive path in sync().
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.sync_local_skills import (
    collect_skill_paths,
    detect_drift,
    main,
    sync,
)


def _write_manifest(tmp_path: Path, skill_refs, *, extra_plugin=None):
    cp_dir = tmp_path / ".claude-plugin"
    cp_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cp_dir / "marketplace.json"
    plugins = [
        {
            "name": "plugin-a",
            "description": "x",
            "source": "./",
            "strict": False,
            "skills": list(skill_refs),
        }
    ]
    if extra_plugin:
        plugins.append(extra_plugin)
    manifest_path.write_text(
        json.dumps(
            {
                "name": "test-pack",
                "owner": {"name": "test-org"},
                "metadata": {"description": "x", "version": "0.0.1"},
                "plugins": plugins,
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


class TestCollectSkillPaths:
    def test_collision_raises(self, tmp_path: Path) -> None:
        manifest = {
            "plugins": [
                {"name": "p1", "skills": ["./skills/a/foo"]},
                {"name": "p2", "skills": ["./skills/b/foo"]},
            ]
        }
        with pytest.raises(SystemExit, match="collision"):
            collect_skill_paths(manifest)

    def test_dedup_same_path(self) -> None:
        manifest = {
            "plugins": [
                {"name": "p1", "skills": ["./skills/a/foo"]},
                {"name": "p2", "skills": ["./skills/a/foo"]},
            ]
        }
        result = collect_skill_paths(manifest)
        assert result == {"foo": "skills/a/foo"}


class TestDetectDriftEdgeCases:
    def test_missing_source_directory(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/ghost"])
        # Do NOT create the skill source directory.
        drift, _ = detect_drift(tmp_path, manifest)
        assert any("missing skill source" in msg for msg in drift)

    def test_unreadable_symlink(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        link = target_dir / "mart-brd"
        os.symlink("../../skills/lifecycle/mart-brd", link)
        # Patch os.readlink to raise an OSError.
        with patch("scripts.sync_local_skills.os.readlink", side_effect=OSError("boom")):
            drift, _ = detect_drift(tmp_path, manifest)
            assert any("cannot read symlink" in msg for msg in drift)


class TestSyncEdgeCases:
    def test_stale_symlink_removed(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        stale = target_dir / "old-skill"
        os.symlink("/nonexistent", stale)
        sync(tmp_path, manifest)
        assert not stale.exists()

    def test_missing_source_warns_and_skips(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/ghost"])
        result = sync(tmp_path, manifest)
        assert result == 0

    def test_wrong_symlink_refreshed(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        _make_skill(tmp_path, "skills/lifecycle/other")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        os.symlink("../../skills/lifecycle/other", target_dir / "mart-brd")
        sync(tmp_path, manifest)
        link = target_dir / "mart-brd"
        assert link.is_symlink()
        assert "mart-brd" in os.readlink(link)

    def test_non_symlink_file_replaced(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        # Create a regular file (not a dir, not a symlink) at the slot.
        (target_dir / "mart-brd").write_text("oops", encoding="utf-8")
        sync(tmp_path, manifest)
        link = target_dir / "mart-brd"
        assert link.is_symlink()

    def test_file_exists_error_handled(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        # Patch os.symlink to raise FileExistsError.
        original_symlink = os.symlink

        def side_effect(src, dst):
            if "mart-brd" in str(dst):
                raise FileExistsError("slot taken")
            return original_symlink(src, dst)

        with patch("scripts.sync_local_skills.os.symlink", side_effect=side_effect):
            result = sync(tmp_path, manifest)
            assert result == 0

    def test_stale_real_dir_not_in_skills_without_force(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        stale_dir = target_dir / "orphan-dir"
        stale_dir.mkdir()
        (stale_dir / "file.txt").write_text("data", encoding="utf-8")
        sync(tmp_path, manifest, force=False)
        assert stale_dir.exists(), "stale real dir should survive without --force"

    def test_stale_real_dir_not_in_skills_with_force(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target_dir = tmp_path / ".claude" / "skills"
        target_dir.mkdir(parents=True)
        stale_dir = target_dir / "orphan-dir"
        stale_dir.mkdir()
        (stale_dir / "file.txt").write_text("data", encoding="utf-8")
        sync(tmp_path, manifest, force=True)
        assert not stale_dir.exists()


class TestMainCLI:
    def test_check_in_sync(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        sync(tmp_path, manifest)
        assert main(["--check", "--repo-root", str(tmp_path), "--manifest", str(manifest)]) == 0

    def test_check_with_drift(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        # Do NOT run sync — drift expected.
        assert main(["--check", "--repo-root", str(tmp_path), "--manifest", str(manifest)]) == 1

    def test_sync_mode(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        assert main(["--repo-root", str(tmp_path), "--manifest", str(manifest)]) == 0
        link = tmp_path / ".claude" / "skills" / "mart-brd"
        assert link.is_symlink()

    def test_force_flag(self, tmp_path: Path) -> None:
        manifest = _write_manifest(tmp_path, ["./skills/lifecycle/mart-brd"])
        _make_skill(tmp_path, "skills/lifecycle/mart-brd")
        target = tmp_path / ".claude" / "skills" / "mart-brd"
        target.mkdir(parents=True)
        (target / "user.md").write_text("x", encoding="utf-8")
        assert main(["--force", "--repo-root", str(tmp_path), "--manifest", str(manifest)]) == 0
        assert target.is_symlink()
