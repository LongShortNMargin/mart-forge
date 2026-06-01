"""Tests for scripts.validate_marketplace.

Covers AC#1 of EMB-322: the marketplace manifest parses, declares the
expected plugin count, and every skill ref resolves to a directory
containing a valid SKILL.md.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from scripts.validate_marketplace import validate


VALID_SKILL_MD = textwrap.dedent(
    """
    ---
    name: example-skill
    description: stub for tests
    ---

    # example-skill

    body
    """
).strip() + "\n"


def _make_skill(root: Path, group: str, name: str) -> None:
    d = root / "skills" / group / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(VALID_SKILL_MD.replace("example-skill", name), encoding="utf-8")


def _write_manifest(root: Path, manifest: dict) -> Path:
    plugin_dir = root / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    p = plugin_dir / "marketplace.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def _good_manifest() -> dict:
    return {
        "name": "test-pack",
        "owner": {"name": "tester"},
        "metadata": {"description": "test", "version": "0.0.1"},
        "plugins": [
            {
                "name": "g1",
                "description": "d1",
                "source": "./",
                "strict": False,
                "skills": ["./skills/lifecycle/a"],
            },
            {
                "name": "g2",
                "description": "d2",
                "source": "./",
                "strict": False,
                "skills": ["./skills/workflow/b"],
            },
            {
                "name": "g3",
                "description": "d3",
                "source": "./",
                "strict": False,
                "skills": ["./skills/duckdb/c"],
            },
            {
                "name": "g4",
                "description": "d4",
                "source": "./",
                "strict": False,
                "skills": ["./skills/quality/d"],
            },
        ],
    }


def _seed_repo(tmp_path: Path) -> Path:
    _make_skill(tmp_path, "lifecycle", "a")
    _make_skill(tmp_path, "workflow", "b")
    _make_skill(tmp_path, "duckdb", "c")
    _make_skill(tmp_path, "quality", "d")
    return tmp_path


class TestHappyPath:
    def test_valid_manifest_passes(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        manifest = _write_manifest(repo, _good_manifest())
        assert validate(manifest, repo) == []


class TestStructureChecks:
    def test_invalid_json_rejected(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        p = plugin_dir / "marketplace.json"
        p.write_text("{not valid", encoding="utf-8")
        errors = validate(p, tmp_path)
        assert errors
        assert any("invalid JSON" in e for e in errors)

    def test_missing_top_level_key_rejected(self, tmp_path: Path) -> None:
        manifest = _good_manifest()
        del manifest["plugins"]
        p = _write_manifest(tmp_path, manifest)
        errors = validate(p, tmp_path)
        assert any("plugins" in e for e in errors)

    def test_wrong_plugin_count_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        manifest = _good_manifest()
        manifest["plugins"] = manifest["plugins"][:2]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("expected 4 plugins" in e for e in errors)

    def test_plugin_without_skills_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        manifest = _good_manifest()
        manifest["plugins"][0]["skills"] = []
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("must list >= 1 skill" in e for e in errors)

    def test_duplicate_plugin_name_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        manifest = _good_manifest()
        manifest["plugins"][1]["name"] = manifest["plugins"][0]["name"]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("duplicate plugin name" in e for e in errors)


class TestSkillPathChecks:
    def test_missing_skill_dir_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        manifest = _good_manifest()
        manifest["plugins"][0]["skills"] = ["./skills/lifecycle/ghost"]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("does not exist on disk" in e for e in errors)

    def test_skill_dir_without_skill_md_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        empty_dir = repo / "skills" / "lifecycle" / "empty"
        empty_dir.mkdir(parents=True)
        manifest = _good_manifest()
        manifest["plugins"][0]["skills"] = ["./skills/lifecycle/empty"]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("missing SKILL.md" in e for e in errors)

    def test_skill_md_without_frontmatter_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        bad_dir = repo / "skills" / "lifecycle" / "noframe"
        bad_dir.mkdir(parents=True)
        (bad_dir / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
        manifest = _good_manifest()
        manifest["plugins"][0]["skills"] = ["./skills/lifecycle/noframe"]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("frontmatter" in e for e in errors)

    def test_skill_md_missing_name_in_frontmatter_rejected(
        self, tmp_path: Path
    ) -> None:
        repo = _seed_repo(tmp_path)
        bad_dir = repo / "skills" / "lifecycle" / "nokey"
        bad_dir.mkdir(parents=True)
        (bad_dir / "SKILL.md").write_text(
            "---\ndescription: only a description\n---\n", encoding="utf-8"
        )
        manifest = _good_manifest()
        manifest["plugins"][0]["skills"] = ["./skills/lifecycle/nokey"]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("frontmatter missing required keys" in e for e in errors)

    def test_non_relative_skill_path_rejected(self, tmp_path: Path) -> None:
        repo = _seed_repo(tmp_path)
        manifest = _good_manifest()
        manifest["plugins"][0]["skills"] = ["/absolute/path/skill"]
        p = _write_manifest(repo, manifest)
        errors = validate(p, repo)
        assert any("relative path beginning with './'" in e for e in errors)


class TestRealManifest:
    """Pin against the actual repo manifest so any drift between the
    manifest and the on-disk skills tree is caught."""

    def test_repo_manifest_passes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        manifest = repo_root / ".claude-plugin" / "marketplace.json"
        if not manifest.exists():
            pytest.skip("marketplace.json not present in this checkout")
        errors = validate(manifest, repo_root)
        assert errors == [], f"manifest drift: {errors}"

    def test_repo_manifest_declares_four_plugins(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        manifest_path = repo_root / ".claude-plugin" / "marketplace.json"
        if not manifest_path.exists():
            pytest.skip("marketplace.json not present in this checkout")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(manifest["plugins"]) == 4

    def test_repo_skill_count_at_least_21(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        skills_root = repo_root / "skills"
        if not skills_root.exists():
            pytest.skip("./skills not present")
        total = 0
        for group in skills_root.iterdir():
            if group.is_dir():
                for skill in group.iterdir():
                    if skill.is_dir() and (skill / "SKILL.md").exists():
                        total += 1
        assert total >= 21, f"AC#2 wants >= 21 skills, found {total}"
